"""Rank compatible records; distance is retrieval ordering, never calibrated confidence."""
import math
from scientific.evidence import equal, finite

NUMERIC=("o2_initial_pct","pressure_psi","flow_velocity_initial_cm_s","diameter_mm","thickness_mm","width_cm",
         "co2_diluent_pct","he_diluent_pct","n2_diluent_pct","ambient_temp_k","aerosol_aging_time_s","mixing_time_s")


def compatible_related(request, rows):
    candidates=[]
    for row in rows:
        if not row["verified"] or row.get("data_quality_issues"):continue
        if row["conditions"].get("pressure_psi") is not None and row["conditions"]["pressure_psi"]<=0:continue
        # Extinction duration must not be substituted by disruption or operator termination.
        subtype=str(row.get("subtype") or "").upper()
        if row["parameter"]=="extinguishing_time_s":
            if any(word in subtype for word in ("DISRUPTION","TERMINATED","COMPLETION","CENSORED")):continue
            end=str(row.get("run",{}).get("raw",{}).get("Test end","")).casefold()
            if end and end!="extinction":continue
        if any(p.state=="specified" and not equal(row["conditions"].get(k),p.value)
               for k,p in request.parameters.items() if k in ("geometry","fuel_phase","flow_direction")):continue
        candidates.append(row)
    ranges={k:max([finite(r["conditions"].get(k)) for r in candidates if finite(r["conditions"].get(k)) is not None],default=0)
              -min([finite(r["conditions"].get(k)) for r in candidates if finite(r["conditions"].get(k)) is not None],default=0) for k in NUMERIC}
    ranked=[]
    for row in candidates:
        distance=0.;differences=[]
        gravity=request.parameters.get("gravity_g")
        gravity_match=gravity is None or gravity.state in ("any","unknown") or (
            equal(row["conditions"].get("gravity_g"),gravity.value) if gravity.state=="specified" else
            row["conditions"].get("gravity_g") is not None and gravity.lower<=row["conditions"]["gravity_g"]<=gravity.upper)
        for k in NUMERIC:
            p=request.parameters.get(k)
            if p is None or p.state in ("any","unknown"):continue
            value=finite(row["conditions"].get(k))
            if value is None:
                distance+=4;differences.append(k+": unknown in source");continue
            delta=abs(value-float(p.value)) if p.state=="specified" else max(p.lower-value,0,value-p.upper)
            if delta>1e-7:differences.append(k)
            distance+=(delta/(ranges[k] or 1.))**2
        ranked.append({**row,"retrieval_distance":math.sqrt(distance),"condition_differences":differences,
                       "compatibility":"COMPARABLE_REGIME" if gravity_match else "DIFFERENT_GRAVITY_CONTEXT"})
    return sorted(ranked,key=lambda r:(r["compatibility"]!="COMPARABLE_REGIME",r["retrieval_distance"],r["psi_id"],str(r["test_id"]),r["id"]))


def source_evidence(row, role):
    facts=[{"parameter":row["parameter"],"value":row["value"],"unit":row["unit"],"subtype":row.get("subtype"),"kind":"reported_measurement"}]
    units={"o2_initial_pct":"%","pressure_psi":"psi","gravity_g":"g","diameter_mm":"mm","thickness_mm":"mm","width_cm":"cm",
           "flow_velocity_initial_cm_s":"cm/s","co2_diluent_pct":"%","he_diluent_pct":"%","n2_diluent_pct":"%","ambient_temp_k":"K"}
    for key,unit in units.items():
        value=finite(row["conditions"].get(key))
        if value is not None:facts.append({"parameter":key,"value":value,"unit":unit,"kind":"recorded_condition"})
    return {**row["source"],"test_id":row["test_id"],"context_role":role,"facts":facts,
            "compatibility":row.get("compatibility","DIRECT_MATCH"),"condition_differences":row.get("condition_differences",[])}
