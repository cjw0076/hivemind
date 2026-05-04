# Agent Worklog

## 2026-05-03 00:00 KST - Codex - Product Evaluation Start

- Context: User asked to act as a tester, create varied tasks/situations, verify CLI packaging/production readiness, and compare Hive Mind against the user's manual shared-folder collaboration method and direct single-agent usage.
- Ownership: Codex owns reproducible CLI/package/routing/UX smoke evaluation, focused fixes found by the evaluation, and evidence docs.
- Expected files: `scripts/hive-product-eval.py`, `docs/HIVE_PRODUCT_EVALUATION.md`, route-quality tests, TODO/log updates, and narrow CLI/routing fixes if failures are found.
- Deferred: Claude-style conceptual product critique and final production branding claims remain review inputs, not assumptions.

## 2026-05-03 00:45 KST - Codex - Product Eval Fixes And Auto Loop

- Context: Product smoke found failures in clean CLI install, Korean/debug routing, and test isolation; user also requested a self-judgment/auto-execution loop but only as an option because it is risky.
- Decision: Fix packaging/onboarding and debug routing first, then add `hive loop` as a bounded chair loop: dry-run by default, no provider CLI auto-execution, no arbitrary shell, no memory commit, explicit `--execute --allow <action>` for safe internal actions.
- Evidence: Added product eval script coverage for wheel install, `hive init`, doctor, route matrix, provider preparation, `hive check run`, `hive next`, and auto-loop dry/blocked modes. Added unit tests for dry-run, allowlist enforcement, and external provider blocking.
- Next: Use the product eval report to decide whether Hive Mind is actually better than manual shared-folder coordination; do not call it production until semantic routing, disagreement extraction, and convergence quality are materially stronger.

## 2026-05-03 01:35 KST - Codex - Subagent Review Integration

- Context: User asked to create and use verifier, evaluator, and actual-user persona subagents.
- Decision: Launched three read-only subagents, registered `hive.verifier`, `hive.product_evaluator`, and `persona.actual_user` as repeatable Hive Mind roles, and captured their findings in a durable review artifact.
- Evidence: Added `docs/SUBAGENT_PERSONAS.md` and `docs/SUBAGENT_REVIEW_2026_05_03.md`. Fixed verifier/persona findings: auto-loop event taxonomy, failed-agent validation, failed local action stop/escalation, read-only product eval `--out -`, temp source wheel build, `hive ask --json`, and debate role validation.
- Verification: `npm test` passed 59 tests; `git diff --check` passed; `python scripts/hive-product-eval.py --out -` passed 19/19; `python scripts/hive-product-eval.py --deep --out -` passed 20/20.
- Next: Implement route-quality scoring, readable `hive "task"`/`hive ask` operator summaries, and real `disagreements.json`.

## 2026-05-03 02:05 KST - Codex - Event-Driven Flow Slice

- Context: User compared their real working method with Hive Mind and identified the gap: current Hive Mind is a linear/manual harness, while actual work is tree/event-driven with sequential locks and parallel barriers.
- Ownership: Codex owns the first safe implementation slice: durable workflow state, automatic prepare-only flow advancement, barrier status, and dynamic context injection from local context artifacts into provider prompts.
- Expected files: `hivemind/harness.py`, `hivemind/hive.py`, `hivemind/run_validation.py`, tests, `docs/CHAIR_RUNTIME_SPEC.md`, `docs/TODO.md`, `.ai-runs/shared/comms_log.md`.
- Deferred: Actual provider CLI auto-execution, semantic route-quality scoring, and full DAG scheduler remain explicit future work.

## 2026-05-03 14:35 KST - Codex - DAG Runtime Evaluation

