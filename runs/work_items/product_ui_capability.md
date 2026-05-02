# Product/UI + CapabilityOS Implementation Breakdown

Source docs read for this breakdown:

- `docs/ui_future.md`
- `docs/capabilityOS.md`
- `docs/ecosystem.md`
- `docs/optima.md` (empty)
- `docs/word.md`
- `docs/NORTHSTAR.md`
- `docs/image.png` metadata checked only; no UI-critical details used

## 0. Product Frame

MemoryOS should start as a local-first product surface for turning scattered AI work into a durable, auditable memory graph. CapabilityOS should be framed as the companion capability layer that maps user goals to the best model, app, MCP, connector, skill, workflow, and agent runtime combination.

The product should not begin as a general visual graph toy or an AI tool directory. The first useful loop is:

```text
input markdown/session log/export
  -> extract memory objects, decisions, assumptions, TODOs, claims
  -> create hyperedge events
  -> review drafts
  -> build context packs
  -> create agent handoffs
  -> execute or export handoff
  -> log result back into memory
```

Core product promise:

```text
Models think. Agents act. MemoryOS remembers. CapabilityOS chooses the right abilities.
```

The implementation should make four primitives concrete before expanding:

1. Memory Object
2. Hyperedge Event
3. Context Pack
4. Agent Handoff

## 1. Product/UI Surfaces

### 1.1 Memory Cockpit

Purpose: home screen for current cognitive/project state.

Primary users:

- User reviewing current project memory.
- Agent operator checking whether a project has enough context for execution.
- Reviewer checking unresolved questions, stale claims, and pending drafts.

Layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ Project switcher | Search memory | Current run/status         │
├──────────────┬──────────────────────────────┬────────────────┤
│ Projects     │ Current Project State         │ Right Rail      │
│              │ - North Star                  │ - Pending drafts│
│ - MemoryOS   │ - Active decisions            │ - Recent runs   │
│ - Uri        │ - Open questions              │ - Capability gap│
│ - Paper #... │ - Next actions                │ - Evidence todo │
├──────────────┴──────────────────────────────┴────────────────┤
│ Timeline: recent decisions, imports, handoffs, critiques       │
└──────────────────────────────────────────────────────────────┘
```

Main components:

- Project selector.
- Project State panel.
- Active Decisions list.
- Open Questions list.
- Next Actions list.
- Pending Memory Drafts widget.
- Recent Agent Runs widget.
- Capability Gap preview.
- Evidence Health preview.

API needs:

- `project.list`
- `project.get_state(project_id)`
- `memory.list_drafts(project_id, status=pending)`
- `run.list_recent(project_id)`
- `capability.gap_for_project(project_id)`
- `evidence.health(project_id)`

Data dependencies:

- Project records.
- Project State summary.
- Memory Objects with status and origin.
- Agent Run events.
- Handoff records.
- Capability scan state.

Acceptance checks:

- User can open the app and see the current project state without graph visualization.
- Active decisions, open questions, and next actions are visible on first screen.
- Pending drafts are clearly separated from committed memory.
- Each displayed decision links to raw refs or is marked unsupported/speculative.
- UI does not imply AI-originated ideas are user-originated.

Risks:

- Overbuilding dashboard chrome before the memory substrate works.
- Showing graph visuals before evidence and origin hygiene are reliable.
- Mixing draft and committed memory in the same visual treatment.

### 1.2 Import Center

Purpose: ingest AI exports, markdown logs, documents, and session artifacts into normalized memory.

Supported v0 inputs:

- Markdown/session logs.
- ChatGPT export files if parser exists.
- Claude/Gemini/Perplexity exports as later adapters.
- Manual pasted text as a fallback.

Pipeline display:

```text
Raw Archive
  -> Message Ledger
  -> Pair Dataset
  -> Segment
  -> Memory Draft
  -> Hyperedge Event
  -> Project State Update
