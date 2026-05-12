# Hive Mind TODO

This TODO is ordered by dependency. Do the earliest unfinished item that improves the working loop.

Use `docs/VISION_GRAPH.md` for source provenance. Major sections below include `VG-*` tags.

## Now

Sources: `VG-03`, `VG-04`, `VG-05`, `VG-13`.

- [x] Add repo-local Codex goal sprint contract and user-value benchmark so production-v0 is measured against direct CLI, manual shared-folder coordination, and adversarial review pressure.
- [x] Add `hive goal` as the operator surface for the active production-v0 goal, validation loop, latest value benchmark, latest release gate, and Claude attack prompt.
- [x] Add `hive goal --write-attack-pack` so Claude or a foreign-context reviewer can attack the v0 claim from one generated evidence packet.
- [x] Add `hive demo quickstart` as the first public-alpha five-minute value demo: prompt intake, role routing, receipts/inspect, memory draft, and MemoryOS read model without provider keys.
- [x] Add `hive demo memory-loop` to close the isolated Hive -> MemoryOS -> Hive loop: run memory draft import, approve, context build, and next Hive run references accepted memory.
- [x] Put the public-alpha recommended path first in README and `hive init`: quickstart, memory-loop, run, inspect, goal.
- [x] Record CapabilityOS design lessons from the Hive sprint: required artifacts, recommendation receipts, workflow recipes, quality observations, and Hive/MemoryOS bridge boundaries.
- [x] Fix `docs/MEMORYOS_MVP.md` examples that still mention `docs/1.md` and `docs/2.md`.
- [x] Add source archive hash and import run ID to every imported node/edge.
- [x] Add deduplication for re-imported files.
- [x] Add `memoryos import --dry-run` to preview counts before appending.
- [x] Add `memoryos audit --json` report snapshots under `runs/reports/`.
- [x] Add `memoryos stats` with platform, role, conversation, pair, and source counts.
- [x] Add local LLM worker prompt/CLI layer before runtime installation.
- [x] Add production-minimum `hive init` onboarding for global/project config, provider detection, and next actions.
- [x] Split local open-weight DeepSeek/Qwen status from hosted `deepseek_api`/`qwen_api` key checks.
- [x] Add `hive local status/setup` for local backend adapters, server state, and local model manifests.
- [x] Include local LLM model manifest detection in `hive init` onboarding output.
- [x] Stabilize `hive` run artifact schemas: task, handoff, run state, verification, memory drafts, final report.
- [x] Add canonical `.runs` protocol spec for the Hive Mind run kernel.
- [x] Add human-readable `transcript.md` for Codex-style run logs.
- [x] Add event taxonomy and validation for `.runs/*/events.jsonl`.
- [x] Normalize provider invocation artifacts for Claude, Codex, Gemini, and local workers.
- [x] Add local worker route table with schema validation, confidence, and escalation fields.
- [x] Make `hive tui` show current run health, provider availability, latest event, failures, and missing artifacts.
- [x] Add parser warnings instead of failing entire imports on one malformed record.
- [x] Persist production settings profile during onboarding so provider paths, local model inventory, and shell exports are tracked.
- [x] Add prompt-first `hive ask` local intent routing that decomposes work into Claude/Codex/Gemini/local artifacts.
- [x] Add event-driven `hive flow` / `hive run --flow` first slice: route, prepare provider prompts, write society/workflow state, and expose barriers without provider auto-execution.
- [x] Install `hive` as a real CLI and support provider-style shorthand: `hive "task"`.
- [x] Add production run board UX: pipeline, agents, artifact status, and next recommended action.
- [x] Add local production wrappers: `bin/hive`, `scripts/install-hive-cli.sh`, and private npm `production` script.
- [x] Make bare `hive` enter a conversational operator shell instead of only a thin command shell.
- [x] Make prompt input default to `hive orchestrate`, creating a multi-agent `society_plan.json`.
- [x] Name the provider-CLI harness product `Hive Mind` and document the API-first harness distinction.
- [x] Add reproducible product evaluation script for packaging, routing, provider preparation, run validation, and auto-loop safety smoke checks.

## Production Hardening From `hive_mind2.md`

Sources: `VG-03`, `VG-04`, `VG-05`, `VG-06`, `VG-13`.

Work order: finish the `hive` operator loop before deeper MemoryOS/CapabilityOS integration.

