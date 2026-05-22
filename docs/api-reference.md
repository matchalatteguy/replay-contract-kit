# API Reference

Replay Contract Kit exposes a deliberately small public Python API from the top-level `replay_contract_kit` package. The CLI remains the recommended interface for CI and shell workflows; the Python API is useful when you want to validate datasets from a notebook, test suite, or local data-preparation script.

## Stability policy

The names listed in `replay_contract_kit.__all__` are the supported public API for the current `0.x` series. Report JSON keys and issue `code` values are intended to be stable within a manifest schema version, but this project is still alpha: new fields may be added and larger compatibility breaks should be called out in release notes.

Helpers in implementation modules may be useful for contributors, but they should not be treated as stable unless they are exported from the top-level package and documented here.

## Loading manifests

### `load_manifest(path: Path | str) -> DatasetManifest`

Read a JSON manifest from disk and return a typed `DatasetManifest`.

```python
from pathlib import Path

from replay_contract_kit import load_manifest

manifest = load_manifest(Path("examples/synthetic_event_dataset/manifest.json"))
print(manifest.dataset_id)
print(manifest.event_path)
```

Raises a `ManifestError` subclass if the file cannot be read, the JSON is invalid, required fields are missing, or manifest paths are unsafe.

### `parse_manifest(data: dict[str, object], root: Path | str) -> DatasetManifest`

Build a manifest from an already-loaded dictionary and an explicit dataset root. This is useful in tests or tools that generate manifest dictionaries before writing them to disk.

```python
from pathlib import Path

from replay_contract_kit import parse_manifest

manifest = parse_manifest(
    {
        "schema_version": "1.0",
        "dataset_id": "toy-workflow",
        "event_file": "events.csv",
        "event_format": "csv",
        "event_time_field": "created_at",
        "sequence_field": "step_number",
        "entity_keys": ["case_id"],
    },
    root=Path("examples/synthetic_csv_dataset"),
)
```

## Manifest objects

### `DatasetManifest`

A frozen dataclass that represents the normalized replay contract. Important attributes include:

- `root`: dataset directory used for resolving relative paths.
- `dataset_id`: stable dataset slug.
- `event_path`: resolved path to the event file.
- `event_format`: `"jsonl"` or `"csv"`.
- `event_time_field`, `sequence_field`, `entity_keys`: ordering contract fields.
- `event_id_field`: optional event identity field.
- `split_field`, `splits`, `allow_entity_overlap`: split contract settings.
- `artifacts`: mapping of artifact names to `ArtifactSpec`.
- `raw`: original manifest dictionary, including ignored custom fields.

Use `manifest.artifact_path(name)` to resolve a declared artifact path through the same containment rules used by validation:

```python
summary_path = manifest.artifact_path("summary")
```

### `ArtifactSpec`

A frozen dataclass for one declared artifact:

- `path`: manifest-relative path.
- `required`: JSON boolean. Required artifacts fail validation when missing; optional artifacts produce warnings.
- `fields`: top-level JSON fields expected in the artifact.

### `SplitWindow`

A frozen dataclass for an optional split window:

- `start`: ISO-8601 timestamp string or `None`.
- `end`: ISO-8601 timestamp string or `None`.

Window starts are inclusive and ends are exclusive.

## Validating datasets

### `validate_dataset(manifest: DatasetManifest) -> ValidationReport`

Run event, split, and artifact checks and return a single report.

```python
from pathlib import Path

from replay_contract_kit import load_manifest, validate_dataset

manifest = load_manifest(Path("examples/synthetic_event_dataset/manifest.json"))
report = validate_dataset(manifest)

if report.passed:
    print(f"validated {report.rows_read} rows")
else:
    for issue in report.failures:
        print(issue.phase, issue.code, issue.message, issue.row_number, issue.context)
```

The function returns validation failures as data when input files are readable. It may raise `ReplayContractError` subclasses for manifest parsing, unreadable files, invalid JSONL syntax, or unsupported formats.

### `validate_events(rows: Iterable[dict[str, object]], manifest: DatasetManifest) -> ValidationReport`

Validate rows that you loaded yourself. Use this when another tool already has event rows in memory and you only want required-field, duplicate-identity, sequence, and timestamp checks.

```python
from replay_contract_kit import validate_events

rows = [
    {"device_id": "sensor-a", "sequence": 1, "observed_at": "2026-01-01T00:00:00Z"},
]
report = validate_events(rows, manifest)
```

Focused reports from `validate_events()` do not add `phase` because all issues are event issues. `validate_dataset()` adds phases while combining focused reports.

### `validate_splits(rows: Iterable[dict[str, object]], manifest: DatasetManifest) -> ValidationReport`

Validate split labels, split-window membership, row overlap, optional entity overlap, and declared window overlap. Use this when you want to isolate leakage problems after event ordering already passes.

### `validate_artifacts(manifest: DatasetManifest) -> ValidationReport`

Validate declared local artifact paths and optional top-level JSON fields. This does not validate nested fields, types, checksums, or file sizes.

### `load_event_rows(path: Path, event_format: str) -> list[dict[str, object]]`

Load JSON Lines or CSV rows using the same reader as the CLI. Rows are loaded eagerly into memory, so use this helper for small and medium fixtures rather than very large logs.

## Reports and issues

### `ValidationReport`

Stable JSON-serializable result object:

- `passed`: `True` when there are no failures.
- `checks`: count of individual checks performed.
- `rows_read`: event rows consumed by the check.
- `failures`: tuple of `ValidationIssue`.
- `warnings`: tuple of `ValidationIssue`.
- `to_dict()`: returns the same shape emitted by the CLI.

### `ValidationIssue`

One failure or warning:

- `code`: machine-readable issue code such as `duplicate_event`.
- `message`: human-readable description.
- `row_number`: one-based row number when the issue belongs to an event row.
- `context`: small dictionary with extra details such as split name, missing fields, or relative artifact path.
- `phase`: optional source layer. `validate_dataset()` currently uses `events`, `splits`, or `artifacts`.

Do not paste report output from sensitive datasets into public issue trackers without review. Context may include field names, split names, identity hashes, and manifest-relative paths.

## Exceptions

All package-specific exceptions inherit from `ReplayContractError`:

- `ManifestError`: invalid manifest shape, unsupported format, bad JSON, or unreadable event file.
- `PathEscapeError`: absolute path or `..` escape from the dataset root.
- `SequenceContractError`: invalid JSONL rows or sequence/time validation raised through strict helper paths.
- `SplitLeakageError`: reserved for split-leakage failures in exception-oriented integrations.
- `ArtifactContractError`: reserved for artifact-contract failures in exception-oriented integrations.

Most users should consume `ValidationReport` data instead of exception types. Exceptions are mainly useful when you want parse/read errors to stop a pipeline immediately.

## CLI/API equivalence

The CLI subcommands map to the same public helpers:

| CLI | Python helper |
| --- | --- |
| `validate-manifest` | `load_manifest()` |
| `validate-events` | `load_event_rows()` + `validate_events()` |
| `check-splits` | `load_event_rows()` + `validate_splits()` |
| `check-artifacts` | `validate_artifacts()` |
| `validate-dataset` | `validate_dataset()` |

The CLI returns JSON by default and supports `--format human` for compact local summaries.
