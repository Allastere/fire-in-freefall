"""FLEX droplet-only protocol. No pool of solids, cool flames or operator-terminated durations."""
import math
from scientific.archive import load_archive
from ml.dataset import components, fingerprint


def extract_flex(db_path, raw_root, task):
    archive = load_archive(db_path, raw_root)
    samples, exclusions, identities, sources = [], [], {}, {}
    candidates = []
    for row in archive["rows"]:
        if row["psi_id"] != "PSI-69" or row["parameter"] != task["target"] or row["subtype"] != task["subtype"]:
            continue
        uid = f"{row['psi_id']}:{row['test_id']}"
        run, raw = row["run"], row["run"].get("raw", {})
        if row["material"] != task["filters"]["material_name"]:
            continue
        try:
            if not row["verified"] or row["eligibility_status"] != "ML_ELIGIBLE" or row["value_type"] != "exact" or row["is_over_range"]:
                raise ValueError("unverified_censored_or_ineligible_target")
            if run.get("geometry") != "Droplet" or run.get("gravity_level") != "0g":
                raise ValueError("incompatible_regime")
            if row["parameter"] == "extinguishing_time_s" and str(raw.get("Test end", "")).casefold() != "extinction":
                raise ValueError("not_natural_extinction")
            session = str(raw.get("Test Date", "")).strip()
            identifier = str(raw.get("FLEX Identifier", "")).strip()
            if not session or not identifier:
                raise ValueError("missing_independent_group_identity")
            # Values come from initial source columns, never final measurements or SQL defaults.
            features = {"o2_initial_pct": float(raw["O initial ambient composition; mole fraction"]) * 100,
                "pressure_psi": float(raw["Ambient pressure; mmHg"]) / 51.71493257,
                "diameter_mm": float(raw["Droplet initial diameter; mm"]),
                "co2_diluent_pct": float(raw["CO initial ambient composition; mole fraction"]) * 100,
                "he_diluent_pct": float(raw["He initial ambient composition; mole fraction"]) * 100,
                "n2_diluent_pct": float(raw["N initial ambient composition; mole fraction"]) * 100}
            if any(not math.isfinite(v) or v < 0 for v in features.values()) or features["diameter_mm"] <= 0:
                raise ValueError("invalid_initial_features")
            if not math.isclose(sum(features[k] for k in ("o2_initial_pct","co2_diluent_pct","he_diluent_pct","n2_diluent_pct")),100,abs_tol=1):
                raise ValueError("invalid_initial_composition")
            ids = {"tokens": [f"sample:PSI-69:{identifier}", f"session:PSI-69:{session}"]}
            identities[uid] = ids
            sample = {"uid": uid, "test_id": row["test_id"], "psi_id": row["psi_id"], "material": row["material"],
                "geometry": "Droplet", "features": features, "target": row["value"],
                "source": {"source_doc": row["source_doc"], "source_sha256": row["source"]["source_sha256"],
                           "source_record": row["source"]["locator"]}, "protocol_id": "flex_initial_droplet_v1",
                "scientific_status": "research_only", "observation_sha256": fingerprint({"uid":uid,"raw":raw,"target":row["value"]})}
            candidates.append(sample)
            sources[row["source_doc"]] = row["source"]["source_sha256"]
        except (ValueError, TypeError, KeyError) as exc:
            exclusions.append({"uid":uid,"reason":str(exc)})
    groups = components(identities)
    seen = set()
    for sample in candidates:
        signature = fingerprint({"features":sample["features"],"target":sample["target"],"group":groups[sample["uid"]]})
        if signature in seen:
            exclusions.append({"uid":sample["uid"],"reason":"duplicate_source_observation"})
            continue
        seen.add(signature)
        samples.append({**sample,**groups[sample["uid"]]})
    snapshot = {"samples":sorted(samples,key=lambda s:s["uid"]),"source_hashes":sources,"task":task,
                "protocols":[{"id":"flex_initial_droplet_v1","scientific_status":"research_only"}]}
    if not samples:
        raise ValueError("INSUFFICIENT_DATA: no compatible FLEX observations")
    return {**snapshot,"dataset_sha256":fingerprint(snapshot),"exclusions":exclusions}
