# MemoryOS Harness TUI

`mos` is the first wrapper CLI/TUI for the structured agent blackboard described in `docs/tui.md`.

## Commands

```bash
python -m memoryos.mos init
scripts/install-mos-cli.sh
mos "Build Draft Review screen"
mos run -q --json "Build Draft Review screen"
mos plan
mos tui
mos completion zsh
```

Without installing:

```bash
python -m memoryos.mos init
python -m memoryos.mos doctor
python -m memoryos.mos local status
python -m memoryos.mos local setup
python -m memoryos.mos agents detect
python -m memoryos.mos settings detect
eval "$(python -m memoryos.mos settings shell)"
python -m memoryos.mos run "Build Draft Review screen"
python -m memoryos.mos ask "Build Draft Review screen"
python -m memoryos.mos plan
python -m memoryos.mos status
python -m memoryos.mos tui
python -m memoryos.mos context
python -m memoryos.mos handoff
python -m memoryos.mos invoke local --role context
python -m memoryos.mos invoke claude --role planner
python -m memoryos.mos invoke codex --role executor
python -m memoryos.mos invoke gemini --role reviewer
python -m memoryos.mos verify
python -m memoryos.mos summarize
python -m memoryos.mos memory draft
```

If installed as a package, `mos` points to the same command.

`mos "your task"` is shorthand for `mos ask "your task"`.

For a fast local workbench loop:

```bash
scripts/mos-workbench.sh "your task"
```

This creates or reuses a run, persists provider/runtime settings, opens the context pack in `$EDITOR`, prepares Claude/Codex/Gemini artifacts, runs verification, and opens the TUI. Set `MOS_SKIP_EDIT=1` or `MOS_OPEN_TUI=0` for scripted runs.

## Onboarding

`python -m memoryos.mos init` is idempotent. It creates:

```text
~/.memoryos/
  config.yaml
  agents.yaml
  routing.yaml
  skills/
  runs/
  imports/
  db/
  logs/
  mcp/
  cache/

project/.memoryos/
  project.yaml
  routing.yaml
  README.md
  runs/
  context/
  skills/
```

It also initializes `.runs/`, runs provider detection, writes `.runs/provider_capabilities.json`, scans local Ollama model manifests, writes `.memoryos/local_runtime.json`, and prints next actions.

It also writes a production settings profile:

```text
~/.memoryos/settings_profile.json
project/.memoryos/settings_profile.json
```

That profile tracks provider command paths, versions, roles, modes, local model inventory, warnings, and shell exports such as `MOS_CODEX_BIN`. This matters when a PATH wrapper is pinned ahead of the real provider binary. On this machine, `/home/user/bin/codex` is gated, while the usable Codex CLI is detected at `/home/user/.nvm/versions/node/v22.22.2/bin/codex`.

## TUI Keybindings

Inside `python -m memoryos.mos tui`:

```text
q  quit
r  refresh
n  enter a new prompt, create a run, and auto-route it
e  edit context_pack.md in $EDITOR
a  auto-route current task through local intent router
l  invoke local context compressor
c  create Claude planner prompt
x  create Codex executor prompt
g  create Gemini reviewer prompt
v  create verification report
s  update final_report.md
m  create memory_drafts.json
```

The TUI does not try to be the final product UI. It is an operational control surface for driving agent work through run artifacts.

## Run Folder

Each run is a structured blackboard under `.runs/`:

```text
.runs/
  current
  run_YYYYMMDD_HHMMSS_xxxxxx/
    task.yaml
    context_pack.md
    handoff.yaml
    events.jsonl
    run_state.json
    verification.yaml
    memory_drafts.json
    final_report.md
    agents/
      local/
      claude/
      codex/
      gemini/
    artifacts/
```

The TUI reads `run_state.json` and `events.jsonl`. It does not require a database.

## Local Worker Behavior

For prompt-first work, use:

```bash
python -m memoryos.mos ask "your task"
```

`mos ask` creates or reuses a run, asks the local `intent_router` worker to decompose the prompt, writes `routing_plan.json`, and prepares the matching Claude/Codex/Gemini/local artifacts. If Ollama is unreachable, it writes a heuristic fallback route so the run remains usable instead of blocking.

Inside `mos tui`, press `n` to enter a fresh prompt directly. The TUI creates a new run and routes it through the same local intent router. Press `a` to re-route the current run.

`mos invoke local --role ...` writes an artifact even when Ollama is unavailable. This keeps the run trace complete and makes infrastructure failures visible in the TUI instead of crashing the harness.

`mos local status` reports the local runtime without requiring hosted provider keys. `mos local setup` writes `.memoryos/local_runtime.json` with the detected wrapper, server state, and model manifests.

DeepSeek and Qwen have two separate paths:

- Local open-weight models through Ollama: no API key required.
- Hosted HTTP providers: require `DEEPSEEK_API_KEY` or `QWEN_API_KEY`.

The current local manifests include `deepseek-coder:6.7b`, `deepseek-coder-v2:16b`, `qwen3:1.7b`, and `qwen3:8b`.

Supported local roles:

- `context`
- `handoff`
- `summarize`
- `memory`
- `review`
- `classify`

## Provider Harness

Provider CLIs are treated as workers behind the same artifact protocol.

```bash
python -m memoryos.mos invoke claude --role planner
python -m memoryos.mos invoke codex --role executor
python -m memoryos.mos invoke gemini --role reviewer
```

These commands create:

```text
agents/<provider>/<role>_prompt.md
agents/<provider>/<role>_command.txt
```

For supported non-interactive execution:

```bash
python -m memoryos.mos invoke claude --role planner --execute
python -m memoryos.mos invoke gemini --role reviewer --execute
```

`codex` uses the documented non-interactive shape:

```bash
codex exec --cd . --sandbox read-only --ask-for-approval never "$(cat .runs/<run>/agents/codex/reviewer_prompt.md)"
```

In the current machine session, the command exists but execution is gated by a local access prompt, so failures are captured as `result.yaml` and `output.md` artifacts instead of crashing the harness.

The installed provider commands currently visible to the harness are:

- `claude`
- `codex` (`exec` contract known; local execution currently gated)
- `gemini` (`gemini --version` reported `0.40.1`)

Use `python -m memoryos.mos settings detect` to refresh the profile after installing or changing provider CLIs. Use `eval "$(python -m memoryos.mos settings shell)"` before custom shell scripts that need the resolved binaries.

## Current Boundary

This is intentionally not the Desktop cockpit. It is the first stable loop:

```text
manual shared folder
  -> structured blackboard
  -> wrapper CLI
  -> TUI status
  -> later Desktop cockpit
```
