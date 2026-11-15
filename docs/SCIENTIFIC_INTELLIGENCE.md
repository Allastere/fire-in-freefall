# Scientific intelligence implementation ? 2026-11-15

Four pages: Overview, Explorer, Ranking, SI Insights. Exactly three primary scientific tasks: PREVENTION, DETECTION, SUPPRESSION. Comparison stays inside SI Insights. No remote Git operation was performed.

## Data audit

19 investigations; 1,810 experiments; 1,810 sample records; 1,810 condition records; 6,199 measurements; 15 catalog findings; 78 registered source files.
All registered source files exist locally and match their SHA-256 digests. Import labels: 4,632 ML_ELIGIBLE, 1,552 EVIDENCE_ONLY, 15 NEEDS_REVIEW.
Import eligibility is not deployment approval. The new independent provenance checks accept 2,561 measurement rows: either an identical original CSV record plus raw-value trace, or an explicitly traced reported document table. The remaining 3,638 rows stay available as context needing additional source review; they are not silently promoted to exact observations.
Sample identifiers are counted separately from observations. Reused specimens and shared sessions are connected before splitting. Detailed per-target/subtype counts, missingness, duplicate observations, materials, phases and censoring are in SCIENTIFIC_DATA_AUDIT.json.

## Architecture decision

A shared registry of target- and regime-specific models was retained. A universal model or exactly three pillar models would mix incompatible physical targets, apparatus, fuel phases and units. Multi-output modeling was rejected because the available targets have different censoring, missingness and observation definitions. Incremental learning is unnecessary at this data volume.
Four new tasks use only original FLEX/PSI-69 microgravity liquid droplets, separately for Methanol and n-Heptane: overall droplet burning-rate constant and natural radiative/diffusive extinction time. Destructive droplets are identified by FLEX identifier and grouped by test date. Initial source columns provide oxygen, pressure, diameter and introduced carbon dioxide/helium/nitrogen composition. No end-state measurement is a predictor.
Extinction-time training excludes disruption, completion and operator termination. Non-exact, over-range, missing-identity, unmatched-source and invalid-composition records are excluded. Different particle statistics and calibration dust are never pooled.
The prior PMMA slab/chamber-carbon-dioxide task was retrained too, preserving its frozen independent benchmark and prior versions. No additional compatible PMMA samples appeared.

## Evaluation and retraining

Executed: `python -m ml.train --all`. This runs each configured task sequentially in its own CPU process. `python -m ml.train --task <id>` and `python -m ml.audit` remain reusable.
Candidates evaluated on grouped development folds: mean DummyRegressor baseline, interpolation baseline, linear regression, Ridge, Random Forest, Gaussian Process and CPU CatBoost. CatBoost is pinned in requirements-ml.txt. An MLP was removed from default candidates because these independent sample counts do not justify neural-network complexity.
Algorithm selection uses GroupKFold only on development data. Calibration and benchmark groups remain separate and frozen. New challengers are compared against previous versions on the same benchmark. Hyperparameters, source/dataset/code fingerprints, feature domains, model hashes, intervals, UTC training dates and promotion decisions are versioned.

| Task | Eligible observations | Development / calibration / benchmark | Selected algorithm | Benchmark MAE | Baseline MAE | R? | Status |
|---|---:|---|---|---:|---:|---:|---|
| flex_heptane_burning_rate | 105 | 74 / 17 / 14 | linear_regression | 0.0459001 | 0.119981 | 0.841994 | RESEARCH_ONLY |
| flex_heptane_extinction_time | 52 | 34 / 6 / 12 | catboost | 1.9483 | 2.7826 | 0.462237 | RESEARCH_ONLY |
| flex_methanol_burning_rate | 149 | 92 / 22 / 35 | linear_regression | 0.0339362 | 0.125314 | 0.902447 | RESEARCH_ONLY |
| flex_methanol_extinction_time | 103 | 69 / 15 / 19 | gaussian_process | 2.37095 | 5.11718 | 0.738486 | RESEARCH_ONLY |
| pmma_slab_co2_final | 19 | 9 / 4 / 6 | random_forest | 0.372171 | 0.420556 | -1.83611 | RESEARCH_ONLY |