- [x] Add multi-view Hive Console routes for board, events, transcript, agents, artifacts, memory, society, and diff.
- [x] Add observer/controller separation with a durable `.runs/<run_id>/control.lock`.
- [x] Add artifact freshness, producer, phase class, and validation metadata to run-board/TUI status.
- [x] Remove current `mos` naming from the Hive Mind CLI boundary so MemoryOS remains a sibling project.
- [x] Add doctor scopes: `hive doctor hardware|providers|models|permissions|all`.
- [x] Add hardware profile output: CPU, RAM, GPU/VRAM, disk, Python, Node, Docker, local adapter status, provider CLI paths, network, and key ports.
- [x] Embed the user/Claude/Codex/local-LLM working method as a project skill protocol.
- [x] Add `evolution of Single Human Intelligence` as a quiet internal product thread, not a scientific claim.
- [x] Expand provider result schema with command, output, timing, changed files, commands run, tests run, artifacts, risk, policy, and memory/capability refs.
- [x] Add `.hivemind/policy.yaml` default policy plus `hive policy check/explain`.
- [x] Add local model profile and role auto-assignment artifacts.
- [x] Add agent role registry, permission policy, role prompt templates, and `hive agents explain <role>`.
- [x] Add verifier, product evaluator, and actual-user persona roles to the agent registry for repeatable product pressure tests.
- [x] Add production context builder/budgeter/validator and `hive context build --for <agent-role>`.
- [x] Add multi-session workspace layout hints with `hive workspace --layout dev|dual`.
- [x] Add run audit/observability command for provider failures, stale artifacts, unverified outputs, and policy drift.
- [x] Add real local model benchmark prompts with measured JSON validity and latency.
- [x] Add optional `llm-checker` adapter plan without vendoring upstream code.
- [x] Add test coverage for expanded provider results, policy gates, context packs, and local model profiles.
- [x] Add expanded on-disk fixtures for invalid provider results, policy gates, local model profiles, and complete minimal runs.

## Public Release Gate

Sources: `VG-03`, `VG-04`, `VG-05`, `VG-13`.

Do not switch the GitHub repository from private to public until this gate is green.

- [x] Keep GitHub visibility private until all public-release blockers are resolved.
- [x] Run and archive `npm test`, `git diff --check`, and `hive doctor all`.
- [x] Run local secret/privacy scan over tracked files and resolve any credential, token, raw export, or personal data exposure.
- [x] Invoke Claude reviewer for public-release security review and resolve all high/medium findings.
- [x] Add expanded on-disk fixtures for invalid provider results, policy gates, local backend profiles, and complete minimal runs.
- [x] Document `hive-local-backend-v1` adapter contract and mark non-Ollama adapters as planned/stubbed until implemented.
- [x] Ensure README and docs say `Status: private alpha` or `public alpha`, with no production-grade claim before production gates pass.
- [x] Verify `.gitignore` excludes `.runs/`, `.hivemind/`, `.local/`, raw exports, generated memory stores, and model files.
- [x] Add a public-release checklist command or script that reproduces the release gate.
- [x] Switch GitHub repository visibility to public only after the above checks pass.

## Provider Debate And Convergence

Sources: `VG-03`, `VG-04`, `VG-06`, `VG-13`.

- [x] Add redacted operator method profile for intent routing and task decomposition system context.
- [x] Add `hive debate <topic>` for provider first opinions, review round, and convergence artifacts.
- [x] Define Hive Mind as the chair that controls turn order, barriers, disagreement records, convergence, and next action.
- [x] Fix qwen3/Ollama JSON routing issue by sending top-level `think: false` plus `/no_think` instead of treating `{}` fallback as acceptable.
- [x] Stop routing from auto-running local worker roles; provider/local execution remains explicit after prompt preparation.
- [x] Bridge prompt routing into lifecycle setup: `hive "task"` / `hive orchestrate` now creates `plan_dag.json` and `workflow_state.json` instead of stopping at `society_plan.json`.
- [x] Promote safe local workers into bounded task processors for simple local tasks through DAG/ledger execution with explicit `--execute-local`.
- [ ] Add disagreement extraction from executed provider outputs into a structured `disagreements.json`.
- [x] Surface `disagreements.json` in `hive inspect` and upgrade inspect verdict to `escalated` for high/medium disagreement topology.
- [ ] Upgrade task decomposition beyond keyword heuristics with a schema-validated router, provider fallback, and route-quality scoring.
- [ ] Add convergence scoring: evidence strength, reversibility, risk, and user-preference fit.
- [ ] Add TUI view for active debate rounds and participant readiness.
- [ ] Add MemoryOS draft extraction from debate convergence only after human review.
- [ ] Add debate mode flags per round: cooperative, adversarial, and verification-only.
- [ ] Add binding `PreCommitTable` artifacts with agent signatures and result-to-disposition matching.
- [ ] Add `Front` state machine so new debate fronts are blocked until the current cheap falsifiable test closes or the user overrides.
- [ ] Add turn arbitration with owner, deadline, next speaker, timeout, and user escalation.
- [ ] Add frame-anchor drift checks for active claim shape and forbidden language before accepting position notes.
- [x] Add source-read registry that can flag shared source input with divergent agent interpretations.

