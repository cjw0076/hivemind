# Compact Handoff For MyWorld Agents

<!--
handoff_owner: Codex
handoff_time_kst: 2026-05-02 08:47 KST
workspace: /home/user/workspaces/jaewon/myworld
purpose: Preserve progress across context compaction so Claude/Codex/Gemini/local agents can resume without replaying the full chat.
-->

## Current Product Direction

<!-- status: active -->

The production target is an installable `mos` CLI that wraps MemoryOS, CapabilityOS, provider CLIs, MCP, local runtime, and Agent Society:

```bash
npm install -g @memoryos/cli
mos init
mos doctor
mos agents detect
mos run "..."
```

Read these first after compaction:

1. `AGENTS.md`
2. `docs/ROUTE.md`
3. `docs/VISION_GRAPH.md`
4. `docs/LOWERCASE_SOURCE_GRAPH.md`
5. `docs/make_production.md`
6. `docs/cli_help.md`
7. `docs/TUI_HARNESS.md`
8. `docs/PROVIDER_HARNESS_GUIDE.md`
9. `runs/work_items/harness_agent_society_work_items.md`
10. `runs/work_items/provider_harness_expansion.md`
11. `.ai-runs/shared/comms_log.md`

## What Was Implemented

<!-- owner: Codex; completed_at_kst: 2026-05-02 08:47 KST -->

- `mos` wrapper CLI/TUI exists in `memoryos/mos.py`, `memoryos/tui.py`, and `memoryos/harness.py`.
- `mos tui` has keybindings:
  - `l`: local context worker
  - `c`: Claude planner prompt
  - `x`: Codex executor prompt
  - `g`: Gemini reviewer prompt
  - `v`: verification report
  - `s`: final report summary
  - `m`: memory draft
  - `r`: refresh
  - `q`: quit
- Provider prompt artifacts are written under `.runs/<run_id>/agents/<provider>/`.
- `mos doctor` checks `.runs`, current run, provider capability artifact, and provider availability.
- `mos agents detect` writes `.runs/provider_capabilities.json`.
- `mos local status/setup` reports the Ollama wrapper, server state, local model manifests, missing recommended models, and writes `.memoryos/local_runtime.json`.
- `mos init` now performs production-minimum onboarding: creates `~/.memoryos/`, project `.memoryos/`, default config/routing/agents files, initializes `.runs/`, runs provider detection, scans local model manifests, writes `.memoryos/local_runtime.json`, and prints next actions.
- `mos verify` now validates run artifact schemas and event taxonomy through `memoryos/run_validation.py`.
- `mos invoke <provider> --dry-run` writes prompt, command, and normalized result artifacts. Codex execution is blocked as prepare-only until stable.
- `mos local routes` exposes local worker route table, model tiers, expected schemas, and escalation fields.
- `mos status`/`mos tui` now show run health: verification verdict, provider availability, missing artifacts, and recent failures.
- `memoryos import` now emits recoverable parser warnings for malformed records instead of failing the entire import.
- `memoryos import-run <run_id|current|path>` now imports run state and memory drafts into draft graph nodes.
- Docs route cleanup added `docs/ROUTE.md` and `docs/VISION_GRAPH.md`; TODO sections now carry `VG-*` provenance tags.
- Lowercase source-vault docs are mapped in `docs/LOWERCASE_SOURCE_GRAPH.md`.
- Reusable Codex skill created at `/home/user/.codex/skills/docs-vision-router` for future docs graph/source routing work.
- Large source docs were split into navigable mirrors under `docs/split/my_world/`, `docs/split/memoryOS/`, and `docs/split/goen_resonance/` without deleting originals.
- Gemini CLI was installed with `npm install -g @google/gemini-cli`; `gemini --version` returned `0.40.1`.
- Codex CLI contract is documented in `docs/cli_help.md`; `codex exec --cd . --sandbox read-only --ask-for-approval never ...` is the intended safe read-only execution shape.
- Current machine has Codex gated by local access prompt; harness captures this as `codex-reviewer [failed]` with result/output artifacts instead of crashing.

## Current Provider State

<!-- source: mos doctor + mos local status; checked_at_kst: 2026-05-02 09:00 KST -->

- Claude: available, `2.1.126 (Claude Code)`.
- Gemini: available, `0.40.1`.
- Codex: command exists, but local execution is gated.
- Ollama wrapper: available at `scripts/ollama-local.sh`; server was unreachable during latest local status check.
- Local open-weight model manifests exist for `deepseek-coder:6.7b`, `deepseek-coder-v2:16b`, `qwen3:1.7b`, and `qwen3:8b`.
- DeepSeek local models do not require an API key; hosted `deepseek_api` is unconfigured because `DEEPSEEK_API_KEY` is not set.
- Qwen local models do not require an API key; hosted `qwen_api` is unconfigured because `QWEN_API_KEY` is not set.

## Active Run State

<!-- current_run_at_handoff: run_20260502_083717_f34e54 -->

Current run:

```text
run_20260502_083717_f34e54
Task: TUI keybinding harness smoke
Status: needs_attention after Codex gated execution test
```

This run includes successful TUI keybinding artifact generation and a captured Codex access-gate failure.

## Parallel Agent Outputs

<!-- owner: subagents; completed_at_kst: 2026-05-02 -->

Provider guide worker created:

- `docs/PROVIDER_HARNESS_GUIDE.md`
- `runs/work_items/provider_harness_expansion.md`

Docs/work-item worker updated:

- `runs/work_items/harness_agent_society_work_items.md`
- `docs/TODO.md`
- `docs/NORTHSTAR.md`
- `docs/ROADMAP.md`

## Next P0 Work

<!-- priority: P0; suggested_owner: Codex -->

1. Add redacted parser fixtures for ChatGPT, DeepSeek, Grok, Perplexity, Claude, and Gemini.
2. Store parser name/version in imported node metadata.
3. Add reviewed node status fields and claim discipline fields.
4. Add HTTP adapters for DeepSeek and Qwen with provider-specific env vars.
5. Add draft graph edit queue and accepted graph edit commit log.

## Guardrails

<!-- safety_policy: active -->

- Keep raw AI export data local-first.
- Do not build Desktop before `mos` run artifacts/review states are stable.
- Local LLM output is draft only.
- Agent Society may propose routing/prompt/profile updates, but must not auto-apply them without review.
- Do not modify `/home/user/workspaces/jaewon/universe/quantum` from MyWorld unless explicitly asked.
