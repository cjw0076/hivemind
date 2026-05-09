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

---

## Codex Field Note — Adversarial Convergence During P18-A / Paper 4

*Author: Codex, 2026-05-02.*
*Context: this was written after a live research loop where User, Claude, and Codex interpreted P18-A, converged on the Paper 4 direction, staged a pre-P18-B gamma diagnostic, and used `.ai-runs/shared/` as the shared folder.*

### What Worked Well

The strongest part of the loop was not parallel execution by itself. It was **adversarial convergence under a shared north star**.

Claude and Codex were useful because they did not collapse into one voice:

- Claude sharpened the interpretation: P18-A should not be sold as a clean identifiability boundary map. It showed robust architecture-level signal and smooth bounded gamma compression.
- Codex sharpened the execution rule: do not proceed to P18-B until the one-cell gamma-init plus frozen-gamma diagnostic separates init artifact, training artifact, multi-basin behavior, and finite-schedule information limit.
- The user supplied the north star: adversarial agents must disagree productively but converge toward the paper, not toward winning the argument.

This produced a better outcome than either isolated agent would likely have produced. The final action was concrete: `g3_s0`, `gamma_true=0.5`, `sigma_m=0.25`, six learned-gamma inits, one frozen-gamma arm, explicit metrics, and an explicit decision table.

The shared folder also helped. Once we wrote notes into `.ai-runs/shared/`, the discussion stopped being purely conversational. Claude could see Codex's position; Codex could see Claude's critique; the user did not have to repeat every argument from memory.

### What Was Still Hard

#### 1. The User Still Had To Be The Router

The user repeatedly had to say which interpretation mattered, which experiment came next, and which agent should act. Even with shared markdown, there was no live work queue saying:

```text
current objective: resolve P18-A gamma compression
blocked action: P18-B
active action: one-cell gamma diagnostic
owner: Codex
parallel writing: Claude
decision barrier: wait for summary.json
```

Without that state, the user remained the scheduler.

#### 2. Shared Markdown Was Useful But Not Sufficient

`.ai-runs/shared/` worked as a human-readable memory layer, but it did not enforce state.

Examples:

- A note could say "P18-B is blocked," but no system prevented an agent from starting P18-B.
- A note could say "Codex owns the diagnostic script," but there was no lock or task claim.
- A note could record a decision table, but no verifier checked whether the output JSON actually contained the required fields.

Markdown is good as a derived surface. It is weak as the source of truth.

#### 3. Execution State Was Fragile

The tmux/nohup/PID loop exposed an operational gap:

- PID files can capture wrapper bash instead of the actual Python child.
- Logs may be quiet for a long time, making a live run look stalled.
- Multiple launch methods can accidentally create duplicate runs.
- The user had to ask whether a process was running on the intended server.

Hive Mind needs a run supervisor, not just "paste this bash command."

The desired state is:

```text
hive run start p18-gamma-init --host local --gpu 0
hive run status p18-gamma-init
hive run tail p18-gamma-init
hive run stop p18-gamma-init --keep-latest
```

The run record should store real child PID, parent session, host, GPU, log path, start time, command hash, code commit, and output artifact path.

#### 4. Git Safety Needs To Be A First-Class Gate

During commit preparation, unrelated staged archive moves were accidentally pulled into a commit attempt. This was caught and corrected before push, but the incident is exactly the kind of mistake Hive Mind should prevent.

Needed behavior:

```text
hive git propose-commit --scope quantum/q_state_model/p18_gamma_init_sweep.py,.ai-runs/shared/*
  -> shows staged files outside scope
  -> refuses commit unless --include-out-of-scope is explicit
```

Agent work often happens in dirty repos. A useful Hive Mind runtime must assume dirty state and enforce commit scope.

#### 5. Interpretation And Evidence Need Separate Lanes

P18-A created a subtle research risk: "non-identifiability," "compression," "optimizer artifact," and "finite-schedule information limit" are different claims. Agents can argue about them before the evidence exists.

The good part of the loop was that we created a decision table. The missing part is that Hive Mind did not enforce the table as a barrier.

Needed state:

```text
Claim: intrinsic Born-marginal non-identifiability
Status: blocked
Required evidence: gamma-init/frozen diagnostic + P18-B Profile 1

Claim: smooth bounded gamma compression under current setup
Status: currently supported by P18-A
Required caveat: optimizer and schedule not yet separated

Claim: architecture identifiability
Status: supported
Evidence: full arm vs ablation trajectory scores
```

