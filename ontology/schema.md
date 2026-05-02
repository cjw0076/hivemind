# MemoryOS Graph Schema

MemoryOS starts as an append-only local graph. Databases, vector indexes, and UI layers should read from this substrate instead of becoming the source of truth.

## Node Types

- `observation`: raw imported file, note, session log, or archive.
- `conversation`: AI conversation container.
- `message`: one user, assistant, system, or tool turn.
- `pair`: nearest user input and assistant output pair.
- `claim`: statement that may be true, false, partial, speculative, or rejected.
- `decision`: stable conclusion used for future work.
- `assumption`: premise or unresolved interpretation.
- `task`: action that should happen.
- `question`: unresolved question.
- `concept`: reusable project, idea, platform, model, or ontology term.

## Edge Types

- `contains`: parent container holds a child node.
- `next`: temporal order between turns.
- `answered_by`: user message answered by assistant message.
- `mentions`: text node mentions concept node.
- `extracts`: extracted claim/decision/task/question came from a parent node.
- `supports`: evidence supports claim.
- `contradicts`: node conflicts with another node.
- `motivates`: claim or decision motivates task.
- `depends_on`: task or claim depends on another node.
- `about`: broad topic relation.

## Storage

- Nodes: `memory/processed/nodes.jsonl`
- Edges: `ontology/edges.jsonl`
- Reports: `runs/reports/`

Every row has a stable ID and source pointer. This makes re-import duplication tolerable for now and gives later deduplication a clear target.
