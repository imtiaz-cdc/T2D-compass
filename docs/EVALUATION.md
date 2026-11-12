# T2D Compass evaluation report

Version 0.4.0 · evidence reviewed November 12, 2026

T2D Compass has passed local software checks. **Real-model quality scoring, independent reference approval, held-out accuracy and clinical interpretation review remain pending.** The team has reported its Databricks deployment; local results below do not independently establish deployed performance or evaluator access. No final demo video or completed clinical/model evaluation has been supplied.

This report covers the submitted two-tool scope: `find_completed_trials` and `get_trial_evidence_card`, the browser workflow and optional tool-using assistant. Comparing retrieved facts in an assistant answer uses those tools; a dedicated comparison tool is not implemented. ClinicalTrials.gov is the only data source. This is a research-support prototype, not treatment advice or an efficacy assessment.

## Recorded results

| Check | Date | Observed result | Evidence and limits |
| --- | --- | --- | --- |
| Automated regression suite | November 12, 2026 | 294 passed; 0 failures, errors or skips; JUnit suite time 6.979 seconds | [JUnit report](../eval/type2diabetes/results/submission-2026-11-12/tests.xml). Includes synthetic inputs and mocked model responses; not 294 clinical or real-model cases. |
| Static checks | November 12, 2026 | Passed for the source, tests, launcher and specified scripts | [Validation summary](../eval/type2diabetes/results/submission-2026-11-12/validation-summary.json). This records Python and installed dependency versions as well as check scope. |
| Generated three-file package | November 12, 2026 | Startup, browser HTML/assets, health and both MCP tools passed | [Package check](../eval/type2diabetes/results/submission-2026-11-12/package-smoke.json). The assistant correctly remained unavailable without user authorization; no model or deployment tested. |
| Public live-registry MCP replay | November 12, 2026 | Passed, 4 calls; median 0.078 seconds, slowest 0.469 seconds | [Live replay](../eval/type2diabetes/results/submission-2026-11-12/live-tool-replay.json). Actual local MCP calls against ClinicalTrials.gov; no model or deployed authentication tested. |
| Frozen-data MCP replay | November 12, 2026 | Passed, 4 calls; median recorded as 0.000 seconds, slowest 0.063 seconds | [Snapshot replay](../eval/type2diabetes/results/submission-2026-11-12/snapshot-tool-replay.json). Millisecond-rounded local tool timing, without a model. |
| Local HTTP transport | November 12, 2026 | Passed; healthy version 0.4.0, both tools discovered, `NCT03244800` retrieved | [HTTP check](../eval/type2diabetes/results/submission-2026-11-12/http-transport.json). Local loopback with frozen data; no deployed authentication tested. |
| Public live-registry MCP replay | October 28, 2026 | Passed, 4 tool calls; median 0.0625 seconds, slowest 0.360 seconds | [Saved live replay](../eval/type2diabetes/results/live-tool-replay.json). Local tool execution against the public API, without a model; this is dated evidence. |
| Frozen-data MCP replay | October 28, 2026 | Passed, 4 tool calls; median recorded as 0.000 seconds, slowest 0.078 seconds | [Saved snapshot replay](../eval/type2diabetes/results/snapshot-tool-replay.json). Durations are rounded to milliseconds; a recorded zero is not zero elapsed time. |
| Local HTTP transport | October 28, 2026 | Healthy version 0.4.0; both tools discovered; `NCT03244800` retrieved | [HTTP report](../eval/type2diabetes/results/http-transport.json). Loopback snapshot execution, not Databricks authentication. |
| Packaged browser | October 28, 2026 | Search and evidence-card checks passed; outside-scope warning observed | [Release record](../eval/type2diabetes/results/release-validation.json), [screenshot](../eval/type2diabetes/results/browser-evidence-card.png). Export download was not reverified for that release. |
| Reference comparison readiness | October 28, 2026 | 6 pending development cards; 0 compared cards/groups; accuracy `null` | [Readiness report](../eval/type2diabetes/results/pending-reference-check.json). An empty critical-error list is not clinical approval. |
| Real-model acceptance suite | Pending | 0 scored runs reported; no quality percentage | [12 scenarios](../eval/type2diabetes/agent_scenarios.json); two runs planned. |
| Independent clinical review and held-out accuracy | Pending | No approved accuracy result | [Reference form](../data/type2diabetes/review/reference-annotations.json). |

Tool timings describe four calls on a particular local run. They do not measure end-to-end assistant latency, hosted-app performance, concurrency, uptime or production capacity. Historical Alzheimer and obesity evidence is not counted as T2D performance.

