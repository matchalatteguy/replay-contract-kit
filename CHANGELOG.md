# Changelog

## 0.2.0 — 2026-10-01

- Reject fractional or boolean sequences instead of truncating them; reject structured/non-finite identifiers with a validation issue.
- Reject duplicate JSON members instead of silently overwriting constraints; split labels must be non-empty strings.
- Invalid declared split timestamps now raise `ManifestError`. Open-ended and nested windows participate in overlap checks.
- Use identical canonical event identity rules for event and split validation; composite identifiers cannot collide through delimiter joining.
- Support numeric Unix-seconds text in CSV timestamps. Reject ambiguous CSV headers and column counts.
- Align manifest parser and structural JSON Schema for optional fields, null values, non-empty strings, and distinct entity keys. Invalid path/timestamp semantics receive additional runtime checks.
- Add Python 3.10–3.14 CI, parser/schema regressions, wheel installation smoke tests, a repair tutorial, and the typed-package marker.

These changes tighten validation of previously accepted malformed inputs. Valid bundled manifests and the CLI report structure are unchanged. Unknown metadata fields remain permitted.

## 0.1.0

Initial local manifest, event-ordering, split, artifact, and CLI validators.
