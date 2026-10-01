"""Regressions for inputs that previously bypassed or crashed validation."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from replay_contract_kit.cli import main
from replay_contract_kit.errors import ManifestError, SequenceContractError
from replay_contract_kit.manifest import parse_manifest
from replay_contract_kit.splits import validate_splits
from replay_contract_kit.validator import load_event_rows, validate_events

ROOT = Path(__file__).parents[1]
BASE = json.loads((ROOT / "examples/synthetic_event_dataset/manifest.json").read_text())
SCHEMA = json.loads((ROOT / "schema/replay-contract-manifest-1.0.schema.json").read_text())


@pytest.mark.parametrize(
    "patch",
    [
        {"event_format": "JSONL"},
        {"event_id_field": None},
        {"split_field": None},
        {"splits": None},
        {"artifacts": None},
        {"entity_keys": ["device_id", "device_id"]},
        {"event_time_field": " "},
        {"allow_entity_overlap": 1},
        {"splits": {"train": {"start": None}}},
        {"artifacts": {"summary": {"path": "summary.json", "fields": [" "]}}},
    ],
)
def test_parser_and_schema_reject_same_structural_errors(tmp_path, patch):
    payload = BASE | patch
    assert not Draft202012Validator(SCHEMA).is_valid(payload)
    with pytest.raises(ManifestError):
        parse_manifest(payload, root=tmp_path)


def test_schema_and_parser_accept_fixtures_and_extension_metadata(tmp_path):
    Draft202012Validator.check_schema(SCHEMA)
    for manifest_path in (ROOT / "examples").rglob("manifest.json"):
        payload = json.loads(manifest_path.read_text()) | {"description": "extra metadata"}
        Draft202012Validator(SCHEMA).validate(payload)
        parse_manifest(payload, root=tmp_path)


@pytest.mark.parametrize("boundary", ["not-a-time", "2026-99-99", "1e999"])
def test_invalid_split_timestamp_cannot_disable_window(tmp_path, boundary):
    payload = BASE | {"splits": {"train": {"start": boundary}}}
    with pytest.raises(ManifestError, match="ISO timestamp"):
        parse_manifest(payload, root=tmp_path)


@pytest.mark.parametrize("sequence", [True, 1.2, 1.0, float("inf")])
def test_sequence_does_not_truncate_fractions_or_accept_booleans(tmp_path, sequence):
    manifest = parse_manifest(BASE, root=tmp_path)
    report = validate_events([row(sequence=sequence)], manifest)
    assert "invalid_sequence" in {issue.code for issue in report.failures}


@pytest.mark.parametrize("identifier", [{"nested": 1}, ["a"], True, float("nan")])
def test_structured_identity_returns_failure_instead_of_crashing(tmp_path, identifier):
    manifest = parse_manifest(BASE, root=tmp_path)
    report = validate_events([row(device_id=identifier)], manifest)
    assert "invalid_identity" in {issue.code for issue in report.failures}
    assert not validate_splits([row(device_id=identifier)], manifest).passed


@pytest.mark.parametrize("timestamp", [True, float("inf"), 10**100, [], "invalid"])
def test_bad_timestamps_fail_without_overflow(tmp_path, timestamp):
    manifest = parse_manifest(BASE, root=tmp_path)
    assert not validate_events([row(observed_at=timestamp)], manifest).passed
    assert not validate_splits([row(observed_at=timestamp)], manifest).passed


def test_derived_identity_uses_identical_rules_in_split_and_event_checks(tmp_path):
    payload = {key: value for key, value in BASE.items() if key != "event_id_field"}
    payload["splits"] = {}
    manifest = parse_manifest(payload, root=tmp_path)
    rows = [row(sequence=1), row(sequence="01", split="test")]
    assert "duplicate_event" in {issue.code for issue in validate_events(rows, manifest).failures}
    assert "row_overlap_between_splits" in {
        issue.code for issue in validate_splits(rows, manifest).failures
    }


def test_composite_identity_has_no_delimiter_collision(tmp_path):
    payload = BASE | {"entity_keys": ["left", "right"], "splits": {}}
    del payload["event_id_field"]
    manifest = parse_manifest(payload, root=tmp_path)
    report = validate_splits(
        [row(left="a|b", right="c"), row(left="a", right="b|c", split="test")], manifest
    )
    assert report.passed, report.to_dict()


def test_open_ended_windows_cannot_hide_overlap(tmp_path):
    payload = BASE | {
        "splits": {
            "train": {"start": "2026-01-01T00:00:00Z"},
            "test": {"start": "2026-01-02T00:00:00Z", "end": "2026-01-03T00:00:00Z"},
        }
    }
    report = validate_splits([], parse_manifest(payload, root=tmp_path))
    assert "overlapping_split_windows" in {issue.code for issue in report.failures}


@pytest.mark.parametrize("csv", ["a,a\n1,2\n", "a,b\n1,2,3\n", "a,b\n1\n", ",a\n1,2\n"])
def test_ambiguous_csv_is_rejected(tmp_path, csv):
    path = tmp_path / "events.csv"
    path.write_text(csv)
    with pytest.raises(SequenceContractError):
        load_event_rows(path, event_format="csv")


def test_cli_emits_structured_error_for_invalid_manifest_boundary(tmp_path, capsys):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(BASE | {"splits": {"train": {"start": "garbage"}}}))
    assert main(["validate-manifest", str(path)]) == 2
    assert json.loads(capsys.readouterr().err)["error"] == "ManifestError"


def test_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    dataset = tmp_path / "dataset"
    dataset.mkdir()
    (dataset / "events.jsonl").symlink_to(outside / "events.jsonl")
    with pytest.raises(ManifestError, match="escapes"):
        parse_manifest(BASE, root=dataset)


def row(**overrides):
    return {
        "event_id": "one",
        "device_id": "a",
        "sequence": 1,
        "observed_at": "2026-01-01T00:00:00Z",
        "split": "train",
    } | overrides


def test_csv_unix_timestamp_text_is_supported(tmp_path):
    manifest = parse_manifest(BASE, root=tmp_path)
    assert validate_events([row(observed_at="1767225600")], manifest).passed


def test_split_time_is_required_when_window_is_declared(tmp_path):
    manifest = parse_manifest(BASE, root=tmp_path)
    event = row()
    del event["observed_at"]
    assert not validate_splits([event], manifest).passed


def test_duplicate_json_manifest_cannot_override_policy(tmp_path):
    from replay_contract_kit.manifest import load_manifest

    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps(BASE)[:-1] + ', "allow_entity_overlap": false, "allow_entity_overlap": true}'
    )
    with pytest.raises(ManifestError, match="duplicate JSON member"):
        load_manifest(path)


def test_duplicate_event_members_are_rejected(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"sequence": 1, "sequence": 2}')
    with pytest.raises(SequenceContractError, match="duplicate JSON member"):
        load_event_rows(path, event_format="jsonl")


@pytest.mark.parametrize("split", [{"label": "train"}, ["train"], 1, True])
def test_split_name_must_be_text_even_without_declared_windows(tmp_path, split):
    manifest = parse_manifest(BASE | {"splits": {}}, root=tmp_path)
    assert not validate_splits([row(split=split)], manifest).passed
