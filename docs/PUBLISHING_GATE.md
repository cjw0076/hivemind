# Hive Mind Publishing Gate

Status: **production v0 close — active.**

---

## Product Definition (as of 2026-05-09)

> A local, auditable, provider-CLI swarm harness that can run bounded agent
> work, preserve native CLI capabilities, record execution receipts, stop safely,
> and degrade cleanly without MemoryOS.

Hive Mind production does **not** require:
- self-improving AIOS
- complete memory-integrated swarm
- autonomous long-horizon cognition
- CapabilityOS-routed agent operating system

MemoryOS is a substrate for long-term memory. Hive Mind production v0 must
work without it. MemoryOS bridge is optional and gracefully degraded.

---

## H-P0 Production Close Checklist

### 1. Provider CLI wrapping
- [ ] Claude/Codex/Gemini/local native CLI stable passthrough (`hive provider`)
- [x] timeout, exit-code, stdout/stderr artifact, failure checkpoint
- [x] dangerous flag denylist + policy gate before execution
- [x] provider/profile allowlist for `hive provider --execute` safe native profiles
- [x] `--execute` always explicit; dry-run is default

### 2. Execution ledger / receipt / proof
- [ ] every prompt/command/result/artifact path recorded in ledger
- [ ] failed/timeout/partial runs leave a readable artifact
- [x] `hive inspect <run>` emits ledger replay with hash chain
- [x] `hive inspect <run>` surfaces provider receipts and local worker terminal artifacts
- [ ] `hive diff` reports touched files + ledger summary

### 3. Scheduler stability
- [x] L0 pingpong (`--scheduler pingpong`) — one serialized turn per round
- [ ] L1 blackboard/claim — step lease, single controller
- [ ] fanout isolated as experimental / not default in production commands
- [x] `hive run stop` terminates cleanly and writes a stop receipt

### 4. Operator UX (must not require file navigation)
- [ ] `hive run` — start/status/tail/stop
- [ ] `hive status` — current run health without opening run folder
- [ ] `hive live` — real-time event stream
- [x] `hive inspect <run>` — replay/debug artifact report
- [ ] `hive next` — one-line operator decision grounded in run state

### 5. MemoryOS bridge (optional / graceful degrade)
- [x] if MemoryOS is absent, context build silently skips
- [x] if MemoryOS returns empty, run proceeds normally
- [ ] Hive only writes `memory_drafts.json`; acceptance is MemoryOS's decision
- [ ] `hive live --memoryos` emits stable event taxonomy, not Hive action names

### 6. Release hygiene
- [x] `scripts/public-release-check.sh` passes (11/11 checks green as of 2026-05-11)
- [x] README states "provider-CLI harness, production v0" clearly
- [x] security review record under `docs/security/`
- [x] no production-grade AIOS claims in README or CLI output

---

## What Moves to Post-v0

These are not v0 blockers. They belong in MemoryOS or CapabilityOS tracks:

- Structured disagreement extraction in `hive debate` (publish gate item → moved to v1)
- Semantic LLM verifier for high-risk runs (v1)
- RetrievalTrace provenance hardening (MemoryOS K43)
- CapabilityOS routing brain (separate project)

---

## Previous Publish Requirements (superseded)

The prior gate required full MemoryOS integration before release. That was too
broad. The items below are preserved for reference; they move to v1 or MemoryOS
tracks:

- `hive debate` structured disagreement extraction → v1
- `hive gaps` canonical MemoryOS context builder → MemoryOS K43
- `hive verify` semantic acceptance checks → v1
- `hive next` conflict-grounded decision list → H-P0 item 4

---

## Current Decision

Active close. H-P0 checklist drives the sprint.
Tag `v0.1.0-production` when all H-P0 items pass and `public-release-check.sh` is green.