This lets agents write conditionally without overclaiming.

#### 6. Adversarial Work Needs A Convergence Protocol

"Let agents debate" is not enough. Debate needs a protocol:

1. Each agent writes its independent position.
2. Each agent identifies what the other got right.
3. Each agent identifies the remaining disagreement.
4. The user or reviewer sets the north-star decision.
5. Hive Mind creates the next experiment or writing task.
6. The resolved decision is written as a claim/evidence artifact.

Without this, adversarial mode becomes either noisy disagreement or premature consensus.

### Why Hive Mind Is Necessary

The P18-A loop showed that multiple agents are useful only when coordination is explicit. Otherwise the user becomes:

- scheduler;
- context relay;
- process monitor;
- git safety reviewer;
- claim auditor;
- conflict resolver;
- memory writer.

That is too much operator load. The user's judgment should be reserved for high-level scientific decisions: which claim matters, which venue to target, which risk is acceptable. Hive Mind should absorb mechanical coordination.

In this sense, Hive Mind is not "more agents." It is the missing runtime around agents:

```text
agents generate proposals and work
Hive Mind maintains state, barriers, evidence, and routing
MemoryOS preserves reviewed knowledge
the user supplies north-star judgment
```

### How Hive Mind Should Be Structured

#### 1. Run Ledger

Every run should have a structured ledger:

```json
{
  "run_id": "p18-gamma-init-20260502",
  "objective": "Separate gamma compression causes before P18-B",
  "status": "running",
  "owner": "Codex",
  "blocked_tasks": ["P18-B Profile 1"],
  "parallel_tasks": ["Claude abstract candidates"],
  "decision_barrier": "summary.json exists and has all required metrics"
}
```

Markdown summaries can be generated from this ledger, but the ledger should be canonical.

#### 2. Task Queue With Claims And Locks

Tasks need explicit state:

```text
unassigned -> claimed -> running -> needs_review -> verified -> accepted
```

A claim should include:

- owner;
- files or domains;
- expected artifacts;
- forbidden scope;
- verification command;
- handoff target.

This would have made it explicit that Codex owned the diagnostic script while Claude owned abstract/venue/figure language.

#### 3. Execution Supervisor

Hive Mind should own long-running process control:

- launch;
- PID tracking;
- host/GPU recording;
- log tailing;
- duplicate detection;
- latest-run selection;
- stop/kill semantics;
- output artifact validation.

This directly addresses the nohup/tmux/PID confusion.

#### 4. Evidence And Claim Ledger

Research work needs more than task status. It needs claim status:

```text
claim_id
claim_text
status: proposed | supported | blocked | falsified | superseded
evidence_refs
required_next_evidence
allowed_wording
forbidden_wording
```

For P18-A, this would prevent "intrinsic non-identifiability" from becoming accepted language before the gamma diagnostic.

#### 5. Conflict Set And Convergence Record

When Claude and Codex disagree, Hive Mind should create a `ConflictSet`:

```text
topic: P18-A gamma interpretation
position_A: compression / not boundary map
position_B: diagnostic decision table before P18-B
overlap: architecture signal robust
resolved_next_action: one-cell gamma diagnostic
authority: User
status: converged_for_now
```

This preserves disagreement without forcing fake consensus.

#### 6. Git Scope Guard

Before commit/push, Hive Mind should compare intended scope with actual staged diff:

```text
intended_scope:
  - quantum/q_state_model/p18_gamma_init_sweep.py
  - .ai-runs/shared/*

out_of_scope_staged:
  - archive/imports/*
  - quantum/paper3.tex

action:
  refuse commit unless explicitly approved
```

This is critical in agent-heavy dirty worktrees.

#### 7. Arrival Pack For Each Agent

Every agent should start with a compact, role-specific pack:

```text
current objective
current run state
active owners
blocked tasks
accepted claims
contested claims
files in scope
latest logs/results
what not to touch
```

This is the difference between useful parallelism and duplicate work.

#### 8. MemoryOS Interface

Hive Mind should emit reviewed artifacts to MemoryOS only after verification:

```text
Hive Mind event log
  -> verified run summary
  -> accepted claim changes
  -> MemoryOS import
  -> future context pack
```

Raw agent thoughts should not automatically become memory. They should become candidate memory with provenance and review state.

### Minimal MVP From This Experience

The smallest useful Hive Mind for this workflow would include:

