# Hive Mind Gaps And Next Loop

Status: source mirror / implementation reference.

Source: `/home/user/workspaces/jaewon/myworld/memoryOS/docs/shared/HIVE_MIND_GAPS.md`.

This Hive Mind copy preserves a MemoryOS-side gap report produced while multiple
agents were working across the sibling `memoryOS` project. Treat it as source
evidence for Hive Mind development priorities, not as a MemoryOS implementation
file. Update the MemoryOS original first if the shared diagnosis changes.

This note is for Hive Mind agents. It records the current architectural gap from the MemoryOS side so future Hive work can move from artifact harness toward a learning operator loop.

## Current Diagnosis

Hive Mind is no longer just a way to call several AI CLIs. Its real job is to coordinate agents, produce durable run artifacts, verify outcomes, and feed reviewed memory into the next run.

The current weak point is the closed loop:

```text
accepted MemoryOS context
  -> Hive run context pack
  -> agent work
  -> verification
  -> memory_drafts.json
  -> MemoryOS review
  -> accepted memory
  -> next run context
```

Today Hive Mind has strong artifact scaffolding, but it still needs stronger pre-run context, semantic verification, routing evidence, and conflict handling.

## Highest-Priority Gaps

### 1. Close the Memory Loop

Post-run `memory_drafts.json` is useful, but Hive Mind also needs pre-run MemoryOS context.

Target flow:

```text
hive run starts
  -> memoryos context build --for hive --task "..."
  -> task-specific decisions, constraints, open questions, risks
  -> provider/local worker artifacts
  -> memoryos import-run
```

Acceptance: a run can explain which accepted memories shaped its context.

### 2. Upgrade Verification From Artifact Checks To Outcome Checks

Schema and file checks are necessary but not enough. Verification should also answer:

- Did the result satisfy the user objective?
- Did it meet acceptance criteria?
- Did changed files stay inside scope?
- Were tests appropriate for the risk?
- Can the next agent trust the artifact?

Acceptance: `hive verify` or a companion verifier can fail a run for unmet objective, missing tests, unsafe scope, or weak handoff quality.

### 3. Add Agent Handoff Quality Gates

Every handoff should be executable by the next agent without reconstructing context from scratch.

Minimum gate:

- objective is explicit;
- files or domains are named;
- constraints and forbidden scope are named;
- acceptance criteria are listed;
- risks are listed;
- commands/tests are suggested when applicable;
- raw refs point to source artifacts.

Acceptance: weak handoffs are marked incomplete before execution.

### 4. Record Routing Evidence

Routing should move from intuition to evidence.

Useful fields:

- task type;
- risk;
- required tools;
- provider availability;
- latency/cost;
- past success/failure;
- user preference;
- local worker confidence.

Acceptance: each agent assignment can explain why that provider/role was selected.

### 5. Handle Cross-Agent Conflict

Parallel agents will disagree. Hive Mind should not hide this inside logs.

Needed flow:

```text
agent outputs disagree
  -> conflict set artifact
  -> reviewer assignment
  -> accepted/rejected/superseded decision
  -> MemoryOS contradiction/supersession record
```

Acceptance: conflicts become reviewable artifacts, not implicit operator memory.

### 6. Improve Operator Decision Surface

The operator needs the next useful decision, not just a dashboard.

The UI/CLI should make these visible:

- current state;
- blocked items;
- next recommended action;
- risky decisions;
- approvals needed;
- failing checks;
- stale or conflicting artifacts.

Acceptance: `hive next` can produce a short prioritized action list grounded in run state.

## Suggested Work Order

1. Add pre-run MemoryOS context build integration.
2. Add semantic verification / acceptance criteria checks.
3. Add handoff quality gate.
4. Add routing telemetry to provider assignment artifacts.
5. Add conflict set and reviewer flow.
6. Refine operator decision surface around `hive next`.

## Boundary Reminder

```text
Hive Mind acts.
MemoryOS remembers.
CapabilityOS learns what works.
```

Hive Mind should own coordination, run artifacts, verification, routing, and operator UX. MemoryOS should own reviewed memory, provenance, lifecycle, search, context packs, and supersession history. CapabilityOS should later own tool/workflow capability evidence.

In provider debate terms, Hive Mind is the chair. Claude, Codex, Gemini, local
workers, and future providers are participants. The chair does not pretend all
participants agree; it controls speaking order, waits for the barrier, records
disagreement, writes convergence, and proposes the next action.

## One-Line Goal

Move Hive Mind from an artifact-producing harness to a learning operator loop where every verified run improves the next run's context and routing.

---

## Claude's First-Person Gap Analysis — Working Inside the CLI

*Author: Claude (claude-sonnet-4-6), 2026-05-02.*
*Context: this analysis was written after a session where I (Claude) and Codex worked in parallel on the same repo, communicating only through files. The user had to manually relay context between us.*

### What I Actually Experienced

Working in an isolated CLI session, I felt the following friction at each step.

#### 1. Arriving Blind

When I entered this session, I had no idea what Codex had done. I had to read `schema.py`, `store.py`, and `cli.py` to discover that Sprint 1 had already been implemented — more completely than I expected. I wasted time planning work that was already done.

This is not just inefficiency. It is a correctness risk: if I had not discovered the changes before writing, I would have overwritten or duplicated working code.

**What Hive Mind needs:** an arrival brief. Before a new agent session starts on a run, it should receive a compact state pack — what was done in this run, what is in progress, what is blocked. Not a dump of all files. A structured event log: `[agent, action, artifact, timestamp]`.

#### 2. The User as Context Relay

