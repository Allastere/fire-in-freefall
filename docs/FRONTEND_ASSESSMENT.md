# Frontend and scientific assessment integration

Implemented on `dev-ui`, using the existing Streamlit, Plotly, SQLite repositories,
Gemini client and serialized ML pipeline. There are exactly five primary pages:
Overview, Explorer, Compare, Ranking and SI Insights. Prediction is part of SI Insights.

## Implementation map

| Files | Responsibility |
| --- | --- |
| `.streamlit/config.toml`, `ui/design.py` | Shared dark theme, Inter / Space Grotesk / JetBrains Mono, orange navigation, compact panels, chart theme and reusable components |
| `app.py` | Five native pages, shared evidence filters, persistent page selections, disclosure and attribution |
| `app_pages/1_Overview.py` | Dynamic counts, research-pillar / oxygen / material plots, investigation cards, summaries, original documents and research highlights |
| `app_pages/2_Explorer.py` | Physical filters, run table, measurement inspector, original rows, CSV export, session uploads and transfer to Compare |
| `app_pages/3_Compare.py` | Actual condition / sensor scatter plots, oxygen / airflow charts, raw observations, CSV and standalone interactive HTML export |
| `app_pages/4_Ranking.py` | Existing deterministic mission ranking, fixed backend weights, score cards, component chart, investigation view and exports |
| `app_pages/5_SI_Insights.py` | Unified physical input form, recorded-run presets, automatic assessment, evidence plots, interpretation, proposals, provenance and JSON export |
| `ui/common.py` | Repository-backed catalog; dynamically resolves registered CSV sources instead of hardcoding an investigation |
| `ui/source_research.py` | Preserved original question-and-document analysis, citations, uploads, session cache and API-error details |
| `scientific/schemas.py` | Validated request and common structured response |
| `scientific/evidence.py` | Read-only dynamic source discovery, SHA-256 checks, original-row matching, deterministic unit mapping, condition and measurement checks |
| `scientific/assessment.py` | Deterministic method selection, conservative matching, reviewed interpolation and existing ML inference integration |
| `scientific/interpretation.py` | Gemini interpretation of a fixed result; reference checks; separate, clearly labelled experimental proposals |
| `tests/test_assessment.py`, `tests/test_dashboard.py` | Scientific service and end-to-end widget regressions |
| `tests/browser_smoke.py` | Optional Edge / Playwright visual and download verification, with Gemini explicitly disabled |

## Routing and scientific limits

`scientific.assessment.assess(AssessmentRequest(...))` is the central service:

1. **OBSERVED** retrieves original measurements only when the material, geometry,
   dimensions, oxygen, pressure, gravity regime, airflow orientation and recorded
   sequence, specimen reuse, burn sides and initial carbon-dioxide conditions match.
   Multiple matches retain all values and their range; no arbitrary representative
   value or uncertainty interval is produced. This is retrieval of recorded runs,
   not validation of repeat experiments at the same nominal conditions.
2. **INTERPOLATED** requires an approved policy in
   `models/interpolation_policies.json`. There is deliberately no production policy
   for the current dataset. A policy must name its version, review, source scope,
   target/unit, physical filters, independently validated method and maximum
   bracket span. All other conditions must match; endpoints must use measured
   pressure, distinct specimens and unambiguous values. No extrapolation occurs.
3. **PREDICTED** calls the existing `ml.predict.assess`, loading the approved
   serialized preprocessing pipeline. The existing material / condition / category /
   numeric-range / joint-distance / independent-local-group checks and validated
   uncertainty gates remain mandatory. Current source-backed support must also
   match the model's physical regime and target unit. Registry pointers are read
   each request; updating an approved version needs no UI change.
   Overlapping approved physical tasks are rejected when their scientific context
   cannot be distinguished from the supplied conditions; no arbitrary model is selected.
4. **INSUFFICIENT_DATA** contains no numerical estimate. Related source records,
   domain boundaries, missing measurements and rejection reasons remain available.

The current trained Random Forest remains **RESEARCH_ONLY**. Its real artifact is
loaded with runtime and checksum verification to expose diagnostics, but it is not
used to generate production predictions. Its negative benchmark R², insufficient
independent calibration data, missing approved tolerances and domain limitations
are shown separately from individual uncertainty. No production registry pointers,
trained artifacts or promotion metadata were changed by this integration.

