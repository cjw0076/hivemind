# GoEN / Dipeen Research Implementation Breakdown

Date: 2026-05-02

Scope: implementation work items for GoEN reverse translation, Dipeen hypergraph memory, ontology plasticity, and reflective graph control inside the MyWorld / MemoryOS direction.

Source boundary: derived only from `docs/goen_resonance.md`, `docs/NORTHSTAR.md`, `docs/ROADMAP.md`, and `docs/MYWORLD_IDEA_EXCERPTS.md`.

## 0. Research Target

Build the smallest executable reflective graph control loop:

```text
partial observation / conversation / file
  -> reverse-translate into claims, events, intents, uncertainty, and ontology structure
  -> store in a durable Dipeen hypergraph
  -> preserve ambiguity, evidence, disagreement, and source provenance
  -> run critique, planning, and guardian passes
  -> propose explicit graph edits
  -> score and commit/reject/defer those edits
  -> feed the revised graph state into future model calls and next actions
```

The target is not a consciousness claim. The measurable target is reflective control: better recall, contradiction detection, plan repair, project continuity, and ontology revision than raw text, vector-only memory, static summaries, or static knowledge graphs.

## 1. MPU Specs

### MPU-RT0: GoEN Reverse Translation Compiler

Goal: convert natural language into reviewable cognitive structure instead of summaries.

Inputs:

- Markdown notes and session logs.
- Normalized conversation messages and user/assistant pairs.
- Research files and code artifact references.
- Existing MemoryOS concepts and graph state.

Outputs:

- `claim`, `event`, `intent`, `assumption`, `question`, `task`, `decision`, `concept`, `uncertainty`, and `evidence` nodes.
- Typed hyperedges linking source spans, claims, concepts, tasks, evidence, and contradictions.
- Ambiguity branches when a statement has multiple plausible interpretations.
- Optional phase-coded fields: salience, confidence, viewpoint, temporal stance, revisability.

Minimum behavior:

- Preserve user-originated ideas separately from AI-suggested ideas.
- Attach every extracted node to a source pointer.
- Mark unsupported or speculative claims explicitly.
- Avoid forcing ambiguous text into one canonical interpretation.

Exit criteria:

- Ambiguous language is represented as branches.
- Claim-evidence alignment improves over static summaries.
- Contradiction candidates are recoverable from graph structure, not only string search.

### MPU-D0: Dipeen Hypergraph Research Memory

Goal: implement the external ontology substrate for research memory.

Minimum corpus:

- 30 research files.
- 20 code artifacts.
- 100 notes or conversation excerpts.

Node types:

- `file`
- `chunk`
- `message`
- `pair`
- `claim`
- `concept`
- `decision`
- `assumption`
- `question`
- `task`
- `experiment`
- `code`
- `result`
- `memory`
- `agent`
- `critique`
- `user_intent`
- `ontology_patch`

Hyperedge types:

- `supports`
- `contradicts`
- `derives_from`
- `implements`
- `tests`
- `remembers`
- `compresses`
- `schedules`
- `depends_on`
- `generalizes`
- `specializes`
- `revises`
- `accepted_by`
- `rejected_by`
- `proposed_by`
- `observed_in`

Durability requirements:

- Append-only JSONL for raw node and edge creation.
- Stable IDs for imported entities.
- Source pointers for every derived object.
- Review status separate from extraction status.
- A graph snapshot or materialized view can be rebuilt from logs.

Exit criteria:

- Same-question evidence retrieval improves over raw text search.
- Duplicate tasks and repeated claims are reduced in real use.
- Stale or contradictory claims are caught by audit.

### MPU-D1: Ontology Plasticity Agent

Goal: prove that explicit ontology edits improve adaptation before scaling to broader agent orchestration.

Edit actions:

- `AddNode`
- `SplitNode`
- `MergeNode`
- `AddTypedEdge`
- `RetypeEdge`
- `PruneEdge`
- `PromoteSubgraph`
- `DemoteConcept`
- `MarkStale`
- `ForkBranch`
- `ResolveBranch`

