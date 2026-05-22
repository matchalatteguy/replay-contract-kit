# Quickstart

This walkthrough assumes Python 3.10+ and `uv` are installed.

## 1. Choose an installation mode

From the repository root, the lowest-friction development path is:

```bash
uv sync --extra dev
uv run replay-contract --help
```

If you want the CLI on your PATH from a local checkout:

```bash
uv tool install .
replay-contract --help
```

Replay Contract Kit does not need environment variables, credentials, config files outside the dataset, or network access. Each dataset is configured by a `manifest.json` stored next to the event file.

## 2. Confirm the CLI is available

```bash
uv run replay-contract --help
uv run replay-contract --version
```

You should see these subcommands:

- `validate-manifest` — validate the JSON manifest and safe relative paths.
- `validate-events` — validate event ordering, required fields, duplicate identities, and timestamps.
- `check-splits` — validate split labels, windows, and leakage rules.
- `check-artifacts` — validate declared local replay artifacts.
- `validate-dataset` — run every check.

The default output is JSON. Add `--format human` before the subcommand for a short local summary:

```bash
uv run replay-contract --format human validate-dataset examples/synthetic_event_dataset/manifest.json
```

## 3. Validate the synthetic JSONL fixture

```bash
uv run replay-contract validate-dataset examples/synthetic_event_dataset/manifest.json
```

Expected result:

```json
{
  "checks": 45,
  "failures": [],
  "passed": true,
  "rows_read": 5,
  "warnings": []
}
```

Exit codes are stable for automation:

- `0`: the contract passed,
- `1`: the manifest parsed, but contract failures were found,
- `2`: the manifest or input file could not be parsed/read.

## 4. Validate the CSV fixture

```bash
uv run replay-contract validate-dataset examples/synthetic_csv_dataset/manifest.json
```

This fixture uses the same contract model with `event_format: "csv"`, workflow-style fields, and `allow_entity_overlap: false`.

## 5. Inspect an intentional failure

```bash
uv run replay-contract validate-dataset examples/invalid_cases/duplicate_and_sequence/manifest.json
```

This command should fail with exit code `1` because row 2 repeats row 1's `event_id` and row 3 moves the entity sequence backward. The JSON failures include `phase: "events"`, `code: "duplicate_event"`, `row_number: 2`, and `code: "non_monotonic_sequence"`.

When debugging your own data, read failures in this order:

1. `phase` — which layer produced the issue: events, splits, or artifacts.
2. `code` — the machine-readable issue family.
3. `row_number` — the one-based row to inspect, when present.
4. `context` — small extra details such as split name, previous row, missing fields, or artifact path.

## 6. Debug one contract layer at a time

```bash
uv run replay-contract validate-manifest examples/synthetic_event_dataset/manifest.json
uv run replay-contract validate-events examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-splits examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-artifacts examples/synthetic_event_dataset/manifest.json
```

Use this sequence when adapting a new dataset: fix manifest problems first, then event ordering, then split leakage, then artifact declarations.

## 7. Adapt to your own dataset

Create a dataset folder with:

- `manifest.json`,
- an event file in JSON Lines or CSV format,
- optional local artifact JSON files.

Point `event_file` and artifact paths to relative paths under that folder. Keep domain-specific fields in your event rows, but map the reusable replay contract fields in the manifest. For example:

| Domain | Entity key | Sequence field | Event time field |
| --- | --- | --- | --- |
| Game telemetry | `match_id` | `tick` | `observed_at` |
| IoT readings | `device_id` | `sequence` | `observed_at` |
| Workflow events | `case_id` | `step_number` | `created_at` |
| Clickstream | `session_id` | `event_index` | `event_time` |

For a fuller checklist, see `docs/adapting-your-dataset.md`. For a fail-fix-pass tutorial, see `docs/tutorial.md`.

## 8. Run project checks before contributing

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
```
