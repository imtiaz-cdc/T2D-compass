# T2D Compass evaluation report

Updated November 23, 2026. Current application candidate 0.4.1; original frozen source-audit candidate 0.4.0; ClinicalTrials.gov is the only study-data source. The completed [delivery report](../deliverables/2026-11-23/02-T2D-Compass-Evaluation-Report.pdf) and preserved evidence distinguish software checks, model execution, reported human scenario assessments, assistant source comparison and live browser observations.

## Evidence and results

| Evidence | Date | Result and scope |
| --- | --- | --- |
| Software suite | November 12 and 17 | 294 tests passed on each dated run; lint passed. Synthetic/mocked cases do not establish model or clinical quality. |
| Two-tool replay and packaging | November 12; dependency repair November 17 | Live/snapshot MCP and local HTTP/package checks passed in the preserved reports. These are dated checks. |
| Model execution | November 21 | 12 scenarios twice; 24 completed executions, 52 model turns and 38 tool calls. Recorded model `databricks-gpt-5-5`, snapshot mode, prompt `t2d-compass-1.0`. |
| Reported scenario assessments | November 21 | Chinelo and Mohammad report 12/12 passes and 7/7 critical passes in both runs. Raw pre-review JSON remains unchanged. |
| Assistant source-reference comparison | November 23 | 140/140 groups and 10/10 complete cards match: development 84/84 groups, 6/6 cards; held-out 56/56 groups, 4/4 cards. |
| Authorized live browser | November 23 | Nine direct browser checks passed. The current version 0.4.1 corrects the outcome/timeframe presentation issue. Two fresh hosted assistant checks completed on this version with live retrieval and passed the selected source-fidelity checks. Earlier failures and the original wording discrepancy remain dated evidence. |

The November 21 complete-task median was 17.508 seconds, range 2.787–36.370 seconds; the recorded suite duration was 453.312 seconds. Both controlled upstream-failure scenarios contain the actual snapshot-only injected error. Expected domain outcomes (`not_found`, `no_matches`, injected `upstream_error`) are distinguished from execution failure. No no-tool baseline was run, so no incremental tool-benefit percentage is claimed.

## Source-reference method

The candidate source, prompt, field contract and exact JSON scoring rule were frozen before held-out annotation. Two separate assistants read the original frozen sources and field dictionary without reading mapper output or the other pass. Both completed all 14 configured field groups for each of the ten records. All ten snapshot hashes matched. The two passes agreed on every expected group before candidate cards were generated; the reconciled reference was sealed and its first comparison preserved.

Exact comparison preserves scalar types, null versus empty arrays, array order, full outcome/timeframe pairs and arm/intervention relationships. A complete-card pass requires every configured group to match. These are 14 groups per card, not every leaf field in ClinicalTrials.gov. Both assistant passes can share systematic errors. Agreement with a source does not establish that the source is complete, internally consistent or clinically valid.

The original approval-gated scorer was also run unchanged. It reports no human-approved comparisons because the new annotations do not invent two named human reviewers. Its null approval-gated accuracy is a separate result from the completed assistant technical comparison. The new work does not backdate or substantiate the conflicting source-approval wording in the November 21 reviewer documents. Their scenario assessment remains separately attributed.

## Reproducible evidence

- [Populated reference annotations](../eval/type2diabetes/results/reference-audit-2026-11-23/reference-annotations.json)
- [Source checks and reconciliation](../eval/type2diabetes/results/reference-audit-2026-11-23/source-check-reconciliation.json)
- [Reference-evaluation results](../eval/type2diabetes/results/reference-audit-2026-11-23/reference-evaluation.json)
- [Complete source-audit archive](../deliverables/2026-11-23/T2D-Compass-Reference-Audit-2026-11-23.zip), including original source copies, independent passes, seals, runner, actual cards, first-execution receipt and human-gate result
- [November 21 scenario archive](../deliverables/2026-11-23/t2d_eval_runs_traces_2026-11-21.zip)
- Raw live browser exports are retained in the local delivery package; the report above summarizes their bounded findings. Operational diagnostics and administrator correspondence are kept separate from the submission.
- [November 12 software evidence](../eval/type2diabetes/results/submission-2026-11-12/validation-summary.json)

The source-audit archive supplies portable verification and reproduction commands. Reproduction must use a new output directory and matching source/candidate hashes; do not overwrite the first held-out result or relabel a subsequent changed-candidate run as the first evaluation. No source, mapper, prompt or scoring rule was changed to improve these results.

## Source interpretation findings

Missing source data remain explicit, including missing outcome arrays in two older held-out records and missing arm/design or type fields. Some records include pediatric, prediabetes, family, healthy-volunteer or comorbid populations. One record contains conflicting age language, and another describes masking that differs across subtrials. These source details were preserved and documented, rather than silently corrected or converted into broad clinical claims.

Eligibility is not the enrolled population; enrollment is not an outcome-analysis denominator. Completion is separate from results availability and treatment benefit. Registry-listed outcomes do not establish prospective specification. Similar endpoints and randomization labels do not establish comparability or low risk of bias. The app does not extract numerical efficacy results or rank treatments.

## Security and operating boundaries

Both tools are read-only. Search arguments and NCT identifiers are bounded; the ClinicalTrials.gov origin is fixed. The app remains behind Databricks authentication. Public registry data and controlled fixtures are used; no patient data or credentials are evaluation inputs. Source content is untrusted evidence, not an instruction source. Exported files were inspected for credential fields before packaging; this is limited hygiene review, not a penetration test or security certification.

The hosted UI displayed `models.ai.gpt-5-6-luna`, whereas the November 21 scenario suite records `databricks-gpt-5-5`. These routes and results are not interchangeable. Authentication error wording alone does not establish a root cause. The timing correction was deployed through the existing authorized app workflow. App permissions and model configuration were not changed.

## Lessons and limits

Field provenance and exact comparison make missingness and relationships inspectable. The conservative condition-label screen reduces known out-of-scope candidates while making possible omissions explicit. Frozen data support reproducibility; separate live checks test current behavior. A small convenience dataset and finite scenario suite support bounded prototype claims, not representative clinical accuracy, treatment effectiveness, production capacity or general safety guarantees.

## Timing correction and current hosted verification

Version **0.4.1**, prompt **t2d-compass-1.1**, was separately tested and deployed on November 23. The original answer changed a zero-minute pre-meal sample into an after-meal sample; the underlying registry card was correct. The revised prompt requires exact study/outcome-index/measure/timeframe blocks. A bounded check uses source-backed cards when those blocks are absent or changed, while preserving the model draft and the check result in the trace. This is a presentation safeguard, not semantic validation of every sentence.

The updated candidate passed **310 software tests** and lint. Two fresh hosted questions (NCT03244800 and NCT05790681) completed in **11.548 and 11.571 seconds**, respectively, each with one live evidence-card tool call. The reviewed final answers preserved all five primary-outcome/timeframe pairs, the pre-meal boundary, results-availability distinctions and relevant population context. These two selected checks do not establish a complete live-suite pass or independent clinical approval.

The original **0.4.0** source-audit candidate, annotations and first held-out result remain unchanged: **140/140 groups, 10/10 cards**. That original result is not relabeled as an evaluation of the changed prompt. The evaluation PDF, video and slides now describe the correction and current verified state consistently. See the [release validation summary](../eval/type2diabetes/results/timing-fix-2026-11-23/validation-summary.json).
