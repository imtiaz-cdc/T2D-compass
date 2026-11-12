# Source and template provenance

The application was originally adapted from [GSA-TTS/mcp-hackathon-template at `6e5fb39`](https://github.com/GSA-TTS/mcp-hackathon-template/tree/6e5fb39b4de044de4f39950ded44fa128416f11a). The original [provenance record](../upstream/PROVENANCE.json) is preserved. Its statement about saved upstream sources refers to the original project workspace, not a promise that all upstream files are duplicated here.

On November 12, 2026, this submission was aligned with [current template commit `f39249f`](https://github.com/GSA-TTS/mcp-hackathon-template/tree/f39249f1768309e3ef8b31742390a4f3a656b5f3): a thin entry point, source package, one file per tool, tests, evaluation documentation, environment example and platform deployment configuration. The CI workflow follows the starter's checkout/uv/test pattern and uses the project's locked dependencies and applicable checks. This alignment does not claim that all later upstream implementation changes were merged.

The original MIT license and Technology Transformation Services copyright are unchanged. T2D-specific code and documentation build on that foundation. Third-party Python dependencies keep their own licenses. Public registry records are source data rather than authored project code; study contributors supply their content.

The public source package intentionally excludes unrelated conversation exports, training transcripts, credentials, local environments, historical disease packages and personal team handbooks. Original materials remain preserved in the team's workspace. Historical connector code is explicitly labeled and retained only for regression tests.

ClinicalTrials.gov is the sole study-data source. The [dataset guide](../data/type2diabetes/README.md), manifests and source hashes document capture and selection. Current model, clinical-review and demonstration gaps are listed in [SUBMISSION.md](SUBMISSION.md).
