"""Real-source pipeline regressions; artificial additions below are test fixtures only."""

import copy
import hashlib
import json
import shutil
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

import numpy as np

from config.settings import BASE_DIR, DB_PATH, RAW_DATA_DIR
from ml.dataset import extract_dataset, fingerprint, read_json
from ml.evaluate import metrics
from ml.predict import assess, load_version
from ml.preprocessing import LocalLinearInterpolation, candidates
from ml.registry import assign_roles, write_json
from ml.train import train
from ml.uncertainty import calibrate

TASK = read_json(BASE_DIR / "ml/tasks.json")["pmma_slab_co2_final"]
PROTOCOLS = read_json(BASE_DIR / "ml/protocols.json")["protocols"]


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "research.db"
        self.raw = self.root / "raw"
        (self.raw / "PSI-25").mkdir(parents=True)
        shutil.copy2(RAW_DATA_DIR / "PSI-25" / PROTOCOLS[0]["file_name"], self.raw / "PSI-25" / PROTOCOLS[0]["file_name"])
        with closing(sqlite3.connect(DB_PATH.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(self.db)) as target:
                source.backup(target)

    def extract(self):
        return extract_dataset(self.db, self.raw, TASK, PROTOCOLS)

    def test_dynamic_readonly_dataset_and_cache_independence(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        dataset = self.extract()
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)
        self.assertTrue(dataset["samples"])
        self.assertTrue(all(s["geometry"] == "Thick Slab" for s in dataset["samples"]))
        forbidden = {"outcome", "o2_final_pct", "flow_velocity_min_cm_s", "flow_velocity_extinction_cm_s"}
        self.assertFalse(forbidden.intersection(dataset["samples"][0]["features"]))
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("INSERT INTO llm_cache(prompt_hash,model_name,response_json) VALUES (?,?,?)",
                         ("ml-test", "test", '"unused"'))
        self.assertEqual(dataset["dataset_sha256"], self.extract()["dataset_sha256"])

    def test_unknown_protocol_and_bad_source_hash_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "no source-backed"):
            extract_dataset(self.db, self.raw, TASK, [])
        csv_path = self.raw / "PSI-25" / PROTOCOLS[0]["file_name"]
        csv_path.write_bytes(csv_path.read_bytes() + b'\n')
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.extract()

    def test_new_compatible_record_is_incorporated_without_count_changes_in_code(self):
        before = self.extract()
        selected = before["samples"][0]
        with closing(sqlite3.connect(self.db)) as conn, conn:
            original = conn.execute("SELECT raw_attributes_json FROM experiments WHERE test_id=?", (selected["test_id"],)).fetchone()[0]
            raw = json.loads(original)
            raw["Test #"], raw["Sample #"], raw["Date"] = "NEW-TEST-ONLY", "90001", "test-only-session"
            # A cloned run is deliberately inserted only into this temporary test database.
            columns = [r[1] for r in conn.execute("PRAGMA table_info(experiments)")]
            values = list(conn.execute("SELECT * FROM experiments WHERE test_id=?", (selected["test_id"],)).fetchone())
            values[columns.index("test_id")] = raw["Test #"]
            values[columns.index("sample_id")] = raw["Sample #"]
            values[columns.index("raw_attributes_json")] = json.dumps(raw)
            conn.execute("INSERT INTO experiments VALUES (?,?,?,?,?,?,?,?,?)", values)
            for table in ("samples", "conditions", "measurements"):
                names = [r[1] for r in conn.execute("PRAGMA table_info(" + table + ")")]
                for source_row in conn.execute("SELECT * FROM " + table + " WHERE test_id=?", (selected["test_id"],)).fetchall():
                    new = list(source_row)
                    new[names.index("id")] = None
                    new[names.index("test_id")] = raw["Test #"]
                    conn.execute("INSERT INTO " + table + " VALUES (" + ",".join("?" for _ in new) + ")", new)
            csv_path = self.raw / "PSI-25" / PROTOCOLS[0]["file_name"]
            import pandas as pd
            frame = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
            frame.columns = frame.columns.str.strip()
            frame.loc[len(frame)] = raw
            frame.to_csv(csv_path, index=False)
            digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
            conn.execute("UPDATE sources SET sha256_hash=? WHERE file_path LIKE ?", (digest, "%" + csv_path.name))
        after = self.extract()
        self.assertEqual(len(after["samples"]), len(before["samples"])+1)
        self.assertNotEqual(before["dataset_sha256"], after["dataset_sha256"])

    def test_persistent_split_refuses_leakage_and_frozen_edits(self):
        dataset = self.extract()
        registry = self.root / "registry"
        assigned, _, manifest = assign_roles(dataset, registry, TASK)
        groups = {}
        for sample in assigned:
            self.assertEqual(groups.setdefault(sample["group"], sample["role"]), sample["role"])
        frozen_uid = next(iter(manifest["frozen"]))
        changed = copy.deepcopy(dataset)
        next(s for s in changed["samples"] if s["uid"] == frozen_uid)["observation_sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "Frozen"):
            assign_roles(changed, registry, TASK)
        cross = copy.deepcopy(dataset)
        dev = next(s for s in cross["samples"] if s["uid"] not in manifest["frozen"])
        frozen_token = next(t for t,r in manifest["tokens"].items() if r == "benchmark")
        dev["tokens"].append(frozen_token)
        with self.assertRaisesRegex(ValueError, "crosses"):
            assign_roles(cross, registry, TASK)

    def test_training_saves_model_and_never_promotes_unreviewed_candidate(self):
        dataset = self.extract()
        registry = self.root / "models" / "pmma_slab_co2_final"
        small = {k: v for k, v in candidates(TASK).items() if k in ("mean_baseline", "linear_regression")}
        with patch("ml.preprocessing.candidates", return_value=small):
            metadata = train("pmma_slab_co2_final", TASK, dataset, registry)
            repeated = train("pmma_slab_co2_final", TASK, dataset, registry)
        self.assertEqual(metadata["version_id"], repeated["version_id"])
        self.assertFalse((registry / "approved.json").exists())
        self.assertFalse((registry / ".training.lock").exists())
        self.assertEqual(metadata["status"], "RESEARCH_ONLY")
        artifact = registry / "versions" / metadata["version_id"] / "pipeline.joblib"
        self.assertTrue(artifact.is_file())
        self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), metadata["artifact_sha256"])
        loaded, _, _ = load_version(registry, metadata["version_id"], require_approved=False)
        self.assertTrue(hasattr(loaded, "predict"))
        result = assess("pmma_slab_co2_final", {}, "PMMA", {}, models_dir=registry.parent)
        self.assertEqual(result["status"], "INSUFFICIENT_DATA")
        self.assertIsNone(result["value"])


class EvaluationTests(unittest.TestCase):
    def test_interpolation_never_extrapolates(self):
        model = LocalLinearInterpolation().fit(np.array([[34.0], [36.0]]), np.array([2.0, 4.0]))
        self.assertAlmostEqual(model.predict([[35.0]])[0], 3.0)
        self.assertTrue(np.isnan(model.predict([[40.0]])[0]))

    def test_insufficient_calibration_does_not_invent_confidence(self):
        class Constant:
            def predict(self, X):
                return np.zeros(len(X))
        result = calibrate(Constant(), np.zeros((2, 1)), np.ones(2), np.array(["same", "same"]),
                           np.zeros((2, 1)), np.ones(2), alpha=0.1)
        self.assertIsNone(result["half_width"])
        self.assertIsNone(result["benchmark_coverage"])

    def test_metrics_preserve_undefined_r2_and_canonical_order(self):
        self.assertIsNone(metrics([1], [1], ["group"])["r2"])
        self.assertEqual(fingerprint({"b": 2, "a": 1}), fingerprint({"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
