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

## 2026-05-04 12:50 KST - Codex - Live Workloop Ledger Start

- Context: User asked whether the shared-folder/pingpong work style can be absorbed into `hive tui` as a real-time surface, then asked to implement the shared operator sense as code.
- Ownership: Codex owns the first visible runtime slice: append-only execution ledger, DAG step start/finish/touched-file records, CLI ledger tail, and a TUI ledger view.
- Expected files: `hivemind/workloop.py`, `hivemind/plan_dag.py`, `hivemind/hive.py`, `hivemind/tui.py`, focused tests, `docs/TODO.md`, `docs/TUI_HARNESS.md`, and `.ai-runs/shared/comms_log.md`.
- Deferred: Full supervisor daemon, provider bypass quorum, and network transport remain design/next slices; this pass makes current work observable first.

## 2026-05-04 13:00 KST - Codex - Live Workloop Ledger Complete

- Context: Completed the first visible runtime slice for turning shared-folder coordination into a real-time TUI read-model.
- Decision: `execution_ledger.jsonl` is now the per-run authority/touched-file ledger. DAG step execution and fan-out scheduler rounds append hash-chained records; CLI and TUI can tail the ledger.
- Evidence: Added `hivemind/workloop.py`, wired `execute_step()` and `execute_fan_out()`, added `hive ledger`, added TUI F9/`/ledger`, and added tests. Verified `python -m unittest tests.test_workloop_ledger tests.test_tui_composer tests.test_plan_dag`, `npm test` (165 tests), `git diff --check`, CLI ledger smoke, and PTY `hive ledger --follow` smoke.
- Next: Build the supervisor/bypass slice on top of this ledger: long-running process lifecycle, vote/quorum artifacts, and explicit bypass policy records.

## 2026-05-04 13:08 KST - Codex - Ledger Protocol Design Start

- Context: User asked to design the protocol that moves on top of the new ledger.
- Ownership: Codex owns the first protocol contract doc: state machine, artifacts, quorum/bypass rules, leases, failure handling, and implementation slices.
- Expected files: `docs/LEDGER_PROTOCOL.md`, `docs/CHAIR_RUNTIME_SPEC.md`, `docs/TODO.md`, `.ai-runs/shared/comms_log.md`.
- Deferred: Python implementation of supervisor/vote/quorum commands stays for the next slice after the artifact protocol is stable.

## 2026-05-04 13:15 KST - Codex - Ledger Protocol Design Complete

- Context: Finished the design pass for the protocol over `execution_ledger.jsonl`.
- Decision: The protocol state machine is `intent -> policy -> vote/quorum -> lease -> execution/proof -> verifier close`. Bypass remains allowed, but only as an explicit protocol class with ledgered intent, decision, lease, proof, and verification.
- Evidence: Added `docs/LEDGER_PROTOCOL.md`, linked it from `docs/ROUTE.md`, `docs/README.md`, `docs/VISION_GRAPH.md` as `VG-17`, and connected it to `docs/CHAIR_RUNTIME_SPEC.md` plus `docs/TODO.md`. Verified references with `rg`, `python -m py_compile hivemind/*.py`, and `git diff --check`.
- Next: Implement protocol artifacts and dry-run CLI first: `hive protocol intent/check/vote/decide/proof`, then gate `hive step run --execute` through approved decisions.

## 2026-05-04 13:33 KST - Codex - Ledger Protocol P0 Implementation Start

- Context: User told Codex to keep pushing and try the protocol implementation rather than stopping at design.
- Ownership: Codex owns the first implementation slice: protocol dataclasses/helpers, `hive protocol` CLI, execution-decision gate for `hive step run --execute`, tests, and docs/log updates.
- Expected files: `hivemind/protocol.py`, `hivemind/hive.py`, `hivemind/plan_dag.py`, `tests/test_protocol.py`, `docs/TODO.md`, `.ai-runs/shared/comms_log.md`.
- Deferred: Supervisor daemon, process heartbeat, replay, and TUI protocol panels remain next slices.

## 2026-05-04 13:41 KST - Codex - Ledger Protocol P0 Complete

- Context: Completed the first executable layer over `execution_ledger.jsonl`.
- Decision: Added protocol artifacts and CLI before adding a supervisor. Provider `hive step run --execute` now requires an approved `ExecutionDecision`; prepare-only and local/internal flows remain available.
- Evidence: Added `hivemind/protocol.py` and `tests/test_protocol.py`; wired `hive protocol intent/check/vote/decide/proof`; blocked provider execute without a decision in `plan_dag.execute_step()`. CLI smoke showed approved provider-bypass quorum and `protocol_gate` blocking an unapproved executor step. Verified `python -m unittest tests.test_protocol tests.test_workloop_ledger tests.test_plan_dag`, `npm test` (172 tests), `python -m py_compile hivemind/*.py`, and `git diff --check`.
- Next: Add `hive ledger replay` and TUI protocol panels for active intent, missing votes, decision, lease, proof, and verifier status.

## 2026-05-04 14:28 KST - Codex - AIOS UX North Star

- Context: User clarified the long-term UX: no visible directories, no filesystem browsing, no app requirement; the experience should be prompt input plus logs.
- Decision: Treat files/run folders/JSONL as internal substrate and debug/export surfaces. The user-facing north star is AIOS-style prompt/log operation: prompt in, chaired workflow runs, live logs/decisions/blocked gates/outcomes out.
- Evidence: Updated `docs/NORTHSTAR.md`, `docs/TUI_HARNESS.md`, `docs/LEDGER_PROTOCOL.md`, `docs/VISION_GRAPH.md` (`VG-18`), and `docs/TODO.md`.
- Next: Future UX work should prioritize `hive live`/prompt-log surfaces and hide artifact paths by default.

