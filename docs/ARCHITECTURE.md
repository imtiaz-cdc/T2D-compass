# Architecture and tool contracts

T2D Compass 0.4.1 uses a single FastMCP application with two tools and an optional model-driven agent. `main.py` imports the source package directly, so Databricks can start the app from the complete checkout after installing `requirements.txt`.

## Responsibilities

| Component | Responsibility |
| --- | --- |
| `app.py`, `config.py` | Compose the service, register routes/tools, select stdio or HTTP |
| `tools/` | One file per tool, Pydantic input constraints, read-only annotations |
| `registry.py` | Fixed ClinicalTrials.gov API origin or hash-checked frozen source reader |
| `disease.py`, `service.py` | Explicit T2D condition screen, completed/interventional filtering, bounded search and safe errors |
| `mapping.py` | Evidence-card extraction with original ordering, source paths, missing values and review flags |
| `webapp.py`, `web/` | Browser search/card workflow, JSON exports and optional assistant |
| `agent.py`, `agent_prompt.txt` | Tool-use loop, limits, trace recording and scenario harness |
| `answer_fidelity.py` | Check outcome/timeframe blocks against retrieved cards and retain the original model draft when source-backed output is used |
| `gateway.py` | Browser Responses adapter using the current user's forwarded Databricks token |
| `review.py` | Fourteen-group comparison against independently approved reference annotations |

No database or patient-data store is required. The app does not write to ClinicalTrials.gov. Registry text remains untrusted source data.

## Tool semantics

`find_completed_trials(intervention=None, limit=3)` accepts at most 120 intervention characters and an integer limit from 1 to 5. It searches the fixed disease query, checks completed/interventional status and explicit supported T2D condition labels, removes duplicates and returns bounded candidates. The service scans at most three pages. It reports coverage and incomplete-search conditions rather than claiming exhaustive retrieval.

`get_trial_evidence_card(nct_id)` accepts the canonical `NCT` plus eight-digit pattern. It returns one card with design, enrollment type, eligibility, arms/interventions, registered primary outcomes/timeframes and results availability. It retains out-of-scope direct lookups with warnings. It does not extract numeric outcome results or make a treatment comparison.

See [FIELD_DICTIONARY.md](FIELD_DICTIONARY.md) for exact output fields. Errors use structured codes and retry guidance. Source failures do not become invented records.

## Interfaces and authorization

Default local transport is stdio. HTTP exposes `/`, `/health`, `/mcp`, `/api/status`, `/api/search`, `/api/card` and `/api/ask`. `/health` reports version, condition and source mode. Browser tool actions use an in-process MCP client. External MCP clients use `/mcp` and must satisfy hosted authentication independently.

Databricks supplies the app port. The hosted browser assistant reads the request's forwarded user token and calls the workspace Responses gateway. Its loop is bounded to six model calls, eight tool calls and 150 seconds. Ordinary local search/card use does not require an LLM. The separate CLI Chat Completions adapter must be verified for the chosen environment before model evaluation.

Authentication is a deployment boundary, not a feature supplied by the local HTTP listener. See [SECURITY.md](SECURITY.md).

## Design choices and limitations

1. Two task-oriented tools keep selection and evidence retrieval explicit and observable.
2. Source text, links, timestamps and JSON field paths make the extraction reviewable. They do not certify source accuracy.
3. Conservative disease filtering reduces broad-query mismatches but can omit relevant records with generic labels.
4. Snapshot mode makes development checks reproducible. Its literal search differs from live registry relevance search.
5. The compatible module and environment-variable names avoid deployment churn while the displayed disease scope remains T2D.

A dedicated comparison tool, numeric effect synthesis and a larger benchmark are future work outside this submission's implemented scope.
