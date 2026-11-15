"""Three scientific tasks, one question, one primary answer and figure."""
import os
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import DB_PATH, RAW_DATA_DIR
from scientific.archive import load_archive
from scientific.cache import AssessmentCache
from scientific.intelligence import ENVIRONMENTS, PILLARS, ScientificRequest, answer_question, relevant_targets
from scientific.materials import Parameter
from scientific.labels import name
from si.gemini_client import GeminiClient
from ui.design import chart, conclusion, metric_row, page_header, section


@st.cache_data(max_entries=2, ttl=60)
def archive_snapshot(signature):
    return load_archive()


def current_archive():
    signature = (DB_PATH.stat().st_mtime_ns, tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in RAW_DATA_DIR.rglob("*") if p.is_file()))
    return archive_snapshot(signature)


def physical_input(key, label, categorical=None):
    state = st.selectbox(label, ["ANY", "UNKNOWN", "SPECIFIED", "RANGE"] if categorical is None else ["ANY", "UNKNOWN", "SPECIFIED"], key="si_state_"+key)
    if state == "SPECIFIED":
        value = st.selectbox(label+" value", categorical, key="si_value_"+key) if categorical else st.number_input(label+" value", value=None, min_value=0., key="si_value_"+key)
        return Parameter(state="specified",value=value) if value is not None else Parameter(state="unknown")
    if state == "RANGE":
        lower = st.number_input(label+" minimum",value=None,min_value=0.,key="si_low_"+key)
        upper = st.number_input(label+" maximum",value=None,min_value=0.,key="si_high_"+key)
        return Parameter(state="range",lower=lower,upper=upper) if lower is not None and upper is not None else Parameter(state="unknown")
    return Parameter.model_validate({"state":state.lower()})


def apply_environment():
    for key,value in ENVIRONMENTS[st.session_state.si_mission].items():
        # Explicit action fills only unrestricted conditions; user values and unknowns survive.
        if st.session_state.get("si_state_"+key,"ANY") == "ANY":
            st.session_state["si_state_"+key] = "SPECIFIED"
            st.session_state["si_value_"+key] = value


def load_record():
    archive = current_archive()
    uid = st.session_state.si_reference
    run = next(r for r in archive["runs"].values() if f"{r['psi_id']}:{r['test_id']}" == uid)
    st.session_state.si_materials = [run["material_name"]]
    for key in list(st.session_state):
        if key.startswith("si_state_"): st.session_state[key]="ANY"
    keys = ["o2_initial_pct","pressure_psi","gravity_g","flow_velocity_initial_cm_s","diameter_mm","thickness_mm","width_cm","geometry","flow_direction","fuel_phase"]
    values = {**run,"gravity_g":{"0g":0.,"1g":1.}.get(run.get("gravity_level"))}
    for key in keys:
        if values.get(key) is not None:
            st.session_state["si_state_"+key]="SPECIFIED"
            value=values[key]
            st.session_state["si_value_"+key]=float(value) if isinstance(value,(int,float)) else value
        else:
            st.session_state["si_state_"+key]="UNKNOWN"
    st.session_state.si_reference_loaded=uid


def clear_reference():
    st.session_state.pop("si_reference_loaded",None)


def build_figure(result):
    observed = next((r for r in result["results"] if r.get("values") and r.get("value_type")=="exact"), None)
    if observed is None:
        estimated=[r for r in result["results"] if r["status"] in ("INTERPOLATED","ML_PREDICTED") and r.get("value") is not None]
        if not estimated:return None
        target=estimated[0]
        fig=go.Figure()
        for r in estimated:
            if (r["parameter"],r["unit"])!=(target["parameter"],target["unit"]):continue
            interval=r.get("interval")
            fig.add_trace(go.Scatter(x=[r["material"]],y=[r["value"]],mode="markers",name=r["status"],
                error_y=dict(type="data",symmetric=False,array=[interval[1]-r["value"]],arrayminus=[r["value"]-interval[0]]) if interval else None,
                text=[r.get("model_version") or "Reviewed interpolation"]))
        fig.update_layout(xaxis_title="Material / fuel",yaxis_title=f"{name(target['parameter'])} ({target['unit']})")
        return fig
    # One definition, statistic and apparatus per chart. Never draw a continuous inferred curve.
    groups = [r for r in result["results"] if (r["parameter"],r.get("subtype"),r.get("unit"),r.get("psi_id")) ==
        (observed["parameter"],observed.get("subtype"),observed.get("unit"),observed.get("psi_id"))]
    frame = pd.DataFrame([{"Material / fuel":r["material"] or "Reported aggregate", "Value":v,
        "Evidence":r["status"],"Investigation":r["psi_id"],"Source":sid,"Definition":r["subtype"]}
        for r in groups for v,sid in zip(r["values"],r["evidence_ids"])])
    return px.strip(frame,x="Material / fuel",y="Value",color="Evidence",hover_data=["Investigation","Source","Definition"],
        labels={"Value":f"{name(observed['parameter'])} ({observed['unit']})"})