## 2026-05-04 14:34 KST - Codex - Prompt/Log Live Surface

- Context: User said to proceed after defining AIOS UX as prompt input plus logs, not directories/files/apps.
- Decision: Added `hive live` as the first prompt/log surface over ledger/protocol state. It creates/routes a run when given a prompt, or reads the current run, then shows task state, next action, authority/protocol state, blocked gates, agent status, and live logs while hiding artifact paths by default.
- Evidence: Added `hivemind/live.py`, CLI wiring in `hivemind/hive.py`, and `tests/test_live.py`. Smoke output masks `.runs/...` paths unless `--paths` is passed.
- Next: Add ledger replay and then make `hive live --follow` the default operator shell once supervisor/protocol replay is stable.

## 2026-05-04 14:43 KST - Codex - MemoryOS Neural Map Boundary

- Context: User clarified that `hive tui` should remain for now, but when Hive Mind attaches to MemoryOS, Hive should mainly receive prompts and MemoryOS should own the neural-map observability UI.
- Decision: Locked the product boundary: Hive owns prompt intake, chair orchestration, provider/local execution records, ledger/protocol state, and stable read models; MemoryOS owns the long-term neural-map UI over agent turns, authority gates, claims, evidence, disagreements, memory nodes, and outcomes.
- Evidence: Updated `docs/NORTHSTAR.md`, `docs/TUI_HARNESS.md`, `docs/LEDGER_PROTOCOL.md`, `docs/VISION_GRAPH.md`, `docs/TODO.md`, and `docs/README.md`.
- Next: Build a MemoryOS-consumable Hive read model/event export before investing further in Hive-specific visual UI.

## 2026-05-04 14:46 KST - Codex - MemoryOS Observability Export Start

- Context: User approved starting the next work slice after setting the Hive/MemoryOS UI boundary.
- Ownership: Codex owns the first MemoryOS-consumable read-model export over `hive live`, ledger, and protocol state.
- Expected files: `hivemind/live.py`, `hivemind/hive.py`, `tests/test_live.py`, `docs/TUI_HARNESS.md`, `docs/TODO.md`, and `.ai-runs/shared/comms_log.md`.
- Deferred: MemoryOS-side neural map rendering and API server work stay in the sibling MemoryOS/UI layer until the JSON contract is stable.

## 2026-05-04 14:49 KST - Codex - MemoryOS Observability Export Complete

- Context: Completed Track B's MemoryOS-consumable event export slice before moving to ledger replay.
- Decision: `hive live --memoryos` now emits a graph-oriented `memoryos_neural_map_read_model` with run, agent turn, workflow step, authority gate, vote, memory draft, disagreement, and event records. Paths remain hidden by default.
- Evidence: Updated `hivemind/live.py`, `hivemind/hive.py`, `tests/test_live.py`, `docs/TUI_HARNESS.md`, `docs/TODO.md`, and `docs/README.md`. Verified focused tests, smoke JSON parsing for a Korean prompt, `python -m py_compile hivemind/*.py`, `git diff --check`, and `npm test` with 179 passing tests.
- Next: Continue Track B with `hive ledger replay`: validate hash chain, reconstruct authority state, and report drift/tamper/stale artifact signals.

## 2026-05-04 14:56 KST - Codex - Ledger Replay Complete

- Context: Continued Track B after MemoryOS export. The goal was to make the ledger replayable, not only tail-able.
- Decision: Added `hive ledger replay` as the first replay verifier. It reads raw JSONL, checks invalid lines, schema drift, sequence drift, hash mismatches, previous-hash drift, missing/invalid referenced JSON artifacts, and intent-id artifact drift, then reconstructs step and authority state.
- Evidence: Updated `hivemind/workloop.py`, `hivemind/hive.py`, `tests/test_workloop_ledger.py`, `docs/TUI_HARNESS.md`, `docs/LEDGER_PROTOCOL.md`, `docs/TODO.md`, and `docs/README.md`. Focused replay tests pass, including tamper and missing-artifact detection. Full `npm test` passed 184 tests; CLI smoke replayed a valid ledger with `ok=True`, `hash_chain_ok=True`, and `seq_ok=True`.
- Next: Track B can move to TUI protocol panels. Claude should work Track A in parallel: typed Probe criteria, disagreement axes, and Referee Escrow semantics.

## 2026-05-04 15:06 KST - Codex - TUI Protocol Panels Start

- Context: User confirmed Claude will take Probe Step, so Codex continues Track B.
- Ownership: Codex owns TUI protocol panels over the replayed ledger state: active intent, missing votes, decision, proof, and replay issues.
- Expected files: `hivemind/tui.py`, `tests/test_tui_composer.py`, `docs/TUI_HARNESS.md`, `docs/TODO.md`, and `.ai-runs/shared/comms_log.md`.
- Deferred: Probe Step typed criteria, Disagreement Topology, and Referee Escrow stay with Claude/Track A.

## 2026-05-04 15:09 KST - Codex - TUI Protocol Panels Complete

- Context: Completed the visible protocol panel slice after `hive ledger replay`.
- Decision: The TUI ledger view now renders replay health, active intent, decision, missing voters, votes, proof status, replay issues, and recent ledger rows from the replayed authority state.
- Evidence: Updated `hivemind/tui.py`, `tests/test_tui_composer.py`, `docs/TUI_HARNESS.md`, `docs/LEDGER_PROTOCOL.md`, and `docs/TODO.md`. Focused TUI tests pass with protocol panel coverage; CLI smoke confirmed panel rows include authority/intent/missing-vote/ledger sections; full `npm test` passed 186 tests.
- Next: Keep Track B ready for supervisor/lease detail work; Claude can proceed with Probe Step and evaluation-to-protocol bridge design without UI conflict.
