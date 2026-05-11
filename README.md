# Hive Mind

Status: production v0 candidate for the local provider-CLI harness only. Public
alpha is still gated on onboarding and reviewer clarity.

Hive Mind is a local swarm harness for existing provider CLIs and local LLM workers.

It coordinates installed tools such as Claude, Codex, Gemini, and Ollama-backed local workers into one shared run state. It does not replace provider CLIs; it wraps them into a user-governed blackboard loop.

## First Five Minutes

Run the provider-free demo first. It shows the value path without API keys or
local models:

```bash
python -m hivemind.hive demo quickstart
```

That creates a Hive run with role routing, agent artifacts, verification,
memory draft, inspect summary, and a MemoryOS-compatible observability graph.

Then run the feedback-loop demo if the sibling `../memoryOS` repo is present:

```bash
python -m hivemind.hive demo memory-loop
```

That proves the closed loop:

```text
Hive run -> memory draft -> MemoryOS import/approval -> next Hive run context
```

After the demos, the normal operator path is:

```bash
python -m hivemind.hive init
python -m hivemind.hive run "your task"
python -m hivemind.hive inspect <run_id>
python -m hivemind.hive goal
```

Use direct Claude/Codex/Gemini CLIs for trivial one-shot commands. Use Hive
when the task needs receipts, policy gates, stop/replay/inspect, multiple
agents, or MemoryOS feedback.

This release is limited to bounded local runtime orchestration. It is not a
general agent operating system, not an end-to-end memory substrate, and not a
long-running autonomous planner. Alpha testing is expected outside the runtime
harness boundary.

Purpose: implement the user's broader agent / ontology system separately from the `universe/quantum` paper workspace.

Current boundary:

- `universe/` remains the active quantum research and Paper4 workspace.
- `myworld/` is for the agent system: memory, ontology graph, multi-agent coordination, reflection, and reconstruction workflows.

Initial principle:

> Build the smallest working agent system that can preserve decisions, represent uncertainty, compare multiple interpretations, and update a shared ontology without contaminating paper experiments.

## Current Modules

- `hivemind/` — `hive` CLI, provider adapters, TUI, local workers, run validation.
- `.runs/` — Hive Mind run blackboard and per-agent artifacts.
- `.hivemind/` — project settings, checks, runtime profile, local logs.
- `docs/` — shared architecture notes and Hive Mind operating docs.

Memory graph importers, schemas, graph store, and audit code live in the sibling
`../memoryOS` repo. Capability graph work belongs in the sibling
`../CapabilityOS` repo.

## Agent Entry

New Claude/Codex sessions should start from:

- `AGENTS.md` — shared operating rules and current boundary.
- `docs/ROUTE.md` — docs route and source-vault map.
- `.ai-runs/shared/COMPACT_HANDOFF.md` — latest compact-safe implementation state.
- `CLAUDE.md` — Claude-specific critique role.
- `CODEX.md` — Codex-specific implementation role.
- `docs/MYWORLD_IDEA_EXCERPTS.md` — extracted MyWorld ideas from the original `my_world.md`.
- `.ai-runs/shared/comms_log.md` — local shared communication log.

## Relation To Universe

The quantum project provides the first rigorous testbed:

```text
partial observation
→ hidden structure reconstruction
→ identifiability audit
→ branch / ontology management
```

MyWorld generalizes that pattern to broader agentic cognition.

## Model Access

See:

- `docs/LOCAL_LLM_INVENTORY.md` — local hardware/runtime/model state.
- `docs/PROVIDER_MODELS.md` — OpenRouter, DeepSeek, xAI/Grok, OpenAI, gpt-oss, Llama access plan.
- `docs/OPEN_MODEL_PROVIDER_SURVEY.md` — broader open-model provider survey.
- `config/providers.example.yaml` — provider registry template.

## Operator Workbench

```bash
scripts/install-hive-cli.sh
hive init
hive demo quickstart       # first value demo, no provider keys required
hive demo memory-loop      # optional Hive -> MemoryOS -> Hive feedback demo
hive run "your task"
hive inspect <run_id>
hive goal
hive tui                   # optional interactive console
```

Or without installing:

```bash
python -m hivemind.hive init
scripts/hive-workbench.sh "your task"
```

Memory graph import/audit code has moved to the sibling `memoryOS` repo:

```bash
cd ../memoryOS
python -m memoryos.cli stats
python -m memoryos.cli import-run --root ../hivemind current --dry-run
```

Onboarding persists detected provider/runtime settings to `.hivemind/settings_profile.json` and `~/.hivemind/settings_profile.json`. Use `eval "$(python -m hivemind.hive settings shell)"` when launching provider CLIs from custom scripts.
