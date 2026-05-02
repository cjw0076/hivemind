# Hive Mind CLI/TUI

`hive` is the Hive Mind control plane for the structured agent blackboard described in `docs/tui.md`. It combines already-installed provider CLIs and local LLM workers instead of replacing their native interfaces.

## Commands

```bash
python -m hivemind.hive init
scripts/install-hive-cli.sh
hive
hive "Build Draft Review screen"
hive run -q --json "Build Draft Review screen"
hive plan
hive check list
hive check run
hive diff
hive review-diff
hive commit-summary
hive agents detect --json
hive agents status
hive chat
hive orchestrate "Build parser and review risks"
hive next
hive prompt
hive log
hive hive activity
hive memory list
hive tui
hive completion zsh
npm run production
```

Without installing:

```bash
python -m hivemind.hive init
python -m hivemind.hive doctor
python -m hivemind.hive local status
python -m hivemind.hive local setup
python -m hivemind.hive agents detect
python -m hivemind.hive settings detect
eval "$(python -m hivemind.hive settings shell)"
python -m hivemind.hive run "Build Draft Review screen"
python -m hivemind.hive ask "Build Draft Review screen"
python -m hivemind.hive plan
python -m hivemind.hive status
python -m hivemind.hive next
python -m hivemind.hive tui
python -m hivemind.hive context
python -m hivemind.hive handoff
python -m hivemind.hive invoke local --role context
python -m hivemind.hive invoke claude --role planner
python -m hivemind.hive invoke codex --role executor
python -m hivemind.hive invoke gemini --role reviewer
python -m hivemind.hive verify
python -m hivemind.hive summarize
python -m hivemind.hive memory draft
python -m hivemind.hive memory list
```

If installed as a package, `hive` and `hivemind` point to the same command.
`mos` is also installed as a deprecated compatibility alias so old shell history
does not break during the rename.

`hive "your task"` is shorthand for `hive orchestrate "your task"`.
Bare `hive` opens the conversational operator shell. Use `hive chat` explicitly for the same shell, or `hive shell` for the older thin slash-command shell. Use `hive tui` for the curses status board.

`hive orchestrate` is the default prompt path. It asks the local router to split the request into a small agent society, prepares each provider/local worker artifact, writes `society_plan.json`, and reports which member owns which role. `hive ask` remains available for route-only debugging.

Hive Mind keeps `events.jsonl` as a machine/audit log and `hive_events.jsonl` as the human activity feed. The TUI latest-events panel prefers `hive_events.jsonl`, so it shows role assignment and swarm decisions instead of only file-created events.

`hive status` prints the run board: pipeline, agent status, artifact status, and the next recommended command. `hive next` prints only the next action for fast terminal loops.

`hive check run` evaluates markdown policy files under `.hivemind/checks/`. `hive diff`, `hive review-diff`, and `hive commit-summary` provide the first git-aware loop without committing automatically.
`hive prompt` reads a multiline/stdin prompt and routes it through the local intent router. `hive log` shows the current run `transcript.md`.

Provider and local worker activity is mirrored into per-agent log files under
`agents/<provider>/<role>.log`, the human activity feed, and `transcript.md`.
When a provider supports execution, stdout lines are streamed into those logs
while the process is running. The TUI dashboard tails `transcript.md` in the
`Live Transcript` panel.

Production wrappers:

```bash
scripts/install-hive-cli.sh
npm run production
npm link
bin/hive doctor
```

`bin/hive` executes `python -m hivemind.hive` from the repo root. The npm package is private and exists as a local production wrapper, not a published registry package.

For a fast local workbench loop:

```bash
scripts/hive-workbench.sh "your task"
```

This creates or reuses a run, persists provider/runtime settings, opens the context pack in `$EDITOR`, prepares Claude/Codex/Gemini artifacts, runs verification, and opens the TUI. Set `HIVE_SKIP_EDIT=1` or `HIVE_OPEN_TUI=0` for scripted runs.

## Onboarding

`python -m hivemind.hive init` is idempotent. It creates:

```text
~/.hivemind/
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

project/.hivemind/
  project.yaml
  routing.yaml
  README.md
  runs/
  context/
  skills/
```

It also initializes `.runs/`, runs provider detection, writes `.runs/provider_capabilities.json`, scans local Ollama model manifests, writes `.hivemind/local_runtime.json`, and prints next actions.

It also writes a production settings profile:

```text
~/.hivemind/settings_profile.json
project/.hivemind/settings_profile.json
```

That profile tracks provider command paths, versions, roles, modes, local model inventory, warnings, and shell exports such as `HIVE_CODEX_BIN`. This matters when a PATH wrapper is pinned ahead of the real provider binary. On this machine, `/home/user/bin/codex` is gated, while the usable Codex CLI is detected at `/home/user/.nvm/versions/node/v22.22.2/bin/codex`.

## TUI Keybindings

Inside `python -m hivemind.hive tui`:

```text
q  quit
r  refresh
enter  open an interactive input line
/  open an interactive slash-command input line
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
d  capture git diff report
h  show keybinding hint
```

Large terminals render the dashboard as a control plane: run/health summary, pipeline, agents, artifacts, latest events, next actions, keybar, and an always-visible `hive>` composer. The TUI is interactive: press `Enter` and type a normal prompt to create and route a new run, or press `/` to enter slash commands such as `/verify`, `/memory`, `/summary`, `/diff`, `/local`, `/claude`, `/codex`, and `/gemini`.

The TUI does not try to be the final desktop UI. It is an operational control surface for driving agent work through run artifacts: pipeline first, agent aware, artifact driven, audit friendly.

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
python -m hivemind.hive ask "your task"
```

`hive ask` creates or reuses a run, asks the local `intent_router` worker to decompose the prompt, writes `routing_plan.json`, and prepares the matching Claude/Codex/Gemini/local artifacts. If Ollama is unreachable, it writes a heuristic fallback route so the run remains usable instead of blocking.

Inside `hive tui`, press `n` to enter a fresh prompt directly. The TUI creates a new run and routes it through the same local intent router. Press `a` to re-route the current run.

`hive invoke local --role ...` writes an artifact even when Ollama is unavailable. This keeps the run trace complete and makes infrastructure failures visible in the TUI instead of crashing the harness.

`hive local status` reports the local runtime without requiring hosted provider keys. `hive local setup` writes `.hivemind/local_runtime.json` with the detected wrapper, server state, and model manifests.

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
python -m hivemind.hive invoke claude --role planner
python -m hivemind.hive invoke codex --role executor
python -m hivemind.hive invoke gemini --role reviewer
```

These commands create:

```text
agents/<provider>/<role>_prompt.md
agents/<provider>/<role>_command.txt
```

For supported non-interactive execution:

```bash
python -m hivemind.hive invoke claude --role planner --execute
python -m hivemind.hive invoke gemini --role reviewer --execute
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

Use `python -m hivemind.hive settings detect` to refresh the profile after installing or changing provider CLIs. Use `eval "$(python -m hivemind.hive settings shell)"` before custom shell scripts that need the resolved binaries.

## Current Boundary

This is intentionally not the Desktop cockpit. It is the first stable loop:

```text
manual shared folder
  -> structured blackboard
  -> wrapper CLI
  -> TUI status
  -> later Desktop cockpit
```
