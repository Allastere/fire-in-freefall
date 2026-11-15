"""Question routing, provenance, cache invalidation and three-pillar scientific regressions."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scientific.archive import load_archive
from scientific.intelligence import ScientificRequest, answer_question, cache_key, grouped_results, rank_research
from scientific.materials import Parameter
from ui.intelligence_workspace import build_figure
from ml.dataset import extract_dataset,read_json
from ml.registry import assign_roles
from config.settings import DB_PATH,RAW_DATA_DIR


class IntelligenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=load_archive()

    def request(self,pillar="DETECTION",**kwargs):
        return ScientificRequest(pillar=pillar,question="What smoke particle sizes are reported?",**kwargs)

    def test_structured_citations_allow_formatting_but_not_changed_evidence(self):
        from si.insights import GroundedInsight,validate_citations,citation_excerpts
        text='{"original": {"Final CO2 % by vol": "0.44"}, "reported_measurement": {"value": 0.44, "unit": "%"}}'
        evidence=[{"source_id":"source","text":text}]
        def answer(quote):
            return GroundedInsight.model_validate({"observations":[{"text":"Recorded carbon dioxide concentration.",
                "citations":[{"source_id":"source","quote":quote}]}],"interpretations":[],"limitations":[]})
        for quote in ('{"unit":"%","value":0.44}', '"value":0.44, "unit":"%"'):
            result=validate_citations(answer(quote),evidence)
            self.assertIn(result.observations[0].citations[0].quote,text)
        for quote in ('{"value":0.45,"unit":"%"}', '{"value":0.44,"unit":"ppm"}',
                      '{"Final CO2 % by vol":0.44}', 'A fabricated scientific quotation.'):
            with self.assertRaises(ValueError):validate_citations(answer(quote),evidence)
        self.assertTrue(citation_excerpts(text))
        self.assertTrue(all(q in text for q in citation_excerpts(text)))

    def test_three_tasks_and_physical_input_states(self):
        for pillar in ("PREVENTION","DETECTION","SUPPRESSION"):
            with self.subTest(pillar=pillar):
                result=answer_question(self.request(pillar),archive=self.archive)
                self.assertTrue(result["answer"])
                self.assertTrue(result["ranking"])
        unknown=Parameter(state="unknown")
        self.assertIsNone(unknown.value)
        self.assertNotEqual(unknown,Parameter(state="specified",value=0))
        with self.assertRaises(ValueError):Parameter(state="specified",value=None)

    def test_observed_b1_and_changed_environment(self):
        query=ScientificRequest(pillar="PREVENTION",question="What final CO2 was recorded?",materials=["PMMA"],reference_uid="PSI-25:B1")
        result=answer_question(query,archive=self.archive)
        self.assertEqual(result["route"],"OBSERVED")
        co2=next(r for r in result["results"] if r["parameter"]=="co2_final_pct")
        self.assertEqual(co2["values"],[.44])
        unsupported=query.model_copy(update={"parameters":{"gravity_g":Parameter(state="specified",value=.166)}})
        result=answer_question(unsupported,archive=self.archive)
        self.assertEqual(result["route"],"INSUFFICIENT_DATA")
        self.assertTrue(result["related"])

    def test_any_unknown_zero_and_ranges_do_not_impute(self):
        zero=self.request("SUPPRESSION",parameters={"flow_velocity_initial_cm_s":Parameter(state="specified",value=0)})
        result=answer_question(zero,archive=self.archive)
        self.assertTrue(result["results"])
        for state in ("any","unknown"):
            result=answer_question(self.request(parameters={"gravity_g":Parameter(state=state)}),archive=self.archive)
            self.assertTrue(result["results"])
        result=answer_question(self.request(parameters={"gravity_g":Parameter(state="range",lower=.1,upper=.4)}),archive=self.archive)
        self.assertEqual(result["route"],"INSUFFICIENT_DATA")

    def test_cache_hit_invalidation_models_data_question_and_states(self):
        with tempfile.TemporaryDirectory() as temp:
            models=Path(temp);cache={};query=self.request()
            first=answer_question(query,archive=self.archive,models_dir=models,cache=cache)
            with patch("scientific.intelligence.rank_research",side_effect=AssertionError("cache missed")):
                hit=answer_question(query,archive=self.archive,models_dir=models,cache=cache)
            self.assertEqual(hit["route"],"CACHED")
            self.assertEqual(first["results"],hit["results"])
            original=cache_key(query,self.archive,models,"gemini")
            self.assertEqual(original,cache_key(self.request(parameters={"gravity_g":Parameter(state="any")}),self.archive,models,"gemini"))
            changed={**self.archive,"fingerprint":"changed"}
            self.assertNotEqual(original,cache_key(query,changed,models,"gemini"))
            (models/"new_task").mkdir();(models/"new_task"/"latest_research.json").write_text('{"version_id":"new"}')
            self.assertNotEqual(original,cache_key(query,self.archive,models,"gemini"))
            self.assertNotEqual(cache_key(self.request(parameters={"gravity_g":Parameter(state="any")}),self.archive,models,"g"),
                cache_key(self.request(parameters={"gravity_g":Parameter(state="unknown")}),self.archive,models,"g"))

    def test_api_failure_and_invalid_quotes_are_not_success_cached(self):
        for response in (RuntimeError("offline"),{"observations":[{"text":"Made up fact","citations":[{"source_id":"fake","quote":"not an original quotation"}]}],"interpretations":[],"limitations":[]}):
            client=Mock();client.model_name="test"
            if isinstance(response,Exception):client.generate.side_effect=response
            else:client.generate.return_value=response
            cache={};result=answer_question(self.request(materials=["Kapton"]),archive=self.archive,cache=cache,client=client)
            self.assertEqual(result["route"],"OBSERVED")
            self.assertTrue(any(word in result["synthesis_status"] for word in ("unavailable","rejected")))
            self.assertFalse(cache)

    def test_diameter_statistics_dust_and_censoring_remain_distinct(self):
        rows=[r for r in self.archive["rows"] if r["parameter"]=="smoke_particle_diameter_nm" and r["verified"]]
        groups=grouped_results(rows)
        self.assertGreater(len({g["subtype"] for g in groups}),3)
        self.assertTrue(all(len({r["statistic_type"] for r in rows if r["source"]["source_id"] in g["evidence_ids"]})==1 for g in groups))
        dust=[g for g in groups if "DUST" in str(g["subtype"])]
        self.assertTrue(dust)
        self.assertTrue(all(g["material"]!="Kapton" for g in dust))

    def test_ranking_and_chart_are_source_traceable(self):
        request=self.request(materials=["Kapton"])
        ranked=rank_research(request,self.archive)
        self.assertIn(ranked[0]["psi_id"],("PSI-101","PSI-102"))
        result=answer_question(request,archive=self.archive)
        chart=build_figure(result)
        self.assertIsNotNone(chart)
        self.assertIn("nm",chart.layout.yaxis.title.text)
        self.assertTrue(all(t.type=="box" and t.boxpoints=="all" for t in chart.data))

    def test_flex_initial_features_and_grouped_split(self):
        task=read_json(Path("ml/tasks.json"))["flex_methanol_extinction_time"]
        snapshot=extract_dataset(DB_PATH,RAW_DATA_DIR,task,[])
        self.assertGreater(len(snapshot["samples"]),40)
        self.assertNotIn("extinguishing_time_s",task["numeric_features"])
        with tempfile.TemporaryDirectory() as temp:
            assigned,quarantine,_=assign_roles(snapshot,Path(temp),task)
            self.assertFalse(quarantine)
            roles={role:{s["group"] for s in assigned if s["role"]==role} for role in ("development","calibration","benchmark")}
            self.assertFalse(roles["development"]&roles["benchmark"])
            self.assertFalse(roles["development"]&roles["calibration"])

    def test_question_material_scope_is_resolved_from_archive(self):
        result=answer_question(ScientificRequest(pillar="DETECTION",question="What particle sizes are reported for Kapton?"),archive=self.archive)
        self.assertEqual(result["interpreted_materials"],["Kapton"])
        self.assertTrue(all(r["material"]=="Kapton" for r in result["results"]))

    def test_specialized_model_selection_missing_features_and_intervals(self):
        task=read_json(Path("ml/tasks.json"))["flex_methanol_extinction_time"]
        supplied={"o2_initial_pct":21.,"pressure_psi":1.,"diameter_mm":2.,"gravity_g":0.,
            "flow_velocity_initial_cm_s":0.,"co2_diluent_pct":0.,"he_diluent_pct":0.,"n2_diluent_pct":79.,
            "geometry":"Droplet","fuel_phase":"Liquid"}
        query=ScientificRequest(pillar="SUPPRESSION",question="What is the extinction time?",materials=["Methanol"],
            parameters={k:Parameter(state="specified",value=v) for k,v in supplied.items()})
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);version="a"*64;d=root/"specialized"/"versions"/version;d.mkdir(parents=True)
            (d/"metadata.json").write_text(json.dumps({"task":task}))
            (root/"specialized"/"approved.json").write_text(json.dumps({"version_id":version}))
            predicted={"status":"PREDICTED","value":3.,"unit":"s","interval":[2.,4.],"model_version":version,"reasons":[]}
            with patch("ml.predict.assess",return_value=predicted) as model:
                result=answer_question(query,archive=self.archive,models_dir=root)
                self.assertEqual(result["route"],"ESTIMATED")
                self.assertEqual(result["results"][0]["status"],"ML_PREDICTED")
                self.assertEqual(model.call_args.args[0],"specialized")
                self.assertEqual(build_figure(result).data[0].error_y.array[0],1.)
            missing=query.model_copy(update={"parameters":{k:v for k,v in query.parameters.items() if k!="diameter_mm"}})
            with patch("ml.predict.assess") as model:
                result=answer_question(missing,archive=self.archive,models_dir=root)
                model.assert_not_called()
                self.assertEqual(result["route"],"INSUFFICIENT_DATA")

    def test_persistent_assessment_cache_uses_existing_sqlite_safely(self):
        import sqlite3
        from contextlib import closing
        from scientific.cache import AssessmentCache
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/"cache.db"
            with closing(sqlite3.connect(db)) as c, c:
                c.execute("CREATE TABLE llm_cache(prompt_hash TEXT PRIMARY KEY,model_name TEXT,response_json TEXT,created_at TEXT)")
            cache=AssessmentCache(db)
            value={"route":"OBSERVED","origin_route":"OBSERVED","answer":"Recorded evidence","results":[]}
            cache["one"]=value
            restored=AssessmentCache(db)
            self.assertIn("one",restored)
            self.assertEqual(restored["one"],value)

    def test_valid_gemini_is_cached_but_numeric_interpretation_is_rejected(self):
        query=self.request(materials=["Kapton"])
        fixed=answer_question(query,archive=self.archive)
        source=fixed["evidence"][0]
        claim={"text":"The archive reports measured smoke particle sizes.","citations":[{"source_id":source["source_id"],"quote":source["text"][:70]}]}
        client=Mock();client.model_name="offline-test"
        client.generate.return_value={"observations":[claim],"interpretations":[],"limitations":[]}
        cache={}
        result=answer_question(query,archive=self.archive,client=client,cache=cache)
        self.assertIsNotNone(result["interpretation"])
        self.assertEqual(answer_question(query,archive=self.archive,client=client,cache=cache)["route"],"CACHED")
        self.assertEqual(client.generate.call_count,1)
        client.generate.return_value={"observations":[claim],"interpretations":[{**claim,"text":"The detector efficiency is 99%."}],"limitations":[]}
        result=answer_question(query,archive=self.archive,client=client,cache={})
        self.assertIsNone(result["interpretation"])
        self.assertEqual(result["results"],fixed["results"])

    def test_gemini_can_repeat_verified_b1_quantity_and_reports_api_errors(self):
        from google.genai import errors
        query=ScientificRequest(pillar="PREVENTION",question="What final CO2 was recorded?",materials=["PMMA"],reference_uid="PSI-25:B1")
        fixed=answer_question(query,archive=self.archive)
        source=fixed["evidence"][0]
        client=Mock();client.model_name="offline-test";client.api_key="private-test-key"
        client.generate.return_value={"observations":[{"text":"PSI-25 test B1 recorded final CO2 of 0.44 percent.",
            "citations":[{"source_id":source["source_id"],"quote":source["text"][:70]}]}],"interpretations":[],"limitations":[]}
        result=answer_question(query,archive=self.archive,client=client)
        self.assertIsNotNone(result["interpretation"])
        self.assertIn("0.44",result["answer"])
        client.generate.side_effect=errors.ClientError(400,{"error":{"message":"Invalid request private-test-key"}})
        result=answer_question(query,archive=self.archive,client=client,cache={})
        self.assertIn("API status 400",result["synthesis_status"])
        self.assertNotIn("private-test-key",result["synthesis_error"])
        self.assertIn("[REDACTED]",result["synthesis_error"])


if __name__=="__main__":unittest.main()
