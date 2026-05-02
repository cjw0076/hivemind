# Export Parsers Implementation Breakdown

## Scope

Build the MemoryOS export parser layer as deterministic provider adapters that convert raw AI service exports into normalized local records. Parser output feeds the existing import pipeline, pair builder, durable node/edge stores, stats, audit, and later graph/vector layers.

The parser layer must stay below semantic extraction. It should not call an LLM, infer claims, assign concepts, or summarize conversations. Its job is to detect source type, preserve raw provenance, normalize conversations/messages/pairs, report recoverable warnings, and give the next pipeline stages stable input.

## Target Pipeline

```text
raw export file or markdown folder
  -> source detector
  -> provider-specific parser
  -> normalized Conversation / Message / Pair / SourceArtifact objects
  -> import dry-run report
  -> append-only node/edge import with dedupe
  -> audit/stats/reporting
```

## Provider-Specific Tasks

### ChatGPT

- Accept either `conversations.json` directly or an official export ZIP containing `conversations.json`.
- Parse conversation tree structures into stable chronological message order.
- Preserve conversation raw ID, title, create/update timestamps when present, message raw IDs, roles, model metadata, content parts, and original mapping parent/child structure if available.
- Handle missing titles, missing timestamps, deleted messages, empty content parts, multimodal placeholders, tool/system messages, and branchy conversation trees.
- Emit parser warnings for skipped malformed messages instead of failing the whole import.
- Add redacted fixtures for:
  - single-turn user/assistant conversation;
  - multi-turn linear conversation;
  - branched or interrupted conversation;
  - attachment, image, file, tool, or non-text placeholder;
  - malformed record with missing message/content fields.
- Acceptance target: stable conversation/message/pair counts, stable role order, stable source archive hash, stable raw message IDs, and no duplicate nodes after re-import.

### DeepSeek

- Support ZIP exports containing `conversations.json` with observed `mapping[].message.fragments`.
- Normalize fragments into a single text field while preserving fragment count and raw fragment type when available.
- Handle missing fragments, null message objects, unknown roles, empty conversations, and provider format drift.
- Keep the parser tied to the observed local format, but make unsupported shapes produce explicit warnings with archive/member path context.
- Add fixtures from a small redacted sample of the current local structure.
- Acceptance target: parser matches known local export counts, preserves role sequence, and warning behavior is covered by malformed fixture tests.

### Grok

- Support ZIP exports containing `prod-grok-backend.json`.
- Detect conversation records and message records from the known local export structure.
- Preserve provider raw IDs, timestamps, role labels, model labels, and any thread/title fields present.
- Convert unsupported/non-chat records into source artifacts or warnings rather than silently dropping them.
- Add fixtures from a small redacted sample of the current local structure.
- Acceptance target: stable counts for conversations/messages/pairs and deterministic handling of unknown record types.

### Perplexity

- Support ZIP archives of markdown/text thread files.
- Treat each thread file as a source artifact and derive a conversation from filename plus file metadata.
- Parse markdown into observations/messages conservatively. If role markers are absent, preserve content as markdown observations rather than inventing user/assistant turns.
- Support manual thread exports first; do not depend on unofficial scraping.
- Add fixtures for:
  - one clearly marked user/assistant thread;
  - one plain markdown research note;
  - one multi-section thread with citations or links;
  - one malformed or empty text file.
- Acceptance target: no fabricated role labels, stable source file references, and markdown content preserved even when pair extraction is impossible.

### Gemini

- Add only after a sample Google Takeout export is available.
- Source detector should recognize Takeout ZIP structures likely to contain Gemini Apps Activity, but should not claim support until fixtures exist.
- Parser should be defensive because Takeout may expose HTML, JSON, or activity-log oriented records depending on account and settings.
- Initial implementation tasks:
  - inventory actual Takeout archive paths from sample;
  - identify Gemini Apps Activity records and Gems records separately;
  - parse user prompt, model response, timestamp, generated media/upload references, and raw activity IDs where present;
  - preserve records that cannot be reliably paired as source artifacts with warnings.
- Add fixtures after sample collection:
  - JSON activity record;
  - HTML activity record;
  - upload/generated-media reference;
  - missing or partial activity record.
- Acceptance target: parser does not overfit a single Takeout shape, warnings identify exact archive members, and unsupported records remain traceable.

### Claude

