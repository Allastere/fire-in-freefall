import pandas as pd
import plotly.express as px
import streamlit as st

from ui.common import data_note, filtered_data, table
from ui.data import LABELS, SEEDED
from ui.design import chart, metric_row, page_header, section



def render_run_comparison():
    page_header("Experiment Comparison", "Compare real measurements across selected runs. Every plotted point represents a stored observation.", "Analysis / comparison workspace")
    investigations, runs, measurements, _ = filtered_data()
    with st.container(border=True):
        filters = st.columns([1, 2.7, 1.2])
        include_seeds = filters[2].checkbox("Include unverified catalog seeds", key="compare_seeds")
        if not include_seeds:
            runs = runs[runs.data_origin != SEEDED]
        materials = filters[0].multiselect("Materials", sorted(runs.material_name.dropna().unique()), key="compare_materials")
        if materials:
            runs = runs[runs.material_name.isin(materials)]
        st.session_state.setdefault("compare_runs", runs.test_id.head(8).tolist())
        st.session_state.compare_runs = [test for test in st.session_state.compare_runs if test in set(runs.test_id)][:20]
        selected = filters[1].multiselect("Runs to compare (up to 20)", runs.test_id.tolist(), max_selections=20, key="compare_runs")
    runs = runs[runs.test_id.isin(selected)].drop_duplicates("test_id")
    metric_row([("Selected experiments", len(runs)), ("Materials", runs.material_name.nunique()),
                ("Investigations", runs.psi_id.nunique())])
    data_note()
    if runs.empty:
        st.info("Select at least one run. If none are available, change the sidebar filters.")
    else:
        st.session_state.setdefault("compare_mode", "Conditions")
        mode = st.segmented_control("Comparison", ["Conditions", "Sensor measurements"], key="compare_mode")
        axes = {k: LABELS[k] for k in ("o2_initial_pct", "o2_final_pct", "pressure_psi",
                                      "flow_velocity_initial_cm_s", "flow_velocity_min_cm_s")}
        cols = st.columns(2)
        x = cols[0].selectbox("Horizontal axis", list(axes), format_func=axes.__getitem__, key="compare_x")
        if mode == "Sensor measurements":
            data = measurements[measurements.test_id.isin(selected)].copy()
            if data.empty:
                st.info("No sensor measurements are available for the selected runs.")
            else:
                pairs = sorted(set(zip(data.parameter, data.unit)))
                pair_labels = [f"{p} ({u})" for p, u in pairs]
                choice = cols[1].selectbox("Measurement and unit", pair_labels, key="compare_parameter")
                parameter, unit = pairs[pair_labels.index(choice)]
                data = data[(data.parameter == parameter) & (data.unit == unit)]
                # Use one condition row per run to avoid multiplying measurement records in joins.
                data = data.drop(columns=[c for c in axes if c in data]).merge(
                    runs[["test_id", *axes]], on="test_id", how="left", validate="many_to_one")
                data[x] = pd.to_numeric(data[x], errors="coerce")
                data["value"] = pd.to_numeric(data["value"], errors="coerce")
                plotted = data.dropna(subset=[x, "value"])
                if plotted.empty:
                    st.info("The selected measurement has no known values for this horizontal axis.")
                else:
                    fig = px.scatter(plotted, x=x, y="value", color="acronym", symbol="is_over_range",
                                     hover_name="test_id", hover_data=["source_doc", "verification_status"],
                                     labels={**LABELS, "value": f"{parameter} ({unit})"})
                    fig.update_traces(marker_size=12)
                table(data[["test_id", "parameter", "value", "unit", "is_over_range", "source_doc"]],
                      alt="Source measurements underlying the sensor comparison")
                st.caption("Over-range readings represent sensor thresholds, not exact concentrations. "
                           "Parameters with different units are never combined on one axis.")
        else:
            st.session_state.setdefault("compare_y", list(axes)[3])
            y = cols[1].selectbox("Vertical axis", list(axes), format_func=axes.__getitem__, key="compare_y")
            plotted = runs.copy()
            for key in {x, y}:
                plotted[key] = pd.to_numeric(plotted[key], errors="coerce")
            plotted = plotted.dropna(subset=list({x, y}))
            if plotted.empty:
                st.info("No known values for this pair of axes. Try different parameters.")
            else:
                fig = px.scatter(plotted, x=x, y=y, color="outcome", symbol="gravity_level",
                                 hover_name="test_id", hover_data=["material_name", "data_origin"], labels=LABELS)
                fig.update_traces(marker_size=12)
            st.caption(f"{len(plotted)} of {len(runs)} runs plotted; records missing an axis value are omitted.")
        st.caption("Airflow readings may have an approximately one-minute sensor response lag. "
                   "A 0g–1g comparison does not establish validated bounds for lunar or Martian fire risk.")

        kind = st.selectbox("Figure type", ["Selected axes", "Oxygen before and after", "Recorded airflow conditions"], key="compare_figure")
        if kind != "Selected axes":
            fields = ["o2_initial_pct", "o2_final_pct"] if kind == "Oxygen before and after" else ["flow_velocity_initial_cm_s", "flow_velocity_min_cm_s"]
            unit = "%" if kind == "Oxygen before and after" else "cm/s"
            summary = runs[["test_id", *fields]].melt(id_vars="test_id", var_name="Condition", value_name="Reading").dropna(subset=["Reading"])
            summary["Condition"] = summary["Condition"].map(LABELS)
            fig = px.bar(summary, x="test_id", y="Reading", color="Condition", barmode="group",
                         labels={"test_id": "Test ID", "Reading": f"Reading ({unit})"})
        if "fig" in locals():
            chart(fig, "Source measurements for the selected comparison figure", height=410)
            st.download_button("Export interactive chart", fig.to_html(include_plotlyjs=True),
                               "experiment_comparison.html", "text/html", key="compare_export")
        st.caption("Measurement uncertainty is not available in the current sources; intervals cannot be displayed.")
        section("Underlying experimental conditions")
        table(runs[["test_id", "material_name", "o2_initial_pct", "pressure_psi",
                    "flow_velocity_initial_cm_s", "gravity_level", "outcome", "data_origin"]],
              alt="Physical conditions of the selected comparison runs")
        st.download_button("Export comparison CSV", runs.to_csv(index=False).encode(), "comparison.csv", "text/csv", key="compare_csv_export")
