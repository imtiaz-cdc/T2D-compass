# Release notes

## 0.4.1 — November 23, 2026

- Preserves exact primary-outcome and timeframe blocks in assistant responses.
- Checks study identifier, outcome index, measure, and timeframe against retrieved evidence.
- Uses source-backed cards when required blocks change or are omitted, while retaining the model draft and check result in the trace.
- Adds 16 regression tests; the release passed 310 software tests and lint.
- Records two hosted checks with all five reviewed final outcome/timeframe pairs preserved.

This bounded check protects the specified blocks; it does not validate every sentence of a model response. See the [release validation](eval/type2diabetes/results/timing-fix-2026-11-23/validation-summary.json) and [evaluation report](docs/EVALUATION.md).

## 0.4.0

- Introduces the type 2 diabetes scope with two MCP tools: completed-trial search and evidence-card retrieval.
- Provides browser search, card inspection, JSON export, and an optional Databricks assistant.
- Adds public registry snapshots, scenario definitions, source manifests, and review forms.

The November 23 reference audit uses the preserved 0.4.0 candidate. Its results are recorded separately from 0.4.1 validation.
