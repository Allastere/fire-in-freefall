"""Session isolation, source traceability and multipage interaction regressions."""

import hashlib
import json
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from docx import Document
from google.genai import errors
from streamlit.testing.v1 import AppTest

from ingestion.file_loader import resolve_psi_folder
from config.settings import DB_PATH, RAW_DATA_DIR
from si.insights import GroundedInsight, build_prompt, select_evidence, validate_citations
from ui.data import UPLOADED, csv_sources, parse_upload

ROOT = Path(__file__).resolve().parents[1]
INV = {"psi_id": "PSI-25", "acronym": "BASS-II", "doi": "10.test/example"}


class SourceTests(unittest.TestCase):
    def test_real_csv_sources_have_record_locators_not_pages(self):
        path = resolve_psi_folder("PSI-25") / "PSI-25_Experimental table_BASS-II.csv"
        sources = csv_sources(path.read_bytes(), path.name, "PSI-25")
        self.assertEqual(len(sources), 129)
        self.assertEqual(sources[0]["test_id"], "B1")
        self.assertIn("CSV record 1", sources[0]["locator"])
        self.assertNotIn("page", sources[0]["locator"])

    def test_upload_preserves_raw_fields_and_does_not_invent_conditions(self):
        data = b'Test ID,Material,O2_pct,Air display,Final CO (ppm),Other\nT1,PMMA,21,"5, 2",OR,original\n'
        parsed = parse_upload(data, "example.csv", INV)
        run = parsed["runs"].iloc[0]
        self.assertEqual(run.data_origin, UPLOADED)
        self.assertEqual(run.gravity_level, "Unknown")
        self.assertIsNone(run.pressure_psi)
        self.assertEqual(run.flow_velocity_min_cm_s, 2)
        self.assertEqual(json.loads(run.raw_attributes_json)["Other"], "original")
        self.assertTrue(parsed["measurements"].iloc[0].is_over_range)
        self.assertEqual(parsed["measurements"].iloc[0].verification_status, "needs_review")
        other = parse_upload(data.replace(b'T1', b'T2'), "example.csv", INV)
        self.assertNotEqual(parsed["sources"][0]["source_id"], other["sources"][0]["source_id"])

    def test_upload_pressure_units_and_invalid_values(self):
        result = parse_upload(b'Test ID,P_atm,O2_pct\nT1,1,21\n', "p.csv", INV)
        self.assertAlmostEqual(result["runs"].iloc[0].pressure_psi, 14.696, places=2)
        for value in ("101", "-2", "inf"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_upload(f'Test ID,O2_pct\nT1,{value}\n'.encode(), "bad.csv", INV)

    def test_docx_upload_extracts_paragraphs_and_table_text(self):
        doc = Document()
        doc.add_paragraph("Test evidence from a session document.")
        doc.add_table(rows=1, cols=1).cell(0, 0).text = "Sensor table evidence"
        buffer = BytesIO()
        doc.save(buffer)
        parsed = parse_upload(buffer.getvalue(), "method.docx", INV)
        self.assertIn("Sensor table evidence", parsed["sources"][0]["text"])
        self.assertIn("page unknown", parsed["sources"][0]["locator"])

    def test_citation_validation_rejects_invented_sources_and_quotes(self):
        source = {"source_id": "S1", "text": "Original measured oxygen was 21 percent.", "test_id": "T1"}
        answer = GroundedInsight.model_validate({"observations": [
            {"text": "The source records oxygen.", "citations": [
                {"source_id": "S1", "quote": "measured oxygen was 21 percent"}]}],
            "interpretations": [], "limitations": ["Single observation."]})
        self.assertIs(validate_citations(answer, [source]), answer)
        answer.observations[0].citations[0].source_id = "invented"
        with self.assertRaises(ValueError):
            validate_citations(answer, [source])
        answer.observations[0].citations[0].source_id = "S1"
        answer.observations[0].citations[0].quote = "fabricated supporting quotation"
        with self.assertRaises(ValueError):
            validate_citations(answer, [source])
        self.assertEqual(select_evidence([source], "oxygen", ["other"]), [])
        with self.assertRaises(ValueError):
            build_prompt("question", {}, [])


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.db_hash = hashlib.sha256(DB_PATH.read_bytes()).digest()
        self.app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()

    def tearDown(self):
        self.assertEqual(hashlib.sha256(DB_PATH.read_bytes()).digest(), self.db_hash)

    def assert_healthy(self):
        self.assertFalse(self.app.exception, str(self.app.exception))
        self.assertFalse(self.app.error, str(self.app.error))

    def test_four_pages_filters_integrated_comparison_and_ranking(self):
        self.assert_healthy()
        for page in ["2_Explorer", "4_Ranking", "5_SI_Insights"]:
            self.app.switch_page(f"app_pages/{page}.py").run()
            self.assert_healthy()
        self.app.segmented_control(key="compare_mode").set_value("Sensor measurements").run()
        self.assert_healthy()
        self.app.switch_page("app_pages/2_Explorer.py").run()
        self.app.segmented_control(key="explorer_view").set_value("Table").run()
        self.app.multiselect(key="explorer_materials").set_value(["PMMA"]).run()
        self.assertTrue((self.app.dataframe[0].value["Material"] == "PMMA").all())
        self.app.text_input(key="explorer_search").set_value("no-such-run").run()
        self.assertTrue(any("No runs match" in x.value for x in self.app.info))
        self.app.switch_page("app_pages/4_Ranking.py").run()
        for mission in ["ISS", "Mars Habitat", "Earth Spin-off", "Lunar Base"]:
            self.app.selectbox(key="mission").set_value(mission).run()
            self.assert_healthy()
        for page in ["2_Explorer", "4_Ranking", "5_SI_Insights"]:
            self.app.switch_page(f"app_pages/{page}.py").run()
            self.app.selectbox(key="safety_pillar").set_value("Detection").run()
            self.app.selectbox(key="facility").set_value("Saffire/Cygnus").run()
            self.assert_healthy()

    def test_uploads_stay_in_session_and_can_be_cleared(self):
        self.app.switch_page("app_pages/2_Explorer.py").run()
        self.app.selectbox(key="upload_psi").set_value("PSI-25").run()
        self.app.file_uploader(key="source_uploads").upload(
            "session.csv", b'Test ID,Material,O2_pct,Air display\nSESSION-T1,PMMA,21,5\n').run()
        self.app.button(key="add_uploads").click().run()
        self.assert_healthy()
        self.assertEqual(len(self.app.session_state.uploads), 1)
        self.assertTrue(any("SESSION-T1" in str(df.value) for df in self.app.dataframe))
        self.app.switch_page("app_pages/5_SI_Insights.py").run()
        self.assertTrue(any("SESSION-T1" in option for option in self.app.multiselect(key="compare_runs").options))
        self.app.switch_page("app_pages/2_Explorer.py").run()
        self.app.button(key="clear_uploads").click().run()
        self.assertEqual(self.app.session_state.uploads, {})

    def test_grounded_analysis_reuses_session_cache_and_rejects_bad_citations(self):
        def generate(client, prompt, schema):
            evidence = json.loads(prompt.split("\n", 1)[1])["evidence"]
            return GroundedInsight.model_validate({"observations": [
                {"text": "The selected source provides experimental values.", "citations": [
                    {"source_id": evidence[0]["source_id"], "quote": evidence[0]["text"][:60]}]}],
                "interpretations": [], "limitations": ["Partial gravity was not measured in these rows."]})
        self.app.switch_page("app_pages/5_SI_Insights.py").run()
        self.app.radio(key="editorial_research_tool").set_value("Document research").run()
        with patch("si.gemini_client.GeminiClient.generate", autospec=True, side_effect=generate) as api:
            self.app.button(key="analyze_evidence").click().run()
            self.assert_healthy()
            self.assertIsNotNone(self.app.session_state.insight_result)
            self.app.button(key="analyze_evidence").click().run()
            self.assertEqual(api.call_count, 1)
            self.assertTrue(self.app.session_state.insight_result["session_hit"])
        bad_answer = GroundedInsight.model_validate({"observations": [{"text": "Unsupported claim",
            "citations": [{"source_id": "invented-source", "quote": "Invented supporting quotation"}]}],
            "interpretations": [], "limitations": []})
        with patch("si.gemini_client.GeminiClient.generate", return_value=bad_answer):
            self.app.text_area(key="insight_question").set_value("Another question about PMMA evidence").run()
            self.app.button(key="analyze_evidence").click().run()
            self.assertIsNone(self.app.session_state.insight_result)
            self.assertTrue(any("No validated answer" in x.value for x in self.app.warning))
        with patch("si.gemini_client.GeminiClient.generate", side_effect=RuntimeError("missing key")):
            self.app.text_area(key="insight_question").set_value("A different question about PMMA").run()
            self.app.button(key="analyze_evidence").click().run()
            self.assertIsNone(self.app.session_state.insight_result)
            self.assertTrue(any("API key" in x.value for x in self.app.info))

    def test_api_error_details_are_visible_without_exposing_key(self):
        self.app.switch_page("app_pages/5_SI_Insights.py").run()
        self.app.radio(key="editorial_research_tool").set_value("Document research").run()
        self.app.text_input(key="user_api_key").set_value("private-test-key").run()
        error = errors.ClientError(400, {"error": {"message": "Invalid schema; key=private-test-key",
                                                   "status": "INVALID_ARGUMENT"}})
        with patch("si.gemini_client.GeminiClient.generate", side_effect=error):
            self.app.button(key="analyze_evidence").click().run()
        self.assert_healthy()
        self.assertTrue(any("API status 400" in x.value for x in self.app.warning))
        details = " ".join(x.value for x in self.app.text)
        self.assertIn("Invalid schema", details)
        self.assertNotIn("private-test-key", details)
        self.assertIn("[REDACTED]", details)

    def test_unified_material_modes_optional_inputs_and_stale_results(self):
        self.app.switch_page("app_pages/5_SI_Insights.py").run()
        for mode in ["Find Materials", "Compare Materials", "Predict Parameter", "Assess Material"]:
            self.app.segmented_control(key="editorial_mode").set_value(mode).run()
            self.assert_healthy()
        self.app.selectbox(key="editorial_state_o2_initial_pct").set_value("Specified").run()
        self.app.number_input(key="editorial_value_o2_initial_pct").set_value(21).run()
        self.app.selectbox(key="editorial_state_gravity_g").set_value("Specified").run()
        self.app.number_input(key="editorial_value_gravity_g").set_value(0).run()
        self.app.button(key="editorial_assessment_submit").click().run()
        self.assert_healthy()
        self.assertIsNotNone(self.app.session_state.material_result)
        self.app.number_input(key="editorial_value_gravity_g").set_value(.166).run()
        self.assertTrue(any("Conditions have changed" in x.value for x in self.app.caption))
        self.app.button(key="editorial_assessment_submit").click().run()
        self.assert_healthy()
        report=self.app.session_state.material_result["reports"][0]
        self.assertTrue(all(c["status"] == "UNAVAILABLE" for c in report["characteristics"]))

    def test_find_and_compare_materials_produce_reports_without_safety_scores(self):
        self.app.switch_page("app_pages/5_SI_Insights.py").run()
        self.app.segmented_control(key="editorial_mode").set_value("Find Materials").run()
        self.app.button(key="editorial_assessment_submit").click().run()
        self.assert_healthy()
        self.assertTrue(self.app.session_state.material_result["reports"])
        self.app.segmented_control(key="editorial_mode").set_value("Compare Materials").run()
        self.app.multiselect(key="editorial_materials").set_value(["PMMA", "SIBAL"]).run()
        self.app.button(key="editorial_assessment_submit").click().run()
        self.assert_healthy()
        result = self.app.session_state.material_result
        self.assertEqual(len(result["reports"]), 2)
        self.assertTrue(result["comparison"])
        self.assertNotIn("safety_score", result)

    def test_b1_record_lookup_preserves_conditions_without_pressure_permission(self):
        self.app.switch_page("app_pages/5_SI_Insights.py").run()
        self.app.selectbox(key="editorial_reference").set_value("PSI-25:B1").run()
        self.app.button(key="editorial_record_load").click().run()
        for field, value in {"o2_initial_pct":22.2, "pressure_psi":14.7, "gravity_g":0, "thickness_mm":.1}.items():
            self.assertEqual(self.app.number_input(key=f"editorial_value_{field}").value,value)
        self.app.selectbox(key="editorial_mission").set_value("Earth Spin-off").run()
        self.assertEqual(self.app.number_input(key="editorial_value_gravity_g").value,0)
        self.app.button(key="editorial_assessment_submit").click().run()
        self.assert_healthy()
        chars=self.app.session_state.material_result["reports"][0]["characteristics"]
        c=next(c for c in chars if c["parameter"]=="co2_final_pct")
        self.assertEqual((c["status"],c["value"]),("OBSERVED",.44))
        self.app.button(key="editorial_mission_apply").click().run()
        self.app.button(key="editorial_assessment_submit").click().run()
        self.assert_healthy()
        chars=self.app.session_state.material_result["reports"][0]["characteristics"]
        self.assertTrue(all(c["status"]=="UNAVAILABLE" for c in chars))

    def test_filters_survive_page_changes_and_send_to_compare_works(self):
        self.app.switch_page("app_pages/2_Explorer.py").run()
        self.app.multiselect(key="explorer_materials").set_value(["PMMA"]).run()
        self.app.text_input(key="explorer_search").set_value("M1").run()
        self.app.button(key="explorer_send").click().run()
        self.assert_healthy()
        selected = self.app.multiselect(key="compare_runs").value
        self.assertTrue(selected and all("M1" in test for test in selected))
        self.app.switch_page("app_pages/2_Explorer.py").run()
        self.assertEqual(self.app.text_input(key="explorer_search").value, "M1")
        self.assertEqual(self.app.multiselect(key="explorer_materials").value, ["PMMA"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
