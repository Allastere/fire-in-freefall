import pandas as pd
from typing import cast
import plotly.express as px
import streamlit as st
from ui.common import filtered_data, raw_record, table
from ui.data import CSV_BACKED, LABELS, RUN_COLUMNS, SEEDED
from ui.design import chart, page_header, section
from ui.uploads import render_uploads

investigations, runs, measurements, _ = filtered_data()
page_header("The experimental archive.", "Search recorded conditions, inspect physical measurements and follow the original scientific evidence.", "02 / database explorer")
cols = st.columns([1.2, 1.2, 2])
ids = cols[0].multiselect("Investigation series", [i["psi_id"] for i in investigations], key="explorer_ids")
materials = cols[1].multiselect("Material", sorted(runs.material_name.dropna().unique()), key="explorer_materials")
search = cols[2].text_input("Search test ID or observations", key="explorer_search")
with st.expander("Advanced filter matrix"):
    cols = st.columns(3)
    gravity = cols[0].multiselect("Gravity regime", sorted(runs.gravity_level.dropna().unique()), key="explorer_gravity")
    outcome = cols[1].multiselect("Recorded outcome", sorted(runs.outcome.dropna().unique()), key="explorer_outcomes")
    seeds = cols[2].checkbox("Include unverified catalog seeds", key="explorer_seeds")
    st.caption("Imported outcomes may be inferred. Catalog seeds and private uploads are not verified observations.")
    for key in ["o2_initial_pct", "pressure_psi", "flow_velocity_initial_cm_s"]:
        values = pd.to_numeric(runs[key], errors="coerce").dropna()
        if not values.empty and values.min() < values.max():
            low, high = float(values.min()), float(values.max())
            range_key = f"explorer_range_{key}"
            previous = st.session_state.get(range_key, (low, high))
            st.session_state[range_key] = (max(low, min(high, previous[0])), max(low, min(high, previous[1])))
            limits = cast(tuple[float, float], st.slider(LABELS[key], low, high, key=range_key))
            runs = runs[pd.to_numeric(runs[key], errors="coerce").between(*limits)]
if not seeds:
    runs = runs[runs.data_origin != SEEDED]
for key, chosen in [("psi_id", ids), ("material_name", materials), ("gravity_level", gravity), ("outcome", outcome)]:
    if chosen:
        runs = runs[runs[key].isin(chosen)]
if search:
    runs = runs[runs.test_id.str.contains(search, case=False, regex=False, na=False) |
                runs.observations.str.contains(search, case=False, regex=False, na=False)]
section(f"Figure 2.0 / {len(runs)} matching experimental runs")
st.session_state.setdefault("explorer_view", "Chart")
view = st.segmented_control("Archive view", ["Chart", "Table"], key="explorer_view")
display = runs[[c for c in RUN_COLUMNS if c not in ("raw_attributes_json", "observations")]]
if runs.empty:
    st.info("No runs match these filters. Broaden the experimental scope.")
else:
    if view == "Table":
        table(display, alt="Filtered experimental archive")
    else:
        axes = ["o2_initial_pct", "o2_final_pct", "flow_velocity_initial_cm_s", "flow_velocity_min_cm_s", "pressure_psi"]
        cols = st.columns(2)
        x = cols[0].selectbox("Horizontal characteristic", axes, format_func=LABELS.__getitem__, key="explorer_x")
        st.session_state.setdefault("explorer_y", axes[2])
        y = cols[1].selectbox("Vertical characteristic", axes, format_func=LABELS.__getitem__, key="explorer_y")
        chart(px.scatter(runs.dropna(subset=list({x,y})), x=x, y=y, color="material_name", symbol="outcome",
            hover_name="test_id", labels={**LABELS, "material_name":"Material", "outcome":"Recorded outcome"}),
            "Stored experimental conditions; inferred outcomes are identified separately", height=430)
    st.download_button("Download filtered runs", runs.to_csv(index=False).encode(), "filtered_runs.csv", "text/csv", key="export_runs")
    with st.expander("Active inspector / measurements and original record"):
        selected = st.selectbox("Inspect a run", runs.test_id.tolist(), key="explorer_run")
        row = runs[runs.test_id == selected].iloc[0]
        st.caption(row["data_origin"])
        raw_record(row)
        st.write(row.get("observations") or "No recorded observations.")
        frame = measurements[(measurements.test_id == selected) & (measurements.psi_id == row["psi_id"])]
        if not frame.empty:
            table(frame[["parameter", "value", "unit", "value_type", "subtype", "statistic_type", "instrument", "eligibility_status", "source_doc", "verification_status"]], alt="Stored physical measurements and their scientific definitions")
        else:
            st.caption("No stored sensor measurements.")
    with st.expander("Complete experimental table"):
        table(display, alt="Full table underlying the archive figure")
    if st.button("Send filtered runs to SI Insights", key="explorer_send"):
        st.session_state.compare_runs = runs.test_id.head(20).tolist()
        st.session_state.editorial_research_tool = "Run comparison"
        st.switch_page("app_pages/5_SI_Insights.py")
render_uploads()