Units: extinction time in seconds; droplet burning-rate constant in mm?/s; PMMA carbon-dioxide error in percentage points.
**No model is currently approved for scientific numerical inference.** All five remain RESEARCH_ONLY. Approved physical error tolerances are absent; calibration groups do not establish a finite interval at the requested coverage, and some joint-domain coverage gates fail. A good individual MAE does not override these blockers.
Numerical ignition probability, detector efficiency/response time, general flame-spread prediction, solid-fire suppression thresholds, and partial-gravity predictions remain unsupported. Detection uses separately defined observations/statistical descriptions; no detection model is forced from the small subtype-specific tables. Classification and survival models were not trained because independent, source-validated outcome/censoring contracts are not yet established.
Sequential measured estimator training time: 23.70 seconds, excluding archive audits and process startup. Random Forest uses one worker; CatBoost two CPU threads; no GPU or nested training. Total-process peak RAM was not measured and is not claimed. Exact Gaussian Processes were evaluated only on these small per-regime training sets.

## Routing, cache and scientific output

Question ? dynamically resolved material/target scope ? per-characteristic source-backed retrieval ? independently approved interpolation/ML when appropriate ? evidence-gap answer. A successful characteristic is retained when another is unsupported. Research-only models never become numerical UI predictions.
Routes: CACHED, OBSERVED, ESTIMATED, INSUFFICIENT_DATA. Result evidence retains OBSERVED, DERIVED, INTERPOLATED, ML_PREDICTED or EVIDENCE_ONLY; CACHED is only a retrieval route. Cache hits bypass interpretation and inference.
Full structured assessments reuse the existing SQLite llm_cache table with an assessment prefix and a session fallback. Keys cover normalized question, pillar, material/agent/instrument scope, all optional states/ranges, dataset fingerprint, registry pointers, processing-code hashes, router version, prompt version and actual Gemini model. Failed/rejected Gemini responses are not saved as successful assessments. A read-only cache failure leaves the answer usable.
ANY is unrestricted retrieval; UNKNOWN is missing physical knowledge. Exact zero is retained. Ranges filter observations and never become model midpoints. Required missing features prevent inference. Joint-domain, independent uncertainty, physical regime and model-approval gates remain mandatory.
Explicit archival lookup can retrieve nominal pressure metadata with a warning; it does not certify measured pressure or permit changed conditions to reuse a value. PSI-25:B1 is resolved from source evidence, with no hardcoded numerical result. Conditions changed to lunar gravity invalidate that observed answer.
Gemini receives the original question, fixed numerical results, original evidence excerpts, ranked investigation metadata and explicitly unverified catalog findings. Citations require supplied IDs and exact source quotes. Numerical prose is rejected; Python owns numerical values. Unavailable or invalid Gemini leaves backend answers, figures and references intact.

## Product and ranking

The paper/graphite/cobalt/orange design is preserved. After analysis, configuration collapses and the direct answer, available indicators, one primary Plotly figure and compact source summary appear first. Definitions, tables, model reliability, related research and original evidence are expandable.
All task options come from the archive. Mission scenarios include ISS/Spacecraft, Lunar Habitat, Martian Habitat, Pressurized Rover, Earth and Custom. Selecting a label changes no values. Explicit preset application fills only unrestricted fields. Detection supports distinct aging/mixing constraints and measurement technologies; suppression filters intentionally introduced diluents rather than combustion-generated gas.
Ranking supports multi-pillar investigations and the actual question, material, conditions and source-backed coverage. Relevance, condition-match counts and evidence availability remain separate from physical hazard and prediction uncertainty. The Ranking page and SI share the same function.
The reported Streamlit error was real: app.py persisted ranking_inspect_* button values and restored them as application state. Button keys are now excluded both when saving and restoring, inspection uses an independent ranking_selected_psi_id, and navigation/rerun regressions exercise this path.

