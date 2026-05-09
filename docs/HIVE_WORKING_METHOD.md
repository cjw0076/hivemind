# Hive Working Method

Hive Mind should turn the way this project is being built into product behavior.

The native loop is:

```text
user direction
  -> Claude-style critique and claim discipline
  -> Codex implementation and reproducible verification
  -> local LLM draft/classify/compress/summarize work
  -> Hive Mind artifacts, policy gates, disagreements, next actions
  -> MemoryOS review/acceptance later
```

This is not just a collaboration habit. It is the first reusable Hive Mind
skill protocol.

## Phase Loop

Hive Mind's phase loop should stay distinct from MemoryOS while sharing the
same north star. Hive acts; MemoryOS remembers; CapabilityOS recommends.

```text
0. Prompt Intake
   user intent enters through `hive`, chat, TUI, or future AIOS prompt/log UI

1. Context Retrieval
   Hive asks MemoryOS for accepted context, not drafts or raw private exports

2. Routing / Planning
   Hive creates a plan DAG, role assignments, ownership claims, and risk gates

3. Provider / Local Execution
   Hive uses role adapters (`hive invoke`) or native passthrough (`hive provider`)
   while preserving provider CLI capabilities

4. Ledger / Proof
   every action writes intent, policy, decision, lease/proof, stdout/stderr,
   result artifacts, and replayable ledger records

5. Verification / Referee
   verifier checks output shape and tests; disagreement escalates to reviewer,
   foreign-context reviewer, or referee instead of being silently resolved

6. Memory Draft
   Hive emits decisions, open questions, constraints, actions, conflicts, and
   artifacts as `memory_drafts.json`

7. MemoryOS Review
   MemoryOS imports drafts, preserves raw refs, and accepts/rejects/stales memory
   through review records

8. Context Feedback
   accepted memory becomes future context; RetrievalTrace explains why it was
   selected
```

The loop is complete only when a future run can use reviewed memory from a past
run without the user acting as hidden scheduler or hidden database.

### Production Runtime Boundary

Hive Mind should close its first production target as a runtime harness, not as
the whole AIOS. The production v0 claim is:

```text
A local, auditable provider-CLI runtime harness that can run bounded agent work,
preserve native CLI capabilities, record receipts/proofs, stop safely, and
degrade cleanly without MemoryOS.
```

MemoryOS and CapabilityOS are aligned substrates, not blockers for this runtime
close:

- MemoryOS improves long-horizon context, accepted-memory review, RetrievalTrace,
  and neural-map observability.
- CapabilityOS later improves model/tool/workflow selection.
- Hive v0 must still work when both are absent.

Do not claim full self-improving AIOS, complete memory-integrated swarm,
autonomous long-horizon cognition, or CapabilityOS-routed execution until those
substrates are production-ready.

### Implemented Context Bridge

Hive now runs the first production slice of phase 1 before routing/planning:

```text
memoryos context build --for hive --task <prompt> --json
  -> .runs/<run_id>/artifacts/memory_context.json
  -> .runs/<run_id>/context_pack.md
  -> run_state.memoryos_context.trace_id
  -> run_state.accepted_memories_used[]
```

The bridge is non-blocking. If MemoryOS is absent, empty, or fails, Hive records
the reason as a run artifact and continues the workflow. Accepted memory remains
MemoryOS-owned; Hive only consumes reviewed context plus RetrievalTrace
provenance.

### Phase Ownership

| Phase | Owner | Notes |
|---|---|---|
| Prompt/log UI | Hive | Final UX hides run folders by default. |
| Scheduling and execution | Hive | Provider/native CLIs stay available but ledgered. |
| Verification and referee routing | Hive | Executor should not verify itself. |
| Draft memory emission | Hive | Drafts are proposals, not accepted memory. |
| Review lifecycle | MemoryOS | Accept/reject/stale is MemoryOS authority. |
| Context paging | MemoryOS -> Hive | Only reviewed memory should feed future runs. |
| Capability selection | CapabilityOS -> Hive | Later: evidence-backed tool/workflow recommendations. |

## Roles

- `user.director`: final direction, taste, acceptance, and boundary.
- `claude.planner`: critique, planning, unresolved risks, claim discipline.
- `codex.executor`: code changes, tests, logs, reproducible evidence.
- `gemini.reviewer`: alternate review and second opinion.
- `local.context`: cheap-first context compression, classification, memory drafts, summaries.

## Product Rule

Prompt changes, role changes, routing changes, and skill changes are proposals
until reviewed. Hive Mind may draft and score them; it should not silently
promote them into policy.

## Foreign-Context Review

Agents working inside the same directory share the same local pressure: dirty
files, recent TODOs, active ownership, passing tests, and the current
implementation frame. That is useful for execution continuity, but it can soften
critique.

Hive should deliberately use a second review mode:

```text
in-directory executor
  -> preserves local state, edits safely, runs tests, records artifacts

foreign-context reviewer
  -> reads the artifact from another directory/context basin
  -> challenges assumptions, claim strength, and missing alternatives
  -> does not inherit the same implementation momentum
```

The reviewer can be the same base model. What matters is not only model family;
it is the context basin. A same-model reviewer with different workspace context
can be sharper than another agent standing inside the same task folder.

Use this mode for:

- architecture claims
- paper framing and research interpretation
- safety/policy boundaries
- provider passthrough permissions
- MemoryOS/Hive/CapabilityOS contract decisions

Record the review as an artifact, not as an informal chat. The executor may
accept, reject, or ask for a referee pass, but should not silently absorb the
review without provenance.

## Hidden Thread

Use `evolution of Single Human Intelligence` as a quiet internal motif for the
product: not a scientific claim, not marketing copy, but a reminder that the
system is extending one person's working memory, judgment, critique, execution,
and self-correction loop.

## Harness Observation Loop

The MemoryOS pingpong experiment exposed a missing layer: Hive can run Claude,
Codex, Gemini, and local workers, but the useful operating pattern is still
mostly buried in stdout logs. Hive should emit a sanitized observation stream
for every provider/native turn.

Minimum event shape:

```json
{
  "event_type": "harness_observation",
  "provider": "codex",
  "role": "executor",
  "phase": "K42.2",
  "command_family": "pytest",
  "tool_family": "shell",
  "artifact_refs": ["agents/codex/executor_result.yaml"],
  "outcome": "passed",
  "failure_class": null,
  "retry_count": 0,
  "privacy_scope": "local_only"
}
```

Ownership split:

- Codex: implement observation emitters, schema tests, and import smokes.
- Claude: review event taxonomy, privacy boundary, and whether observations can
  influence routing policy.
- Local LLM: summarize large raw logs into bounded aggregate observations only;
  it must not accept memory or silently change prompts/routes.

MemoryOS may ingest these rows as draft operational memory. Accepted policy
changes still require review.
