# Swiss Scientific Editorial V2 / material assessment upgrade

This guide supersedes the earlier five-page frontend integration guide.

## Implemented architecture

Exactly four primary pages are registered: Overview, Explorer, Ranking and SI Insights.
The permanent sidebar and old dark dashboard theme are replaced by horizontal editorial
navigation, warm paper, cobalt typography, thin separators and on-demand scientific details.
The original stack remains Python / Streamlit / Plotly / SQLite / scikit-learn / SciPy / Gemini.

SI Insights has four compact modes: Assess Material, Find Materials, Compare Materials and
Predict Parameter. The first is the default. Existing experiment-level comparison plots,
condition/measurement selectors, source tables, CSV and interactive HTML exports remain in
an advanced tool inside SI Insights. The original document-research assistant, quote checks,
session uploads and cache behaviour are preserved alongside it.

Assessments expose a concise conclusion, available characteristics and one main figure.
Scientific inputs collapse after a result is generated. Editing inputs hides the old conclusion;
it must be reassessed. Full characteristics, interpretation, original evidence, condition groups,
model reliability, proposed experiments, source references and diagnostics are on demand.
Essential uncertainty and applicability limits remain visible.

## Optional conditions and independent characteristics

`scientific.materials.Parameter` explicitly separates:

| State | Retrieval meaning | Numerical input meaning |
| --- | --- | --- |
| Specified | Match the supplied exact value/category | Can satisfy a required feature |
| Any | Do not restrict retrieval by this variable | Does not supply a model input |
| Unknown | Preserve missing physical information; related records remain discoverable | Cannot satisfy a required feature |
| Range | Retrieve observations within explicit bounds | Never automatically use a midpoint |

Physical values are nullable. Zero remains meaningful for gravity, gas concentration and airflow;
unknown dimensions are not represented by zero. Negative/invalid physical inputs and reversed
ranges are rejected. No averages, random values, Gemini inputs or new imputation strategy are used.

`MaterialAssessment` contains independent `MaterialReport` / `Characteristic` results. Targets
are discovered from SQLite measurements and existing model metadata. Each characteristic is
OBSERVED, INTERPOLATED, PREDICTED or UNAVAILABLE; a missing target cannot cancel another.
An OBSERVED result distinguishes a recorded observation from conditional observations under
partially specified conditions. Conditional results use observed ranges/distributions and retain
all supporting records, rather than claiming a unique outcome.

Observation strata preserve investigation/source apparatus, target units, geometry, gravity,
pressure, airflow/history, specimen dimensions, initial gas background, reuse and burn sides.
Incompatible records are not pooled into averages. Different units remain separate.

Find Materials discovers evidence-bearing research candidates and supports optional physical
criteria. It does not rank by record quantity or infer safety from lower carbon dioxide.
Compare Materials preserves missing characteristics and reports whether records share physical
strata; matching strata alone do not validate material-property equivalence. Current evidence
does not justify an operational material recommendation or universal winner.

## B1 root cause and general fix

The old strict router treated retrieving a historical observation as equivalent to proving a
fully measured environment. Nominal pressure therefore rejected source-verified B1 even when
all recorded conditions matched, then fell through to unsupported prediction and an inappropriate
future research proposal. Mission replacement could also produce a different physical scenario.

An explicit `AssessmentRequest.reference_uid` now identifies archive lookup. It retrieves that
verified observation with the source's nominal-pressure limitation, without requiring the user to
assert that pressure was measured. SHA-256, raw-row identity, units, target verification and
condition equality still apply. No B1-specific exception or hardcoded result exists.

Loading conditions runs through a callback and copies all available source fields. Choosing a
mission does not apply it; the separate replacement action does. Modifying conditions is assessed
again and cannot preserve an inapplicable recorded result. The regression cases retrieve B1 final
carbon dioxide at 0.44 percent and M1 at 0.61 percent; lunar or terrestrial replacements do not
turn those observations into validated partial-gravity or ground predictions.

## ML and Gemini

The strict numerical router, reviewed interpolation interface, serialized preprocessing/model
loader, artifact/runtime checks, promotion flags, joint applicability domain, local independent
groups and uncertainty gates are reused. Evidence snapshots avoid reading the same archive twice
for each characteristic. Model metadata is checked for target relevance before deserializing an
unrelated artifact. No production model is retrained, edited or promoted.

The current Random Forest remains RESEARCH_ONLY. No production interpolation policy is approved.
Approved-model and interpolation tests use temporary fixtures explicitly labelled as such.
Missing required inputs withhold only the estimate, while recorded/related evidence remains useful.

