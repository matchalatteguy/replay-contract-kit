# Agent Notes

This repository is a public-safe Python project for validating local replay dataset contracts.

## Work safely

- Keep examples synthetic and compact.
- Do not add live service integrations, credential handling, network calls, order/execution flows, or scheduler assumptions.
- Do not include private project names, local absolute paths, usernames, hostnames, tokens, customer data, or production datasets in docs, code, tests, or examples.
- Prefer generic domain examples such as sensor, game, workflow, or clickstream events.

## Development loop

```bash
uv sync --extra dev
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run replay-contract validate-dataset examples/synthetic_event_dataset/manifest.json
```

## Important files

- `README.md`: project overview and first-5-minute experience.
- `docs/contract-spec.md`: manifest and validation rules.
- `docs/adapting-your-dataset.md`: checklist for mapping new data.
- `examples/`: public-safe synthetic fixtures.
- `src/replay_contract_kit/`: library and CLI.
- `tests/`: pytest coverage.
