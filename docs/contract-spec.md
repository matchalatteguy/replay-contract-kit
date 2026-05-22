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
| `allow_entity_overlap` | boolean | If `false`, the same entity may not appear in multiple splits. Defaults to `true`. Must be a JSON boolean, not a string such as `"false"`. |
| `artifacts` | object | Declared local artifacts created by a replay pipeline. |

Unknown fields are preserved on `DatasetManifest.raw` but ignored by current runtime validation. The draft JSON Schema in `schema/replay-contract-manifest-1.0.schema.json` is stricter and rejects additional properties for portable public fixtures. Keep custom fields generic and public-safe if you intentionally use them outside schema-validated examples.

## Event sequence rules

For each entity stream:

1. Required fields must be present and non-empty.
2. Sequence values must be integers.
3. Sequence values must strictly increase.
4. Event time values must parse as ISO-8601 text or Unix timestamps.
5. Event time must not move backward.
6. Event identities must not be duplicated.

These checks catch the most common reasons that a replay dataset cannot be deterministically consumed: missing ordering fields, duplicate messages, out-of-order updates, and malformed timestamps.

If `event_id_field` is omitted, the event identity is a deterministic hash derived from the entity keys, sequence field, and event time field. This is portable, but less readable in failures than a real event id.

For CSV inputs, all values are read as text with Python's default `csv.DictReader` behavior. Sequence values still must parse as integers, and timestamp fields follow the same ISO-8601/Unix timestamp rules as JSON Lines rows.

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

Artifacts are optional contracts for local replay outputs. Each artifact declares a relative `path`, whether it is `required`, and optional top-level JSON `fields`. The `required` value must be a JSON boolean, not a string.

```json
"artifacts": {
  "summary": {
    "path": "artifacts/replay_summary.json",
    "required": true,
    "fields": ["dataset_id", "rows_processed", "status"]
  }
}
```

The validator checks that required artifacts exist. If `fields` are declared, the artifact must be a JSON object containing those top-level keys. It does not currently validate nested paths, field types, checksums, glob patterns, or size limits.

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

Failures and warnings include a machine-readable `code`, a human-readable `message`, and, when available, `phase`, `row_number`, and `context` fields.

`phase` is added by `validate_dataset()` when merging focused reports. Current phase values are `events`, `splits`, and `artifacts`.

## Issue codes

Common issue codes include:

| Code | Phase | Meaning |
| --- | --- | --- |
| `missing_required_field` | events | A configured event field is missing or empty. |
| `invalid_sequence` | events | The sequence value is not an integer. |
| `invalid_event_time` | events | The event time is not ISO-8601 text or a Unix timestamp. |
| `duplicate_event` | events | Two rows share the same event identity. |
| `non_monotonic_sequence` | events | A sequence did not strictly increase within an entity stream. |
| `non_monotonic_event_time` | events | Event time moved backward within an entity stream. |
| `empty_event_file` | events | The event file had no rows. |
| `missing_split` | splits | A row is missing its split assignment. |
| `unknown_split` | splits | A row names a split not declared in the manifest. |
| `row_overlap_between_splits` | splits | The same event identity appears in multiple splits. |
| `entity_overlap_between_splits` | splits | An entity appears in multiple splits while entity overlap is disabled. |
| `split_time_before_start` | splits | A row appears before its declared split window. |
| `split_time_after_end` | splits | A row is on or after its split window's exclusive end. |
| `invalid_split_window` | splits | A split window starts at or after its end. |
| `overlapping_split_windows` | splits | Declared split windows overlap. |
| `missing_required_artifact` | artifacts | A required artifact file does not exist. |
| `missing_optional_artifact` | artifacts | An optional artifact file does not exist; this is a warning. |
| `artifact_invalid_json` | artifacts | An artifact with declared fields is not valid JSON. |
| `artifact_not_object` | artifacts | An artifact with declared fields is not a JSON object. |
| `artifact_missing_fields` | artifacts | A declared top-level artifact field is missing. |

## Configuration and environment

There is no `.env` file and no runtime environment configuration. The manifest is the configuration. This is deliberate: replay fixtures should be deterministic, portable, and safe to validate in CI without credentials or service access.

## Versioning policy

Manifest `schema_version: "1.0"` means the required/optional fields and validation semantics described here. Within the `0.x` package series, report objects may gain additive fields, but issue codes and existing top-level report keys should remain stable for schema `1.0` unless a release note says otherwise.

A future manifest schema should use a new `schema_version` when changing required fields, path semantics, split semantics, or artifact semantics in a non-backward-compatible way.

## Current limitations

- Event rows are loaded eagerly into memory.
- CSV dialect options, duplicate-header checks, and schema inference are not modeled.
- Artifact checks are shallow by design.
- A draft standalone JSON Schema exists, but schema/parser parity should be checked in CI before treating it as a release guarantee.
- Human-readable CLI output is intentionally compact; JSON remains the best automation interface.

## What this contract does not do

Replay Contract Kit does not fetch remote data, run simulations, place orders, call live services, infer a domain-specific schema, manage credentials, or read environment variables. It validates local files against the manifest you provide.
