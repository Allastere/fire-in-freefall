"""Strict Pydantic models for NASA PSI database entities, CSV column mapping, and SI outputs."""

import json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

SafetyPillar = Literal["Prevention", "Detection", "Suppression", "Multi"]
FuelCategory = Literal["Solid", "Liquid", "Gas", "Aerosol/Smoke"]
HardwareFacility = Literal["MSG", "CIR", "MDCA", "Saffire/Cygnus"]
FlowDirection = Literal["Opposed", "Concurrent", "Stagnation", "Quiescent", "Unknown"]
ExperimentOutcome = Literal["Sustained", "Quenched", "Blowoff", "No Ignition", "Unknown"]
SampleGeometry = Literal[
    "Thin Film",
    "Thick Slab",
    "Rod",
    "Sphere",
    "Fabric",
    "Droplet",
    "Porous Burner",
    "Gaseous Burner",
    "Wire/Insulation",
    "Bulk/Dust",
]
GravityLevel = Literal["0g", "1g", "Simulated Partial-g"]
ValueType = Literal[
    "exact",
    "approximate",
    "threshold",
    "interval",
    "upper_bound",
    "lower_bound",
    "censored_ft",
]
VerificationStatus = Literal["verified", "needs_review", "conflict"]
EligibilityStatus = Literal["ML_ELIGIBLE", "EVIDENCE_ONLY", "NEEDS_REVIEW"]
FindingCategory = Literal[
    "Flammability Limit",
    "Toxicity",
    "Suppression",
    "Detection",
    "Partial Gravity",
    "Earth Spin-off",
    "Hardware Link",
    "Research Limitation",
    "Equipment Implication",
]


def _ensure_json_str(v: Any, default_empty: str = "{}") -> str:
    if v is None:
        return default_empty
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)
    if isinstance(v, str):
        stripped = v.strip()
        if not stripped:
            return default_empty
        json.loads(stripped)
        return stripped
    raise ValueError(f"Expected JSON string, dict, or list, got {type(v)}")


class InvestigationModel(BaseModel):
    """NASA PSI investigation metadata, mandatory DOI citation, and research intelligence profile."""

    model_config = ConfigDict(extra="forbid")

    psi_id: str = Field(..., min_length=1, description="Primary identifier, e.g. 'PSI-25'")
    acronym: str = Field(..., min_length=1, description="Investigation acronym, e.g. 'BASS-II'")
    title: str = Field(..., min_length=1)
    doi: str = Field(..., min_length=3, description="Mandatory official NASA PSI DOI")
    psi_url: str = Field(..., min_length=10, description="Direct URL to psi.nasa.gov")
    citation_text: str = Field(..., min_length=10, description="Official NASA citation string")
    safety_pillar: SafetyPillar
    fuel_category: FuelCategory
    hardware_facility: HardwareFacility
    objectives: str
    summary: str
    earth_spinoff_text: str
    related_psi_ids: list[str] = Field(default_factory=list)
    pi_names: str = ""
    pillar_classifications_json: str = "[]"
    objective_tags_json: str = "[]"
    hardware_relationships_json: str = "{}"
    cross_relationships_json: str = "[]"
    limitations_json: str = "[]"

    @field_validator(
        "pillar_classifications_json",
        "objective_tags_json",
        "cross_relationships_json",
        "limitations_json",
        mode="before",
    )
    @classmethod
    def ensure_json_array(cls, v: Any) -> str:
        return _ensure_json_str(v, "[]")

    @field_validator("hardware_relationships_json", mode="before")
    @classmethod
    def ensure_json_obj(cls, v: Any) -> str:
        return _ensure_json_str(v, "{}")


class SampleModel(BaseModel):
    """Material sample and burner geometry associated with an experiment test_id."""

    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    test_id: str = Field(..., min_length=1)
    material_name: str = Field(..., min_length=1)
    geometry: SampleGeometry
    thickness_mm: float | None = Field(default=None, ge=0.0)
    width_cm: float | None = Field(default=None, ge=0.0)
    diameter_mm: float | None = Field(default=None, ge=0.0)
    original_material_designation: str | None = None
    material_family: str | None = None
    fuel_phase: str = "Solid"
    length_cm: float | None = Field(default=None, ge=0.0)

    @field_validator("thickness_mm", "width_cm", "diameter_mm", "length_cm", mode="before")
    @classmethod
    def sanitize_non_negative_dim(cls, v: Any) -> float | None:
        if v is None:
            return None
        try:
            fv = float(v)
            return max(0.0, fv)
        except (ValueError, TypeError):
            return None


