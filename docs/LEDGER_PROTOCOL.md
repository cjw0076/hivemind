# Ledger Protocol

Status: design contract / P0 partially implemented.

Hive Mind uses ordinary files as the coordination substrate. The ledger protocol
turns that shared-folder work style into a replayable execution system: every
authority transition is written to `.runs/<run_id>/execution_ledger.jsonl`, and
the TUI renders that ledger as the live control surface.

The goal is not to hide automation. The goal is to make automation explicit,
auditable, reversible when possible, and stoppable when it is not.

## North Star

```text
operator intent
  -> execution intent artifact
  -> policy check
  -> vote / quorum when needed
  -> lease
  -> execution or prepare-only artifact
  -> verification
  -> close / memory draft / next action
```

The ledger is the source of truth for authority. Other files such as
`plan_dag.json`, `workflow_state.json`, and TUI read models may cache state, but
they should be derivable from the ledger plus artifacts.

## Core Invariants

1. No hidden execution.
   Every provider call, local worker call, shell command, bypass decision, and
   supervisor action must append a ledger record before and after it runs.

2. Intent before execution.
   A step cannot execute until an `ExecutionIntent` exists and the ledger has an
   `intent_proposed` record.

3. Policy before lease.
   A step cannot acquire an execution lease until the policy gate has emitted
   `policy_allowed`, `policy_blocked`, or `policy_needs_vote`.

4. Bypass is explicit.
   Bypass is allowed because full automation needs it, but bypass must be
   visible as `bypass_mode` in the ledger and must include a policy/vote record.

5. Executor cannot approve itself.
   The role that will run the command may provide risk facts, but cannot be the
   deciding voter for its own execution.

6. Irreversible work needs stronger authority.
   Low-reversibility, broad write scope, networked mutation, memory commit, or
   public publishing requires either a user approval artifact or a repository
   policy that explicitly grants that class of action.

7. Verification closes work.
   A step is not truly complete until execution output is present and a verifier
   record has accepted the required artifact shape.

8. Replay must detect drift.
   Ledger hash chain, artifact hashes, command hashes, prompt hashes, and touched
   file hints should be enough to detect stale or tampered state.

## Protocol Roles

| Role | Layer | Responsibility | May Decide? |
|---|---|---|---|
| Operator | user | direction, taste, high-risk approval, publish boundary | yes |
| Dispatcher | L0 | DAG runnable selection, turns, timeouts, barriers | structural only |
| Policy Gate | L1 | permission, reversibility, scope, bypass class | structural/risk |
| Verifier | L1 | schema, artifacts, command hygiene, tests, stale state | low judgment |
| Working Agent | L2 | plan, implement, review, summarize, execute | within assigned scope |
| Referee | L3 | procedural disagreement resolution | yes, with evidence |
| North-Star Auditor | L4 | drift from project target | yes, periodic |
| Conflict Reviewer | L5 | content contradiction and synthesis pressure | yes |

## Artifact Layout

```text
.runs/<run_id>/
  execution_ledger.jsonl
  execution_intents/
    <intent_id>.json
  execution_votes/
    <intent_id>/
      <voter_role>.json
  execution_decisions/
    <intent_id>.json
  execution_proofs/
    <intent_id>.json
  supervisor_state.json
  plan_dag.json
  agents/
  artifacts/
```

`execution_ledger.jsonl` is append-only. The JSON artifacts are the structured
payloads that ledger records point to.

## ExecutionIntent

An `ExecutionIntent` is a proposed unit of authority. It is created before a
step executes.

```json
{
  "schema_version": 1,
  "intent_id": "intent_<run_id>_<step_id>_<attempt>",
  "run_id": "run_...",
  "step_id": "executor",
  "attempt": 1,
  "requested_by": "harness",
  "owner_role": "codex-executor",
  "provider": "codex",
  "provider_family": "openai",
  "action_type": "provider_cli",
  "command_path": "/abs/path/to/codex",
  "command_hash": "sha256:...",
  "prompt_path": ".runs/<run_id>/agents/codex/executor_prompt.md",
  "prompt_hash": "sha256:...",
  "cwd": "/home/user/workspaces/jaewon/myworld/hivemind",
  "permission_mode": "workspace_write_with_policy",
  "bypass_mode": "prepare",
  "reversibility": 0.5,
  "reversibility_source": "estimated",
  "reversibility_factors": ["permission=workspace_write_with_policy"],
  "expected_artifacts": ["agents/codex/executor_result.yaml"],
  "expected_file_scopes": ["hivemind/**", "tests/**", "docs/**"],
  "timeout_seconds": 600,
  "network_access": "none",
  "env_allowlist": ["PATH", "HOME", "HIVE_*"],
  "risk_level": "medium",
  "created_at": "..."
}
```