## Layered Chair Runtime

Sources: `VG-03`, `VG-04`, `VG-05`, `VG-12`, `VG-14`, `VG-15`, `VG-16`, `VG-17`.

Source: `docs/HIVE_MIND_GAPS.md` section "Header Role Decomposition and Per-Layer Provider Selection".

- [x] Add a small chair runtime spec before implementation so L0/L1 do not become an over-designed header LLM.
- [ ] Define chair layer artifact schemas: `DispatcherState`, `VerifierCheck`, `WorkingAgentTurn`, `RefereeDecision`, `NorthStarAudit`, and `ConflictReview`.
- [ ] Implement L0 dispatcher as code-first state machine for rounds, fronts, turns, timeouts, artifact arrival, and next-speaker scheduling.
- [x] Add first `plan_dag.json` runtime and CLI surface: `hive plan dag`, `hive step list/status/next/run`, and DAG-aware `hive next`.
- [ ] Reconcile `artifacts/workflow_state.json` and `plan_dag.json` into one durable scheduler surface.
- [ ] Harden DAG step result handling so failed local/provider artifacts become `failed` or `skipped`, not `completed`.
- [ ] Policy-gate or replace the Claude `--dangerously-skip-permissions` execute workaround before expanding automation.
- [x] Specify adaptive adversarial chair design: task feature vectors, step evaluations, append-only DAG mutations, referee decisions, and capability learning.
- [ ] Persist `StepEvaluation` artifacts under `.runs/<run_id>/step_evaluations/`, not only inline `PlanStep.evaluation`.
- [ ] Converge `PlanStep` on `evaluation_policy` and phase out ad hoc `quality_gates`, `escalation_threshold`, and `referee_policy` use.
- [ ] Add `TaskFeatureVector` artifact and mode router for cooperative/adversarial/verification-only/red-team defaults by task shape.
- [ ] Add `dag_mutations.jsonl` tests for observe-only mutation proposals: retry, reviewer, verifier, referee, run_test, ask_user.
- [x] Refresh auto-estimated reversibility on every execution attempt, preserve operator-declared values, and surface gate factors in `execute_fan_out`.
- [ ] Calibrate reversibility thresholds from run history and false-positive review logs before raising `REVERSIBILITY_BLOCK_THRESHOLD`.
- [x] Add per-run `execution_ledger.jsonl` so DAG scheduler/step authority, permission mode, bypass mode, touched files, and artifacts are visible to CLI/TUI.
- [x] Specify ledger protocol over `execution_ledger.jsonl`: `ExecutionIntent`, `ExecutionVote`, `ExecutionDecision`, `ExecutionProof`, quorum, bypass class, lease, verifier close, and replay rules.
- [x] Implement protocol artifact schemas and helpers for `execution_intents/`, `execution_votes/`, `execution_decisions/`, and `execution_proofs/`.
- [x] Add `hive protocol intent/check/vote/decide/proof` as dry-run-first CLI commands.
- [x] Gate provider `hive step run --execute` through an approved `ExecutionDecision` while preserving prepare-only flow.
- [x] Add `hive ledger replay` to reconstruct step authority state and detect hash/artifact drift.
- [ ] Extend ledger replay with artifact content hashes and command/prompt hash drift.
- [x] Add ledger `artifact_sha256` tracking and replay-time `artifact_hash_drift` detection for recorded artifacts.
- [x] Extend TUI ledger view with current authority, waiting votes, active intent, replay issues, and verifier/proof state.
- [ ] Extend TUI protocol drilldown with per-intent conditions, artifact paths, and active lease details.
- [x] Design `ProbeStep` criterion schema before implementation: typed criterion, evaluator, expected artifact field, timeout, and failure disposition.
- [x] Surface `ProbeStep` action, confidence, and criteria count in ledger replay, TUI ledger cockpit, and supervised run status.
- [ ] Add bounded parallel fan-out/fan-in runner for safe runnable steps, with durable resume and barrier joins.
- [ ] Add evaluation-aware barrier joins: close only when dependency status and evaluation policy are satisfied.
- [ ] Add `RefereeDecision` artifact and `referee` step type; prefer required next tests over winner selection.
- [ ] Add capability-performance memory by provider, role, task feature vector, quality, cost, and outcome.
- [ ] Implement L1 verifier checks for schema validity, process launch hygiene, stale artifact detection, forbidden-language scans, and file/scope checks.
- [ ] Add provider-family metadata to provider capabilities so L2/L3/L5 can enforce model-family heterogeneity.
- [ ] Add role routing policy: L0 code/local-only, L1 code/local/cheap-hosted, L2 frontier workers, L3 different-family referee, L4 long-context auditor, L5 different-family conflict reviewer.
- [x] Promote the MemoryOS pingpong pattern into `hive run start --scheduler pingpong` as an L0 serialized execution kernel.
- [x] Add `HANDOFF.json`/shared-folder compatibility import so old MemoryOS pingpong loops can be replayed into Hive run artifacts.
- [ ] Add L1 blackboard claim/scope artifacts for multi-agent ownership beyond a single current turn.
- [ ] Add `foreign-context reviewer` routing: export a compact artifact for review from a sibling directory/context basin before accepting architecture, policy, or research-framing changes.
- [ ] Add `ContextBasin` metadata and `coupling_score`/`independence_score` to reviewer routing so repeated cross-directory interaction can decay independence over time.
- [ ] Add `foreign_review_<run_id>.json` artifact with source_basin, target_basin, prior_shared_rounds, review_mode, pushbacks, risks, and recommended_tests.
- [ ] Add `hive chair status` to show active layer, front, turn owner, pending verifier checks, and next escalation.
- [ ] Add `hive chair audit` for event-triggered North-Star audits on front close, claim wording changes, frame edits, and publish gates.
- [ ] Add `hive chair assign` dry-run to explain which provider family will be used for each layer and why.
- [ ] Add tests for monolithic-header prevention: L0 cannot make content judgments, L3/L5 cannot reuse the active working-agent family unless explicitly overridden.