Edit payload:

```json
{
  "edit_id": "edit_...",
  "op": "RetypeEdge",
  "targets": ["edge_..."],
  "proposal_reason": "new evidence changes relation from supports to contradicts",
  "evidence_ids": ["node_...", "chunk_..."],
  "expected_gain": {
    "predictive": 0.0,
    "compression": 0.0,
    "consistency": 0.0,
    "intervention": 0.0,
    "stability": 0.0
  },
  "risk": {
    "forgetting": 0.0,
    "overmerge": 0.0,
    "unsupported_claim": 0.0
  },
  "status": "proposed"
}
```

Plasticity rule:

```text
prediction error / uncertainty / contradiction / task pressure / source recency
  -> plasticity gate
  -> candidate graph edits
  -> edit scoring
  -> commit, reject, defer, or branch
```

Exit criteria:

- The ontology-editing agent repairs hidden relation changes better than fixed graph and vector-memory baselines.
- Merge and split operations reduce duplicates without erasing meaningful disagreement.
- Retype and prune operations improve contradiction precision without destroying source traceability.

### MPU-D2: Reflective Graph Control And Swarm Rewrite Policy

Goal: make multiple agents useful as graph rewrite operators without corrupting memory.

Agents:

- Archivist: preserve source, normalize records, detect duplicates, maintain provenance.
- Critic: flag unsupported, contradictory, overbroad, stale, or scope-violating claims.
- Planner: convert active decisions, questions, and blocked tasks into next actions.
- Guardian: flag privacy, security, cost, and boundary risks.
- Synthesizer: compress subgraphs into candidate concepts without claiming final truth.

Control objects:

- Proposed edit queue.
- Agent permission matrix over node and edge types.
- Commit log with before/after graph hashes.
- Rollback pointer for committed edit batches.
- Disagreement records between agents.
- Review state for user acceptance, rejection, or deferral.

Exit criteria:

- Agents can disagree without overwriting each other.
- The graph records why an edit was accepted, rejected, or deferred.
- Reflection produces actionable next steps with evidence references.

### MPU-D3: Optional GoEN Structural Plasticity Learner

Goal: connect the symbolic hypergraph system to GoEN as a graph plasticity learner once file substrate and edit policy are stable.

Inputs:

- Hypergraph snapshots.
- Edit history.
- Prediction targets such as next task, stale claim, contradiction, relation change, or evidence link.

Outputs:

- Candidate edge/node edit priors.
- Salience and revisability scores.
- Subgraph promotion candidates.
- Phase-coded representation fields for salience, confidence, viewpoint, temporal stance, and revisability.

Exit criteria:

- Learned edit priors beat heuristic edit ranking on held-out graph evolution tasks.
- The learner improves adaptation speed without increasing unsupported edit commits.

## 2. Module Breakdown

### 2.1 Reverse Translation Modules

`rt.surface_parser`

- Splits documents and conversations into source-addressable spans.
- Preserves role, model, timestamp, file path, archive member, and parser version.
- Emits source span IDs for downstream extraction.

`rt.cognitive_extractor`

- Extracts claims, events, intents, uncertainty, decisions, assumptions, questions, and tasks.
- Distinguishes user-originated statements from assistant-originated suggestions.
- Emits confidence, evidence state, and status: `new`, `speculative`, `unsupported`, or `needs_review`.

`rt.ontology_mapper`

- Maps extracted objects to existing concepts.
- Proposes `AddNode`, `MergeNode`, or `ForkBranch` when mapping confidence is low.
- Keeps near-duplicate concepts reviewable instead of silently merging.

`rt.hyperedge_constructor`

- Builds typed edges and hyperedges: support, contradiction, derivation, dependency, implementation, test, memory, compression, schedule.
- Allows n-ary edges, such as one result supporting multiple claims through one experiment.

`rt.brancher`

- Represents ambiguous interpretations as branches.
- Links branches to the same source span.
- Defers resolution until new evidence, critique, or user decision.

