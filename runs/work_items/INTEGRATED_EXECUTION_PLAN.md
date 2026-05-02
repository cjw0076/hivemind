# MemoryOS Integrated Execution Plan

Date: 2026-05-02 KST

Inputs:

- `runs/work_items/core_substrate.md`
- `runs/work_items/export_parsers.md`
- `runs/work_items/research_goen_dipeen.md`
- `runs/work_items/product_ui_capability.md`

## The Vibe

MemoryOS is not a chat archive UI. It is the file-backed cognitive ledger underneath a future memory-native agent ecosystem.

The immediate job is to harden the substrate so every later layer has something real to stand on:

```text
source artifact
  -> deterministic parser
  -> normalized messages / pairs
  -> reviewable memory objects
  -> typed graph / hypergraph events
  -> audit / search / critique
  -> API / UI / agent harness
  -> GoEN/Dipeen reflective control
```

The product vision is rich, but the fast path is not to build the cockpit first. The fast path is to make the memory graph trustworthy enough that the cockpit, Ask Memory, Draft Review, Hypergraph Explorer, and CapabilityOS views can all read from the same durable substrate.

## Four Parallel Tracks

### Track A - Core Substrate

Owner pattern: one worker owns schema/store/CLI.

Goal: make the append-only file substrate stable, traceable, deduplicated, reviewable, and inspectable.

Immediate units:

1. Split monolithic `memoryos/importers.py` into package modules only after tests exist.
2. Add `ImportRun` records at `memory/processed/import_runs.jsonl`.
3. Add `SourceArtifact` records at `memory/processed/source_artifacts.jsonl`.
4. Add canonical schema enums for node type, edge type, status, provenance, provider, role, evidence state.
5. Add first `HyperedgeEvent` representation as a node plus participant edges.
6. Add `memoryos inspect <node_id>` to trace source path/member/span.
7. Add `memoryos search <query>` keyword search before vector search.
8. Add review state storage: `memory/processed/reviews.jsonl`.

Acceptance:

- Every new node/edge has source artifact, import run, parser, provenance, and stable ID metadata.
- Re-importing the same export adds zero duplicate records.
- A node can be traced back to source file/archive member without reading all JSONL manually.

### Track B - Export Parsers

Owner pattern: one worker owns parser contracts and fixture tests.

Goal: deterministic provider adapters, no semantic inference.

Immediate units:

1. Add parser result/warning types.
2. Add source detector.
3. Add parser versions.
4. Add fixture directory under `tests/fixtures/exports/`.
5. Create redacted fixtures for DeepSeek, Grok, Perplexity from current local exports.
6. Create synthetic ChatGPT fixture.
7. Add tests for stable counts, stable role order, stable pair IDs, malformed record warnings.
8. Add Claude/Gemini stubs that produce explicit unsupported/sample-needed warnings.

Acceptance:

- Parser fixtures do not contain private data.
- Malformed provider records produce warnings and skipped counts, not full import failure.
- Parser code never invents roles when markdown lacks explicit role markers.

### Track C - GoEN / Dipeen Research

Owner pattern: one worker owns research specs and experimental modules; do not block core substrate.

Goal: make reverse translation and ontology plasticity executable after the graph substrate is ready.

Immediate units:

1. Write `docs/MPU_D0_HYPERGRAPH_RESEARCH_MEMORY.md`.
2. Write `docs/GOEN_REVERSE_TRANSLATION_SPEC.md`.
3. Add schema placeholders for ambiguity branches, evidence bundles, critique nodes, ontology patches.
4. Implement branch records only after SourceArtifact and ReviewState exist.
5. Define experiments E0-E2 first: extraction quality, evidence retrieval, contradiction/stale claim audit.
6. Defer learned GoEN model until graph edit history exists.

Acceptance:

- No consciousness claims in implementation docs; call it reflective control.
- Ambiguity is preserved as branches instead of collapsed summaries.
- Experiments compare against raw text, vector-only, static summary, and static graph baselines.

### Track D - Product / UI / CapabilityOS

Owner pattern: one worker owns API/UI contracts and does not fabricate data.

Goal: product surfaces read real graph state.

Immediate units:

1. Define `MemoryObject`, `RawRef`, `HyperedgeEvent`, `ContextPack`, `HandoffArtifact` schemas.
2. Build Draft Review first, not the whole cockpit.
3. Build Project State from accepted/reviewed memories only.
4. Build Ask Memory with evidence packs.
5. Build Handoff Generator with completeness checks.
6. Seed Capability Ontology with one vertical: Design-to-Code.
7. Build Task Planner and Capability Gap only after seeded ontology exists.

Acceptance:

- Every UI answer links to source/evidence nodes.
- Draft Review can accept/edit/reject extracted memories.
- CapabilityOS recommends workflows by capability, not by tool name alone.

## Shared Contracts

These objects should be stabilized before workers diverge too far:

```text
ImportRun
SourceArtifact / RawRef
MemoryObject / Node
Edge
HyperedgeEvent
ReviewState
ParserWarning
ContextPack
HandoffArtifact
ProposedGraphEdit
GraphCommit
DisagreementRecord
```

Do not let UI, research, and parser code create competing versions of these concepts.

## Recommended Next Sprint

### Sprint 1: Trustworthy Import Loop

1. Implement `SourceArtifact` registry.
2. Implement `ImportRun` registry.
3. Add parser warnings.
4. Add redacted parser fixtures and tests.
5. Add `inspect` command.
6. Add keyword search command.
7. Add review state JSONL.

### Sprint 2: Reviewable Memory

1. Add node statuses and provenance fields.
2. Add manual review command.
3. Add unsupported claim / unresolved question / stale decision reports.
4. Add project nodes and project membership.
5. Add Draft Review API or CLI prototype.

### Sprint 3: First Product Slice

1. Local API over import/stats/audit/search/inspect/review.
2. Draft Review UI.
3. Ask Memory with evidence pack.
4. Project State view.

### Sprint 4: Research Slice

1. GoEN reverse translation spec.
2. Dipeen hypergraph event schema.
3. Ambiguity branch representation.
4. E0/E1/E2 experiments on current docs/export corpus.

## Work Allocation Pattern

Use subagents as implementation workers with disjoint write scopes:

- Worker A: `memoryos/schema.py`, `memoryos/store.py`, new `memoryos/provenance.py`.
- Worker B: `memoryos/importers*`, `tests/fixtures/exports/`, parser tests.
- Worker C: `memoryos/audit.py`, new `memoryos/search.py`, report docs.
- Worker D: research specs under `docs/` only.
- Worker E: API/UI contracts under `docs/` or future app directory only.

Main agent role:

- Keep shared schemas coherent.
- Review subagent patches.
- Run verification.
- Update `docs/TODO.md` and `.ai-runs/shared/comms_log.md`.
- Integrate without reverting unrelated changes.

## Immediate Implementation Decision

Proceed with Sprint 1, starting with `SourceArtifact` and `ImportRun`.

Reason:

- It unblocks parser fixtures, inspect, audit provenance, UI evidence links, and GoEN source discipline.
- It is low-risk and local-only.
- It prevents future UI/research code from building on weak source metadata.

