# Hive Mind

Status: public alpha candidate for the local provider-CLI harness.

Hive Mind is a local swarm harness for existing provider CLIs and local LLM workers.

It coordinates installed tools such as Claude, Codex, Gemini, and Ollama-backed local workers into one shared run state. It does not replace provider CLIs; it wraps them into a user-governed blackboard loop.

## First Five Minutes

Run the provider-free demo first. It shows the value path without API keys or
local models:

```bash
python -m hivemind.hive demo quickstart
```

That creates a Hive run with role routing, agent artifacts, verification,
memory draft, inspect summary, and a MemoryOS-compatible observability graph.

Then run the feedback-loop demo if the sibling `../memoryOS` repo is present:

```bash
python -m hivemind.hive demo memory-loop
```

That proves the closed loop:

```text
Hive run -> memory draft -> MemoryOS import/approval -> next Hive run context
```

After the demos, the normal operator path is:

```bash
python -m hivemind.hive init
python -m hivemind.hive run "your task"
python -m hivemind.hive inspect <run_id>
python -m hivemind.hive goal
```

Use direct Claude/Codex/Gemini CLIs for trivial one-shot commands. Use Hive
when the task needs receipts, policy gates, stop/replay/inspect, multiple
agents, or MemoryOS feedback.

This release is limited to bounded local runtime orchestration. It is not a
general agent operating system, not an end-to-end memory substrate, and not a
long-running autonomous planner.

## Current Modules

- `hivemind/` — `hive` CLI, provider adapters, TUI, local workers, run validation.
- `.runs/` — Hive Mind run blackboard and per-agent artifacts.
- `.hivemind/` — project settings, checks, runtime profile, local logs.
- `docs/` — shared architecture notes and Hive Mind operating docs.

Memory graph importers, schemas, graph store, and audit code live in the sibling
`../memoryOS` repo. Capability graph work belongs in the sibling
`../CapabilityOS` repo.

## Operator Workbench

```bash
scripts/install-hive-cli.sh
hive init
hive demo quickstart       # first value demo, no provider keys required
hive demo memory-loop      # optional Hive -> MemoryOS -> Hive feedback demo
hive run "your task"
hive inspect <run_id>
hive goal
hive tui                   # optional interactive console
```

Or without installing:

```bash
python -m hivemind.hive init
scripts/hive-workbench.sh "your task"
```

Memory graph import/audit code has moved to the sibling `memoryOS` repo:

```bash
cd ../memoryOS
python -m memoryos.cli stats
python -m memoryos.cli import-run --root ../hivemind current --dry-run
```

Onboarding persists detected provider/runtime settings to `.hivemind/settings_profile.json` and `~/.hivemind/settings_profile.json`. Use `eval "$(python -m hivemind.hive settings shell)"` when launching provider CLIs from custom scripts.

## Contributing

Contributor and internal workspace notes live in `CONTRIBUTING.md` and
`AGENTS.md`. Public users can start with the demos above.