`rt.claim_discipline`

- Enforces evidence state.
- Flags claims with no source, no evidence, overbroad language, or speculative status mismatch.

### 2.2 Dipeen Hypergraph Modules

`dipeen.schema`

- Defines node, edge, hyperedge, status, evidence, agent, edit, and review schemas.
- Versioned from the start.

`dipeen.store`

- Append-only JSONL writer and reader.
- Materialized graph builder.
- Stable ID generation and source-hash deduplication.

`dipeen.index`

- Keyword index first.
- Optional embedding index later.
- Graph filters by type, status, source, project, agent, confidence, and evidence state.

`dipeen.audit`

- Reports unsupported claims, unresolved questions, stale decisions, duplicate concepts, missing evidence, and contradictions.
- Separates extracted graph state from accepted graph state.

`dipeen.review`

- Accept, reject, edit, mark speculative, mark stale, or request evidence.
- Avoids manual editing of raw JSONL.

`dipeen.provenance`

- Traces every node and edge to source spans and edit history.
- Answers "why does this relation exist?"

### 2.3 Ontology Plasticity Modules

`plasticity.state`

- Creates a graph state view with node age, edge age, confidence, use count, source count, contradiction count, and review status.

`plasticity.proposer`

- Generates candidate edits from extraction diffs, critique findings, retrieval failures, and recurring unresolved questions.

`plasticity.scorer`

- Scores predictive gain, compression gain, consistency gain, intervention usefulness, and memory stability.
- Penalizes unsupported merges, source loss, excessive pruning, and stale evidence.

`plasticity.policy`

- Decides commit, reject, defer, or branch.
- Applies permission gates by agent role.
- Requires user review for high-impact concept merges and claim status changes.

`plasticity.commit_log`

- Records proposed edit, agent, score, evidence, decision, before hash, after hash, and rollback pointer.

`plasticity.snapshot`

- Rebuilds materialized graph views from append-only events and committed edit logs.

### 2.4 Reflective Control Modules

`control.loop`

- Orchestrates generate, objectify, relate, critique, rewire, act, observe, update.

`control.agents.archivist`

- Runs import normalization, dedup candidates, and provenance checks.

`control.agents.critic`

- Produces critique nodes and edit proposals for unsupported, contradictory, stale, or overbroad claims.

`control.agents.planner`

- Produces next-action candidates from active tasks, unresolved questions, and accepted decisions.

`control.agents.guardian`

- Flags privacy, security, cost, boundary, and claim-discipline risks.

`control.disagreement`

- Stores agent disagreement as first-class graph objects.
- Links disagreement to claims, evidence, branches, and user decisions.

`control.reporter`

- Emits reviewable reports: active claims, unresolved questions, risky assumptions, proposed edits, accepted edits, rejected edits, and next actions.

## 3. Data Model

### 3.1 Node Record

```json
{
  "id": "node_...",
  "type": "claim",
  "text": "...",
  "status": "new",
  "origin": "user|assistant|agent|file|experiment",
  "source_refs": ["src_..."],
  "confidence": 0.62,
  "evidence_state": "supported|unsupported|contradicted|speculative|unknown",
  "review": {
    "reviewer": null,
    "last_reviewed": null,
    "notes": null
  },
  "phase": {
    "salience": 0.0,
    "viewpoint": "user|critic|planner|guardian|unknown",
    "temporal_stance": "past|present|future|timeless|unknown",
    "revisability": 0.0
  },
  "created_at": "..."
}
```

### 3.2 Hyperedge Record

```json
{
  "id": "edge_...",
  "type": "supports",
  "src": ["node_...", "src_..."],
  "dst": ["node_..."],
  "confidence": 0.74,
  "status": "new",
  "source_refs": ["src_..."],
  "evidence_ids": ["node_..."],
  "agent_refs": ["agent_archivist"],
  "created_at": "..."
}
```

### 3.3 Disagreement Record

