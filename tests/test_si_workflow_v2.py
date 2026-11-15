"""Regressions against real archive/registry artifacts; model inference is not mocked."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from config.settings import BASE_DIR, DB_PATH, RAW_DATA_DIR
from ml.dataset import extract_dataset, read_json, fingerprint
from ml.registry import assign_roles
from scientific.archive import load_archive
from scientific.intelligence import ScientificRequest, answer_question
from scientific.input_validation import input_issues
from scientific.materials import Parameter
from scientific.retrieval import compatible_related


def methanol(diameter=2.5,pillar="SUPPRESSION",question_diameter=None,**changes):
    values={"o2_initial_pct":21.,"pressure_psi":14.78,"gravity_g":0.,"flow_velocity_initial_cm_s":0.,
        "diameter_mm":diameter,"co2_diluent_pct":0.,"he_diluent_pct":0.,"n2_diluent_pct":79.,
        "geometry":"Droplet","fuel_phase":"Liquid"}
    values.update(changes)
    return ScientificRequest(pillar=pillar,question=f"Estimate the natural extinction time of a {question_diameter or diameter:g} mm methanol droplet under these conditions.",
        materials=["Methanol"],parameters={k:Parameter(state="specified",value=v) for k,v in values.items()})


def cited_client():
    client=Mock();client.model_name="offline-scientific-test";client.api_key=None
    def generate(prompt,response_schema):
        payload=json.loads(prompt.split("\n",1)[1])
        source=next(s for s in payload["evidence"] if s.get("context_role")=="RELATED_OBSERVATION")
        value=source["facts"][0]["value"]
        return {"observations":[],"interpretations":[{"text":f"Other experiments reported an extinction time of {value:g} seconds under different conditions.",
            "citations":[{"source_id":source["source_id"],"quote":source["quote_options"][0]}]}],"limitations":[]}
    client.generate.side_effect=generate
    return client


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.archive=load_archive()

    def test_real_registry_new_supported_point_without_approved_model(self):
        registry=BASE_DIR/"models/flex_methanol_extinction_time"
        self.assertFalse((registry/"approved.json").exists())
        result=answer_question(methanol(),archive=self.archive,client=cited_client())
        self.assertEqual(result["route"],"ESTIMATED")
        self.assertEqual(result["prediction_status"],"RESEARCH_ONLY")
        self.assertEqual(result["interpretation_status"],"SUCCEEDED")
        prediction=result["prediction_results"][0]
        self.assertGreater(prediction["value"],0)
        self.assertEqual(prediction["unit"],"s")
        self.assertEqual(len(prediction["model_version"]),64)
        self.assertIsNone(prediction["interval"])
        self.assertIn("Research-only",result["answer"])

    def test_original_165_point_keeps_gemini_when_local_support_blocks_ml(self):
        result=answer_question(methanol(1.65),archive=self.archive,client=cited_client())
        self.assertEqual(result["prediction_status"],"BLOCKED")
        self.assertEqual(result["interpretation_status"],"SUCCEEDED")
        self.assertFalse(result["prediction_results"])
        self.assertIn("other",result["answer"].lower())
        self.assertTrue(any("independent groups" in reason for d in result["model_diagnostics"] for reason in d["reasons"]))

    def test_no_registry_does_not_block_evidence_interpretation(self):
        with tempfile.TemporaryDirectory() as folder:
            result=answer_question(methanol(),archive=self.archive,models_dir=Path(folder),client=cited_client())
        self.assertEqual(result["prediction_status"],"UNAVAILABLE")
        self.assertEqual(result["interpretation_status"],"SUCCEEDED")
        self.assertTrue(result["related_results"])

    def test_related_measurements_cannot_be_presented_as_new_predictions(self):
        client=cited_client();generate=client.generate.side_effect
        def invalid(prompt,response_schema):
            answer=generate(prompt,response_schema)
            answer["interpretations"][0]["text"]+=" This is the predicted extinction time for the requested case."
            return answer
        client.generate.side_effect=invalid
        result=answer_question(methanol(1.65),archive=self.archive,client=client)
        self.assertEqual(result["interpretation_status"],"REJECTED")
        self.assertTrue(result["related_results"])

    def test_requested_condition_can_be_discussed_without_becoming_a_measurement(self):
        client=cited_client();generate=client.generate.side_effect
        def explain(prompt,response_schema):
            answer=generate(prompt,response_schema)
            answer["interpretations"][0]["text"]="For the requested 1.65mm droplet no estimate is available. "+answer["interpretations"][0]["text"]
            return answer
        client.generate.side_effect=explain
        result=answer_question(methanol(1.65),archive=self.archive,client=client)
        self.assertEqual(result["interpretation_status"],"SUCCEEDED")
        self.assertFalse(result["prediction_results"])

    def test_bad_api_preserves_real_local_prediction(self):
        client=Mock();client.model_name="offline";client.api_key=None;client.generate.side_effect=RuntimeError("offline")
        result=answer_question(methanol(),archive=self.archive,client=client)
        self.assertEqual(result["prediction_status"],"RESEARCH_ONLY")
        self.assertEqual(result["interpretation_status"],"UNAVAILABLE")
        self.assertTrue(result["prediction_results"])
        self.assertIn("Research-only",result["answer"])

    def test_input_conflicts_stop_before_external_or_local_analysis(self):
        for request in (methanol(16.5,question_diameter=1.65),methanol(pillar="PREVENTION")):
            client=cited_client()
            result=answer_question(request,archive=self.archive,client=client)
            self.assertEqual(result["route"],"INVALID_INPUT")
            self.assertTrue(result["validation_issues"])
            client.generate.assert_not_called()
            self.assertFalse(result["prediction_results"])
        self.assertEqual(methanol(16.5,question_diameter=1.65).parameters["diameter_mm"].value,16.5)
        request=methanol().model_copy(update={"question":"Estimate extinction time for a 2.5 mm droplet under 30% oxygen."})
        self.assertTrue(any(i["field"]=="o2_initial_pct" for i in input_issues(request)))

    def test_outside_domain_does_not_extrapolate_but_gemini_explains_sources(self):
        result=answer_question(methanol(16.5),archive=self.archive,client=cited_client())
        self.assertFalse(result["prediction_results"])
        self.assertEqual(result["interpretation_status"],"SUCCEEDED")
        self.assertTrue(any("diameter_mm" in reason for d in result["model_diagnostics"] for reason in d["reasons"]))

    def test_related_records_are_sorted_and_natural_extinction_only(self):
        query=methanol()
        rows=[r for r in self.archive["rows"] if r["parameter"]=="extinguishing_time_s" and r["material"]=="Methanol"]
        selected=compatible_related(query,list(reversed(rows)))
        self.assertEqual([r["id"] for r in selected],[r["id"] for r in compatible_related(query,rows)])
        self.assertEqual([r["retrieval_distance"] for r in selected],sorted(r["retrieval_distance"] for r in selected))
        self.assertTrue(all(r["subtype"]=="RADIATIVE_DIFFUSIVE_DROPLET_EXTINCTION_TIME" for r in selected))
        self.assertTrue(all(not r.get("data_quality_issues") for r in selected))

    def test_zero_pressure_is_quarantined_and_frozen_benchmarks_preserved(self):
        baseline=read_json(BASE_DIR/"docs/RETRAINING_V2_BASELINE.json")
        for task_id in ("flex_methanol_extinction_time","flex_methanol_burning_rate"):
            root=BASE_DIR/"models"/task_id
            pointer=read_json(root/"latest_research.json")
            folder=root/"versions"/pointer["version_id"]
            snapshot=read_json(folder/"dataset_snapshot.json")
            self.assertFalse(any(s["uid"]=="PSI-69:FLEX-114" for s in snapshot["samples"]))
            self.assertTrue(any(s.get("uid")=="PSI-69:FLEX-114" and s["reason"]=="nonpositive_source_pressure_quarantined" for s in snapshot["exclusions"]))
            metadata=read_json(folder/"metadata.json")
            self.assertEqual(metadata["benchmark_sha256"],baseline[task_id]["benchmark_sha256"])
            self.assertEqual(read_json(folder/"split_manifest.json")["frozen"],baseline[task_id]["frozen"])
            self.assertEqual(metadata["calibration_plan"]["version"],2)
            self.assertEqual(metadata["calibration_plan"]["required_calibration_groups"],9)
            self.assertGreater(metadata["calibration_plan"]["additional_independent_groups_needed"],0)
            self.assertIsNone(metadata["uncertainty"]["half_width"])

    def test_new_groups_are_reserved_without_reusing_existing_development(self):
        task=read_json(BASE_DIR/"ml/tasks.json")["flex_methanol_extinction_time"]
        root=BASE_DIR/"models/flex_methanol_extinction_time"
        version=read_json(root/"latest_research.json")["version_id"]
        snapshot=read_json(root/"versions"/version/"dataset_snapshot.json")
        manifest=read_json(root/"split_manifest.json")
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);(path/"split_manifest.json").write_text(json.dumps(manifest))
            new=copy.deepcopy(snapshot["samples"][0]);new.update(uid="new-prospective",group="new-group",tokens=["unseen-specimen","unseen-session"],observation_sha256="new-observation")
            snapshot["samples"].append(new)
            assigned,_,updated=assign_roles(snapshot,path,task)
            self.assertEqual(next(s["role"] for s in assigned if s["uid"]==new["uid"]),"calibration")
            for token,role in manifest["tokens"].items():self.assertEqual(updated["tokens"][token],role)
            roles={s["group"]:s["role"] for s in assigned}
            self.assertEqual(len(roles),len({s["group"] for s in assigned}))


class WorkflowUITests(unittest.TestCase):
    def test_real_model_and_interpretation_render_and_invalid_input_is_blocked(self):
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest
        generate=cited_client().generate.side_effect
        with patch("ui.intelligence_workspace.AssessmentCache",return_value={}),patch("si.gemini_client.GeminiClient.generate",side_effect=generate):
            app=AppTest.from_file(str(BASE_DIR/"app.py"),default_timeout=90).run()
            query=methanol()
            app.session_state.si_pillar="SUPPRESSION"
            app.session_state.si_question_SUPPRESSION=query.question
            app.session_state.si_materials=["Methanol"]
            for key,p in query.parameters.items():
                app.session_state["si_state_"+key]="SPECIFIED"
                app.session_state["si_value_"+key]=p.value
            app.switch_page("app_pages/5_SI_Insights.py").run()
            self.assertFalse(app.exception)
            app.button(key="si_analyze").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state.scientific_answer["prediction_status"],"RESEARCH_ONLY")
            self.assertEqual(app.session_state.scientific_answer["interpretation_status"],"SUCCEEDED")
            self.assertTrue(any("research-only" in metric.label.lower() for metric in app.metric))
            app.number_input(key="si_value_diameter_mm").set_value(16.5).run()
            self.assertTrue(app.button(key="si_analyze").disabled)
            self.assertTrue(any("conflict" in w.value for w in app.warning))


if __name__=="__main__":unittest.main()
