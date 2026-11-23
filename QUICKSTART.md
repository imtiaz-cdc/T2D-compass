# T2D Compass quick start

Run commands from the repository root. Use Python 3.11+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

## Install the tested dependency set

```sh
git clone https://github.com/imtiaz-cdc/T2D-compass.git
cd T2D-compass
uv sync --locked --group dev
```

The lock file fixes dependency versions. `requirements.txt` is the hash-pinned runtime export used by Databricks. Do not upgrade packages as part of reproducing the recorded checks.

## Browser interface without credentials

PowerShell:

```powershell
$env:ALZ_COMPASS_DATA_MODE = "snapshot"
$env:MCP_TRANSPORT = "streamable-http"
uv run python main.py
```

macOS/Linux:

```sh
ALZ_COMPASS_DATA_MODE=snapshot MCP_TRANSPORT=streamable-http uv run python main.py
```

Open http://127.0.0.1:8000. Search for three candidates, open `NCT03244800`, inspect source fields and download its JSON card. Frozen search uses the six development records and literal intervention-text matching. It does not reproduce the live registry search engine.

Change `ALZ_COMPASS_DATA_MODE` to `live` and restart for current public ClinicalTrials.gov retrieval. Live results and timings may change. The **Ask assistant** function needs a permitted model and Databricks user authorization; plain local card/search controls do not.

## Connect a local MCP client

Start in default stdio mode with `uv run python main.py`. In a client that accepts the common `mcpServers` configuration, substitute the absolute checkout path below:

```json
{
  "mcpServers": {
    "t2d-compass": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/T2D-compass", "run", "python", "main.py"],
      "env": {"ALZ_COMPASS_DATA_MODE": "snapshot", "MCP_TRANSPORT": "stdio"}
    }
  }
}
```

Client configuration formats vary. Discovery should expose exactly `find_completed_trials` and `get_trial_evidence_card`. A JSON-safe Windows path uses forward slashes or escaped backslashes.

## Reproduce checks

```sh
uv run python -m pytest -q
uv run python -m ruff check src tests main.py scripts/build_bundles.py scripts/collect_type2diabetes_data.py
uv run python -m alz_compass.verify --output eval/type2diabetes/results/my-snapshot-replay.json
uv run python -m alz_compass.verify_http --output eval/type2diabetes/results/my-http-check.json
uv run python -m alz_compass.review evaluate --output eval/type2diabetes/results/my-reference-check.json
```

The last command uses the original human-approval form, whose approval fields remain blank; its accuracy result is therefore null. The completed [source-reference technical audit](eval/type2diabetes/results/reference-audit-2026-11-23/README.md) is a separate record, with reproduction instructions pinned to the original version 0.4.0 candidate. See the [evaluation report](docs/EVALUATION.md) for current results. Use `verify --live` for a separate network check and a new filename. Avoid overwriting dated evidence.

## Configuration

Settings can be placed in a local `.env` copied from `.env.example`; `.env` is ignored by Git. Environment variables override that file.

| Setting | Default / use |
| --- | --- |
| `ALZ_COMPASS_DATA_MODE` | `live` or `snapshot` |
| `ALZ_COMPASS_MANIFEST` | Default `data/type2diabetes/manifest.json`; use an absolute path when overriding |
| `MCP_TRANSPORT` | `stdio`; use `streamable-http` for browser/HTTP |
| `MCP_HOST`, `MCP_PORT` | Local `127.0.0.1`, `8000` |
| `DATABRICKS_APP_PORT` / `PORT` | Platform-provided port automatically selects HTTP |
| `DATABRICKS_HOST` | Operator's Databricks workspace origin for assistant calls |
| `ALZ_COMPASS_MODEL` | Existing vendor model name; verify it is available to the user |

The legacy CLI agent additionally reads `DATABRICKS_TOKEN` and can use `ALZ_COMPASS_MCP_TOKEN` for a remote MCP endpoint. Keep credentials in an approved local environment or credential mechanism. The CLI model adapter differs from the browser adapter and needs its own integration verification before scoring a real-model suite.

See [deployment](docs/EASY_DEPLOY.md), [evaluation](docs/EVALUATION.md) and [security](SECURITY.md).
