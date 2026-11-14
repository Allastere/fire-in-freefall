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
    "Thin Film", "Thick Slab", "Rod", "Sphere", "Fabric", "Droplet", "Porous Burner"
]
GravityLevel = Literal["0g", "1g", "Simulated Partial-g"]
ValueType = Literal["exact", "approximate", "threshold"]
VerificationStatus = Literal["verified", "needs_review", "conflict"]
FindingCategory = Literal[
    "Flammability Limit",
    "Toxicity",
    "Suppression",
    "Detection",
    "Partial Gravity",
    "Earth Spin-off",
    "Hardware Link",
]


class InvestigationModel(BaseModel):
    """NASA PSI investigation metadata and mandatory DOI citation attributes."""

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
        if isinstance(v, dict):
            return json.dumps(v, ensure_ascii=False)
        if isinstance(v, str):
            json.loads(v)
            return v
        raise ValueError("raw_attributes_json must be a valid JSON string or dict")


class MeasurementModel(BaseModel):
    """Vertical EAV sensor measurement row."""

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
