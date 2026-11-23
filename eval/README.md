# Evaluation

The [evaluation report](../docs/EVALUATION.md) describes the methods, results and limitations. Results are recorded separately for software behavior, model scenarios, source extraction and hosted answers.

## Results and records

| Evaluation | Result | Evidence |
| --- | --- | --- |
| Software, version 0.4.1 | 310 tests and lint passed | [November 23 validation](type2diabetes/results/timing-fix-2026-11-23/validation-summary.json) |
| Hosted answers, version 0.4.1 | Two selected live cases completed in 11.548 and 11.571 seconds; all five final outcome/timeframe pairs matched their source | [Hosted-check summary](type2diabetes/results/timing-fix-2026-11-23/validation-summary.json) |
| Model scenarios | 24 completed snapshot executions: 12 scenarios, repeated twice. Supplied team reviews report 12/12 scenario passes and 7/7 critical passes in each repeat | [Original traces](../deliverables/2026-11-23/t2d_eval_runs_traces_2026-11-21.zip) · [Reviewer documents](../deliverables/2026-11-23/README.md) |
| Source extraction, version 0.4.0 | 140/140 field groups and 10/10 cards matched: 84/84 development groups and 56/56 held-out groups | [Source-reference audit](type2diabetes/results/reference-audit-2026-11-23/README.md) |

The source-reference audit used two assistant source-reading passes and exact comparison with the frozen candidate. It is a technical agreement result, separate from independent human clinical approval. The two hosted cases do not establish a full live-suite pass.

## Evaluation inputs

- [Scenario definitions](type2diabetes/agent_scenarios.json): twelve cases, including seven critical cases.
- [Bindings](type2diabetes/bindings.example.json) and [scenario guide](type2diabetes/README.md): frozen inputs and expected behavior.
- [Source manifest](../data/type2diabetes/manifest.json): six development and four held-out records. The active-study exclusion is separate from the accuracy denominator.
- [Original review form](../data/type2diabetes/review/reference-annotations.json): preserved blank human-approval fields. The approval-gated scorer consequently retains null accuracy; it is separate from the completed technical audit.

## Reproduction and history

Use the commands in [QUICKSTART.md](../QUICKSTART.md). Save new results under a new dated directory and preserve the original runs. Snapshot, synthetic and live checks must retain their execution labels. Keep held-out records out of prompt tuning and implementation decisions.

The original source audit is pinned to revision [`ae42c913c4870376c269a387713cf2718df4eac4`](https://github.com/imtiaz-cdc/T2D-compass/tree/ae42c913c4870376c269a387713cf2718df4eac4). Follow its [reproduction note](type2diabetes/results/reference-audit-2026-11-23/README.md); the audit predates the version 0.4.1 prompt correction.

Earlier [October 28](type2diabetes/results/release-validation.json) and [November 12](type2diabetes/results/submission-2026-11-12/validation-summary.json) checks remain dated evidence. The [original reference-readiness check](type2diabetes/results/pending-reference-check.json) records zero approved comparisons at that stage.