class ConditionModel(BaseModel):
    """Environmental and ventilation boundary conditions for an experiment test_id."""

    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    test_id: str = Field(..., min_length=1)
    o2_initial_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    o2_final_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    pressure_psi: float = Field(default=14.7, gt=0.0)
    diluent_gas: str | None = None
    diluent_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    flow_velocity_initial_cm_s: float | None = Field(default=None, ge=0.0)
    flow_velocity_min_cm_s: float | None = Field(default=None, ge=0.0)
    flow_velocity_extinction_cm_s: float | None = Field(default=None, ge=0.0)
    flow_sequence_raw: str | None = None
    gravity_level: GravityLevel = "0g"
    oxygen_location: str = "CHAMBER_AMBIENT"
    co2_diluent_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    he_diluent_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    n2_diluent_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    ambient_temp_k: float | None = Field(default=None, gt=0.0)
    ignition_outcome: str = "UNKNOWN"
    propagation_outcome: str = "UNKNOWN"
    suppression_outcome: str = "UNKNOWN"
    material_behaviour: str = "NONE"

    @field_validator("pressure_psi", mode="before")
    @classmethod
    def sanitize_pressure_psi(cls, v: Any) -> float:
        if v is None:
            return 14.7
        try:
            fv = float(v)
            return fv if fv > 0.0 else 14.7
        except (ValueError, TypeError):
            return 14.7

    @field_validator("ambient_temp_k", mode="before")
    @classmethod
    def sanitize_ambient_temp_k(cls, v: Any) -> float | None:
        if v is None:
            return None
        try:
            fv = float(v)
            return fv if fv > 0.0 else None
        except (ValueError, TypeError):
            return None

    @field_validator(
        "flow_velocity_initial_cm_s",
        "flow_velocity_min_cm_s",
        "flow_velocity_extinction_cm_s",
        mode="before",
    )
    @classmethod
    def sanitize_flow_velocity(cls, v: Any) -> float | None:
        if v is None:
            return None
        try:
            fv = float(v)
            return max(0.0, fv)
        except (ValueError, TypeError):
            return None

    @field_validator(
        "o2_initial_pct",
        "o2_final_pct",
        "diluent_pct",
        "co2_diluent_pct",
        "he_diluent_pct",
        "n2_diluent_pct",
        mode="before",
    )
    @classmethod
    def sanitize_pct(cls, v: Any) -> float | None:
        if v is None:
            return None
        try:
            fv = float(v)
            if fv < 0.0:
                return 0.0
            if fv > 100.0:
                return 100.0
            return fv
        except (ValueError, TypeError):
            return None


class ExperimentModel(BaseModel):
    """Single experimental run with raw JSON fallback for non-standard CSV columns."""

    model_config = ConfigDict(extra="forbid")

    test_id: str = Field(..., min_length=1)
    psi_id: str = Field(..., min_length=1)
    pi_name: str = Field(..., min_length=1)
    sample_id: str
    is_reused_sample: bool = False
    flow_direction: FlowDirection = "Unknown"
    outcome: ExperimentOutcome = "Unknown"
    observations: str = ""
    raw_attributes_json: str = Field(default="{}")

    @field_validator("raw_attributes_json", mode="before")
    @classmethod
    def ensure_json_string(cls, v: Any) -> str:
        return _ensure_json_str(v, "{}")


class MeasurementModel(BaseModel):
    """Vertical EAV sensor measurement row with scientific subtype, bounds, and ML eligibility."""

    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    psi_id: str = Field(..., min_length=1)
    test_id: str | None = None
    parameter: str = Field(..., min_length=1)
    value: float
    unit: str = Field(..., min_length=1)
    is_over_range: bool = False
    value_type: ValueType = "exact"
    source_doc: str = Field(..., min_length=1)
    source_page: int | None = Field(default=None, ge=1)
    verification_status: VerificationStatus = "verified"
    subtype: str | None = None
    value_min: float | None = None
    value_max: float | None = None
    statistic_type: str = "EXACT_RUN"
    instrument: str | None = None
    ignition_method: str | None = None
    eligibility_status: EligibilityStatus = "ML_ELIGIBLE"
    source_trace_json: str = "{}"

    @field_validator("source_trace_json", mode="before")
    @classmethod
    def ensure_trace_json(cls, v: Any) -> str:
        return _ensure_json_str(v, "{}")


class FindingModel(BaseModel):
    """Verified scientific claim and evidence quote linked to a source document and page."""

    model_config = ConfigDict(extra="forbid")

    id: int | None = None
    psi_id: str = Field(..., min_length=1)
    category: FindingCategory
    claim: str = Field(..., min_length=5)
    evidence_quote: str = Field(..., min_length=5)
    source_doc: str = Field(..., min_length=1)
    source_page: int | None = Field(default=None, ge=1)
    finding_title: str = ""
    finding_type: str = "DIRECT_EXPERIMENTAL"
    safety_pillar: str = "Prevention"
    objective_tag: str = ""


# --- CSV Adaptive Column Mapping Schemas (Context.md Section 5.1) ---


class ColumnMappingTarget(BaseModel):
    """Mapping of a single raw CSV column header to a canonical table/parameter."""

    model_config = ConfigDict(extra="forbid")

    raw_column: str
    target_table: Literal["experiments", "samples", "conditions", "measurements", "ignore"]
    target_field: str = Field(
        ...,
        description="Column name in target table, or canonical parameter name if measurements",
    )
    detected_unit: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ColumnMappingPlan(BaseModel):
    """Structured output schema for deterministic + Gemini CSV column mapping."""

    model_config = ConfigDict(extra="forbid")

    psi_id: str
    mappings: list[ColumnMappingTarget]
    unmapped_columns: list[str] = Field(default_factory=list)


# --- Structured SI Output Schemas (Context.md Section 6.2) ---


class SICitation(BaseModel):
    """Verified citation reference with mandatory DOI and document page."""

    model_config = ConfigDict(extra="forbid")

    psi_id: str
    doi: str
    source_doc: str
    source_page: int | None = None
    quote_snippet: str

    def format_tag(self) -> str:
        page_str = f"стр. {self.source_page}" if self.source_page is not None else "стр. Unknown"
        return f"[{self.psi_id} | {self.doi} | {self.source_doc}, {page_str}]"


class SIInsightResponse(BaseModel):
    """Strict structured response for SI Engineering Copilot (gemini-3.5-flash-lite)."""

    model_config = ConfigDict(extra="forbid")

    executive_summary: str
    prevention_insights: str
    detection_insights: str
    suppression_insights: str
    partial_gravity_corridor_analysis: str
    earth_spinoff_relevance: str
    missing_parameters: list[str] = Field(
        default_factory=list,
        description="Parameters not explicitly present in the provided SQLite/PDF context",
    )
    citations: list[SICitation] = Field(..., min_length=1)
