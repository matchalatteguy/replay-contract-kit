# Adapting Your Dataset

Use this checklist to map a new event-sequence dataset into Replay Contract Kit without coupling the repository to a private domain.

## 1. Choose the dataset root

Put the manifest beside the event file it describes:

```text
my_dataset/
├── manifest.json
├── events.jsonl
└── artifacts/
    └── replay_summary.json
```

All paths in `manifest.json` should be relative to `my_dataset/`.

## 2. Identify the replay stream

Pick fields that answer these questions:

| Question | Manifest field |
| --- | --- |
| Which row order is valid inside one stream? | `sequence_field` |
| Which timestamp should never move backward? | `event_time_field` |
| Which fields identify one independent stream? | `entity_keys` |
| Which field uniquely names a row? | `event_id_field` |

Examples:

- IoT data: `entity_keys: ["device_id"]`, `sequence_field: "sequence"`.
- Game telemetry: `entity_keys: ["match_id", "player_id"]`, `sequence_field: "tick"`.
- Workflow audit logs: `entity_keys: ["case_id"]`, `sequence_field: "step_number"`.

## 3. Pick JSONL or CSV

Set `event_format` to:

- `jsonl` when each line is a JSON object,
- `csv` when the first row contains headers.

JSONL is usually easier for nested or typed event payloads. CSV is useful for spreadsheet-style fixtures.

## 4. Declare split behavior

If your event rows include a split label, set `split_field` and declare windows:

```json
"split_field": "split",
"allow_entity_overlap": true,
"splits": {
  "train": {"start": "2026-01-01T00:00:00Z", "end": "2026-02-01T00:00:00Z"},
  "validation": {"start": "2026-02-01T00:00:00Z", "end": "2026-02-15T00:00:00Z"},
  "test": {"start": "2026-02-15T00:00:00Z", "end": "2026-03-01T00:00:00Z"}
}
```

Use `allow_entity_overlap: false` only when the same entity must not appear in multiple splits. This is strict and may be inappropriate for continuous streams where time-window splits are expected.

## 5. Declare replay outputs

If a replay or evaluation job creates local JSON outputs, declare them as artifacts:

```json
"artifacts": {
  "summary": {
    "path": "artifacts/replay_summary.json",
    "required": true,
    "fields": ["dataset_id", "rows_processed", "status"]
  }
}
```

Keep artifact paths relative. Do not include machine-specific absolute paths, credentials, account names, or live-service URLs in fixtures.

## 6. Validate and iterate

Run checks in this order:

```bash
uv run replay-contract validate-manifest my_dataset/manifest.json
uv run replay-contract validate-events my_dataset/manifest.json
uv run replay-contract check-splits my_dataset/manifest.json
uv run replay-contract check-artifacts my_dataset/manifest.json
uv run replay-contract validate-dataset my_dataset/manifest.json
```

Fix the first failing layer before moving to the next one. This usually produces clearer errors than starting with the full dataset check.

## 7. Keep public examples synthetic

For open-source examples, prefer small synthetic fixtures that demonstrate edge cases without revealing internal systems, customers, local paths, internal repository names, credentials, or live integration details.
