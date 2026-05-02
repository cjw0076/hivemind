# MyWorld / MemoryOS Docs

Start here. This directory contains both current implementation docs and large source-vault notes.

## Read First

1. `../AGENTS.md`
2. `../.ai-runs/shared/COMPACT_HANDOFF.md`
3. `../.ai-runs/shared/comms_log.md`
4. `ROUTE.md`
5. `VISION_GRAPH.md`
6. `LOWERCASE_SOURCE_GRAPH.md`
7. `NORTHSTAR.md`
8. `ROADMAP.md`
9. `TODO.md`

## Current Work

The active build target is an installable `mos` CLI/TUI harness:

```text
mos init
mos doctor
mos run "your task"
mos tui
mos local status
```

Relevant docs:

- `TUI_HARNESS.md`
- `PROVIDER_HARNESS_GUIDE.md`
- `LOCAL_LLM_WORKERS.md`
- `MEMORYOS_MVP.md`
- `make_production.md`
- `cli_help.md`

## Important Boundary

`/home/user/workspaces/jaewon/myworld` is for MemoryOS, CapabilityOS, Agent Society, local/provider harnessing, and multi-ontology memory.

`/home/user/workspaces/jaewon/universe/quantum` is the quantum Paper #4 / P18 workspace. Do not modify it from here unless explicitly asked.

## Large Docs

The largest source docs are:

- `my_world.md`
- `memoryOS.md`
- `goen_resonance.md`

Do not read them fully for routine implementation. Use `ROUTE.md` and the split mirrors under `docs/split/` when available.

## Local Models

Onboarding checks local LLM state:

```bash
python -m memoryos.mos init
python -m memoryos.mos local status
```

DeepSeek and Qwen local open-weight models through Ollama do not need API keys. Hosted API providers need `DEEPSEEK_API_KEY` or `QWEN_API_KEY`.
