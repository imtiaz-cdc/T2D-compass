# Submission materials

**Project:** T2D Compass · **Track:** Data · **Application:** 0.4.1

T2D Compass helps researchers inspect completed type 2 diabetes intervention studies through source-linked ClinicalTrials.gov evidence cards. The application provides two read-only MCP tools, browser search, card inspection, JSON export and an optional research assistant.

## Deliverables

| Material | File |
| --- | --- |
| Evaluation report | [PDF](../deliverables/2026-11-23/02-T2D-Compass-Evaluation-Report.pdf) |
| Presentation | Delivered separately |
| Source-code reference | [Repository-link PDF](../deliverables/2026-11-23/04-T2D-Compass-Code-Submission.pdf) |
| Source-reference evidence | [Annotations and results](../eval/type2diabetes/results/reference-audit-2026-11-23/README.md) · [Complete audit archive](../deliverables/2026-11-23/T2D-Compass-Reference-Audit-2026-11-23.zip) |
| Model evaluation traces | [November 21 archive](../deliverables/2026-11-23/t2d_eval_runs_traces_2026-11-21.zip) |
| Demonstration | Supplied separately; [app walkthrough](DEMO.md) |

The [delivery directory](../deliverables/2026-11-23/README.md) provides the file index. The presentation and demo video are delivered separately from this repository.

## Application access

[Open T2D Compass](https://t2d-compass-7474654188777746.aws.databricksapps.com/). The hosted app requires authorized Databricks access. Repository files can be reviewed without app-management permissions. Access for an individual evaluator must be arranged separately; a successful team sign-in does not establish that evaluator's access.

For local use, follow [QUICKSTART.md](../QUICKSTART.md). Search and evidence cards can run against the supplied public snapshots without model credentials.

## Evaluation summary

Version 0.4.1 passed 310 software tests and lint. Two hosted assistant checks retained all five reviewed primary-outcome/timeframe pairs. The original 0.4.0 audit matched 140/140 configured source groups across ten cards. The November 21 archive contains 24 snapshot-mode model executions; supplied team reviews report 12/12 scenario passes and 7/7 critical passes in each repeat.

The [evaluation report](EVALUATION.md) explains the candidate versions, methods, reviewer attribution and limits. Source agreement and team scenario assessments are separate from independent clinical approval.

The files are prepared for submission. Contact information and the organizer's submission form are handled separately; publishing this repository does not submit the form.
