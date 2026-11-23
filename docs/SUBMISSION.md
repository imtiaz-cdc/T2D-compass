# T2D Compass delivery record

Prepared November 23, 2026 for the Data track. Scope: version 0.4.0, one MCP server, two read-only tools, browser search/card inspection/JSON export and the optional assistant. ClinicalTrials.gov is the only study-data source.

## Delivery files

The [dated package](../deliverables/2026-11-23/README.md) provides the demonstration MP4, evaluation PDF, slide deck, public-repository-link PDF and supporting evidence. These files describe actual completed work and bounded findings. The narrated demo uses dated recorded evidence with automated narration; it is not a new uninterrupted live screen recording.

The user-supplied organizer form, inspected November 16, accepts a video under 50 MB (MP4/ZIP), an evaluation PDF, a PPTX/PDF deck and a PDF containing the public repository link. Contact details and the actual event-form response are separate from preparing or publishing these files. Repository publication is not event submission.

## Evidence scope

The supplied November 21 archive contains all 24 snapshot-mode model executions and the Word documents report both reviewers' scenario assessments. The November 23 assistant source audit contains all 140 references and exact comparison results. Human clinical approval of those newly prepared annotations is not claimed. Historical raw review-status labels are preserved rather than rewritten to create approval.

Nine direct browser checks passed. After an administrator-reported fix, two hosted assistant questions also completed with live retrieval. One answer had a minor timeframe-wording discrepancy; see the later-verification findings below. Earlier authentication failures are retained as historical evidence.

The [ordinary app URL](https://t2d-compass-7474654188777746.aws.databricksapps.com/) requires authorized Databricks access. Management access is not required to read the submitted files. Individual judges' app permissions are not inferred from the signed-in testing account.

## One-sentence use case

T2D Compass helps researchers inspect completed type 2 diabetes intervention studies using source-linked ClinicalTrials.gov evidence cards with explicit missing information, results-availability labels and interpretation limits.

After the administrator reported a fix, two later hosted assistant checks completed with live retrieval: the previously failed exact-ID question and a completed-without-posted-results question. Each used one evidence-card tool call. Assistant review found one minor pre-meal/post-meal wording discrepancy in the first answer; the underlying card was correct. The second answer met the selected critical scenario criteria. These bounded checks establish restored execution in the tested session, not a full live-suite pass or independent human clinical approval. The earlier failures remain historical evidence.
