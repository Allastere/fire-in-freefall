"""Four editorial research workspaces. Run: streamlit run app.py."""

import os
import streamlit as st
from dotenv import load_dotenv
from config.settings import GEMINI_MODEL
from ui.common import catalog
from ui.design import brand, install_design

load_dotenv()
st.set_page_config(page_title="Flame in Freefall", page_icon=":material/science:", layout="wide")
install_design()
for key, value in {"uploads": {}, "insight_cache": {}, "insight_result": None}.items():
    st.session_state.setdefault(key, value)

pages = [
    st.Page("app_pages/1_Overview.py", title="Overview", default=True),
    st.Page("app_pages/2_Explorer.py", title="Explorer"),
    st.Page("app_pages/4_Ranking.py", title="Ranking"),
    st.Page("app_pages/5_SI_Insights.py", title="SI Insights"),
]
page = st.navigation(pages, position="hidden")
for key, value in st.session_state.get("_workspace_filters", {}).items():
    if key not in st.session_state and not key.startswith("ranking_inspect_"):
        st.session_state[key] = value
investigations = catalog()[0]
with st.container(key="editorial_nav"):
    columns = st.columns([3.3, 1, 1, 1, 1.2, .65], vertical_alignment="center")
    with columns[0]:
        brand()
    for column, destination in zip(columns[1:5], pages):
        with column, st.container(key="nav_active" if destination == page else f"nav_{destination.title.replace(' ', '_')}"):
            st.page_link(destination, label=destination.title)
    with columns[5], st.popover(":material/tune:", help="Archive scope and SI settings"):
        st.selectbox("Safety pillar", ["All", *sorted({i["safety_pillar"] for i in investigations})], key="safety_pillar")
        st.selectbox("Research facility", ["All", *sorted({i["hardware_facility"] for i in investigations})], key="facility")
        st.toggle("Show Earth spin-offs", key="show_spinoffs")
        st.text_input("Optional Gemini API key", type="password", key="user_api_key")
        st.caption(f"Gemini: {os.getenv('GEMINI_MODEL') or GEMINI_MODEL}")
        st.caption("Source text is sent only when you request synthesis.")
page.run()
# Keep page widgets alive across navigation, excluding buttons and uploaded file handles.
st.session_state._workspace_filters = {
    key: value for key, value in st.session_state.items()
    if isinstance(key, str) and (key.startswith(("explorer_", "compare_", "ranking_", "range_", "insight_", "editorial_", "si_state_", "si_value_", "si_low_", "si_high_", "si_question_"))
        or key in ("si_pillar","si_materials","si_mission","si_reference","si_detector","si_agent","si_synthesis"))
    and key not in ("insight_result", "insight_cache")
    and not key.startswith(("ranking_inspect_", "editorial_record_", "editorial_mission_"))
    and not key.endswith(("_send", "_export", "_download", "_submit", "_load", "_apply", "_restore"))
    and isinstance(value, (str, int, float, bool, list, tuple))
}
st.html('<div class="ff-footer">Experimental decision-support tool. Not a certified spacecraft fire safety assessment.<br>NASA Physical Sciences Informatics / source attribution required.</div>')
st.caption("SI Development Disclosure — Gemini provides optional source-grounded interpretation. Generated conclusions require scientific review.")
