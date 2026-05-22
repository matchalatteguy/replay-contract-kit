# Invalid example cases

These fixtures are intentionally broken so new users can see concrete issue codes and report shape. They should fail validation.

## duplicate_and_sequence

Run:

```bash
replay-contract validate-dataset examples/invalid_cases/duplicate_and_sequence/manifest.json
```

Expected result: exit code `1`, `passed: false`, and event-phase failures including:

- `duplicate_event` for the reused `evt-001` identity,
- `non_monotonic_sequence` because `sensor-a` moves from sequence `2` back to `1`.

For a terminal-friendly explanation:

```bash
replay-contract --format human validate-dataset examples/invalid_cases/duplicate_and_sequence/manifest.json
```