## Challenge review

The [official NASA challenge summary](https://www.spaceappschallenge.org/2026/challenges/flame-in-freefall/) explicitly calls for an interactive dashboard that summarizes, ranks and interprets combustion findings for human exploration. Discovery, comparison, provenance and research gaps support that objective; custom ML is supporting functionality, not a substitute for it. The full challenge page returned HTTP 502 during review; only the indexed official summary was accessible, so additional requirements beyond the supplied specification are not asserted.

## Scientific limitations

An importer verified label does not prove a physically independent sample or complete measurement uncertainty. Document-table traces are reported evidence, not a new independent digitization/replication of the source. Untested compatibility, missing conditions and unverified catalog claims remain explicit. DAFT dust is distinguished from combustion smoke; GMD/CMD/MMD/TEM/Moment observations stay separate. Operator termination is not natural extinction; liquid-droplet results do not establish solid-material fire safety. Findings are research evidence, never operational firefighting instructions.

## Files

Created: scientific/archive.py, scientific/intelligence.py, scientific/cache.py, ui/intelligence_workspace.py, ml/audit.py, ml/flex.py, tests/test_intelligence.py, audit/training JSON reports, this report, specialized model registries and browser screenshots in design_reference/verification-intelligence/.
Updated: app.py, all four app_pages scripts, ui/data.py, ml/dataset.py, ml/preprocessing.py, ml/predict.py, ml/uncertainty.py, ml/train.py, ml/tasks.json, requirements-ml.txt, tests/test_dashboard.py, tests/browser_smoke.py, Context.md and README.md. Existing raw sources and previous model versions are preserved.

## Verification actually executed

- Full offline application/scientific suite: 68 tests passed (`python -m unittest discover -s tests -v`).
- Final router suite after additional Gemini, registry and persistent-cache checks: 12 tests passed.
- Existing SQLite/Gemini transport cache suite: 7 tests passed (`python test_gemini.py`).
- Type checking: `ty check app.py app_pages ui scientific ml` passed.
- Running Streamlit agent API: Overview, SI Detection assessment without an API call, Ranking inspection of PSI-25, Explorer redirect and repeated Ranking navigation passed.
- Microsoft Edge/Playwright: all four pages, detection question answer, source-backed Plotly figure and 600-pixel layout passed. Screenshots are in `design_reference/verification-intelligence/`.
- PSI-25:B1 source observation is retrieved; changed gravity refuses the old numerical answer. Optional values and explicit zero, independent grouping, frozen benchmarks, valid interpolation/ML fixtures, mixed outcomes, cache invalidation, source citations and API failure handling were exercised.
- Real paid Gemini calls were not made. Its SDK serialization, valid structured answers, invalid quotations/numerical prose, unavailable API handling and caching were tested offline.
- Development-only assessment cache entries were removed after verification. Scientific tables and the original three cached Gemini answers were compared against the pre-task database before restoring identical database bytes. Original sources and trained historical versions are preserved.
- The temporary localhost verification server was stopped. No commit, push or remote branch modification was performed.

## Subsequent Gemini validation fix

Supersedes the earlier numeric-prose ban and offline-only verification note above. A live B1 request successfully
returned the source-cited final carbon-dioxide observation. A blanket prohibition on digits was rejecting correct
answers; numerical claims now must match fixed backend values associated with their cited source. Unknown values
remain rejected. Structured source_id/quote citations override legacy inline page/DOI instructions, preventing CSV
records from acquiring fabricated page references. Validation failures get one bounded correction attempt. API
status codes, invalid schema and scientific validation failures are distinguished with redacted error details.
Verified: 13 routing/validation tests, 7 cache tests and 1 SDK transport test; type checking passed. Live verification
used cache_writes=False and did not modify the scientific database. No palette or layout changes were made.
