"""Automatic registry selection with separate approved and exploratory inference policies."""
import json
import re
from pathlib import Path

from ml.predict import assess, assess_research
from scientific.evidence import equal


def predict_targets(request, targets, models_dir):
    estimates,diagnostics=[],[]
    for root in sorted(Path(models_dir).glob("*")):
        approved=(root/"approved.json").is_file()
        pointer=root/("approved.json" if approved else "latest_research.json")
        if not pointer.is_file():continue
        try:
            version=json.loads(pointer.read_text())["version_id"]
            if not re.fullmatch(r"[0-9a-f]{64}",version):raise ValueError("Invalid registry version.")
            metadata=json.loads((root/"versions"/version/"metadata.json").read_text())
            task=metadata["task"]
            material=task["filters"]["material_name"]
            if task["target"] not in targets or material not in request.materials:continue
            diagnostic={"task_id":root.name,"target":task["target"],"material":material,"status":"BLOCKED",
                "model_version":version,"inference_level":"VALIDATED" if approved else "RESEARCH_ONLY","reasons":[]}
            diagnostics.append(diagnostic)
            if not approved and not task.get("research_inference",{}).get("enabled"):
                diagnostic["reasons"]=["No approved model and no explicitly enabled research-inference policy."];continue
            regime=task.get("inference_categories",{"geometry":task["filters"].get("geometry")})
            needed=set(task["numeric_features"]+task["categorical_features"]+list(task["constant_conditions"])+list(regime))
            missing=[k for k in sorted(needed) if k not in request.parameters or request.parameters[k].state!="specified"]
            if missing:
                diagnostic["reasons"]=["Required initial feature is missing or not exact: "+k for k in missing];continue
            supplied={k:p.value for k,p in request.parameters.items() if p.state=="specified"}
            mismatch=[k for k,v in regime.items() if not equal(supplied.get(k),v)]
            if mismatch:
                diagnostic["reasons"]=["Unsupported physical regime: "+k for k in mismatch];continue
            extra=[k for k,p in request.parameters.items() if p.state=="range" or (p.state=="specified" and k not in needed)]
            if extra:
                diagnostic["reasons"]=["A point model cannot validate this additional or range constraint: "+k for k in extra];continue
            prediction=(assess if approved else assess_research)(root.name,supplied,material,supplied,models_dir)
            diagnostic["reasons"]=prediction.get("reasons",[])
            if prediction["status"]=="INSUFFICIENT_DATA":continue
            diagnostic["status"]="PREDICTED"
            level=diagnostic["inference_level"]
            if level=="RESEARCH_ONLY":prediction["value"]=float(f"{prediction['value']:.3g}")
            source={"source_id":f"model:{root.name}:{version}","psi_id":"Local model","source_doc":root.name,
                "locator":"Model artifact version "+version,"context_role":"MODEL_ESTIMATE",
                "facts":[{"parameter":task["target"],"value":prediction["value"],"unit":prediction["unit"],"kind":"model_estimate"},
                    *[{"parameter":k,"value":v,"kind":"requested_condition"} for k,v in supplied.items() if isinstance(v,(int,float))]],
                "text":json.dumps({"task":root.name,"model_version":version,"evidence_type":"ML_PREDICTED",
                    "inference_level":level,"value":prediction["value"],"unit":prediction["unit"],
                    "prediction_interval":prediction.get("interval"),"initial_conditions":supplied,
                    "limitations":prediction.get("limitations",[])},sort_keys=True)}
            estimates.append({"parameter":task["target"],"material":material,"status":"ML_PREDICTED",
                "inference_level":level,"value":prediction["value"],"unit":prediction["unit"],
                "interval":prediction.get("interval"),"model_version":version,
                "dataset_sha256":prediction.get("dataset_sha256"),"evidence":[{"source":source}],
                "limitations":prediction.get("limitations",[]),"calibration_plan":prediction.get("calibration_plan")})
        except (OSError,ValueError,KeyError) as exc:
            diagnostics.append({"task_id":root.name,"status":"BLOCKED","reasons":["Model cannot be validated: "+str(exc)]})
    return estimates,diagnostics