## Hive Mind Gap Closure

Sources: `VG-01`, `VG-03`, `VG-06`, `VG-14`.

Source mirror: `docs/HIVE_MIND_GAPS.md` from `../memoryOS/docs/shared/HIVE_MIND_GAPS.md`.

- [x] Add pre-run MemoryOS context build integration so each Hive run records accepted memories used.
- [x] Upgrade verification from artifact checks to objective, scope, acceptance, and trust checks.
- [x] Add handoff quality gates for objective, files/domains, constraints, acceptance criteria, risks, commands, tests, and raw refs.
- [x] Record routing evidence: task type, risk, required tools, provider availability, latency/cost, past performance, user preference, and local confidence.
- [x] Add cross-agent conflict set artifacts with reviewer assignment and accepted/rejected/superseded resolution.
- [x] Refine `hive next` into a prioritized operator decision surface grounded in run state.
- [ ] Replace placeholder MemoryOS context command with the sibling repo's canonical command after MemoryOS exposes it.
- [x] Add semantic verifier LLM review for high-risk runs.
- [ ] Add document supersession edges so stale handoffs are explicitly replaced, not inferred from mtimes.
- [ ] Add claim/evidence ledger with supported, blocked, falsified, superseded, required evidence, allowed wording, and forbidden wording fields.
- [x] Add arrival packs generated from live run state: objective, owners, blocked tasks, accepted claims, contested claims, scope, logs, and latest artifacts.
- [x] Add first-class `hive evaluate` or `hive subagents review` command that runs verifier, product evaluator, and actual-user persona checks into durable artifacts.

## Harness Runtime

Sources: `VG-03`, `VG-04`, `VG-13`, `VG-18`.

