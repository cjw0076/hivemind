# MyWorld Docs Route

This route keeps agents from rereading the full source vault unless needed.

## Fast Start

Read these first for current implementation work:

1. `../AGENTS.md` - workspace rules, boundaries, logging, claim discipline.
2. `../.ai-runs/shared/COMPACT_HANDOFF.md` - latest compact-safe implementation state.
3. `../.ai-runs/shared/comms_log.md` - chronological decisions and agent handoffs.
4. `NORTHSTAR.md` - product and research direction.
5. `VISION_GRAPH.md` - graph-like map from vision nodes to source docs and TODO surfaces.
6. `LOWERCASE_SOURCE_GRAPH.md` - graph map for lowercase source-vault docs.
7. `ROADMAP.md` - phase order.
8. `TODO.md` - active work queue.
9. `TUI_HARNESS.md` - current `mos` CLI/TUI harness.
10. `PROVIDER_HARNESS_GUIDE.md` - Claude/Codex/Gemini/local/provider usage.

## Current Build Surface

Use these when changing code:

- `MEMORYOS_MVP.md` - local-first MemoryOS loop and CLI boundary.
- `ARCHITECTURE.md` - object model and guardrails.
- `EXPORT_PARSERS.md` - import adapter contract.
- `LOCAL_LLM_WORKERS.md` - local worker roles, routing, escalation.
- `LOCAL_LLM_INVENTORY.md` - local hardware/runtime/model state.
- `PROVIDER_MODELS.md` - provider routing policy.
- `OPEN_MODEL_PROVIDER_SURVEY.md` - external provider candidates.
- `cli_help.md` - local captured CLI help for Claude, Gemini, Codex.
- `make_production.md` - installable `mos` target.

## Product Vision

Use these for product planning and UX direction:

- `final.md` - Human-AI-Agent Operating Stack.
- `tui.md` - wrapper CLI/TUI and artifact blackboard direction.
- `ui_future.md` - future chatbot/agent harness and visual product framing.
- `image.png` - visual board reference.
- `capabilityOS.md` - CapabilityOS concept and capability graph.
- `agent_society.md` - agent self-improvement and routing society.
- `ecosystem.md` - broader field/ecosystem model.
- `for_future_agent.md` - future capability/package protocol direction.
- `optima.md` - storage, source graph, and discrimination principles.
- `word.md` - technical lexicon.
- `LOWERCASE_SOURCE_GRAPH.md` - graph map for lowercase source docs and canonicalization targets.

## Research And Source Vault

Do not read these fully by default. Prefer the split mirrors under `docs/split/` once available.

- `my_world.md` - largest raw MyWorld source context.
- `memoryOS.md` - raw MemoryOS source discussion and implementation handoffs.
- `goen_resonance.md` - GoEN/Dipeen/ontology-plasticity framing.
- `MYWORLD_IDEA_EXCERPTS.md` - curated excerpts and guardrails extracted from `my_world.md`.
- `SOURCE_LINKS.md` - source inventory.
- `VISION_GRAPH.md` - source-to-work graph for the current product/research vision.
- `LOWERCASE_SOURCE_GRAPH.md` - source-vault route for lowercase docs.

## Split Mirrors

Large files should be split without deleting originals:

```text
docs/split/my_world/
docs/split/memoryOS/
docs/split/goen_resonance/
```

Each split directory should contain:

- `index.md` - route for the source.
- `part-*.md` - smaller chunks in source order.
- provenance at the top of each part: original path and line or byte range where practical.

## Logging Rule

Any meaningful docs route change, split, implementation decision, or critique must be logged in:

```text
../.ai-runs/shared/comms_log.md
```
