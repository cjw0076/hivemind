# MemoryOS MVP

MemoryOS is the local-first memory layer for MyWorld. The product vision in `docs/image.png` should sit on top of a smaller substrate:

```text
AI exports / markdown logs
  -> normalized observations, messages, and input-output pairs
  -> extracted claims, decisions, assumptions, questions, tasks, concepts
  -> append-only memory graph
  -> audit report for next actions and unresolved questions
```

## Current Scope

The first version supports:

- Markdown or text import.
- ChatGPT `conversations.json` or export ZIP import.
- DeepSeek export ZIP import for the observed `mapping/fragments` format.
- Grok export ZIP import for the observed `prod-grok-backend.json` format.
- Perplexity markdown ZIP import.
- JSONL node and edge stores.
- Deterministic local extraction.
- Audit summaries for counts, concepts, sample decisions, tasks, and questions.

It intentionally does not require Neo4j, vector DBs, embeddings, or model API keys yet.

## Commands

```bash
python -m memoryos.cli import docs/memoryOS.md docs/goen_resonance.md
python -m memoryos.cli audit --out runs/reports/latest_audit.md
python -m memoryos.cli stats
```

For a ChatGPT export:

```bash
python -m memoryos.cli import memory/raw/chatgpt_export.zip
```

For the current local exports:

```bash
python -m memoryos.cli import data/deepseek_data-2026-05-01.zip data/grok_session_data.zip data/perplexity_session_data.zip
```

Preview an import without appending:

```bash
python -m memoryos.cli import --dry-run data/deepseek_data-2026-05-01.zip
```

## Next Build Steps

1. Add deduplication and source versioning.
2. Add redacted parser fixtures and tests for every supported export format.
3. Add manual review states: accepted, rejected, speculative, stale.
4. Add embedding generation behind a provider/local-runtime adapter.
5. Add a lightweight local API for the visual board.
6. Add Neo4j/Postgres export only after the file substrate stabilizes.