- [x] Add schema validation to `python -m hivemind.hive verify`.
- [x] Validate provider `*_result.yaml` artifacts during `hive verify`.
- [x] Add `MemoryObject` and `Hyperedge` schemas in code.
- [x] Add `hive invoke <provider> --dry-run` for prompt/command artifact generation.
- [x] Add `hive provider <claude|codex|gemini> --dry-run|--execute -- <native args...>` passthrough so native CLI features remain available under Hive artifacts/ledger.
- [x] Keep Codex prepare-only until non-interactive execution is explicitly stable.
- [x] Record provider mode: `prepare_only`, `execute_supported`, or `unavailable`.
- [x] Ensure failed provider/local invocations write artifacts and events.
- [x] Add a minimal valid run fixture for harness tests.
- [x] Add `memoryos import-run .runs/<run_id>` or equivalent draft import path.
- [x] Add `hive settings detect/shell` and `scripts/hive-workbench.sh` for context editing plus fast provider artifact preparation.
- [x] Add `hive provider <claude|codex|gemini> -- <native args>` passthrough so native CLI features stay available behind Hive artifacts, ledger intents, policy decisions, stdout/stderr capture, and proof records.
- [x] Add TUI prompt routing controls: `n` for new prompt and `a` for auto-routing the current run.
- [x] Add `hive run -q --json` and shell completion script generation for bash/zsh/fish.
- [x] Add interactive slash-command shell for `hive` inspired by OpenClaude/Open Codex.
- [x] Add UTF-8/Hangul-capable TUI composer with cursor movement, Ctrl+C cancel, Ctrl+V paste, Ctrl+D quit, and provider-style line editing.
- [x] Make TUI prompt submission non-blocking so slow local/provider routing cannot freeze the console.
- [x] Make TUI current-run lock handling dynamic so new prompt runs do not break controller heartbeat.
- [x] Treat dead controller-lock PIDs as stale before TTL so killed TUI sessions do not block restart.
- [x] Use fast heuristic routing for normal TUI prompts so local LLM router latency does not make the console feel stuck.
- [x] Add `.hivemind/checks/*.md` markdown-as-agent-check policy files inspired by Continue.
- [x] Add git-first diff/check/commit summary loop inspired by Aider.
- [x] Make `hive diff` include ledger health, record count, artifact hash drift count, and ledger-touched files.
- [x] Add unified prompt input via `hive prompt` and slash shell `/prompt`.
- [x] Add adapter registry stubs for opencode, goose, OpenClaude-compatible runtimes.
- [x] Add `hive next`, `hive agents status`, and `hive memory list` for fast operator loops.
- [x] Ground `hive next` in disagreement topology, DAG state, provider failures, and pipeline fallback.
- [x] Add option-only `hive loop` self-judgment/autopilot surface: dry-run by default, `--execute` plus per-action `--allow`, no provider CLI auto-execution, no arbitrary shell, no memory commit.
- [x] Make `hive loop` validation-safe and failure-aware: auto-loop events are accepted by run validation, failed local workers stop the loop, and failed agent state fails verification.
- [x] Make `hive tui` interactive with prompt input, slash command input, and dashboard layout.
- [x] Add always-visible TUI `hive>` composer so prompt entry is discoverable.
- [x] Add `hive demo live` and TUI `/demo` to animate multi-agent coordination through real run artifacts without executing provider CLIs.
- [x] Make bare `hive` open the Hive Console/TUI on interactive terminals while keeping `hive tui` as the explicit mode.
- [x] Add `hive ledger` and TUI ledger view for real-time workloop visibility.
- [x] Add `hive_events.jsonl` and `hive hive activity` so human activity shows role assignment, not only artifact creation.
- [x] Harden provider result validation for all prepared/executed adapters.
- [x] Add supervised run control: `hive run start/status/tail/stop` with PID, host, log path, command hash, commit, replay health, and active lease reporting.
- [x] Connect prompt intake to the DAG lifecycle read model so prompt/log and future desktop/chatbot surfaces consume the same core scheduler state.
- [ ] Extend supervised run control with process heartbeat, timeout recovery, GPU/runtime snapshot, and stronger output artifact validation.
- [ ] Add `hive git guard` / scoped commit proposal that refuses out-of-scope staged files unless explicitly approved.
- [ ] Make `hive "task"` and `hive ask` return a readable operator summary with artifact links, next command, risk, and expected artifact.
- [ ] Add Korean-first operator summaries when the input prompt is Korean.
- [x] Move primary UX toward prompt/log AIOS mode: hide run-folder paths by default, show live log, decisions, blocked gates, risks, and outcomes first.
- [x] Add a `hive live` / default prompt-log surface that follows ledger decisions without requiring users to browse TUI panels or filesystem artifacts.
- [ ] Make bare interactive `hive` default to prompt/log live mode once supervisor/protocol replay is stable enough.
- [x] Export `hive live` / ledger / protocol state as a stable MemoryOS-consumable read model for neural-map observability.
- [x] Add `HiveLiveEventV1` fields to `hive live --memoryos` events: `event_id`, `event_type`, `run_id`, `timestamp`, `agent_id`, and `payload`.
- [x] Derive MemoryOS live event IDs from execution ledger `seq/hash` when available, with content-hash fallback for older `hive_events.jsonl` activity.
- [x] Replace planned MemoryOS context command placeholders with an actual `memoryos context build --for hive --json` pre-run context bridge.
- [ ] Ask Claude to review provider passthrough policy boundaries: which native flags stay hard-blocked, which require protocol approval, and whether `event_type` should normalize provider passthrough as `agent_action`.

