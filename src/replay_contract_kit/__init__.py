"""Public API for Replay Contract Kit."""

from replay_contract_kit.errors import (
    ArtifactContractError,
    ManifestError,
    PathEscapeError,
    ReplayContractError,
    SequenceContractError,
    SplitLeakageError,
)
from replay_contract_kit.manifest import (
    ArtifactSpec,
    DatasetManifest,
    SplitWindow,
    load_manifest,
    parse_manifest,
)
from replay_contract_kit.splits import validate_splits
from replay_contract_kit.validator import (
    ValidationIssue,
    ValidationReport,
    load_event_rows,
    validate_artifacts,
    validate_dataset,
    validate_events,
)

__all__ = [
    "ArtifactContractError",
    "ArtifactSpec",
    "DatasetManifest",
    "ManifestError",
    "PathEscapeError",
    "ReplayContractError",
    "SequenceContractError",
    "SplitLeakageError",
    "SplitWindow",
    "ValidationIssue",
    "ValidationReport",
    "load_manifest",
    "parse_manifest",
    "load_event_rows",
    "validate_artifacts",
    "validate_dataset",
    "validate_events",
    "validate_splits",
]
