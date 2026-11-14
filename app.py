import os

import streamlit as st
from dotenv import load_dotenv

from si.gemini_client import GeminiClient


load_dotenv()


# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="Flame in Freefall",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================
# MISSION PROFILES
# ==========================================

from config.settings import (
    MISSION_PROFILES,
    GEMINI_MODEL,
    DB_PATH
)

from database.repository import (
    get_all_investigations,
    get_experiments_df,
    get_measurements_df,
    get_findings,
    get_ranked_experiments_df,
    get_ranked_investigations
)


# ==========================================
# CUSTOM STYLING
# ==========================================

st.markdown(
    """
    <style>

    .stApp {
        background-color: #080D17;
        color: #E2E8F0;
    }

    [data-testid="stSidebar"] {
        background-color: #111B2E;
        border-right: 1px solid #263449;
    }

    [data-testid="stMetric"] {
        background-color: #111B2E;
        border: 1px solid #263449;
        padding: 20px;
        border-radius: 12px;
    }

    h1 {
        color: #FF6B35;
    }

    h2, h3 {
        color: #E2E8F0;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.title("Flame in Freefall")

    st.caption(
        "Microgravity Fire Safety Intelligence"
    )

    st.divider()

    st.subheader("Mission Profile")

    mission = st.selectbox(
    "Select mission environment",
    list(MISSION_PROFILES.keys()),
    format_func=lambda key: MISSION_PROFILES[key]["label"]
    )

    st.subheader("Safety Pillar")

    safety_pillar = st.radio(
        "Fire safety category",
        [
            "All",
            "Prevention",
            "Detection",
            "Suppression"
        ]
    )

    st.subheader("Research Facility")

    facility = st.selectbox(
        "Experimental facility",
        [
            "All",
            "MSG",
            "CIR / MDCA",
            "Saffire / Cygnus"
        ]
    )

    show_spinoffs = st.toggle(
        "Highlight Earth Spin-offs"
    )

    st.divider()

    with st.expander("SI Configuration"):

        user_api_key = st.text_input(
            "Optional Gemini API Key",
            type="password"
        )

        model_name = os.getenv(
            "GEMINI_MODEL",
            GEMINI_MODEL
        ) or GEMINI_MODEL

        st.caption(f"Model: {model_name}")

        if user_api_key or os.getenv("GEMINI_API_KEY"):
            st.success("API key configured")
        else:
            st.info("Offline mode")

    st.divider()

    st.caption("Data Source")

    st.markdown(
        "[NASA Physical Sciences Informatics]"
        "(https://psi.nasa.gov/)"
    )


# ==========================================
# SESSION STATE
# ==========================================

st.session_state["mission"] = mission
st.session_state["safety_pillar"] = safety_pillar
st.session_state["facility"] = facility
st.session_state["show_spinoffs"] = show_spinoffs


# ==========================================
# SI CLIENT
# ==========================================

si_client = GeminiClient(
    api_key=user_api_key or None,
    model_name=model_name
)


# ==========================================
# MAIN HEADER
# ==========================================

st.title("FLAME IN FREEFALL")

st.markdown(
    "### Super Intelligence for Spacecraft Fire Safety"
)

st.caption(
    "NASA Space Apps Challenge 2026 | "
    "Microgravity Combustion Research"
)

st.divider()


# ==========================================
# MISSION ENVIRONMENT
# ==========================================

st.subheader("Mission Environment")

st.markdown(f"**Selected mission:** {mission}")

profile = MISSION_PROFILES[mission]

col1, col2, col3 = st.columns(3)

col1.metric(
    "Gravity",
    f"{profile['gravity_g']} g"
)

col2.metric(
    "Target Oxygen",
    f"{profile['target_o2_pct']}%"
)

col3.metric(
    "Target Pressure",
    f"{profile['target_pressure_psi']} psi"
)

st.caption(profile["description"])

st.caption(
    "Illustrative mission scenario, "
    "not certified spacecraft operating limits."
)


# ==========================================
# FIRE SAFETY PILLARS
# ==========================================

st.divider()

st.subheader("Fire Safety Pillars")

col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.markdown("### Prevention")
        st.write(
            "Material flammability, flame propagation "
            "and ignition conditions."
        )

with col2:
    with st.container(border=True):
        st.markdown("### Detection")
        st.write(
            "Smoke particles, aerosols and "
            "early fire detection systems."
        )

with col3:
    with st.container(border=True):
        st.markdown("### Suppression")
        st.write(
            "Flame extinction, suppressing agents "
            "and combustion control."
        )


# ==========================================
# RESEARCH WORKSPACE
# ==========================================

st.divider()
st.subheader("Research Workspace")

facility_mapping = {
    "All": None,
    "MSG": ["MSG"],
    "CIR / MDCA": ["CIR", "MDCA"],
    "Saffire / Cygnus": ["Saffire/Cygnus"]
}

selected_facilities = facility_mapping[facility]

try:
    if not DB_PATH.is_file():
        raise FileNotFoundError("Research database missing")

    investigations = get_all_investigations(
        safety_pillar=safety_pillar
    )

    if selected_facilities:
        investigations = [
            item for item in investigations
            if item["hardware_facility"]
            in selected_facilities
        ]

    selected_ids = {
        item["psi_id"] for item in investigations
    }

    experiments = get_experiments_df()

    experiments = experiments[
        experiments["psi_id"].isin(selected_ids)
    ]

    measurements = get_measurements_df()

    measurements = measurements[
        measurements["psi_id"].isin(selected_ids)
    ]

    findings = [
        item for item in get_findings()
        if item["psi_id"] in selected_ids
    ]

    # KEY PERFORMANCE INDICATORS

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Investigations",
        len(investigations)
    )

    col2.metric(
        "Experimental Runs",
        experiments["test_id"].nunique()
    )

    col3.metric(
        "Measurements",
        measurements["id"].nunique()
    )

    col4.metric(
        "Research Findings",
        len(findings)
    )

    st.divider()

    # RESEARCH CARDS

    if not investigations:
        st.info(
            "No investigations match the selected filters."
        )

    for investigation in investigations:

        with st.container(border=True):

            st.subheader(
                f"{investigation['acronym']} "
                f"— {investigation['psi_id']}"
            )

            st.caption(
                investigation["title"]
            )

            col1, col2, col3 = st.columns(3)

            col1.write(
                f"**Pillar:** "
                f"{investigation['safety_pillar']}"
            )

            col2.write(
                f"**Fuel:** "
                f"{investigation['fuel_category']}"
            )

            col3.write(
                f"**Facility:** "
                f"{investigation['hardware_facility']}"
            )

            st.write(
                investigation.get("summary")
                or "Summary unavailable."
            )

            if investigation.get("doi"):

                doi = investigation["doi"]

                doi_url = (
                    doi if doi.startswith("https://doi.org/")
                    else f"https://doi.org/{doi}"
                )

                st.markdown(
                    f"[DOI: {doi}]({doi_url})"
                )

            if investigation.get("psi_url"):
                st.link_button(
                    "Open NASA PSI Source",
                    investigation["psi_url"]
                )

            with st.expander("Official Citation"):
                st.code(
                    investigation["citation_text"],
                    language=None
                )

            if show_spinoffs:
                st.markdown("**Earth Spin-off**")

                st.write(
                    investigation.get("earth_spinoff_text")
                    or "No information available."
                )

except Exception as exc:

    st.error("Unable to load the research database.")

    st.exception(exc)


# ==========================================
# FOOTER
# ==========================================

st.divider()

with st.container():

    st.markdown("#### SI Development Disclosure")

    st.caption(
        "This application uses Gemini models to assist "
        "with scientific data extraction, summarization "
        "and interpretation. SI-generated findings must "
        "be verified against original scientific sources."
    )

    st.markdown("#### NASA PSI DOI Attribution Notice")

    st.caption(
        "NASA Physical Sciences Informatics datasets "
        "and publications must be cited using their "
        "official DOI and recommended citation."
    )
