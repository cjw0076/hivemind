# Claude Shared Vision

This file is the compact handoff from Codex to Claude for the current MyWorld / MemoryOS direction.

## Core Vision

MemoryOS is not just a memory database. It is one layer in a Human-AI-Agent Operating Stack:

```text
Human intent
  -> Chatbot Harness
  -> Deliberation Layer
  -> MemoryOS <-> CapabilityOS
  -> Agent Handoff
  -> Agent Harness
  -> Execution Agents
  -> Verifier / Discriminator
  -> MemoryOS + CapabilityOS update
  -> better next action
```

Short roles:

- MemoryOS remembers decisions, project state, conversations, evidence, disagreements, artifacts, and agent runs.
- CapabilityOS maps tools, models, MCP servers, workflows, quality tiers, risks, and legacy comparisons.
- Surfer discovers new external signals: tools, repos, papers, docs, changelogs, and community workflows.
- Discriminator judges value, risk, novelty, production readiness, and legacy superiority.
- Chatbot Harness refines thought before execution.
- Agent Harness executes through Codex, Claude Code, local agents, tools, tests, and repo edits.
- Verifier checks whether outputs satisfy constraints, tests, safety, and user intent.

The closed loop is:

```text
Discover -> Judge -> Remember -> Deliberate -> Specify -> Execute -> Verify -> Learn -> Recommend
```

## Local LLM Runtime

The local model layer should behave like a provider runtime, not a loose collection of model calls. Codex implemented the first role-based harness in `memoryos local`.

Current local models:

- `qwen3:1.7b`: micro router/classifier only. Use for short tags, routing, duplicate candidates, and shallow JSON.
- `qwen3:8b`: default structured worker. Use for memory extraction, context compression, capability drafts, and handoff drafts.
- `deepseek-coder:6.7b`: coding/log worker. Use for test logs, stack traces, parser drafts, and code summaries.
- `deepseek-coder-v2:16b`: stronger local reasoning/code review worker. Use for handoff drafts, diff review, implementation option comparison, and local review before Claude.
- Claude/Codex: final judgment, architecture, implementation, integration, and user-facing synthesis.

Role commands:

```bash
python -m memoryos.cli local classify --input docs/local_llm_use.md
python -m memoryos.cli local extract-memory --input docs/local_llm_use.md
python -m memoryos.cli local extract-capability --input docs/local_llm_use.md
python -m memoryos.cli local compress-context --input runs/work_items/INTEGRATED_EXECUTION_PLAN.md
python -m memoryos.cli local draft-handoff --input runs/work_items/INTEGRATED_EXECUTION_PLAN.md --complexity strong
python -m memoryos.cli local summarize-log --input runs/work_items/INTEGRATED_EXECUTION_PLAN.md
python -m memoryos.cli local review-diff --input runs/local_workers/diff.txt --complexity strong
```

Workspace-local Ollama:

```bash
scripts/start-ollama-local.sh
scripts/ollama-local.sh list
```

## Claude Role

Claude should not reprocess raw bulk context by default. Ask MemoryOS/local workers for compact context packs, then focus on:

- conceptual discipline;
- architecture and product judgment;
- detecting overclaims;
- clarifying assumptions and risks;
- resolving disagreements;
- deciding whether local-worker drafts are worth committing.

Local output is always draft, never authority:

```text
local output = candidate
Claude output = judge / critique
user + harness = commit authority
```

Escalate to Claude when local confidence is low, when schema or architecture changes are involved, when security/privacy risk appears, when workers disagree, or when final prose/strategy matters.

## Current Implementation Boundary

Keep the near-term substrate explicit and file-first:

```text
input markdown/session log
  -> extract claims, decisions, assumptions, TODOs
  -> store as durable nodes
  -> link evidence and disagreements
  -> run critique/audit pass
  -> emit next actions and unresolved questions
```

Do not turn the system into a large UI, database, or swarm before this substrate is stable.

## Claim Discipline

Allowed as project language:

- Generative Truth Engine
- Dipeen
- GoEN
- Asimov
- mechanical truth-seeking system
- multi-ontology

Do not treat these as proven scientific claims. Keep the distinction between vision, implementation, evidence, and speculation explicit.
