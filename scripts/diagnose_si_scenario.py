"""Read-only reproduction of the reported methanol SI workflow; --live also calls Gemini."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
import numpy as np

from config.settings import BASE_DIR, DB_PATH
from ml.predict import load_version
from ml.uncertainty import domain_reasons
from scientific.archive import load_archive
from scientific.intelligence import ScientificRequest, answer_question, relevant_targets
from scientific.materials import Parameter
from si.gemini_client import GeminiClient


QUESTION = "Estimate the natural extinction time of a 1.65 mm methanol droplet under these conditions using comparable FLEX experiments. Explain the uncertainty and limitations."


class RecordingClient(GeminiClient):
    def __init__(self):
        super().__init__(cache_writes=False)
        self.responses=[]

    def generate(self,*args,**kwargs):
        response=super().generate(*args,**kwargs)
        self.responses.append(response.model_dump())
        return response


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live",action="store_true")
    args=parser.parse_args()
    before=hashlib.sha256(DB_PATH.read_bytes()).hexdigest()
    archive=load_archive()
    base={"o2_initial_pct":21.,"pressure_psi":14.78,"gravity_g":0.,"flow_velocity_initial_cm_s":0.,
          "geometry":"Droplet","fuel_phase":"Liquid"}
    cases=[("screenshot","PREVENTION",{**base,"diameter_mm":16.5}),
           ("corrected_inputs","SUPPRESSION",{**base,"diameter_mm":1.65,"co2_diluent_pct":0.,"he_diluent_pct":0.,"n2_diluent_pct":79.})]
    report={"scientific_database_counts":{k:len(v) for k,v in archive["tables"].items()},"cases":[],"models":[]}
    registry=BASE_DIR/"models"/"flex_methanol_extinction_time"
    version=json.loads((registry/"latest_research.json").read_text())["version_id"]
    model,metadata,domain=load_version(registry,version,require_approved=False)
    for name,pillar,values in cases:
        query=ScientificRequest.model_validate(dict(pillar=pillar,question=QUESTION,materials=["Methanol"],
            parameters={k:Parameter(state="specified",value=v) for k,v in values.items()}))
        client=RecordingClient() if args.live else None
        result=answer_question(query,archive=archive,client=client)
        targets=relevant_targets(query,archive)
        relevant=[r for r in archive["rows"] if r["parameter"] in targets and r["material"]=="Methanol"]
        item={"name":name,"request":query.model_dump(),"selected_targets":targets,
            "route":result["route"],"matching_result_groups":len(result["results"]),
            "related_measurements":len(relevant),"verified_related_measurements":sum(r["verified"] for r in relevant),
            "evidence_sent":len(result["evidence"]),"synthesis_status":result["synthesis_status"],
            "synthesis_error":result.get("synthesis_error"),"answer":result["answer"],
            "gemini_attempts":client.responses if client else [],
            "approved_pointer_exists":(registry/"approved.json").exists(),
            "diagnostic_domain_reasons":domain_reasons(domain,values,"Methanol",values)}
        # Diagnostic only: never publish extrapolated values, and never treat this as approved inference.
        if name=="corrected_inputs" and not item["diagnostic_domain_reasons"]:
            item["research_only_artifact_point_prediction_s"]=float(model.predict(pd.DataFrame([values]))[0])
            item["prediction_note"]="Offline artifact diagnostic only; not an approved prediction and no calibrated interval is available."
        report["cases"].append(item)
        print(json.dumps({k:item[k] for k in ("name","route","synthesis_status","synthesis_error","diagnostic_domain_reasons")}),flush=True)
    for root in sorted((BASE_DIR/"models").iterdir()):
        if not (root/"latest_research.json").is_file():continue
        pointer=json.loads((root/"latest_research.json").read_text())
        m=json.loads((root/"versions"/pointer["version_id"]/"metadata.json").read_text())
        assigned=json.loads((root/"versions"/pointer["version_id"]/"assigned_observations.json").read_text())
        invalid_pressure=[{"uid":s["uid"],"role":s["role"]} for s in assigned if s["features"].get("pressure_psi",1)<=0]
        report["models"].append({"task_id":root.name,"approved_pointer_exists":(root/"approved.json").exists(),
            "nonpositive_pressure_training_records":invalid_pressure,
            **{k:m[k] for k in ("status","model","counts","evaluation","uncertainty","promotion")}})
    point_values={k:p.value for k,p in query.parameters.items()}
    order=domain["numeric_feature_order"]
    point=np.array([point_values[k] for k in order])/domain["scale"]
    report["corrected_point_local_groups"]=len({g for row,g in zip(domain["training_points"],domain["training_groups"])
        if np.linalg.norm(np.array([row[k] for k in order])/domain["scale"]-point)<=domain["neighbor_radius"]})
    control={**point_values,"diameter_mm":2.5}
    control_reasons=domain_reasons(domain,control,"Methanol",control)
    report["artifact_execution_control"]={"inputs":control,"diagnostic_domain_reasons":control_reasons,
        "raw_artifact_output_s":float(model.predict(pd.DataFrame([control]))[0]) if not control_reasons else None,
        "status":"RESEARCH_ONLY","approved_for_ui":False,"calibrated_interval":metadata["uncertainty"]["half_width"],
        "note":"Artifact execution diagnostic only; not an approved scientific estimate."}
    report["methanol_extinction_domain"]={k:domain[k] for k in ("numeric_ranges","radius_validated","min_local_groups","benchmark_domain_coverage")}
    report["database_unchanged"]=before==hashlib.sha256(DB_PATH.read_bytes()).hexdigest()
    assert report["database_unchanged"]
    output=BASE_DIR/"docs"/"SI_SCENARIO_DIAGNOSTICS.json"
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("Report:",output)


if __name__=="__main__":main()