## Dataset and inputs

The [core manifest](../data/type2diabetes/manifest.json) freezes ten public registry records captured October 28: **six development and four held-out**. The [agent manifest](../data/type2diabetes/manifest-agent.json) contains those six development records plus one separate active-study exclusion, `NCT05743387`. The exclusion is outside the ten-record accuracy denominator; the four held-out records are not in the scenario manifest.

Development selection covers registry-listed drug, behavioral and procedure interventions, each with and without posted results, under completed/interventional, treatment-purpose and explicit type 2 diabetes condition-label rules. This small convenience set is not representative of the disease or the registry. A procedure classification does not establish that a procedure is a therapy. Population, age, comorbidity, design and outcome differences remain important. See the [dataset guide](../data/type2diabetes/README.md) and [selection ledger](../data/type2diabetes/selection.json) for exact queries, ordering, exclusions and exposure rules.

Each frozen source retains its source URL, capture time and SHA-256. Held-out content must remain outside implementation changes and prompt tuning until the candidate and scoring rules are frozen. Preserve the first held-out run and label later checks influenced by its failures as regression tests. The larger 24-record benchmark is future work, not this submission's dataset.

The [scenario bindings](../eval/type2diabetes/bindings.example.json) use:

| Role | Input | Interpretation |
| --- | --- | --- |
| Completed, posted results | `NCT03244800` | First evidence-card example |
| Completed, no posted results | `NCT05790681` | Pediatric source context must be retained |
| Second completed record | `NCT04214600` | Keep depression/comorbidity context; no clinical-equivalence inference |
| Active exclusion | `NCT05743387` | Direct card must retain actual status and scope warning |
| Intervention search | `MEDI0382` | Frozen development-set search input |
| Missing record | `NCT99999999` | Absent in this snapshot; not a new live 404 observation |
| No-match search | `T2D_COMPASS_NO_MATCH_87C4` | Controlled frozen-set boundary input |

## Methodology

### Software and protocol verification

The automated suite checks structured input validation, mapping, provenance, search filtering and bounds, error handling, snapshot integrity, MCP registration and transport, browser requests, agent tool/call limits, and credential redaction. It uses public snapshots and clearly synthetic or mocked cases. Relevant checks include preserving every outcome/timeframe pair and arm/intervention relationship, distinguishing missing/false/zero values, and distinguishing completion from posted results.

MCP replays discover exactly the two intended tools, call `find_completed_trials` with `limit: 3`, then retrieve a card for each returned ID. Reports retain actual arguments, outputs, source modes and durations. Local HTTP verification separately starts the application, checks health, discovers tools and retrieves a known development card. A replay pass is not an independent source-accuracy judgment.

Run from the repository root, using a new results directory so preserved evidence is not overwritten:

```powershell
uv sync --locked --group dev
uv run python -m pytest -q --junitxml=eval/type2diabetes/results/local-check/tests.xml
uv run python -m ruff check src tests main.py scripts/build_bundles.py scripts/collect_type2diabetes_data.py
uv run python -m alz_compass.verify --output eval/type2diabetes/results/local-check/snapshot-tool-replay.json
uv run python -m alz_compass.verify_http --output eval/type2diabetes/results/local-check/http-transport.json
```

For a separate public-source freshness check, `uv run python -m alz_compass.verify --live --output eval/type2diabetes/results/local-check/live-tool-replay.json` contacts ClinicalTrials.gov. Label that result live and retain its retrieval time; live records may differ from frozen accuracy fixtures.

### Independent reference accuracy

Mohammad prepares expected values directly from source records. Chinelo independently verifies mappings and important relationships; they reconcile differences before approval. Generated evidence cards must not become their own reference answers.

The existing reference form requires all 14 configured field/groups per record, explicit annotation flags (including intentionally missing values), source locations, matching snapshot hash, approved review status and two distinct reviewer names. The scorer compares JSON values and whole groups exactly, preserving false versus zero. These are 14 groups, not every leaf field in the original record.

```powershell
uv run python -m alz_compass.review evaluate --output eval/type2diabetes/results/local-check/reference-evaluation.json
```

An exit code of 2 with `pending_review` is expected while references are incomplete. Zero approved comparisons means **pending/null accuracy**, not 0% or 100%. Report matched groups/compared groups and fully correct cards/compared cards separately. The maximum is 84 groups for six development records and 56 for four held-out records; use actual denominators. `--include-heldout` combines both splits, so derive held-out-only metrics from per-record results. Reviewers must classify clinically consequential errors separately.

