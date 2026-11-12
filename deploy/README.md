# Deployment files

Use the root `app.yaml` with the complete source tree, or generate the three-file bundle with `uv run python scripts/build_bundles.py`. Follow [the current Databricks guide](../docs/EASY_DEPLOY.md).

`three_file_main.py.in` is the source-packaging launcher template. The bundle builder embeds the current app files, not a separate implementation.

`databricks/ALZ_Compass_Connect.py` and `databricks/history/alz-compass-1.0.txt` are **historical external-client examples**, retained because `tests/test_databricks_notebook.py` tests their connector helpers. Their disease examples and model route must not be presented as current T2D results. Do not run them unchanged as the current deployment guide.
