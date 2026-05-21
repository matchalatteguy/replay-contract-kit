# Quickstart

## 1. Install developer dependencies

```bash
uv sync --extra dev
```

## 2. Validate the synthetic fixture

```bash
uv run replay-contract validate-dataset examples/synthetic_event_dataset/manifest.json
```

The command returns pretty-printed JSON. Exit code `0` means the dataset passed. Exit code `1` means contract failures were found. Exit code `2` means the manifest or input file could not be parsed.

## 3. Try individual checks

```bash
uv run replay-contract validate-manifest examples/synthetic_event_dataset/manifest.json
uv run replay-contract validate-events examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-splits examples/synthetic_event_dataset/manifest.json
uv run replay-contract check-artifacts examples/synthetic_event_dataset/manifest.json
```

## 4. Adapt to your own dataset

Create a folder with:

- a manifest JSON file,
- an event file in JSON Lines or CSV format,
- optional artifact JSON files.

Point `event_file` and artifact paths to relative paths under that folder. Keep the fields domain-specific in your event rows, but map the replay contract fields in the manifest. For example, a game replay dataset might use `match_id` as the entity key, while a sensor dataset might use `device_id`.
