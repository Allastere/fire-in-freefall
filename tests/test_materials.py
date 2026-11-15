"""Partial-condition, archive-retrieval and multi-characteristic scientific regressions."""

import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from config.settings import BASE_DIR, DB_PATH, RAW_DATA_DIR
from scientific.evidence import load_evidence
from scientific.materials import (Characteristic, MaterialQuery, MaterialReport, Parameter, assess_materials,
                                 compare_reports, discover_targets, strict_request)
from scientific.schemas import AssessmentRequest
from scientific.synthesis import ScientificSynthesis, synthesize
import test_assessment as prediction_fixtures


class MaterialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pool = {target: load_evidence(DB_PATH, RAW_DATA_DIR, target)[0] for target in discover_targets()}
        cls.b1 = next(o for o in cls.pool["co2_final_pct"] if o["uid"] == "PSI-25:B1")
        cls.m1 = next(o for o in cls.pool["co2_final_pct"] if o["uid"] == "PSI-25:M1")
        cls.db_hash = hashlib.sha256(DB_PATH.read_bytes()).hexdigest()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.models = Path(self.temp.name)

    def tearDown(self):
        self.assertEqual(self.db_hash, hashlib.sha256(DB_PATH.read_bytes()).hexdigest())

    def route(self, query, pool=None, models=None):
        pool = pool or self.pool
        with patch("scientific.materials.load_evidence", side_effect=lambda db, root, target: (pool.get(target, []), [])):
            return assess_materials(query, models_dir=models or self.models)

    def characteristic(self, result, target="co2_final_pct"):
        return next(c for c in result.reports[0].characteristics if c.parameter == target)

    def test_real_b1_lookup_without_nominal_pressure_permission(self):
        result = assess_materials(MaterialQuery(materials=["PMMA"], mode="Predict Parameter", target="co2_final_pct", reference_uid="PSI-25:B1"))
        characteristic = self.characteristic(result)
        self.assertEqual((characteristic.status, characteristic.value), ("OBSERVED", .44))
        self.assertTrue(characteristic.evidence[0]["source"]["locator"].startswith("CSV record"))
        self.assertTrue(any("nominal" in s.lower() for s in characteristic.limitations))

    def test_other_record_and_modified_conditions(self):
        query = MaterialQuery(materials=["PMMA"], reference_uid="PSI-25:M1")
        self.assertEqual(self.characteristic(self.route(query)).value, .61)
        changed = query.model_copy(update={"parameters": {"gravity_g": Parameter(state="specified", value=.166)}})
        result = self.route(changed)
        self.assertEqual(self.characteristic(result).status, "UNAVAILABLE")
        self.assertIsNone(self.characteristic(result).value)
        self.assertTrue(result.sources)

    def test_unrestricted_numeric_categorical_and_unknown_are_explicit(self):
        query = MaterialQuery(materials=["PMMA"], parameters={
            "o2_initial_pct": Parameter(state="specified", value=21), "gravity_g": Parameter(state="specified", value=0),
            "flow_velocity_initial_cm_s": Parameter(state="any"), "geometry": Parameter(state="any"),
            "thickness_mm": Parameter(state="unknown")})
        result = self.route(query)
        characteristic = self.characteristic(result)
        self.assertEqual(characteristic.status, "OBSERVED")
        self.assertIn("Conditional", characteristic.relation)
        self.assertIsNone(characteristic.value)
        self.assertGreater(len(characteristic.evidence), 1)
        self.assertTrue(all(o["conditions"]["o2_initial_pct"] == 21 for o in characteristic.evidence))
        self.assertNotEqual(result.query.parameters["geometry"].state, result.query.parameters["thickness_mm"].state)
        self.assertGreater(len(characteristic.groups), 1)

    def test_explicit_zero_and_invalid_unknown_substitution(self):
        p = Parameter(state="specified", value=0)
        self.assertEqual(p.value, 0)
        self.assertIsNone(Parameter(state="unknown").value)
        with self.assertRaises(ValueError):
            Parameter(state="unknown", value=0)
        with self.assertRaises(ValueError):
            MaterialQuery(parameters={"thickness_mm": p})
        self.assertEqual(MaterialQuery(parameters={"gravity_g": p}).parameters["gravity_g"].value, 0)

    def test_range_retrieval_does_not_impute_a_midpoint(self):
        query = MaterialQuery(materials=["PMMA"], parameters={"o2_initial_pct": Parameter(state="range", lower=20, upper=21.5)})
        request, missing = strict_request(query, "PMMA", "co2_final_pct")
        self.assertIsNone(request)
        self.assertIn("o2_initial_pct", missing)
        characteristic = self.characteristic(self.route(query))
        self.assertTrue(all(20 <= o["conditions"]["o2_initial_pct"] <= 21.5 for o in characteristic.evidence))
        with self.assertRaises(ValueError):
            Parameter(state="range", lower=22, upper=20)

    def test_observed_and_unavailable_characteristics_do_not_override_each_other(self):
        result = self.route(MaterialQuery(materials=["PMMA"], reference_uid="PSI-25:B1"))
        self.assertEqual(self.characteristic(result).status, "OBSERVED")
        self.assertEqual(self.characteristic(result, "flame_spread_rate_mm_s").status, "UNAVAILABLE")
        self.assertIn("Recorded combustion evidence", result.conclusion)

    def test_all_available_characteristics_can_be_observed(self):
        targets = ["co2_final_pct", "co_final_ppm"]
        with patch("scientific.materials.discover_targets", return_value=targets):
            result = self.route(MaterialQuery(materials=["PMMA"], reference_uid="PSI-25:B1"))
        self.assertTrue(all(c.status == "OBSERVED" for c in result.reports[0].characteristics))

    def test_no_exact_evidence_keeps_related_records_and_unknown_material_is_honest(self):
        result = self.route(MaterialQuery(materials=["PMMA"], parameters={"gravity_g": Parameter(state="specified", value=.166)}))
        self.assertTrue(all(c.status == "UNAVAILABLE" for c in result.reports[0].characteristics))
        self.assertTrue(result.sources)
        self.assertIn("Related experimental records", result.conclusion)
        unknown = self.route(MaterialQuery(materials=["Nonexistent material"]))
        self.assertFalse(unknown.sources)
        self.assertTrue(all(c.status == "UNAVAILABLE" for c in unknown.reports[0].characteristics))

    def test_find_materials_has_no_evidence_quantity_or_safety_ranking(self):
        result = self.route(MaterialQuery(mode="Find Materials"))
        self.assertTrue(result.reports)
        self.assertFalse(any("score" in r.model_dump() for r in result.reports))
        self.assertNotIn("safest", result.conclusion.lower())

    def test_comparison_stratifies_physics_and_preserves_missing_measurements(self):
        evidence = [copy.deepcopy(self.b1), copy.deepcopy(self.b1)]
        reports = []
        for material, observation in zip(["Fixture A", "Fixture B"], evidence):
            from scientific.assessment import public_observation
            observation["features"]["material_name"] = material
            reports.append(MaterialReport(material=material, conclusion="Fixture only", characteristics=[
                Characteristic(parameter="co2_final_pct", display_name="Final carbon dioxide", status="OBSERVED",
                               unit="%", evidence=[public_observation(observation)])]))
        self.assertTrue(compare_reports(reports)[0]["comparable"])
        reports[1].characteristics[0].evidence[0]["conditions"]["gravity_g"] = 1
        self.assertFalse(compare_reports(reports)[0]["comparable"])
        reports[1].characteristics = []
        self.assertEqual(compare_reports(reports)[0]["materials"][1]["status"], "Missing measurements")

    def test_mixed_observed_predicted_uses_existing_approved_pipeline(self):
        fixture = prediction_fixtures.AssessmentTests()
        fixture.models = self.models
        fixture.query = AssessmentRequest(**self.m1["features"], target="co2_final_pct")
        fixture.fixture_model()
        parameters = {key: Parameter(state="specified", value=value) for key, value in self.m1["features"].items()
                      if key != "material_name" and value is not None}
        parameters["flow_sequence_raw"] = Parameter(state="specified", value="10")
        query = MaterialQuery(materials=["PMMA"], parameters=parameters)
        # Fixture observation of a different characteristic at the requested sequence.
        oxygen = copy.deepcopy(next(o for o in self.pool["o2_final_calibrated_pct"] if o["uid"] == "PSI-25:M1"))
        oxygen["features"]["flow_sequence_raw"] = "10"
        pool = {**self.pool, "o2_final_calibrated_pct": [oxygen]}
        with patch("scientific.materials.discover_targets", return_value=["co2_final_pct", "o2_final_calibrated_pct"]):
            result = self.route(query, pool=pool)
        self.assertEqual(self.characteristic(result).status, "PREDICTED")
        self.assertIsNotNone(self.characteristic(result).prediction_interval)
        self.assertEqual(self.characteristic(result, "o2_final_calibrated_pct").status, "OBSERVED")
        # The existing model uses initial airflow, not the raw sequence. Missing history
        # prevents exact matching but is not silently made a new ML feature requirement.
        parameters["flow_sequence_raw"] = Parameter(state="unknown")
        query = query.model_copy(update={"parameters": parameters})
        result = self.route(query, pool=pool)
        self.assertEqual(self.characteristic(result).status, "PREDICTED")

    def test_missing_model_features_and_research_model_cannot_predict(self):
        query = MaterialQuery(materials=["PMMA"], mode="Predict Parameter", target="co2_final_pct",
                              parameters={"gravity_g": Parameter(state="specified", value=.166)})
        characteristic = self.characteristic(self.route(query))
        self.assertEqual(characteristic.status, "UNAVAILABLE")
        self.assertTrue(characteristic.missing_features)
        self.assertIsNone(characteristic.prediction_interval)
        parameters = {key: Parameter(state="specified", value=value) for key, value in self.m1["features"].items()
                      if key != "material_name" and value is not None}
        parameters["o2_initial_pct"] = Parameter(state="specified", value=21.75)
        report = self.route(MaterialQuery(materials=["PMMA"], mode="Predict Parameter", target="co2_final_pct", parameters=parameters),
                            models=BASE_DIR / "models")
        characteristic = self.characteristic(report)
        self.assertEqual(characteristic.status, "UNAVAILABLE")
        self.assertEqual(characteristic.numerical_result["model_diagnostics"]["status"], "RESEARCH_ONLY")

    def test_selection_criterion_without_comparable_measurements_does_not_rank(self):
        result = self.route(MaterialQuery(mode="Find Materials", criterion="hrr_watts"))
        self.assertTrue(result.reports)
        self.assertTrue(any("no applicable verified measurements" in limitation for limitation in result.limitations))
        self.assertNotIn("winner", result.model_dump())

    def test_structured_synthesis_preserves_numbers_and_never_proposes_for_record_lookup(self):
        result = self.route(MaterialQuery(materials=["PMMA"], reference_uid="PSI-25:B1"))
        source = result.sources[0]
        claim = {"text": "Recorded evidence describes the tested specimen. Its applicability requires review.", "citations": [
            {"source_id": source["source_id"], "quote": source["text"][:60]}]}
        answer = ScientificSynthesis.model_validate(dict(primary_conclusion=claim, behaviour=[], advantages=[], concerns=[],
            alternatives=[], knowledge_gaps=[], limitations=[]))
        client = Mock()
        client.generate.return_value = answer
        after = synthesize(result, client)
        self.assertIsNotNone(after.synthesis)
        self.assertEqual(self.characteristic(after).value, .44)
        self.assertIsNone(after.synthesis["proposed_investigation"])
        client.generate.side_effect = RuntimeError("Unavailable")
        failed = synthesize(result, client)
        self.assertEqual(self.characteristic(failed).value, .44)
        self.assertIsNone(failed.synthesis)
        client.generate.side_effect = None
        answer.primary_conclusion.text = "The measured value is 99 percent."
        self.assertIsNone(synthesize(result, client).synthesis)
        answer.primary_conclusion.text = claim["text"]
        answer.primary_conclusion.citations[0].source_id = "Invented source"
        self.assertIsNone(synthesize(result, client).synthesis)

    def test_no_future_proposal_for_valid_record_and_session_cache_reuse(self):
        from scientific.interpretation import ExperimentalProposal
        result = self.route(MaterialQuery(materials=["PMMA"], reference_uid="PSI-25:B1"))
        proposal = ExperimentalProposal(objective="A proposed study", independent_variables=["Gravity"],
            controlled_variables=["Material"], required_measurements=["Gas concentrations"], suggested_techniques=["Gas analysis"],
            comparison_rationale="Compare source conditions", expected_knowledge_gain="Establish transfer limits")
        answer = ScientificSynthesis(primary_conclusion=None, behaviour=[], advantages=[], concerns=[], alternatives=[],
            knowledge_gaps=[], limitations=[], proposed_investigation=proposal)
        client = Mock()
        client._generate_hash.return_value = "fixture-cache-key"
        client.generate.return_value = answer
        cache = {}
        after = synthesize(result, client, cache)
        self.assertIsNone(after.synthesis["proposed_investigation"])
        synthesize(result, client, cache)
        client.generate.assert_called_once()


if __name__ == "__main__":
    unittest.main(verbosity=2)