- Context: User summarized a new `plan_dag.py` implementation and asked whether the next P0 should be parallel fan-out plus barrier join.
- Decision: Verified the DAG runtime as a real and useful direction, but do not put fan-out first. The immediate order is safety and correctness: policy-gate the Claude danger-mode execute workaround, harden step result handling, reconcile `hive flow` with `plan_dag.json`, then add bounded parallel fan-out.
- Evidence: `hive plan dag --intent implementation`, `hive step list`, `hive step next`, and `hive step run context --json` worked in a temp workspace. `npm test` passed 80 tests. `python scripts/hive-product-eval.py --deep --out -` passed 21/21.
- Next: Patch DAG execution semantics before parallelism: inspect local/provider result artifacts, apply `on_failure`, define skipped dependency barrier rules, and keep provider CLI execution behind explicit policy.

## 2026-05-03 15:10 KST - Codex - Adaptive Adversarial Chair Design

- Context: User asked for researcher-level ideas beyond the current implementation and for system design toward a dynamic multi-adversarial coordinator.
- Decision: Defined the target as an adaptive adversarial chair: every DAG step is an epistemic trial; evaluator outputs drive observe-only mutation proposals first; referee decisions prefer discriminating tests over winner selection; provider allocation should be based on task features, uncertainty, risk, disagreement, cost, and reversibility.
- Evidence: Added `docs/ADAPTIVE_ADVERSARIAL_CHAIR.md`, added `VG-16 Adaptive Adversarial Chair`, updated `docs/CHAIR_RUNTIME_SPEC.md`, and expanded `docs/TODO.md` with StepEvaluation, TaskFeatureVector, mutation log, evaluation-aware barrier, referee, and capability-memory work items. Existing `hivemind/plan_dag.py` already has a compatible `evaluation_policy` seed and observe-only mutation path; preserved it.
- Next: Implement the contract slice: persist `step_evaluations/<step_id>.json`, add tests for retry/reviewer/referee mutation proposals, and make `workflow_state.json` a read model derived from `plan_dag.json`.

## 2026-05-04 11:10 KST - Codex - TUI Live Swarm Demo

- Context: User wanted to see Codex, Claude, local, Gemini, verifier, and memory roles visibly moving together inside `hive tui`, and also asked to absorb the useful parts of Hermes Agent without making the UI/UX opaque.
- Decision: Added a safe live-demo path instead of pretending provider execution is production-ready. `hive demo live` and TUI `/demo` create or reuse a run, animate role transitions through real `.runs` artifacts and `hive_events.jsonl`, and keep external provider CLIs in prepare-only mode. Bare `hive` now opens the Hive Console/TUI on interactive terminals; `hive tui` remains the explicit mode and `hive chat` remains the plain shell.
- Evidence: Updated `hivemind/harness.py`, `hivemind/hive.py`, `hivemind/tui.py`, `hivemind/run_validation.py`, `tests/test_demo_live.py`, `tests/test_cli_entrypoint.py`, `docs/TUI_HARNESS.md`, `README.md`, and `docs/TODO.md`. Verified focused unit tests, CLI JSON smoke, and a PTY TUI run where the board followed local context, Claude planner, Codex executor, Gemini reviewer, summarizer, verifier, memory, and close.
- Next: Use this demo as the visible read-model baseline, then add transaction/lease semantics before true parallel fan-out and keep networking deferred to a transport boundary rather than a distributed runtime.

## 2026-05-04 12:20 KST - Codex - Reversibility Gate Tightening

- Context: User reviewed the reversibility gate and flagged stale estimated values, false-positive-prone patterns, uncalibrated block threshold, missing fan-out gate reasons, and the risk of rushing Probe Step with a single string criterion.
- Decision: Keep the default/declared/estimated source split and gate position, but refresh auto-estimated reversibility on every execution attempt. Preserve operator-declared values, narrow noisy destructive patterns, persist `reversibility_factors`, and aggregate reversibility gate reasons in fan-out output.
- Evidence: Updated `hivemind/plan_dag.py`, `hivemind/hive.py`, `tests/test_plan_dag.py`, and `docs/TODO.md`. Focused tests caught and fixed an additional bug: estimator was reading `root/<artifact>` but not `.runs/<run_id>/<artifact>`, so actual run artifacts such as `handoff.yaml` could be missed.
- Next: Do not implement Probe Step yet. First design a typed criterion schema and calibrate reversibility threshold/pattern false positives from run history.
