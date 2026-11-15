"""Editorial material assessment workspace and on-demand scientific dossiers."""

import json
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.settings import DB_PATH, MISSION_PROFILES, RAW_DATA_DIR
from scientific.evidence import load_evidence
from scientific.labels import UNITS, name
from scientific.materials import MODES, MaterialAssessment, MaterialQuery, Parameter, assess_materials, discover_targets
from scientific.synthesis import synthesize
from si.gemini_client import GeminiClient
from ui.common import catalog, get_sources
from ui.design import chart, conclusion, metric_row, page_header, section

STATES = {"Any": "any", "Unknown": "unknown", "Specified": "specified", "Range": "range"}
MAIN = ["o2_initial_pct", "pressure_psi", "gravity_g", "flow_velocity_initial_cm_s"]
ADVANCED = ["geometry", "flow_direction", "thickness_mm", "width_cm", "diameter_mm", "burn_sides",
            "co2_initial_pct", "is_reused_sample", "flow_sequence_raw"]


@st.cache_data(ttl=60, max_entries=3)
def reference_records(signature):
    records = {}
    # Discover evidence-bearing targets instead of relying on the current investigation list.
    for target in discover_targets():
        try:
            for record in load_evidence(DB_PATH, RAW_DATA_DIR, target)[0]:
                records.setdefault(record["uid"], record)
        except Exception:
            pass
    return records


def recorded_scope(records):
    uid = st.session_state.get("editorial_reference")
    if uid not in records:
        return
    record = records[uid]
    st.session_state.editorial_materials = [record["features"]["material_name"]]
    st.session_state.material_reference_uid = uid
    for field in MAIN + ADVANCED:
        value = record["features"].get(field)
        st.session_state[f"editorial_state_{field}"] = "Unknown" if value is None else "Specified"
        st.session_state[f"editorial_value_{field}"] = value
    st.session_state.material_result = None


def mission_scope():
    profile = MISSION_PROFILES[st.session_state.editorial_mission]
    for field, value in {"o2_initial_pct": profile["target_o2_pct"], "pressure_psi": profile["target_pressure_psi"],
                         "gravity_g": profile["gravity_g"]}.items():
        st.session_state[f"editorial_state_{field}"] = "Specified"
        st.session_state[f"editorial_value_{field}"] = value
    st.session_state.material_result = None


def parameter_control(field):
    numeric = field in UNITS
    label = name(field) + (f" ({UNITS[field]})" if numeric else "")
    st.caption(label)
    state_key = f"editorial_state_{field}"
    st.session_state.setdefault(state_key, "Any" if field in MAIN else "Unknown")
    state = st.selectbox(f"{name(field)} input type", list(STATES) if numeric else list(STATES)[:3],
                         key=state_key, label_visibility="collapsed")
    if state in ("Any", "Unknown"):
        return Parameter.model_validate({"state": STATES[state]})
    key = f"editorial_value_{field}"
    if state == "Range":
        cols = st.columns(2)
        low = cols[0].number_input(f"{name(field)} minimum", value=None, key=f"editorial_low_{field}")
        high = cols[1].number_input(f"{name(field)} maximum", value=None, key=f"editorial_high_{field}")
        return {"state": "range", "lower": low, "upper": high}
    if numeric:
        value = st.number_input(label, value=None, key=key, label_visibility="collapsed", format="%.4f")
    elif field == "is_reused_sample":
        st.session_state.setdefault(key, False)
        value = st.checkbox("Specimen has been reused", key=key)
    else:
        value = st.text_input(label, key=key, label_visibility="collapsed")
    return {"state": "specified", "value": value}


