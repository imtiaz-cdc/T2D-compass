# Maintenance scripts

`build_bundles.py` builds auditable source and live-runtime packages from the repository. Run with `uv run python scripts/build_bundles.py`. Generated archives remain local under ignored `bundles/`.

`collect_type2diabetes_data.py` records the original collection method. The committed dataset is already captured, so the collector intentionally refuses to overwrite it. It is not needed to run or evaluate the app. A future capture requires a separately chosen output location and revised evaluation governance; live ordering and records may have changed.

`templates/agent-scenarios-original.json` preserves the historical scenario template used to create the T2D suite. It is an input to the collector, not the active evaluation suite. `templates/prior-exposure-ids.json` contains only the prior study identifiers excluded during original held-out selection. It makes the exclusion list portable without copying earlier disease datasets. The active suite remains `eval/type2diabetes/agent_scenarios.json`.
