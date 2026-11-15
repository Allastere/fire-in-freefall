import pandas as pd
import plotly.express as px
import streamlit as st
from ui.common import attribution, filtered_data, source_files
from ui.data import CSV_BACKED
from ui.design import chart, metric_row, page_header, section

investigations, runs, measurements, findings = filtered_data(include_uploads=False)
page_header("Combustion in\nmicrogravity.", "An experimental research archive for understanding material behaviour, environmental applicability and scientific knowledge gaps.", "01 / editorial research index")
st.page_link("app_pages/5_SI_Insights.py", label="Run a material assessment →")
metric_row([("Investigation series", len(investigations)), ("Experimental runs", len(runs)), ("Materials in catalog", runs.material_name.nunique())])
section("Figure 1.0 / experimental landscape")
scope = runs[runs.data_origin == CSV_BACKED]
characteristic = st.selectbox("Landscape characteristic", ["Oxygen and airflow", "Oxygen and nominal pressure"], key="editorial_overview_figure")
if not scope.empty:
    y = "flow_velocity_initial_cm_s" if characteristic == "Oxygen and airflow" else "pressure_psi"
    fig = px.scatter(scope.dropna(subset=["o2_initial_pct", y]), x="o2_initial_pct", y=y,
        color="material_name", symbol="gravity_level", hover_name="test_id",
        labels={"o2_initial_pct": "Initial oxygen (%)", y: "Initial airflow (cm/s)" if y.startswith("flow") else "Nominal pressure (psi)",
                "material_name": "Material", "gravity_level": "Gravity"})
    fig.update_traces(marker_size=8)
    chart(fig, "Recorded experimental conditions; no inferred extinction boundary", height=410)
    st.caption("Source-backed conditions. Nominal pressure and imported outcome labels are not independently measured safety limits.")
else:
    st.info("No source-backed experimental records in this scope.")
section("Table 1.1 / investigation series index")
for inv in investigations:
    columns = st.columns([1.1, 3, 1, 1])
    columns[0].write(f"**{inv['acronym']}**")
    columns[0].caption(inv["psi_id"])
    columns[1].write(inv["title"])
    columns[1].caption(inv["hardware_facility"] + " / " + inv["safety_pillar"])
    columns[2].write(f"{int((runs.psi_id == inv['psi_id']).sum())} runs")
    if columns[3].button("Inspect →", key=f"overview_inspect_{inv['psi_id']}"):
        st.session_state.explorer_ids = [inv["psi_id"]]
        st.switch_page("app_pages/2_Explorer.py")
    with st.expander(f"Sources and scientific context / {inv['acronym']}"):
        st.write(inv.get("summary") or "A source summary is unavailable.")
        attribution(inv)
        st.code(inv.get("citation_text") or "Use the original NASA citation.", language=None)
        source_files(inv, "overview")
        for finding in [f for f in findings if f["psi_id"] == inv["psi_id"]]:
            st.write(finding["claim"])
            st.caption("Catalog finding; verify against the original document.")
        if st.session_state.get("show_spinoffs"):
            st.write(inv.get("earth_spinoff_text") or "No documented Earth spin-off.")
