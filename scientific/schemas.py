"""One contract for database retrieval, approved inference and interpretation."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    material_name: str = Field(min_length=1)
    geometry: str = Field(min_length=1)
    target: str = Field(min_length=1)
    o2_initial_pct: float = Field(ge=0, le=100)
    pressure_psi: float = Field(gt=0)
    flow_velocity_initial_cm_s: float = Field(ge=0)
    gravity_g: float = Field(ge=0)
    flow_direction: str
    thickness_mm: float | None = Field(default=None, gt=0)
    width_cm: float | None = Field(default=None, gt=0)
    diameter_mm: float | None = Field(default=None, gt=0)
    co2_initial_pct: float | None = Field(default=None, ge=0, le=100)
    is_reused_sample: bool = False
    burn_sides: str = "unspecified"
    flow_sequence_raw: str | None = None
    allow_nominal_pressure: bool = False
    mission: str = "Custom conditions"
    reference_uid: str | None = None


class Assessment(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    status: Literal["OBSERVED", "INTERPOLATED", "PREDICTED", "INSUFFICIENT_DATA"] = "INSUFFICIENT_DATA"
    method: str = "Evidence assessment; numerical estimation withheld"
    target: str
    value: float | None = None
    unit: str | None = None
    observed_values: list[float] = Field(default_factory=list)
    observed_range: list[float] | None = None
    prediction_interval: list[float] | None = None
    measurement_uncertainty: list[float] | None = None
    validation_metrics: dict[str, Any] | None = None
    model_version: str | None = None
    dataset_sha256: str | None = None
    training_sample_count: int | None = None
    independent_training_groups: int | None = None
    supporting_experiments: list[dict[str, Any]] = Field(default_factory=list)
    domain_assessment: dict[str, Any] = Field(default_factory=dict)
    model_diagnostics: dict[str, Any] | None = None
    limitations: list[str] = Field(default_factory=list)
    scientific_interpretation: dict[str, Any] | None = None
    recommended_experiments: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    interpretation_status: str = "Not requested"