- Add only after a sample official export is available.
- Support official export first; support manual markdown as a separate manual/markdown parser path.
- Parser tasks after sample collection:
  - identify top-level conversation/thread schema;
  - preserve raw conversation IDs, project/workspace fields if present, message IDs, roles, timestamps, model labels, attachments, and file references;
  - handle missing self-service exports by documenting manual import fallback rather than scraping.
- Add fixtures after sample collection:
  - single-turn official export;
  - multi-turn official export;
  - project/file/attachment conversation if available;
  - malformed record.
- Acceptance target: official export import is reproducible, manual markdown imports are clearly marked as manual provenance, and parser does not mix official and manual source semantics.

### Manual Markdown / Text

- Keep markdown/text import as a first-class fallback for Claude, Perplexity, session logs, and curated research notes.
- Preserve file path, file hash, imported-at timestamp, parser name/version, and line-span provenance for each emitted observation/message where feasible.
- Use explicit role markers only; otherwise import as observations without user/assistant pairing.
- Acceptance target: no semantic claims are extracted by the parser itself, and line/file provenance is available for later critique/audit.

## Parser Contracts

### Source Detection Contract

Each import must produce a source detection result before parsing:

```text
SourceDetection {
  source_type: chatgpt | deepseek | grok | perplexity | gemini | claude | markdown | unknown
  confidence: exact | likely | weak | unknown
  matched_paths: list of archive/file paths
  warnings: list of ParserWarning
}
```

Rules:

- Exact detection requires a provider-specific filename or schema marker.
- Likely detection may suggest a parser but must be overridable by source hint.
- Unknown detection must fail cleanly before import append, unless the user explicitly imports as markdown/text.
- Detection must not inspect files outside the provided import target.

### Parser Input Contract

Every parser receives:

```text
ParserInput {
  import_run_id: string
  source_hint: optional string
  raw_file_path: string
  raw_archive_sha256: string
  archive_member_path: optional string
  parser_options: object
}
```

Rules:

- Use archive-safe reads only; never extract untrusted ZIPs into arbitrary filesystem paths.
- Hash the raw archive/file before parsing.
- Keep local-only parsing as the default behavior.
- Parser options may control strictness, redaction preview, and whether to include non-chat artifacts.

### Normalized Output Contract

Each parser emits:

```text
ParsedExport {
  parser_name: string
  parser_version: string
  source_type: string
  import_run_id: string
  raw_archive_sha256: string
  source_artifacts: SourceArtifact[]
  conversations: Conversation[]
  messages: Message[]
  pairs: Pair[]
  warnings: ParserWarning[]
  counts: ParsedCounts
}
```

Required normalized records:

```text
Conversation {
  id: stable MemoryOS ID
  source_type: string
  raw_id: optional string
  title: optional string
  created_at: optional timestamp
  updated_at: optional timestamp
  source_artifact_id: string
  parser_name: string
  parser_version: string
  import_run_id: string
  raw_archive_sha256: string
}

Message {
  id: stable MemoryOS ID
  conversation_id: string
  source_type: string
  raw_id: optional string
  role: user | assistant | system | tool | unknown
  text: string
  model: optional string
  created_at: optional timestamp
  turn_index: integer
  source_artifact_id: string
  raw_path: optional string
  raw_offset: optional string
  parser_name: string
  parser_version: string
  import_run_id: string
  raw_archive_sha256: string
}

Pair {
  id: stable MemoryOS ID
  conversation_id: string
  source_type: string
  input_message_id: string
  output_message_id: string
  turn_index: integer
  pair_type: one_hop
  parser_name: string
  parser_version: string
  import_run_id: string
  raw_archive_sha256: string
}

SourceArtifact {
  id: stable MemoryOS ID
  source_type: string
  raw_file_path: string
  raw_archive_sha256: string
  archive_member_path: optional string
  member_sha256: optional string
  media_type: optional string
  parser_name: string
  parser_version: string
  import_run_id: string
}

ParserWarning {
  code: string
  severity: info | warning | error
  message: string
  source_type: string
  raw_file_path: string
  archive_member_path: optional string
  raw_id: optional string
  recoverable: boolean
}
```

Pair rules:

- Build only nearest `user -> assistant` pairs in parser or immediately after normalized message ordering.
- Do not create pairs across conversations.
- Do not create pairs from unknown/manual observations unless role markers are explicit.
- Preserve non-paired messages as messages, not as failures.
- Contextual and trajectory pairs are later-stage products, not parser output for this work item.

ID rules:

- Stable IDs should derive from source type, raw archive hash, provider raw ID when available, archive member path, and turn index fallback.
- Re-importing the same raw export must generate the same IDs.
- Parser version changes must be recorded but should not alone duplicate nodes unless the normalized identity changed.

