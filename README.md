# Replay Contract Kit

Replay Contract Kit is a small Python package and CLI for validating deterministic event-sequence datasets before they are used in replay, simulation, backtesting, or audit pipelines.

It helps answer practical questions:

- Does the dataset manifest declare the fields needed to replay events in order?
- Are event sequence numbers and timestamps monotonic within each entity stream?
- Are duplicate event identities present?
- Do declared train/validation/test splits leak rows, entities, or time ranges?
- Are output artifacts listed in a stable, public schema?

The package is intentionally domain-neutral. The examples use synthetic sensor telemetry, but the same contract shape can describe clickstreams, game telemetry, IoT logs, workflow events, or any event sequence that needs deterministic replay.

## Install for development

```bash
uv sync --extra dev
```

Or use the package directly from a checkout:

```bash
python -m replay_contract_kit.cli --help
```

## Quickstart

Validate the included synthetic dataset:

```bash
replay-contract validate-dataset examples/synthetic_event_dataset/manifest.json
```

Equivalent module invocation:

```bash
python -m replay_contract_kit.cli validate-dataset examples/synthetic_event_dataset/manifest.json
```

A successful run prints JSON similar to:

```json
{
  "passed": true,
  "checks": 12,
  "failures": [],
  "warnings": []
}
```

## Manifest shape

A manifest is a JSON document with a versioned contract:

```json
{
  "schema_version": "1.0",
  "dataset_id": "synthetic-sensor-demo",
  "event_source": "offline synthetic fixture",
  "event_file": "events.jsonl",
  "event_format": "jsonl",
  "event_time_field": "observed_at",
  "sequence_field": "sequence",
  "entity_keys": ["device_id"],
  "event_id_field": "event_id",
  "split_field": "split",
  "splits": {
    "train": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:03:00Z"},
    "validation": {"start": "2026-01-01T00:03:00Z", "end": "2026-01-01T00:04:00Z"},
    "test": {"start": "2026-01-01T00:04:00Z", "end": "2026-01-01T00:05:00Z"}
  }
}
```

See `docs/contract-spec.md` for the full schema and `docs/quickstart.md` for CLI walkthroughs.

## Python API

```python
from pathlib import Path

from replay_contract_kit import load_manifest, validate_dataset

manifest = load_manifest(Path("examples/synthetic_event_dataset/manifest.json"))
report = validate_dataset(manifest)
assert report.passed
```

## Safety and scope

This project only reads local manifest and event files supplied by the user. It has no network calls, scheduler integrations, account setup, or deployment workflow assumptions. All included examples are synthetic.

## License

MIT
