# Quickstart

This walkthrough assumes Python 3.10+ and `uv` are installed.

## 1. Install developer dependencies

From the repository root:

```bash
uv sync --extra dev
```

## 2. Confirm the CLI is available

```bash
uv run replay-contract --help
```

You should see these subcommands:

- `validate-manifest` — validate the JSON manifest and safe relative paths.
- `validate-events` — validate event ordering, required fields, duplicate identities, and timestamps.
- `check-splits` — validate split labels, windows, and leakage rules.
- `check-artifacts` — validate declared local replay artifacts.
- `validate-dataset` — run every check.

## 3. Validate the synthetic fixture

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

## 4. Debug one contract layer at a time

```bash
uv run replay-contract validate-manifest examples/synthetic_event_dataset/manifest.json
uv run replay-contract validate-events examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-splits examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-artifacts examples/synthetic_event_dataset/manifest.json
```

Use this sequence when adapting a new dataset: fix manifest problems first, then event ordering, then split leakage, then artifact declarations.

## 5. Adapt to your own dataset

Create a dataset folder with:

- `manifest.json`,
- an event file in JSON Lines or CSV format,
- optional local artifact JSON files.

Point `event_file` and artifact paths to relative paths under that folder. Keep domain-specific fields in your event rows, but map the replay contract fields in the manifest. For example:

| Domain | Entity key | Sequence field | Event time field |
| --- | --- | --- | --- |
| Game telemetry | `match_id` | `tick` | `observed_at` |
| IoT readings | `device_id` | `sequence` | `observed_at` |
| Workflow events | `case_id` | `step_number` | `created_at` |
| Clickstream | `session_id` | `event_index` | `event_time` |

For a fuller checklist, see `docs/adapting-your-dataset.md`.

## 6. Run project checks before contributing

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
```
