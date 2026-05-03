# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Claude Role In MyWorld

You are working in `/home/user/workspaces/jaewon/myworld`.

Before analysis, read:

1. `AGENTS.md`
2. `docs/MYWORLD_IDEA_EXCERPTS.md`
3. `docs/CLAUDE_SHARED_VISION.md`
4. `.ai-runs/shared/comms_log.md`

Your main role here is critique and conceptual discipline:

- identify overclaims;
- separate vision from executable design;
- pressure-test ontology language;
- turn vague ideas into explicit assumptions, risks, and next actions;
- preserve disagreements in logs.

Do not silently import the quantum Paper #4 scope into this project. Quantum is a testbed and reference domain, but MyWorld is the agent-memory / ontology / reflective-system workspace.

When you finish a meaningful critique or decision, append a short note to `.ai-runs/shared/comms_log.md`.

Conversation language: Korean is preferred. Keep code identifiers and filenames in English.

---

## Hivemind: What This Repo Is

`hivemind/` is a local swarm harness for existing provider CLIs and local LLM workers. It coordinates Claude, Codex, Gemini, and Ollama-backed workers into one shared run state. It does not replace provider CLIs; it wraps them into a user-governed blackboard loop.

Status: **public alpha** — do not claim production-grade. See `docs/PUBLISHING_GATE.md` for the release gate checklist.

Sibling repos: `../memoryOS` (memory graph import/audit), `../CapabilityOS` (capability graph).

---

## Commands

### Install
```bash
pip install -e .                          # installs hive and hivemind CLIs
# or without installing:
python -m hivemind.hive <command>
```

### Core CLI
```bash
hive init                   # onboarding: detect providers, write settings profile
hive "your task"            # shorthand: creates run + orchestrate society plan
hive ask "task"             # same, explicit
hive orchestrate "task"     # multi-agent society plan (society_plan.json)
hive status                 # current run state
hive board                  # run board with pipeline, agents, artifact status, next action
hive tui                    # curses TUI (requires interactive terminal)
hive doctor                 # provider/CLI health check
hive doctor hardware|providers|models|permissions|all
hive agents detect|status|view|roles|policy|explain
hive run list|open|audit
hive check run              # run validation verdict
hive policy check|explain
hive local status|setup|routes|benchmark|checker
hive debate "topic"         # chaired provider debate (first-opinion → review → convergence)
hive gaps                   # build gap-closure artifacts for MemoryOS integration
hive next                   # next operator action grounded in current run state
hive diff                   # git diff report for current run
hive context build --for <agent-role>
hive workspace --layout dev|dual
```

### Tests
```bash
pytest tests/ -v                          # full suite (47 tests, ~12s)
pytest tests/test_tui_composer.py -v      # single file
pytest tests/test_run_validation.py::RunValidationTest::test_minimal_fixture_passes -v
```

---

## Architecture

### Source Layout (`hivemind/`)
- `hive.py` — CLI entry point (`main()`), all subcommand dispatch, arg parsing.
- `harness.py` — the core orchestration layer: `RunPaths`, `create_run`, `invoke_external_agent`, `invoke_local`, `orchestrate_prompt`, `ask_router`, `debate_topic`, `close_gap_loop`, all `format_*` and `*_report` functions. ~5000 LOC — the bulk of all logic.
- `tui.py` — curses TUI with 8 views (board/events/transcript/agents/artifacts/memory/society/diff), always-visible composer, background submit thread.
- `local_workers.py` — `WorkerSpec` definitions for intent_router, classifier, json_normalizer, memory_extractor, and other workers; `run_worker()` calls Ollama; `worker_route_table()` selects fast/default/strong model by budget.
- `run_validation.py` — `validate_run_artifacts()` checks run folder against all schemas (task, handoff, run_state, events, verification, memory_drafts, provider_results).
- `utils.py` — `is_valid_run_id()`, `now_iso()`, `stable_id()`.

### Run Artifact Layout (`.runs/<run_id>/`)
```
task.yaml                        # intake artifact
routing_plan.json                # route phase output
context_pack.md                  # context phase (agent-specific context)
agents/<provider>/<role>_result.yaml  # provider result (expanded schema)
handoff.yaml                     # deliberate → execute handoff gate
verification.yaml                # verify phase verdict
memory_drafts.json               # memory phase drafts (for MemoryOS review)
final_report.md                  # close phase
run_state.json                   # mutable blackboard state
events.jsonl                     # append-only event log
transcript.md                    # human-readable run log
society_plan.json                # orchestrate multi-agent plan
control.lock                     # observer/controller separation
artifacts/                       # gap-closure artifacts (gap_closure.json index)
```

`.runs/provider_capabilities.json` — cached provider detection snapshot.
`.hivemind/settings_profile.json` / `~/.hivemind/settings_profile.json` — persisted onboarding profile.
`.hivemind/policy.yaml` — default safety/danger-mode policy.

### Key Invariants
- `run_id` must match `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$`; `RunPaths.__post_init__` enforces this. Path traversal is rejected at every public entry point.
- `control.lock` enforces single-controller: TUI acquires on open, heartbeats every 30s, releases on exit. Second controller is blocked until lock expires (>60s stale).
- Provider result schema requires `schema_version`, `provider`, `role`, `status` plus expanded fields; `validate_run_artifacts()` checks all.
- `hive "prompt"` always calls `orchestrate_prompt()`, not `ask_router()` directly.

### Pipeline Spec (in order)
`intake → route → context → deliberate → handoff → execute → verify → memory → close`

### Publishing Gate
`docs/PUBLISHING_GATE.md` lists the remaining blockers before a public release tag. Current blockers: structured disagreement extraction in `hive debate`, canonical MemoryOS context hook for `hive gaps`, semantic LLM verifier for high-risk runs.
