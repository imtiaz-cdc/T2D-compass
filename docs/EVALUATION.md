# Evaluation

Updated November 23, 2026. The current application is **0.4.1**, with prompt **t2d-compass-1.1**. The source-reference audit evaluates the preserved **0.4.0** candidate. ClinicalTrials.gov is the only study-data source.

## Results

| Evaluation | Candidate and date | Result |
| --- | --- | --- |
| Software tests | 0.4.1 · November 23 | 310 tests passed; lint passed. Includes input validation, mapping, transport, browser, model-adapter and outcome/timeframe regression checks. |
| Hosted assistant checks | 0.4.1 · November 23 | Two selected questions completed in 11.548 and 11.571 seconds. Each retrieved one live evidence card; all five final primary-outcome/timeframe pairs matched the retrieved source. |
| Model scenario executions | 0.4.0 · November 21 | 12 scenarios run twice: 24 completed executions, 52 model turns and 38 tool calls. Recorded model: `databricks-gpt-5-5`; snapshot mode; prompt `t2d-compass-1.0`. |
| Team scenario assessments | November 21 | Chinelo Njoku's and Mohammad Alpha Jalloh's supplied reviews report 12/12 scenario passes and 7/7 critical passes in each run. Original review documents and raw trace fields are preserved. |
| AI-assisted source-reference audit | 0.4.0 · November 23 | 140/140 configured field groups and 10/10 cards matched: development 84/84 groups across six cards; held-out 56/56 groups across four cards. |
| Browser checks | November 23 | Nine direct checks passed for search, card retrieval, scope warnings and exports in an authorized Databricks session. |

Software tests include controlled and mocked cases. Scenario execution, reported reviewer assessments, source agreement and hosted checks measure different aspects of the system. None is a general measure of clinical accuracy.

The November 21 complete-task median was 17.508 seconds, with a range of 2.787–36.370 seconds; recorded suite duration was 453.312 seconds. The two controlled upstream-failure cases include the intended snapshot-only error. Expected `not_found`, `no_matches` and injected `upstream_error` outcomes are distinguished from execution failures. No no-tool baseline was run.

## Outcome/timeframe correction

An earlier assistant answer changed a zero-minute pre-meal sample into an after-meal sample; the retrieved evidence card was correct. Version 0.4.1 requires exact study, outcome-index, measure and timeframe blocks. When a block is absent or changed, a bounded check presents the source-backed card while preserving the model draft and check result in the trace.

The two hosted checks used NCT03244800 and NCT05790681. Their final answers retained the pre-meal boundary, all five primary-outcome/timeframe pairs, results-availability distinctions and relevant population context. This checks the required blocks rather than the meaning of every generated sentence. Two selected cases do not establish a full live-suite pass.

See the [release validation summary](../eval/type2diabetes/results/timing-fix-2026-11-23/validation-summary.json). The changed prompt was not used to overwrite or relabel the original 0.4.0 source-audit result.

## Source-reference method

The candidate source, prompt, field contract and exact JSON scoring rule were frozen before held-out annotation. Two separate AI assistants read the original frozen records and field dictionary without reading mapper output or each other's pass. Each annotated 14 configured groups for each of ten records. All ten source hashes matched, and both passes agreed before candidate cards were generated. The reconciled reference was sealed and the first comparison retained.

Scoring preserves scalar types, null versus empty arrays, array order, complete outcome/timeframe pairs and arm/intervention relationships. A card passes only when all configured groups match. The 14 groups do not cover every field in a registry record, and both annotation passes may share systematic errors.

This is a technical source-agreement audit, not independent human clinical approval. The original human-approval-gated scorer remains unchanged and reports no human-approved comparisons. The new annotations do not resolve conflicting source-approval statements in the supplied reviewer documents; their scenario assessments remain separately attributed.

## Evidence and reproduction

| Record | Contents |
| --- | --- |
| [Evaluation report PDF](../deliverables/2026-11-23/02-T2D-Compass-Evaluation-Report.pdf) | Current release addendum and original evaluation report |
| [Reference annotations](../eval/type2diabetes/results/reference-audit-2026-11-23/reference-annotations.json) | Expected values for all configured groups |
| [Source checks and reconciliation](../eval/type2diabetes/results/reference-audit-2026-11-23/source-check-reconciliation.json) | Source locations, hashes and agreement record |
| [Reference results](../eval/type2diabetes/results/reference-audit-2026-11-23/reference-evaluation.json) | Development and first held-out comparisons |
| [Source-audit archive](../deliverables/2026-11-23/T2D-Compass-Reference-Audit-2026-11-23.zip) | Original sources, annotation passes, seals, runner, candidate cards and first-run receipt |
| [November 21 scenario traces](../deliverables/2026-11-23/t2d_eval_runs_traces_2026-11-21.zip) | 24 completed snapshot executions |
| [November 12 verification](../eval/type2diabetes/results/submission-2026-11-12/validation-summary.json) | Earlier software, tool replay, HTTP and packaging checks |

Use commit [`ae42c913c4870376c269a387713cf2718df4eac4`](https://github.com/imtiaz-cdc/T2D-compass/tree/ae42c913c4870376c269a387713cf2718df4eac4) for the frozen candidate and protocol. The source-audit archive contains reproduction commands. Write rerun results to a new directory and verify the recorded candidate and source hashes. Preserve the first held-out result; a later run against a changed candidate is a separate evaluation.

Raw current live exports remain in the local delivery package. The repository contains their release summary; operational troubleshooting is maintained separately.

## Interpretation limits

The reference set is a small convenience sample. It includes missing outcome arrays in older records, missing design and type fields, conflicting age language, and masking descriptions that differ across subtrials. These details remain explicit. Several records include pediatric, prediabetes, family, healthy-volunteer or comorbid populations.

Eligibility describes entry criteria rather than the enrolled population. Enrollment is not an outcome-analysis denominator. Completed status does not establish posted results or treatment benefit. Registry-listed outcomes do not establish prospective specification, and similar endpoints do not establish comparability. T2D Compass does not extract numerical efficacy results or rank treatments.

The conservative condition-label screen may omit relevant records with broader labels. Frozen snapshots support reproducibility; live registry records can change. The hosted interface displayed `models.ai.gpt-5-6-luna`, while the November 21 suite recorded `databricks-gpt-5-5`; those results are not interchangeable.

Both tools are read-only and use a fixed ClinicalTrials.gov origin. Evaluation uses public registry data and controlled fixtures. Source text is treated as evidence, not instructions. The app requires authorized Databricks access. These checks do not constitute a security certification, representative clinical validation or production-load assessment.
