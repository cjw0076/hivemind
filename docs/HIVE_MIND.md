# Hive Mind

Hive Mind is the working product name for `mos`.

The goal is not to replace Claude Code, Codex CLI, Gemini CLI, or local LLM runtimes. The goal is to harness already-installed provider CLIs as specialized members of one shared run.

## Difference From API-First Harnesses

Projects such as oh-my-opencode-style harnesses often compose providers through APIs and shared agent presets. Hive Mind takes a different path:

- Keep provider CLIs intact.
- Let Claude, Codex, Gemini, and local LLMs keep their native strengths and command contracts.
- Use `mos` as the control plane that creates shared context, role assignment, run state, artifacts, events, and memory drafts.
- Treat provider CLIs as stateless specialists working over one blackboard, not as separate conversations with separate memories.

## Core Loop

```text
user prompt
  -> local intent router
  -> society_plan.json
  -> provider/local member artifacts
  -> hive_events.jsonl activity feed
  -> verification/checks/memory draft
  -> later synthesis artifact
```

## Logs

Hive Mind keeps two event layers:

- `events.jsonl`: machine/audit log for validation.
- `hive_events.jsonl`: human-readable activity feed showing why members were assigned and what the hive is doing.

Use:

```bash
mos hive activity
mos tui
```

## Current Member Types

- `local/intent-router`: decomposes the prompt.
- `local/context`: compresses local context.
- `claude/planner`: conceptual plan, critique, risk discipline.
- `codex/executor`: implementation-oriented artifact and execution path.
- `gemini/reviewer`: alternate review and broad perspective.

The next major step is synthesis: collect member results and produce one merged decision/action artifact.