## Parser Work

Sources: `VG-01`, `VG-11`.

- [ ] Create `tests/fixtures/exports/`.
- [ ] Add redacted ChatGPT fixture.
- [ ] Add redacted DeepSeek fixture from current local structure.

## H-P0 Production Harness Close

Definition: Hive Mind production v0 is the runtime harness only. It must be a
local, auditable, provider-CLI swarm harness that can run bounded agent work,
preserve native provider CLI capability, record execution receipts, stop safely,
and degrade cleanly without MemoryOS. MemoryOS and CapabilityOS remain optional
substrates for memory/context and capability routing.

- [x] Stabilize the current green runtime changes before adding new behavior.
- [x] Split or plan extraction from `hivemind/harness.py` into narrower runtime modules: memory bridge, provider passthrough, flow runtime, and run receipts.
- [x] Extract the MemoryOS context bridge from `hivemind/harness.py` into `hivemind/memory_bridge.py` while preserving public harness imports.
- [x] Extract native provider passthrough from `hivemind/harness.py` into `hivemind/provider_passthrough.py` while preserving the public harness wrapper.
- [x] Extract provider/local run receipt helpers from `hivemind/harness.py` into `hivemind/run_receipts.py` and make validation inspect nested native passthrough receipts.
- [x] Extract prompt-to-workflow advancement from `hivemind/harness.py` into `hivemind/flow_runtime.py` while preserving public harness wrappers.
- [x] Harden provider passthrough policy from denylist-only toward provider/profile allowlists plus explicit approval-gated escape hatches.
- [x] Add provider/profile allowlist enforcement for `hive provider --execute` while keeping dry-run passthrough broad for native CLI capability discovery.
- [ ] Add terminal receipt coverage for completed, failed, timeout, skipped, policy-blocked, and partial provider/local runs.
- [x] Add explicit provider passthrough timeout receipts with status `timeout`, returncode `124`, captured partial stdout/stderr, validation, proof, and inspect visibility.
- [x] Add local worker terminal artifact inspection and validation for completed, failed, fallback, skipped, timeout, and partial local results under `agents/local/*.json`.
- [x] Add `hive inspect <run>` as a path-hidden operator summary over run state, ledger, provider results, receipts, policy decisions, and next action.
- [x] Harden supervisor heartbeat/timeout recovery and make `hive run stop/status/tail` production-safe for interrupted runs.
- [x] Add a Hive-only production smoke script that does not require MemoryOS: init, run, local step, provider dry-run, ledger replay, inspect, stop, validation.
- [ ] Keep MemoryOS context hook optional and non-blocking; failed/absent MemoryOS must produce a receipt, not abort Hive runtime.
- [x] Update public-facing docs to claim only "production runtime harness v0" until MemoryOS/CapabilityOS loops are production-ready.
- [ ] Add redacted Grok fixture from current local structure.
- [ ] Add redacted Perplexity markdown ZIP fixture.
- [ ] Add Claude export parser after a sample export is available.
- [ ] Add Gemini Takeout parser after a sample export is available.
- [ ] Store parser name and parser version in imported node metadata.
- [ ] Document user-facing export steps for each provider.

## Schema Work

Sources: `VG-01`, `VG-07`, `VG-09`, `VG-12`.

- [ ] Add `SourceArtifact` or equivalent source table/file for archive members.
- [ ] Add node review statuses: `new`, `reviewed`, `accepted`, `rejected`, `speculative`, `stale`.
- [ ] Add claim fields: evidence_state, confidence, reviewer, review_time.
- [ ] Add edge fields: relation confidence, evidence list, plasticity score, last used.
- [ ] Add hyperedge representation for multi-node events.
- [x] Add first `Hyperedge` dataclass representation for multi-node events.
- [ ] Add project nodes and project membership edges.
- [ ] Add user-originated vs AI-originated provenance fields.

## Extraction Work

Sources: `VG-01`, `VG-08`, `VG-12`.

