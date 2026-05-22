# Examples

This directory contains small, synthetic fixtures for learning and testing Replay Contract Kit.

## `synthetic_event_dataset/`

A five-row JSON Lines dataset that models generic sensor readings.

```text
synthetic_event_dataset/
├── manifest.json
├── events.jsonl
└── artifacts/
    └── replay_summary.json
```

The fixture demonstrates:

- a versioned manifest,
- JSONL events,
- a single entity key (`device_id`),
- strictly increasing sequence numbers per device,
- non-overlapping train/validation/test windows,
- and a required replay summary artifact.

Validate it with:

```bash
uv run replay-contract validate-dataset examples/synthetic_event_dataset/manifest.json
```

Expected result: `passed` is `true`, `rows_read` is `5`, and the failures list is empty.

## `synthetic_csv_dataset/`

A four-row CSV dataset that models generic workflow case events.

```text
synthetic_csv_dataset/
├── manifest.json
├── events.csv
└── artifacts/
    └── replay_summary.json
```

The fixture demonstrates:

- CSV input with `event_format: "csv"`,
- a workflow-style entity key (`case_id`),
- per-case step ordering,
- non-overlapping train/validation/test windows,
- `allow_entity_overlap: false`,
- and a required replay summary artifact.

Validate it with:

```bash
uv run replay-contract validate-dataset examples/synthetic_csv_dataset/manifest.json
```

Expected result: `passed` is `true`, `rows_read` is `4`, and the failures list is empty.

## `invalid_cases/`

Intentionally broken JSON Lines fixtures with expected issue codes.

```text
invalid_cases/
├── README.md
└── duplicate_and_sequence/
    ├── manifest.json
    └── events.jsonl
```

Validate the duplicate/sequence case with:

```bash
uv run replay-contract validate-dataset examples/invalid_cases/duplicate_and_sequence/manifest.json
```

Expected result: the command exits with status `1`; `passed` is `false`; failures include `phase: "events"`, `code: "duplicate_event"`, and `code: "non_monotonic_sequence"`.

These fixtures are useful when learning how report data points back to the source row that needs repair. They should remain invalid.

## Adding more examples

Keep examples synthetic, compact, and deterministic. A good example should teach one idea at a time, such as:

- multi-field entity keys,
- optional artifacts,
- split-window boundary behavior,
- missing artifact fields,
- or another deliberately invalid fixture with expected issue codes.

Do not add live credentials, account identifiers, private hostnames, local absolute paths, or data copied from production systems.
