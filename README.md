# Replay Contract Kit

Validate event ordering, split leakage, and required output files before a replay consumes your dataset. A small manifest tells the validator which fields define time, sequence, stream identity, and split assignments. It returns a JSON report and a useful exit code.

For example, a repeated event ID is a contract failure:

```json
{"code": "duplicate_event", "message": "duplicate event identity", "phase": "events", "row_number": 2}
```

Use this for local replay fixtures, simulation inputs, sensor histories, or workflow logs. It checks the input contract; it does not run the replay or establish that an experiment's conclusions are correct.

## Try it

Python 3.10+ and [uv](https://docs.astral.sh/uv/) are required for the checkout workflow.

```bash
git clone https://github.com/matchalatteguy/replay-contract-kit.git
cd replay-contract-kit
uv sync --locked --extra dev
uv run replay-contract validate-dataset examples/synthetic_event_dataset/manifest.json
```

The included five-event sensor fixture passes:

```json
{"checks": 45, "failures": [], "passed": true, "rows_read": 5, "warnings": []}
```

Then try the broken fixture:

```bash
uv run replay-contract validate-dataset examples/invalid_cases/duplicate_and_sequence/manifest.json
```

It exits `1` and reports both `duplicate_event` and `non_monotonic_sequence`. The [repair tutorial](docs/tutorial.md) walks through a failing dataset and its fix. A [CSV fixture](examples/synthetic_csv_dataset) demonstrates the same contract in a second format.

## Define a contract

Put a manifest beside your event file:

```json
{
  "schema_version": "1.0",
  "dataset_id": "sensor-demo",
  "event_file": "events.jsonl",
  "event_format": "jsonl",
  "event_time_field": "observed_at",
  "sequence_field": "sequence",
  "entity_keys": ["device_id"],
  "event_id_field": "event_id",
  "split_field": "split",
  "splits": {
    "train": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-02T00:00:00Z"},
    "test": {"start": "2026-01-02T00:00:00Z", "end": "2026-01-03T00:00:00Z"}
  },
  "artifacts": {
    "summary": {"path": "summary.json", "fields": ["rows_processed", "status"]}
  }
}
```

The validator checks:

- required event fields, unique identities, integer sequences, and increasing order within each entity stream;
- valid timestamps, with naive ISO timestamps interpreted as UTC;
- split membership, inclusive starts, exclusive ends, overlapping windows, and optional entity separation;
- relative paths contained inside the dataset directory, including resolved symlinks;
- artifact files and optional top-level JSON field presence.

JSON Lines and CSV are supported. CSV rows must have a unique, non-empty header and the declared number of columns. Events are loaded into memory, so this is intended for small and medium local datasets.

## Integrate it

```python
from replay_contract_kit import load_manifest, validate_dataset

report = validate_dataset(load_manifest("dataset/manifest.json"))
if not report.passed:
    for issue in report.failures:
        print(issue.phase, issue.code, issue.row_number, issue.message)
    raise SystemExit(1)
```

The default CLI output is JSON. Use `--format human` before the command for a compact readable report. Focused commands are `validate-manifest`, `validate-events`, `check-splits`, and `check-artifacts`.

| Exit code | Meaning |
| --- | --- |
| `0` | Validation passed |
| `1` | Dataset contract failed |
| `2` | Manifest or input could not be read or parsed |

Install the CLI from a checkout with `uv tool install .`. No package registry release is required.

## Contract and limits

The [contract specification](docs/contract-spec.md), [adaptation guide](docs/adapting-your-dataset.md), and [Python API](docs/api-reference.md) describe supported semantics. The [JSON Schema](schema/replay-contract-manifest-1.0.schema.json) validates structural types; runtime parsing additionally checks timestamp semantics and path containment. Tests exercise parser/schema agreement for structural failures and all bundled manifests.

Artifacts receive shallow checks, not nested type validation, checksums, or proof that they came from the declared events. Custom CSV dialects, streaming validation, and domain-specific payload schemas are outside the current contract. The `0.x` API may evolve; behavior changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## Development

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv build
```

CI runs tests, lint, builds, and an installed-wheel smoke test on Python 3.10–3.14. Runtime validation only reads local files. Included datasets are synthetic; see [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

MIT licensed.