- [ ] Replace current heuristic extraction with a two-stage pipeline: deterministic chunking first, LLM/local model labeling second.
- [ ] Extract intent: question, request, critique, idea, decision, reflection, implementation, design, research.
- [ ] Extract project: Uri, Dipeen, GoEN, North Star, Deepfake, Capstone, MemoryOS, unknown.
- [ ] Extract evidence links and unsupported claims separately.
- [ ] Extract action items with owner, status, source, and due context if present.
- [ ] Preserve ambiguity as branches instead of forcing one interpretation.

## Local LLM Workers

Sources: `VG-05`, `VG-03`, `VG-04`.

- [x] Define route table for classify, extract-memory, extract-capability, compress-context, draft-handoff, summarize-log, and review-diff.
- [x] Store primary model, fallback model, complexity, expected schema, and escalation rule for each role.
- [x] Add schema validation for worker outputs.
- [x] Add `confidence`, `should_escalate`, and `escalation_reason` to worker draft schemas.
- [x] Add role-specific MemoryOS, CapabilityOS, and code-log benchmark prompts.
- [x] Record model, latency, output validity, and failure reason for each worker run.
- [x] Decouple local worker runtime from Ollama through `hive-local-backend-v1`.
- [x] Record first local model benchmark summary in `docs/LOCAL_MODEL_BENCHMARK.md`.
- [ ] Add corpus-backed benchmark fixtures for longer MemoryOS, CapabilityOS, and code-log samples.

## Audit Work

Sources: `VG-12`, `VG-01`.

- [ ] Separate extracted nodes from reviewed nodes in audit output.
- [ ] Add unsupported claim report.
- [ ] Add unresolved question report.
- [ ] Add stale decision report.
- [ ] Add repeated concern report.
- [ ] Add "my ideas only" report using role/provenance.
- [ ] Add cross-provider disagreement report.

## Search And Embeddings

Sources: `VG-01`, `VG-07`.

- [ ] Choose first local embedding path.
- [ ] Add embedding records for message, pair, segment, conversation summary, and user-only thought.
- [ ] Add local vector index.
- [ ] Add hybrid keyword + vector search.
- [ ] Add graph-filtered search by project, source, role, and node type.
- [ ] Add evaluation queries from `docs/NORTHSTAR.md`.

## API And UI

Sources: `VG-10`, `VG-01`, `VG-03`, `VG-18`.

- [ ] Add local FastAPI or equivalent API.
- [ ] Add endpoints: import status, audit summary, search, node detail, node review, graph neighborhood.
- [ ] Add Hive run observability endpoints for MemoryOS using the `hive live --memoryos` read-model contract and `HiveLiveEventV1` event fields.
- [ ] Build import center against real import runs.
- [ ] Build memory cockpit against real graph counts.
- [ ] Build Ask Memory with evidence-linked answers.
- [ ] Build graph explorer for project/concept/claim/task edges.
- [ ] Design the MemoryOS neural map around Hive read-model events instead of duplicating Hive's terminal dashboard.
- [ ] Build draft review screen for accept/edit/reject.
- [ ] Keep the visual cockpit deferred until `hive` run artifacts, ledger/protocol read models, and MemoryOS review state are stable.

## Agent Harness

Sources: `VG-03`, `VG-04`, `VG-06`.

- [ ] Define agent roles as local prompt/protocol files: archivist, critic, planner, synthesizer, guardian.
- [ ] Define provider adapter roles: planner, executor, reviewer, summarizer, memory extractor, capability extractor.
- [ ] Define `AgentRun` and `AgentRunEvent` records from harness artifacts.
- [ ] Link every run-derived memory draft to raw refs under `.runs/<run_id>/`.
- [ ] Add proposed graph edit queue.
- [ ] Add graph edit scoring fields.
- [ ] Add commit log for accepted graph edits.
- [ ] Add disagreement log for conflicting agent recommendations.
- [ ] Add rollback story for bad graph edits.

## CapabilityOS

Sources: `VG-02`, `VG-04`, `VG-13`.

- [ ] Define `TechnologyCard`, `Capability`, `WorkflowRecipe`, `ProviderRuntime`, `QualityProfile`, `Risk`, and `LegacyRelation` schemas.
- [ ] Seed provider/runtime records for qwen local workers, DeepSeek code workers, Claude, Codex, Gemini, and local backend adapters.
- [ ] Store `extract-capability` output as draft CapabilityOS records only.
- [ ] Add first workflow recipe: `hive planning -> Codex implementation -> local summarize -> MemoryOS memory draft`.
- [ ] Add legacy comparisons for raw chat, manual shared folder, screenshot-only, and local-model-only workflows.
- [ ] Require source refs for every capability recommendation.

