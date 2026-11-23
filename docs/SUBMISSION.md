# T2D Compass delivery record

Prepared November 23, 2026 for the Data track. Scope: version 0.4.0, one MCP server, two read-only tools, browser search/card inspection/JSON export and the optional assistant. ClinicalTrials.gov is the only study-data source.

## Delivery files

The [dated package](../deliverables/2026-11-23/README.md) provides the demonstration MP4, evaluation PDF, slide deck, public-repository-link PDF and supporting evidence. These files describe actual completed work and bounded findings. The narrated demo uses dated recorded evidence with automated narration; it is not a new uninterrupted live screen recording.

The user-supplied organizer form, inspected November 16, accepts a video under 50 MB (MP4/ZIP), an evaluation PDF, a PPTX/PDF deck and a PDF containing the public repository link. Contact details and the actual event-form response are separate from preparing or publishing these files. Repository publication is not event submission.

## Evidence scope

The supplied November 21 archive contains all 24 snapshot-mode model executions and the Word documents report both reviewers' scenario assessments. The November 23 assistant source audit contains all 140 references and exact comparison results. Human clinical approval of those newly prepared annotations is not claimed. Historical raw review-status labels are preserved rather than rewritten to create approval.

Nine direct browser checks passed. Two hosted assistant attempts failed with `model_authentication_failed` and zero tool calls, including one retry after reopening the app. This is an observed authentication limitation, not a passing live model suite.

The [ordinary app URL](https://t2d-compass-7474654188777746.aws.databricksapps.com/) requires authorized Databricks access. Management access is not required to read the submitted files. Individual judges' app permissions are not inferred from the signed-in testing account.

## One-sentence use case

T2D Compass helps researchers inspect completed type 2 diabetes intervention studies using source-linked ClinicalTrials.gov evidence cards with explicit missing information, results-availability labels and interpretation limits.

The user subsequently reported that the hosted assistant also failed in a private browser session. No successful live assistant result is claimed. Detailed operational diagnostics are retained locally.
