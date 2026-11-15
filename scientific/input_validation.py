"""Detect contradictory intent/conditions without rewriting user input."""
import math
import re


def question_pillar(question):
    q=question.casefold()
    if re.search(r"extinct|extinguish|suppression|угасан|тушени|подавлен",q):return "SUPPRESSION"
    if re.search(r"smoke|aerosol|detector|particle|дым|аэрозол|детектор|частиц",q):return "DETECTION"
    if re.search(r"ignition|flammab|flame propagation|flame spread|воспламен|горюч|распростран",q):return "PREVENTION"
    return None


def input_issues(request):
    issues=[]
    intended=question_pillar(request.question)
    if intended and intended!=request.pillar:
        issues.append({"field":"pillar","message":f"The question concerns {intended}, but {request.pillar} is selected. Select {intended} or revise the question."})
    q=request.question.casefold().replace(",", ".")
    checks=[("pressure_psi",r"(\d+(?:\.\d+)?)\s*psi",1.),
            ("pressure_psi",r"(\d+(?:\.\d+)?)\s*kpa",1/6.894757293),
            ("gravity_g",r"(\d+(?:\.\d+)?)\s*g\b",1.),
            ("flow_velocity_initial_cm_s",r"(\d+(?:\.\d+)?)\s*cm/s",1.),
            ("o2_initial_pct",r"(\d+(?:\.\d+)?)\s*%\s*(?:oxygen|o2)\b",1.),
            ("o2_initial_pct",r"(?:oxygen|o2)(?:\s+(?:concentration|level))?\s*(?:of|at|=|:)?\s*(\d+(?:\.\d+)?)\s*%",1.),
            ("ambient_temp_k",r"(\d+(?:\.\d+)?)\s*(?:k|kelvin)\b",1.)]
    if re.search(r"droplet|diameter|капл|диаметр",q):checks.append(("diameter_mm",r"(\d+(?:\.\d+)?)\s*(?:mm|мм)\b",1.))
    for field,pattern,factor in checks:
        parameter=request.parameters.get(field)
        if parameter is None or parameter.state not in ("specified","range"):continue
        for match in re.finditer(pattern,q):
            value=float(match.group(1))*factor
            agrees=(math.isclose(float(parameter.value),value,rel_tol=1e-4,abs_tol=1e-6) if parameter.state=="specified"
                    else parameter.lower<=value<=parameter.upper)
            if not agrees:issues.append({"field":field,"message":f"Question and {field} conflict: the question specifies {value:g}, but the physical input is {parameter.value if parameter.state=='specified' else [parameter.lower,parameter.upper]}. Correct one before analysis."})
    if "UNKNOWN" in request.materials and len(request.materials)>1:
        issues.append({"field":"materials","message":"Choose either UNKNOWN or named materials, rather than both."})
    gases=[request.parameters.get(k) for k in ("o2_initial_pct","co2_diluent_pct","he_diluent_pct","n2_diluent_pct")]
    if all(p is not None and p.state=="specified" for p in gases):
        if not math.isclose(sum(float(p.value) for p in gases),100.,abs_tol=.1):
            issues.append({"field":"composition","message":"Specified initial oxygen and diluent percentages must total 100%."})
    return issues