```

UI structure:

- Left: import source selector and file/drop zone.
- Center: pipeline steps with statuses.
- Right: extracted summary, warnings, and draft count.
- Bottom: recent imports table.

API needs:

- `import.create(source_type, file_refs, project_id)`
- `import.get_status(import_id)`
- `import.list_recent(project_id)`
- `parser.detect_source(file_ref)`
- `parser.normalize(import_id)`
- `memory.extract_drafts(import_id)`
- `hyperedge.build_from_import(import_id)`

Data dependencies:

- Raw archive file references.
- Normalized messages.
- Message pairs.
- Segments.
- Extraction job status.
- Parser warnings.
- Draft Memory Objects.
- Hyperedge Event candidates.

Acceptance checks:

- User can import at least one markdown/session log.
- Pipeline state is visible and recoverable after refresh/reopen.
- Failed parser steps show actionable error messages.
- Raw input remains preserved and linked from drafts.
- No extracted memory is committed without explicit approval or configured policy.

Risks:

- Parser-specific complexity derails v0.
- Extraction quality may be poor without a review loop.
- Large exports may require background processing and pagination.

### 1.3 Draft Review

Purpose: memory quality control. Agents can suggest memories, but the harness controls commits and the user can approve, edit, reject, merge, or supersede.

Draft types:

- idea
- decision
- question
- action
- preference
- constraint
- artifact
- reflection
- fact
- claim
- assumption

UI structure:

```text
Queue filters: project | type | origin | confidence | source | status

Draft card:
  content
  type
  origin: user / assistant / mixed / unknown
  confidence
  importance
  raw refs
  proposed links
  conflicts
  actions: approve | edit | reject | merge | mark speculative
