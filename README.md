# Hive Mind

Hive Mind is a local swarm harness for existing provider CLIs and local LLM workers.

It coordinates installed tools such as Claude, Codex, Gemini, and Ollama-backed local workers into one shared run state. It does not replace provider CLIs; it wraps them into a user-governed blackboard loop.

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

## Fast Workbench

```bash
scripts/install-hive-cli.sh
hive init
hive
hive "your task"
hive hive activity
hive plan
hive check run
hive tui
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