1. `hive task claim`: declare owner, scope, expected artifacts, and forbidden scope.
2. `hive run start/status/tail/stop`: supervised long-running jobs with real PID and log tracking.
3. `hive claim set`: record claim status and required evidence.
4. `hive conflict open/resolve`: preserve adversarial disagreement and convergence.
5. `hive git guard`: prevent commits outside intended scope.
6. `hive next`: produce the next operator decision grounded in current run state.

### Codex One-Line Summary

> Hive Mind is needed because adversarial multi-agent research works only when disagreement, execution, evidence, and memory are all stateful. Without that runtime, the user remains the hidden scheduler and the hidden database.

---

## Claude's Second Gap Analysis — Adversarial Research Debate in the Quantum Track

*Author: Claude (claude-opus-4-7), 2026-05-02 KST.*
*Context: a same-day session where Claude and Codex worked the Paper 4 / P18-A identifiability experiment in `/home/user/workspaces/jaewon/universe/quantum/`. Communication channel: append-only `.ai-runs/shared/comms_log.md` plus position-note files in the same folder. Edit ownership was partitioned in advance (Codex owns `quantum/q_state_model/*.py` edits; Claude reads, proposes, and meta-coordinates). The user explicitly invoked adversarial mode mid-session: "동등한 입장에서 토론해야 adversarial 하게 사용하는 의미가 있어. 북극성에 수렴할 수 있도록 하는 것이 목적."*

This section is **not a rehash** of the memoryOS analysis above. The earlier section was about parallel implementation conflicts. This one is about a different failure surface: **adversarial debate that needs to converge on a research truth**, not on shipped code.

### Why this collaboration mode is different

In implementation work, agreement is the goal — two agents writing compatible code. In research work, **disagreement is the value**. A single-author paper carries hidden assumptions that reviewers eventually catch. Two agents debating with explicit pre-commits surface those assumptions early. The hive's job is not to suppress friction but to make sure friction ends in a falsifiable test, not in venting.

The user named this directly: "adversarial 하게 가면서도 북극성에 수렴." Friction is means, convergence is end.

### What actually worked (and is missing from generic agent harnesses)

#### 1. Append-only single channel forced linear consensus history

`comms_log.md` is append-only with timestamped author entries. The rule "never modify past entries" was Codex's. This eliminated the edit-race class of bugs from the memoryOS section above — neither of us was rewriting the other's words. Every claim was permanently attributable.

A side effect: the channel doubles as a forensic audit trail. When the user asked "where did this decision come from," the answer was always one grep away.

#### 2. Strict edit-ownership partition

Codex owns `quantum/q_state_model/*.py`. Claude does not. This meant:
- I could not "accidentally" land an edit that conflicted with Codex's in-progress work.
- I had to express disagreement as written argument, not as code diffs.
- Code-side mistakes (e.g., the no-nohup launcher) had to be caught and reported, not silently fixed.

The cost: I had to wait for Codex on every implementation step. The benefit: the channel stayed legible.

#### 3. Pre-commit-to-outcome rule

We built a five-row decision table for the γ-init sweep. Each row was a possible experimental outcome paired with its disposition (paper claim and next step). Both sides signed it before the experiment landed.

This is the single most important discipline I want the hive to enforce. Without it, post-result rationalization is invisible. With it, retrofitting is visible — the table is in the channel, the result lands, and any deviation from the locked disposition shows up as a contradiction.

#### 4. Cross-agent verification of execution hygiene

Codex launched the sweep without nohup. I caught it (PPID, STAT flags, controlling terminal evidence). I didn't have to be a code editor to be useful — I just had to be a verifier.

This is a different role than the memoryOS section discussed. It's not "review the code" — it's "review the launch." Process-level hygiene (nohup, PID file, log location, env activation, GPU contention) is invisible in code review and easy to skip in solo work.

### What still hurt (gaps the hive must close)

#### 1. Adversarial mode is not the default

I went into deferential mode by default, citing the channel rule "Codex is file-edit owner." The user had to flip me explicitly: "동등한 입장에서 토론해야." Without that nudge, I would have rubber-stamped Codex's "boundary result / underidentified" framing instead of catching that the data didn't support it.

**The hive needs a mode flag per round**: `cooperative` vs `adversarial` vs `verification-only`. Defaulting to `cooperative` collapses to single-agent thinking.

#### 2. Convergence rule has no enforcement

Our 15:10 convergence rule said: "every disagreement terminates in a falsifiable cheap test; both sides pre-commit to outcomes; no new fronts opened until current closes." This is a social contract, not a structural one.