```

API needs:

- `memory.list_drafts(filters)`
- `memory.get_draft(draft_id)`
- `memory.approve(draft_id, edits?)`
- `memory.reject(draft_id, reason)`
- `memory.merge(draft_ids, merged_content)`
- `memory.mark_superseded(memory_id, superseded_by)`
- `memory.find_similar(draft_id)`
- `memory.find_conflicts(draft_id)`

Data dependencies:

- Memory draft table.
- Raw references.
- Similarity index.
- Contradiction sets.
- Origin metadata.
- Memory lifecycle statuses.

Acceptance checks:

- User can approve, edit, and reject drafts.
- Approved drafts become committed memories with immutable raw refs.
- Similar or conflicting memories are shown before approval.
- Origin separation is visible and editable only with audit trace.
- Bulk approval is gated by confidence/source filters.

Risks:

- Review queue becomes too large and unusable.
- User may trust low-confidence AI extraction if UI over-polishes it.
- Merge/supersession semantics can corrupt project memory if rushed.

### 1.4 Ask Memory

Purpose: query the memory graph and produce answers with evidence packs.

Modes:

- Ask current project.
- Ask all memory.
- Ask decisions only.
- Ask unresolved questions.
- Ask by source/export.

Answer contract:

```text
answer
evidence memories
hyperedges
raw refs
uncertainties
stale/conflicting notes
suggested next action
```

API needs:

- `memory.search(query, filters)`
- `hypergraph.search(query, filters)`
- `context.build_pack(task, project_id, query)`
- `answer.generate_from_context(context_pack_id, mode)`
- `evidence.pack(answer_id)`

Data dependencies:

- Keyword index.
- Vector index.
- Hypergraph relationships.
- Project State.
- Raw refs.
- Memory confidence/status.

Acceptance checks:

- Answers cite committed memory and raw refs.
- Unsupported or speculative claims are labeled.
- Contradictions are surfaced instead of hidden.
- User can promote an answer into a memory draft or next action.

Risks:

- Vector-only retrieval may hallucinate continuity.
- Raw refs may be too verbose unless compact evidence previews exist.
- Cross-project retrieval may leak irrelevant context into focused work.

### 1.5 Hypergraph Explorer

Purpose: inspect cognitive events, not just pretty nodes.

Initial scope:

- Text-first explorer with optional simple graph preview.
- Prioritize clickable events and evidence over force-directed visuals.

Core entities:

- Node: Message, Pair, Segment, Memory, Project, Concept, Decision, Question, Action, Artifact, Agent, Tool, Source, TimePeriod.
- Hyperedge: TurnEvent, EpisodeEvent, DecisionEvent, IdeaComposition, ActionDerivation, ContradictionSet, AgentHandoffEvent, SystemBootstrappingEvent.

UI structure:

- Left: entity filters and saved views.
- Center: selected event detail.
- Right: members, raw refs, related events, confidence/status.

API needs:

- `hypergraph.get_event(event_id)`
- `hypergraph.list_events(filters)`
- `hypergraph.expand(node_id, depth, relation_types)`
- `hypergraph.create_event(type, members, metadata)`
- `hypergraph.retype_event(event_id, new_type)`

Data dependencies:

- Node store.
- Hyperedge event store.
- Event-member relationships.
- Raw refs.
- Project mapping.

Acceptance checks:

- User can open a DecisionEvent and see decision, evidence, constraints, alternatives, and derived actions.
- User can inspect a ContradictionSet and see old/new positions plus winner/current status.
- Explorer remains useful without advanced graph rendering.

Risks:

- Full visual graph can become unreadable.
- Retyping/splitting/merging hyperedges needs audit history.
- Users may need guided views more than raw graph browsing.

### 1.6 Deliberation Room

Purpose: Chatbot Harness surface. Rough ideas are refined before execution.

Design principle:

```text
Do not execute before deliberation when task clarity is below threshold.
```

UI structure:

```text
┌──────────────────────────────────────────────────────┐
│ Deliberation Room                                    │
├───────────────┬──────────────────────┬───────────────┤
│ User Intent   │ Model Deliberation   │ Synthesis     │
│ rough idea    │ Claude               │ Final spec     │
│ memory refs   │ GPT                  │ Decisions      │
│ constraints   │ Gemini               │ Risks          │
│ task clarity  │ Perplexity           │ Handoff        │
│               │ DeepSeek             │               │
└───────────────┴──────────────────────┴───────────────┘
```

Workflow:

1. User enters rough idea.
2. MemoryOS retrieves project context.
3. System selects model roles.
4. Models generate independent views.
5. Critique/debate pass runs.
6. Synthesis Agent creates final spec.
7. Handoff Generator produces Agent Handoff.
8. User sends to Agent Harness or saves to MemoryOS.

API needs:

- `deliberation.create(project_id, user_intent)`
- `context.build_pack(task, project_id)`
- `model.run_panel(deliberation_id, model_role)`
- `deliberation.add_critique(deliberation_id, from_role, target_role)`
- `deliberation.synthesize(deliberation_id)`
- `handoff.create_from_deliberation(deliberation_id)`
- `memory.write_draft_from_deliberation(deliberation_id)`

Data dependencies:

- Model/provider registry.
- Prompt templates by role.
- Project State.
- Relevant memories and open questions.
- Deliberation transcripts.
- Handoff completeness score.

Acceptance checks:

- A rough idea produces a structured final spec with decisions, risks, constraints, and acceptance criteria.
- Handoff cannot be sent to Agent Harness unless objective, constraints, acceptance criteria, memory refs, and expected output are present or explicitly waived.
- Each model panel is labeled as model-generated, not user decision.
- User can save the synthesis as memory drafts.

Risks:

- Multi-model flow can become slow and expensive.
- Debate can create noise unless synthesis is disciplined.
- Provider integrations may need to start as manual paste/import instead of API-driven calls.

### 1.7 Agent Harness View

Purpose: execution control surface for agents, tools, MCPs, handoffs, run state, and verification.

UI sections:

- Agent Registry.
- Capability Registry.
- Routing Policy.
- Pending Handoffs.
- Active Runs.
- Event Log.
- Execution Results.

API needs:

- `agent.list`
- `agent.get_capabilities(agent_id)`
- `routing.get_policy(project_id)`
- `routing.recommend(task, context_pack_id)`
- `handoff.list(status=pending)`
- `run.create(agent_id, handoff_id)`
- `run.get_status(run_id)`
- `run.log_event(run_id, event)`
- `run.attach_result(run_id, artifact_refs)`
- `context.commit_session(run_id)`

Data dependencies:

- Agent registry.
- Runtime adapters.
- Tool/MCP registry.
- Routing policy.
- Agent Run records.
- Event log.
- Handoff artifacts.

Acceptance checks:

- User can inspect why a handoff is routed to Codex, Claude Code, local LLM, or another runtime.
- Every run has objective, context pack, tools used, result, status, and events.
- Run results can create memory drafts rather than direct committed memories.
- Failed runs preserve enough event log for audit.

Risks:

- Direct execution before handoff clarity recreates the original problem.
- Tool permissions and auth scopes can become unsafe if hidden.
- CLI-as-worker adapters may be brittle across provider updates.

### 1.8 CapabilityOS: Capability Map

Purpose: show the user's available AI abilities, not just installed tools.

Core idea:

```text
Task quality depends on capability composition, not just model access.
```

UI structure:

```text
Design
  read_figma_layout: connected via Figma MCP
  visual_qa: missing
  component_mapping: partial

