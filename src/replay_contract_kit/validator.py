"""Dataset contract validators for replayable event sequences."""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from replay_contract_kit.errors import ArtifactContractError, ManifestError, SequenceContractError
from replay_contract_kit.manifest import DatasetManifest, safe_join
from replay_contract_kit.splits import validate_splits


@dataclass(frozen=True)
class ValidationIssue:
    """One validation warning or failure."""

    code: str
    message: str
    row_number: int | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.row_number is not None:
            data["row_number"] = self.row_number
        if self.context:
            data["context"] = self.context
        return data


@dataclass(frozen=True)
class ValidationReport:
    """Stable JSON-serializable validation result."""

    passed: bool
    checks: int
    failures: tuple[ValidationIssue, ...] = ()
    warnings: tuple[ValidationIssue, ...] = ()
    rows_read: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "rows_read": self.rows_read,
            "failures": [issue.to_dict() for issue in self.failures],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


def validate_dataset(manifest: DatasetManifest) -> ValidationReport:
    """Validate manifest, events, split contract, and declared artifacts."""

    event_rows = load_event_rows(manifest.event_path, event_format=manifest.event_format)
    sequence_report = validate_events(event_rows, manifest)
    split_report = validate_splits(event_rows, manifest)
    artifact_report = validate_artifacts(manifest)
    failures = (*sequence_report.failures, *split_report.failures, *artifact_report.failures)
    warnings = (*sequence_report.warnings, *split_report.warnings, *artifact_report.warnings)
    return ValidationReport(
        passed=not failures,
        checks=sequence_report.checks + split_report.checks + artifact_report.checks,
        failures=failures,
        warnings=warnings,
        rows_read=sequence_report.rows_read,
    )


def validate_events(rows: Iterable[dict[str, Any]], manifest: DatasetManifest) -> ValidationReport:
    """Validate required fields, duplicates, and monotonic order for event rows."""

    failures: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    checks = 0
    rows_seen = 0
    seen_event_keys: set[str] = set()
    last_by_entity: dict[tuple[Any, ...], tuple[Any, datetime | None, int]] = {}
    required_fields = [
        manifest.sequence_field,
        manifest.event_time_field,
        *manifest.entity_keys,
    ]
    if manifest.event_id_field:
        required_fields.append(manifest.event_id_field)
    if manifest.split_field:
        required_fields.append(manifest.split_field)

    for row_number, row in enumerate(rows, start=1):
        rows_seen += 1
        for field_name in required_fields:
            checks += 1
            if field_name not in row or row[field_name] in (None, ""):
                failures.append(
                    ValidationIssue(
                        "missing_required_field",
                        f"required field {field_name!r} is missing or empty",
                        row_number=row_number,
                    )
                )
        if any(
            field_name not in row or row[field_name] in (None, "") for field_name in required_fields
        ):
            continue

        sequence = _coerce_sequence(row[manifest.sequence_field], row_number, failures)
        event_time = _coerce_time(row[manifest.event_time_field], row_number, failures)
        entity_key = tuple(row[key] for key in manifest.entity_keys)
        identity = _event_identity(row, manifest, entity_key)
        checks += 1
        if identity in seen_event_keys:
            failures.append(
                ValidationIssue(
                    "duplicate_event",
                    "duplicate event identity",
                    row_number=row_number,
                    context={"identity": identity},
                )
            )
        seen_event_keys.add(identity)

        if sequence is None:
            continue
        previous = last_by_entity.get(entity_key)
        if previous is not None:
            previous_sequence, previous_time, previous_row = previous
            checks += 1
            if sequence <= previous_sequence:
                failures.append(
                    ValidationIssue(
                        "non_monotonic_sequence",
                        "sequence must strictly increase within each entity stream",
                        row_number=row_number,
                        context={
                            "previous_row": previous_row,
                            "previous_sequence": previous_sequence,
                        },
                    )
                )
            if event_time is not None and previous_time is not None and event_time < previous_time:
                failures.append(
                    ValidationIssue(
                        "non_monotonic_event_time",
                        "event time must not move backward within each entity stream",
                        row_number=row_number,
                        context={
                            "previous_row": previous_row,
                            "previous_time": previous_time.isoformat(),
                        },
                    )
                )
        last_by_entity[entity_key] = (sequence, event_time, row_number)

    checks += 1
    if rows_seen == 0:
        failures.append(ValidationIssue("empty_event_file", "event file contains no rows"))
    return ValidationReport(
        passed=not failures,
        checks=checks,
        failures=tuple(failures),
        warnings=tuple(warnings),
        rows_read=rows_seen,
    )


