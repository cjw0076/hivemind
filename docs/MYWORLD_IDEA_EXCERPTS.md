# MyWorld Idea Excerpts

Source: `/home/user/workspaces/jaewon/universe/quantum/northstar/shift/my_world.md`

Purpose: Claude/Codex/User sessions in `/home/user/workspaces/jaewon/myworld` should read this first to recover the MyWorld agent-system idea without loading the full 11k-line source file.

## 0. Guardrail

This file is for the MyWorld / multi-ontology / agent-system project. It is not a Paper #4 manuscript source.

Keep the distinction strict:

- `universe/quantum/`: quantum identifiability, P18, Paper #4, NeurIPS sprint.
- `myworld/`: agent memory, ontology graph, reflective critique loop, multi-agent research operating system.

Vision language is allowed here as design context. It should not leak into quantum paper claims.

## 1. Minimal Research Operating System

Relevant source idea:

> 기계화된 진리 탐구를 가능하게 하는 최소 연구 운영체제.

The minimal system is not a general chatbot. It is a research operating system that keeps hypotheses, observations, critiques, and revisions explicit.

Minimum components:

1. Quantum Paper #4: Born Branch Collapse Curve / Identifiability Basin Map / Auditor.
2. Dipeen Research Workflow: Claude/Codex/GPT roles; record judgments as markdown.
3. GoEN Personal Loop: today tasks / failure causes / next action / prevent overabstraction.
4. Asimov Ontology Note: time / space / causality / observation / intervention / truth as common language.

Operational translation for MyWorld:

- Store every important agent decision as a durable note.
- Separate generation, critique, implementation, and audit.
- Track which claims are supported, unsupported, speculative, or rejected.
- Let the ontology graph change only through logged observations or explicit user decisions.

## 2. Agent System Idea

Relevant source idea:

> Dipeen은 단일 agent가 아니라 agent들의 상호작용으로 생기는 집단적 사고를 다룬다.

> 여러 agent를 군체처럼 써서 하나의 확장된 인지 시스템을 만드는 것.

MyWorld should treat agents as a structured research ensemble, not as one omniscient assistant.

Working roles:

| Role | Primary function | Failure mode to watch |
| --- | --- | --- |
| User | final taste, direction, acceptance, philosophical boundary | moving too fast without freezing decisions |
| Codex | implementation, filesystem state, reproducible scripts, logs | overbuilding before evidence |
| Claude | critique, reviewer voice, conceptual risk, claim discipline | staying at critique without executable path |
| GPT / other models | ideation, alternative framing, external pressure tests | persuasive but unsupported synthesis |

The useful object is not any single answer. The useful object is the logged disagreement, resolution, and next action.

## 3. Project Roles And Integration

Relevant source idea:

> Quantum을 연구하고, Dipeen으로 사고하며, Goen으로 너 자신을 업데이트하고, Asimov로 장기 세계관을 보존한다.

Interpretation:

- Quantum is the empirical testbed.
- Dipeen is the multi-agent thinking workflow.
- GoEN is the self-updating ontology / memory graph.
- Asimov is the long-horizon ontology for time, space, causality, observation, intervention, and truth.

MyWorld should implement the non-quantum infrastructure that lets those layers talk:

1. A persistent memory layer.
2. An ontology graph layer.
3. A run/session log layer.
4. A critique/audit layer.
5. A model/provider adapter layer.

## 4. Reflective Graph Loop

Core loop from source:

```text
Generate -> Objectify -> Relate -> Critique -> Rewire -> Act -> Observe -> Update
```

Expanded architecture:

```text
Forward Generator
  -> Graph / Objectification Layer
  -> Reflective Critique Layer
  -> Identifiability / Uncertainty Auditor
  -> Intervention / Experiment Planner
  -> Observation
  -> Graph Plasticity Update
  -> Theory Revision
```

Meaning:

