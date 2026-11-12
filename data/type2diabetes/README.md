# Type 2 diabetes starter source set

Captured October 28, 2026 from the public ClinicalTrials.gov API for T2D Compass. This new baseline is separate from the preserved Alzheimer and obesity source sets and their historical reports. ClinicalTrials.gov remains the only project source.

`manifest.json` contains **10 core records: six development and four held-out**. `manifest-agent.json` contains the six development records plus one active interventional exclusion; the exclusion is outside the accuracy benchmark. The snapshot reader loads development records only unless held-out inclusion is explicitly requested for approved evaluation.

## Selection and preservation

The development selection rule was declared before capture: completed interventional records, `TREATMENT` primary purpose, an explicit type 2 diabetes condition label accepted by the app's shared scope matcher, and nonempty title, brief summary, eligibility text, primary outcome measure and intervention name. Within each of six strata—registry-listed `DRUG`, `BEHAVIORAL` or `PROCEDURE`, paired with posted or unposted results—the collector selected the first eligible unused record among the first 20 relevance-ordered search results.

This is a convenience starter set with readable source material, not a representative clinical benchmark. Presence of a procedure intervention does not mean that procedure is a therapy; the selected records include a hypoglycemic clamp and blood-pressure measurement. The treatment-purpose filter applies to the study as reported, not to every individual intervention. Adult and pediatric populations, comorbidities, designs and outcomes differ; their inclusion does not establish clinically equivalent comparisons.

Held-out selection used a separate completed/interventional type 2 diabetes query with **NCTId-only projection**, sorted by first posting date ascending. It chose the first four unseen IDs, excluding every candidate whose metadata appeared in the development queries, known earlier source sets/candidate lists and preliminary inspected candidates. Held-out full records were downloaded and checked mechanically for identity, status, study type and hashes, without using their content for development example selection, implementation, expected answers or prompt tuning.

The exclusion was the first unused active/not-recruiting interventional candidate with an explicit type 2 diabetes label. It must not enter completed-study search results.

[selection.json](selection.json) preserves the exact queries, candidate responses, timestamps and API version. Each public record file preserves the downloaded JSON response bytes; its manifest entry includes source/API URLs, retrieval time and SHA-256. The [collector](../../scripts/collect_type2diabetes_data.py) uses the same label matcher as the app and refuses to overwrite an existing capture or run with another active disease profile. Future refreshes need a separate capture location. The frozen files reproduce this baseline; live relevance order and source content may change.

## Development examples

| Purpose | NCT identifier | Captured source context |
| --- | --- | --- |
| Drug; posted results; first browser example | [NCT03244800](https://clinicaltrials.gov/study/NCT03244800) | MEDI0382 and placebo; type 2 diabetes condition label |
| Drug; no posted results | [NCT05790681](https://clinicaltrials.gov/study/NCT05790681) | Insulin icodec; title specifies children and teenagers—retain age context |
| Behavioral; posted results; second comparison example | [NCT04214600](https://clinicaltrials.gov/study/NCT04214600) | Cognitive behavioral therapy for adherence; type 2 diabetes and depression labels |
| Behavioral; no posted results | [NCT01596244](https://clinicaltrials.gov/study/NCT01596244) | Jordan Diabetes Microclinic Project; `Diabetes Mellitus, Type II` label |
| Procedure; posted results | [NCT01614769](https://clinicaltrials.gov/study/NCT01614769) | Glimepiride/placebo and hypoglycemic clamp; a procedure is not automatically a treatment |
| Procedure; no posted results | [NCT02811055](https://clinicaltrials.gov/study/NCT02811055) | Aprepitant/placebo and measurement procedures; type 2 diabetes and hypertension labels |
| Active exclusion, outside core benchmark | [NCT05743387](https://clinicaltrials.gov/study/NCT05743387) | Active/not recruiting, interventional; direct card must retain status and outside-completed-scope flag |

All six core development records are completed and interventional at capture. These are source extraction checks, not approved clinical interpretations. Eligibility criteria do not establish actual enrolled characteristics, and completion or posted results does not establish treatment benefit.

One development-query candidate was [NCT05024032](https://clinicaltrials.gov/study/NCT05024032), an obesity/overweight study whose title says participants were without type 2 diabetes. Its labels did not establish type 2 diabetes, so it was excluded. This illustrates why a disease query alone is insufficient: source relevance needs an explicit screen and human review.

## Review and evaluation status

[review/reference-annotations.json](review/reference-annotations.json) is blank and pending independent review. All 14 expected field groups per record remain unannotated. Mohammad and Chinelo should prepare source-first references and approve them independently; generated cards must not be substituted for reference answers. Keep held-out answers out of development and prompt tuning.

The [capture checks](../../eval/type2diabetes/results/fixture-validation.json) verify record counts, strata, hashes and scenario placeholders. The [actual snapshot binding checks](../../eval/type2diabetes/results/binding-validation.json) verify the current reader and service, including posted/unposted records, intervention search, active exclusion, absent ID and no-match behavior. The [reference readiness check](../../eval/type2diabetes/results/pending-reference-check.json) correctly reports six pending development references and zero compared cards. These are mechanical checks, not clinical validation or real-model evaluation.

The expanded 24-record benchmark has not been collected for type 2 diabetes. Preserve this baseline and agree on broader clinical relevance/diversity criteria before expansion and evaluation.
