import json
from pathlib import Path

from replay_contract_kit.cli import main
from replay_contract_kit.manifest import parse_manifest
from replay_contract_kit.splits import validate_splits
from replay_contract_kit.validator import validate_artifacts

FIXTURE = Path(__file__).parents[1] / "examples" / "synthetic_event_dataset" / "manifest.json"


def test_split_checker_catches_time_window_leak(tmp_path):
    manifest = parse_manifest(
        {
            "schema_version": "1.0",
            "dataset_id": "demo",
            "event_file": "events.jsonl",
            "event_format": "jsonl",
            "event_time_field": "observed_at",
            "sequence_field": "sequence",
            "entity_keys": ["device_id"],
            "event_id_field": "event_id",
            "split_field": "split",
            "splits": {"train": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T00:01:00Z"}},
        },
        root=tmp_path,
    )
    rows = [
        {
            "event_id": "one",
            "device_id": "a",
            "sequence": 1,
            "observed_at": "2026-01-01T00:02:00Z",
            "split": "train",
        }
    ]

    report = validate_splits(rows, manifest)

    assert not report.passed
    assert any(issue.code == "split_time_after_end" for issue in report.failures)


def test_split_checker_normalizes_naive_iso_timestamps(tmp_path):
    manifest = parse_manifest(
        {
            "schema_version": "1.0",
            "dataset_id": "demo",
            "event_file": "events.jsonl",
            "event_format": "jsonl",
            "event_time_field": "observed_at",
            "sequence_field": "sequence",
            "entity_keys": ["device_id"],
            "event_id_field": "event_id",
            "split_field": "split",
            "splits": {
                "train": {
                    "start": "2026-01-01T00:00:00Z",
                    "end": "2026-01-01T00:02:00Z",
                }
            },
        },
        root=tmp_path,
    )
    rows = [
        {
            "event_id": "one",
            "device_id": "a",
            "sequence": 1,
            "observed_at": "2026-01-01T00:01:00",
            "split": "train",
        }
    ]

    report = validate_splits(rows, manifest)

    assert report.passed, report.to_dict()


def test_split_checker_catches_entity_leakage_when_disabled(tmp_path):
    manifest = parse_manifest(
        {
            "schema_version": "1.0",
            "dataset_id": "demo",
            "event_file": "events.jsonl",
            "event_format": "jsonl",
            "event_time_field": "observed_at",
            "sequence_field": "sequence",
            "entity_keys": ["device_id"],
            "event_id_field": "event_id",
            "split_field": "split",
            "allow_entity_overlap": False,
        },
        root=tmp_path,
    )
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
            "observed_at": "2026-01-01T00:01:00Z",
            "split": "test",
        },
    ]

    report = validate_splits(rows, manifest)

    assert not report.passed
    assert any(issue.code == "entity_overlap_between_splits" for issue in report.failures)


def test_artifact_checker_catches_missing_json_fields(tmp_path):
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "summary.json").write_text(
        json.dumps({"status": "completed"}), encoding="utf-8"
    )
    manifest = parse_manifest(
        {
            "schema_version": "1.0",
            "dataset_id": "demo",
            "event_file": "events.jsonl",
            "event_format": "jsonl",
            "event_time_field": "observed_at",
            "sequence_field": "sequence",
            "entity_keys": ["device_id"],
            "artifacts": {
                "summary": {
                    "path": "artifacts/summary.json",
                    "fields": ["status", "rows_processed"],
                }
            },
        },
        root=tmp_path,
    )

    report = validate_artifacts(manifest)

    assert not report.passed
    assert any(issue.code == "artifact_missing_fields" for issue in report.failures)


def test_cli_validate_dataset_outputs_json(capsys):
    exit_code = main(["validate-dataset", str(FIXTURE)])

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert exit_code == 0
    assert payload["passed"] is True


def test_cli_reports_contract_failure(tmp_path, capsys):
    manifest_path = tmp_path / "manifest.json"
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "event_id": "one",
                "device_id": "a",
                "sequence": 1,
                "observed_at": "2026-01-01T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
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
        ),
        encoding="utf-8",
    )

    exit_code = main(["validate-dataset", str(manifest_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["passed"] is False
    assert payload["failures"]
