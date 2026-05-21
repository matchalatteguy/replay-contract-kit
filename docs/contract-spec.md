# Replay Dataset Contract Specification

This document describes schema version `1.0` for Replay Contract Kit manifests.

## Required manifest fields

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | string | Must be `1.0`. |
| `dataset_id` | string | Stable dataset slug. Use letters, numbers, dots, dashes, or underscores. |
| `event_file` | string | Relative path to a JSON Lines or CSV event file. Absolute paths and `..` escapes are rejected. |
| `event_format` | string | `jsonl` or `csv`. |
| `event_time_field` | string | Field containing ISO-8601 text or Unix timestamps. |
| `sequence_field` | string | Integer field that must strictly increase within each entity stream. |
| `entity_keys` | array[string] | One or more fields defining an independent replay stream. |

## Optional manifest fields

| Field | Type | Meaning |
| --- | --- | --- |
| `event_id_field` | string | Unique event identity. If omitted, identity is derived from entity keys, sequence, and time. |
| `split_field` | string | Field containing split names such as `train`, `validation`, or `test`. |
| `splits` | object | Declared split windows with optional `start` and `end` ISO timestamps. End is exclusive. |
| `allow_entity_overlap` | boolean | If `false`, the same entity may not appear in multiple splits. Defaults to `true`. |
| `artifacts` | object | Declared local artifacts created by a replay pipeline. |

## Event sequence rules

For each entity stream:

1. Required fields must be present and non-empty.
2. Sequence values must be integers.
3. Sequence values must strictly increase.
4. Event time values must parse as ISO-8601 text or Unix timestamps.
5. Event time must not move backward.
6. Event identities must not be duplicated.

These checks catch the most common reasons that a replay dataset cannot be deterministically consumed: missing ordering fields, duplicate messages, out-of-order updates, and malformed timestamps.

## Split rules

If a split field is configured:

1. Each row must name a split.
2. Split names should be declared in `splits`.
3. The same event identity must not appear in more than one split.
4. Rows must fall within their declared split time window.
5. Declared split windows must not overlap.
6. If `allow_entity_overlap` is `false`, an entity may appear in only one split.

## Artifact rules

Artifacts are optional contracts for local replay outputs. Each artifact declares a relative `path`, whether it is `required`, and optional top-level JSON `fields`.

```json
"artifacts": {
  "summary": {
    "path": "artifacts/replay_summary.json",
    "required": true,
    "fields": ["dataset_id", "rows_processed", "status"]
  }
}
```

The validator rejects absolute paths and paths that escape the dataset root.
