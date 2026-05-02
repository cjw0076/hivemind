# Repo Split

This workspace is bootstrapped as three private product repositories:

```text
hivemind     -> swarm orchestration runtime and CLI/TUI
memoryOS     -> local-first memory graph substrate
CapabilityOS -> capability graph, workflow recipes, and tool ontology
```

## Local Layout

```text
myworld/                 # umbrella workspace, not a product repo
├── hivemind/            # Git remote: cjw0076/hivemind
│   ├── docs/            # shared north-star and architecture docs
│   ├── .runs/           # local Hive Mind run blackboard artifacts
│   ├── .ai-runs/shared/ # cross-agent communication log
│   └── .hivemind/       # local Hive Mind memory pointers
├── memoryOS/            # Git remote: cjw0076/memoryOS
└── CapabilityOS/        # Git remote: cjw0076/CapabilityOS
```

The umbrella `myworld/` directory is a local workspace, not the canonical
product repo. Each child directory has its own `.git` directory and commit
history.

## Shared Docs

During bootstrap, `hivemind/docs/` remains the shared source of truth for the
whole stack. The `memoryOS` and `CapabilityOS` repos use local symlinks at
`docs/shared` that point back to `../../hivemind/docs`.

Canonical orientation docs:

- `docs/final.md`
- `docs/NORTHSTAR.md`
- `docs/ROADMAP.md`
- `docs/TODO.md`
- `docs/hive_mind.md`
- `docs/memoryOS.md`
- `docs/capabilityOS.md`

## Session Memory

Past work sessions remain in the Hive Mind repo at `myworld/hivemind/`:

- `.runs/` stores run blackboard artifacts.
- `.ai-runs/shared/comms_log.md` stores human-readable agent handoffs.
- `.hivemind/session_memory.md` indexes these locations for local agents.

MemoryOS should later ingest these artifacts as structured memory objects, but
Hive Mind owns the working run history for now.
