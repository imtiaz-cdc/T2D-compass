# Evidence-card field dictionary

Schema version: `1.0`. Implementation: `src/alz_compass/mapping.py`, `build_evidence_card`.

The card label is **Registry extraction pending human review**. Values come from a ClinicalTrials.gov API v2 study object. This document specifies the implemented extraction contract, not a clinical interpretation of registry data.

## Top-level contract

The retrieval tool wraps the card in `{status: "ok", source_mode, card}`. Errors instead carry a status code and `error: {code, message, retryable}`. The card contract below starts inside `card`.

| Key | Meaning |
| --- | --- |
| `schema_version` | Version of the card contract |
| `label` | Human-review status of the extraction |
| `source_mode` | `live` or `snapshot` |
| `identity`, `status`, `design`, `enrollment`, `population` | Directly mapped study information |
| `arms`, `interventions`, `primary_outcomes` | Source arrays preserved in original order |
| `results` | Registry results availability and source URL |
| `provenance` | Retrieval metadata and field-level source paths/values |
| `review_flags` | Explicit missing, invalid, estimated, or out-of-scope information |
| `limitations` | Interpretation limits carried with every card |

## Search response

Search returns `status`, `source_mode`, `criteria`, `coverage`, `search_semantics`, `retrieved_at`, `studies`, `returned_count`, `pages_fetched`, `records_examined`, `search_incomplete`, and `review_flags`, with an `error` where applicable. Each study summary includes identifier, title, conditions, status, study type, results availability, and study URL.

`coverage` is `bounded_candidates`. `criteria` records the actual condition/status/type filters, intervention, limit, and API parameters. Search rechecks completed/interventional eligibility and removes duplicate identifiers. A requested result limit or retrieval budget can leave additional candidates unexamined, which must remain visible.

Live search uses the registry's condition query semantics and may return broader related terms. Both live and snapshot candidates must pass the explicit supported type 2 diabetes condition-label screen, which can omit relevant studies with broader labels. Snapshot search uses only the development records and literal case-insensitive intervention text matching. The two modes need not return identical candidate sets. Their `search_semantics` values distinguish `registry_condition_query` from `bounded_snapshot`.

## Mapping

In the table below, `P` means `$.protocolSection`. Array indices such as `[i]` refer to the same position in the source and card.

| Card field | Source path |
| --- | --- |
| `identity.nct_id` | `P.identificationModule.nctId` |
| `identity.title` | `P.identificationModule.briefTitle` |
| `identity.official_title` | `P.identificationModule.officialTitle` |
| `identity.conditions` | `P.conditionsModule.conditions` |
| `identity.study_url` | Derived from a canonical `NCT` plus eight-digit identifier |
| `status.study_type` | `P.designModule.studyType` |
| `status.overall_status` | `P.statusModule.overallStatus` |
| `status.completion_date` | `P.statusModule.completionDateStruct.date` |
| `status.completion_date_type` | `P.statusModule.completionDateStruct.type` |
| `design.phases` | `P.designModule.phases` |
| `design.allocation` | `P.designModule.designInfo.allocation` |
| `design.intervention_model` | `P.designModule.designInfo.interventionModel` |
| `design.masking` | `P.designModule.designInfo.maskingInfo.masking` |
| `design.who_masked` | `P.designModule.designInfo.maskingInfo.whoMasked` |
| `enrollment.count` | `P.designModule.enrollmentInfo.count` |
| `enrollment.type` | `P.designModule.enrollmentInfo.type` |
| `population.eligibility_criteria` | `P.eligibilityModule.eligibilityCriteria` |
| `population.healthy_volunteers` | `P.eligibilityModule.healthyVolunteers` |
| `population.sex` | `P.eligibilityModule.sex` |
| `population.minimum_age` | `P.eligibilityModule.minimumAge` |
| `population.maximum_age` | `P.eligibilityModule.maximumAge` |
| `population.interpretation` | Fixed statement identifying these as eligibility criteria |
| `arms[i].label` | `P.armsInterventionsModule.armGroups[i].label` |
| `arms[i].type` | `P.armsInterventionsModule.armGroups[i].type` |
| `arms[i].description` | `P.armsInterventionsModule.armGroups[i].description` |
| `arms[i].intervention_names` | `P.armsInterventionsModule.armGroups[i].interventionNames` |
| `interventions[i].name` | `P.armsInterventionsModule.interventions[i].name` |
| `interventions[i].type` | `P.armsInterventionsModule.interventions[i].type` |
| `interventions[i].description` | `P.armsInterventionsModule.interventions[i].description` |
| `interventions[i].arm_group_labels` | `P.armsInterventionsModule.interventions[i].armGroupLabels` |
| `interventions[i].other_names` | `P.armsInterventionsModule.interventions[i].otherNames` |
| `primary_outcomes[i].measure` | `P.outcomesModule.primaryOutcomes[i].measure` |
| `primary_outcomes[i].description` | `P.outcomesModule.primaryOutcomes[i].description` |
| `primary_outcomes[i].time_frame` | `P.outcomesModule.primaryOutcomes[i].timeFrame` |
| `results.has_results` | `$.hasResults` |
| `results.status` | Strict `true` gives `posted`, `false` gives `not_posted`, unavailable/invalid gives `unknown` |
| `results.url` | Canonical study URL, with `?tab=results` only when results are posted |
| `provenance.registry_update_date` | `P.statusModule.lastUpdatePostDateStruct.date` |