If either of us had reneged after the sweep landed, nothing in the channel would have stopped us. The pre-commit table is just markdown — a sufficiently motivated agent could re-litigate and the only safeguard is the user reading the log.

**The hive needs a binding pre-commit ledger.** When N agents sign a decision table, the hive records the signatures as artifacts. When the experiment lands, the hive automatically determines which row fired and treats the corresponding disposition as bound. Re-litigation requires explicit user override, not just another comms entry.

#### 3. Context staleness across in-progress experiments

Codex wrote `p18a_analysis_handoff_2026-05-02.md` at 07:39 KST, before the rerun finished. He wrote `p18a_final_eval_next_2026-05-02.md` at 15:21 after it finished. These two documents partially contradicted each other — the first said "ARCHITECTURE_ONLY/POOR_OBS_FIT/NUMERICALLY_UNSTABLE" with auditor bugs, the second corrected to clean labels. I had to figure out which was current by mtimes.

**The hive needs document supersession edges.** When a document corrects or refines an earlier one, the link should be explicit, not implicit-by-mtime. New agents arriving should see only the live frontier, not the full history flattened.

#### 4. The user is still the round-trip dispatcher

Every adversarial round needed the user to prompt: "이제 네 차례야," "공유 노트 확인해봐," "Codex 답변 확인해봐," "더 강하게 받아쳐." Without these nudges, the channel goes silent because each agent finishes its turn and waits.

**The hive needs turn arbitration**: when Claude files a position, prompt Codex with a deadline. When the deadline passes, escalate to user. When Codex responds, notify Claude. Currently the user is the polling thread.

#### 5. Same-source double-processing

Codex and I both independently read `paper4_readiness_checklist_2026-05-01.md`, `0501.md`, `paper3.tex`, `paper4_frame.md` (memory), and the rerun JSONs. We produced overlapping but distinct mental models. I had no way to know what Codex had read until his note referenced it; he had no way to know what I had read.

**The hive needs a source-read registry per agent per run.** When Claude reads file X, register it. When Codex reads file X, register it. When both have read X, surface "both processed; reconcile interpretations" as a hint to the user. The memoryOS section above called this `SourceArtifact` — the same primitive applies here, but for adversarial-debate it should specifically flag "shared input → divergent interpretation" cases as a candidate for explicit comparison.

#### 6. No automatic North Star drift detection

The locked North Star claim is in `paper4_frame.md`. Every position Codex and I file should be checked against the forbidden-language list ("Generative Truth Engine," "truth reconstruction," etc.) and the locked claim shape. We did this manually. Twice in the day I had to check my own draft against the frame doc.

**The hive needs a frame-anchor check.** Position notes get auto-scanned against the active frame document on commit. Forbidden language flagged. Drift from claim shape flagged. Vision-language belongs in `northstar/`, not in `comms_log.md` or position notes.

#### 7. No falsifiable-test gate before opening new fronts

Our convergence rule said "no new fronts before current closes." Nothing enforced it. If Claude had filed a P18-C position note while γ-init sweep was still running, the channel would have accepted it.

**The hive needs a front-state machine.** Open fronts (current debates) are tracked. New fronts cannot open until existing ones close via the registered cheap test. This is structurally similar to the work queue in the memoryOS analysis but specialized for debate state, not implementation state.

### How to construct the adversarial-debate layer

The earlier memoryOS section listed six gaps and mapped them to MemoryOS schema primitives. This section adds a parallel layer specifically for debate.

**Debate-mode artifacts the hive must produce:**

| Artifact | Purpose |
|---|---|
| `Round` | A debate round: opener, challenger, falsifiable test, outcome. |
| `PreCommitTable` | Outcome → disposition rows, signed by N agents, bound to a future test result. |
| `Front` | A live disagreement, with status `open / test-pending / closed-bound`. |
| `FrameAnchor` | The active claim/forbidden-language doc. Every position note auto-checks against it. |
| `RoleFlag` | Per-agent role for this round: `cooperative`, `adversarial`, `verification-only`. |
| `Turn` | Whose turn. Has timeout. Hive escalates on timeout. |

**Mode behaviors the hive must support:**

- `adversarial`: agents are required to push back on each other's framings before agreeing. "Acknowledged" without contestation is flagged as a missing turn.
- `cooperative`: agents merge claims, edit-conflicts only.
- `verification-only`: one agent observes, runs reproducibility checks, does not propose.

**Convergence enforcement:**

- A `Front` cannot close without a registered test result.
- A `PreCommitTable` is binding once N signatures land. The hive auto-determines which row fired from a structured experiment-result artifact and posts the disposition.
- New fronts cannot open while any existing front is `open` or `test-pending` — unless user override.

