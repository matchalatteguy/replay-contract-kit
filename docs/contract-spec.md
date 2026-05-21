# Replay Dataset Contract Specification

This document describes manifest schema version `1.0` for Replay Contract Kit.

A replay contract has three goals:

1. make event ordering explicit,
2. make train/validation/test split boundaries auditable,
3. make local replay outputs discoverable and verifiable.

## Manifest location and path rules

A manifest is a JSON file stored inside a dataset directory. Relative paths are resolved from the manifest's parent directory.

The validator rejects:

- absolute paths,
- paths that escape the dataset directory with `..`,
- unsupported event formats,
- missing required manifest fields.

These path rules keep fixtures portable across machines and safe to share publicly.

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

For CSV inputs, all values are read as text. Sequence values still must parse as integers, and timestamp fields follow the same ISO-8601/Unix timestamp rules as JSON Lines rows.

## Split rules

If a split field is configured:

1. Each row must name a split.
2. Split names should be declared in `splits`.
3. The same event identity must not appear in more than one split.
4. Rows must fall within their declared split time window.
5. Declared split windows must not overlap.
6. If `allow_entity_overlap` is `false`, an entity may appear in only one split.

Timestamps may use ISO-8601 text with an explicit offset, a trailing `Z`, naive ISO-8601 text, or Unix timestamps. Naive ISO-8601 timestamps are interpreted as UTC so mixed fixture styles do not crash comparisons.

Split windows use inclusive starts and exclusive ends. This convention makes adjacent windows safe:

```json
{
  "train": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-02T00:00:00Z"},
  "validation": {"start": "2026-01-02T00:00:00Z", "end": "2026-01-03T00:00:00Z"}
}
```

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

The validator checks that required artifacts exist. If `fields` are declared, the artifact must be a JSON object containing those top-level keys.

## Validation report shape

CLI commands and the Python API return a stable report shape:

```json
{
  "passed": true,
  "checks": 45,
  "rows_read": 5,
  "failures": [],
  "warnings": []
}
```

Failures and warnings include a machine-readable `code`, a human-readable `message`, and, when available, `row_number` and `context` fields.

## What this contract does not do

Replay Contract Kit does not fetch remote data, run simulations, place orders, call live services, or infer a domain-specific schema. It validates local files against the manifest you provide.
