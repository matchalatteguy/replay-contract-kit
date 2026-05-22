# Replay Contract Kit

Replay Contract Kit is a small Python package and CLI for validating local event-sequence datasets before they are used in replay, simulation, backtesting, audit, or evaluation pipelines.

It turns a dataset folder into an explicit replay contract:

- which file contains the events,
- which fields define event time, sequence, entity streams, and event identity,
- which split windows are allowed,
- which local output artifacts should exist after a replay run,
- and whether the rows can be consumed deterministically.

The package is intentionally domain-neutral. The included fixtures use synthetic sensor and workflow data, but the same contract shape can describe clickstreams, game telemetry, IoT logs, support queues, job histories, or any ordered event stream that must be replayed reliably.

## Who this is for

Use Replay Contract Kit when you have local, ordered event rows and want a CI-friendly contract check before another tool consumes them. It is most useful for:

- replay fixtures used by tests or evaluations,
- simulation/backtest inputs that need deterministic ordering,
- ML or analytics datasets built from event logs,
- audit timelines where split leakage would invalidate results,
- examples generated for agents or notebooks that should stay portable.

## What this is not

Replay Contract Kit is not a database validator, schema inference engine, full data-quality framework, ETL runner, replay engine, scheduler, live connector, or credential manager. It only reads local files named by a manifest and reports contract failures.

## Why use it?

Replay failures are usually discovered too late: after an experiment, benchmark, or audit run has already consumed malformed inputs. This kit catches common contract violations up front:

- missing ordering fields,
- duplicate event identities,
- non-monotonic sequence numbers,
- event timestamps that move backward within an entity stream,
- split leakage across event ids, entities, or time windows,
- missing replay output artifacts,
- and unsafe manifest paths such as absolute paths or `..` escapes.

## Installation modes

