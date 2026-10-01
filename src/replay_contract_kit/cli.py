"""Command-line interface for Replay Contract Kit."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.metadata import PackageNotFoundError, version
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


def _package_version() -> str:
    try:
        return version("replay-contract-kit")
    except PackageNotFoundError:
        return "0.0.0+local"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="replay-contract", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    parser.add_argument(
        "--format",
        choices=("json", "human"),
        default="json",
        help="output format for successful validation reports (default: json)",
    )
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
    if args.format == "human":
        print(_format_human(payload))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("passed") else 1


def _format_human(payload: dict[str, object]) -> str:
    status = "PASS" if payload.get("passed") else "FAIL"
    lines = [
        f"{status}: {payload.get('checks', 0)} checks, {payload.get('rows_read', 0)} rows read"
    ]
    failures = payload.get("failures")
    if isinstance(failures, list) and failures:
        lines.append("Failures:")
        for issue in failures:
            if not isinstance(issue, dict):
                continue
            phase = f"[{issue['phase']}] " if issue.get("phase") else ""
            row = f" row {issue['row_number']}:" if issue.get("row_number") is not None else ":"
            lines.append(f"- {phase}{issue.get('code')}{row} {issue.get('message')}")
    warnings = payload.get("warnings")
    if isinstance(warnings, list) and warnings:
        lines.append("Warnings:")
        for issue in warnings:
            if isinstance(issue, dict):
                phase = f"[{issue['phase']}] " if issue.get("phase") else ""
                lines.append(f"- {phase}{issue.get('code')}: {issue.get('message')}")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
