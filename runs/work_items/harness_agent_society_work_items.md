# Harness, Provider Runtime, and Agent Society Work Items

Date: 2026-05-02 KST

Inputs read for this decomposition:

- `docs/TUI_HARNESS.md`
- `docs/CLAUDE_SHARED_VISION.md`
- `docs/LOCAL_LLM_WORKERS.md`
- `docs/local_llm_use.md`
- `docs/final.md`
- `docs/tui.md`
- `docs/NORTHSTAR.md`
- `docs/ROADMAP.md`
- `docs/TODO.md`
- `docs/capabilityOS.md`
- `docs/agent_society.md`

## 0. Direction

The next executable slice is not a Desktop cockpit or autonomous swarm. It is a file-backed harness that turns agent work into durable artifacts:

```text
user request
  -> mos run folder
  -> context pack
  -> provider/local worker artifacts
  -> verification report
  -> memory/capability drafts
  -> reviewed updates to MemoryOS and CapabilityOS
```

Local LLMs are workers. Claude is a judge/critic. Codex is the implementation executor. The harness is the source of run truth.

## 1. Track H1 - Stabilize `mos` Run Protocol

Goal: make every run inspectable, resumable, and usable by later MemoryOS/CapabilityOS extraction.

Work items:

1. Define schemas for `task.yaml`, `handoff.yaml`, `run_state.json`, `verification.yaml`, `memory_drafts.json`, and `final_report.md`.
2. Add schema validation to `python -m memoryos.mos verify` for the current run folder.
3. Add `mos current` or extend `mos status` to print the resolved `.runs/current` target and missing artifact checklist.
4. Add event types for `run_created`, `context_built`, `agent_prompt_prepared`, `agent_executed`, `verification_written`, `memory_drafts_created`, `summary_written`, and `run_failed`.
5. Add a recoverable failure path: failed provider/local invocations must still write an artifact and event.
6. Add a run fixture under tests that contains a minimal valid run folder.

Acceptance:

- `mos run "x"` creates all required files or explicit placeholders.
- `mos verify` distinguishes valid, incomplete, and corrupted run folders.
- A failed local/provider worker is visible in `events.jsonl` and `run_state.json`.

## 2. Track H2 - Provider Adapter Contracts

Goal: treat Claude, Codex, Gemini, and local workers as provider adapters behind one artifact protocol.

Work items:

1. Define `ProviderInvocation` artifact fields: provider, role, mode, prompt_path, command_path, output_path, exit_status, started_at, finished_at, error_summary.
2. Keep Codex prepare-only until a stable non-interactive execution contract is chosen.
3. Implement adapter capability detection for installed commands: `claude`, `codex`, `gemini`, `ollama`.
4. Add explicit provider modes: `prepare_only`, `execute_supported`, `unavailable`.
5. Add `--dry-run` to `mos invoke <provider>` to render prompt and command without execution.
6. Add provider adapter tests with fake command binaries or command-path injection.

Acceptance:

- `mos invoke claude --role planner --dry-run` writes prompt/command artifacts without calling Claude.
- `mos invoke gemini --role reviewer --execute` records command, output, and exit status when supported.
- Missing provider binaries are reported as harness state, not crashes.

## 3. Track H3 - Local LLM Worker Runtime

Goal: promote the current local worker layer into a provider-like runtime with routing, schema checks, and escalation flags.

Work items:

1. Create a route table for roles: `classify`, `extract-memory`, `extract-capability`, `compress-context`, `draft-handoff`, `summarize-log`, `review-diff`.
2. Store route metadata: primary model, fallback model, complexity, expected schema, escalation rule.
3. Validate worker JSON/YAML output where a schema exists; write invalid-output artifacts instead of silently accepting prose.
4. Add `confidence`, `should_escalate`, and `escalation_reason` to all local worker draft schemas.
5. Add benchmark fixtures for MemoryOS, CapabilityOS, and code-log tasks.
6. Record latency, model, token estimate if available, and output validity for each worker run.

Acceptance:

- `python -m memoryos.cli local-workers status` reports model availability and route readiness.
- `mos invoke local --role memory` writes a schema-checkable draft or a failure artifact.
- Local outputs are clearly marked `draft`, never committed memory.

## 4. Track H4 - MemoryOS Harness Integration

Goal: make run artifacts feed the existing memory substrate without losing source discipline.

Work items:

