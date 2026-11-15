import os

import streamlit as st
from google.genai import errors
from pydantic import ValidationError

from config.settings import GEMINI_MODEL, MISSION_PROFILES
from si.gemini_client import GeminiClient
from si.insights import GroundedInsight, build_prompt, select_evidence, validate_citations
from ui.common import attribution, filtered_data, get_sources, source_files
from ui.data import CSV_BACKED



def render_source_research():
    st.caption("SI engineering copilot · Ask about original experimental evidence, with traceable references.")
    investigations, runs, _, _ = filtered_data()
    by_id = {i["psi_id"]: i for i in investigations}
    source_backed_ids = sorted(set(runs.loc[runs.data_origin == CSV_BACKED, "psi_id"]) & set(by_id))
    st.session_state.setdefault("insight_ids", source_backed_ids[:1] or list(by_id)[:1])
    st.session_state.insight_ids = [pid for pid in st.session_state.insight_ids if pid in by_id]
    chosen_ids = st.multiselect("Research scope (up to 3 investigations)", list(by_id),
                                max_selections=3, format_func=lambda p: f"{by_id[p]['acronym']} · {p}", key="insight_ids")
    scope = runs[runs.psi_id.isin(chosen_ids)]
    available = scope.loc[scope.data_origin == CSV_BACKED, "test_id"].tolist()
    st.session_state.setdefault("insight_tests", available[:5])
    st.session_state.insight_tests = [test for test in st.session_state.insight_tests if test in available]
    selected_tests = st.multiselect("Source-backed runs to include (up to 12)", available,
                                    max_selections=12, key="insight_tests")
    include_uploads = st.checkbox("Include my session source files", key="insight_uploads",
                                  disabled=not st.session_state.uploads)
    mission = st.selectbox("Interpretation scenario", list(MISSION_PROFILES),
                           format_func=lambda k: MISSION_PROFILES[k]["label"], key="insight_mission")
    question = st.text_area("Research question", value="What experimental evidence is available about PMMA "
                            "flammability under lunar habitat conditions?", max_chars=2000, key="insight_question")
    st.caption("Analyze sends this question and the selected source excerpts to Gemini. New answers and private "
               "uploads are kept in this session, not written to the shared database. Existing SQLite answers can be reused.")

    if st.button("Analyze evidence", type="primary", key="analyze_evidence", disabled=not chosen_ids or not question.strip()):
        st.session_state.insight_result = None
        try:
            with st.spinner("Retrieving source evidence…"):
                sources = []
                for pid in chosen_ids:
                    sources.extend(get_sources(by_id[pid]))
                if include_uploads:
                    for item in st.session_state.uploads.values():
                        if item["psi_id"] in chosen_ids:
                            sources.extend(item["sources"])
                            selected_tests = selected_tests + item["runs"].test_id.head(12).tolist()
                evidence = select_evidence(sources, question, selected_tests)
                prompt = build_prompt(question.strip(), {"name": mission,
                    "target_o2_pct": MISSION_PROFILES[mission]["target_o2_pct"],
                    "target_pressure_psi": MISSION_PROFILES[mission]["target_pressure_psi"],
                    "gravity_g": MISSION_PROFILES[mission]["gravity_g"]}, evidence)
                client = GeminiClient(api_key=st.session_state.get("user_api_key") or None,
                                      model_name=os.getenv("GEMINI_MODEL") or GEMINI_MODEL, cache_writes=False)
                cache_key = client._generate_hash(prompt, GroundedInsight)
                cached = st.session_state.insight_cache.get(cache_key)
                with st.spinner("Analyzing the selected evidence…"):
                    answer = GroundedInsight.model_validate(cached) if cached else client.generate(prompt, GroundedInsight)
                    validate_citations(answer, evidence)
                if len(st.session_state.insight_cache) >= 20:
                    st.session_state.insight_cache.pop(next(iter(st.session_state.insight_cache)))
                st.session_state.insight_cache[cache_key] = answer.model_dump(mode="json")
                st.session_state.insight_result = {"question": question, "mission": mission,
                    "answer": answer.model_dump(mode="json"), "evidence": evidence, "session_hit": bool(cached)}
        except (ValueError, ValidationError):
            st.warning("No validated answer was produced. Select original source files or try a more specific question.")
        except errors.APIError as exc:
            st.warning(f"Gemini request failed (API status {exc.code}). Your data is unchanged; original sources remain available below.")
            details = exc.message or "No error details were returned by the API."
            for secret in (st.session_state.get("user_api_key"), os.getenv("GEMINI_API_KEY")):
                if secret:
                    details = details.replace(secret, "[REDACTED]")
            with st.expander("API error details"):
                st.text(details[:2000])
        except RuntimeError:
            st.info("No saved answer was found and no usable API key is configured. Add a Gemini API key in SI configuration.")
        except Exception:
            st.warning("The analysis could not be completed. Please retry; the original research data is unchanged.")

    result = st.session_state.insight_result
    if result:
        answer = GroundedInsight.model_validate(result["answer"])
        registry = {s["source_id"]: s for s in result["evidence"]}
        st.subheader("Analysis")
        st.write(result["question"])
        st.caption(f"Scenario: {result['mission']} · " + ("Reused session answer" if result["session_hit"] else "Source-based answer"))
        st.caption("Cited source IDs and exact quotations were checked. This does not independently validate the scientific claims.")
        for heading, claims in (("Observations", answer.observations), ("Interpretations", answer.interpretations)):
            st.markdown(f"### {heading}")
            if not claims:
                st.write("Insufficient evidence for a supported claim.")
            for claim_index, claim in enumerate(claims):
                st.write(claim.text)
                for citation_index, citation in enumerate(claim.citations):
                    source = registry[citation.source_id]
                    st.caption(f"[{source['psi_id']} | {source.get('doi') or 'DOI unknown'} | "
                               f"{source['source_doc']}, {source['locator']}]")
                    with st.expander("Supporting excerpt", key=f"quote_{heading}_{claim_index}_{citation_index}"):
                        st.text(citation.quote)
        st.markdown("### Limitations")
        for limitation in answer.limitations:
            st.write(f"• {limitation}")
        with st.expander("Evidence supplied to Gemini"):
            for source in result["evidence"]:
                st.write(f"**{source['source_doc']} · {source['locator']}**")
                st.text(source["text"])
        st.download_button("Download analysis JSON", answer.model_dump_json(indent=2),
                           "source_based_insight.json", "application/json", key="insight_download")

    st.subheader("Original sources")
    if not chosen_ids:
        st.info("Choose an investigation to inspect its original source files.")
    for pid in chosen_ids:
        attribution(by_id[pid])
        source_files(by_id[pid], "insights")