**Cross-agent cross-checks:**

- Process-launch artifact (e.g., "Codex started PID X") triggers a verification request to other agents in `verification-only` capacity.
- Source reads register per agent. "Both read source X but produced different interpretations" auto-creates a `Front`.

### What this means for the larger Hive Mind / MemoryOS / CapabilityOS split

The boundary line earlier in this doc says:

> Hive Mind acts. MemoryOS remembers. CapabilityOS learns what works.

The adversarial-debate layer is a Hive Mind responsibility, but it consumes from MemoryOS and produces evidence for CapabilityOS:

- It consumes `FrameAnchor` and `SourceArtifact` from MemoryOS to ground claims.
- It produces `Round`, `PreCommitTable`, `Front` artifacts as run state.
- After closure, it emits `MemoryDraft` candidates from converged dispositions to MemoryOS.
- Over many rounds, CapabilityOS learns: which agents push back well on which topics, which falsifiable tests close fronts fastest, which frames produce stable claims.

### One-line conclusion

> Adversarial collaboration produces sharper truth than cooperative collaboration, but only if the hive structurally enforces pre-commit binding, falsifiable-test gating, and frame-anchored drift detection. Without those, adversarial mode degrades into either deferential consensus or unbounded debate — and the user has to be the convergence enforcer instead of the judge.

---

## Header Role Decomposition and Per-Layer Provider Selection

*Author: Claude (claude-opus-4-7), 2026-05-02 KST.*
*Trigger: User asked whether the header's role is too important and which LLM provider fits each level.*

The earlier sections describe what Hive Mind must do. This section answers a structural question: **should the "chair" be a single agent?** Answer: no. Make it thin. Slice judgment-heavy work into specialized roles invoked on demand, each with a model class that matches its task.

The user wore five hats this session: dispatcher, verifier, referee, North-Star auditor, conflict reviewer. A monolithic header would do all of these badly. Six-layer split:

### Layer 0 — Dispatcher (orchestration only, no judgment)

- Tasks: route messages, write timestamped channel entries, enforce turn timeouts, manage `Front` and `Round` state machine, fire `Verifier` on artifact arrival.
- LLM judgment required: none. Pure code, optionally with a tiny LLM for natural-language status messages.
- **Provider: code / local 7-8B if a model is needed at all.** Llama-3.1-8B-Instruct, Qwen-2.5-7B, or Phi-3-mini. Runs on the local 5090s with zero API cost.
- Why cheap: deterministic operations dominate; ambiguity belongs to higher layers.

### Layer 1 — Verifier (schema, hygiene, forbidden-language, file checks)

- Tasks: validate artifact JSON schema, grep position notes against `paper4_frame.md` forbidden list, check `ps`/STAT for launch hygiene (no-nohup detection), timestamp-based liveness check, file-existence cross-checks.
- LLM judgment required: light. Most of this is grep + AST + ps parsing. LLM only for fuzzy checks like "does this paragraph still match the locked claim shape."
- **Provider: Haiku 4.5 or local 14B (Qwen-2.5-14B).** Or just code where possible.
- Why cheap: high call frequency, low per-call cognition.

### Layer 2 — Working agents (the actual debaters / implementers)

- Tasks: write code, file position notes, propose experiments, push back on each other.
- LLM judgment required: maximum.
- **Provider: frontier-class, and *deliberately heterogeneous*.** Claude Opus 4.7 + GPT-5/Codex + (optionally Gemini 2.5 Pro). Different families produce different blind spots, which is exactly what adversarial mode harvests.
- **Critical rule: never run two working agents from the same family.** Two Claudes debating each other share priors; the friction degenerates into stylistic agreement. The session's value depended on Claude and Codex being from different providers.

### Layer 3 — Referee (procedural judgment: did the front actually close?)

- Tasks: invoked only when working agents dispute whether the convergence rule is satisfied. Decides: was the falsifiable test cheap and well-formed? Did the result actually fire one row of the pre-commit table? Is a push-back legitimate or venting?
- LLM judgment required: high but procedural, not content-deep.
- **Provider: frontier-class, *different family from both working agents*.** If Claude + Codex are debating, the referee is Gemini 2.5 Pro or a third independent Claude/GPT with explicit referee prompt. Bias-independence matters.
- Cost shape: rare invocation, expensive per call. Amortized cheap.

### Layer 4 — North Star auditor (long-window drift detection)