1. Add `AgentRun` and `AgentRunEvent` node/edge or hyperedge placeholders to the MemoryOS schema.
2. Link every run-derived memory draft to raw refs under `.runs/<run_id>/`.
3. Add `memoryos import-run .runs/<run_id>` or equivalent command for importing harness artifacts.
4. Add audit checks for run-derived memories: missing raw ref, missing provider, missing verification, unsupported decision.
5. Generate memory drafts from `final_report.md`, `verification.yaml`, and provider result artifacts.
6. Keep run import separate from committing accepted memory.

Acceptance:

- A completed run can be imported as draft memory objects with raw refs.
- Audit output separates run artifacts, extracted drafts, and accepted memory.
- No provider output becomes accepted memory without review state.

## 5. Track H5 - CapabilityOS Seed From Harness Evidence

Goal: start CapabilityOS as evidence-backed capability records, not an AI tool directory.

Work items:

1. Define first `TechnologyCard`, `Capability`, `WorkflowRecipe`, `ProviderRuntime`, and `Risk` schemas.
2. Seed local runtime capabilities from current docs: qwen router, qwen structured worker, deepseek code/log worker, deepseek-v2 local reasoning worker, Claude judge, Codex executor, Gemini reviewer.
3. Add `extract-capability` worker output as a draft TechnologyCard only.
4. Add `capability draft` and `capability review` CLI placeholders or document the expected artifact format.
5. Add workflow recipes for the first vertical: `mos planning -> codex implementation -> local summarize -> memory draft`.
6. Track legacy comparison fields: screenshot-only, raw chat-only, manual shared folder, `mos` harness.

Acceptance:

- Capability records name capabilities and constraints, not only tool names.
- Every seeded capability has source refs to docs or run artifacts.
- Workflow recommendation can explain why local worker, Claude, Codex, or Gemini is selected for a role.

## 6. Track H6 - Agent Society Metrics and Safety Gate

Goal: capture agent performance without allowing unsafe self-modification.

Work items:

1. Define `AgentProfile`, `PerformanceRecord`, `PeerReview`, `UserFeedback`, `RoutingPolicyProposal`, and `PromptMutationProposal`.
2. Add structured peer-review artifact for reviewer agents: criteria, found issues, risk, recommendation.
3. Add user feedback states: accepted, accepted_with_edits, rejected, redo_requested, manually_fixed, ignored.
4. Add attribution fields: context issue, prompt issue, provider limitation, task ambiguity, implementation bug, verification gap.
5. Add a safety gate: profile/routing/prompt changes are proposed, not applied, unless explicitly approved.
6. Add low-risk auto-update candidates only for counters and aggregate metrics.

Acceptance:

- Agent Society stores observations and proposals, not autonomous prompt rewrites.
- Routing changes have evidence from multiple runs or explicit user approval.
- Disagreements are logged as first-class records.

## 7. Track H7 - TUI Status Surface

Goal: make the TUI useful as the first operational cockpit while staying file-first.

Work items:

1. Show current run ID, task, phase, status, and missing artifacts.
2. Show provider/local worker availability.
3. Show latest event and last failure.
4. Show artifact checklist: task, context, handoff, provider outputs, verification, memory drafts, summary.
5. Show draft counts: memory drafts, capability drafts, unresolved questions, proposed graph edits.
6. Add a read-only mode first; defer editing/approval to CLI commands until schemas harden.

Acceptance:

- `python -m memoryos.mos tui` can diagnose a run without opening raw files.
- TUI uses only `run_state.json` and `events.jsonl` plus known artifact paths.
- It does not require a DB.

## 8. First Sprint Order

1. H1.1-H1.4: stabilize run schemas and event taxonomy.
2. H2.1-H2.5: normalize provider invocation artifacts.
3. H3.1-H3.4: route table, schema checks, escalation fields for local workers.
4. H7.1-H7.4: make TUI status reflect run health.
5. H4.1-H4.3: import completed runs into MemoryOS as draft records.
6. H5.1-H5.3: seed CapabilityOS draft schemas from current provider docs.
7. H6.1-H6.3: define Agent Society metrics without self-modification.

## 9. Scope Guardrails

- Do not build Desktop before `mos` run artifacts and review states are stable.
- Do not let local LLM output become authority; it remains draft.
- Do not let Agent Society mutate prompts/routing without review.
- Do not build CapabilityOS as a generic directory; every record needs a task/capability/workflow relation.
- Do not modify the quantum workspace from this track.
