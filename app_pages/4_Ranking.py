"""Question-specific research discovery; relevance never denotes physical safety."""
import pandas as pd
import streamlit as st
from config.settings import MISSION_PROFILES
from scientific.intelligence import PILLARS, ScientificRequest, rank_research
from scientific.materials import Parameter
from ui.common import attribution, filtered_data
from ui.design import page_header, section
from ui.intelligence_workspace import current_archive

page_header("Research relevance.\nScientific context.","Find investigations that address your question across prevention, detection and suppression.","03 / research discovery")
pillar=st.segmented_control("Scientific task",list(PILLARS),default="PREVENTION",key="ranking_pillar") or "PREVENTION"
question=st.text_input("Research objective",value="Compare material combustion and flame propagation evidence",key="ranking_question")
mission=st.selectbox("Mission reference",list(MISSION_PROFILES),key="mission")
profile=MISSION_PROFILES[mission]
st.caption("Illustrative mission relevance; no partial-gravity prediction, uncertainty percentage or material safety score.")
request=ScientificRequest.model_validate({"pillar":pillar,"question":question or "Relevant combustion research","mission":mission,
    "parameters":{"gravity_g":Parameter(state="specified",value=profile["gravity_g"]),
                  "o2_initial_pct":Parameter(state="specified",value=profile["target_o2_pct"])}})
archive=current_archive()
scope={i["psi_id"] for i in filtered_data(include_uploads=False)[0]}
ranked=[r for r in rank_research(request,archive) if r["psi_id"] in scope]
section("Investigation priority index")
for index,inv in enumerate(ranked,1):
    columns=st.columns([.7,4,1.3,1])
    columns[0].html(f'<div class="ff-index">{index:02d}</div>')
    columns[1].subheader(inv["title"])
    columns[1].caption(f"{inv['acronym']} / {inv['psi_id']} / {inv['verified_measurements']} source-backed measurements")
    columns[2].metric("Relevance / 100",f"{inv['relevance']:.1f}")
    if columns[3].button("Inspect",key=f"ranking_inspect_button_{inv['psi_id']}"):
        st.session_state.ranking_selected_psi_id=inv["psi_id"]
        st.session_state.explorer_ids=[inv["psi_id"]]
        st.switch_page("app_pages/2_Explorer.py")
    with st.expander(f"Scientific dossier / {inv['acronym']}"):
        attribution(inv)
        st.write(inv.get("objectives") or inv.get("summary"))
        for reason in inv["reasons"]:st.caption(reason)
        for limitation in inv["limitations"]:st.caption(str(limitation))
with st.expander("Ranking method"):
    st.write("Pillar relevance 35%, material relevance 25%, question terms 20%, matching conditions 10%, source-backed evidence availability 10%.")
    st.caption("Multi-pillar classifications are supported. Coverage and condition matching are reported separately; nominal pressure is not certified as measured.")
if ranked:
    st.download_button("Download investigation ranking",pd.DataFrame(ranked).to_csv(index=False).encode(),"investigation_ranking.csv","text/csv",key="ranking_investigation_export")