`scientific.synthesis` gives Gemini the fixed multi-characteristic result and bounded original
source excerpts. It validates structured output, supplied source identities and exact quotations.
The primary conclusion is limited to two sentences / forty words. Numerical prose and invented
references are rejected; rendered values/intervals always come from Python. The client retains
transport retries and existing SQLite cache reads; new validated synthesis answers stay in the
bounded session cache. The shared research database is not written by assessments.

A successful recorded lookup never becomes a proposed future experiment. Genuine unresolved
gaps can receive a clearly labelled SI-generated proposal, not an existing NASA result, validated
protocol or safe procedure. Gemini failure keeps deterministic conclusions and observations.
Quotation validation establishes traceability, not scientific truth.

## Files

| Area | Files |
| --- | --- |
| Theme and navigation | `.streamlit/config.toml`, `app.py`, `ui/design.py` |
| Four page layouts | `app_pages/1_Overview.py`, `2_Explorer.py`, `4_Ranking.py`, `5_SI_Insights.py` |
| Central workspace | `ui/material_workspace.py` |
| Preserved tools | `ui/run_comparison.py`, `ui/source_research.py`, `ui/uploads.py`, `ui/common.py` |
| Scientific service | `scientific/materials.py`, `scientific/labels.py`, `scientific/synthesis.py`, `scientific/schemas.py`, `scientific/assessment.py` |
| Verification | `tests/test_materials.py`, updated `tests/test_dashboard.py`, `tests/browser_smoke.py` |
| Current architecture | `Context.md`, `README.md` |

The removed standalone `app_pages/3_Compare.py` is preserved functionally in `ui/run_comparison.py`.
Colleague-owned ingestion, database schema/repositories, ranking implementation, raw NASA files
and trained model artifacts were not changed. Existing unrelated working-tree changes are preserved.

## Scientific limits and differences from Stitch

The checked archive mainly supports calibrated oxygen and initial/final gas concentrations.
Seed-only flame-spread, heat-release, smoke and other characteristics remain unavailable until
source verification. Gas concentration is not automatically gas production, combustion efficiency
or fire safety. Pressure is nominal in the source CSV; time-resolved ventilation, duration and
measurement uncertainty are missing. No validated lunar/Martian numerical prediction is claimed.

The new four Stitch screenshots and HTML/CSS were inspected and extracted separately.
The implementation follows their editorial hierarchy and explicit requested paper palette.
Native Streamlit controls/expanders and table scrolling retain their own dimensions. The interface
uses canonical psi rather than the illustrative kPa labels. It does not copy fake counts, telemetry,
DOI identifiers, latency, safety percentages, model metrics, confidence bands, fitted envelopes,
optical photographs or scientific claims from the exported examples. Real data therefore produces
different chart shapes, shorter ranking lists and honest unavailable states.

The figure always represents source observations or approved numerical outputs, not the screenshot's
illustrative flame-spread curve. Material discovery currently gives research candidates rather
than a scientifically unsupported recommendation. Additional imported datasets and approved
scientific models are required to expand those capabilities.

## Run and verify

Restart Streamlit after updating modules/theme:

```powershell
cd C:\Education_programming\NASA\fire-in-freefall
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Existing runtime and optional ML dependencies remain in `requirements.txt` / `requirements-ml.txt`.
No new runtime dependency is required. Playwright and installed Edge are development-only.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe test_gemini.py
.\.venv\Scripts\ty.exe check app.py app_pages ui scientific --output-format concise
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.port=8766 --server.enableAgentApi=true
# In another terminal:
.\.venv\Scripts\python.exe tests/browser_smoke.py
```

Browser screenshots are stored in `design_reference/verification-v2/`. Tests cover record loading,
mission changes, partial/unknown/unrestricted/range inputs, explicit zero, independent characteristics,
compatible/incompatible comparison strata, unsupported criteria, existing model gates, Gemini
success/failure/invalid responses, immutable numerical results, session caching and suppression of
unnecessary proposals. Gemini calls in automated verification are mocked or disabled.

Executed verification: 17 strict-router tests, 15 material-service tests, 13 updated dashboard/source
tests, 8 existing training/evaluation tests, 1 structured transport test and 7 cache tests passed
(61 cases across the executed suites). `ty` and `git diff --check` passed. Edge verified all four
pages, the new light palette/no sidebar, B1 lookup, changed-input invalidation, related-evidence
handling and a narrower viewport. Streamlit's localhost agent API independently confirmed exactly
four registered pages, B1 retrieval without a pressure checkbox and reassessment after a gravity change.
No paid Gemini request was made. The database SHA-256 stayed
`e14492fdd28830feaec54a30379d93f587fc23915d6b988e7f57bae80a420475`.