def render_characteristic_chart(characteristic, material=None, oxygen=None, predictions=None):
    if not characteristic.evidence:
        st.caption("No source-verified observations are available for this characteristic.")
        return
    rows = []
    for item in characteristic.evidence:
        rows.append({"Material": item.get("material", material), "Test": item["uid"],
                     "Initial oxygen (%)": item["conditions"].get("o2_initial_pct"),
                     "Value": item["value"], "Unit": item["unit"],
                     "Geometry": item["conditions"].get("geometry"), "Gravity (g)": item["conditions"].get("gravity_g")})
    frame = pd.DataFrame(rows)
    units = frame.Unit.unique()
    unit = st.selectbox("Measurement unit", list(units), key="editorial_chart_unit") if len(units) > 1 else units[0]
    frame = frame[frame.Unit == unit]
    fig = px.scatter(frame, x="Initial oxygen (%)", y="Value", color="Material", symbol="Geometry", hover_name="Test",
                     hover_data=["Gravity (g)", "Geometry"], labels={"Value": f"{characteristic.display_name} ({unit})"})
    fig.update_traces(marker_size=9)
    if frame.Value.min() >= 0:
        fig.update_yaxes(rangemode="nonnegative")
    for estimate in predictions if predictions is not None else [characteristic]:
        if estimate.status not in ("PREDICTED", "INTERPOLATED") or estimate.value is None or estimate.unit != unit:
            continue
        interval = estimate.prediction_interval
        label = estimate.evidence[0].get("material", "") if estimate.evidence else ""
        fig.add_trace(go.Scatter(x=[oxygen], y=[estimate.value], mode="markers", name=f"{label} / {estimate.status.title()}",
            marker=dict(color="#C88A60", symbol="diamond", size=12),
            error_y=dict(type="data", symmetric=False, array=[interval[1]-estimate.value],
                         arrayminus=[estimate.value-interval[0]], color="#7B9DB8") if interval else None))
    chart(fig, "Recorded observations grouped by material and geometry; no fitted response curve", height=430)
    st.caption("Individual source observations. Different geometry, gravity, apparatus or airflow does not establish a controlled material comparison.")


