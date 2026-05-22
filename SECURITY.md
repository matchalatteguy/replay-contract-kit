# Security

Replay Contract Kit is a local-file validator. It does not make network calls, connect to services, read environment credentials, or execute replay workloads.

## Supported threat model

The package is designed to help catch local dataset-contract problems before replay or evaluation:

- unsafe manifest paths such as absolute paths or `..` escapes,
- malformed manifests,
- duplicate event identities,
- non-monotonic sequence or event-time ordering,
- split leakage,
- missing or malformed local artifacts.

It is not a sandbox for untrusted files. Treat manifests, JSONL/CSV rows, and artifacts as local input data that may appear in validation reports.

## Sensitive data guidance

Do not put secrets, access tokens, private URLs, customer data, production identifiers, or local machine paths in manifests, examples, event rows, or artifact paths. CLI JSON can include issue context such as field names, row numbers, event identities, split names, and relative artifact paths.

## Reporting issues

If you find a path traversal issue, accidental sensitive-data exposure pattern, or another security problem, report it through the repository's private vulnerability reporting channel if one exists. If no channel is configured yet, open a minimal issue that describes the class of problem without attaching secrets or private datasets.

## Maintainer release checks

Before release or publication:

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run replay-contract validate-dataset examples/synthetic_event_dataset/manifest.json
git status --short
```

Confirm generated artifacts, caches, virtualenvs, build outputs, and local datasets are untracked.
