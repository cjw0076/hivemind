# Adaptive Adversarial Chair

Status: system design / implementation target.

Sources: `VG-14`, `VG-15`, `VG-16`.

Hive Mind should not become "many agents in a row." The target is an adaptive
research and execution OS: each task is decomposed into epistemic trials, each
trial produces evidence and uncertainty, and the chair changes the next agent
allocation based on quality, risk, disagreement, cost, and reversibility.

## Core Thesis

The chair is not a smart monolithic LLM. It is a deterministic coordination
runtime with explicit evaluator and referee layers.

```text
Coordinator
  -> Dispatcher: DAG runnable steps, dependency state, barriers, deadlines
  -> Evaluator: output quality, risk, evidence, disagreement, cost
  -> Referee: contested claims, procedure, synthesis, required next test
```

The system becomes useful when the evaluator and referee are first-class DAG
participants. `on_failure: escalate` and `debate_topic()` are only seeds; they
must be integrated into step evaluation, mutation proposals, and barrier logic.

## Ideal Product Shape

Hive Mind should feel like this:

```text
hive "ship this feature safely"
  -> classify task feature vector
  -> build adaptive DAG
  -> run cheap parallel context/review workers
  -> evaluate outputs
  -> promote uncertainty to the right provider only when valuable
  -> run implementation/review/verification
  -> surface disagreements and next tests
  -> close with evidence, residual risk, memory draft, and next action
```

For small tasks, Hive Mind should stay quiet and cheap. For ambiguous,
high-risk, research-like tasks, Hive Mind should widen the agent society,
force disagreement to be explicit, and converge through evidence rather than
social consensus.

## New Research Ideas

### 1. Epistemic Trial

A `PlanStep` is not just an action. It is a trial:

```text
hypothesis / task slice
  -> input artifacts
  -> agent output
  -> extracted claims
  -> quality evaluation
  -> next allocation decision
```

This makes implementation, review, architecture, and research use the same
runtime shape.

### 2. Value Of Information Scheduler

The scheduler should ask whether another model call is worth it:

```text
value = uncertainty_reduction * decision_impact * irreversibility
        - provider_cost - latency_cost - coordination_overhead
```

Rules of thumb:

- low risk + reversible + tests pass: accept;
- high uncertainty + cheap reversible work: local or small hosted second pass;
- high risk + low reversibility: referee or auditor;
- high disagreement + falsifiable test exists: run the test before more debate;
- high disagreement + no test: referee or user decision.

This prevents "call every provider" from becoming a fake quality signal.

### 3. Disagreement Topology

Disagreement should be represented as a graph, not a flat note.

```text
claim A
  conflicts_with claim B
  supported_by artifact X
  blocked_by missing test Y
  owner: claude-planner
  challenger: gemini-reviewer
```

The chair can then route by conflict shape:

- wording conflict: L1 verifier or local normalizer;
- implementation conflict: Codex/diff test;
- risk conflict: security reviewer;
- strategy conflict: referee;
- north-star conflict: L4 auditor;
- unsupported claim conflict: claim ledger gate.

### 4. Mode Router

Adversarial is not the default for every task.

| Task shape | Default mode | Escalation |
|---|---|---|
| Small reversible implementation | cooperative | review after diff |
| High-risk implementation | cooperative + verifier | adversarial review |
| Architecture | independent proposals | referee/synthesis |
| Research | adversarial | falsifiable test gate |
| Security/public release | red-team first | user approval |
| Memory extraction | verifier-heavy | claim/evidence audit |
| Product taste | user-preference fit | optional outside reader |

### 5. Referee As Test Designer

The referee should not mainly pick a winner. The strongest referee output is a
next discriminating test:

```yaml
disposition: run_test
accepted_claims: [...]
rejected_claims: [...]
unresolved_claims: [...]
required_next_test:
  command: python -m unittest tests.test_plan_dag
  expected_result: failing case reproduces barrier bug
```

When no test exists, the referee should expose the hidden assumption and ask
for user taste or project direction.

### 6. Dual Memory

Hive Mind needs two memory lanes:

- `task_memory`: accepted decisions and evidence for this project;
- `capability_memory`: how each provider/role performed on similar task
  features.

The scheduler should learn from capability memory without letting it override
current evidence.

### 7. Counterfactual Baseline

Hive Mind must keep proving it is worth the overhead. Product eval should
compare:

- direct Codex;
- direct Claude;
- manual shared-folder collaboration;
- Hive Mind adaptive chair.

The key metric is not raw speed only. It is:

```text
quality gain + auditability gain + risk reduction - coordination cost
```

### 8. No Consensus Without Receipts

Consensus should not close a front unless the accepted claims have evidence.

Required close fields:

- accepted claims;
- rejected claims;
- unresolved claims;
- evidence artifacts;
- tests run;
- residual risk;
- next action;
- human approval requirement.

## Artifact Model

### TaskFeatureVector

Path: `.runs/<run_id>/chair/task_features.json`

```json
{
  "risk": "low|medium|high|critical",
  "ambiguity": "low|medium|high",
  "reversibility": "low|medium|high",
  "parallelizable": true,
  "needs_code_write": false,
  "needs_review": true,
  "needs_referee": false,
  "needs_north_star_audit": false,
  "estimated_cost_class": "cheap|normal|expensive",
  "preferred_mode": "cooperative|adversarial|verification_only|red_team"
}
```

