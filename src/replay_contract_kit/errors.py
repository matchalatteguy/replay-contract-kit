"""Typed exceptions raised by Replay Contract Kit."""

from __future__ import annotations


class ReplayContractError(ValueError):
    """Base class for public contract validation failures."""


class ManifestError(ReplayContractError):
    """A manifest is missing required fields or has invalid values."""


class SequenceContractError(ReplayContractError):
    """Events violate deterministic replay sequence rules."""


class SplitLeakageError(ReplayContractError):
    """Dataset splits overlap or leak time/entity information."""


class ArtifactContractError(ReplayContractError):
    """Declared artifacts are missing or do not match their contract."""


class PathEscapeError(ManifestError):
    """A manifest path escapes the dataset root."""