Prerequisites for development: Python 3.10+ and [`uv`](https://docs.astral.sh/uv/).

Use from a checkout without installing globally:

```bash
uv sync --extra dev
uv run replay-contract --help
```

Install the CLI from a local checkout when you want `replay-contract` on your PATH:

```bash
uv tool install .
replay-contract --help
```

Editable contributor install:

```bash
uv sync --extra dev
uv run --extra dev pytest -q
uv run --extra dev ruff check .
```

PyPI/package-registry instructions are intentionally not shown here until the package is published. Until then, use the checkout or local tool install commands above.

## Configuration and environment

No environment variables, service credentials, API keys, or network access are required. Configuration lives in each dataset's `manifest.json`.

Paths in a manifest are resolved relative to the manifest file. Absolute paths and parent-directory escapes are rejected so fixtures can move between machines and remain safe to publish.

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

Try human-readable output for local debugging:

```bash
uv run replay-contract --format human validate-dataset examples/synthetic_event_dataset/manifest.json
```

Try the focused checks when you want to debug one layer of the contract:

```bash
uv run replay-contract validate-manifest examples/synthetic_event_dataset/manifest.json
uv run replay-contract validate-events examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-splits examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-artifacts examples/synthetic_event_dataset/manifest.json
```

## Failure example

The invalid fixture intentionally repeats an event id and moves an entity sequence backward:

```bash
uv run replay-contract validate-dataset examples/invalid_cases/duplicate_and_sequence/manifest.json
```

The command exits with status `1` and reports a machine-readable failure similar to:

```json
{
  "code": "duplicate_event",
  "message": "duplicate event identity",
  "phase": "events",
  "row_number": 2
}
```

Use the `phase`, `code`, `row_number`, and `context` fields to decide whether the fix belongs in the manifest, event rows, split assignments, or artifact outputs.

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
- `docs/contract-spec.md` for manifest and validation semantics,
- `docs/api-reference.md` for the supported Python API,
- `docs/tutorial.md` for a failure-to-pass walkthrough,
- `docs/adapting-your-dataset.md` for mapping your own data into the contract,
- `examples/README.md` for the included fixture layout,
- `schema/replay-contract-manifest-1.0.schema.json` for the draft JSON Schema.

## Python API

```python
from pathlib import Path

from replay_contract_kit import load_manifest, validate_dataset

manifest = load_manifest(Path("examples/synthetic_event_dataset/manifest.json"))
report = validate_dataset(manifest)
summary_path = manifest.artifact_path("summary")

if not report.passed:
    for failure in report.failures:
        print(failure.phase, failure.code, failure.row_number, failure.message)
```

`ValidationReport.to_dict()` returns the same stable JSON shape used by the CLI, which makes it easy to plug into CI jobs, notebook checks, or local data-preparation scripts. Full `validate_dataset()` reports annotate failures with `phase` so callers can route fixes to events, splits, or artifacts. `validate_events`, `validate_splits`, `validate_artifacts`, and `load_event_rows` are documented public helpers. `DatasetManifest.event_path` and `DatasetManifest.artifact_path(name)` expose manifest-relative paths without making callers duplicate the kit's path-containment rules.

## Repository map

```text
.
├── docs/
│   ├── adapting-your-dataset.md      # How to map your data into the generic contract
│   ├── api-reference.md              # Supported top-level Python API
│   ├── contract-spec.md              # Manifest schema and validation behavior
│   ├── tutorial.md                   # Learn from an intentional contract failure
│   └── quickstart.md                 # CLI walkthrough
├── examples/
│   ├── README.md                     # Fixture tour
│   ├── invalid_cases/                # Intentional failure fixtures with expected issue codes
│   ├── synthetic_event_dataset/      # Synthetic JSONL dataset + artifact
│   └── synthetic_csv_dataset/        # Synthetic CSV workflow dataset + artifact
├── schema/                           # Draft JSON Schema for manifest 1.0
├── src/replay_contract_kit/          # Library and CLI implementation
└── tests/                            # Pytest coverage for manifest, split, CLI, and validator behavior
```

## Validation report shape

Successful commands return JSON by default:

```json
{
  "passed": true,
  "checks": 45,
  "rows_read": 5,
  "failures": [],
  "warnings": []
}
```

Failures and warnings include:

- `phase`: `events`, `splits`, or `artifacts` for full dataset validation,
- `code`: stable machine-readable issue code,
- `message`: human-readable explanation,
- `row_number`: one-based event row number when available,
- `context`: small extra details such as split name, missing fields, or relative artifact path.

Exit codes are stable for automation:

- `0`: the command passed,
- `1`: the manifest parsed but validation failures were found,
- `2`: the manifest or input file could not be parsed/read.

## Current limitations

- Event rows are loaded eagerly into memory. The kit is best suited to small and medium local fixtures, not multi-gigabyte logs.
- CSV support uses Python's default `csv.DictReader` behavior; custom dialects and duplicate-header checks are not modeled yet.
- Artifact checks are shallow: existence plus optional top-level JSON fields. Nested selectors, checksums, glob patterns, and type checks are out of scope for the current manifest version.
- A draft JSON Schema is included, but parser/schema parity still needs release-level hardening and CI validation.
- The project is alpha (`0.x`); public API names exported from `replay_contract_kit.__all__` are documented, but larger compatibility breaks can still happen before `1.0`.

## Development checks

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
```

## Safety and scope

This project only reads local manifest, event, and artifact files supplied by the user. It has no network calls, scheduler integrations, account setup, credentials, live data connectors, or order/execution workflows. All included examples are synthetic.

Manifest file paths must be relative to the dataset folder. Absolute paths and parent-directory escapes are rejected to keep fixtures portable and public-safe.

Do not put credentials, private hostnames, account identifiers, local absolute paths, or production data in manifests, examples, reports, or issue trackers. CLI output may include field names, split names, identity hashes, and manifest-relative artifact paths.

## License

MIT
