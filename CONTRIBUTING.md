# Contributing

Thanks for helping improve Replay Contract Kit. The project is intentionally small, local-only, and domain-neutral; contributions should preserve that shape.

## Development setup

Prerequisites: Python 3.10+ and `uv`.

```bash
uv sync --extra dev
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run replay-contract validate-dataset examples/synthetic_event_dataset/manifest.json
uv run replay-contract validate-dataset examples/synthetic_csv_dataset/manifest.json
```

## Contribution checklist

Before opening a change, verify:

- Public examples remain synthetic and compact.
- Docs do not include local absolute paths, user names, hostnames, credentials, private service URLs, or production data.
- Manifest changes are documented in `docs/contract-spec.md` and, when applicable, `schema/replay-contract-manifest-1.0.schema.json`.
- New issue codes or report fields have tests and are described in docs.
- CLI behavior is covered by tests when user-facing flags or exit codes change.
- Generated files, caches, virtualenvs, `dist/`, and bytecode are not tracked.

## Compatibility policy

While the package is `0.x`, APIs may evolve, but changes should still be deliberate:

- Keep `schema_version: "1.0"` backwards-compatible unless a new schema file is added.
- Avoid renaming existing issue codes without a migration note.
- Prefer additive report fields over replacing the existing JSON shape.
- Keep the CLI default JSON output stable for automation.

## Scope boundaries

Good contributions improve local replay contract validation, examples, docs, schema clarity, or tests.

Out of scope for this package:

- live data connectors,
- credential handling,
- network calls,
- schedulers or job runners,
- domain-specific order/execution logic,
- large generated datasets or binary artifacts.
