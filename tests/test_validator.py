from pathlib import Path

from replay_contract_kit.manifest import load_manifest, parse_manifest
from replay_contract_kit.validator import validate_dataset, validate_events

FIXTURE = Path(__file__).parents[1] / "examples" / "synthetic_event_dataset" / "manifest.json"
CSV_FIXTURE = Path(__file__).parents[1] / "examples" / "synthetic_csv_dataset" / "manifest.json"
INVALID_FIXTURE = (
    Path(__file__).parents[1]
    / "examples"
    / "invalid_cases"
    / "duplicate_and_sequence"
    / "manifest.json"
)


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


def test_validate_dataset_passes_csv_fixture():
    report = validate_dataset(load_manifest(CSV_FIXTURE))

    assert report.passed, report.to_dict()
    assert report.rows_read == 4


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


def test_validate_events_reports_invalid_sequence_and_blank_required_fields(tmp_path):
    manifest = _manifest(tmp_path)
    rows = [
        {
            "event_id": "one",
            "device_id": "a",
            "sequence": "not-an-int",
            "observed_at": "2026-01-01T00:00:00Z",
            "split": "train",
        },
        {
            "event_id": "two",
            "device_id": "",
            "sequence": 2,
            "observed_at": "2026-01-01T00:01:00Z",
            "split": "train",
        },
    ]

    report = validate_events(rows, manifest)

    assert not report.passed
    assert any(issue.code == "invalid_sequence" for issue in report.failures)
    assert any(issue.code == "missing_required_field" for issue in report.failures)


def test_validation_report_to_dict_shape_is_stable():
    manifest = _manifest(Path("."))
    report = validate_events([], manifest)

    assert report.to_dict() == {
        "passed": False,
        "checks": 1,
        "rows_read": 0,
        "failures": [
            {
                "code": "empty_event_file",
                "message": "event file contains no rows",
            }
        ],
        "warnings": [],
    }


def test_validate_dataset_annotates_combined_failures_with_phase(tmp_path):
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        '{"event_id":"same","device_id":"a","sequence":1,"observed_at":"2026-01-01T00:00:00Z","split":"train"}\n'
        '{"event_id":"same","device_id":"a","sequence":2,"observed_at":"2026-01-01T00:01:00Z","split":"train"}\n',
        encoding="utf-8",
    )
    manifest = _manifest(tmp_path)

    report = validate_dataset(manifest)

    assert not report.passed
    failure = next(issue for issue in report.failures if issue.code == "duplicate_event")
    assert failure.phase == "events"
    assert failure.to_dict()["phase"] == "events"


def test_invalid_example_fixture_produces_documented_issue_codes():
    report = validate_dataset(load_manifest(INVALID_FIXTURE))

    assert not report.passed
    issues = {(issue.phase, issue.code) for issue in report.failures}
    assert ("events", "duplicate_event") in issues
    assert ("events", "non_monotonic_sequence") in issues
