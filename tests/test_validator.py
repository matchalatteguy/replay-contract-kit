from pathlib import Path

from replay_contract_kit.manifest import load_manifest, parse_manifest
from replay_contract_kit.validator import validate_dataset, validate_events

FIXTURE = Path(__file__).parents[1] / "examples" / "synthetic_event_dataset" / "manifest.json"


def _manifest(tmp_path, **overrides):
    data = {
        "schema_version": "1.0",
        "dataset_id": "demo",
        "event_file": "events.jsonl",
        "event_format": "jsonl",
        "event_time_field": "observed_at",
        "sequence_field": "sequence",
        "entity_keys": ["device_id"],
        "event_id_field": "event_id",
        "split_field": "split",
    }
    data.update(overrides)
    return parse_manifest(data, root=tmp_path)


def test_validate_dataset_passes_synthetic_fixture():
    report = validate_dataset(load_manifest(FIXTURE))

    assert report.passed, report.to_dict()
    assert report.rows_read == 5


def test_validate_events_catches_duplicate_event_id(tmp_path):
    manifest = _manifest(tmp_path)
    rows = [
        {
            "event_id": "same",
            "device_id": "a",
            "sequence": 1,
            "observed_at": "2026-01-01T00:00:00Z",
            "split": "train",
        },
        {
            "event_id": "same",
            "device_id": "a",
            "sequence": 2,
            "observed_at": "2026-01-01T00:01:00Z",
            "split": "train",
        },
    ]

    report = validate_events(rows, manifest)

    assert not report.passed
    assert any(issue.code == "duplicate_event" for issue in report.failures)


def test_validate_events_catches_out_of_order_sequence(tmp_path):
    manifest = _manifest(tmp_path)
    rows = [
        {
            "event_id": "one",
            "device_id": "a",
            "sequence": 2,
            "observed_at": "2026-01-01T00:00:00Z",
            "split": "train",
        },
        {
            "event_id": "two",
            "device_id": "a",
            "sequence": 1,
            "observed_at": "2026-01-01T00:01:00Z",
            "split": "train",
        },
    ]

    report = validate_events(rows, manifest)

    assert not report.passed
    assert any(issue.code == "non_monotonic_sequence" for issue in report.failures)


def test_validate_events_catches_out_of_order_time(tmp_path):
    manifest = _manifest(tmp_path)
    rows = [
        {
            "event_id": "one",
            "device_id": "a",
            "sequence": 1,
            "observed_at": "2026-01-01T00:02:00Z",
            "split": "train",
        },
        {
            "event_id": "two",
            "device_id": "a",
            "sequence": 2,
            "observed_at": "2026-01-01T00:01:00Z",
            "split": "train",
        },
    ]

    report = validate_events(rows, manifest)

    assert not report.passed
    assert any(issue.code == "non_monotonic_event_time" for issue in report.failures)


def test_validate_events_normalizes_naive_iso_timestamps(tmp_path):
    manifest = _manifest(tmp_path)
    rows = [
        {
            "event_id": "one",
            "device_id": "a",
            "sequence": 1,
            "observed_at": "2026-01-01T00:00:00Z",
            "split": "train",
        },
        {
            "event_id": "two",
            "device_id": "a",
            "sequence": 2,
            "observed_at": "2026-01-01T00:01:00",
            "split": "train",
        },
    ]

    report = validate_events(rows, manifest)

    assert report.passed, report.to_dict()
