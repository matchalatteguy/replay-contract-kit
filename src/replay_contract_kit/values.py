"""Shared timestamp and identity rules for event and split validation."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any


def parse_time(value: Any) -> datetime | None:
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc)
        if not isinstance(value, str):
            return None
        text = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            if re.fullmatch(r"[+-]?\d+(?:\.\d+)?", text):
                return datetime.fromtimestamp(float(text), tz=timezone.utc)
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def scalar_identifier(value: Any) -> bool:
    return (
        isinstance(value, (str, int, float))
        and not isinstance(value, bool)
        and (not isinstance(value, float) or math.isfinite(value))
        and (not isinstance(value, str) or bool(value.strip()))
    )


def event_identity(
    row: dict[str, Any],
    entity_keys: tuple[str, ...],
    sequence_field: str,
    time_field: str,
    event_id_field: str | None,
) -> str:
    if event_id_field and event_id_field in row:
        return str(row[event_id_field])
    # Structured serialization avoids delimiter collisions between composite keys.
    sequence = row.get(sequence_field)
    try:
        if isinstance(sequence, (str, int)) and not isinstance(sequence, bool):
            sequence = int(sequence)
    except ValueError:
        pass
    event_time = parse_time(row.get(time_field))
    payload = {
        "entity": [row.get(key) for key in entity_keys],
        "sequence": sequence,
        "time": event_time.isoformat() if event_time is not None else row.get(time_field),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def strict_json(text: str) -> Any:
    """Reject duplicate members and non-standard constants instead of overwriting rules."""

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, value in pairs:
            if name in result:
                raise ValueError(f"duplicate JSON member: {name!r}")
            result[name] = value
        return result

    def invalid_constant(value: str) -> Any:
        raise ValueError(f"non-standard JSON constant: {value}")

    return json.loads(text, object_pairs_hook=object_pairs, parse_constant=invalid_constant)