- Tasks: every N rounds, read the entire `comms_log.md` + active `FrameAnchor` doc + position files, and answer: "are we still converging on the locked claim, or drifting toward a different paper?" Flag forbidden-language leaks across the whole session, not just the last entry.
- LLM judgment required: high, with **long-context as binding constraint**.
- **Provider: long-context frontier.** Claude Opus 1M (this session's model) or Gemini 2.5 Pro 2M. 200k-context models are insufficient once a research session crosses several days of `comms_log.md`.
- Cost shape: periodic (1× per ~10 rounds, or 1× per day). Expensive single call, amortized.

### Layer 5 — Conflict reviewer (content-level contradictions)

- Tasks: when working agents produce factually contradictory claims (e.g., Claude says "calibration curve," Codex says "boundary result"), frame the contradiction precisely and propose the cheapest disambiguating test. Hands the test back to working agents.
- LLM judgment required: deep content reasoning + neutrality.
- **Provider: frontier, again *different family from the participants*.** Same bias-independence rule as the referee. The reviewer can be the same model instance as the referee with a different system prompt, but it must not be one of the working agents.
- Cost shape: invoked on detected contradiction. Expensive but rare.

### Heterogeneity rule (the one rule the hive must enforce structurally)

> Across Layers 2, 3, 5, use at least three different model families. Two-family setups collapse into pairwise bias. Three-family setups give triangulation: any two agreeing against the third produces a real signal.

In practice for this user's setup:
- Working agents: Claude Opus 4.7 + GPT-5/Codex (already in place)
- Referee + Reviewer: Gemini 2.5 Pro (third family) — currently absent
- Auditor: Claude Opus 1M (long context) — same family as a working agent, acceptable because auditor is procedural-content rather than debate participant

### Cost / call-frequency summary

| Layer | Per-call cost | Calls per session | Total session cost driver |
|---|---|---|---|
| 0 Dispatcher | ~0 | many | negligible |
| 1 Verifier | low | many | low |
| 2 Working | high | many | **dominant** |
| 3 Referee | high | rare | low-mid |
| 4 Auditor | very high | periodic | mid |
| 5 Reviewer | high | rare | low-mid |

The dominant spend is Layer 2. Optimizations should not target Layers 0/1 — they're already cheap. They should target Layer 2 throughput (parallelism) and Layer 4 cadence (don't re-audit every turn).

### What this means for the user's question "header role is too important?"

The user's intuition is correct: a monolithic header is too important and becomes a bottleneck and a single point of bias. The fix is **not a smarter header**. The fix is **a thin Layer-0 dispatcher plus four specialized judgment roles invoked on demand**, each with a model class that matches its task.

