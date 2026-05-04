# MyWorld / Hive Mind Docs

Status: public alpha docs. Public-facing claims must stay alpha-scoped until
the production gates in `TODO.md` are green.

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

The active build target is the installable `hive` CLI/TUI harness:

```text
hive init
hive doctor
hive run "your task"
hive run start --max-rounds 8
hive run status
hive live "your task"
hive live --memoryos
hive ledger replay
hive tui
hive local status
```

`hive tui` remains the operator/debug cockpit. The long-term MemoryOS-integrated
UX should treat Hive as prompt intake plus orchestration/ledger/protocol engine;
MemoryOS owns the neural-map observability UI over Hive events and accepted
memory.

Relevant docs:

- `TUI_HARNESS.md`
- `LEDGER_PROTOCOL.md`
- `HIVE_WORKING_METHOD.md`
- `THIRD_PARTY_INTEGRATIONS.md`
- `PROVIDER_HARNESS_GUIDE.md`
- `LOCAL_LLM_WORKERS.md`
- `MEMORYOS_MVP.md`
- `make_production.md`
- `hive_mind2.md`
- `cli_help.md`

## Important Boundary

`/home/user/workspaces/jaewon/myworld` is the umbrella workspace for Hive Mind, MemoryOS, CapabilityOS, Agent Society, local/provider harnessing, and multi-ontology memory.

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
python -m hivemind.hive init
python -m hivemind.hive local status
python -m hivemind.hive local benchmark --backend auto --limit 1
scripts/hive-local-benchmark.sh qwen3:1.7b
HIVE_LOCAL_BACKEND=ollama HIVE_OLLAMA_MODE=docker scripts/hive-local-benchmark.sh qwen3:1.7b
```

DeepSeek and Qwen local open-weight models through a local backend do not need API keys. Ollama is an optional adapter, not a required Hive Mind dependency. Hosted API providers need `DEEPSEEK_API_KEY` or `QWEN_API_KEY`.