```json
{
  "id": "disagree_...",
  "type": "agent_disagreement",
  "claim_id": "node_...",
  "positions": [
    {
      "agent": "critic",
      "stance": "reject",
      "reason": "unsupported claim"
    },
    {
      "agent": "planner",
      "stance": "defer",
      "reason": "useful as a task hypothesis"
    }
  ],
  "resolution": "unresolved",
  "source_refs": ["src_..."]
}
```

## 4. Experiments

### Experiment E0: Reverse Translation Extraction Quality

Question: does GoEN-RT extract more useful reviewable structure than summary-only memory?

Dataset:

- 100 notes or conversation excerpts.
- Human-labeled subset with claims, decisions, questions, tasks, assumptions, and evidence spans.

Baselines:

- Raw markdown search.
- Static summary per document.
- Vector retrieval over chunks.

Metrics:

- Node extraction precision and recall by type.
- Evidence span accuracy.
- User-originated vs AI-originated attribution accuracy.
- Unsupported claim detection rate.
- Ambiguity preservation rate.

Pass condition:

- Improves evidence-linked claim retrieval over summary baseline.
- Does not collapse ambiguous statements into unsupported hard claims.

### Experiment E1: Hypergraph Evidence Retrieval

Question: does Dipeen retrieve better evidence for recurring research questions than raw text?

Dataset:

- Same-question queries repeated across notes, conversations, and code artifacts.

Baselines:

- Keyword search.
- Vector-only search.
- Static knowledge graph without hyperedges.

Metrics:

- Evidence recall at k.
- Evidence precision at k.
- Source trace completeness.
- Time to recover decision context.
- Duplicate task reduction.

Pass condition:

- Same-question evidence retrieval improves over raw text search.
- Returned answers cite source nodes and relation paths.

### Experiment E2: Contradiction And Stale Claim Audit

Question: does reflective graph audit catch stale or contradictory claims better than static summaries?

Dataset:

- Versioned notes with changed decisions, abandoned assumptions, and contradicted claims.

Baselines:

- Latest summary only.
- Vector search plus LLM judgment.
- Static graph without statuses or edit history.

Metrics:

- Contradiction precision and recall.
- Stale claim detection precision and recall.
- False stale rate for still-valid claims.
- Review burden per true issue found.

Pass condition:

- Catches more stale/contradictory claims without overwhelming review.

### Experiment E3: Ontology Plasticity Hidden Relation Change

Question: does ontology editing adapt faster to relation changes than fixed graph memory?

Setup:

- Small synthetic research world with concepts, claims, evidence, tasks, and hidden relation changes.
- Example changes: support becomes contradiction, concept splits into two meanings, two duplicate concepts merge, task dependency is invalidated.

Baselines:

```text
fixed graph
  < rewired typed graph
  < ontology-editing graph
```

Metrics:

- Prediction error reduction after hidden change.
- Adaptation speed in number of observations.
- Contradiction reduction.
- Catastrophic forgetting rate.
- Task transfer success.
- Bad merge rate.

Pass condition:

- Ontology-editing graph repairs hidden relation changes faster than baselines while preserving evidence traceability.

### Experiment E4: Reflective Control Loop Utility

Question: does the full loop improve project continuity and next-action quality?

Dataset:

- Multi-session project logs with decisions, tasks, failures, critiques, and next actions.

Baselines:

- Chat transcript only.
- Summary memory.
- Static graph without critique and rewiring.

Metrics:

- Next-action quality judged against accepted project direction.
- Plan repair after failed task.
- Recurring unresolved question detection.
- Decision recovery accuracy.
- Agent disagreement preservation.
- User review acceptance rate.

Pass condition:

- Produces fewer repeated tasks, better next actions, and more accurate decision recovery than baselines.

### Experiment E5: Learned Edit Prior

Question: can GoEN structural plasticity learn useful edit priors from graph evolution?

Dataset:

- Historical graph snapshots and committed edit logs.

Baselines:

- Heuristic scorer only.
- Random edit ranking.
- Static embeddings over nodes.

