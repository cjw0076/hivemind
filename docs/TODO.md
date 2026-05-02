# MemoryOS TODO

This TODO is ordered by dependency. Do the earliest unfinished item that improves the working loop.

Use `docs/VISION_GRAPH.md` for source provenance. Major sections below include `VG-*` tags.

## Now

Sources: `VG-03`, `VG-04`, `VG-05`, `VG-13`.

- [x] Fix `docs/MEMORYOS_MVP.md` examples that still mention `docs/1.md` and `docs/2.md`.
- [x] Add source archive hash and import run ID to every imported node/edge.
- [x] Add deduplication for re-imported files.
- [x] Add `memoryos import --dry-run` to preview counts before appending.
- [x] Add `memoryos audit --json` report snapshots under `runs/reports/`.
- [x] Add `memoryos stats` with platform, role, conversation, pair, and source counts.
- [x] Add local LLM worker prompt/CLI layer before runtime installation.
- [x] Add production-minimum `mos init` onboarding for global/project config, provider detection, and next actions.
- [x] Split local open-weight DeepSeek/Qwen status from hosted `deepseek_api`/`qwen_api` key checks.
- [x] Add `mos local status/setup` for Ollama wrapper, server state, and local model manifests.
- [x] Include local LLM model manifest detection in `mos init` onboarding output.
- [x] Stabilize `mos` run artifact schemas: task, handoff, run state, verification, memory drafts, final report.
- [x] Add event taxonomy and validation for `.runs/*/events.jsonl`.
- [x] Normalize provider invocation artifacts for Claude, Codex, Gemini, and local workers.
- [x] Add local worker route table with schema validation, confidence, and escalation fields.
- [x] Make `mos tui` show current run health, provider availability, latest event, failures, and missing artifacts.
- [x] Add parser warnings instead of failing entire imports on one malformed record.
- [x] Persist production settings profile during onboarding so provider paths, local model inventory, and shell exports are tracked.

## Harness Runtime

Sources: `VG-03`, `VG-04`, `VG-13`.

- [x] Add schema validation to `python -m memoryos.mos verify`.
- [x] Add `mos invoke <provider> --dry-run` for prompt/command artifact generation.
- [x] Keep Codex prepare-only until non-interactive execution is explicitly stable.
- [x] Record provider mode: `prepare_only`, `execute_supported`, or `unavailable`.
- [x] Ensure failed provider/local invocations write artifacts and events.
- [x] Add a minimal valid run fixture for harness tests.
- [x] Add `memoryos import-run .runs/<run_id>` or equivalent draft import path.
- [x] Add `mos settings detect/shell` and `scripts/mos-workbench.sh` for context editing plus fast provider artifact preparation.

## Parser Work

Sources: `VG-01`, `VG-11`.

- [ ] Create `tests/fixtures/exports/`.
- [ ] Add redacted ChatGPT fixture.
- [ ] Add redacted DeepSeek fixture from current local structure.
- [ ] Add redacted Grok fixture from current local structure.
- [ ] Add redacted Perplexity markdown ZIP fixture.
- [ ] Add Claude export parser after a sample export is available.
- [ ] Add Gemini Takeout parser after a sample export is available.
- [ ] Store parser name and parser version in imported node metadata.
- [ ] Document user-facing export steps for each provider.

## Schema Work

Sources: `VG-01`, `VG-07`, `VG-09`, `VG-12`.

- [ ] Add `SourceArtifact` or equivalent source table/file for archive members.
- [ ] Add node review statuses: `new`, `reviewed`, `accepted`, `rejected`, `speculative`, `stale`.
- [ ] Add claim fields: evidence_state, confidence, reviewer, review_time.
- [ ] Add edge fields: relation confidence, evidence list, plasticity score, last used.
- [ ] Add hyperedge representation for multi-node events.
- [ ] Add project nodes and project membership edges.
- [ ] Add user-originated vs AI-originated provenance fields.

## Extraction Work

Sources: `VG-01`, `VG-08`, `VG-12`.

- [ ] Replace current heuristic extraction with a two-stage pipeline: deterministic chunking first, LLM/local model labeling second.
- [ ] Extract intent: question, request, critique, idea, decision, reflection, implementation, design, research.
- [ ] Extract project: Uri, Dipeen, GoEN, North Star, Deepfake, Capstone, MemoryOS, unknown.
- [ ] Extract evidence links and unsupported claims separately.
- [ ] Extract action items with owner, status, source, and due context if present.
- [ ] Preserve ambiguity as branches instead of forcing one interpretation.

## Local LLM Workers

Sources: `VG-05`, `VG-03`, `VG-04`.

- [ ] Define route table for classify, extract-memory, extract-capability, compress-context, draft-handoff, summarize-log, and review-diff.
- [ ] Store primary model, fallback model, complexity, expected schema, and escalation rule for each role.
- [ ] Add schema validation for worker outputs.
- [ ] Add `confidence`, `should_escalate`, and `escalation_reason` to worker draft schemas.
- [ ] Add MemoryOS, CapabilityOS, and code-log benchmark fixtures.
- [ ] Record model, latency, output validity, and failure reason for each worker run.

## Audit Work

Sources: `VG-12`, `VG-01`.

- [ ] Separate extracted nodes from reviewed nodes in audit output.
- [ ] Add unsupported claim report.
- [ ] Add unresolved question report.
- [ ] Add stale decision report.
- [ ] Add repeated concern report.
- [ ] Add "my ideas only" report using role/provenance.
- [ ] Add cross-provider disagreement report.

