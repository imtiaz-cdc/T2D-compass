# Databricks deployment and reviewer access

## Existing team deployment

- [T2D Compass application](https://t2d-compass-7474654188777746.aws.databricksapps.com)
- [App management page](https://dbc-aae0ba16-8727.cloud.databricks.com/apps-v2/app/t2d-compass/overview?o=7474654188777746), for authorized **CAN MANAGE** users

The team reported this deployment on November 6 and supplied these links again on November 12, 2026. Repository preparation does not verify the deployed source revision, change the app, or grant access. Reviewers should use the application link. Arrange their authorized access or provide the recorded demonstration; do not make the service public to bypass sign-in.

## Source deployment

Use the complete repository hierarchy. The minimum live runtime contains `main.py`, `app.yaml`, `requirements.txt` and the entire `src/alz_compass/` tree, including browser files and `agent_prompt.txt`. Snapshot mode also needs `data/type2diabetes/`. Databricks installs the runtime requirements and runs `python main.py` from `app.yaml`.

Flattening Python files during manual upload breaks imports. Preserve folders, or generate the three-file upload bundle:

```sh
uv run python scripts/build_bundles.py
```

Generated output under `bundles/` includes `t2d-compass-three-files/` (`main.py`, `app.yaml`, `requirements.txt`), an expanded runtime, a source archive and hash manifests. The three-file launcher contains the same source/assets and reconstructs their hierarchy at startup. Generated bundles are ignored by Git; the repository is the auditable source. The builder refuses unexpected or modified managed output instead of silently deleting it.

Deploy only through the team's authorized Databricks workflow. The platform-provided `DATABRICKS_APP_PORT` or `PORT` selects HTTP on the platform interface. Keep local HTTP runs on loopback.

## Optional assistant

The browser assistant uses the signed-in user's forwarded token, the operator-configured workspace host and `ALZ_COMPASS_MODEL`. The current configuration preserves the vendor environment's existing model name. Verify the model is actually available before demonstrating it; this repository does not grant model privileges.

The app's user authorization must include the appropriate `ai-gateway` scope and user consent. Databricks app access and permissions on downstream model resources are separate checks. Current platform references, checked November 12, 2026: [authorization](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/auth) and [app permissions](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/permissions). Workspace policies and available UI may differ.

## Deployment acceptance record

For the actual candidate revision, record:

1. Deployment/source revision, app version, source mode and date.
2. Authorized reviewer can open the app; `/health` shows the expected version and condition.
3. Search returns candidates; a card opens with source fields and JSON download.
4. An assistant question produces actual tool calls and an exportable trace, if assistant functionality is demonstrated.
5. A missing or out-of-scope record produces the expected message/flags.
6. Clinical/source review and model scoring are recorded separately from successful execution.

Do not include credentials, account screens, authorization headers or private prompts in shared evidence. A healthy endpoint alone is not proof that the model or MCP tools worked.

## External clients and historical connector

External `/mcp` clients require supported Databricks OAuth access and app-use permission. Follow the [current Databricks API connection documentation](https://docs.databricks.com/aws/en/dev-tools/databricks-apps/connect-local). The current browser workflow does not require a notebook.

`deploy/databricks/ALZ_Compass_Connect.py` and its historical prompt are retained to support the existing offline connector tests. They describe an earlier integration and are not the T2D browser setup or proof of current external-client authentication. See [the deployment directory note](../deploy/README.md).
