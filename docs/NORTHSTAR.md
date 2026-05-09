# MemoryOS North Star

MemoryOS is a local-first personal memory and ontology operating system for AI-era work.

Its goal is to turn scattered AI conversations, research notes, files, decisions, claims, experiments, and agent actions into a durable graph that can be searched, audited, revised, and used by future agents.

## Core Thesis

LLMs are strong forward generators: they fluently predict, associate, compress, and verbalize. But without persistent structure, they do not reliably preserve what the user has already decided, what remains uncertain, what evidence supports a claim, or how a project changed over time.

MemoryOS adds the missing reflective loop:

```text
Generate
  -> Objectify
  -> Relate
  -> Critique
  -> Rewire
  -> Act
  -> Observe
  -> Update
```

The system should not merely store chats. It should objectify thoughts into claims, decisions, assumptions, tasks, questions, concepts, evidence, contradictions, and project trajectories.

## One-Sentence Product Definition

MemoryOS turns all of a user's AI conversations and research artifacts into a private, searchable, auditable memory graph that helps recover decisions, unresolved questions, project ontology, and next actions.

## One-Sentence Research Definition

MemoryOS/Dipeen is the external ontology substrate, GoEN is the internal structural-plasticity substrate, and the full system studies whether reflective graph rewiring improves long-horizon reasoning, memory consistency, and self-revision.

## Working Model

```text
LLM
  = unconscious forward generator

GoEN Reverse Translation
  = language -> claim/event/intent/uncertainty/ontology structure

Dipeen / MemoryOS Hypergraph
  = externalized self-memory and ontology substrate

Swarm Agents
  = reflective operators over the graph

GoEN
  = graph plasticity learner / adaptive structural substrate

Self-awareness loop
  = LLM output -> graphification -> critique -> rewire -> next action
```

## Memory Layers

MemoryOS should grow in layers, not as a large monolith.

| Layer | Name | Purpose |
| --- | --- | --- |
| 0 | Raw Archive | Preserve original exports, notes, files, and logs. |
| 1 | Message Ledger | Normalize conversations, messages, timestamps, roles, models, and sources. |
| 2 | Pair Dataset | Build user-input / assistant-output pairs for replay, eval, and later training. |
| 3 | Semantic Memory | Embed messages, pairs, segments, summaries, and user-only thoughts. |
| 4 | Concept Graph | Link projects, concepts, claims, decisions, tasks, evidence, contradictions. |
| 5 | Reflective Agents | Run archivist, critic, planner, synthesizer, and guardian passes. |
| 6 | Plastic Hypergraph | Support node/edge retyping, merging, splitting, pruning, promotion, and revision. |
| 7 | Personal Thought Encoder | Project general embeddings into the user's personal semantic space. |

## Design Commitments

- Local-first before cloud-first.
- Official exports and user-provided files before scraping.
- User-originated ideas must be separable from AI-suggested ideas.
- Raw text, normalized records, graph relations, and embeddings must remain distinguishable.
- Uncertainty and disagreement are first-class, not cleanup noise.
- Claims need evidence links or an explicit unsupported/speculative status.
- The first working loop matters more than the full visual board.
- Databases and UI layers should read from a stable file substrate until the schema hardens.
- Agent work must become durable artifacts before it becomes memory.
- Capability recommendations must be evidence-backed workflow records, not tool-name lists.
- Local LLM output is draft worker output; Claude/Codex/user review remains the authority for high-impact decisions.
- Future UX must hide directories, run folders, and filesystem mechanics by default. The user-facing surface is prompt input plus live logs/decisions; files remain the internal substrate and debug/export layer.
- Hive Mind should not become the final visual app. It owns prompt intake, chair orchestration, ledger/protocol state, and provider execution records; MemoryOS owns the long-term neural-map observability UI over that state.

## Operating Stack

MemoryOS now sits inside a broader Human-AI-Agent Operating Stack:

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
```

Near-term, this stack is implemented through the `hive` harness and file-backed run folders, not a large autonomous swarm.

Long-term, this becomes an AIOS-style operator layer rather than an app. The
user should not have to browse directories, inspect run folders, or manage
artifact paths during normal work. The system should accept prompts, execute the
appropriate chaired workflow, and expose only the live log, decisions, blocked
questions, risk gates, and final outcomes. Terminal/TUI, desktop, and file views
are transitional control/debug surfaces over the same operating layer.

When Hive Mind is attached to MemoryOS, Hive should provide prompt intake plus a
stable read model/event stream. MemoryOS should render the user's main
observability surface as a neural map: agent turns, authority gates, memory
nodes, claims, disagreements, evidence, and task flow become graph events rather
than file paths or terminal panels. `hive tui` remains useful as an operator
console and debugging harness, but it is not the product north star.

Roles:

- MemoryOS remembers decisions, claims, evidence, disagreements, project state, and agent runs.
- MemoryOS owns the neural-map observability UI and accepted-memory review surface.
- CapabilityOS maps tools, models, MCP servers, skills, connectors, workflows, risks, quality tiers, and legacy comparisons.
- The `hive` harness turns user prompts into chaired workflows, task specs, context packs, handoffs, provider artifacts, ledger/protocol records, verification reports, and memory drafts.
- Local LLM workers classify, extract, compress, summarize, and draft handoffs as cheap provider-like workers.
- Claude, Codex, Gemini, and future providers plug into the same artifact protocol according to their strengths.
- Agent Society records performance, peer review, user feedback, and routing proposals, but prompt/routing mutations require review.
- Review independence is a function of both provider family and context basin.
  Agents working from sibling directories or clean checkouts can produce sharper
  critique because they are less coupled to the target repo's local consensus.
  Repeated cross-basin interaction increases coupling and should be tracked
  rather than treated as permanent independence.

## Key Questions The System Must Answer

- What did I decide, and when?
- What questions keep recurring without resolution?
- Which ideas are mine, which came from AI, and which were accepted or abandoned?
- What evidence supports or contradicts this claim?
- How did this project ontology evolve over time?
- Where do GPT, Claude, Gemini, Grok, DeepSeek, and Perplexity disagree on the same topic?
- What next action is justified by the current graph?
- Which old claim is stale because newer evidence changed the context?
- Which provider, local worker, skill, MCP, or workflow is justified for this task?
- Which agent handoff is complete enough to execute safely?
- Which agent recommendation was accepted, rejected, or contradicted by later evidence?

## Research North Star

Build a reflective graph control loop that preserves and rewires a user's long-term cognitive work:

```text
partial observation / conversation / file
  -> reverse-translate into structured memory
  -> maintain multiple meaning branches when ambiguous
  -> link claims to evidence, tasks, projects, and contradictions
  -> run critique and planning agents
  -> update the graph through explicit plasticity operations
  -> feed the revised state into future LLM calls
```

The measurable target is not "consciousness." The measurable target is reflective control: better recall, contradiction detection, plan repair, project continuity, and ontology revision than raw text, vector-only memory, static summaries, or static knowledge graphs.
