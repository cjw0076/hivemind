# MemoryOS Export Parsers

MemoryOS should treat each AI service export as an adapter with a stable contract:

```text
raw export file
  -> platform-specific parser
  -> normalized Conversation / Message / Pair objects
  -> graph extraction
```

## Current Parser Coverage

| Source | Current input | Status |
| --- | --- | --- |
| ChatGPT | `conversations.json` or export ZIP containing it | Implemented structurally, needs fixture test |
| DeepSeek | ZIP containing `conversations.json` with `mapping[].message.fragments` | Implemented for current local export |
| Grok | ZIP containing `prod-grok-backend.json` | Implemented for current local export |
| Perplexity | ZIP of markdown/text thread files | Implemented as markdown observations |
| Gemini | Google Takeout | Not implemented |
| Claude | official export or manual markdown | Not implemented |

## Parser Contract

Each parser should emit:

- `Conversation`: platform, raw ID, title, created time.
- `Message`: role, text, model, created time, turn index.
- `Pair`: nearest user message followed by assistant message.
- `Source`: exact archive path and internal filename when applicable.

The parser should not call an LLM. Extraction of claims, concepts, and tasks is a later stage.

## Test Fixtures

Add small redacted fixtures under:

```text
tests/fixtures/exports/
```

Recommended fixture per platform:

- one single-turn conversation;
- one multi-turn conversation;
- one conversation with attachments or non-text content;
- one malformed or partially missing record.

The success condition is stable counts and stable role order, not perfect semantic extraction.

## Product Notes

Export parsers are a product surface, not just ETL code. A usable app also needs:

- export instructions for each provider;
- privacy warning before upload;
- local-only parsing option;
- redaction preview;
- parser version stored on imported nodes;
- re-import deduplication by source archive hash and raw message ID.