## Provenance

`provenance.retrieved_at` records the retrieval time supplied by the adapter. For a snapshot this is the source capture time, not a claim of a fresh network request. `source_url` and `api_url` identify the study and API record. `snapshot_sha256` identifies the saved response when provided.

`provenance.fields` is keyed by output JSONPath. Each entry includes `source_path` and the original `source_value`. Derived fields also include a `derivation` explanation. For example, `$.primary_outcomes[0].time_frame` points to the first source outcome's `timeFrame`.

Constant labels and interpretation rules are application text. They should not be presented as quotations from the registry. The stored source value supports review when validation rejects a source value.

## Missing and invalid values

- A missing, empty-string, or invalid scalar maps to `null`. A required missing field receives a review flag.
- A missing array maps to `null`. An explicitly empty array remains `[]`. Empty required record arrays receive a flag.
- `0` remains a numeric zero and `false` remains a boolean false. Neither becomes missing.
- Invalid array elements keep their original index with null mapped fields. The mapper never shifts an outcome's timeframe onto a neighboring outcome.
- Optional values include official title, who was masked, optional population detail, and optional association/name arrays. Their absence is preserved without implying that another value applies.
- Display null values as **Not reported in this record.** Do not replace an explicit `NA` enum with missing.
- Preserve partial dates as supplied. Do not invent a month or day.

## Associations and clinical limits

Arms and interventions carry explicit labels and names from the source. The mapper flags missing associations and unresolved arm labels. It does not match by list order or infer a comparator from similar names.

The mapper adds scope flags when completion/interventional status is absent or outside scope. A condition-label check can flag unconfirmed type 2 diabetes relevance, and every card requests manual disease/population relevance review. This is not an automatic diagnosis or eligibility adjudication.

Results availability is separate from numerical results. A completed study can have no posted registry results. Eligibility criteria do not describe the enrolled sample. Enrollment does not supply the denominator for an outcome analysis. Registered outcomes alone do not prove prospective specification. Design fields alone do not establish low risk of bias.

## Review flag structure

Each flag has `code`, output `field`, and plain-language `message`. Current codes include `MISSING_FIELD`, `INVALID_SOURCE_TYPE`, `EMPTY_REQUESTED_ARRAY`, `INVALID_NCT_ID`, `OUTSIDE_COMPLETED_SCOPE`, `OUTSIDE_INTERVENTIONAL_SCOPE`, `TYPE2_DIABETES_SCOPE_UNCONFIRMED`, `DISEASE_RELEVANCE_REQUIRES_REVIEW`, `ESTIMATED_ENROLLMENT`, `ESTIMATED_COMPLETION_DATE`, `RESULTS_NOT_POSTED`, `RESULTS_AVAILABILITY_UNKNOWN`, `UNRESOLVED_ARM_REFERENCE`, and `ARM_INTERVENTION_LINK_NOT_REPORTED`.

## Sources

The mapping above documents the project implementation and the preserved API responses. Current API reference: [ClinicalTrials.gov data API](https://clinicaltrials.gov/data-api/api). Human interpretation and independent reference approval remain assigned to Mohammad and Chinelo.
