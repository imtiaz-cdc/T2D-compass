# App walkthrough

This walkthrough covers search, evidence-card review and an assistant answer with an inspectable tool trace. The demonstration video is distributed separately.

Use an authorized [Databricks app session](https://t2d-compass-7474654188777746.aws.databricksapps.com/) or the [local snapshot setup](../QUICKSTART.md). Confirm the source mode before starting: live registry records can differ from the preserved snapshots.

## 1. Find completed studies

Search for `MEDI0382` with a limit of three candidates. Inspect the returned study identifiers and the search-coverage note. The tool checks completed/interventional status and supported type 2 diabetes condition labels within a bounded candidate set; it is not an exhaustive literature search.

## 2. Open an evidence card

Open `NCT03244800`. Review the study design, enrollment and its actual/estimated label, eligibility, arms, interventions and primary outcomes. Follow the ClinicalTrials.gov source link and export the card as JSON.

## 3. Check outcomes in context

Read each primary outcome together with its full timeframe, including before-meal and after-meal boundaries. Inspect source paths and review flags. Missing fields remain missing. Eligibility and enrollment labels should not be presented as measured treatment outcomes.

## 4. Ask the assistant and inspect the trace

Use this question:

> Prepare a source-linked evidence card for NCT03244800. Include design, enrollment, interventions, each primary outcome and its timeframe, and results availability.

Inspect the actual card-tool call, retrieved evidence, model draft and final answer. Export the trace. Version 0.4.1 checks the required outcome/timeframe blocks and can display source-backed cards when a block is changed or omitted. The trace retains the draft and check result.

## 5. Distinguish completion from results

Open `NCT05790681` and inspect status, posted-results availability and population context. The preserved snapshot is a completed study without posted results and includes pediatric eligibility. A completed study alone does not establish results or effectiveness.

The [evaluation report](EVALUATION.md) separates this workflow from the frozen model scenarios, reference audit and selected hosted checks. A successful demonstration is not a substitute for those evaluations.