## Agent Society

Sources: `VG-06`, `VG-00`.

- [ ] Define `AgentProfile`, `PerformanceRecord`, `PeerReview`, `UserFeedback`, `RoutingPolicyProposal`, and `PromptMutationProposal`.
- [ ] Add `HarnessObservation` import contract for provider/pingpong runs: provider CLI, role, phase, command family, tool/MCP family, artifact refs, test/check outcome, failure class, retry count, and privacy scope. This should feed MemoryOS as draft operational memory, not accepted policy.
- [ ] Add `hive harness observe` or equivalent export surface that emits sanitized observation JSONL for Claude/Codex/Gemini/local worker turns without raw prompt/stdout content.
- [ ] Add local LLM summarizer role for harness observations: compress raw run logs into bounded tool-use/failure/retry summaries; never accept memory or mutate routing policy directly.
- [ ] Add structured peer review artifact criteria: acceptance fit, quality, risk, project alignment, missing tests, recommendation.
- [ ] Add user feedback states: accepted, accepted_with_edits, rejected, redo_requested, manually_fixed, ignored.
- [ ] Add failure attribution fields: context issue, prompt issue, provider limitation, task ambiguity, implementation bug, verification gap.
- [ ] Add safety gate so profile/routing/prompt changes are proposals until reviewed.
- [ ] Allow only low-risk aggregate metric updates without manual approval.

## GoEN / Dipeen Research

Sources: `VG-07`, `VG-08`, `VG-09`.

- [ ] Write MPU-D0 spec: Hypergraph Research Memory.
- [ ] Build corpus benchmark with files, code, notes, and conversation excerpts.
- [ ] Measure evidence recall against raw text and vector-only baselines.
- [ ] Write GoEN Reverse Translation spec.
- [ ] Implement possibility branch representation.
- [ ] Write MPU-D1 spec: Ontology Plasticity Agent.
- [ ] Define synthetic world with hidden relation changes.
- [ ] Compare fixed graph, rewired graph, and ontology-editing graph.

## Security And Product

Sources: `VG-12`, `VG-13`.

- [ ] Decide local-only default for raw exports.
- [ ] Add raw export deletion command.
- [ ] Add redaction preview for sensitive imports.
- [ ] Add private project exclusion.
- [ ] Draft privacy principles: no training on user uploads, export/delete always available.
- [ ] Design optional encrypted backup.
- [x] Add `run_id` format validation as post-alpha hardening.
- [ ] Redact env var names from public status JSON where practical.
- [ ] Add secret scrubbing for captured subprocess output artifacts.

## Publishing Gate

Sources: `VG-00`, `VG-03`, `VG-06`, `VG-12`, `VG-14`.

- [x] Preserve Claude public-alpha security review evidence in `docs/security/PUBLIC_ALPHA_SECURITY_REVIEW.md`.
- [x] Define publish as release/tag/package/announcement, separate from current public-alpha GitHub visibility.
- [x] Run foreign-context public-alpha review and resolve high/medium onboarding blockers.
- [ ] Add structured disagreement extraction to `hive debate`.
- [ ] Connect `hive gaps` to canonical MemoryOS context builder.
- [x] Add semantic verifier review for high-risk runs.
- [ ] Publish release/tag/package/announcement only after the North Star gate is materially met.

## Documentation

Sources: `VG-00` through `VG-13`.

- [ ] Keep `docs/NORTHSTAR.md` as the top-level vision.
- [ ] Keep `docs/ROADMAP.md` as phase order.
- [ ] Keep `docs/TODO.md` as the active implementation list.
- [x] Add `docs/ROUTE.md` as the docs route map.
- [x] Add `docs/VISION_GRAPH.md` as the source-to-work vision graph.
- [x] Add `docs/LOWERCASE_SOURCE_GRAPH.md` for lowercase source-vault docs.
- [x] Split large source vault docs into `docs/split/` mirrors without deleting originals.
- [x] Create reusable Codex skill `docs-vision-router` for future docs graph/source routing work.
- [ ] Keep `docs/MEMORYOS_MVP.md` focused only on the current local MVP.
- [ ] Keep `docs/EXPORT_PARSERS.md` focused only on provider export adapters.
- [ ] Add a short `docs/README.md` index for new sessions.
