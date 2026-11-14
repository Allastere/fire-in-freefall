"""Physical sanity checks for boundary conditions and sensor readings."""

from core.schemas import ConditionModel, VerificationStatus


def validate_condition(cond: ConditionModel) -> tuple[VerificationStatus, list[str]]:
    """Validate physical plausibility of O2 bounds, pressure, and ventilation speeds."""
    warnings: list[str] = []
    status: VerificationStatus = "verified"

    if cond.o2_initial_pct is not None:
        if not (0.0 <= cond.o2_initial_pct <= 100.0):
            warnings.append(f"Out-of-range initial O2%: {cond.o2_initial_pct}")
            status = "conflict"

    if cond.o2_final_pct is not None:
        if not (0.0 <= cond.o2_final_pct <= 100.0):
            warnings.append(f"Out-of-range final O2%: {cond.o2_final_pct}")
            status = "conflict"
        elif cond.o2_initial_pct is not None:
            # Combustion consumes O2; an apparent rise >0.5% or drop >10% indicates post-burn sensor power-off/drift
            if cond.o2_final_pct > cond.o2_initial_pct + 0.5:
                warnings.append(
                    f"Sensor spike anomaly: final O2 ({cond.o2_final_pct}%) > initial O2 ({cond.o2_initial_pct}%)"
                )
                status = "needs_review"
            elif cond.o2_final_pct < 5.0 and cond.o2_initial_pct > 15.0:
                warnings.append(
                    f"Sensor drop/offline anomaly: final O2 ({cond.o2_final_pct}%) vs initial ({cond.o2_initial_pct}%)"
                )
                status = "needs_review"

    if cond.pressure_psi <= 0.0:
        warnings.append(f"Non-positive pressure_psi: {cond.pressure_psi}")
        status = "conflict"

    for label, vel in (
        ("initial_flow", cond.flow_velocity_initial_cm_s),
        ("min_flow", cond.flow_velocity_min_cm_s),
        ("extinction_flow", cond.flow_velocity_extinction_cm_s),
    ):
        if vel is not None and vel < 0.0:
            warnings.append(f"Negative {label}: {vel}")
            status = "conflict"

    return status, warnings


def validate_co2_pct(co2_pct: float | None) -> tuple[VerificationStatus, str | None]:
    """Verify CO2 volume percentage falls within physical chamber limits."""
    if co2_pct is None:
        return "verified", None
    if not (0.0 <= co2_pct <= 25.0):
        return "needs_review", f"Implausible CO2%: {co2_pct}%"
    return "verified", None