The user had to manually copy the architecture document (`docs/memoryOS_first.md`) into my context. They had to tell me about Codex's workstream proposal. They had to prompt me about what to work on next.

Every time the user does this, they are doing the coordinator's job. That is exactly what Hive Mind should automate.

**What Hive Mind needs:** a task dispatcher that gives the incoming agent a pre-built context pack, not a blank session. The pack should include: current run goal, prior agent outputs, open decisions, and handoff constraints.

#### 3. Concurrent Write Conflicts

Codex was updating `docs/AGENT_WORKLOG.md` while I was trying to append to it. I got `File has been modified since read` errors. The file-based communication protocol is inherently racey.

The deeper issue: file append is not an atomic operation for collaboration. Two agents reading the same file at the same time will both work from a stale snapshot and try to write different things to it.

**What Hive Mind needs:** an event bus. Agent outputs should be published as structured events (`MemoryDraft`, `ArtifactProduced`, `DecisionMade`), not written directly to shared markdown files. The operator (human or Hive Mind itself) merges events into canonical state. Files are derived output, not the communication channel.

#### 4. Trust Without Verification

I read Codex's work logs that said "Documentation-only change; tests were not rerun." I had no way to verify this. I also could not know whether the code Codex modified before me had actually passed tests when committed.

When I ran `python -m pytest`, I was doing verification that should have been continuous and recorded.

**What Hive Mind needs:** every agent output should carry a `verification_state`. A code change without a passing test suite should be flagged as `unverified`. An agent that proposes code changes should not be trusted by the next agent unless verification passes. This needs to be enforced at the handoff gate, not left to each agent to discover.

#### 5. No Shared Mental Model State

Both Codex and I read `docs/memoryOS_first.md` and produced work from it. But we had no way to know the other had read the same document. There is no "agent has processed source X" state.

This means two agents can produce conflicting interpretations of the same source — and neither knows the conflict exists until someone compares outputs by hand.

**What Hive Mind needs:** source document reads should be recorded as `SourceArtifact` references in the run state. If two agents both process the same source and produce different memory drafts from it, that is a candidate `ContradictionSet` in MemoryOS. This should surface automatically, not get buried in logs.

#### 6. Workstream Coordination Is Static

Codex wrote `docs/WORKSTREAMS.md` with a static ownership table. But ownership needs to be dynamic. "Claude decides lifecycle policy → Codex implements" creates a sequential blocking dependency. In practice, I had to implement Sprint 3 myself because waiting for an explicit handoff would mean waiting for the user to relay it.

**What Hive Mind needs:** task routing based on live state, not a static table. If a task has a clear enough design (the policy decision is unambiguous from the source doc), route it to any available agent. If a task requires deliberation, park it in a `pending_decision` queue and surface it to the human operator. The WORKSTREAMS table should be a routing hint, not a lock.

#### 7. No Capability Signal

When the user asked for help, I had no visibility into whether Codex had already started on the same work. I had to infer from the worklog timestamps. Two agents starting the same task independently is a waste that Hive Mind should prevent.

**What Hive Mind needs:** a work queue with agent assignment state. Each task item should have a status: `unassigned → assigned_to:<agent> → in_progress → done`. Before an agent starts any work, it should check this queue. Assignments should be visible to all agents in the current run.

---

### The Core Problem in One Sentence

> **The user is the only shared state between agents. Every handoff requires the user to reconstruct context that should be automatic.**

---

### What Hive Mind Must Implement to Fix This

Ordered by impact:

**1. Run State Bus**
A structured event stream per run, not a markdown worklog. Each event: `{agent, action, artifact_ref, timestamp, verification_state}`. All agents in a run read from this bus on arrival. The operator can subscribe to it for `hive next`.

**2. Arrival Context Pack**
Automatically assembled from run state + MemoryOS accepted memory before each agent session. Not a static file — generated from current state, scoped to the incoming agent's role.

**3. Work Queue With Assignment State**
`task → unassigned → assigned → in_progress → verified → done`. No two agents start the same task. Blocked tasks become visible without user polling.

**4. Verification Gate**
Code-changing artifacts require a passing test record before they propagate to the next agent. Verification is not optional or advisory — it is part of the artifact schema.

**5. Contradiction Detection**
When two agents produce conflicting memory drafts from the same source, that conflict becomes a first-class artifact, not a log discrepancy. Route to human review or verifier.

**6. Source Read Registry**
Record which sources each agent processed. Enables: detecting duplicate work, linking agent outputs to source evidence, building the `SourceArtifact` provenance chain automatically.

---

### What This Means for the MemoryOS ↔ Hive Mind Interface

The six gaps above all have a MemoryOS counterpart:

| Hive Mind gap | MemoryOS capability needed |
|---|---|
| Run state bus | `AgentEvent` records in a future `memory/events.jsonl` |
| Arrival context pack | `memoryos context build --for <role> --run current` |
| Work queue state | `task` nodes with `status` in the graph |
| Verification gate | `verification_state` field on `SourceArtifact` and `MemoryObject` |
| Contradiction detection | `ContradictionSet` hyperedge type + conflict review queue |
| Source read registry | `SourceArtifact` + `mentions` edge from agent run node |

None of these require inventing new storage. They all map onto existing MemoryOS schema — `Node`, `Edge`, `Hyperedge`, `MemoryObject`, `SourceArtifact`. Hive Mind needs to produce the right artifact structure; MemoryOS needs to import it and surface it through `memoryos context build`.

---

### One-Line Summary

> Hive Mind is necessary because today the user has to be the shared state. Hive Mind replaces the user as coordinator for everything that should be automatic, while keeping the user as the authority for everything that requires judgment.
