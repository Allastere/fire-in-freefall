## Scientific intelligence update

SI Insights now centers on Prevention, Detection and Suppression questions. Direct observations take priority;
validated numerical estimates are used only when an independently approved model applies. All current model candidates
remain RESEARCH_ONLY. Unknown conditions are never replaced with zero, and partial-gravity results are not invented.

Run the app with `streamlit run app.py`; install optional training dependencies with `pip install -r requirements-ml.txt`.
Audit with `python -m ml.audit`; retrain sequentially on CPU with `python -m ml.train --all`.
See [scientific architecture and validation](docs/SCIENTIFIC_INTELLIGENCE.md) for current data counts, models and limitations.

# Flame in Freefall

Scientific material assessment and decision-support workspace for NASA combustion research, using Swiss Scientific Editorial V2.

## Run locally

From the repository directory in PowerShell, using the existing virtual environment:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

For a new environment, install the pinned packages in `requirements.txt` first.
Copy `.env.example` to `.env` and set `GEMINI_API_KEY` to enable new Gemini analyses.
`GEMINI_MODEL` overrides the default from `config/settings.py`. Never commit `.env`.
All four workspaces and scientific evidence retrieval work without a Gemini API key.

## Workspaces

| Page | Purpose |
| --- | --- |
| Overview | Compact catalog, counts, research highlights, DOI references and original files |
| Explorer | Material, gravity, outcome and numerical filters; measurements and raw rows; CSV export |
| Ranking | Mission-specific deterministic scores and weighted component breakdowns |
| SI Insights | Assess Material, Find Materials, Compare Materials and advanced Predict Parameter; evidence, synthesis and sources on demand |

Pages live in `app_pages/` and use `st.navigation`; `app.py` provides horizontal navigation and a discreet footer.
Pillar and facility filters are available from the header settings control and apply across pages. Mission selection lives in Ranking and SI Insights.

## Data and provenance

The application reads the existing `data/database/research.db` through `database/repository.py`.
The current snapshot contains 5 investigations, 134 runs and 783 measurements. Of the runs,
129 are backed by the local BASS-II master CSV. Other seeded records require source verification.
The interface labels these origins and excludes catalog seeds from comparisons and ranking by default.
CSV availability does not independently verify inferred outcomes, assumed conditions or catalog summaries.

Original BASS-II CSV, PDF and DOCX files are available under `data/raw/PSI-25/` and downloadable in the app.
For the other investigations, use the NASA PSI links to obtain and verify the original documents.
Research highlights are catalog claims; an unconfirmed local quote is labelled accordingly.
CSV record numbers exclude the header and are not PDF pages. PDF references in SI Insights identify
the physical page in the PDF; DOCX and text files have no reliable page number.

Explorer accepts CSV, PDF, DOCX and UTF-8 TXT uploads. It keeps them in `st.session_state`, never in the
shared database. Limits: 10 MB per file, 10,000 CSV records and 300 PDF pages. CSV mapping reuses the
backend dictionary and normalization helpers; inspect the mapping and original row before using an
unfamiliar file. Unmapped columns remain in the original data. Scanned PDFs need a text layer.
CSV uploads can be compared in the current session; uploaded documents can be included in SI Insights.
Session uploads are excluded from the official ranking and disappear when the session ends.

## SI analysis and caching

In SI Insights, select a mode and material scope, optionally specify environmental conditions, then click **Run assessment**.
For a recorded measurement, load a source-verified experiment. No nominal-pressure checkbox is required for archive lookup.
The original **Analyze evidence** document workflow remains under **Compare experimental runs / source research tools**.
The application sends the question, scenario and a bounded selection of original source excerpts to Gemini.
It validates returned source IDs and exact supporting quotations before displaying the structured answer.
This checks traceability, not whether the interpretation is scientifically correct.
Unavailable sources, missing API keys and API errors produce an explanatory message.

The Gemini client supports the SQLite `llm_cache` table. Interactive SI Insights reads existing cached answers
but does not write new user questions or uploaded documents to this shared table. New validated answers
are cached only within the current session, up to 20 answers. This preserves the tracked research database.

## Experimental model training

An optional CPU training pipeline is available for the source-backed BASS-II PMMA slab CO₂ task.
It compares linear regression, Random Forest, Gaussian Process and a small MLP against baselines,
with frozen specimen/session groups and independent calibration/benchmark data.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ml.txt
.\.venv\Scripts\python.exe -m ml.train --audit-only
.\.venv\Scripts\python.exe -m ml.train
```

Models and immutable training reports are stored in `models/<task>/versions/<version_id>/`.
The initial model is **RESEARCH_ONLY**: benchmark R² is negative, calibration data is insufficient,
and scientific tolerances have not been approved. SI Insights loads its checked artifact for diagnostics
and uses only an approved model for numerical prediction.
See [training results](docs/ML_TRAINING_RESULTS.md) and [the expansion design](docs/ML_RETRAINING_DESIGN.md).
New compatible imported records are read dynamically; unknown protocols remain excluded until reviewed.
`ml.predict.assess` loads only an approved model and otherwise returns `INSUFFICIENT_DATA`.

The redesigned SI Insights workspace automatically routes requests to original measurements,
reviewed interpolation, approved ML inference or an explicit refusal. Gemini interprets the fixed
result and can propose clearly labelled follow-up experiments. See the
[current editorial upgrade guide](docs/EDITORIAL_V2_UPGRADE.md) for files, scientific limits,
reference-design differences, launch instructions and browser verification.

## Automated validation

```powershell
.\.venv\Scripts\python.exe -m database.repository
.\.venv\Scripts\python.exe test_gemini.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Cache and dashboard tests use mocked Gemini responses and temporary data. They do not call a paid API
or write to the research database. No mathematical risk envelope or synthetic flame-spread curve is generated
from missing data; relevance scores are not safety ratings.

## NASA data attribution

The app displays DOI and citation metadata supplied by the backend catalog. Consult the investigation
pages for the authoritative dataset descriptions and recommended citations:

- [BASS-II — DOI 10.60555/4qc4-de67](https://doi.org/10.60555/4qc4-de67)
- [FLEX — DOI 10.60555/mbq8-0451](https://doi.org/10.60555/mbq8-0451)
- [SAME — DOI 10.60555/gd4k-8h62](https://doi.org/10.60555/gd4k-8h62)
- [SAFFIRE-I — DOI 10.60555/0t15-1z43](https://doi.org/10.60555/0t15-1z43)
- [ACME CFI-G — DOI 10.60555/cyt1-kh64](https://doi.org/10.60555/cyt1-kh64)

## SI Development Disclosure

Codex assisted with implementation, integration and automated testing. Gemini is used at runtime for
source-based interpretation when the user requests an analysis. SI-generated findings require verification
against original scientific documents and must not be treated as certified engineering recommendations.

Project license: Apache License 2.0; see `LICENSE`. Dependencies retain their respective licenses.