def validate_artifacts(manifest: DatasetManifest) -> ValidationReport:
    """Validate declared artifact paths and optional JSON field contracts."""

    failures: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    checks = 0
    for name, artifact in manifest.artifacts.items():
        checks += 1
        path = safe_join(manifest.root, artifact.path)
        if not path.exists():
            if artifact.required:
                failures.append(
                    ValidationIssue(
                        "missing_required_artifact",
                        f"artifact {name!r} does not exist",
                        context={"path": artifact.path},
                    )
                )
            else:
                warnings.append(
                    ValidationIssue(
                        "missing_optional_artifact",
                        f"optional artifact {name!r} does not exist",
                        context={"path": artifact.path},
                    )
                )
            continue
        if artifact.fields:
            checks += 1
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                failures.append(
                    ValidationIssue(
                        "artifact_invalid_json",
                        f"artifact {name!r} is not valid JSON: {exc}",
                        context={"path": artifact.path},
                    )
                )
                continue
            if not isinstance(payload, dict):
                failures.append(
                    ValidationIssue(
                        "artifact_not_object",
                        f"artifact {name!r} must contain a JSON object",
                        context={"path": artifact.path},
                    )
                )
                continue
            missing_fields = [
                field_name for field_name in artifact.fields if field_name not in payload
            ]
            if missing_fields:
                failures.append(
                    ValidationIssue(
                        "artifact_missing_fields",
                        f"artifact {name!r} missing required fields",
                        context={"path": artifact.path, "missing": missing_fields},
                    )
                )
    return ValidationReport(
        passed=not failures, checks=checks, failures=tuple(failures), warnings=tuple(warnings)
    )


def load_event_rows(path: Path, *, event_format: str) -> list[dict[str, Any]]:
    """Load JSON Lines or CSV events into dictionaries."""

    try:
        if event_format == "jsonl":
            return _load_jsonl(path)
        if event_format == "csv":
            return _load_csv(path)
    except OSError as exc:
        raise ManifestError(f"event file could not be read: {exc}") from exc
    raise ManifestError(f"unsupported event format: {event_format!r}")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SequenceContractError(f"invalid JSON on line {line_number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise SequenceContractError(f"line {line_number} must contain a JSON object")
        rows.append(payload)
    return rows


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _coerce_sequence(value: Any, row_number: int, failures: list[ValidationIssue]) -> int | None:
    try:
        if isinstance(value, bool):
            raise TypeError
        return int(value)
    except (TypeError, ValueError):
        failures.append(
            ValidationIssue(
                "invalid_sequence", "sequence must be an integer", row_number=row_number
            )
        )
        return None


def _coerce_time(value: Any, row_number: int, failures: list[ValidationIssue]) -> datetime | None:
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        text = str(value)
        if text.endswith("Z"):
            text = f"{text[:-1]}+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OSError):
        failures.append(
            ValidationIssue(
                "invalid_event_time",
                "event time must be ISO-8601 text or a Unix timestamp",
                row_number=row_number,
            )
        )
        return None


def _event_identity(
    row: dict[str, Any], manifest: DatasetManifest, entity_key: tuple[Any, ...]
) -> str:
    if manifest.event_id_field:
        return str(row[manifest.event_id_field])
    payload = {
        "entity": entity_key,
        "sequence": row.get(manifest.sequence_field),
        "time": row.get(manifest.event_time_field),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def raise_for_report(report: ValidationReport) -> None:
    """Raise a typed public error for the first failed validation issue."""

    if report.passed:
        return
    first = report.failures[0]
    if first.code.startswith("artifact") or first.code.startswith("missing_required_artifact"):
        raise ArtifactContractError(first.message)
    raise SequenceContractError(first.message)
