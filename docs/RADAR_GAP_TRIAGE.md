# Hive Radar Gap Triage

Generated for MyWorld contract `ASC-0020`.

## Source Inventory

- `docs/AGENT_WORKLOG.md`: high-signal execution history. Use it as evidence
  for what already landed, not as a direct backlog.
- `docs/HIVE_MIND_GAPS.md`: architectural gap mirror from MemoryOS. Use it to
  preserve the north-star gap categories.
- `docs/TODO.md`: current repo-local backlog authority. Use unchecked items
  here as the source of executable packets.

## Do Not Reopen

These gap categories are already materially closed in Hive and should not be
reissued as fresh work without a narrower regression:

- MemoryOS pre-run context bridge: implemented through the real
  `memoryos context build --for hive --json` bridge and recorded in TODO.
- Artifact-to-outcome verification: TODO records objective, scope,
  acceptance, and trust checks as closed.
- Handoff quality gate: TODO records objective/files/constraints/acceptance
  criteria/risk/test fields as closed.
- Routing evidence: TODO records task type, risk, required tools, availability,
  latency/cost, performance history, user preference, and local confidence as
  closed.
- Cross-agent conflict artifacts: TODO records conflict set artifacts and
  reviewer disposition flow as closed.
- Operator next surface: TODO records `hive next` as grounded in run state,
  disagreement topology, DAG state, provider failures, and fallback.
- Public-alpha onboarding, memory-loop demo, and H-P0 runtime hardening:
  worklog entries show these are completed and verified.

## Current Unchecked Hive Candidates

The remaining candidates that are still Hive-owned and do not require
CapabilityOS first are:

1. Arrival packs generated from live run state:
   objective, owners, blocked tasks, accepted claims, contested claims, scope,
   logs, and latest artifacts.
2. Source-read registry that records which source artifacts each agent read and
   can flag divergent interpretations.
3. `HANDOFF.json`/shared-folder compatibility import so old MemoryOS pingpong
   loops can be replayed into Hive run artifacts.
4. `hive evaluate` / `hive subagents review` command that runs verifier,
   product evaluator, and actual-user persona checks into durable artifacts.
5. Semantic verifier LLM review for high-risk runs.

Candidates that should remain held until CapabilityOS evidence improves:

- provider-family routing policy;
- capability-performance memory by provider/role/task shape/outcome;
- schema-validated router with provider fallback and route-quality scoring.

## Selected Next Packet

### ASC-0021 — Hive Arrival Pack

- target_repo: `hivemind`
- target_agent: `codex`
- goal: add a repo-local arrival pack surface that generates a compact
  incoming-agent brief from current run state.
- reason: this directly closes the "arriving blind" and "user as context
  relay" problems in `docs/HIVE_MIND_GAPS.md`, and it is executable without
  waiting on CapabilityOS.
- likely_allowed_files:
  - `hivemind/arrival_pack.py`
  - `hivemind/hive.py`
  - `tests/test_arrival_pack.py`
  - `docs/TODO.md`
  - `docs/AGENT_WORKLOG.md`
  - `.ai-runs/shared/comms_log.md`
- forbidden_files:
  - `.runs/**`
  - `data/**`
  - `raw_exports/**`
  - `exports/**`
  - `logs/**`
  - `weights/**`
  - `.env`
  - `.env.*`
- verification_gate:
  - `python -m pytest tests/test_arrival_pack.py -v`
  - `python -m hivemind.hive arrival-pack --run <fixture-run> --json`
- expected_result:
  - a JSON arrival pack with objective, run id, owners/agents, blocked items,
    accepted/contested claims when present, scope hints, latest artifacts,
    suggested commands, and privacy-safe path references.
- stop_conditions:
  - arrival pack includes raw provider stdout/stderr bodies;
  - arrival pack requires MemoryOS or CapabilityOS to be available;
  - implementation mutates `.runs/**` fixtures instead of using synthetic test
    roots;
  - command duplicates `hive inspect` without incoming-agent fields.

## Operator Note

The loop policy can keep using `docs/AGENT_WORKLOG.md` as a high-signal source,
but new contracts should resolve through current unchecked TODO items before
dispatch. Worklog history alone is not an implementation target.
