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