- `Generate`: produce candidate hypotheses, plans, explanations, or worlds.
- `Objectify`: turn them into durable nodes with IDs, claims, assumptions, and evidence links.
- `Relate`: connect nodes by support, contradiction, dependency, analogy, or derivation.
- `Critique`: attack the graph from reviewer / skeptic / adversarial perspectives.
- `Rewire`: update graph edges and statuses after critique.
- `Act`: run code, experiment, reading, or user decision.
- `Observe`: record the result.
- `Update`: revise graph state and next actions.

This loop is the first executable target for MyWorld.

## 5. Quantum As Testbed

Quantum loop from source:

```text
Born marginal observation
  -> Hidden world reconstruction
  -> Candidate world graph
  -> Identifiability auditor
  -> Branch collapse analysis
  -> Next measurement suggestion
  -> Intervention protocol
  -> New Born observation
  -> Theory / ontology update
```

For MyWorld, quantum should be used as a high-quality example domain, not as the whole system.

The important abstraction is:

```text
partial observation
  -> candidate hidden structures
  -> uncertainty / identifiability audit
  -> next intervention
  -> new observation
  -> theory update
```

That abstraction can later apply to research planning, memory consolidation, ontology revision, and multi-agent disagreement resolution.

## 6. North Star

Relevant source sentence:

> 부분 관측된 세계에서, 숨은 상태·법칙·관계·개입 효과를 복원하고, 무엇이 식별 가능하고 무엇이 불가능한지 판정하며, 다음 관측과 자기수정을 설계하는 기계적 진리 탐구 시스템을 만든다.

Working English version:

Build a mechanical truth-seeking system that, under partial observation, reconstructs hidden states, laws, relations, and intervention effects; decides what is identifiable or non-identifiable; and designs the next observation and self-update.

This is the MyWorld north star. It is not a claim that the MVP already satisfies it.

## 7. Layer Names

From source:

| Layer | Name | Meaning |
| --- | --- | --- |
| Layer 0 | Quantum / BMIF | Born-Marginal Identifiability Framework |
| Layer 1 | GoEN-RT | GoEN Reverse Translation / cognitive compiler stack |
| Layer 2 | Dipeen | Plastic Hypergraph Swarm Cognition |
| Layer 3 | GoEN | Graph Ontology Evolution Network |
| Layer 4 | Asimov | Spacetime-Causality Ontology |

Related terms:

- `MIGS`: Minimal Invariant Generative Structure.
- `BLIGA`: Born-Lindblad Interventional Generative Architecture. Treat as historical / speculative unless explicitly revived.

## 8. Execution Phases

Source-derived phase order:

1. Phase 1: Quantum first / Paper #4.
2. Phase 2: GoEN-RT as research memory compiler.
3. Phase 3: Dipeen as research OS.
4. Phase 4: GoEN plasticity rule-based ontology update.
5. Phase 5: Asimov as long-term ontology.

Current MyWorld implementation should start at Phase 2/3 infrastructure:

- ingest notes;
- create durable claim nodes;
- record agent critiques;
- maintain a session/shared log;
- expose a small CLI or local API before building a large UI.

## 9. Immediate Build Target

Smallest useful MyWorld MVP:

```text
input markdown/session log
  -> extract claims, decisions, assumptions, TODOs
  -> store as nodes
  -> link evidence and disagreements
  -> run critique/audit pass
  -> emit next actions and unresolved questions
```

The MVP should prefer explicit files and simple schemas before database complexity.

Suggested first directories:

```text
myworld/
  agents/      # role prompts, adapters, orchestration notes
  memory/      # durable extracted memories and claim nodes
  ontology/    # graph schema, relation types, ontology snapshots
  runs/        # execution traces and experiment outputs
  docs/        # architecture and source excerpts
  .ai-runs/    # Claude/Codex/User shared logs
```

## 10. Boundaries

Do:

- Preserve disagreements.
- Keep claims evidence-linked.
- Separate vision, design, and executable implementation.
- Let paper/experiment results update the ontology, not the reverse.

Do not:

- Turn MyWorld into only a chatbot wrapper.
- Mix quantum Paper #4 claims with speculative ontology prose.
- Use tetration/power-tower language as a scientific anchor.
- Start with a large agent swarm before the memory/graph/log substrate works.