def render_result(result):
    section(result["route"].replace("_"," ")+" / scientific answer")
    conclusion(result["answer"])
    st.caption(result["synthesis_status"] + (f" · Original route: {result['origin_route']}" if result["route"]=="CACHED" else ""))
    if result.get("synthesis_error"):
        with st.expander("Gemini response details"):
            st.text(result["synthesis_error"])
    indicators=[]
    for r in result["results"][:4]:
        if r.get("values"):
            value=f"{r['minimum']:g}–{r['maximum']:g}" if r["minimum"]!=r["maximum"] else f"{r['minimum']:g}"
        elif r.get("value") is not None: value=f"{r['value']:g}"
        else: continue
        definition=(r.get('subtype') or r['status']).replace('_',' ').lower()
        indicators.append((f"{name(r['parameter'])} · {definition}", value+" "+(r.get("unit") or "")))
    metric_row(indicators)
    fig=build_figure(result)
    if fig is not None:
        chart(fig,"Source-backed observations within one physical measurement definition",height=410)
    else:
        st.info("No compatible numerical distribution is available. Inspect the related research below.")
    section("Sources / evidence classification")
    for inv in result["ranking"][:3]:
        st.markdown(f"**{inv['acronym']} · {inv['psi_id']}** — {inv['title']}")
        statuses=sorted({r["status"] for r in result["results"] if r.get("psi_id")==inv["psi_id"]}) or ["EVIDENCE_ONLY"]
        st.caption(f"{' / '.join(statuses)} · Research relevance {inv['relevance']:g}/100; relevance is not hazard.")
        if inv.get("doi"):st.link_button("Original investigation ↗", "https://doi.org/"+inv["doi"].removeprefix("https://doi.org/"))
    if result["results"]:
        with st.expander("Experimental results and comparisons"):
            st.dataframe(pd.DataFrame([{k:v for k,v in r.items() if k not in ('values','evidence','evidence_ids')} for r in result["results"]]),hide_index=True,
                alt="Results retain separate materials, measurement definitions, statistics and evidence statuses")
            st.caption("Side-by-side research evidence does not establish a controlled material comparison or a universal winner.")
    if result.get("interpretation"):
        with st.expander("Detailed scientific explanation"):
            for claim in result["interpretation"]["interpretations"]: st.write(claim["text"])
    with st.expander("Scientific limitations, model reliability and research gaps"):
        for line in result["limitations"]: st.write("• "+line)
        st.caption("Research-only models are withheld. Missing required features and unsupported joint domains prevent predictions.")
    if result["related"] or result["findings"]:
        with st.expander("Related experimental evidence and reported findings"):
            st.dataframe(pd.DataFrame([{k:v for k,v in r.items() if k!='source'} for r in result["related"]]),hide_index=True,alt="Related evidence may not match requested conditions")
            for f in result["findings"]:
                st.write(f["claim"])
                st.caption(f"Catalog finding for source review · {f['psi_id']} · {f['source_doc']} · page {f['source_page']}")
    with st.expander("Original references"):
        for source in result["evidence"]:
            st.write(f"{source['psi_id']} · {source['source_doc']} · {source['locator']}")
            with st.expander(source["source_id"]): st.text(source["text"])
        st.caption("Dataset SHA-256: "+result["dataset_sha256"])


