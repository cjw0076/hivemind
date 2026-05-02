# MemoryOS Core Substrate Implementation Breakdown

## Scope

The core substrate is the local-first MemoryOS layer that turns raw notes and AI exports into durable, traceable, reviewable memory graph records.

It should remain useful without a database server, vector DB, hosted model key, or UI. Later API, board, semantic search, hypergraph, and agent features should read from this stable file substrate instead of replacing it.

## Goals

1. Preserve every source artifact with enough provenance to trace any node or edge back to the original file, archive member, parser, import run, and content hash.
2. Normalize heterogeneous inputs into stable records: observations, conversations, messages, pairs, concepts, claims, decisions, assumptions, questions, tasks, evidence, uncertainty, branches, projects, and ontology nodes.
3. Store graph state as append-only JSONL with deterministic IDs, deduplication, and explicit import metadata.
4. Keep raw text, normalized records, extracted memory nodes, graph edges, review state, and audit reports distinguishable.
5. Make uncertainty, unsupported claims, disagreements, source role, and user-versus-AI provenance first-class fields.
6. Provide a CLI loop for import, dry-run, stats, audit, review, search-by-keyword, and graph inspection.
7. Emit repeatable reports that support manual review: unsupported claims, unresolved questions, stale decisions, duplicate concepts, repeated tasks, and next actions.
8. Defer embeddings, local API, visual board, Neo4j/Postgres export, and swarm orchestration until the file substrate is stable.

## Non-Goals For This Work Item

- No web UI.
- No external database requirement.
- No vector search dependency.
- No hosted LLM dependency.
- No quantum workspace edits.
- No scientific claims beyond implementation behavior.
- No destructive migration of existing JSONL files without an explicit backup and migration command.

## Proposed File And Module Layout

```text
memoryos/
  __init__.py
  cli.py
  schema.py
  ids.py
  time.py
  jsonl.py
  importers/
    __init__.py
    base.py
    markdown.py
    chatgpt.py
    deepseek.py
    grok.py
    perplexity.py
    claude.py
    gemini.py
  extraction/
    __init__.py
    chunking.py
    heuristics.py
    labels.py
  graph/
    __init__.py
    store.py
    dedupe.py
    edges.py
    review.py
    migrations.py
  audit/
    __init__.py
    reports.py
    checks.py
  search/
    __init__.py
    keyword.py
  tests/
    fixtures/
      exports/
      redacted/

memory/
  raw/
  processed/
    import_runs.jsonl
    source_artifacts.jsonl
    nodes.jsonl
    reviews.jsonl

ontology/
  edges.jsonl
  proposed_edits.jsonl
  graph_commits.jsonl
  disagreements.jsonl

runs/
  reports/
    latest_audit.md
    audit_YYYYMMDD_HHMMSS.json
  work_items/
    core_substrate.md
```

The exact package layout can adapt to the existing code, but the boundaries should remain: importers parse source formats, extraction labels memory objects, graph modules own IDs/dedup/review/edges, audit modules report graph quality, and CLI commands orchestrate those pieces.

## Core Schemas

### ImportRun

Purpose: one record per import attempt.

Fields:

- `id`: deterministic or generated import run ID.
- `started_at`, `finished_at`.
- `inputs`: list of input paths or archive members.
- `mode`: `append` or `dry_run`.
- `parser_results`: counts and warnings by parser.
- `node_count`, `edge_count`, `skipped_count`, `duplicate_count`.
- `status`: `completed`, `completed_with_warnings`, or `failed`.

### SourceArtifact

Purpose: durable source pointer for every node and edge.

Fields:

- `id`: deterministic hash over archive hash, member path, and content hash.
- `source_path`: local input path.
- `archive_hash`: hash of the source archive when applicable.
- `member_path`: path inside ZIP/export when applicable.
- `content_hash`: hash of normalized source content.
- `media_type`: markdown, json, txt, zip member, unknown.
- `provider`: manual, ChatGPT, DeepSeek, Grok, Perplexity, Claude, Gemini, unknown.
- `parser_name`, `parser_version`.
- `import_run_id`.
- `created_at`.

### Node

Purpose: append-only memory object.

Required fields:

- `id`: deterministic stable ID where possible.
- `type`: observation, conversation, message, pair, concept, claim, decision, assumption, question, task, evidence, uncertainty, branch, project, ontology_node.
- `text`: normalized content or short canonical label.
- `status`: `new`, `reviewed`, `accepted`, `rejected`, `speculative`, or `stale`.
- `source_artifact_id`.
- `source_span`: line, character, message index, archive member, or provider-specific pointer.
- `import_run_id`.
- `created_at`.
- `updated_at`.
- `provenance`: `user_originated`, `ai_originated`, `mixed`, `system`, or `unknown`.
- `provider`, `role`, `model`.
- `metadata`: parser-specific and type-specific data.