### Real-model scenario evaluation

The [executable suite](../eval/type2diabetes/agent_scenarios.json) specifies six normal and six boundary cases, seven designated critical. It tests exact-ID retrieval, posted-results limitations, search followed by card retrieval, intervention filtering, comparison of supplied records, alternative wording, invalid/missing identifiers, no matches, controlled upstream failure, out-of-scope retrieval and an unsupported best-treatment request.

Run all twelve twice with a real tool-enabled model, retain both runs and independently score every expected behavior. A model returning an answer is an execution completion, not a quality pass. The team target is at least 11/12 passing in **each** run, every critical case passing, and no unresolved clinically consequential error in the evaluated answers. These are project acceptance targets, not GSA judging thresholds or general safety guarantees.

Before using the CLI scenario runner, verify its model route. It currently uses a Chat Completions adapter; the browser assistant uses a separate Responses gateway. Browser success does not validate that adapter. Obtain credentials through the approved environment without committing them. Once compatible model access is established:

```powershell
$env:ALZ_COMPASS_DATA_MODE = "snapshot"
$env:ALZ_COMPASS_MANIFEST = (Resolve-Path 'data/type2diabetes/manifest-agent.json').Path
uv run python -m alz_compass.agent --run scenarios --bindings eval/type2diabetes/bindings.example.json --repeats 2 --output eval/type2diabetes/runs/review-run-01.json
```

Use local stdio with `ALZ_COMPASS_MCP_URL` unset for the controlled outage fixture. A remote server does not receive the local injected fault; count that case only when the saved trace proves the fault was present. Frozen absent-ID and no-match cases must remain labeled as fixture behavior. Restore normal source settings after evaluation.

Retain model identity, prompt version, source mode, bindings, tool arguments/results, final answer, durations, execution status, human score, severity and reviewer/date. Report passes and not-run cases with denominators per run, plus median and slowest complete-task durations. Do not relabel mocked tests as model results. Local JSON traces are sufficient for this project's evidence trail; Phoenix/MLflow are optional instrumentation choices suggested by the starter.

## Security considerations

The two tools are read-only and use a fixed ClinicalTrials.gov API origin. They accept bounded search parameters or validated NCT identifiers rather than arbitrary URLs. The software checks exercise redirects, timeouts, error sanitization, source-text instructions, tool allowlisting and credential redaction. These checks are limited tests, not a penetration test or security certification.

Use public registry data and synthetic fixtures only. Do not put patient records, private agency information, credentials or private prompts into the prototype or shared reports. Treat registry text as untrusted evidence. Keep local HTTP on loopback and the deployed app behind Databricks authentication. The optional assistant's access token is request-scoped; never publish tokens or authorization headers. Review exported traces and screenshots before sharing. See [SECURITY.md](SECURITY.md) for boundaries and limitations.

The current label screen intentionally favors explicit type 2 diabetes labels and may omit broadly labeled relevant records. Eligibility is not proof of the actual enrolled population. Completion is not treatment success; absent posted results is not absence of publications. Matching outcome names do not establish equivalent endpoints, and this app does not extract numerical findings or rank treatments.

## Lessons learned and recommendations

1. Registry query relevance alone is insufficient. An explicit disease-label screen prevents known off-scope candidates while making possible omissions visible.
2. Traceable structured fields help reviewers find errors. Preserve source paths, URLs, timestamps, original outcome/timeframe pairs and uncertainty before asking a model to summarize.
3. Separate evidence types. Passing software tests, direct MCP calls, successful hosted authentication, real-model answers and clinical approval establish different things.
4. Preserve reproducibility. Frozen public records, hashes and distinct development/held-out sets support review; live calls separately test current access and freshness.
5. Complete the current evaluation before expanding scope. Priorities are independent references, two scored scenario runs, deployed access/export checks and the demonstration recording. A third tool and larger benchmark remain future work.

## Submission basis

The [GSA event page](https://www.gsa.gov/super-intelligence/si-community-of-practice/events-and-training/mcp-server-and-si-agent-government-hackathon), checked November 12 and labeled updated November 4, requests evaluation methodology, metrics, security considerations and lessons. This document supplies that structure with actual local evidence and explicit pending results. The [starter evaluation guide](https://github.com/GSA-TTS/mcp-hackathon-template/blob/f39249f1768309e3ef8b31742390a4f3a656b5f3/eval/README.md) motivates evaluating whether a model can use the tools; it does not make the suggested Phoenix harness the only accepted method. See [the submission checklist](SUBMISSION.md) for remaining artifacts and release gates.
