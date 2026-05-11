# Hive Mind Goal Sprint

Status: active goal sprint

Codex goal mode is enabled in the operator environment. This document is the
repo-local goal contract for the sprint.

## Final Goal

Hive Mind should become a production-grade local provider-CLI operating harness:

- preserve native Claude, Codex, Gemini, and local-worker capabilities;
- add auditability through run folders, receipts, ledger, proof, and inspect;
- make multi-agent work more reliable than manual shared-folder coordination;
- keep direct provider CLI use preferable for trivial one-shot commands;
- degrade cleanly when MemoryOS, local LLMs, or provider CLIs are unavailable;
- expose prompt/log operation first, with files as internal substrate;
- hand accepted-memory authority to MemoryOS and capability recommendation to
  CapabilityOS.

North star:

```text
AIOS-style prompt/log operation where the user is no longer the hidden
scheduler, hidden database, hidden verifier, or hidden dispatcher.
```

## Non-Goals For This Sprint

- Do not claim autonomous long-horizon cognition.
- Do not claim complete AIOS.
- Do not make MemoryOS required for Hive Mind production-v0.
- Do not replace native provider CLIs with a weaker abstraction.
- Do not optimize for trivial CLI latency over inspectable multi-agent work.

## Production-V0 Exit Criteria

Hive Mind can be called production-v0 only when these are true:

1. `scripts/public-release-check.sh` passes with zero failures.
2. `scripts/user-value-benchmark.py` passes and writes a durable report.
3. `hive provider <provider> --dry-run -- <native args>` preserves native CLI
   args under Hive artifacts.
4. Dangerous provider bypass patterns are blocked before execution.
5. `hive run start/status/tail/stop`, `hive inspect`, `hive ledger replay`,
   `hive next`, and `hive diff` work on a real run.
6. Failed, skipped, timeout, blocked, and stopped paths leave receipts.
7. Direct CLI remains acknowledged as better for trivial one-shot calls.
8. Hive's value is demonstrated for audited work: provenance, recovery,
   multi-agent coordination, policy gates, and reviewer attack hooks.

## Claude Attack Protocol

Claude should attack the goal from a separate context basin when possible. The
attack is successful if it finds a case where Hive is worse than direct CLI
without adding enough audit, policy, or coordination value.

Suggested attack surfaces:

- provider passthrough flags that bypass policy;
- failed or partial executions without receipts;
- ledger drift false positives or false negatives;
- corrupted run state and missing run UX;
- Korean, Unicode, paste, and long prompt handling;
- local runtime missing or slow local model behavior;
- supervisor stale PID, timeout, and stop behavior;
- direct CLI versus Hive overhead on trivial commands;
- multi-agent handoff where Hive adds ceremony but no quality;
- MemoryOS absence and bridge graceful-degrade behavior.

Claude should log findings in `.ai-runs/shared/comms_log.md` and, for release
blockers, write a focused report under `docs/security/` or `docs/reviews/`.

To generate the review packet:

```bash
hive goal --write-attack-pack
```

## Sprint Loop

Repeat this loop until the value benchmark and release gate both stay green
after adversarial review:

1. Run `scripts/user-value-benchmark.py`.
2. Run `scripts/public-release-check.sh`.
3. Fix the highest-risk failure or highest-friction UX issue.
4. Re-run focused tests and the two gates.
5. Log decision, evidence, and next action.

## Current Verdict

Hive Mind production-v0 is technically complete under the narrow local runtime
harness definition. That does not mean the repository is ready for public alpha.

Hive Mind is not faster than direct CLI for trivial calls. That is acceptable
for production-v0 but not enough for public release.

Hive Mind must be better when the task needs:

- more than one agent;
- a durable trail of who did what;
- native CLI execution wrapped in receipts and policy;
- stop/resume/inspect/debug after a run;
- disagreement, verifier, or reviewer pressure;
- later MemoryOS import and context feedback.

## Next Goal: Public Alpha Wow

Before public release, Hive Mind needs a five-minute entry path:

```bash
hive demo quickstart
```

The demo must show prompt intake, role routing, agent artifacts, verification,
memory draft, inspect report, and MemoryOS-compatible observability without
requiring provider keys.
