# Run Artifact Protocol

This is the canonical `.runs/<run_id>/` contract for the current MemoryOS Core loop.

## Required Files

```text
.runs/<run_id>/
  task.yaml
  context_pack.md
  handoff.yaml
  events.jsonl
  run_state.json
  verification.yaml
  memory_drafts.json
  final_report.md
  agents/
    local/
    claude/
    codex/
    gemini/
  artifacts/
```

## Provider Results

Provider result files live under:

```text
agents/<provider>/<role>_result.yaml
```

Required fields:

```yaml
schema_version: 1
agent: claude
role: planner
status: prepared
provider_mode: execute_supported
```

Allowed statuses:

```text
prepared, completed, failed, fallback
```

Allowed provider modes:

```text
prepare_only, execute_supported, unavailable, local_runtime, http
```

Optional path fields such as `prompt`, `command`, and `output` must point to existing files when present.

## Memory Drafts

`memory_drafts.json` must be:

```json
{
  "memory_drafts": [
    {
      "type": "decision",
      "content": "Keep mos run protocol canonical.",
      "origin": "user",
      "project": "MemoryOS",
      "confidence": 0.9,
      "status": "draft",
      "raw_refs": ["docs/TODO.md"]
    }
  ]
}
```

Allowed draft types:

```text
idea, decision, action, question, constraint, preference, artifact, reflection
```

Allowed origins:

```text
user, assistant, mixed, unknown
```

Allowed statuses:

```text
draft, reviewed, accepted, rejected, speculative, stale
```

## Verification

`mos verify` validates:

- required run files;
- task, handoff, run state, memory draft, final report schemas;
- event taxonomy and run id consistency;
- run state artifact references;
- provider result schemas.

This protocol is the kernel consumed by CLI, TUI, future Desktop, future API, and future MCP.
