# Repair a replay contract

The invalid fixture contains three rows. The first two share an event ID, and the third moves the sequence backward. Start from a writable copy:

```bash
cp -R examples/invalid_cases/duplicate_and_sequence /tmp/replay-contract-demo
uv run replay-contract --format human validate-dataset /tmp/replay-contract-demo/manifest.json
```

Expect a failing exit code and both `duplicate_event` and `non_monotonic_sequence`. Open `/tmp/replay-contract-demo/events.jsonl`. Give the second row the distinct `event_id` `evt-002`, then change the third row's `sequence` from `1` to `3`. The fixture's timestamps and split assignments already follow the declared windows.

Validate the copy again:

```bash
uv run replay-contract --format human validate-dataset /tmp/replay-contract-demo/manifest.json
```

It now passes. The correction gives the two events separate identities and places them in a deterministic order. Changing the manifest to omit a required ordering field would weaken the check rather than repair the dataset.

For a real dataset, establish the intended identity and sequence semantics from the producer's contract before changing rows. Do not silently invent timestamps or reorder records to hide a producer error.
