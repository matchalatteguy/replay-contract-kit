"""Command-line interface for Replay Contract Kit."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from replay_contract_kit.errors import ReplayContractError
from replay_contract_kit.manifest import load_manifest
from replay_contract_kit.splits import validate_splits
from replay_contract_kit.validator import (
    load_event_rows,
    validate_artifacts,
    validate_dataset,
    validate_events,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="replay-contract", description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    manifest_parser = subcommands.add_parser(
        "validate-manifest", help="validate a manifest JSON file"
    )
    manifest_parser.add_argument("manifest", type=Path)

    events_parser = subcommands.add_parser(
        "validate-events", help="validate event sequence contracts"
    )
    events_parser.add_argument("manifest", type=Path)

    splits_parser = subcommands.add_parser("check-splits", help="validate replay split contracts")
    splits_parser.add_argument("manifest", type=Path)

    artifacts_parser = subcommands.add_parser(
        "check-artifacts", help="validate declared artifact contracts"
    )
    artifacts_parser.add_argument("manifest", type=Path)

    dataset_parser = subcommands.add_parser("validate-dataset", help="run all validation checks")
    dataset_parser.add_argument("manifest", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        if args.command == "validate-manifest":
            payload = {
                "passed": True,
                "dataset_id": manifest.dataset_id,
                "schema_version": manifest.schema_version,
            }
        elif args.command == "validate-events":
            rows = load_event_rows(manifest.event_path, event_format=manifest.event_format)
            payload = validate_events(rows, manifest).to_dict()
        elif args.command == "check-splits":
            rows = load_event_rows(manifest.event_path, event_format=manifest.event_format)
            payload = validate_splits(rows, manifest).to_dict()
        elif args.command == "check-artifacts":
            payload = validate_artifacts(manifest).to_dict()
        else:
            payload = validate_dataset(manifest).to_dict()
    except ReplayContractError as exc:
        payload = {"passed": False, "error": type(exc).__name__, "message": str(exc)}
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