Coding
  repo_edit: available via Codex
  github_context: connected
  deployment_logs: missing

Research
  sourced_search: partial
  citation_export: missing
  docs_lookup: available
```

API needs:

- `capability.list_domains`
- `capability.map_user_environment(user_id/project_id)`
- `tool.list_connected`
- `mcp.list_servers`
- `skill.list_installed`
- `runtime.list`
- `capability.resolve_provider(capability_id)`

Data dependencies:

- Capability Ontology.
- Tool/MCP/Skill registry.
- User environment scan.
- Auth/permission state.
- Runtime compatibility.

Acceptance checks:

- Map displays capabilities by task/domain.
- Missing capabilities are distinguished from disconnected tools.
- Runtime compatibility is visible.
- User can click a capability and see providers, setup requirements, risk, and quality impact.

Risks:

- Tool list can degrade into generic directory unless mapped to task capabilities.
- Environment scanning may be platform-specific.
- Auth state may be stale unless refresh is explicit.

### 1.9 CapabilityOS: Task Planner

Purpose: user enters a goal; system recommends workflow options by quality, cost, risk, and setup complexity.

Example goal:

```text
Figma design to React implementation
```

Recommended output:

- High quality: Claude Code + Figma MCP + GitHub repo + design-to-code skill + visual QA.
- Medium: GPT/Claude screenshot analysis + manual implementation.
- Low: local LLM with screenshot only.

API needs:

- `task.classify(goal_text)`
- `capability.extract_required(task_id)`
- `workflow.find_candidates(task_id, constraints)`
- `workflow.score(workflow_id, user_environment)`
- `workflow.compare(workflow_ids)`
- `handoff.create_from_workflow(workflow_id, goal_text, project_id)`

Data dependencies:

- Task taxonomy.
- Capability Ontology.
- Workflow records.
- Quality profiles.
- Cost profiles.
- Risk profiles.
- User environment capabilities.

Acceptance checks:

- User receives at least three workflow tiers when available.
- Recommendation explains missing capabilities and expected quality impact.
- User can generate an Agent Handoff from the selected workflow.
- Recommendation is personalized by project context and installed capabilities.

Risks:

- Recommendations may overstate quality without evidence.
- Cost/risk estimates may be too vague for user trust.
- Workflow quality tiers need periodic re-evaluation.

### 1.10 CapabilityOS: Capability Gap + Auto Setup

Purpose: show what is missing for a target workflow and help configure it.

UI sections:

- Current environment.
- Required capabilities.
- Missing capabilities.
- Setup actions.
- Permission/auth requirements.
- Security warnings.
- Test connection buttons.

Setup levels:

1. MCP Discovery.
2. MCP Installation Assistant.
3. MCP Copy/Fork/Adapt.
4. MCP Generator from API/OpenAPI docs.
5. Capability Wrapper around API, CLI, file watcher, webhook, or browser automation.

API needs:

- `capability.gap(task_id, workflow_id, environment_id)`
- `setup.plan(tool_or_capability_id, runtime_id)`
- `setup.generate_config(mcp_server_id, runtime_id)`
- `setup.test_connection(tool_id)`
- `setup.record_manual_step(step_id, status)`
- `security.evaluate_setup(setup_plan_id)`

Data dependencies:

- Setup instructions.
- Runtime config templates.
- Auth requirements.
- Permission scopes.
- Security/risk profiles.
- Connection test results.

Acceptance checks:

- User can see exactly why a high-quality workflow is blocked.
- Setup plan lists auth scopes and local file/config changes before action.
- Connection tests update capability map.
- Manual setup can be tracked if auto-install is not implemented.

Risks:

- Auto setup can be dangerous without explicit permission boundaries.
- Provider setup docs change often.
- MCP generation from API docs is high-complexity and should not be v0.

### 1.11 Capability Radar

Purpose: Surfer-Discriminator surface for discovering and evaluating new AI tools, MCPs, skills, papers, workflows, and API updates.

Pipeline:

```text
WWW / SNS / Community / Papers / GitHub / MCP Registry
  -> Surfer Layer
  -> Raw Signal Store
  -> Normalizer
  -> Capability Ontology Builder
  -> Discriminator Layer
  -> Evidence / Benchmark / Risk / Quality Evaluation
  -> Capability Graph
  -> Legacy Stratifier
  -> Recommendation Engine
