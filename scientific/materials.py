"""Partial-condition, multi-characteristic research assessment; never a material safety score."""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from config.settings import BASE_DIR, DB_PATH, RAW_DATA_DIR
from database.repository import get_experiments_df, get_findings, get_measurements_df
from scientific.assessment import MATCH_FIELDS, assess, public_observation
from scientific.evidence import equal, finite, load_evidence, related_records
from scientific.labels import name
from scientific.schemas import AssessmentRequest

MODES = ["Assess Material", "Find Materials", "Compare Materials", "Predict Parameter"]


class Parameter(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    state: Literal["specified", "any", "unknown", "range"] = "unknown"
    value: float | str | bool | None = None
    lower: float | None = None
    upper: float | None = None

    @model_validator(mode="after")
    def semantics(self):
        if self.state == "specified" and (self.value is None or self.value == ""):
            raise ValueError("A specified parameter needs a value.")
        if self.state == "range" and (self.lower is None or self.upper is None or self.lower > self.upper):
            raise ValueError("Provide ordered range bounds.")
        if self.state in ("any", "unknown") and any(v is not None for v in (self.value, self.lower, self.upper)):
            raise ValueError("Unrestricted and unknown parameters have no physical value.")
        if self.state == "specified" and (self.lower is not None or self.upper is not None):
            raise ValueError("An exact value cannot have range bounds.")
        if self.state == "range" and self.value is not None:
            raise ValueError("A range has no automatic midpoint.")
        return self


class MaterialQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["Assess Material", "Find Materials", "Compare Materials", "Predict Parameter"] = "Assess Material"
    materials: list[str] = Field(default_factory=list)
    application: str = ""
    mission: str = "Custom conditions"
    parameters: dict[str, Parameter] = Field(default_factory=dict)
    target: str | None = None
    reference_uid: str | None = None
    criterion: Literal["flame_spread_rate_mm_s", "hrr_watts", "limiting_oxygen_index_pct"] | None = None

    @model_validator(mode="after")
    def physical_values(self):
        if self.mode in ("Assess Material", "Predict Parameter") and len(self.materials) > 1:
            raise ValueError("Choose one material or use Compare Materials.")
        if set(self.parameters) - set(MATCH_FIELDS):
            raise ValueError("Unsupported physical parameter.")
        for key, parameter in self.parameters.items():
            if key in ("o2_initial_pct", "co2_initial_pct", "pressure_psi", "gravity_g",
                       "flow_velocity_initial_cm_s", "thickness_mm", "width_cm", "diameter_mm"):
                numbers = [parameter.value] if parameter.state == "specified" else (
                    [parameter.lower, parameter.upper] if parameter.state == "range" else [])
                for value in numbers:
                    parsed = finite(value)
                    if parsed is None or parsed < 0 or (key.endswith("_pct") and parsed > 100):
                        raise ValueError(f"Invalid {name(key)}.")
                    if key in ("pressure_psi", "thickness_mm", "width_cm", "diameter_mm") and parsed == 0:
                        raise ValueError(f"{name(key)} must be positive or unknown.")
        if self.mode == "Predict Parameter" and not self.target:
            raise ValueError("Select a physical characteristic.")
        return self


class Characteristic(BaseModel):
    parameter: str
    display_name: str
    status: Literal["OBSERVED", "INTERPOLATED", "PREDICTED", "UNAVAILABLE"] = "UNAVAILABLE"
    relation: str = "Unavailable"
    value: float | None = None
    observed_range: list[float] | None = None
    unit: str | None = None
    prediction_interval: list[float] | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    groups: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    missing_features: list[str] = Field(default_factory=list)
    numerical_result: dict[str, Any] | None = None


class MaterialReport(BaseModel):
    material: str
    conclusion: str
    characteristics: list[Characteristic] = Field(default_factory=list)
    qualitative_evidence: list[dict[str, Any]] = Field(default_factory=list)
    source_records: list[dict[str, Any]] = Field(default_factory=list)


class MaterialAssessment(BaseModel):
    query: MaterialQuery
    conclusion: str
    reports: list[MaterialReport] = Field(default_factory=list)
    comparison: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    synthesis: dict[str, Any] | None = None
    synthesis_status: str = "Not requested"


def discover_targets(db_path=DB_PATH, models_dir=BASE_DIR / "models"):
    targets = set(get_measurements_df(db_path=db_path).parameter.dropna())
    for registry in Path(models_dir).glob("*"):
        for pointer in (registry / "approved.json", registry / "latest_research.json"):
            try:
                version = json.loads(pointer.read_text(encoding="utf-8"))["version_id"]
                if len(version) != 64 or any(c not in "0123456789abcdef" for c in version):
                    continue
                targets.add(json.loads((registry / "versions" / version / "metadata.json").read_text(encoding="utf-8"))["target"])
            except (OSError, ValueError, KeyError):
                pass
    return sorted(targets)


def matches(features, parameters):
    for key, parameter in parameters.items():
        if parameter.state == "specified" and not equal(features.get(key), parameter.value):
            return False
        if parameter.state == "range":
            value = finite(features.get(key))
            if value is None or not parameter.lower <= value <= parameter.upper:
                return False
    return True


def strict_request(query, material, target, reference=None):
    """No imputation. A record lookup can inherit source conditions; a prediction cannot."""
    values = dict(reference["features"]) if reference else {}
    for key, parameter in query.parameters.items():
        if parameter.state == "specified":
            values[key] = parameter.value
        else:
            values.pop(key, None)
    required = ["geometry", "o2_initial_pct", "pressure_psi", "flow_velocity_initial_cm_s", "gravity_g",
                "flow_direction", "is_reused_sample", "burn_sides", "co2_initial_pct"]
    geometry = str(values.get("geometry", "")).lower()
    required += ["thickness_mm", "width_cm"] if any(k in geometry for k in ("slab", "film", "sheet")) else []
    required += ["diameter_mm"] if any(k in geometry for k in ("rod", "sphere")) else []
    missing = [k for k in required if values.get(k) is None]
    if missing:
        return None, missing
    values.update(material_name=material, target=target, mission=query.mission,
                  reference_uid=query.reference_uid if reference else None)
    try:
        return AssessmentRequest(**values), []
    except ValueError:
        return None, required


GROUP_KEYS = ("geometry", "gravity_g", "flow_direction", "pressure_psi", "thickness_mm", "width_cm",
              "diameter_mm", "flow_velocity_initial_cm_s", "flow_sequence_raw", "co2_initial_pct", "burn_sides", "is_reused_sample")


def observation_groups(observations):
    groups = {}
    for observation in observations:
        features = observation["features"]
        # Investigation and source document protect against pooling different apparatus/methods.
        key = json.dumps([observation["psi_id"], observation["source"]["source_doc"], observation["unit"],
                          *[features.get(k) for k in GROUP_KEYS]], sort_keys=True)
        group = groups.setdefault(key, {"conditions": {k: features.get(k) for k in GROUP_KEYS},
            "psi_id": observation["psi_id"], "source_doc": observation["source"]["source_doc"],
            "unit": observation["unit"], "values": [], "test_ids": []})
        group["values"].append(observation["value"])
        group["test_ids"].append(observation["test_id"])
    return list(groups.values())


def compare_reports(reports):
    """No universal winner: only exact protocol/physical-condition strata can be compared."""
    comparison = []
    for target in sorted({c.parameter for r in reports for c in r.characteristics}):
        entries, signatures = [], {}
        for report in reports:
            characteristic = next((c for c in report.characteristics if c.parameter == target), None)
            if not characteristic or not characteristic.evidence:
                entries.append({"material": report.material, "status": "Missing measurements"})
                continue
            entries.append({"material": report.material, "status": characteristic.relation,
                            "range": characteristic.observed_range, "unit": characteristic.unit})
            for evidence in characteristic.evidence:
                conditions = evidence["conditions"]
                signature = json.dumps([evidence["psi_id"], evidence["source"]["source_doc"], evidence["unit"],
                    conditions.get("o2_initial_pct"), *[conditions.get(k) for k in GROUP_KEYS]], sort_keys=True)
                signatures.setdefault(signature, set()).add(report.material)
        comparable = any(len(materials) == len(reports) and len(materials) > 1 for materials in signatures.values())
        comparison.append({"parameter": target, "display_name": name(target), "comparable": comparable,
            "conclusion": "Shared recorded conditions; material-property equivalence still requires scientific review." if comparable else
                          "Available records do not establish a controlled comparison between all selected materials.", "materials": entries})
    return comparison


def assess_materials(query, db_path=DB_PATH, raw_root=RAW_DATA_DIR, models_dir=BASE_DIR / "models"):
    result = MaterialAssessment(query=query, conclusion="Insufficient evidence for material selection.")
    try:
        targets = [query.target] if query.mode == "Predict Parameter" else discover_targets(db_path, models_dir)
        pool, failures = {}, []
        for target in targets:
            try:
                pool[target], _ = load_evidence(db_path, raw_root, target)
            except Exception:
                pool[target] = []
                failures.append(name(target))
        materials = query.materials
        if query.mode == "Find Materials":
            materials = sorted({o["features"]["material_name"] for observations in pool.values() for o in observations
                                if matches(o["features"], query.parameters)})
            if not materials:
                # Show related candidates honestly, without claiming environmental applicability.
                materials = sorted({o["features"]["material_name"] for observations in pool.values() for o in observations})
                result.limitations.append("No candidate has verified measurements matching all requested conditions; listed materials are related research candidates only.")
        findings = get_findings(db_path=db_path)
        for material in dict.fromkeys(materials):
            context = related_records(db_path, raw_root, material)
            reference = next((o for observations in pool.values() for o in observations
                              if o["uid"] == query.reference_uid and equal(o["features"]["material_name"], material)), None)
            report = MaterialReport(material=material, conclusion="Limited experimental evidence; material suitability is not established.")
            for target in targets:
                observations = [o for o in pool[target] if equal(o["features"]["material_name"], material)]
                selected = [o for o in observations if matches(o["features"], query.parameters)
                            and (query.reference_uid is None or o["uid"] == query.reference_uid)]
                characteristic = Characteristic(parameter=target, display_name=name(target))
                request, missing = strict_request(query, material, target, reference)
                if request is not None:
                    try:
                        numerical = assess(request, db_path=db_path, raw_root=raw_root, models_dir=models_dir,
                                           evidence_snapshot=(pool[target], []), related_context=context)
                        characteristic.numerical_result = numerical.model_dump()
                        if numerical.status != "INSUFFICIENT_DATA":
                            characteristic.status = numerical.status
                            characteristic.relation = "Recorded observation" if numerical.status == "OBSERVED" else numerical.status.title()
                            characteristic.value, characteristic.unit = numerical.value, numerical.unit
                            characteristic.observed_range = numerical.observed_range
                            characteristic.prediction_interval = numerical.prediction_interval
                            characteristic.evidence = numerical.supporting_experiments
                            characteristic.limitations = numerical.limitations
                    except Exception:
                        characteristic.limitations.append("The numerical estimator is unavailable; original evidence remains accessible.")
                characteristic.missing_features = missing
                if characteristic.status == "UNAVAILABLE" and selected:
                    characteristic.status = "OBSERVED"
                    characteristic.relation = "Conditional observations — not an exact physical match"
                    characteristic.evidence = [public_observation(o) for o in selected]
                    units = {o["unit"] for o in selected}
                    characteristic.unit = next(iter(units)) if len(units) == 1 else None
                    if len(units) == 1:
                        characteristic.observed_range = [min(o["value"] for o in selected), max(o["value"] for o in selected)]
                    characteristic.limitations.append("Unrestricted or unknown conditions prevent a uniquely specified physical outcome. The observed range is not a prediction interval.")
                characteristic.groups = observation_groups(selected)
                if not characteristic.evidence:
                    characteristic.relation = "Related evidence only" if observations else "No verified measurement"
                    characteristic.evidence = [public_observation(o) for o in observations]
                report.characteristics.append(characteristic)
            report.source_records = context
            ids = {o["psi_id"] for o in context}
            report.qualitative_evidence = [f for f in findings if f["psi_id"] in ids]
            usable = [c for c in report.characteristics if c.status != "UNAVAILABLE"]
            if usable:
                report.conclusion = "Recorded combustion evidence is available under the selected scope. Further validation is required before material selection."
            result.reports.append(report)
        result.comparison = compare_reports(result.reports) if len(result.reports) > 1 else []
        if query.criterion:
            result.limitations.append(f"Selection criterion: {name(query.criterion)}. A numerical ordering requires shared experimental conditions and reviewed material equivalence; no safety ranking is inferred.")
            if not any(c.parameter == query.criterion and c.status != "UNAVAILABLE" for r in result.reports for c in r.characteristics):
                result.limitations.append("The requested selection criterion has no applicable verified measurements in this scope.")
        sources = {s["source"]["source_id"]: s["source"] for r in result.reports for s in r.source_records}
        result.sources = list(sources.values())
        if any(c.status != "UNAVAILABLE" for r in result.reports for c in r.characteristics):
            result.conclusion = "Recorded combustion evidence is available for the selected scope. It does not establish material safety or suitability outside the tested conditions."
        elif result.sources:
            result.conclusion = "Related experimental records are available, but the requested conditions lack directly applicable measurements. Material selection requires further validation."
        result.limitations += ["Quantitative measurement uncertainty is not supplied by the current source CSV.",
            "Lower final CO₂ concentration alone does not establish greater fire safety."]
        if query.application:
            result.limitations.append("Intended application is context for interpretation; this archive does not establish application-specific qualification or material suitability.")
        if failures:
            result.limitations.append("Some characteristics could not be retrieved; other results remain available.")
    except Exception:
        result.limitations.append("The experimental archive is unavailable. No measurements or suitability claims were generated.")
    return result
