"""Reproducible archive-wide scientific audit: python -m ml.audit."""
from collections import Counter, defaultdict
from pathlib import Path
import json

from scientific.archive import load_archive
from config.settings import BASE_DIR


def audit(archive):
    grouped = defaultdict(list)
    for row in archive["rows"]:
        grouped[(row["parameter"], row["subtype"], row["unit"])].append(row)
    targets = []
    for (target, subtype, unit), rows in sorted(grouped.items(), key=lambda pair: str(pair[0])):
        samples = {(r["psi_id"], r["run"].get("sample_id")) for r in rows if r["run"].get("sample_id")}
        targets.append({"target": target, "subtype": subtype, "unit": unit, "observations": len(rows),
            "unique_experiments": len({r["test_id"] for r in rows if r["test_id"]}),
            "reported_sample_identifiers": len(samples), "source_verified": sum(r["verified"] for r in rows),
            "eligibility_labels": dict(Counter(r["eligibility_status"] for r in rows)),
            "value_types": dict(Counter(r["value_type"] for r in rows)),
            "materials": dict(Counter(str(r["material"]) for r in rows)),
            "fuel_phases": dict(Counter(str(r["conditions"].get("fuel_phase")) for r in rows)),
            "regimes": dict(Counter(str(r["conditions"].get("gravity_g")) for r in rows)),
            "missing_conditions": {k: sum(r["conditions"].get(k) is None for r in rows)
                for k in ("o2_initial_pct", "pressure_psi", "gravity_g", "flow_velocity_initial_cm_s", "diameter_mm")},
            "reused_runs": len({r["test_id"] for r in rows if r["run"].get("is_reused_sample")}),
            "duplicate_observations": len(rows) - len({(r["psi_id"],r["test_id"],r["source_doc"],r["source_page"],r["subtype"],r["value"]) for r in rows}),
            "training_policy": "Import eligibility is necessary but not sufficient; require explicit compatible task, source checks and independent groups."})
    return {"dataset_sha256": archive["fingerprint"], "counts": {k: len(v) for k,v in archive["tables"].items()},
        "source_problems": archive["problems"], "targets": targets,
        "limitations": ["Sample identifiers are not proof of independent specimens; sessions and reused samples are grouped.",
            "Aggregate document tables, calibration dust and censored/terminated tests are not ordinary training samples."]}


def main():
    report = audit(load_archive())
    path = BASE_DIR / "docs" / "SCIENTIFIC_DATA_AUDIT.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(path), "counts": report["counts"], "source_problems": report["source_problems"]}, indent=2))


if __name__ == "__main__":
    main()
