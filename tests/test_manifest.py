import json
from pathlib import Path

import pytest

from replay_contract_kit.errors import ManifestError, PathEscapeError
from replay_contract_kit.manifest import load_manifest, parse_manifest

FIXTURE = Path(__file__).parents[1] / "examples" / "synthetic_event_dataset" / "manifest.json"


def test_load_manifest_parses_fixture():
    manifest = load_manifest(FIXTURE)

    assert manifest.dataset_id == "synthetic-sensor-demo"
    assert manifest.event_path.name == "events.jsonl"
    assert manifest.entity_keys == ("device_id",)


def test_manifest_requires_core_fields(tmp_path):
    with pytest.raises(ManifestError, match="missing required fields"):
        parse_manifest({"schema_version": "1.0"}, root=tmp_path)


def test_manifest_rejects_escaping_event_path(tmp_path):
    data = {
        "schema_version": "1.0",
        "dataset_id": "demo",
        "event_file": "../events.jsonl",
        "event_format": "jsonl",
        "event_time_field": "observed_at",
        "sequence_field": "sequence",
        "entity_keys": ["device_id"],
    }

    with pytest.raises(PathEscapeError):
        parse_manifest(data, root=tmp_path)


def test_manifest_rejects_unsupported_schema_and_event_format(tmp_path):
    data = {
        "schema_version": "2.0",
        "dataset_id": "demo",
        "event_file": "events.jsonl",
        "event_format": "jsonl",
        "event_time_field": "observed_at",
        "sequence_field": "sequence",
        "entity_keys": ["device_id"],
    }

    with pytest.raises(ManifestError, match="unsupported schema_version"):
        parse_manifest(data, root=tmp_path)

    data["schema_version"] = "1.0"
    data["event_format"] = "parquet"
    with pytest.raises(ManifestError, match="event_format must be one of"):
        parse_manifest(data, root=tmp_path)


def test_manifest_rejects_invalid_dataset_id_and_entity_keys(tmp_path):
    data = {
        "schema_version": "1.0",
        "dataset_id": "bad id with spaces",
        "event_file": "events.jsonl",
        "event_format": "jsonl",
        "event_time_field": "observed_at",
        "sequence_field": "sequence",
        "entity_keys": ["device_id"],
    }

    with pytest.raises(ManifestError, match="dataset_id must be a short slug"):
        parse_manifest(data, root=tmp_path)

    data["dataset_id"] = "demo"
    data["entity_keys"] = ["device_id", ""]
    with pytest.raises(ManifestError, match=r"entity_keys\[\] must be a non-empty string"):
        parse_manifest(data, root=tmp_path)


def test_manifest_rejects_absolute_and_escaping_artifact_paths(tmp_path):
    data = {
        "schema_version": "1.0",
        "dataset_id": "demo",
        "event_file": "events.jsonl",
        "event_format": "jsonl",
        "event_time_field": "observed_at",
        "sequence_field": "sequence",
        "entity_keys": ["device_id"],
        "artifacts": {"summary": {"path": "/tmp/summary.json"}},
    }

    with pytest.raises(PathEscapeError, match="artifact 'summary' escapes dataset root"):
        parse_manifest(data, root=tmp_path)

    data["artifacts"]["summary"]["path"] = "../summary.json"
    with pytest.raises(PathEscapeError, match="artifact 'summary' escapes dataset root"):
        parse_manifest(data, root=tmp_path)


def test_manifest_rejects_string_booleans(tmp_path):
    data = {
        "schema_version": "1.0",
        "dataset_id": "demo",
        "event_file": "events.jsonl",
        "event_format": "jsonl",
        "event_time_field": "observed_at",
        "sequence_field": "sequence",
        "entity_keys": ["device_id"],
        "allow_entity_overlap": "false",
        "artifacts": {"summary": {"path": "summary.json", "required": "false"}},
    }

    with pytest.raises(ManifestError, match="required must be a boolean"):
        parse_manifest(data, root=tmp_path)

    data["artifacts"]["summary"]["required"] = False
    with pytest.raises(ManifestError, match="allow_entity_overlap must be a boolean"):
        parse_manifest(data, root=tmp_path)


def test_manifest_resolves_artifact_paths_with_public_helper(tmp_path):
    manifest = parse_manifest(
        {
            "schema_version": "1.0",
            "dataset_id": "demo",
            "event_file": "events.jsonl",
            "event_format": "jsonl",
            "event_time_field": "observed_at",
            "sequence_field": "sequence",
            "entity_keys": ["device_id"],
            "artifacts": {"summary": {"path": "artifacts/summary.json"}},
        },
        root=tmp_path,
    )

    assert manifest.artifact_path("summary") == tmp_path.resolve() / "artifacts" / "summary.json"
    with pytest.raises(ManifestError, match="unknown artifact"):
        manifest.artifact_path("missing")


def test_manifest_json_schema_is_valid_json_and_matches_fixture_contract():
    schema_path = Path(__file__).parents[1] / "schema" / "replay-contract-manifest-1.0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    manifest = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert schema["properties"]["schema_version"]["const"] == "1.0"
    assert set(schema["required"]).issubset(manifest)
    assert manifest["event_format"] in schema["properties"]["event_format"]["enum"]
    assert schema["properties"]["allow_entity_overlap"]["type"] == "boolean"
