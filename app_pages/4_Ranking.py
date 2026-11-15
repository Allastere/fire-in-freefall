import streamlit as st
from config.settings import MISSION_PROFILES, RANKING_WEIGHTS
from core.ranking import rank_experiments_df, rank_investigations_df
from ui.common import attribution, filtered_data, table
from ui.data import CSV_BACKED
from ui.design import page_header, section

page_header("Research relevance.\nMission context.", "Prioritize investigations for a research scenario using the existing deterministic evidence-relevance algorithm.", "03 / scientific decision support")
cols = st.columns([2, 1])
mission = cols[1].selectbox("Mission reference", list(MISSION_PROFILES), key="mission")
st.session_state.active_mission = mission
profile = MISSION_PROFILES[mission]
cols[0].caption(f"Requested environment / {profile['target_o2_pct']}% oxygen / {profile['target_pressure_psi']} psi / {profile['gravity_g']} g")
st.caption("Research relevance is not material safety, certification or validated partial-gravity prediction.")
investigations, runs, measurements, _ = filtered_data(include_uploads=False)
with st.expander("Evidence scope and algorithm weights"):
    seeds = st.checkbox("Include unverified catalog seeds", key="ranking_seeds")
    st.write(" / ".join(f"{key.capitalize()} {weight:.0%}" for key, weight in RANKING_WEIGHTS.items()))
    st.caption("Fixed backend weights; editable decision matrices are unavailable.")
if not seeds:
    runs = runs[runs.data_origin == CSV_BACKED]
measurements = measurements[measurements.test_id.isin(runs.test_id)]
section("Investigation priority index")
if runs.empty:
    st.info("No experimental evidence in this scope.")
else:
    eligible = [i for i in investigations if i["psi_id"] in set(runs.psi_id)]
    ranked = rank_investigations_df(eligible, runs, measurements, mission)
    for index, inv in enumerate(ranked.to_dict("records"), 1):
        columns = st.columns([.7, 4, 1.5, 1])
        columns[0].html(f'<div class="ff-index">{index:02d}</div>')
        columns[1].subheader(inv["title"])
        columns[1].caption(f"{inv['acronym']} / {inv['hardware_facility']} / {inv['run_count']} runs")
        columns[2].metric("Relevance / 100", f"{inv['research_relevance_score']:.1f}")
        if columns[3].button("Inspect ↗", key=f"ranking_inspect_{inv['psi_id']}"):
            st.session_state.explorer_ids = [inv["psi_id"]]
            st.switch_page("app_pages/2_Explorer.py")
        with st.expander(f"Scientific dossier / {inv['acronym']}"):
            attribution(inv)
            st.write(inv.get("summary") or "Summary unavailable.")
            st.caption("No confidence interval is defined for this deterministic relevance score.")
    with st.expander("Experimental run ranking and score components"):
        experiments = rank_experiments_df(runs, measurements, mission)
        table(experiments[["test_id","material_name","research_relevance_score","s_scenario","s_completeness","s_evidence","s_comparability"]],
              alt="Deterministic run relevance and four backend score components")
        st.download_button("Download ranked runs", experiments.to_csv(index=False).encode(), "ranked_runs.csv", "text/csv", key="ranking_download")
    st.download_button("Download investigation ranking", ranked.to_csv(index=False).encode(), "investigation_ranking.csv", "text/csv", key="ranking_investigation_export")