def result_view(result):
    title = ", ".join(r.material for r in result.reports) or "No matching material records"
    section("Scientific assessment / " + title)
    conclusion(result.conclusion)
    requested = []
    for field in MAIN:
        parameter = result.query.parameters.get(field)
        if parameter and parameter.state == "specified":
            requested.append(f"{name(field)} {parameter.value} {UNITS.get(field, '')}")
        elif parameter and parameter.state == "range":
            requested.append(f"{name(field)} {parameter.lower}–{parameter.upper} {UNITS.get(field, '')}")
    st.caption("Requested conditions / " + (" / ".join(requested) if requested else "Unrestricted or unknown; see the submitted parameter states."))
    st.caption("Quantitative measurement uncertainty is unavailable in the source CSV. Nominal pressure is source metadata, not a measured pressure condition.")
    if result.synthesis_status.startswith("Gemini"):
        st.caption(result.synthesis_status)
    characteristics = [c for report in result.reports for c in report.characteristics]
    available = [c for c in characteristics if c.status != "UNAVAILABLE"]
    if not result.reports:
        st.info("No material records match this request. Broaden the conditions or inspect the archive.")
        return
    if not available:
        st.caption("No directly applicable numerical result is available. The figure shows related source records under different conditions; it is not a prediction for the requested environment.")
    if result.query.mode == "Find Materials":
        entries = [{"Material": r.material, "Evidence": "Recorded observations" if any(c.status != "UNAVAILABLE" for c in r.characteristics) else "Related records only",
                    "Conclusion": r.conclusion} for r in result.reports]
        st.dataframe(pd.DataFrame(entries), hide_index=True, width="stretch", alt="Research candidates, without an unsupported safety ranking")
        st.caption("Research candidates only. Evidence availability is not a material suitability score; no universal winner is assigned.")
    elif result.query.mode != "Compare Materials":
        featured = sorted([c for c in available if "initial" not in c.parameter] or available, key=lambda c: c.parameter)[:4]
        short_names = {"co2_final_pct": "Final CO₂", "co_final_ppm": "Final CO", "o2_final_calibrated_pct": "Final O₂"}
        metric_row([(f"{short_names.get(c.parameter, c.display_name)} / {c.status.lower()}",
                     f"{c.value:g} {c.unit}" if c.value is not None else
                     f"{c.observed_range[0]:g}–{c.observed_range[1]:g} {c.unit}" if c.observed_range else "Unavailable") for c in featured])
        for c in featured:
            if c.prediction_interval:
                st.caption(f"{c.display_name}: prediction interval {c.prediction_interval[0]:g}–{c.prediction_interval[1]:g} {c.unit}.")
        if any("Conditional" in c.relation for c in featured):
            st.caption("Conditional observations: unspecified conditions vary. Observed ranges are not predictions or uncertainty intervals.")
    keys = sorted({c.parameter for c in characteristics if c.evidence})
    if keys:
        key = st.selectbox("Figure / scientific characteristic", keys, format_func=name, key="editorial_characteristic")
        if result.query.mode == "Compare Materials":
            entries = []
            for report in result.reports:
                c = next((c for c in report.characteristics if c.parameter == key), None)
                entries.append({"Material": report.material, "Characteristic": name(key), "Value": c.value if c else None,
                    "Observed range": str(c.observed_range) if c and c.observed_range else None, "Unit": c.unit if c else None,
                    "Method": c.status.title() if c else "Unavailable", "Prediction interval": str(c.prediction_interval) if c and c.prediction_interval else None,
                    "Applicability": c.relation if c else "No measurement"})
            st.dataframe(pd.DataFrame(entries), hide_index=True, width="stretch", alt="Material comparison for the selected scientific characteristic")
        chosen = [c for c in characteristics if c.parameter == key and c.evidence]
        selected = chosen[0].model_copy(deep=True)
        selected.evidence = [item for c in chosen for item in c.evidence]
        oxygen = result.query.parameters.get("o2_initial_pct")
        render_characteristic_chart(selected, oxygen=oxygen.value if oxygen and oxygen.state == "specified" else None, predictions=chosen)
        if len(result.reports) > 1:
            comparison = next((c for c in result.comparison if c["parameter"] == key), None)
            if comparison:
                st.caption(comparison["conclusion"])
    section("Evidence on demand")
    with st.expander("All combustion characteristics"):
        st.dataframe(pd.DataFrame([{"Material": report.material, "Characteristic": c.display_name, "Method": c.status.title(),
            "Applicability": c.relation, "Value": c.value, "Observed range": str(c.observed_range) if c.observed_range else None,
            "Unit": c.unit, "Prediction interval": str(c.prediction_interval) if c.prediction_interval else None}
            for report in result.reports for c in report.characteristics]), hide_index=True, width="stretch", alt="All independently assessed combustion characteristics")
    if result.synthesis:
        with st.expander("Full scientific interpretation"):
            from ui.scientific_narrative import render_narrative
            render_narrative(result.synthesis, result.sources)
    evidence = [dict(Material=r.material, **o) for r in result.reports for c in r.characteristics for o in c.evidence]
    if evidence:
        with st.expander("Experimental evidence and comparability"):
            st.dataframe(pd.DataFrame([{"Material": o["Material"], "Experiment": o["uid"], "Value": o["value"], "Unit": o["unit"],
                "Source": o["source"]["source_doc"], "Location": o["source"]["locator"]} for o in evidence]).drop_duplicates(),
                hide_index=True, width="stretch", alt="Original experimental evidence and source locations")
            for report in result.reports:
                for finding in report.qualitative_evidence:
                    st.write(finding["claim"])
                    st.caption(f"Catalog finding / {finding['psi_id']} / {finding.get('source_doc') or 'Source not supplied'}. Verify the quotation in the original document; not a material-specific measured value.")
                for c in report.characteristics:
                    if len(c.groups) > 1:
                        st.write(f"{report.material} / {c.display_name}: {len(c.groups)} physical-condition groups; no pooled average.")
    with st.expander("Scientific limitations and missing information"):
        for limitation in result.limitations:
            st.write(limitation)
        for limitation in sorted({limitation for report in result.reports for c in report.characteristics for limitation in c.limitations}):
            st.write(limitation)
        for report in result.reports:
            for c in report.characteristics:
                if c.missing_features:
                    st.caption(f"{report.material} / {c.display_name}: numerical estimation needs " + ", ".join(name(k) for k in c.missing_features))
    models = [c.numerical_result for c in characteristics if c.numerical_result and c.numerical_result.get("model_diagnostics")]
    if models:
        with st.expander("Model reliability and uncertainty"):
            for model in models:
                diagnostics = model["model_diagnostics"]
                st.write(f"{name(model['target'])}: {diagnostics['status']}")
                st.caption("Model-level validation errors are distinct from the uncertainty of any individual prediction.")
                st.json(diagnostics)
    if result.synthesis and result.synthesis.get("proposed_investigation"):
        with st.expander("Recommended experiments"):
            st.caption("SI-generated research proposal — not an existing NASA result or a validated safe protocol.")
            st.json(result.synthesis["proposed_investigation"])
    if result.sources:
        with st.expander("NASA source references"):
            refs = {(s["psi_id"], s.get("doi"), s["source_doc"]) for s in result.sources}
            for pid, doi, document in sorted(refs, key=str):
                st.write(f"{pid} / {document}")
                st.markdown("[NASA PSI](https://psi.nasa.gov/)" + (f" · [DOI: {doi}](https://doi.org/{doi})" if doi else ""))
    with st.expander("Technical diagnostics and export"):
        st.json(result.query.model_dump())
        st.json([{ "material": report.material, "target": c.parameter, "missing_features": c.missing_features,
                  "domain_assessment": c.numerical_result.get("domain_assessment") if c.numerical_result else None}
                 for report in result.reports for c in report.characteristics])
        st.download_button("Download material assessment", result.model_dump_json(indent=2), "material_assessment.json", "application/json", key="editorial_assessment_download")