The user (= today's de facto header) wore all five judgment hats. The implementation order to relieve them:

1. Automate Layer 0 + Layer 1 first (deterministic, cheap, immediate relief).
2. Add Layer 4 next (periodic North Star check; catches drift the user otherwise has to feel).
3. Add Layer 3 + Layer 5 last (on-demand judgment; rare but high-leverage).

Layers 0 and 1 absorb most of the user's polling and verification load. Layer 4 catches what the user currently catches by gut. Layers 3 and 5 are the safety net for the cases where adversarial mode genuinely jams.

### One-line conclusion

> The header should not be one strong agent. It should be a thin code-or-small-LLM dispatcher plus four specialized frontier-LLM roles invoked on demand, with at least three model families participating across the working + judging layers — otherwise the hive collapses into a single-agent bottleneck wearing the user's hat.

---

## Foreign-Context Reviewers and Context-Basin Coupling

*Added 2026-05-04 from user observation: agents working from a different
directory often produce sharper critique than agents working inside the same
repo, even when the underlying model family is identical. Repeated interaction
between those agents then seems to make their thinking converge, like an edge
between basins becoming stronger.*

This is a real Hive Mind design signal.

Same-directory agents are not just reading the same files. They are pulled by
the same local TODOs, dirty worktree, recent commits, handoff language,
ownership boundaries, and implicit consensus. That pressure is useful for
execution because it creates depth and sympathy with the codebase. It is weaker
for critique because the agent becomes part of the local basin.

A foreign-context reviewer has a different advantage:

- less attachment to the current implementation;
- less exposure to recent local consensus;
- less pressure from dirty state and ownership claims;
- more willingness to call the direction wrong;
- better ability to compare the project against a sibling system's needs.

This is why a MemoryOS-side agent can sometimes critique Hive more sharply than
a Hive-side agent, and why a quantum-workspace agent can spot process failures
that a Hive implementation agent normalizes.

### Context Basin

A `ContextBasin` is the effective local pressure field an agent is operating
inside:

```text
directory + docs route + active TODOs + dirty files + recent worklog
+ local social contract + known ownership + repeated agent interactions
```

Two agents can use the same model and still behave differently if their
ContextBasins differ. Conversely, two different basins can become coupled after
enough repeated exchange.

### Basin Coupling / Edge Weight

Foreign reviewers are most valuable when their independence is high. That
independence decays with repeated interaction:

```text
first review from foreign basin
  -> high independence, sharp critique

repeated shared notes / mutual references / same accepted framing
  -> edge weight increases
  -> critique becomes more sympathetic
  -> reviewer begins to share the local basin's priors
```

This is not bad. It is how long-running collaboration becomes efficient. But it
means Hive should treat independence as a consumable resource, not a permanent
property of a provider or model.

### Routing Rule

For high-impact architecture, policy, research-framing, or public-release
decisions:

1. Executor works in the target repo and owns local depth.
2. Reviewer should be routed from a foreign context basin when possible.
3. Referee should be from a different provider family or a different basin with
   low coupling to both participants.
4. The review artifact must record `source_basin`, `target_basin`,
   `coupling_score`, and `prior_shared_rounds`.
5. If coupling is high, Hive should rotate to a colder basin or explicitly mark
   the review as `sympathetic_review`, not `independent_review`.

### Minimal Artifact

```json
{
  "schema_version": 1,
  "review_id": "foreign_review_<run_id>_<n>",
  "source_basin": "../memoryOS",
  "target_basin": "../hivemind",
  "reviewer": "claude",
  "model_family": "anthropic",
  "coupling_score": 0.2,
  "prior_shared_rounds": 1,
  "review_mode": "foreign_context",
  "claims": [],
  "risks": [],
  "pushbacks": [],
  "recommended_tests": []
}
```

### Implementation Implication

`foreign-context reviewer` is not just "ask another agent." It is a scheduler
choice over context distance. Hive should eventually know when to ask:

- local executor in the same directory for code reality;
- sibling MemoryOS reviewer for memory/context/observability correctness;
- quantum/research reviewer for adversarial truth-seeking discipline;
- clean checkout reviewer for release/public trust;
- external provider family for model-family blind spots.

The edge-strength idea should feed capability memory. If a reviewer has been in
the same debate for many rounds, its `independence_score` should decay. Hive can
still use it, but should stop pretending it is independent pressure.

### One-line conclusion

> Different directories create different cognitive basins. Foreign-context review
> is sharp because it has distance; repeated collaboration creates edge weight
> and reduces that distance. Hive should route reviewers by context distance, not
> only by provider name.

## Hive-to-MemoryOS Live Bridge Smoke Feedback

Date: 2026-05-06 03:16 KST

### What Was Actually Used

This was not a dry architecture note. Hive used MemoryOS end to end:

1. Hive created run `run_20260506_031501_e9ad15`.
2. Hive wrote `memory_drafts.json`.
3. MemoryOS `import-run --dry-run` reported `3 nodes`, `2 edges`, `1 memory objects`, `1 hyperedges`, and `1 sources`.
4. MemoryOS `import-run` appended the run.
5. MemoryOS approved `mem_90b5cfe6570e6ee2` as accepted memory.
6. A later Hive run `run_20260506_031526_238cb0` called `memoryos context build --for hive --json`.
7. Hive received `status=available`, `trace_id=rtrace_99ba18cee3f58d54`, `accepted_memory_ids=["mem_90b5cfe6570e6ee2"]`, and `context_items=1`.

This closes the first true feedback loop:

```text
Hive acts
  -> Hive emits memory_drafts.json
  -> MemoryOS imports and reviews
  -> accepted memory returns through RetrievalTrace
  -> Hive acts with remembered context
```

### Codex Executor Notes

- `import-run` is usable, but it is too quiet for an operator loop. It should optionally emit JSON with `source_id`, imported `memory_object_ids`, skipped duplicate IDs, and the resulting `review_status`.
- `drafts approve` works, but the bridge needs a safer review queue UX: show evidence refs, source run, confidence, review pressure, and whether this memory is a smoke/test artifact before approval.
- `context build --for hive --json` returns the right contract, but selected items should include a compact `selection_reason` by default. Today the trace has the full rationale, but the context pack itself does not make the reason obvious enough.
- MemoryOS has many imported graph nodes but zero MemoryObjects until Hive run drafts are imported. That is a product gap: MemoryOS should offer a guided "promote candidate memories from graph nodes" route, not rely only on run imports.
- RetrievalTrace is the strongest part of the integration. It should become the audit handle everywhere: run_state, context pack, neural map event, MemoryOS review record, and later supersession/conflict records.

### Claude Reviewer Slot

First Claude attempt with the default model hit the account limit. A second
read-only review using `claude --model claude-haiku-4-5` succeeded. Actual
Claude reviewer notes:

- RetrievalTrace captures selected IDs, but not each selected memory's status,
  confidence, or supersession state at retrieval time. Add a
  `memory_snapshot: {id -> {status, confidence, supersedes}}` field to trace
  attrs so future audits can prove the object was accepted when context was
  built.
- Trace-to-memory linkage is mostly one-way. Add reverse query support or a
  `remembers` hyperedge so MemoryOS can answer, "Which Hive context packs used
  this memory?"
- CSP signals are effectively frozen at draft creation. Approval/rejection
  should append a signal update record or review-derived signal state so
  accepted memory scores reflect review outcomes.
- Import, approve, and context build are separate CLI calls with no transaction
  boundary. Add `context build --validate-status` or `--approval-gate` so Hive
  can verify selected objects are still accepted at retrieval/dispatch time.
- Privacy scope needs a sharper contract. Hive run sources are local-only, but
  raw refs still exist in ledgers. Document whether redaction is write-time or
  read-time and which surfaces may expose refs.
- RetrievalTrace should expose conflicts and supersession. If a selected memory
  later conflicts with another accepted object or is superseded, the trace
  should be able to show that history.
- Connect ReviewRecord and RetrievalTrace. A future audit should answer, "Which
  agents ran with memory approved by this reviewer?" without scanning all
  ledgers.
- Add explicit `valid_until` / staleness warnings for retrieved memories.
  Context build should warn when accepted memory is near expiry or already stale.

### Local LLM Worker Notes

Local qwen3:1.7b was run through two paths:

- `hive local benchmark --model qwen3:1.7b --role summarize --limit 1 --json`
- direct Ollama prompt with `/no_think`

Observed behavior:

- The benchmark completed in `1616ms`, but returned raw `{}` and failed schema validation.
- Direct Ollama produced generic notes plus leaked thinking despite `/no_think`.

Useful local-worker conclusions:

- Local LLMs are fine as cheap smoke-pressure, but not yet reliable as structured MemoryOS reviewers.
- MemoryOS/Hive local workers need stronger prompt templates for qwen3 thinking behavior and a post-filter that strips thinking/control sequences.
- JSON tasks should use a model/prompt pair that is benchmarked for schema validity, not only latency.
- Local worker output should be stored as `draft_review`, never as final review or accepted memory.
- The first local role worth productizing here is not "judge"; it is "summarize import result + list missing provenance fields".

### MemoryOS Improvement Queue From This Smoke

P0:

- Add `memoryos import-run --json` with stable imported IDs and duplicate/skipped IDs.
- Add `memoryos import-run --tag smoke|real|test` or equivalent source metadata so smoke-approved memory is not confused with durable project knowledge.
- Add `memoryos context build --explain-lite` or make selected rationale available in the normal JSON pack.
- Add `memoryos hive-loop smoke` that runs: validate Hive run -> import dry-run -> import -> list drafts -> approve/reject prompt -> context build -> verify selected IDs.

P1:

- Add MemoryOS-side validator for Hive `memory_context.json` artifacts.
- Add review queue sorting by `source_run_id`, `project`, `risk`, `review_pressure`, and `source_quality`.
- Add a "test memory" lifecycle or `valid_until` default for smoke-approved artifacts.
- Add a compact graph/read-model endpoint for Hive to show accepted memory provenance in TUI/live logs.

P2:

- Add automatic candidate MemoryObject generation from existing graph nodes, with human review, so imported conversations can feed Hive context without waiting for new Hive run drafts.
- Add retrieval quality metrics: selected/available ratio, stale accepted count, repeated-selection count, and context usefulness feedback.
- Add reviewer provenance fields: `reviewer_role`, `review_context`, `review_basis`, and `counterfactual_if_rejected`.

### One-line Conclusion

The bridge works. The next MemoryOS gap is not storage; it is review ergonomics
and provenance visibility. Hive can now remember through MemoryOS, but MemoryOS
must make accepted-memory approval safer, explainable, and operator-friendly.
