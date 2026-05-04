# Chair Runtime Spec

Status: implementation spec / not complete.

Source: `docs/HIVE_MIND_GAPS.md` section "Header Role Decomposition and
Per-Layer Provider Selection"; `docs/PUBLISHING_GATE.md` North Star;
`docs/ADAPTIVE_ADVERSARIAL_CHAIR.md`.

This spec prevents a monolithic "header LLM" from becoming the hidden product.
Hive Mind should be a thin chair runtime: deterministic state first, judgment
roles only when needed.

## Current State Versus Intent

Current implementation:

- `hive ask` and `hive orchestrate` create run artifacts and provider prompts.
- `hive flow` and `hive run --flow` advance a run through the first event-driven
  prepare-only workflow slice and write `artifacts/workflow_state.json`.
- Provider execution defaults to `prepare_only`.
- TUI prompt routing uses a fast heuristic path for responsiveness.
- `hive loop` can judge the next run action, but it is option-only: dry-run by
  default, execution requires `--execute` and per-action `--allow`.
- Deep decomposition is still incomplete when local/router output is invalid or
  shallow.

Product intent:

```text
user intent
  -> classify and decompose
  -> gather role-specific context
  -> evaluate each step as an epistemic trial
  -> chaired debate when judgment is needed
  -> adaptive DAG mutation proposals when uncertainty/risk/disagreement warrants
  -> implementation / review / verification artifacts
  -> disagreement and convergence records
```

The current state must not be described as if it already satisfies the intent.
Prepare-only provider prompts are intentional. Heuristic-only decomposition is a
temporary gap.

## Layer Boundaries

| Layer | Name | Owner | Code Home | Artifact Home | Judgment |
|---|---|---|---|---|---|
| L0 | Dispatcher | code | `hivemind/chair.py` then `harness.py` integration | `.runs/<run_id>/chair/dispatcher_state.json` | none |
| L1 | Verifier | code/local | `hivemind/chair.py` plus `run_validation.py` hooks | `.runs/<run_id>/chair/verifier_checks.json` | low |
| L2 | Working agents | providers/local | existing provider adapters | `.runs/<run_id>/agents/<provider>/` | high |
| L3 | Referee | provider | provider adapter role | `.runs/<run_id>/chair/referee_decision.json` | procedural |
| L4 | North-Star auditor | long-context provider | provider adapter role | `.runs/<run_id>/chair/north_star_audit.json` | high / long context |
| L5 | Conflict reviewer | provider | provider adapter role | `.runs/<run_id>/chair/conflict_review.json` | high / content |

## L0 Dispatcher Scope

L0 may:

- track active front, round, turn owner, and timeout;
- notice artifact arrival;
- schedule the next verifier or participant;
- record state transitions;
- refuse structurally invalid transitions.

L0 must not:

- decide whether a research claim is true;
- decide whether an argument is strong;
- rewrite provider conclusions;
- choose a scientific or product conclusion without a higher-layer artifact.

## L1 Verifier Scope

L1 may check:

- schema validity;
- process launch hygiene;
- stale or missing artifacts;
- forbidden-language grep against a `FrameAnchor`;
- staged-file scope;
- whether a pre-commit table has all required fields and signatures.

L1 must mark fuzzy semantic judgments as `needs_referee` or `needs_auditor`.

## First Implementation Slice

The first runtime slice now exists as `hive flow`:

- route a task if `routing_plan.json` is missing;
- prepare provider prompt/result artifacts without executing provider CLIs;
- write `society_plan.json`;
- write `artifacts/workflow_state.json` with sequential steps, parallel members,
  barrier status, next action, and policy;
- optionally run local context with `--execute-local`;
- re-prepare provider prompts after local context so downstream prompts receive
  the completed local context artifact.

Next read-only chair work:

1. Add `hivemind/chair.py` with dataclasses and pure functions only.
2. Write `dispatcher_state.json` from current run facts without changing run
   behavior.
3. Write `verifier_checks.json` from existing validation, lock, provider, and
   artifact freshness checks.
4. Add `hive chair status --json` as read-only output.
5. Add provider-family metadata and dry-run assignment explanation.

Only after the read-only slice is stable should L0 start blocking or scheduling
turns.

## Adaptive Adversarial Layer

The next chair layer is specified in `docs/ADAPTIVE_ADVERSARIAL_CHAIR.md`.
Summary:

- each `PlanStep` is an epistemic trial, not just a command;
- evaluation is multi-dimensional: syntax, execution, claim, risk, and
  disagreement;
- dynamic DAG changes are append-only mutation proposals first;
- default mutation mode is `observe_only`;
- real DAG insertion must require explicit `--adaptive` and policy approval;
- referee output should prefer a discriminating next test over winner picking.

`PlanStep.evaluation_policy` is the preferred future contract. Compatibility
fields such as `quality_gates`, `escalation_threshold`, and `referee_policy`
may remain during migration, but new scheduler code should converge on one
policy shape.

## Option-Only Auto Loop

`hive loop` is the narrow first slice of self-judgment and auto-execution. It is
not a provider autopilot.

Allowed by design:

- propose the next action from current run state;
- write `.runs/<run_id>/artifacts/auto_loop_plan.json`;
- with `--execute --allow <action>`, run allowlisted internal actions only:
  `audit`, `verify`, `memory-draft`, `summarize`, `diff`, `check-run`,
  `local-context`, or `local-review`.

Blocked by design:

- provider CLI execution such as Claude, Codex, or Gemini;
- arbitrary shell commands;
- memory commit;
- opening a new prompt/routing boundary without the operator.
- repeating a failed local action without surfacing `hive audit`.

This keeps the chair loop useful for repetitive run hygiene while preserving
the user as the authority for risky execution and project direction.

## Provider Policy

- L0: code only, no LLM required.
- L1: code first; local or cheap hosted model only for fuzzy wording checks.
- L2: frontier-class working agents.
- L3/L5: provider family should differ from active L2 agents unless the user
  explicitly overrides.
- L4: long-context provider, event-triggered rather than every turn.
