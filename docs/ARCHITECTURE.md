# MyWorld Architecture Draft

## Core Loop

```text
input / observation
→ parse into claims, evidence, uncertainty, intent
→ attach to ontology graph
→ compare against existing memory
→ detect contradiction, novelty, salience, and open branches
→ assign agent tasks
→ write completed conclusions back into durable memory
```

## First-Class Objects

- `Observation`: raw input, file, experiment result, conversation, or external event.
- `Claim`: a statement that may be true, false, partial, or context-dependent.
- `Evidence`: supporting file, result, citation, metric, or log.
- `Uncertainty`: what is unknown, underdetermined, or disputed.
- `Branch`: multiple compatible interpretations that have not collapsed.
- `Decision`: a stable conclusion used for future work.
- `Task`: an action assigned to an agent or user.
- `OntologyNode`: concept or structure that persists across tasks.

## Agent Roles

- `Builder`: implements code and file changes.
- `Critic`: reviews claims, risks, and missing evidence.
- `Archivist`: extracts durable conclusions and keeps references clean.
- `Mapper`: maintains ontology graph and branch structure.
- `Auditor`: distinguishes known, unknown, ambiguous, and overclaimed states.

## Immediate MVP

1. Define a small JSON/YAML schema for claims, evidence, decisions, and branches.
2. Build a local append-only memory log.
3. Build an ontology index that links notes across projects.
4. Add a simple CLI for:
   - capture
   - summarize
   - search
   - link
   - audit

## Guardrails

- Do not mix speculative ontology language into `universe/quantum` paper drafts.
- Keep experimental evidence linked to source files.
- Preserve uncertainty instead of forcing a single conclusion.
- Completed conclusions should be reusable without rereading whole chat logs.