def render_workspace():
    st.session_state.setdefault("editorial_mode", "Assess Material")
    mode = st.segmented_control("Assessment mode", MODES, key="editorial_mode", label_visibility="collapsed") or "Assess Material"
    if not st.session_state.get("material_result"):
        page_header("Material evidence. Scientific judgement.", "Understand combustion behaviour under the conditions that matter to your research.", "04 / scientific intelligence")
    with st.expander("Configure material and environment", expanded=not bool(st.session_state.get("material_result")),
                     key=f"editorial_configuration_{st.session_state.get('material_result_version', 0)}"):
        _, runs, _, _ = catalog()
        materials = sorted(runs.material_name.dropna().unique())
        st.session_state.setdefault("editorial_materials", ["PMMA"] if "PMMA" in materials else materials[:1])
        top = st.columns([2, 1.3, 2])
        if mode != "Find Materials":
            top[0].multiselect("Material scope", materials, key="editorial_materials", accept_new_options=True)
        else:
            top[0].caption("Candidates are discovered from the experimental archive.")
        mission = top[1].selectbox("Mission reference", list(MISSION_PROFILES), key="editorial_mission")
        application = top[2].text_input("Intended application (optional)", key="editorial_application", placeholder="e.g. cabin interior material")
        if mode == "Predict Parameter":
            targets = discover_targets()
            if st.session_state.get("editorial_target") not in targets:
                st.session_state.editorial_target = "co2_final_pct" if "co2_final_pct" in targets else next(iter(targets), None)
            st.selectbox("Physical characteristic", targets, format_func=name, key="editorial_target")
        criterion = None
        if mode in ("Find Materials", "Compare Materials"):
            criterion = st.selectbox("Research selection criterion (optional)", [None, "flame_spread_rate_mm_s", "hrr_watts", "limiting_oxygen_index_pct"],
                format_func=lambda key: "Evidence scope only — no safety ranking" if key is None else name(key), key="editorial_criterion")
        parameters = {}
        for column, field in zip(st.columns(4), MAIN):
            with column:
                parameters[field] = parameter_control(field)
        st.caption("Any searches across recorded values. Unknown preserves missing physical information. Ranges filter evidence; they are never converted to prediction midpoints.")
        with st.expander("Advanced conditions"):
            columns = st.columns(3)
            for index, field in enumerate(ADVANCED):
                with columns[index % 3]:
                    parameters[field] = parameter_control(field)
        signature = (DB_PATH.stat().st_mtime_ns, tuple((str(p), p.stat().st_mtime_ns) for p in sorted(RAW_DATA_DIR.glob("*/*.csv"))))
        with st.expander("Use a recorded experiment or mission environment"):
            records = reference_records(signature)
            st.selectbox("Recorded experiment", [None, *records], format_func=lambda uid: uid or "Choose a source-verified experiment", key="editorial_reference")
            st.button("Load recorded conditions", key="editorial_record_load", on_click=recorded_scope, args=(records,), disabled=not st.session_state.editorial_reference)
            st.button("Replace environment with mission reference", key="editorial_mission_apply", on_click=mission_scope)
            st.caption("Loading a record preserves nominal versus measured conditions. Replacing its environment removes an exact match when the physical values change.")
        reference_uid = st.session_state.get("material_reference_uid")
        if reference_uid:
            st.caption(f"Recorded context: {reference_uid}. Submitted conditions are reassessed; a mission reference is never applied automatically.")
        try:
            query = MaterialQuery.model_validate(dict(mode=mode, materials=[] if mode == "Find Materials" else st.session_state.editorial_materials,
                application=application, mission=mission, parameters=parameters,
                target=st.session_state.get("editorial_target") if mode == "Predict Parameter" else None,
                reference_uid=reference_uid if mode not in ("Find Materials", "Compare Materials") else None, criterion=criterion))
        except ValueError:
            query = None
            st.caption("Choose one material for assessment/prediction and complete specified values or range bounds; use Any / Unknown for missing conditions.")
        request_synthesis = st.checkbox("Include Gemini scientific synthesis", value=False, key="editorial_synthesis")
        if st.button("Run assessment", type="primary", key="editorial_assessment_submit", disabled=query is None) and query is not None:
            if query.mode != "Find Materials" and not query.materials:
                st.info("Choose at least one material.")
            elif query.mode == "Compare Materials" and len(query.materials) < 2:
                st.info("Choose two or more materials for comparison.")
            else:
                with st.spinner("Reading experimental evidence and checking scientific applicability…"):
                    result = assess_materials(query)
                if request_synthesis:
                    with st.spinner("Synthesizing the fixed scientific evidence…"):
                        try:
                            from si.insights import select_evidence
                            ids = {s["psi_id"] for s in result.sources}
                            documents = [s for inv in catalog()[0] if inv["psi_id"] in ids for s in get_sources(inv)]
                            tests = [o["test_id"] for report in result.reports for c in report.characteristics for o in c.evidence]
                            chosen = select_evidence(documents, " ".join(query.materials) + " " + query.application + " combustion flame oxygen gravity", tests)
                            result.sources = list({s["source_id"]: s for s in chosen + result.sources}.values())
                        except (OSError, ValueError):
                            pass
                        result = synthesize(result, GeminiClient(api_key=st.session_state.get("user_api_key"), cache_writes=False),
                                            response_cache=st.session_state.insight_cache)
                st.session_state.material_result = result.model_dump()
                st.session_state.material_result_version = st.session_state.get("material_result_version", 0) + 1
                st.rerun()
    saved = st.session_state.get("material_result")
    if saved:
        result = MaterialAssessment.model_validate(saved)
        if query is None or result.query != query:
            st.caption("Conditions have changed. Run assessment again to update the report.")
        else:
            result_view(result)
    with st.expander("Compare experimental runs / source research tools"):
        tool = st.radio("Research tool", ["Run comparison", "Document research"], horizontal=True, key="editorial_research_tool")
        if tool == "Run comparison":
            from ui.run_comparison import render_run_comparison
            render_run_comparison()
        else:
            from ui.source_research import render_source_research
            render_source_research()
