"""Readable scientific prose with numbered, deduplicated references on demand."""

import json

import pandas as pd
import streamlit as st


def render_narrative(synthesis, sources):
    registry = {source["source_id"]: source for source in sources}
    references = {}
    headings = {"behaviour": "Combustion behaviour", "advantages": "Supported advantages",
                "concerns": "Scientific considerations", "alternatives": "Material alternatives"}
    for field, heading in headings.items():
        claims = synthesis.get(field, [])
        if not claims:
            continue
        st.subheader(heading)
        for claim in claims:
            numbers = []
            for citation in claim["citations"]:
                reference = references.setdefault(citation["source_id"], {"number": len(references) + 1, "quotes": []})
                if citation["quote"] not in reference["quotes"]:
                    reference["quotes"].append(citation["quote"])
                if reference["number"] not in numbers:
                    numbers.append(reference["number"])
            st.write(claim["text"])
            st.caption("Sources " + ", ".join(f"[{number}]" for number in numbers))
    if synthesis.get("knowledge_gaps"):
        st.subheader("Open research questions")
        for gap in synthesis["knowledge_gaps"]:
            st.write(gap)
    if synthesis.get("limitations"):
        st.subheader("Interpretation limits")
        for limitation in synthesis["limitations"]:
            st.write(limitation)
    if references:
        with st.expander("References for this interpretation"):
            for source_id, reference in references.items():
                source = registry.get(source_id, {})
                st.markdown(f"**[{reference['number']}] {source.get('psi_id', 'Source')} · {source.get('source_doc', 'Original evidence')}**")
                st.caption(source.get("locator", "Location unavailable"))
                if source.get("doi"):
                    st.link_button("Original investigation · DOI", "https://doi.org/" + source["doi"])
                with st.expander(f"Supporting excerpt [{reference['number']}]"):
                    for quote in reference["quotes"]:
                        try:
                            row = json.loads(quote)
                        except (ValueError, TypeError):
                            row = None
                        if isinstance(row, dict):
                            st.dataframe(pd.DataFrame({"Recorded field": list(row), "Source value": [str(value) for value in row.values()]}),
                                         hide_index=True, width="stretch", alt="Original source fields supporting the interpretation")
                        else:
                            st.write(quote)
