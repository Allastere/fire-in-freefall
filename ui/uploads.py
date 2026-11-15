import hashlib
import pandas as pd
import streamlit as st
from ui.common import catalog
from ui.data import parse_upload
from ui.design import section

def render_uploads():
    section("Extend the evidence archive")
    with st.expander("Upload NASA source files · CSV / PDF / DOCX / TXT"):
        all_investigations = catalog()[0]
        by_id = {i["psi_id"]: i for i in all_investigations}
        upload_psi = st.selectbox("Associate files with an investigation", list(by_id),
                                  format_func=lambda p: f"{by_id[p]['acronym']} · {p}", key="upload_psi")
        files = st.file_uploader("Source files (up to 10 MB each)", type=["csv", "pdf", "docx", "txt"],
                                 accept_multiple_files=True, key="source_uploads", max_upload_size=10)
        st.caption("Uploads stay in this browser session. CSV units use the displayed backend column mapping; "
                   "review it before interpreting values. Uploaded data is not automatically verified.")
        if st.button("Add to session", disabled=not files, key="add_uploads"):
            for uploaded in files:
                content = uploaded.getvalue()
                upload_key = f"{upload_psi}:{hashlib.sha256(content).hexdigest()}"
                if upload_key in st.session_state.uploads:
                    st.info(f"{uploaded.name}: already in this session.")
                    continue
                try:
                    parsed = parse_upload(content, uploaded.name, by_id[upload_psi])
                except Exception:
                    st.error(f"Could not parse {uploaded.name}. Check the format, UTF-8 encoding, "
                             "physical values and the 10 MB / 10,000 record / 300 PDF page limits.")
                else:
                    st.session_state.uploads[upload_key] = parsed
                    st.success(f"{uploaded.name}: added to the session.")
            st.rerun()
        if st.session_state.uploads and st.button("Clear session uploads", key="clear_uploads"):
            st.session_state.uploads = {}
            st.session_state.insight_result = None
            st.session_state.insight_cache = {}
            st.rerun()

    if st.session_state.uploads:
        with st.expander("Session file previews"):
            for item in st.session_state.uploads.values():
                st.write(f"**{item['name']} · {item['psi_id']}**")
                if "raw" in item:
                    st.dataframe(item["raw"].head(30), hide_index=True, alt="Uploaded CSV source preview")
                    st.dataframe(pd.DataFrame(item["mapping"]), hide_index=True, alt="Detected CSV column mapping")
                    if item["unmapped"]:
                        st.caption("Preserved without mapping: " + ", ".join(item["unmapped"]))
                else:
                    st.text(item["sources"][0]["text"])