### StepEvaluation

Path: `.runs/<run_id>/step_evaluations/<step_id>.json`

```json
{
  "step_id": "planner",
  "evaluated_at": "ISO-8601",
  "evaluators": {
    "syntax": {"schema_valid": true, "artifact_complete": true},
    "execution": {"tests_run": [], "returncode": null},
    "claim": {"claim_count": 4, "unsupported_claims": 1, "evidence_score": 0.62},
    "risk": {"risk_level": "medium", "scope_risk": "low"},
    "disagreement": {"count": 2, "targets": ["alt_planner"]}
  },
  "recommendation": "accept|retry|escalate|add_review|referee|run_test|ask_user|block",
  "reason": "unsupported_claims_above threshold",
  "mutation_mode": "observe_only|adaptive"
}
```

### DagMutation

Path: `.runs/<run_id>/dag_mutations.jsonl`

Dynamic mutation must be append-only.

```json
{
  "event": "dynamic_step_proposed",
  "active": false,
  "mode": "observe_only",
  "trigger_step": "planner",
  "would_insert": "gemini-risk-review",
  "reason": "risk_level=high",
  "source_evaluation": "step_evaluations/planner.json"
}
```

Only `--adaptive` should allow `active: true`.

### RefereeDecision

Path: `.runs/<run_id>/chair/referee_decision.json`

```json
{
  "front_id": "front-001",
  "disposition": "synthesize|choose_a|choose_b|run_test|ask_user|split_front|block",
  "accepted_claims": [],
  "rejected_claims": [],
  "unresolved_claims": [],
  "required_next_test": null,
  "reason": "",
  "provider_family_independent": true
}
```

### AgentPerformance

Path: `.hivemind/agent_performance.jsonl`

```json
{
  "provider": "claude",
  "role": "planner",
  "task_features": {"risk": "medium", "ambiguity": "high"},
  "quality": {"accepted_claim_rate": 0.8, "unsupported_claim_rate": 0.1},
  "cost": {"duration_ms": 120000},
  "outcome": "accepted|revised|rejected|blocked"
}
```

## PlanStep Policy Shape

`PlanStep` should expose policy, not hidden logic.

```yaml
evaluation_policy:
  evaluators: [syntax, execution, claim, risk, disagreement]
  accept_if:
    schema_valid: true
    risk_below: high
    unsupported_claims_below: 1
    disagreement_below: 2
  escalate_if:
    confidence_below: 0.5
    risk_level_above: medium
    unsupported_claims_above: 1
    disagreement_with: [alt_planner]
  referee_if:
    contradictory_core_claims: true
    no_falsifiable_test: true
  mutation_policy:
    mode: observe_only
    allowed_insertions: [retry, reviewer, verifier, referee, run_test, ask_user]
```

Compatibility fields such as `quality_gates`, `escalation_threshold`, and
`referee_policy` can remain temporarily, but new code should converge on
`evaluation_policy`.

## Runtime Loop

```text
1. classify task feature vector
2. build initial DAG
3. run runnable safe parallel steps
4. evaluate every completed/prepared/failed step
5. write StepEvaluation artifacts
6. propose DagMutation records in observe_only mode
7. close barrier only when join criteria and evaluation policy are satisfied
8. call referee when conflict cannot be resolved by tests or schema
9. in --adaptive mode, materialize approved mutations
10. verify, summarize, draft memory, close
```

## Safety Rules

- Default mutation mode is `observe_only`.
- Provider CLI execution remains explicit and policy-gated.
- L0 dispatcher cannot make content judgments.
- L1 verifier cannot accept fuzzy semantic claims.
- L3 referee cannot be the same provider family as the contested L2 workers
  unless the user explicitly overrides.
- Dynamic DAG mutation is append-only and replayable.
- Memory commit remains human-reviewed.

## Implementation Sequence

P0. Contract foundation:

- converge `PlanStep` on `evaluation_policy`;
- write `StepEvaluation` artifacts, not only inline fields;
- keep `dag_mutations.jsonl` observe-only;
- add tests for low confidence, failed artifact, high risk, and disagreement
  recommendations.

P1. Scheduler unification:

- make `plan_dag.json` the canonical scheduler;
- keep `workflow_state.json` as a read model derived from the DAG;
- make `hive flow` create or advance the DAG.

P2. Parallel fan-out:

- run safe local/internal parallel steps first;
- add timeout and partial-failure handling;
- close barriers using evaluation-aware join rules.

P3. Referee integration:

- add `referee` step type;
- extract disagreements into `disagreements.json`;
- generate `referee_decision.json`;
- prefer required next tests over winner selection.

P4. Adaptive mode:

- enable dynamic step insertion only behind `--adaptive`;
- require allowed insertion types;
- log every mutation;
- support replay from initial DAG plus mutation log.

P5. Capability learning:

- record provider/role performance by task feature vector;
- use performance memory as a routing prior;
- never let past performance override current evidence.

## North Star

The product win is not "more agents." The win is that Hive Mind can decide when
more agents are worth using, preserve why that decision was made, and converge
through evidence while keeping the user in control of irreversible direction.
