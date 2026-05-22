# Changelog

All notable changes to Replay Contract Kit are recorded here.

The project follows a simple pre-1.0 policy: keep manifest/report changes additive when possible, document breaking behavior clearly, and preserve stable CLI JSON output for automation.

## Unreleased

### Added

- Public manifest schema at `schema/replay-contract-manifest-1.0.schema.json` for editor and CI validation.
- Failure-driven tutorial showing how to move from invalid rows to a passing replay contract.
- Human CLI summary mode via `replay-contract --format human ...`.
- `replay-contract --version`.
- Validation issue `phase` annotations in full `validate_dataset()` reports so users can distinguish event, split, and artifact failures.
- Public API exports for focused validation helpers: `validate_splits`, `validate_artifacts`, and `load_event_rows`.
- GitHub Actions CI template covering pytest, ruff, example smoke tests, and clean-tree checks.
- Contributor and security guidance for public-safe local-only development.

### Changed

- Documentation now describes install modes, use/not-use guidance, report phases, schema/versioning expectations, and shallow artifact semantics more explicitly.
