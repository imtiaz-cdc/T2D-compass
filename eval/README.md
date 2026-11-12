# Evaluation evidence

Start with the [evaluation report](../docs/EVALUATION.md) for methodology, inputs, actual results, security and lessons. T2D Compass version 0.4.0 has two MCP tools. Local software verification is available; real-model scoring, independent clinical references and held-out accuracy are pending.

| Location | Purpose |
| --- | --- |
| [type2diabetes/agent_scenarios.json](type2diabetes/agent_scenarios.json) | Twelve scenario definitions, seven critical cases, two planned runs and explicit expected behaviors |
| [type2diabetes/bindings.example.json](type2diabetes/bindings.example.json) | Frozen development/exclusion inputs; source-checked fixture roles, not clinical approval |
| [type2diabetes/README.md](type2diabetes/README.md) | Scenario fixture context and boundaries |
| [November 12 validation summary](type2diabetes/results/submission-2026-11-12/validation-summary.json) | Fresh repository-preparation checks and their limits |
| [November 12 tests](type2diabetes/results/submission-2026-11-12/tests.xml) | 294 passed; zero failures, errors or skips; software tests, not clinical cases |
| [October 28 release validation](type2diabetes/results/release-validation.json) | Preserved local release checks, including dated live/snapshot MCP replay and browser evidence |
| [Pending reference check](type2diabetes/results/pending-reference-check.json) | Zero approved comparisons; accuracy remains null |
| [Source manifest](../data/type2diabetes/manifest.json) | Ten frozen public records: six development, four held-out |
| [Reference form](../data/type2diabetes/review/reference-annotations.json) | Blank independent review fields requiring approval before accuracy scoring |

The additional active-study fixture is outside the core accuracy denominator. Do not use held-out records for prompt tuning. Comparison scenarios retrieve cards with the existing tools; no third comparison tool is claimed.

Run the documented commands from the repository root. Save new results under a new dated directory; retain original reports and failed runs. Label snapshot, synthetic, live, local and deployed execution accurately. Review traces for credentials and private content before committing. A completed model answer is not a scored pass, and results from previous disease versions do not transfer to T2D Compass.