## ExecutionVote

Votes are separate artifacts so multiple agents can reason independently.

```json
{
  "schema_version": 1,
  "intent_id": "intent_...",
  "voter_role": "verifier",
  "voter_provider": "local",
  "vote": "approve",
  "confidence": 0.82,
  "risk_level": "medium",
  "reasons": ["scope is constrained", "reversibility above block threshold"],
  "required_conditions": ["run tests after execution"],
  "created_at": "..."
}
```

Allowed votes:

- `approve`
- `approve_with_conditions`
- `block`
- `ask_user`
- `needs_referee`

## ExecutionDecision

The dispatcher writes one decision artifact after policy/votes are collected.

```json
{
  "schema_version": 1,
  "intent_id": "intent_...",
  "decision": "approved",
  "quorum_policy": "reversible_write",
  "votes": {
    "verifier": "approve",
    "risk-evaluator": "approve_with_conditions"
  },
  "conditions": ["run tests after execution"],
  "decided_by": "harness",
  "created_at": "..."
}
```

Allowed decisions:

- `approved`
- `approved_with_conditions`
- `blocked`
- `ask_user`
- `needs_referee`
- `prepare_only`

## ExecutionProof

The proof closes the loop after execution.

```json
{
  "schema_version": 1,
  "intent_id": "intent_...",
  "status": "completed",
  "returncode": 0,
  "started_at": "...",
  "finished_at": "...",
  "duration_ms": 4210,
  "stdout_path": ".runs/<run_id>/agents/codex/stdout.txt",
  "stderr_path": ".runs/<run_id>/agents/codex/stderr.txt",
  "output_path": ".runs/<run_id>/agents/codex/executor_result.yaml",
  "files_touched": ["hivemind/plan_dag.py", "tests/test_plan_dag.py"],
  "commands_run": ["python -m unittest tests.test_plan_dag"],
  "tests_run": ["tests.test_plan_dag"],
  "artifacts_created": ["agents/codex/executor_result.yaml"],
  "policy_violations": [],
  "verifier_status": "accepted"
}
```

## Ledger Event Taxonomy

### Intent and Policy

- `intent_proposed`
- `policy_allowed`
- `policy_blocked`
- `policy_needs_vote`
- `vote_requested`
- `vote_cast`
- `quorum_decided`
- `operator_approval_requested`
- `operator_approved`
- `operator_blocked`

### Lease and Process

- `lease_requested`
- `lease_acquired`
- `lease_conflict`
- `process_started`
- `process_heartbeat`
- `process_completed`
- `process_failed`
- `process_timeout`
- `process_killed`

### Step and Artifact

- `step_started`
- `artifact_created`
- `artifact_updated`
- `verifier_started`
- `verifier_accepted`
- `verifier_rejected`
- `step_completed`
- `step_failed`
- `step_skipped`
- `step_blocked`

### Scheduler and Recovery

- `scheduler_round_started`
- `scheduler_round_completed`
- `barrier_waiting`
- `barrier_closed`
- `supervisor_started`
- `supervisor_stopped`
- `lease_recovered`
- `run_aborted`

The existing implementation already writes a subset of these events. New
commands should extend the taxonomy rather than invent parallel logs.

## State Machine

```text
pending
  -> proposed
  -> policy_checked
  -> voting
  -> approved | blocked | ask_user | needs_referee | prepare_only
  -> leased
  -> running
  -> produced
  -> verified
  -> closed
```

Failure states:

```text
running -> timed_out -> recovered | killed | failed
running -> output_invalid -> retry | needs_referee | ask_user | failed
approved -> lease_conflict -> wait | recover | ask_user
verified -> policy_violation -> rollback | ask_user | failed
```

## Permission and Bypass Classes

| Class | Meaning | Required Authority |
|---|---|---|
| `prepare` | write prompts/results only, no provider execution | dispatcher |
| `local_read` | local read-only analysis or summarization | dispatcher + verifier policy |
| `local_write_reversible` | local files/artifacts only, reversible | policy allow or verifier vote |
| `provider_plan` | hosted/provider planning without repo write | policy allow |
| `provider_bypass_reversible` | provider CLI with bypass and constrained write scope | quorum |
| `provider_bypass_irreversible` | provider CLI with bypass and low reversibility | user approval or explicit repo policy |
| `memory_draft` | draft memory candidate only | verifier policy |
| `memory_commit` | accepted MemoryOS write | user approval or MemoryOS policy |
| `publish` | public release, push, package publish | user approval and publish gate |