## Search And Embeddings

Sources: `VG-01`, `VG-07`.

- [ ] Choose first local embedding path.
- [ ] Add embedding records for message, pair, segment, conversation summary, and user-only thought.
- [ ] Add local vector index.
- [ ] Add hybrid keyword + vector search.
- [ ] Add graph-filtered search by project, source, role, and node type.
- [ ] Add evaluation queries from `docs/NORTHSTAR.md`.

## API And UI

Sources: `VG-10`, `VG-01`, `VG-03`.

- [ ] Add local FastAPI or equivalent API.
- [ ] Add endpoints: import status, audit summary, search, node detail, node review, graph neighborhood.
- [ ] Build import center against real import runs.
- [ ] Build memory cockpit against real graph counts.
- [ ] Build Ask Memory with evidence-linked answers.
- [ ] Build graph explorer for project/concept/claim/task edges.
- [ ] Build draft review screen for accept/edit/reject.
- [ ] Keep Desktop cockpit deferred until `mos` run artifacts and review state are stable.

## Agent Harness

Sources: `VG-03`, `VG-04`, `VG-06`.

- [ ] Define agent roles as local prompt/protocol files: archivist, critic, planner, synthesizer, guardian.
- [ ] Define provider adapter roles: planner, executor, reviewer, summarizer, memory extractor, capability extractor.
- [ ] Define `AgentRun` and `AgentRunEvent` records from harness artifacts.
- [ ] Link every run-derived memory draft to raw refs under `.runs/<run_id>/`.
- [ ] Add proposed graph edit queue.
- [ ] Add graph edit scoring fields.
- [ ] Add commit log for accepted graph edits.
- [ ] Add disagreement log for conflicting agent recommendations.
- [ ] Add rollback story for bad graph edits.

## CapabilityOS

Sources: `VG-02`, `VG-04`, `VG-13`.

- [ ] Define `TechnologyCard`, `Capability`, `WorkflowRecipe`, `ProviderRuntime`, `QualityProfile`, `Risk`, and `LegacyRelation` schemas.
- [ ] Seed provider/runtime records for qwen local workers, DeepSeek code workers, Claude, Codex, Gemini, and Ollama.
- [ ] Store `extract-capability` output as draft CapabilityOS records only.
- [ ] Add first workflow recipe: `mos planning -> Codex implementation -> local summarize -> MemoryOS draft`.
- [ ] Add legacy comparisons for raw chat, manual shared folder, screenshot-only, and local-model-only workflows.
- [ ] Require source refs for every capability recommendation.

## Agent Society

Sources: `VG-06`, `VG-00`.

- [ ] Define `AgentProfile`, `PerformanceRecord`, `PeerReview`, `UserFeedback`, `RoutingPolicyProposal`, and `PromptMutationProposal`.
- [ ] Add structured peer review artifact criteria: acceptance fit, quality, risk, project alignment, missing tests, recommendation.
- [ ] Add user feedback states: accepted, accepted_with_edits, rejected, redo_requested, manually_fixed, ignored.
- [ ] Add failure attribution fields: context issue, prompt issue, provider limitation, task ambiguity, implementation bug, verification gap.
- [ ] Add safety gate so profile/routing/prompt changes are proposals until reviewed.
- [ ] Allow only low-risk aggregate metric updates without manual approval.

## GoEN / Dipeen Research

Sources: `VG-07`, `VG-08`, `VG-09`.

- [ ] Write MPU-D0 spec: Hypergraph Research Memory.
- [ ] Build corpus benchmark with files, code, notes, and conversation excerpts.
- [ ] Measure evidence recall against raw text and vector-only baselines.
- [ ] Write GoEN Reverse Translation spec.
- [ ] Implement possibility branch representation.
- [ ] Write MPU-D1 spec: Ontology Plasticity Agent.
- [ ] Define synthetic world with hidden relation changes.
- [ ] Compare fixed graph, rewired graph, and ontology-editing graph.

## Security And Product

Sources: `VG-12`, `VG-13`.

- [ ] Decide local-only default for raw exports.
- [ ] Add raw export deletion command.
- [ ] Add redaction preview for sensitive imports.
- [ ] Add private project exclusion.
- [ ] Draft privacy principles: no training on user uploads, export/delete always available.
- [ ] Design optional encrypted backup.

## Documentation

Sources: `VG-00` through `VG-13`.

- [ ] Keep `docs/NORTHSTAR.md` as the top-level vision.
- [ ] Keep `docs/ROADMAP.md` as phase order.
- [ ] Keep `docs/TODO.md` as the active implementation list.
- [x] Add `docs/ROUTE.md` as the docs route map.
- [x] Add `docs/VISION_GRAPH.md` as the source-to-work vision graph.
- [x] Add `docs/LOWERCASE_SOURCE_GRAPH.md` for lowercase source-vault docs.
- [x] Split large source vault docs into `docs/split/` mirrors without deleting originals.
- [x] Create reusable Codex skill `docs-vision-router` for future docs graph/source routing work.
- [ ] Keep `docs/MEMORYOS_MVP.md` focused only on the current local MVP.
- [ ] Keep `docs/EXPORT_PARSERS.md` focused only on provider export adapters.
- [ ] Add a short `docs/README.md` index for new sessions.