Type-specific fields:

- Claim: `evidence_state`, `confidence`, `reviewer`, `review_time`, `temporal_scope`.
- Task: `owner`, `task_status`, `due_context`, `next_action`.
- Decision: `decision_state`, `supersedes`, `stale_reason`.
- Question: `question_status`, `recurrence_count`.
- Branch: `branch_group_id`, `interpretation`, `collapse_status`.
- Project: `project_key`, `aliases`.

### Edge

Purpose: typed relation between memory objects.

Fields:

- `id`: deterministic hash over relation, endpoints, source, and optional qualifier.
- `type`: supports, contradicts, derives_from, implements, tests, remembers, compresses, schedules, depends_on, generalizes, specializes, mentions, belongs_to_project, answers, asks, follows_from, duplicates, supersedes.
- `from_id`.
- `to_id`.
- `source_artifact_id`.
- `import_run_id`.
- `confidence`.
- `evidence_ids`.
- `plasticity_score`.
- `last_used`.
- `metadata`.

### Hyperedge

Purpose: represent multi-node events without forcing everything into binary edges.

Initial representation can be a node of type `hyperedge_event` plus typed participant edges.

Fields:

- `id`.
- `event_type`: decision_event, contradiction_event, evidence_bundle, task_plan, branch_set.
- `participant_ids`.
- `role_map`: participant ID to event role.
- `source_artifact_id`.
- `confidence`.
- `metadata`.

## Concrete Tasks

### 1. Schema Hardening

- Define canonical enums for node types, edge types, statuses, provenance, evidence state, roles, and providers.
- Add typed schema constructors or dataclasses in `memoryos/schema.py`.
- Add schema validation before appending records.
- Ensure schema validation returns recoverable warnings for bad records during import.
- Add parser name and parser version to every imported node and edge.
- Add source archive hash and source content hash to import metadata.
- Add user-originated versus AI-originated provenance fields to messages, pairs, claims, decisions, questions, and tasks.
- Add review statuses to nodes.
- Add relation confidence, evidence list, plasticity score, and last-used fields to edges.
- Add a first hyperedge representation for multi-node events.

Dependencies:

- Existing JSONL store.
- Existing import run ID and source hash logic.

Acceptance checks:

- `memoryos import --dry-run` validates records without appending.
- Every appended node has `id`, `type`, `status`, `source_artifact_id`, `import_run_id`, and provenance fields.
- Every appended edge has `id`, `type`, endpoints, `source_artifact_id`, and `import_run_id`.
- Malformed records produce warnings and skipped counts, not full import failure.
- Re-imported files do not create uncontrolled duplicate nodes or edges.

### 2. Source Artifact Registry

- Add `memory/processed/source_artifacts.jsonl`.
- Create one SourceArtifact per raw file or archive member.
- Link all parsed observations, conversations, messages, pairs, nodes, and edges to SourceArtifact IDs.
- Store archive-level hash separately from member-level content hash.
- Record parser name and version at the artifact level and copy key parser metadata into node metadata.
- Add source pointer helpers for markdown line spans, JSON paths, conversation IDs, message IDs, and archive member paths.

Dependencies:

- Hash utilities.
- Importer base interface.

Acceptance checks:

- Given a node ID, a CLI or helper can print the original source path/member and source pointer.
- Audit output can count nodes by provider, parser, source artifact, and import run.
- Dry-run reports source artifacts that would be added, duplicated, or skipped.

### 3. Importer Interface And Parser Warnings

- Define a common parser result object with `artifacts`, `records`, `warnings`, and `stats`.
- Update markdown/text importer to emit observations and source spans.
- Update ChatGPT importer for `conversations.json`.
- Update DeepSeek importer for observed `mapping[].message.fragments`.
- Update Grok importer for observed `prod-grok-backend.json`.
- Update Perplexity importer for markdown ZIP bundles.
- Add stub parsers for Claude and Gemini that fail gracefully with a clear unsupported-format warning until samples exist.
- Add parser fixture directory under `tests/fixtures/exports/`.
- Add redacted fixtures for each supported provider.
- Ensure malformed or partial provider records are skipped with warnings.

Dependencies:

- SourceArtifact registry.
- Schema validation.

Acceptance checks:

- Each supported provider has at least one redacted fixture.
- Tests cover role order, timestamp handling, message extraction, pair generation, and warning behavior.
- A bad message inside an export does not abort the whole import.
- Parser versions appear in import run metadata.

### 4. Deterministic Extraction Pipeline