Metrics:

- Accepted edit ranking MRR.
- Rejected edit suppression rate.
- Relation retype accuracy.
- Merge/split proposal precision.
- Unsupported edit false-positive rate.

Pass condition:

- Learned priors improve proposal ranking without increasing unsafe commits.

## 5. Metrics

### Memory Quality

- Evidence recall at k.
- Evidence precision at k.
- Source trace completeness.
- Decision recovery accuracy.
- User-originated attribution accuracy.
- AI-suggested attribution accuracy.
- Duplicate concept/task reduction.

### Claim Discipline

- Unsupported claim detection precision and recall.
- Contradiction detection precision and recall.
- Stale claim detection precision and recall.
- Speculative claim labeling accuracy.
- Review burden per accepted correction.

### Ontology Plasticity

- Prediction error reduction.
- Adaptation speed.
- Catastrophic forgetting reduction.
- Contradiction reduction after edits.
- Task transfer improvement.
- Bad merge rate.
- Bad prune rate.
- Branch resolution accuracy.

### Reflective Control

- Next-action quality.
- Plan repair success.
- Recurring unresolved question detection.
- Disagreement preservation rate.
- Accepted edit rate.
- Rejected unsafe edit rate.
- Rollback frequency.

### System Reliability

- Re-import duplication rate.
- Parser failure recovery rate.
- Schema migration success.
- Materialized graph rebuild determinism.
- Edit log replay determinism.

## 6. Dependencies

### Immediate Dependencies

- Stable file substrate with append-only JSONL nodes and edges.
- Existing import path for markdown/text notes and AI exports.
- Source hashing and source pointer conventions.
- Node and edge schema versioning.
- Audit report generation.
- Review status fields.

### Near-Term Dependencies

- Parser fixtures for supported providers and manual markdown.
- Redacted fixture suite.
- Local semantic search abstraction.
- Graph materialization from JSONL.
- CLI commands for review and audit.
- Evaluation harness for extraction, retrieval, contradiction, and edit scoring.

### Later Dependencies

- Embedding provider abstraction.
- Vector index backend.
- Local API and visual board.
- Agent permission policy.
- Rollback-capable edit commits.
- Learned graph edit prior.
- Optional GoEN encoder integration.

## 7. Implementation Phases

### Phase A: File-First Graph Substrate

Build:

- Versioned schemas for nodes, hyperedges, source refs, reviews, agents, and edits.
- Append-only writers.
- Materialized graph builder.
- Audit report over unsupported claims, unresolved questions, stale decisions, duplicates, and missing evidence.

Do not build yet:

- Large UI.
- Agent swarm orchestration.
- Learned GoEN model.

Deliverable:

- A small corpus can be imported, audited, rebuilt, and reviewed from files.

### Phase B: Reverse Translation V0

Build:

- Surface parser.
- Cognitive extractor.
- Ontology mapper.
- Hyperedge constructor.
- Ambiguity brancher.

Deliverable:

- Markdown/session logs become reviewable claim, task, decision, assumption, question, and evidence nodes.

### Phase C: Dipeen Hypergraph V0

Build:

- Hyperedge support.
- Provenance queries.
- Evidence retrieval.
- Duplicate concept/task candidates.
- Claim status audit.

Deliverable:

- Same-question evidence retrieval and decision recovery outperform raw text search in a small corpus.

### Phase D: Plasticity Agent V0

Build:

- Proposed edit queue.
- Edit scorer.
- Merge, split, retype, prune, branch, and promote operations.
- Commit log and rollback pointer.

Deliverable:

- Hidden relation change benchmark demonstrates adaptation advantage over fixed graph.

### Phase E: Reflective Control V0

Build:

- Archivist, critic, planner, and guardian passes.
- Agent disagreement records.
- Next-action report.
- Permission policy for graph edits.

Deliverable:

- Full generate/objectify/relate/critique/rewire/act/observe/update loop produces reviewable next actions and graph edits.

### Phase F: GoEN Learner V0

Build:

- Snapshot dataset.
- Edit-history prediction task.
- Heuristic-vs-learned edit ranking.
- Salience, confidence, viewpoint, temporal stance, and revisability priors.

Deliverable:

- Learned edit priors improve edit ranking on held-out graph evolution cases.

## 8. Risks And Mitigations

### Risk: Overclaiming

Problem: vision language can sound like scientific proof.

Mitigation:

- Keep measurable target as reflective control.
- Label unsupported and speculative claims.
- Keep GoEN/Dipeen research claims separate from empirical results.

### Risk: Ontology Collapse Through Bad Merges

Problem: merging concepts can erase meaningful disagreement or ambiguity.

Mitigation:

- Require review for high-impact merges.
- Preserve source branches.
- Track bad merge rate.
- Allow split and rollback.

### Risk: Graph Noise From Over-Extraction

Problem: too many low-quality nodes make memory unusable.

Mitigation:

- Use status fields and confidence thresholds.
- Separate extracted from accepted.
- Score salience and revisability.
- Add review queues rather than auto-accepting.

### Risk: Agent Corruption Of Graph State

Problem: reflective agents may overwrite each other or commit unsupported edits.

Mitigation:

- Use proposed edit queue.
- Enforce permission matrix.
- Store disagreement records.
- Commit only through policy.
- Log before/after graph hashes.

### Risk: Vector Memory Masquerading As Ontology

Problem: semantic search alone can look useful while failing claim discipline.

Mitigation:

- Keep embeddings separate from nodes, edges, evidence, and review status.
- Measure evidence-linked retrieval, contradiction detection, and decision recovery.

### Risk: Premature UI Or Database Complexity

Problem: building dashboards before schema stability hides data-quality failures.

Mitigation:

- Keep file-first substrate.
- Add local API/UI only after real graph data and audit reports are stable.

### Risk: Learned GoEN Model Too Early

Problem: training a graph learner before edit logs exist produces weak supervision.

Mitigation:

- Start with heuristic plasticity.
- Collect committed/rejected/deferred edits.
- Train learned edit priors only after enough graph evolution data exists.

### Risk: Source Boundary Drift

Problem: speculative MyWorld ontology prose leaks into other projects or papers.

Mitigation:

- Keep project boundary explicit.
- Mark source project and target project on claims.
- Use guardian audit for boundary violations.

## 9. First Concrete Work Items

1. Define schema files for node, hyperedge, source ref, review, edit, and disagreement records.
2. Implement append-only JSONL store and materialized graph rebuild.
3. Implement source span addressing for markdown/session logs.
4. Implement extraction of claims, decisions, assumptions, questions, tasks, intents, and evidence refs.
5. Implement first audit report: unsupported claims, unresolved questions, duplicate concepts, stale decisions, and missing evidence.
6. Implement review commands for accept, reject, speculative, stale, and request-evidence.
7. Implement proposed edit queue with `AddNode`, `MergeNode`, `SplitNode`, `AddTypedEdge`, `RetypeEdge`, `PruneEdge`, and `PromoteSubgraph`.
8. Implement edit scoring with predictive, compression, consistency, intervention, and stability terms.
9. Implement hidden relation change benchmark for ontology plasticity.
10. Implement reflective control report with archivist, critic, planner, and guardian sections.

## 10. Definition Of Done For The First Research Loop

The first loop is done when a markdown/session-log corpus can be processed end to end:

```text
input files
  -> source spans
  -> extracted cognitive nodes
  -> typed hyperedges
  -> audit findings
  -> proposed ontology edits
  -> accepted/rejected/deferred edit log
  -> next actions with evidence references
```

Minimum acceptance checks:

- Every output node has a source pointer.
- User-originated and AI-originated ideas remain separable.
- Unsupported claims are not silently treated as accepted.
- Ambiguity can remain unresolved without data loss.
- Agent disagreement is stored, not flattened.
- Graph state can be rebuilt from append-only records.
- Ontology edits are explicit, scored, and reversible.