The original source CSV lacks measured atmospheric pressure. By default this
blocks exact matching. The user can explicitly accept the importer nominal
pressure **for observed retrieval**, with a visible limitation; this does not validate
pressure variation, interpolation, partial gravity or prediction. Gravity regime and
flow orientation are investigation/import metadata, not measured sensor values.
Time-resolved ventilation, exposure duration and measurement uncertainty remain
unavailable. Censored/over-range readings and inconsistent raw values are excluded
from exact numerical retrieval. Unknown materials/protocols are not silently assumed
compatible with an existing training task.

## Gemini and experimental proposals

Gemini runs after routing and receives the fixed assessment and bounded original
source excerpts. Its response schema has no field for changing the numerical
result, status, method or interval. Factual claims require supplied source IDs and
verbatim supporting quotations. Numerical prose is rejected, so UI numerical results
come from Python only. This validates traceability, not scientific correctness.

For insufficient evidence, a proposal can describe objectives, independent and
controlled variables, measurements, sensors, comparisons and knowledge gains.
Its physical conditions are copied from the user's request rather than invented.
It is labelled **SI-generated experimental proposal — not an existing NASA
investigation or a validated safe protocol**. If Gemini fails or is disabled,
database/ML results and original evidence remain available. No Gemini numerical
fallback is permitted. The original document-research assistant remains available
in an expander on the same page.

UI requests reuse existing SQLite answers but do not write questions or uploaded
documents to the shared database. Uploaded files remain unverified session data
and do not automatically enter official training, ranking or numeric assessment.
New compatible records imported through the backend are discovered dynamically.

## Visual verification and practical differences from Stitch

All five ZIP archives were extracted into separate `design_reference` directories;
their screenshots and HTML/CSS informed the shared typography, palette, sidebar,
borders, cards and layouts. Actual browser screenshots are in
`design_reference/verification/`.

The layout uses functional native Streamlit widgets rather than the exported HTML
controls. Selectors, tables and expansion panels therefore retain Streamlit's
dimensions and scrolling behavior. The sidebar filters replace decorative user
identity and simulated telemetry. Catalog content and card heights reflect real
records. Graphs use actual observations instead of the reference's illustrative
curves, fake confidence bands and sample performance values. Optical imagery,
editable ranking weights and uncertainty controls without backend support are
omitted or explicitly marked unavailable. No reference screenshot is embedded as UI.

## Run and verify

From the `fire-in-freefall` directory:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

To demonstrate observed retrieval: SI Insights → choose final carbon dioxide →
load `PSI-25:M1` → explicitly accept nominal pressure → run assessment. The
source-backed measurement is `0.61 %`. Changing gravity to lunar conditions
withholds a numerical result. This example is an archive lookup, not a safety claim.

Recorded-condition loading updates all fields before rendering the form. A visible
banner identifies the loaded run and its oxygen/pressure/gravity. Replacing the
environment with a mission preset explicitly warns when those values differ;
`Restore all recorded conditions` restores the last loaded record. For `PSI-25:B1`,
the matching conditions include oxygen `22.2 %`, nominal pressure `14.7 psi` and
gravity `0 g`; the observed final carbon-dioxide measurement is `0.44 %`.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe test_gemini.py
.\.venv\Scripts\ty.exe check app.py app_pages ui scientific --output-format concise
```

The service suite covers all twelve mandatory scenarios, plus nominal pressure,
research-only rejection, local data density, fabricated citations/numbers and labelled
proposals. Approved-model and interpolation tests use clearly identified temporary
fixtures; they never approve the production research model. Gemini responses are
mocked; no paid API call is needed.

Verification completed: 37 service/dashboard/transport/training regression tests
and 7 cache tests passed; `ty` passed. All five pages, automatic observed/refused
assessments, JSON downloads and a narrower viewport were exercised in Edge.
The running app was also exercised through Streamlit's localhost agent API:
Explorer filtering reduced the table from 129 to 11 runs; assessment completed
without exceptions. The research database SHA-256 remained
`e14492fdd28830feaec54a30379d93f587fc23915d6b988e7f57bae80a420475`.

For browser verification, install Playwright only as a development tool and use an
installed Edge browser; it is not a new runtime dependency:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.port=8765
# In another terminal:
.\.venv\Scripts\python.exe tests/browser_smoke.py
```

No database migration, original NASA file changes, colleague backend changes,
model retraining, Git commit or push is part of this implementation.
