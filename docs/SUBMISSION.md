# T2D Compass delivery record

Prepared November 23, 2026 for the Data track. Scope: current version 0.4.1, one MCP server, two read-only tools, browser search/card inspection/JSON export and the optional assistant. ClinicalTrials.gov is the only study-data source.

## Delivery files

The [dated package](../deliverables/2026-11-23/README.md) provides the demonstration MP4, evaluation PDF, slide deck, public-repository-link PDF and supporting evidence. These files describe actual completed work and bounded findings. The narrated demo uses dated recorded evidence with automated narration; it is not a new uninterrupted live screen recording.

The user-supplied organizer form, inspected November 16, accepts a video under 50 MB (MP4/ZIP), an evaluation PDF, a PPTX/PDF deck and a PDF containing the public repository link. Contact details and the actual event-form response are separate from preparing or publishing these files. Repository publication is not event submission.

## Evidence scope

The supplied November 21 archive contains all 24 snapshot-mode model executions and the Word documents report both reviewers' scenario assessments. The November 23 assistant source audit contains all 140 references and exact comparison results. Human clinical approval of those newly prepared annotations is not claimed. Historical raw review-status labels are preserved rather than rewritten to create approval.

Nine direct browser checks passed. The current version 0.4.1 corrects the outcome/timeframe presentation issue. Two fresh hosted assistant checks completed on this version with live retrieval and passed the selected source-fidelity checks. Earlier failures and the original wording discrepancy remain dated evidence.

The [ordinary app URL](https://t2d-compass-7474654188777746.aws.databricksapps.com/) requires authorized Databricks access. Management access is not required to read the submitted files. Individual judges' app permissions are not inferred from the signed-in testing account.

## One-sentence use case

T2D Compass helps researchers inspect completed type 2 diabetes intervention studies using source-linked ClinicalTrials.gov evidence cards with explicit missing information, results-availability labels and interpretation limits.

## Timing correction and current hosted verification

Version **0.4.1**, prompt **t2d-compass-1.1**, was separately tested and deployed on November 23. The original answer changed a zero-minute pre-meal sample into an after-meal sample; the underlying registry card was correct. The revised prompt requires exact study/outcome-index/measure/timeframe blocks. A bounded check uses source-backed cards when those blocks are absent or changed, while preserving the model draft and the check result in the trace. This is a presentation safeguard, not semantic validation of every sentence.

The updated candidate passed **310 software tests** and lint. Two fresh hosted questions (NCT03244800 and NCT05790681) completed in **11.548 and 11.571 seconds**, respectively, each with one live evidence-card tool call. The reviewed final answers preserved all five primary-outcome/timeframe pairs, the pre-meal boundary, results-availability distinctions and relevant population context. These two selected checks do not establish a complete live-suite pass or independent clinical approval.

The original **0.4.0** source-audit candidate, annotations and first held-out result remain unchanged: **140/140 groups, 10/10 cards**. That original result is not relabeled as an evaluation of the changed prompt. The evaluation PDF, video and slides now describe the correction and current verified state consistently. See the [release validation summary](../eval/type2diabetes/results/timing-fix-2026-11-23/validation-summary.json).