Bypass is not a dirty exception. It is a protocol class.

## Quorum Policies

Start conservative:

| Policy | Applies To | Rule |
|---|---|---|
| `prepare_only` | prompt/result preparation | dispatcher may approve |
| `read_only` | no repo write, no network mutation | dispatcher + policy gate |
| `reversible_write` | constrained write, reversibility >= 0.3 | verifier approve; executor cannot vote |
| `provider_bypass` | provider execution with bypass | verifier approve + one independent reviewer or user |
| `irreversible` | reversibility < 0.3, deletion, schema/drop, publish | user approval or explicit policy |
| `conflicted` | evaluator disagreement, high uncertainty | referee or ask_user |

Votes should include `confidence`; quorum can be numerically satisfied but still
escalate if agreement is low.

## Supervisor Loop

The supervisor is a ledger client, not a hidden daemon with private state.

One round:

1. Read `plan_dag.json` and latest ledger.
2. Find runnable steps.
3. Build `ExecutionIntent` for each candidate.
4. Append `intent_proposed`.
5. Run policy check.
6. If needed, request/cast votes.
7. Append `quorum_decided`.
8. Acquire lease.
9. Run prepare/execute action.
10. Write `ExecutionProof`.
11. Run verifier.
12. Close step or escalate.

The TUI should show the current round from ledger state, not from supervisor
stdout.

The ledger is also a UX abstraction boundary. Normal users should eventually see
only prompt input, live logs, decisions, blocked gates, and outcomes. Direct
artifact paths, directory trees, and JSON files are for the AIOS runtime,
debugging, export, and replay, not for the primary workflow.

For the MemoryOS integration, the ledger/protocol stream is also the source feed
for the neural-map observability UI. Hive should export current authority,
agent turns, gates, proofs, touched scopes, decisions, disagreements, and memory
draft status as read-model events. MemoryOS decides how those events become a
map; Hive should not grow a parallel long-term visual interface.

## TUI Read Model

The ledger view should grow into three panels:

- Current authority: active intent, decision, lease holder, bypass mode.
- Work in motion: process, heartbeat age, artifact output, touched files.
- Waiting gates: votes needed, policy block, ask_user, referee, verifier.

This solves the user's current pain point: separate terminal sessions no longer
need to be visually monitored to know whether work is active, blocked, or
mutating files.

## First Implementation Slice

P0:

1. [x] Add `ExecutionIntent`, `ExecutionVote`, `ExecutionDecision`, and
   `ExecutionProof` dataclasses plus JSON read/write helpers.
2. [x] Add `hive protocol intent <step_id>` to write a dry-run intent.
3. [x] Add `hive protocol check <intent_id>` to apply policy/reversibility rules.
4. [x] Add `hive protocol vote <intent_id> --voter verifier --vote approve`.
5. [x] Add `hive protocol decide <intent_id>` with conservative quorum rules.
6. [x] Update provider `execute_step()` so `--execute` requires an approved
   decision while prepare-only flow remains available.
7. [x] Add `hive ledger replay` to reconstruct step/authority state and detect
   hash/artifact drift.
8. [x] Extend TUI ledger view with replay health, active intent, decision,
   missing voters, votes, proof, and replay issues.

P1:

1. [x] Add `hive run start/status/tail/stop` as the first supervisor control
   surface.
2. [x] Add supervisor state/log with PID, host, command hash, git commit,
   replay health, and active lease reporting.
3. [ ] Add process heartbeat and timeout recovery.
4. [ ] Add provider bypass execution through protocol-approved intents.
5. [ ] Add verifier proof validation for stdout/stderr/output paths.
6. [ ] Extend replay with artifact content hashes and command/prompt hash drift.
7. [ ] Add richer TUI drilldown for per-intent artifacts and conditions.

P2:

1. Add referee escalation.
2. Add North-Star audit triggers.
3. Add capability memory from historical decisions and proof quality.
4. Add protocol export for MemoryOS accepted-memory review.

## Open Questions

- Should quorum defaults live in `.hivemind/policy.yaml` or a separate
  `.hivemind/protocol.yaml`?
- Should the first supervisor execute one step per round or keep running until a
  human gate is reached?
- Should provider bypass be allowed for Claude first, or should the first
  automated executor be a local-only command runner?
- How much touched-file precision is required before public alpha?
