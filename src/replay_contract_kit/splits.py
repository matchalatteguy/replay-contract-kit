"""Split contract validators for replay datasets."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from replay_contract_kit.manifest import DatasetManifest
from replay_contract_kit.values import event_identity, parse_time, scalar_identifier

if TYPE_CHECKING:
    from replay_contract_kit.validator import ValidationReport


def validate_splits(rows: Iterable[dict[str, Any]], manifest: DatasetManifest) -> ValidationReport:
    """Validate split row overlap, optional entity leakage, and time windows."""

    from replay_contract_kit.validator import ValidationIssue, ValidationReport

    if not manifest.split_field and not manifest.splits:
        return ValidationReport(passed=True, checks=1, rows_read=0)
    failures: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []
    checks = 0
    rows_seen = 0
    row_keys_by_split: dict[str, set[str]] = defaultdict(set)
    entities_by_split: dict[str, set[tuple[Any, ...]]] = defaultdict(set)
    times_by_split: dict[str, list[datetime]] = defaultdict(list)

    for row_number, row in enumerate(rows, start=1):
        rows_seen += 1
        if not manifest.split_field:
            break
        split = row.get(manifest.split_field)
        checks += 1
        if not isinstance(split, str) or not split.strip():
            failures.append(
                ValidationIssue(
                    "missing_split", "row is missing split assignment", row_number=row_number
                )
            )
            continue
        split_name = split
        if manifest.splits and split_name not in manifest.splits:
            failures.append(
                ValidationIssue(
                    "unknown_split",
                    "row split is not declared in manifest",
                    row_number=row_number,
                    context={"split": split_name},
                )
            )
        row_key = _row_key(row, manifest)
        row_keys_by_split[split_name].add(row_key)
        if all(scalar_identifier(row.get(key)) for key in manifest.entity_keys):
            entities_by_split[split_name].add(tuple(row[key] for key in manifest.entity_keys))
        else:
            failures.append(
                ValidationIssue(
                    "invalid_split_entity", "invalid entity identity", row_number=row_number
                )
            )
        if manifest.splits or manifest.event_time_field in row:
            event_time = _parse_time(row.get(manifest.event_time_field))
            if event_time is None:
                failures.append(
                    ValidationIssue(
                        "invalid_split_event_time", "invalid event time", row_number=row_number
                    )
                )
            if event_time is not None:
                times_by_split[split_name].append(event_time)
                window = manifest.splits.get(split_name)
                if window is not None:
                    start = _parse_time(window.start) if window.start else None
                    end = _parse_time(window.end) if window.end else None
                    if start and event_time < start:
                        failures.append(
                            ValidationIssue(
                                "split_time_before_start",
                                "row event time is before declared split start",
                                row_number=row_number,
                                context={"split": split_name, "start": start.isoformat()},
                            )
                        )
                    if end and event_time >= end:
                        failures.append(
                            ValidationIssue(
                                "split_time_after_end",
                                "row event time is on or after declared split end",
                                row_number=row_number,
                                context={"split": split_name, "end": end.isoformat()},
                            )
                        )

    split_names = sorted(row_keys_by_split)
    for index, left in enumerate(split_names):
        for right in split_names[index + 1 :]:
            checks += 1
            overlap = row_keys_by_split[left] & row_keys_by_split[right]
            if overlap:
                failures.append(
                    ValidationIssue(
                        "row_overlap_between_splits",
                        "the same event identity appears in multiple splits",
                        context={"left": left, "right": right, "overlap_count": len(overlap)},
                    )
                )
            if not manifest.allow_entity_overlap:
                entity_overlap = entities_by_split[left] & entities_by_split[right]
                if entity_overlap:
                    failures.append(
                        ValidationIssue(
                            "entity_overlap_between_splits",
                            "the same entity appears in multiple splits while "
                            "entity overlap is disabled",
                            context={
                                "left": left,
                                "right": right,
                                "overlap_count": len(entity_overlap),
                            },
                        )
                    )
    checks += 1
    _check_declared_window_order(manifest, failures)
    return ValidationReport(
        passed=not failures,
        checks=checks,
        failures=tuple(failures),
        warnings=tuple(warnings),
        rows_read=rows_seen,
    )


def _check_declared_window_order(manifest: DatasetManifest, failures: list[Any]) -> None:
    from replay_contract_kit.validator import ValidationIssue

    windows = []
    for name, window in manifest.splits.items():
        start = _parse_time(window.start) if window.start else None
        end = _parse_time(window.end) if window.end else None
        if start and end and start >= end:
            failures.append(
                ValidationIssue(
                    "invalid_split_window",
                    "split start must be before split end",
                    context={"split": name},
                )
            )
        if start or end:
            windows.append((name, start, end))
    minimum = datetime.min.replace(tzinfo=timezone.utc)
    maximum = datetime.max.replace(tzinfo=timezone.utc)
    for index, (left_name, left_start, left_end) in enumerate(windows):
        for right_name, right_start, right_end in windows[index + 1 :]:
            if max(left_start or minimum, right_start or minimum) < min(
                left_end or maximum, right_end or maximum
            ):
                failures.append(
                    ValidationIssue(
                        "overlapping_split_windows",
                        "declared split time windows overlap",
                        context={"left": left_name, "right": right_name},
                    )
                )


def _row_key(row: dict[str, Any], manifest: DatasetManifest) -> str:
    return event_identity(
        row,
        manifest.entity_keys,
        manifest.sequence_field,
        manifest.event_time_field,
        manifest.event_id_field,
    )


def _parse_time(value: Any) -> datetime | None:
    return parse_time(value)