def render_workspace():
    page_header("Scientific questions.\nExperimental answers.","Ask about prevention, detection or suppression. Enter the conditions you know; inspect the evidence behind each answer.","04 / scientific intelligence")
    archive=current_archive()
    pillar=st.segmented_control("Scientific task",list(PILLARS),default="PREVENTION",key="si_pillar") or "PREVENTION"
    with st.expander("Scientific question and conditions",expanded=not bool(st.session_state.get("scientific_answer"))):
        defaults={"PREVENTION":"How does PMMA behave, and what evidence exists for flame propagation?",
            "DETECTION":"What smoke particle sizes are reported for Kapton?",
            "SUPPRESSION":"What evidence exists for natural flame extinction in liquid droplets?"}
        question=st.text_area("Scientific question",value=defaults[pillar],key="si_question_"+pillar,height=85,max_chars=2000)
        materials=sorted({r["material"] for r in archive["rows"] if r["material"]})
        left,right=st.columns([2,1])
        selected=left.multiselect("Materials / fuels · empty means ANY",["UNKNOWN",*materials],key="si_materials")
        mission=right.selectbox("Mission environment",list(ENVIRONMENTS),index=5,key="si_mission")
        st.button("Apply illustrative environment to unrestricted fields",key="si_environment_apply",on_click=apply_environment)
        st.caption("Mission selection alone changes no conditions. Presets are illustrative, editable research scenarios.")
        parameters={}
        keys=[("o2_initial_pct","Oxygen (%)"),("pressure_psi","Pressure (psi)"),("gravity_g","Gravity (g)"),("flow_velocity_initial_cm_s","Airflow (cm/s)")]
        primary=keys[2:] if pillar=="DETECTION" else keys
        try:
            for col,(key,label) in zip(st.columns(len(primary)),primary):
                with col: parameters[key]=physical_input(key,label)
            detector=agent=None
            if pillar=="DETECTION":
                instruments=sorted({r["instrument"] for r in archive["rows"] if r.get("instrument") and ("smoke" in r["parameter"] or "detection" in r["parameter"])})
                choice=st.selectbox("Detection / measurement technology",["ANY","UNKNOWN",*instruments],key="si_detector")
                detector=None if choice=="ANY" else choice
            if pillar=="SUPPRESSION":
                agents=[agent for agent,field in (("CO2","co2_diluent_pct"),("He","he_diluent_pct"),("N2","n2_diluent_pct")) if any((r["conditions"].get(field) or 0)>0 for r in archive["rows"])]
                choice=st.selectbox("Introduced diluent / suppression mechanism",["ANY","UNKNOWN",*agents],key="si_agent")
                agent=None if choice=="ANY" else choice
            with st.expander("Advanced conditions"):
                advanced=[*([k for k in keys if k not in primary]),("ambient_temp_k","Ambient temperature (K)"),
                    ("diameter_mm","Initial diameter (mm)"),("thickness_mm","Thickness (mm)"),("width_cm","Width (cm)")]
                if pillar=="SUPPRESSION": advanced += [("co2_diluent_pct","Introduced carbon dioxide (%)"),("he_diluent_pct","Introduced helium (%)"),("n2_diluent_pct","Introduced nitrogen (%)")]
                if pillar=="DETECTION": advanced += [("aerosol_aging_time_s","Net aerosol aging time (s)"),("mixing_time_s","Primary mixing time (s)")]
                for key,label in advanced:
                    if any(r["conditions"].get(key) is not None for r in archive["rows"]):parameters[key]=physical_input(key,label)
                for key,label in [("geometry","Sample geometry"),("flow_direction","Airflow direction"),("fuel_phase","Fuel phase")]:
                    values=sorted({r["conditions"][key] for r in archive["rows"] if r["conditions"].get(key)})
                    if values: parameters[key]=physical_input(key,label,values)
                refs=sorted({f"{r['psi_id']}:{r['test_id']}" for r in archive["rows"] if r["verified"] and r["test_id"]})
                st.selectbox("Recorded experiment",refs,index=None,key="si_reference")
                st.button("Load recorded conditions",key="si_record_load",on_click=load_record,disabled=not st.session_state.get("si_reference"))
                if st.session_state.get("si_reference_loaded"):
                    st.button("Release recorded experiment scope",key="si_record_release",on_click=clear_reference)
                st.caption("Recorded lookup retains nominal-pressure limitations. Editing conditions triggers a new applicability check.")
            query=ScientificRequest.model_validate(dict(pillar=pillar,question=question,materials=selected,mission=mission,parameters=parameters,
                detector=detector,agent=agent,reference_uid=st.session_state.get("si_reference_loaded")))
        except ValueError as exc:
            st.info(str(exc));return
        st.caption("ANY leaves retrieval unrestricted. UNKNOWN preserves missing information. Zero is a physical value; ranges are never converted to midpoints.")
        synthesis=st.checkbox("Include source-cited Gemini interpretation",value=True,key="si_synthesis")
        if st.button("Analyze scientific question",key="si_analyze",type="primary"):
            st.session_state.setdefault("scientific_assessment_cache",AssessmentCache(DB_PATH))
            client=GeminiClient(api_key=st.session_state.get("user_api_key") or os.getenv("GEMINI_API_KEY"),cache_writes=False) if synthesis else None
            with st.spinner("Assessing original evidence and scientific applicability…"):
                st.session_state.scientific_answer=answer_question(query,archive=archive,cache=st.session_state.scientific_assessment_cache,client=client)
                st.session_state.scientific_submitted=query.model_dump()
            st.rerun()
    if st.session_state.get("scientific_answer"):
        if st.session_state.scientific_submitted==query.model_dump():render_result(st.session_state.scientific_answer)
        else:st.caption("Conditions have changed. Analyze again to update the answer.")
    with st.expander("Compare experimental runs / source research tools"):
        tool=st.radio("Supporting source tool",["Experimental comparison","Document research"],key="editorial_research_tool",horizontal=True)
        if tool=="Experimental comparison":
            from ui.run_comparison import render_run_comparison
            render_run_comparison()
        else:
            from ui.source_research import render_source_research
            render_source_research()