- Split extraction into deterministic chunking and labeling.
- Keep deterministic local heuristics as the default labeler.
- Define label types: intent, project, claim, decision, assumption, question, task, concept, evidence, uncertainty, branch.
- Extract intent labels: question, request, critique, idea, decision, reflection, implementation, design, research.
- Extract project labels: Uri, Dipeen, GoEN, North Star, Deepfake, Capstone, MemoryOS, unknown.
- Extract action items with owner, status, source, and due context when present.
- Extract evidence links separately from unsupported claims.
- Preserve ambiguity by emitting branch nodes rather than choosing one interpretation.
- Keep raw message records separate from extracted memory nodes.

Dependencies:

- Normalized messages and pairs.
- Stable node schema.
- Project and branch node support.

Acceptance checks:

- Importing markdown or provider exports creates normalized records and extracted nodes as distinct objects.
- Claims without evidence are marked `evidence_state: unsupported`.
- User-originated questions can be reported separately from assistant suggestions.
- Ambiguous extraction creates branch records with a shared branch group.

### 5. Deduplication And Stable IDs

- Centralize ID generation in `memoryos/ids.py`.
- Use deterministic IDs for source artifacts, messages, pairs, and extracted nodes where source spans are stable.
- Use content fingerprints plus type, source, role, and span to detect duplicates.
- Add duplicate edges for repeated concepts or repeated claims when preserving recurrence is useful.
- Add merge candidates for concepts, repeated claims, and repeated tasks without silently deleting history.
- Track import-run duplicates in dry-run and append modes.

Dependencies:

- SourceArtifact registry.
- Schema constructors.

Acceptance checks:

- Re-importing the same file reports duplicates and does not append uncontrolled copies.
- Similar repeated tasks can be reported as recurrence without losing separate source references.
- Concept dedupe produces reviewable merge candidates, not irreversible automatic merges.

### 6. Review State And Manual Corrections

- Add `memory/processed/reviews.jsonl` as an append-only review overlay.
- Implement `memoryos review` commands for accept, reject, mark speculative, mark stale, and add reviewer notes.
- Keep original extracted nodes immutable; review overlay resolves current effective status.
- Add support for stale decisions and superseding decisions.
- Add CLI filters for `new`, `accepted`, `rejected`, `speculative`, and `stale`.

Dependencies:

- Node status fields.
- Effective state resolver in graph store.

Acceptance checks:

- A user can review important nodes without hand-editing `nodes.jsonl`.
- Audit output distinguishes extracted, reviewed, accepted, rejected, speculative, and stale records.
- Stale decisions include a reason and optional newer supporting node.

### 7. Audit Reports

- Expand audit checks into reusable functions.
- Keep markdown and JSON outputs.
- Add unsupported claim report.
- Add unresolved question report.
- Add stale decision report.
- Add repeated concern report.
- Add duplicate concept report.
- Add repeated task report.
- Add `my ideas only` report using role and provenance.
- Add cross-provider disagreement report using contradiction edges and provider metadata.
- Add next actions derived from active tasks, unresolved questions, unsupported claims, and stale decisions.

Dependencies:

- Review overlay.
- Provenance fields.
- Edge confidence and evidence fields.

Acceptance checks:

- `memoryos audit --out runs/reports/latest_audit.md` emits a readable summary.
- `memoryos audit --json` writes timestamped snapshots under `runs/reports/`.
- Audit counts match `memoryos stats` for nodes, edges, providers, roles, sources, conversations, and pairs.
- Audit reports include source references for every cited node.

### 8. Keyword Search And Graph Inspection

- Add simple local keyword search over node text, metadata, source pointers, and project labels.
- Add graph filters by project, source, role, provider, node type, status, and provenance.
- Add node detail command that prints source pointer, review state, incoming edges, outgoing edges, and evidence links.
- Add graph neighborhood command for project, concept, claim, task, and question nodes.
- Keep this independent of embeddings.

Dependencies:

- Graph store loader.
- Effective status resolver.

Acceptance checks:

- A user can answer "what did I decide and when?" using CLI commands.
- A user can list unresolved MemoryOS questions from user-originated records only.
- A user can inspect evidence linked to a claim without opening raw JSONL by hand.

### 9. Test Fixtures And Regression Suite

- Create redacted fixtures for supported exports.
- Add parser tests for ChatGPT, DeepSeek, Grok, Perplexity, and markdown.
- Add dry-run tests.
- Add re-import dedupe tests.
- Add malformed-record warning tests.
- Add schema validation tests.
- Add audit JSON snapshot shape tests.
- Add review overlay tests.

Dependencies:

- Importer interface.
- Schema validation.

Acceptance checks:

- Parser fixtures do not contain private conversation text.
- Tests prove stable role order and pair generation.
- Tests prove malformed partial records are skipped with warnings.
- Tests prove re-imports are controlled.

### 10. Migration And Compatibility

- Add a schema version field to new records.
- Add a read-time compatibility layer for existing records.
- Add `memoryos migrate --dry-run` for future schema upgrades.
- Avoid rewriting old append-only files unless a migration command is explicitly run.
- When migration is necessary, write migrated output to new files or create timestamped backups first.

Dependencies:

- Schema versioning.
- JSONL readers and writers.

Acceptance checks:

- Existing `nodes.jsonl` and `edges.jsonl` remain readable.
- New commands can load mixed old and new records.
- Migration dry-run reports counts and proposed changes without writing.

## Dependency Order

1. Schema hardening.
2. SourceArtifact registry.
3. Importer interface and parser warning protocol.
4. Stable IDs and deduplication.
5. Deterministic extraction pipeline.
6. Review overlay.
7. Audit expansion.
8. Keyword search and graph inspection.
9. Fixtures and regression tests.
10. Migration support.

Tests should be added alongside each step rather than deferred to the end.

## CLI Surface

```bash
python -m memoryos.cli import INPUT...
python -m memoryos.cli import --dry-run INPUT...
python -m memoryos.cli stats
python -m memoryos.cli audit --out runs/reports/latest_audit.md
python -m memoryos.cli audit --json
python -m memoryos.cli node NODE_ID
python -m memoryos.cli search QUERY --type claim --project MemoryOS --provenance user_originated
python -m memoryos.cli graph NODE_ID --depth 1
python -m memoryos.cli review NODE_ID --status accepted --note "Manually confirmed"
python -m memoryos.cli review NODE_ID --status stale --reason "Superseded by newer decision"
python -m memoryos.cli migrate --dry-run
```

## Acceptance Checks For The Whole Substrate

- Import markdown/text, ChatGPT, DeepSeek, Grok, and Perplexity inputs without external services.
- Dry-run shows counts, warnings, duplicates, source artifacts, nodes, and edges that would be appended.
- Re-importing the same source does not create uncontrolled duplication.
- Every node and edge traces back to a source artifact and import run.
- Parser warnings are recoverable and visible in import reports.
- `memoryos stats` reports platform, role, conversation, pair, node, edge, source, and import counts.
- `memoryos audit` distinguishes extracted from accepted/rejected/speculative/stale.
- Unsupported claims, unresolved questions, stale decisions, repeated tasks, and duplicate concepts are visible in audit output.
- User-originated ideas can be queried separately from AI-originated suggestions.
- Existing JSONL data remains readable.
- No UI, vector DB, model API key, or external database is required.

## Risks

- Parser drift: provider export structures may change. Mitigation: version parsers, store parser metadata, and keep fixtures per observed structure.
- Private data leakage in tests: real exports may contain sensitive text. Mitigation: use redacted fixtures only and add fixture review before commit.
- Over-aggressive dedupe: repeated concerns can be meaningful. Mitigation: preserve recurrence and source references; produce merge candidates instead of silent deletion.
- Schema churn: early fields may change as the graph matures. Mitigation: schema versioning, compatibility readers, and append-only review overlays.
- Unsupported claims becoming trusted memory: extraction may look authoritative. Mitigation: default extracted claims to `new` or `unsupported`; require review for accepted state.
- Ambiguity collapse: heuristics may force one interpretation. Mitigation: branch nodes and branch groups for unresolved interpretations.
- Raw text and graph state mixing: downstream UI or agents may treat summaries as source. Mitigation: keep source artifacts, normalized records, extracted nodes, review state, and audit outputs separate.
- Import failure from one bad record: large exports often contain malformed fragments. Mitigation: parser warning protocol with skipped-record counts.
- File growth: append-only JSONL can become large. Mitigation: indexed manifests and later compaction/export commands after schema stabilization.
- Premature infrastructure: adding DBs, embeddings, or UI too early can hide substrate defects. Mitigation: keep Phase 0 and Phase 1 exit criteria as gates.

## Immediate Implementation Slice

The next smallest useful slice is:

1. Add `SourceArtifact` records and link every new node and edge to them.
2. Add parser warning objects so malformed records do not abort imports.
3. Add parser name/version metadata.
4. Add node review statuses with a read-time default for existing nodes.
5. Add tests for dry-run, re-import dedupe, and malformed-record warnings.
6. Expand audit JSON/markdown to show unsupported claims and unresolved questions separately from accepted memory.

This slice directly supports the roadmap Phase 0 exit criteria and unlocks Phase 1 parser reliability without requiring embeddings, UI, or database changes.
