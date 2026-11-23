# Type 2 diabetes evaluation suite

[agent_scenarios.json](agent_scenarios.json) defines twelve cases: six normal cases and six boundary cases, including seven critical cases. The acceptance target is at least 11/12 passes in each of two repeats, with every critical case passing.

The [November 21 trace archive](../../deliverables/2026-11-23/t2d_eval_runs_traces_2026-11-21.zip) contains all **24 completed snapshot model executions**. The supplied team reviews report **12/12 scenario passes and 7/7 critical passes in each repeat**. Execution completion and reviewer assessments are recorded separately. The scenario definition retains its original `not_run` metadata; dated traces and reviewer documents record subsequent execution.

The [evaluation report](../../docs/EVALUATION.md) also covers the completed version 0.4.0 source-reference audit and the separate version 0.4.1 software and hosted checks. The proposed twenty-case expansion is outside this suite.

## Frozen bindings

Use [bindings.example.json](bindings.example.json) with [the agent manifest](../../data/type2diabetes/manifest-agent.json).

| Binding | Value |
| --- | --- |
| Completed with posted results | `NCT03244800` |
| Completed without posted results | `NCT05790681` |
| Different completed comparison record | `NCT04214600` |
| Active exclusion | `NCT05743387` |
| Intervention text | `MEDI0382` |
| Missing ID in the frozen snapshot | `NCT99999999` |

The no-results example concerns children and teenagers; answers must retain that population context. Comparison cases describe registry differences, without establishing equivalent outcomes or treatment effects. The active exclusion remains outside the ten-record accuracy benchmark.

`NCT99999999` is absent from this snapshot; that does not establish a current live HTTP 404. `T2D_COMPASS_NO_MATCH_87C4` has no matches in the frozen set. The two archived outage cases retain the explicit snapshot-only injected failure.

## Run another evaluation

From the repository root, set `ALZ_COMPASS_DATA_MODE` to `snapshot` and `ALZ_COMPASS_MANIFEST` to the absolute path of `data/type2diabetes/manifest-agent.json`. Use the runner with `--run scenarios --bindings eval/type2diabetes/bindings.example.json --repeats 2` after configuring and verifying its model route. The CLI and hosted browser use different gateway adapters; verify the route being evaluated. Restore the default manifest afterward.

Save new traces and assessments separately from the original archive. Preserve source mode, model identity, actual tool calls, failures and reviewer attribution. Do not use held-out records for prompt tuning.

## Supporting checks

- [Source-reference audit](results/reference-audit-2026-11-23/README.md): 140/140 groups matched across ten cards in two splits. This assistant technical audit does not supply independent human clinical approval.
- [Version 0.4.1 validation](results/timing-fix-2026-11-23/validation-summary.json): 310 software tests, lint and two selected hosted cases with all five final outcome/timeframe pairs retained.
- [Fixture validation](results/fixture-validation.json): ten core records, six development/four held-out, one separate exclusion, hashes and all twelve prompt bindings.
- [Snapshot binding validation](results/binding-validation.json): development/exclusion loading, search, card roles and error cases; no held-out records loaded.
- [Original reference-readiness check](results/pending-reference-check.json): six unapproved development cards, zero compared cards and null accuracy. The original human-approval gate is preserved separately from the completed technical audit.

The [dataset guide](../../data/type2diabetes/README.md) documents selection, provenance and source limitations.
