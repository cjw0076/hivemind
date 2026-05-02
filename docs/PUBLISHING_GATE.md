# Hive Mind Publishing Gate

Status: release gate.

The GitHub repository may remain public alpha for collaboration and inspection,
but official publishing means a release tag, package publication, announcement,
or broader distribution. Do not do that until Hive Mind is closer to the North
Star.

## North Star

Hive Mind is the chair for provider and local-agent work:

```text
user intent
  -> classify and decompose
  -> gather role-specific context
  -> chaired provider debate when judgment is needed
  -> implementation / review / verification artifacts
  -> disagreement and convergence records
  -> MemoryOS-reviewed memory
  -> next run with better context
```

## Publish Requirements

- `hive debate` extracts structured disagreements, not only round artifacts.
- `hive gaps` connects to the canonical MemoryOS context builder.
- `hive verify` includes semantic objective and acceptance checks for high-risk runs.
- `hive next` gives a short operator decision list grounded in run state and conflicts.
- Security review evidence is preserved under `docs/security/`.
- `scripts/public-release-check.sh` passes.
- README states public alpha limitations clearly and avoids production-grade claims.

## Current Decision

Continue implementation in public alpha. Defer release/tag/package/announcement
publishing until the requirements above are met.