```

UI views:

- Capability Radar feed.
- Technology Card.
- Workflow Recommendation.
- Legacy Timeline.
- Evidence and Risk tabs.

Discriminator axes:

- Novelty.
- Utility.
- Quality impact.
- Reproducibility.
- Maturity.
- Risk.
- Fit.
- Cost.
- Security.
- Legacy relation.

API needs:

- `signal.collect(source_id)`
- `signal.normalize(signal_id)`
- `entity.extract_from_signal(signal_id)`
- `capability.map_entity(entity_id)`
- `claim.extract(entity_id)`
- `evidence.gather(claim_id)`
- `discriminator.evaluate(entity_id, axes)`
- `legacy.compare(entity_id)`
- `capability.update_ontology(entity_id)`
- `recommendation.generate_for_user(entity_id, project_id)`

Data dependencies:

- Source registry.
- Raw signals.
- Normalized technology entities.
- Claims and evidence.
- Evaluation scores.
- Legacy/supersession relationships.
- Capability Ontology.

Acceptance checks:

- A Technology Card shows what the tool is, what capability it provides, what evidence supports it, what risks exist, and what workflows it improves.
- Legacy Timeline shows what a new tool supersedes or fails to supersede.
- Recommendations can be tied to user/project context rather than global popularity.

Risks:

- Web scraping/legal constraints, especially social/community sources.
- Evaluation can become subjective without reproducible tests.
- Radar can become a news feed instead of a workflow-quality engine.

## 2. CapabilityOS / Ecosystem Framing

### 2.1 Positioning

Weak positioning to avoid:

```text
AI tools recommendation site
```

Stronger positioning:

```text
Capability orchestration platform for better AI work outcomes.
```

Short product statement:

```text
CapabilityOS analyzes a user's goal and current AI environment, then recommends and configures the best MCP, Skill, App, Agent, and workflow combination.
```

Relationship to MemoryOS:

```text
MemoryOS = context provider
CapabilityOS = capability provider
Agent Harness = execution provider
Chatbot Harness = deliberation provider
```

### 2.2 Capability Ontology

Core nodes:

- Task
- Capability
- Tool
- MCPServer
- Connector
- Skill
- Model
- AgentRuntime
- App
- Workflow
- Provider
- Cost
- QualityProfile
- Risk
- Permission
- UserContext
- Technology
- Evidence
- LegacyRelation

Core relationships:

- `Task REQUIRES Capability`
- `Tool/MCPServer/Skill PROVIDES Capability`
- `Skill IMPROVES Workflow`
- `Model GOOD_AT Capability`
- `AgentRuntime CAN_USE MCPServer`
- `Tool INTEGRATES_WITH App`
- `Workflow USES Tool/MCPServer/Skill/Model`
- `Workflow ACHIEVES Task`
- `Workflow HAS_QUALITY_PROFILE QualityProfile`
- `Workflow HAS_RISK Risk`
- `Workflow HAS_COST Cost`
- `UserContext HAS_AVAILABLE Tool`
- `Technology SUPERSEDES Technology`
- `Evidence SUPPORTS Claim`

Minimum schemas:

```json
{
  "tool_id": "figma_mcp",
  "type": "mcp_server",
  "name": "Figma MCP",
  "provider": "Figma",
  "capabilities": [
    "read_design_components",
    "read_layout_data",
    "read_design_variables",
    "generate_code_from_frames"
  ],
  "compatible_runtimes": ["claude_code", "codex", "cursor"],
  "requires_auth": true,
  "risk_level": "medium",
  "quality_impact": {
    "design_to_code": "high"
  },
  "setup": {
    "docs_url": "...",
    "install_methods": ["plugin", "mcp_config"]
  }
}
```

```json
{
  "workflow_id": "design_to_react_high_quality",
  "task": "design_to_code",
  "required_capabilities": [
    "read_design_components",
    "read_layout_data",
    "repo_edit",
    "visual_qa"
  ],
  "recommended_stack": [
    "claude_code",
    "figma_mcp",
    "github_mcp",
    "design_to_code_skill"
  ],
  "fallback_stack": [
    "chatbot_screenshot_analysis",
    "manual_css_implementation"
  ],
  "quality_tier": "high",
  "cost_tier": "medium",
  "setup_complexity": "medium"
}
```

### 2.3 Recommendation Algorithm

Inputs:

- User goal.
- Project State.
- Relevant Memory Objects.
- User current environment.
- Available runtimes.
- Available MCPs/connectors/skills.
- Budget/security preferences.

Process:

1. Classify task.
2. Extract required capabilities.
3. Scan available capabilities.
4. Calculate capability gap.
5. Find workflow candidates.
6. Score quality/cost/risk/setup/user fit.
7. Recommend workflow tiers.
8. Generate handoff or setup plan.

Scoring:

```text
workflow_score =
  task_fit * 0.30
