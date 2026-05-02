# MyWorld Agent Entry

This directory is the MyWorld / multi-ontology agent-system workspace.

Read these first:

1. `docs/MYWORLD_IDEA_EXCERPTS.md`
2. `docs/ROUTE.md`
3. `docs/VISION_GRAPH.md`
4. `docs/LOWERCASE_SOURCE_GRAPH.md`
5. `docs/ARCHITECTURE.md`
6. `docs/PROVIDER_MODELS.md`
7. `docs/CLAUDE_SHARED_VISION.md`
8. `.ai-runs/shared/COMPACT_HANDOFF.md`
9. `.ai-runs/shared/comms_log.md`

## Current Boundary

`/home/user/workspaces/jaewon/universe/quantum` is the quantum Paper #4 / P18 workspace.

`/home/user/workspaces/jaewon/myworld` is the agent memory, ontology graph, reflective critique, and multi-agent research OS workspace.

Do not modify quantum experiments from here unless the user explicitly asks.

## Working Roles

- User: final direction, taste, acceptance, and project boundary.
- Codex: implementation, filesystem state, scripts, reproducible logs.
- Claude: critique, reviewer voice, conceptual risk, claim discipline.
- Other models: alternative framings, external pressure tests, provider/model comparison.

The goal is not agreement by default. The goal is logged disagreement, resolution, and next action.

## Required Logging

When a session makes a meaningful decision, file change, experiment, or critique, append a short entry to:

```text
.ai-runs/shared/comms_log.md
```

Recommended format:

```text
## YYYY-MM-DD HH:MM KST - Agent

- Context:
- Decision:
- Evidence:
- Next:
```

## Immediate MyWorld MVP

Build the smallest useful loop:

```text
input markdown/session log
  -> extract claims, decisions, assumptions, TODOs
  -> store as durable nodes
  -> link evidence and disagreements
  -> run critique/audit pass
  -> emit next actions and unresolved questions
```

Prefer explicit files and schemas first. Add databases, web UI, and agent swarm orchestration only after the memory/graph/log substrate is stable.

## Claim Discipline

Allowed in MyWorld design docs:

- Generative Truth Engine
- Dipeen
- GoEN
- Asimov
- mechanical truth-seeking system
- multi-ontology

Not allowed as scientific claims without evidence:

- “solves truth”
- “first framework”
- “fractal boundary”
- tetration/power-tower as an anchor for quantum identifiability

Keep vision prose out of Paper #4 drafts.
