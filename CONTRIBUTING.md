# Contributing

Start with the [quick start](QUICKSTART.md) and [architecture](docs/ARCHITECTURE.md). Keep changes focused and describe the affected behavior, rationale, and verification in the pull request.

## Development checks

```sh
uv sync --locked --group dev
uv run python -m pytest -q
uv run python -m ruff check src tests main.py scripts/build_bundles.py scripts/collect_type2diabetes_data.py
uv run python -m alz_compass.verify --output eval/type2diabetes/results/my-snapshot-replay.json
uv run python -m alz_compass.verify_http --output eval/type2diabetes/results/my-http-check.json
```

Add targeted tests when changing tool behavior, source mapping, validation, or assistant safeguards. Document changes to public tool inputs and output fields. Keep new check outputs separate from dated evidence.

## Data and evaluation

- Use public registry records or clearly labeled synthetic fixtures.
- Preserve original source hashes, split assignments, and frozen evaluation records.
- Record a new dated result when evaluating a changed candidate; do not overwrite prior results.
- Keep observed execution, automated checks, and reviewer assessments distinguishable.
- Never commit patient data, credentials, private prompts, or local configuration files.

Report security concerns using the process in [SECURITY.md](SECURITY.md).
