# Source provenance

## Application foundation

T2D Compass adapts the [GSA MCP server template](https://github.com/GSA-TTS/mcp-hackathon-template/tree/6e5fb39b4de044de4f39950ded44fa128416f11a), originally captured at commit `6e5fb39b4de044de4f39950ded44fa128416f11a`. The [upstream provenance record](../upstream/PROVENANCE.json) preserves that reference. Original upstream source copies remain in the project workspace.

On November 12, 2026, the repository was aligned with template commit [`f39249f1768309e3ef8b31742390a4f3a656b5f3`](https://github.com/GSA-TTS/mcp-hackathon-template/tree/f39249f1768309e3ef8b31742390a4f3a656b5f3): a thin entry point, source package, one file per tool, tests, evaluation documentation, environment example and deployment configuration. CI follows the template's checkout, dependency installation and test pattern using this project's locked dependencies. This records structural alignment, not a merge of every upstream change.

## License

The [MIT license](../LICENSE) retains the original Technology Transformation Services copyright notice. Third-party Python dependencies retain their own licenses. ClinicalTrials.gov records are study-source data supplied by registry contributors, rather than project-authored software.

## Data and evaluation records

ClinicalTrials.gov is the sole study-data source. The [dataset guide](../data/type2diabetes/README.md), manifests and source hashes record capture, selection and split assignment. Original snapshots, team review documents and evaluation traces retain their dates and authorship.

The [evaluation report](EVALUATION.md) distinguishes software tests, model runs, reported team assessments and the AI-assisted source-reference audit. The original frozen candidate and first held-out results are preserved separately from later application changes.

Repository content excludes credentials, local environments, private working material and operational troubleshooting. Historical connector code is labeled in [deployment documentation](../deploy/README.md) and retained for regression checks.