## Import Reliability Tasks

1. Add parser warnings.
   - Replace all-or-nothing failures on malformed records with structured `ParserWarning` entries.
   - Keep hard failures for unreadable archives, unsupported source type, corrupt ZIP central directory, and invalid parser contract output.
   - Surface warning counts in `memoryos import --dry-run`, normal import, `stats`, and audit JSON reports.

2. Add source artifacts.
   - Create `SourceArtifact` records for raw archive members, direct JSON files, markdown files, attachments, and unsupported but preserved records.
   - Link every Conversation, Message, Pair, node, and edge back to at least one source artifact.
   - Include exact archive path and internal filename when applicable.

3. Store parser metadata everywhere.
   - Add `parser_name` and `parser_version` to imported node/edge metadata.
   - Use semantic parser versions such as `chatgpt_export_v1`.
   - Include parser metadata in dry-run output and audit snapshots.

4. Strengthen deduplication.
   - Deduplicate imports by raw archive/file hash plus raw conversation/message IDs where available.
   - Fall back to source type, archive member path, content hash, and turn index for manual files.
   - Treat re-import of the same file as idempotent.
   - Report duplicate counts in dry-run before append.

5. Add import run manifests.
   - Each import run should write or emit a manifest containing import run ID, source detection result, parser version, raw hashes, parsed counts, warning counts, duplicate counts, and appended counts.
   - The manifest is the reconciliation point between raw exports, normalized records, and graph nodes/edges.

6. Keep raw access constrained.
   - Ingestion code can read raw exports.
   - Downstream audit/search/agent code should consume normalized records and source references, not raw archives directly.
   - Add a later deletion command for raw exports without breaking normalized provenance.

7. Add redaction preview path.
   - Provide import preview counts plus sampled redacted snippets before append.
   - Redaction preview should not mutate source text or parser output by default; it is a user-facing review layer.

## Fixture Plan

### Directory Layout

```text
tests/fixtures/exports/
  chatgpt/
    single_turn/
    multi_turn/
    branch_or_non_text/
    malformed/
  deepseek/
    single_turn/
    multi_turn/
    malformed/
  grok/
    single_turn/
    multi_turn/
    unknown_record/
  perplexity/
    marked_thread_zip/
    plain_markdown_zip/
    citations_zip/
    malformed_zip/
  gemini/
    pending_sample/
  claude/
    pending_sample/
```

### Fixture Requirements

- Fixtures must be small, redacted, and synthetic where possible.
- If a fixture is derived from a real local export, remove names, account identifiers, emails, private project details, file IDs, URLs that expose private data, and long content.
- Keep enough structural fidelity that parser behavior is tested against provider-specific shape.
- Store expected outputs as compact count snapshots:

```text
expected.json
  source_type
  parser_name
  conversations
  messages
  pairs
  source_artifacts
  warnings
  role_order
  duplicate_count_on_second_import
```

- Do not require semantic extraction assertions in parser fixtures.
- Include malformed fixtures for warnings and partial success.
- Include at least one fixture per currently supported provider before changing parser internals.

### Fixture Test Matrix

For each fixture:

- source detection returns expected source type;
- parser emits valid contract object;
- counts match expected snapshot;
- role order matches expected snapshot;
- all records include `import_run_id`, raw hash, parser name, parser version, and source artifact ID;
- malformed records emit warnings with archive/member path;
- dry-run reports the same counts without appending;
- importing the same fixture twice is idempotent;
- audit/stats can consume the imported records without crashing.

## Source Provenance Requirements

Provenance is mandatory because MemoryOS needs to distinguish user-originated statements, AI-originated statements, manual notes, provider exports, and later extracted claims.

Required provenance fields:

- `source_type`: provider or manual source.
- `raw_archive_sha256`: hash of raw import file or direct file.
- `source_artifact_id`: normalized artifact record ID.
- `archive_member_path`: internal ZIP member path when present.
- `raw_id`: provider conversation/message ID when present.
- `raw_path` or `raw_offset`: JSON path, markdown line span, or equivalent locator when feasible.
- `import_run_id`: import execution ID.
- `parser_name` and `parser_version`: exact adapter used.
- `role`: user, assistant, system, tool, unknown.
- `origin`: user-originated, AI-originated, provider-generated, manual, or unknown where the schema supports it.

Graph/source linkage:

- `Conversation` nodes link to `SourceArtifact`.
- `Message` nodes link to `Conversation` and `SourceArtifact`.
- `Pair` nodes link to input/output `Message` nodes and inherit source provenance.
- Extracted claims, decisions, assumptions, questions, tasks, concepts, and edges must later cite source message/pair IDs rather than only raw text.

## Acceptance Checks

### Parser Contract Acceptance

- Every parser can be run through the same contract validation helper.
- No parser emits records without source type, import run ID, raw hash, parser name, parser version, and source artifact reference.
- Unsupported provider files fail with a clear source detection error before append.
- Recoverable malformed records become warnings and partial parsed output.
- Parser output is deterministic for the same fixture.

### Import Acceptance

- `memoryos import --dry-run <fixture>` reports conversations, messages, pairs, source artifacts, warnings, duplicates, and would-append counts.
- A real import appends expected normalized nodes/edges.
- Re-importing the same fixture appends nothing new and reports duplicates.
- `memoryos stats` includes platform, role, conversation, pair, source, warning, and parser-version counts.
- `memoryos audit --json` can include parser/import warning snapshots under `runs/reports/`.

### Fixture Acceptance

- Redacted fixtures exist for ChatGPT, DeepSeek, Grok, and Perplexity before parser refactors.
- Gemini and Claude fixture directories remain pending until sample exports are available.
- Each supported provider has at least one malformed fixture.
- Snapshot counts are stable and intentionally updated only when parser contract changes.

### Provenance Acceptance

- Every imported node/edge can be traced to an import run and source artifact.
- Exact archive path and internal filename are preserved when applicable.
- Parser version is visible on imported metadata.
- User-originated and AI-originated messages are distinguishable by role/origin fields.
- Manual markdown records are not misrepresented as official provider exports.

## Risks

- Provider format drift: ChatGPT, DeepSeek, Grok, Gemini, Claude, and Perplexity may change export schemas without notice. Mitigation: fixture snapshots, warning-first parsing, parser versions, and source detection confidence.
- Overfitting local samples: DeepSeek and Grok support is based on current observed local structures. Mitigation: small contract surface, unsupported-shape warnings, and adding new fixtures before parser changes.
- Gemini Takeout variability: Takeout can expose HTML, JSON, activity records, generated media, and uploads in account-dependent layouts. Mitigation: wait for real sample, preserve unparsed source artifacts, and avoid claiming complete support early.
- Claude export availability: official export shape may be unavailable or inconsistent. Mitigation: support manual markdown separately and mark provenance accurately.
- Pair fabrication: markdown/manual imports may not contain reliable roles. Mitigation: only pair explicit user/assistant turns.
- Silent data loss: unsupported attachments, deleted messages, tool calls, or unknown records could be dropped. Mitigation: source artifacts and warnings for preserved-but-unparsed records.
- Duplicate graph growth: re-imports can inflate memory if IDs are unstable. Mitigation: raw hashes, raw IDs, source artifact IDs, and duplicate dry-run reporting.
- Privacy leakage: fixtures and raw exports may contain sensitive personal/project data. Mitigation: redacted fixtures, local-only parsing, redaction preview, and raw export deletion path.
- Parser/extraction boundary creep: LLM extraction inside parsers would make imports nondeterministic. Mitigation: contract tests that assert parser output is structural only.
- Provenance gaps: later audit and disagreement workflows become weak if source fields are optional. Mitigation: contract validation fails records without required provenance.

## Implementation Order

1. Add shared parser contract types and validation.
2. Add `SourceArtifact` records and provenance fields to normalized outputs.
3. Add parser warning collection and dry-run warning reporting.
4. Add parser name/version metadata to all imported records.
5. Add fixture directory and expected snapshot format.
6. Add ChatGPT fixture tests.
7. Add DeepSeek fixture tests.
8. Add Grok fixture tests.
9. Add Perplexity markdown ZIP fixture tests.
10. Add idempotent re-import tests for every supported fixture.
11. Add import run manifest output.
12. Add user-facing export instructions for ChatGPT, DeepSeek/Grok local exports if relevant, Perplexity manual markdown, Gemini Takeout, and Claude official/manual paths.
13. Add Gemini parser only after sample export fixture exists.
14. Add Claude parser only after sample official export fixture exists.

## Done Definition

This work item is done when MemoryOS can import supported provider fixtures through a deterministic, warning-tolerant, provenance-complete parser layer; dry-run can preview counts and duplicates; re-imports are idempotent; parser fixtures cover normal and malformed records; and every normalized conversation/message/pair can be traced back to a raw archive/file, archive member path, parser version, and import run.