+ capability_coverage * 0.25
+ expected_quality * 0.20
+ user_environment_fit * 0.10
+ setup_ease * 0.05
+ cost_fit * 0.05
+ risk_fit * 0.05
```

### 2.4 Ecosystem Expansion Path

Near-term:

- Personal Memory OS.
- Agent Harness.
- Design-to-Code Capability Advisor.

Medium-term:

- Project Memory Space.
- Shared Context Spaces.
- Skill and Memory Pack sharing.
- Capability Radar.

Long-term:

- Memory Pack marketplace.
- Skill marketplace.
- Agent Profile registry.
- Context Graph exchange.
- Contribution Trace and reputation.

The ecosystem should be described as a Cognitive Field or Human-Agent Field, but implemented through small concrete primitives first.

## 3. User-Facing Workflows

### 3.1 Import Conversation To Memory

User flow:

1. User opens Import Center.
2. User selects project.
3. User drops a markdown/session log or export.
4. System preserves raw archive.
5. Parser normalizes messages and pairs.
6. Extractor proposes memory drafts.
7. Hyperedge builder proposes cognitive events.
8. User reviews drafts.
9. Approved memories update Project State.

Acceptance:

- Raw file is preserved.
- Drafts contain raw refs.
- User can reject noisy extraction.
- Project State changes are visible after approval.

### 3.2 Ask "What Did We Decide?"

User flow:

1. User opens Ask Memory.
2. User asks: "What did we decide about MemoryOS desktop MVP?"
3. Retrieval Orchestrator combines keyword, vector, graph, recency, confidence, and project state.
4. Answer shows active decisions, superseded decisions, evidence refs, and unresolved questions.
5. User creates a next action or handoff.

Acceptance:

- Answer separates active/superseded/rejected/speculative.
- Evidence Pack is accessible.
- User can trace each decision to raw refs.

### 3.3 Turn Rough Idea Into Agent Handoff

User flow:

1. User enters rough idea in Deliberation Room.
2. System builds memory context pack.
3. Chatbot Harness runs role-based deliberation.
4. Synthesis Agent produces objective, constraints, risks, decisions, acceptance criteria.
5. Handoff completeness is scored.
6. User sends handoff to Agent Harness.

Acceptance:

- Handoff includes objective, context, decisions, constraints, files/scope, acceptance criteria, test plan, memory refs, expected output.
- Low-completeness handoff is blocked or requires explicit override.
- Handoff is saved as an AgentHandoffEvent.

### 3.4 Choose Best Workflow For A Goal

User flow:

1. User opens Task Planner.
2. User enters: "Implement Figma design in React."
3. CapabilityOS classifies task.
4. Capability Map scans current environment.
5. System compares low/medium/high/production workflows.
6. Capability Gap shows missing Figma MCP or visual QA.
7. User selects a workflow.
8. System creates setup plan or Agent Handoff.

Acceptance:

- Recommendation explains quality delta between screenshot-only and Figma MCP path.
- Missing capabilities are actionable.
- User can choose fallback if setup is too expensive or risky.

### 3.5 Review A New Capability

User flow:

1. Capability Radar detects a new MCP/tool/workflow.
2. Surfer creates raw signal.
3. Normalizer extracts entity, claims, install instructions, examples.
4. Discriminator evaluates novelty, utility, risk, maturity, reproducibility.
5. Legacy Stratifier links it to replaced/older workflows.
6. Technology Card appears.
7. User marks as relevant, ignored, or trial candidate.

Acceptance:

- Technology Card distinguishes marketing claims from verified evidence.
- Security and auth risks are visible.
- Trial candidate can become a Workflow or Capability entry.

## 4. API Boundary Summary

### Memory MCP / Memory Kernel

- `project.get_state`
- `project.list`
- `memory.search`
- `memory.list_drafts`
- `memory.write_draft`
- `memory.approve`
- `memory.reject`
- `hypergraph.search`
- `hypergraph.get_event`
- `context.build_pack`
- `context.commit_session`
- `handoff.create`
- `run.log_event`

### Import / Extraction

- `import.create`
- `import.get_status`
- `import.list_recent`
- `parser.detect_source`
- `parser.normalize`
- `memory.extract_drafts`
- `hyperedge.build_from_import`

### Harness

- `deliberation.create`
- `deliberation.synthesize`
- `handoff.create_from_deliberation`
- `agent.list`
- `agent.get_capabilities`
- `routing.recommend`
- `run.create`
- `run.get_status`
- `run.attach_result`

### CapabilityOS

- `task.classify`
- `capability.extract_required`
- `capability.map_user_environment`
- `capability.gap`
- `workflow.find_candidates`
- `workflow.score`
- `setup.plan`
- `setup.test_connection`
- `security.evaluate_setup`

### Capability Radar

- `signal.collect`
- `signal.normalize`
- `entity.extract_from_signal`
- `claim.extract`
- `evidence.gather`
- `discriminator.evaluate`
- `legacy.compare`
- `capability.update_ontology`
- `recommendation.generate_for_user`

## 5. Data Model Dependencies

Minimum v0 entities:

- Project
- Source
- RawArchiveItem
- Message
- Pair
- Segment
- MemoryObject
- MemoryDraft
- RawRef
- Node
- HyperedgeEvent
- ProjectState
- ContextPack
- HandoffArtifact
- Agent
- AgentRuntime
- AgentRun
- RunEvent
- Tool
- MCPServer
- Connector
- Skill
- Capability
- Workflow
- QualityProfile
- RiskProfile
- SetupPlan
- TechnologySignal
- Evidence
- Claim
- LegacyRelation

Minimum lifecycle statuses:

- Memory: draft, active, reinforced, stale, superseded, rejected, archived.
- Handoff: draft, ready, sent, running, completed, failed, archived.
- Run: queued, running, blocked, completed, failed.
- Capability: available, partial, missing, blocked, deprecated.
- Technology: raw, normalized, evaluated, accepted, ignored, superseded.

## 6. Build Order

### Milestone 1: File Substrate + Import Loop

Build:

- Raw archive preservation.
- Markdown/session log import.
- Normalized messages/pairs.
- Draft Memory Objects.
- Basic Draft Review.

Do not build:

- Full graph visualization.
- Auto-install.
- Marketplace.

Acceptance:

- One session log can become reviewed Memory Objects with raw refs.

### Milestone 2: Project State + Ask Memory

Build:

- Project State generation.
- Active decisions/open questions/next actions.
- Hybrid search over text and memory metadata.
- Evidence Pack display.

Acceptance:

- User can ask what was decided and inspect evidence.

### Milestone 3: Handoff + Agent Harness View

Build:

- Context Pack schema.
- Handoff Artifact schema.
- Handoff completeness scoring.
- Agent Run/Event Log records.
- Manual export/send handoff path.

Acceptance:

- Rough spec can become an auditable handoff with context refs.

### Milestone 4: Deliberation Room

Build:

- User Intent intake.
- Memory context retrieval.
- Role panels, initially manual/API-stub friendly.
- Synthesis output.
- Handoff generation.

Acceptance:

- Ambiguous request is refined before execution.

### Milestone 5: CapabilityOS Advisor

Build:

- Capability Ontology v0.
- Task Planner.
- Capability Map.
- Capability Gap.
- Workflow scoring.
- Design-to-Code vertical first.

Acceptance:

- User goal produces workflow tiers and missing capability actions.

### Milestone 6: Capability Radar

Build:

- Source registry.
- Manual/limited signal ingestion.
- Technology Card.
- Discriminator scores.
- Legacy Timeline.

Acceptance:

- New tool/workflow can be evaluated and mapped to tasks.

## 7. Cross-Cutting Acceptance Checks

- Local-first is default for memory data.
- Raw archive, normalized records, graph relations, and embeddings remain distinguishable.
- User-originated ideas are separable from AI-suggested ideas.
- Claims link to evidence or carry unsupported/speculative status.
- Disagreement and uncertainty are first-class.
- Agents can suggest memory, but committed memory has review/approval policy.
- Every handoff has objective, constraints, acceptance criteria, and context refs.
- Every agent run has an event log.
- Capability recommendations show quality, cost, risk, setup complexity, and environment fit.
- Databases/UI read from a stable file substrate until schema hardens.

## 8. Key Risks

### Product Risks

- Scope inflation from memory tool into full cognitive economy before primitives work.
- Users may not review drafts if the queue is too noisy.
- Graph visuals can distract from evidence, decisions, and next actions.
- CapabilityOS can look like a generic AI directory if capability/task mapping is weak.

### Technical Risks

- Parser heterogeneity across providers.
- Weak extraction quality without deterministic schemas and review.
- Search quality issues if vector retrieval is used without graph/status/evidence filters.
- MCP/tool setup changes frequently.
- Multi-provider deliberation costs and latency.

### Trust/Safety Risks

- Origin confusion between user and assistant ideas.
- Unsupported claims accidentally promoted into project truth.
- Auto setup requiring broad permissions or leaking API keys.
- Web-source ingestion violating platform terms if scraping is too aggressive.

### Ecosystem Risks

- Marketplace/reputation concepts require contribution trace integrity.
- Shared context spaces need access control and privacy design.
- Workflow quality claims need evidence or benchmarks to avoid marketing drift.

## 9. Immediate Next Work Items

1. Define `MemoryObject`, `RawRef`, `HyperedgeEvent`, `ContextPack`, and `HandoffArtifact` schemas.
2. Implement markdown/session log import into raw archive and normalized messages.
3. Build Draft Review as the first quality-control UI.
4. Build Project State from approved memories.
5. Add Ask Memory with evidence packs.
6. Add Handoff Generator with completeness checks.
7. Seed Capability Ontology with Design-to-Code vertical.
8. Build Task Planner and Capability Gap over seeded ontology.

