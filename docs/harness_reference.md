# Harness Reference

MemoryOS should behave like a provider-native CLI wrapper, but for a whole agent harness:

```text
prompt
  -> local intent router
  -> role decomposition
  -> provider/local artifacts
  -> TUI status and review loop
```

## Current Entry Points

```bash
python -m memoryos.mos ask "your task"
python -m memoryos.mos plan
python -m memoryos.mos tui
```

In TUI:

```text
n  enter a new prompt and auto-route it
a  auto-route current run
e  edit context_pack.md
c  prepare Claude planner
x  prepare Codex executor
g  prepare Gemini reviewer
l  run local context compressor
v  verify artifacts
```

## Routing Policy

- Local `intent_router` decomposes the prompt first.
- Local workers are used for cheap context compression and draft artifacts.
- Claude is preferred for planning, critique, and claim discipline.
- Codex is preferred for implementation artifacts and repo edits.
- Gemini is preferred for alternate review and second perspective.
- Provider execution remains prepare-only unless explicitly supported and safe.

## Artifact Contract

Each routed run writes:

```text
.runs/<run_id>/
  routing_plan.json
  agents/local/intent_router.json
  agents/local/context.json
  agents/claude/planner_result.yaml
  agents/codex/executor_result.yaml
  agents/gemini/reviewer_result.yaml
```

If the local router is unavailable or invalid, the harness writes a fallback route instead of blocking the run.
