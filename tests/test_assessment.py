"""Scientific routing integration tests. Synthetic approvals exist ONLY inside temporary fixtures.

These exercise the real serialized predictor/loader without approving the production research model.
"""

import copy
import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

from config.settings import BASE_DIR, DB_PATH, RAW_DATA_DIR
from ml.dataset import read_json
from ml.registry import write_json
from ml.uncertainty import supported_domain
from scientific import AssessmentRequest, assess
from scientific.evidence import load_evidence
from scientific.interpretation import AssessmentNarrative, ExperimentalProposal, interpret


class AssessmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.observations, _ = load_evidence(DB_PATH, RAW_DATA_DIR, "co2_final_pct")
        cls.observation = next(o for o in cls.observations if o["test_id"] == "M1")
        cls.original_hash = hashlib.sha256(DB_PATH.read_bytes()).hexdigest()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.models = self.root / "models"
        self.models.mkdir()
        self.query = AssessmentRequest(**self.observation["features"], target="co2_final_pct", allow_nominal_pressure=True)

    def tearDown(self):
        self.assertEqual(hashlib.sha256(DB_PATH.read_bytes()).hexdigest(), self.original_hash)

    def route(self, query=None, observations=None):
        with patch("scientific.assessment.load_evidence", return_value=(observations if observations is not None else self.observations, [])):
            return assess(query or self.query, models_dir=self.models)

    def fixture_model(self, version="a" * 64):
        """Temporary, deliberately artificial approval/domain metadata; never touches models/ in the repo."""
        registry = self.models / "fixture_task"
        destination = registry / "versions" / version
        destination.mkdir(parents=True)
        actual_registry = BASE_DIR / "models" / "pmma_slab_co2_final"
        pointer = read_json(actual_registry / "latest_research.json")
        original = actual_registry / "versions" / pointer["version_id"]
        shutil.copy2(original / "pipeline.joblib", destination / "pipeline.joblib")
        metadata = read_json(original / "metadata.json")
        metadata.update(version_id=version, status="APPROVED", task_id="fixture_task")
        metadata["promotion"] = {"approved": True, "reasons": []}
        metadata["uncertainty"]["half_width"] = .2
        metadata["limitations"] = ["Artificial integration-test approval only."]
        features = {key: self.query.model_dump()[key] for key in metadata["features"]}
        samples = []
        for index, delta in enumerate((-.2, 0, .2)):
            sample_features = {**features, "o2_initial_pct": features["o2_initial_pct"] + delta}
            samples.append({"features": sample_features, "material": "PMMA", "group": f"fixture-{index}"})
        domain = supported_domain(samples, metadata["task"])
        domain["radius_validated"] = True
        # Query at the middle point has three neighbors within this fixture's domain.
        domain["neighbor_radius"] *= 2
        write_json(destination / "metadata.json", metadata)
        write_json(destination / "domain.json", domain)
        write_json(registry / "approved.json", {"version_id": version, "artifact_sha256": metadata["artifact_sha256"]})
        return registry

    def test_exact_experimental_match_does_not_invoke_ml(self):
        with patch("scientific.assessment.model_assessment", side_effect=AssertionError("ML must not run")):
            result = assess(self.query, models_dir=self.models)
        self.assertEqual(result.status, "OBSERVED")
        self.assertEqual(result.value, .61)
        self.assertEqual(result.unit, "%")
        self.assertIsNone(result.prediction_interval)
        self.assertIn("CSV record", result.sources[0]["locator"])

    def test_multiple_matching_observations_report_variability(self):
        other = copy.deepcopy(self.observation)
        other.update(uid="fixture:replicate", test_id="replicate", value=.9)
        result = self.route(observations=[self.observation, other])
        self.assertEqual(result.status, "OBSERVED")
        self.assertIsNone(result.value)
        self.assertEqual(result.observed_values, [.61, .9])
        self.assertEqual(result.observed_range, [.61, .9])

    def test_trained_serialized_model_predicts_only_in_approved_domain(self):
        self.fixture_model()
        # Change airflow-history metadata so no stored observation matches exactly; the approved
        # fixture's numerical feature domain still includes the query.
        result = self.route(self.query.model_copy(update={"flow_sequence_raw": "10"}))
        self.assertEqual(result.status, "PREDICTED", result.limitations)
        self.assertTrue(result.prediction_interval[0] <= result.value <= result.prediction_interval[1])
        self.assertTrue(result.model_diagnostics["artifact_loaded"])
        self.assertIsNotNone(result.validation_metrics)

    def test_reviewed_interpolation_brackets_observations_and_never_extrapolates(self):
        endpoints = [copy.deepcopy(self.observation), copy.deepcopy(self.observation)]
        for row, oxygen, value, sample in zip(endpoints, (20.0, 24.0), (.4, .8), ("one", "two")):
            row["features"]["o2_initial_pct"] = oxygen
            row.update(value=value, pressure_measured=True, sample_id=sample)
        write_json(self.models / "interpolation_policies.json", [{"status": "APPROVED", "target": "co2_final_pct",
            "unit": "%", "axis": "o2_initial_pct", "version": "fixture-policy", "scientific_review": "Fixture reviewer",
            "physical_filters": {"material_name": "PMMA", "geometry": "Thick Slab", "gravity_g": 0.0},
            "source_scope": [self.observation["psi_id"]], "max_bracket_span": 4,
            "validation": {"independent_groups": 3, "method": "Fixture independent validation"}}])
        result = self.route(observations=endpoints)
        self.assertEqual(result.status, "INTERPOLATED")
        self.assertAlmostEqual(result.value, .62)
        self.assertIsNone(result.prediction_interval)
        result = self.route(self.query.model_copy(update={"o2_initial_pct": 25.0}), endpoints)
        self.assertEqual(result.status, "INSUFFICIENT_DATA")

    def test_unsupported_material(self):
        result = self.route(self.query.model_copy(update={"material_name": "Unknown polymer"}))
        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertIsNone(result.value)

    def test_unsupported_gravity(self):
        self.fixture_model()
        result = self.route(self.query.model_copy(update={"gravity_g": .166}))
        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertIsNone(result.value)
        self.assertTrue(any("gravity" in r for r in result.domain_assessment["rejection_reasons"]))

    def test_outside_joint_domain_never_predicts(self):
        self.fixture_model()
        result = self.route(self.query.model_copy(update={"o2_initial_pct": 34.0}))
        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertIsNone(result.value)
        # Being inside each feature range still fails if local independent support is absent.
        registry = self.models / "fixture_task"
        domain_path = registry / "versions" / ("a" * 64) / "domain.json"
        domain = read_json(domain_path)
        domain["training_groups"] = ["same specimen"] * 3
        write_json(domain_path, domain)
        result = self.route(self.query.model_copy(update={"flow_sequence_raw": "10"}))
        self.assertEqual(result.status, "INSUFFICIENT_DATA")

    def test_missing_target(self):
        result = assess(self.query.model_copy(update={"target": "flame_spread_rate_mm_s"}), models_dir=self.models)
        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertIsNone(result.value)

    def test_missing_or_broken_model_preserves_observations(self):
        self.assertEqual(self.route().status, "OBSERVED")
        changed = self.query.model_copy(update={"o2_initial_pct": 21.75})
        self.assertEqual(self.route(changed).status, "INSUFFICIENT_DATA")
        registry = self.fixture_model()
        (registry / "versions" / ("a" * 64) / "pipeline.joblib").write_bytes(b"corrupt")
        self.assertEqual(self.route(changed).status, "INSUFFICIENT_DATA")
        self.assertEqual(self.route().status, "OBSERVED")

    def test_gemini_api_failure_never_changes_fixed_results(self):
        original = self.route()
        client = Mock()
        client.generate.side_effect = RuntimeError("API unavailable")
        result = interpret(self.query, original, client)
        self.assertEqual(result.value, original.value)
        self.assertEqual(result.status, "OBSERVED")
        self.assertIsNone(result.scientific_interpretation)
        self.assertIn("unchanged", result.interpretation_status)

    def test_newly_imported_investigation_is_dynamically_discovered(self):
        db, raw = self.root / "research.db", self.root / "raw"
        with closing(sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(db)) as destination:
                source.backup(destination)
        pid, test_id, name = "PSI-NEW-FIXTURE", "NEW-T1", "new.csv"
        with closing(sqlite3.connect(db)) as conn, conn:
            # Clone a complete known-compatible physical record into a newly registered investigation.
            for table, field in (("investigations", "psi_id"), ("experiments", "test_id"), ("samples", "test_id"),
                                 ("conditions", "test_id"), ("measurements", "test_id")):
                conn.row_factory = sqlite3.Row
                original_key = "PSI-25" if table == "investigations" else "M1"
                rows = conn.execute(f"SELECT * FROM {table} WHERE {field}=?", (original_key,)).fetchall()
                for original in rows:
                    record = dict(original)
                    record.pop("id", None)
                    if "psi_id" in record:
                        record["psi_id"] = pid
                    if "test_id" in record:
                        record["test_id"] = test_id
                    if table == "experiments":
                        source_row = json.loads(record["raw_attributes_json"])
                        source_row["Test #"] = test_id
                        source_row["Gravity"] = "0g"
                        source_row["Flow direction"] = "Opposed"
                        record["raw_attributes_json"] = json.dumps(source_row)
                    if table == "measurements":
                        record["source_doc"] = name
                    columns = list(record)
                    conn.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", list(record.values()))
            import pandas as pd
            content = pd.DataFrame([source_row]).to_csv(index=False).encode()
            (raw / pid).mkdir(parents=True)
            (raw / pid / name).write_bytes(content)
            # Preserve all non-CSV source metadata defaults by cloning the existing source row.
            registered = dict(conn.execute("SELECT * FROM sources WHERE file_path LIKE '%.csv' LIMIT 1").fetchone())
            registered.pop("id", None)
            registered.update(psi_id=pid, file_path=f"{pid}/{name}", sha256_hash=hashlib.sha256(content).hexdigest())
            conn.execute(f"INSERT INTO sources ({','.join(registered)}) VALUES ({','.join('?' for _ in registered)})", list(registered.values()))
        result = assess(self.query, db_path=db, raw_root=raw, models_dir=self.models)
        self.assertEqual(result.status, "OBSERVED", result.limitations)
        self.assertEqual(result.supporting_experiments[0]["psi_id"], pid)
        # Legacy importer defaults cannot establish physical compatibility for an unknown source.
        source_row.pop("Gravity")
        source_row.pop("Flow direction")
        content = pd.DataFrame([source_row]).to_csv(index=False).encode()
        (raw / pid / name).write_bytes(content)
        with closing(sqlite3.connect(db)) as conn, conn:
            conn.execute("UPDATE sources SET sha256_hash=? WHERE psi_id=?", (hashlib.sha256(content).hexdigest(), pid))
            conn.execute("UPDATE experiments SET raw_attributes_json=? WHERE psi_id=?", (json.dumps(source_row), pid))
        rejected = assess(self.query, db_path=db, raw_root=raw, models_dir=self.models)
        self.assertEqual(rejected.status, "INSUFFICIENT_DATA")
        self.assertTrue(rejected.sources)  # Still useful for qualitative interpretation.

    def test_updated_approved_version_is_loaded_without_ui_changes(self):
        self.fixture_model()
        query = self.query.model_copy(update={"flow_sequence_raw": "10"})
        self.assertEqual(self.route(query).model_version, "a" * 64)
        self.fixture_model(version="b" * 64)
        self.assertEqual(self.route(query).model_version, "b" * 64)

    def test_overlapping_physical_models_do_not_select_arbitrarily(self):
        registry = self.fixture_model()
        other = self.models / "different_physical_task"
        shutil.copytree(registry, other)
        result = self.route(self.query.model_copy(update={"flow_sequence_raw": "10"}))
        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertIsNone(result.value)
        self.assertTrue(any("ambiguous" in r for r in result.domain_assessment["rejection_reasons"]))

    def test_nominal_pressure_requires_explicit_acknowledgment(self):
        result = self.route(self.query.model_copy(update={"allow_nominal_pressure": False}))
        self.assertEqual(result.status, "INSUFFICIENT_DATA")

    def test_actual_research_model_is_loaded_but_never_silently_promoted(self):
        query = self.query.model_copy(update={"o2_initial_pct": 21.75})
        result = assess(query)
        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertTrue(result.model_diagnostics["artifact_loaded"])
        self.assertEqual(result.model_diagnostics["status"], "RESEARCH_ONLY")
        self.assertIsNone(result.value)

    def test_gemini_cannot_invent_numbers_or_sources(self):
        original = self.route()
        client = Mock()
        source = original.sources[0]
        answer = AssessmentNarrative.model_validate({"observations": [{"text": "Predicted value is 99 percent", "citations": [
            {"source_id": source["source_id"], "quote": source["text"][:60]}]}], "interpretations": [], "limitations": []})
        client.generate.return_value = answer
        result = interpret(self.query, original, client)
        self.assertIsNone(result.scientific_interpretation)
        self.assertEqual(result.value, original.value)
        answer.observations[0].text = "The source contains experimental values."
        answer.observations[0].citations[0].source_id = "invented"
        self.assertIsNone(interpret(self.query, original, client).scientific_interpretation)

    def test_experimental_proposal_is_distinct_and_uses_only_requested_conditions(self):
        original = self.route(self.query.model_copy(update={"gravity_g": .166}))
        client = Mock()
        client.generate.return_value = AssessmentNarrative(observations=[], interpretations=[], limitations=["Partial gravity evidence is absent."],
            proposed_investigation=ExperimentalProposal(objective="Characterize the requested gravity regime.",
                independent_variables=["Gravity"], controlled_variables=["Material", "Geometry"], required_measurements=["Chamber gas concentrations"],
                suggested_techniques=["Calibrated gas analysis"], comparison_rationale="Compare against supplied source evidence.",
                expected_knowledge_gain="Establish applicability of future estimators."))
        result = interpret(self.query, original, client)
        self.assertEqual(result.status, "INSUFFICIENT_DATA")
        self.assertIsNone(result.value)
        self.assertIn("not an existing NASA", result.recommended_experiments[0]["label"])
        self.assertEqual(result.recommended_experiments[0]["proposed_conditions"], self.query.model_dump())


if __name__ == "__main__":
    unittest.main(verbosity=2)
