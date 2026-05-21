# Replay Contract Kit

Replay Contract Kit is a small Python package and CLI for validating deterministic event-sequence datasets before they are used in replay, simulation, backtesting, audit, or evaluation pipelines.

It turns a dataset folder into an explicit replay contract:

- which file contains the events,
- which fields define event time, sequence, entity streams, and event identity,
- which train/validation/test windows are allowed,
- which local output artifacts should exist after a replay run,
- and whether the rows can be consumed deterministically.

The package is intentionally domain-neutral. The included fixture uses synthetic sensor telemetry, but the same contract shape can describe clickstreams, game telemetry, IoT logs, workflow events, support queues, or any ordered event stream that must be replayed reliably.

## Why use it?

Replay failures are usually discovered too late: after an experiment, benchmark, or audit run has already consumed malformed inputs. This kit catches common contract violations up front:

- missing ordering fields,
- duplicate event identities,
- non-monotonic sequence numbers,
- event timestamps that move backward within an entity stream,
- split leakage across event ids, entities, or time windows,
- missing replay output artifacts,
- and unsafe manifest paths such as absolute paths or `..` escapes.

## Install for development

Prerequisites: Python 3.10+ and [`uv`](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
```

Run the CLI from the checkout:

```bash
uv run replay-contract --help
```

## First 5 minutes

Validate the included synthetic JSON Lines dataset:

```bash
uv run replay-contract validate-dataset examples/synthetic_event_dataset/manifest.json
```

Expected output:

```json
{
  "checks": 45,
  "failures": [],
  "passed": true,
  "rows_read": 5,
  "warnings": []
}
```

Validate the included synthetic CSV workflow fixture as a second format smoke test:

```bash
uv run replay-contract validate-dataset examples/synthetic_csv_dataset/manifest.json
```

Expected output has `passed: true` and `rows_read: 4`.

Try the focused checks when you want to debug one layer of the contract:

```bash
uv run replay-contract validate-manifest examples/synthetic_event_dataset/manifest.json
uv run replay-contract validate-events examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-splits examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-artifacts examples/synthetic_event_dataset/manifest.json
```

## Manifest shape

A manifest is a JSON document stored beside the event file it describes:

```json
{
  "schema_version": "1.0",
  "dataset_id": "synthetic-sensor-demo",
  "event_file": "events.jsonl",
  "event_format": "jsonl",
  "event_time_field": "observed_at",
  "sequence_field": "sequence",
  "entity_keys": ["device_id"],
  "event_id_field": "event_id",
  "split_field": "split",
  "allow_entity_overlap": true,
  "splits": {
    "train": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:03:00Z"},
    "validation": {"start": "2026-01-01T00:03:00Z", "end": "2026-01-01T00:04:00Z"},
    "test": {"start": "2026-01-01T00:04:00Z", "end": "2026-01-01T00:05:00Z"}
  },
  "artifacts": {
    "summary": {
      "path": "artifacts/replay_summary.json",
      "required": true,
      "fields": ["dataset_id", "rows_processed", "status"]
    }
  }
}
```

See:

- `docs/quickstart.md` for a CLI walkthrough,
- `docs/contract-spec.md` for the schema and validation rules,
- `docs/adapting-your-dataset.md` for mapping your own data into the contract,
- `examples/README.md` for the included fixture layout.

## Python API

```python
from pathlib import Path

from replay_contract_kit import load_manifest, validate_dataset

manifest = load_manifest(Path("examples/synthetic_event_dataset/manifest.json"))
report = validate_dataset(manifest)

if not report.passed:
    for failure in report.failures:
        print(failure.code, failure.message)
```

`ValidationReport.to_dict()` returns the same stable JSON shape used by the CLI, which makes it easy to plug into CI jobs, notebook checks, or local data-preparation scripts.

## Repository map

```text
.
├── docs/
│   ├── adapting-your-dataset.md   # How to map real data into the generic contract
│   ├── contract-spec.md           # Manifest schema and validation behavior
│   └── quickstart.md              # CLI walkthrough
├── examples/
│   ├── README.md                  # Fixture tour
│   ├── synthetic_event_dataset/   # Synthetic JSONL dataset + artifact
│   └── synthetic_csv_dataset/     # Synthetic CSV workflow dataset + artifact
├── src/replay_contract_kit/       # Library and CLI implementation
└── tests/                         # Pytest coverage for manifest, split, CLI, and validator behavior
```

## Development checks

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
```

## Safety and scope

This project only reads local manifest, event, and artifact files supplied by the user. It has no network calls, scheduler integrations, account setup, credentials, live data connectors, or order/execution workflows. All included examples are synthetic.

Manifest file paths must be relative to the dataset folder. Absolute paths and parent-directory escapes are rejected to keep fixtures portable and public-safe.

## License

MIT
