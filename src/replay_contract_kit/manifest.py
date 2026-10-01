"""Versioned dataset manifest schema and path-safety helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from replay_contract_kit.errors import ManifestError, PathEscapeError
from replay_contract_kit.values import parse_time, strict_json

SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
SUPPORTED_EVENT_FORMATS = {"jsonl", "csv"}
_DATASET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


@dataclass(frozen=True)
class SplitWindow:
    """Declared time window for one dataset split."""

    start: str | None = None
    end: str | None = None


@dataclass(frozen=True)
class ArtifactSpec:
    """Contract for a local output artifact created by a replay pipeline."""

    path: str
    required: bool = True
    fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class DatasetManifest:
    """Parsed replay dataset manifest.

    Paths are resolved relative to ``root`` and must remain inside that root.
    """

    root: Path
    schema_version: str
    dataset_id: str
    event_file: str
    event_format: str
    event_time_field: str
    sequence_field: str
    entity_keys: tuple[str, ...]
    event_id_field: str | None = None
    split_field: str | None = None
    splits: dict[str, SplitWindow] = field(default_factory=dict)
    artifacts: dict[str, ArtifactSpec] = field(default_factory=dict)
    allow_entity_overlap: bool = True
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def event_path(self) -> Path:
        """Return the path to the declared event file after containment checks."""

        return safe_join(self.root, self.event_file)

    def artifact_path(self, name: str) -> Path:
        """Return the resolved path for a declared artifact.

        This keeps consumers from reimplementing manifest-relative path handling
        and preserves the same containment checks used by the built-in validator.
        """

        try:
            artifact = self.artifacts[name]
        except KeyError as exc:
            raise ManifestError(f"unknown artifact: {name!r}") from exc
        return safe_join(self.root, artifact.path)


def load_manifest(path: Path | str) -> DatasetManifest:
    """Load and validate a manifest JSON file."""

    manifest_path = Path(path).resolve()
    try:
        data = strict_json(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise ManifestError(f"manifest is not valid JSON: {exc}") from exc
    except (OSError, UnicodeError) as exc:
        raise ManifestError(f"manifest could not be read: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a JSON object")
    return parse_manifest(data, root=manifest_path.parent)


def parse_manifest(data: dict[str, Any], *, root: Path | str) -> DatasetManifest:
    """Parse a manifest object into a typed ``DatasetManifest``."""

    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a JSON object")

    required = [
        "schema_version",
        "dataset_id",
        "event_file",
        "event_format",
        "event_time_field",
        "sequence_field",
        "entity_keys",
    ]
    missing = [field_name for field_name in required if field_name not in data]
    if missing:
        raise ManifestError(f"manifest missing required fields: {', '.join(missing)}")

    schema_version = _string(data["schema_version"], "schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ManifestError(f"unsupported schema_version: {schema_version!r}")

    dataset_id = _string(data["dataset_id"], "dataset_id")
    if not _DATASET_ID_RE.fullmatch(dataset_id):
        raise ManifestError(
            "dataset_id must be a short slug containing letters, numbers, dots, "
            "dashes, or underscores"
        )

    event_format = _string(data["event_format"], "event_format")
    if event_format not in SUPPORTED_EVENT_FORMATS:
        raise ManifestError(f"event_format must be one of: {sorted(SUPPORTED_EVENT_FORMATS)}")

    entity_keys_value = data["entity_keys"]
    if not isinstance(entity_keys_value, list) or not entity_keys_value:
        raise ManifestError("entity_keys must be a non-empty list of field names")
    entity_keys = tuple(_string(value, "entity_keys[]") for value in entity_keys_value)
    if len(entity_keys) != len(set(entity_keys)):
        raise ManifestError("entity_keys must contain distinct field names")

    split_field = data.get("split_field")
    if "split_field" in data:
        split_field = _string(split_field, "split_field")

    event_id_field = data.get("event_id_field")
    if "event_id_field" in data:
        event_id_field = _string(event_id_field, "event_id_field")

    splits = _parse_splits(data.get("splits", {}))
    artifacts = _parse_artifacts(data.get("artifacts", {}))
    root_path = Path(root).resolve()
    event_file = _string(data["event_file"], "event_file")
    safe_join(root_path, event_file)
    for name, artifact in artifacts.items():
        try:
            safe_join(root_path, artifact.path)
        except PathEscapeError as exc:
            raise PathEscapeError(
                f"artifact {name!r} escapes dataset root: {artifact.path!r}"
            ) from exc

    return DatasetManifest(
        root=root_path,
        schema_version=schema_version,
        dataset_id=dataset_id,
        event_file=event_file,
        event_format=event_format,
        event_time_field=_string(data["event_time_field"], "event_time_field"),
        sequence_field=_string(data["sequence_field"], "sequence_field"),
        entity_keys=entity_keys,
        event_id_field=event_id_field,
        split_field=split_field,
        splits=splits,
        artifacts=artifacts,
        allow_entity_overlap=_bool(data.get("allow_entity_overlap", True), "allow_entity_overlap"),
        raw=dict(data),
    )


def safe_join(root: Path, relative_path: str) -> Path:
    """Resolve ``relative_path`` under ``root`` and reject absolute or escaping paths."""

    if "\x00" in relative_path:
        raise PathEscapeError("paths cannot contain null bytes")
    candidate_raw = Path(relative_path)
    if candidate_raw.is_absolute():
        raise PathEscapeError(f"absolute paths are not allowed: {relative_path!r}")
    candidate = (root / candidate_raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise PathEscapeError(f"path escapes dataset root: {relative_path!r}") from exc
    return candidate


def _parse_splits(value: Any) -> dict[str, SplitWindow]:
    if not isinstance(value, dict):
        raise ManifestError("splits must be an object")
    parsed: dict[str, SplitWindow] = {}
    for name, window_value in value.items():
        split_name = _string(name, "split name")
        if not isinstance(window_value, dict):
            raise ManifestError(f"split {split_name!r} must be an object")
        start = window_value.get("start")
        end = window_value.get("end")
        for boundary in ("start", "end"):
            if boundary in window_value:
                text = _string(window_value[boundary], f"splits.{split_name}.{boundary}")
                if parse_time(text) is None:
                    raise ManifestError(
                        f"splits.{split_name}.{boundary} must be an ISO timestamp or Unix seconds"
                    )
        parsed[split_name] = SplitWindow(start=start, end=end)
    return parsed


def _parse_artifacts(value: Any) -> dict[str, ArtifactSpec]:
    if not isinstance(value, dict):
        raise ManifestError("artifacts must be an object")
    parsed: dict[str, ArtifactSpec] = {}
    for name, spec in value.items():
        artifact_name = _string(name, "artifact name")
        if not isinstance(spec, dict):
            raise ManifestError(f"artifact {artifact_name!r} must be an object")
        if "path" not in spec:
            raise ManifestError(f"artifact {artifact_name!r} missing path")
        fields_value = spec.get("fields", [])
        if not isinstance(fields_value, list):
            raise ManifestError(f"artifact {artifact_name!r} fields must be a list")
        parsed[artifact_name] = ArtifactSpec(
            path=_string(spec["path"], f"artifacts.{artifact_name}.path"),
            required=_bool(spec.get("required", True), f"artifacts.{artifact_name}.required"),
            fields=tuple(
                _string(item, f"artifacts.{artifact_name}.fields[]") for item in fields_value
            ),
        )
    return parsed


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{name} must be a non-empty string")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ManifestError(f"{name} must be a boolean")
    return value
