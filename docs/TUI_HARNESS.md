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
hive agents roles
hive agents policy
hive agents explain codex.executor
hive policy check --write
hive policy explain codex.executor
hive audit
hive workspace --layout dev
hive workspace --layout dual
hive doctor all
hive doctor hardware
hive doctor providers
hive doctor models
hive doctor permissions
hive chat
hive orchestrate "Build parser and review risks"
hive next
hive board
hive events --tail 60
hive events --follow
hive transcript --tail 120
hive artifacts
hive agents view
hive memory view
hive society
hive prompt
hive log
hive hive activity
hive memory list
hive tui
hive tui --view board
hive tui --view events --observer
hive tui --view transcript --observer
hive completion zsh
npm run production
```

Without installing:

```bash
python -m hivemind.hive init
python -m hivemind.hive doctor
python -m hivemind.hive doctor hardware
python -m hivemind.hive local status
python -m hivemind.hive local setup
python -m hivemind.hive local setup --auto
python -m hivemind.hive local benchmark --limit 1 --role json_normalizer
python -m hivemind.hive local checker
scripts/hive-local-benchmark.sh qwen3:1.7b
HIVE_LOCAL_BACKEND=ollama HIVE_OLLAMA_MODE=docker scripts/hive-local-benchmark.sh qwen3:1.7b
python -m hivemind.hive agents detect
python -m hivemind.hive agents roles
python -m hivemind.hive settings detect
eval "$(python -m hivemind.hive settings shell)"
python -m hivemind.hive run "Build Draft Review screen"
python -m hivemind.hive ask "Build Draft Review screen"
python -m hivemind.hive plan
python -m hivemind.hive status
python -m hivemind.hive next
python -m hivemind.hive tui
python -m hivemind.hive tui --view agents --observer
python -m hivemind.hive events --tail 60
python -m hivemind.hive transcript --tail 120
python -m hivemind.hive context
python -m hivemind.hive context build --for claude.planner
python -m hivemind.hive context build --for codex.executor
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

`hive "your task"` is shorthand for `hive orchestrate "your task"`.
Bare `hive` opens the conversational operator shell. Use `hive chat` explicitly for the same shell, or `hive shell` for the older thin slash-command shell. Use `hive tui` for the curses status board.

`hive tui` is a multi-view cockpit, not one mega-dashboard. The default `board`
view focuses on current run, next action, pipeline, agent reasons, missing
artifact classes, decisions/open questions, and recent events. Longer material
is split into observer views:

```text
1 board
2 events
3 transcript
4 agents
5 artifacts
6 memory
7 society
8 diff
```

Use multiple terminals or tmux panes for the intended workflow:

```bash
hive board
hive events --follow
hive transcript --tui
hive agents view
hive diff --tui
```

Observer mode blocks action keys and is meant for read-only monitoring.
Controller mode can still run prompt, route, provider, verify, memory, and diff
actions.

Only one controller can own a run at a time. Controller sessions create:

```text
.runs/<run_id>/control.lock
```

The lock contains a session id, pid, role, start time, heartbeat, and TTL.
`hive tui` refreshes the heartbeat while open and removes the lock on clean
exit. Observer views do not acquire this lock. If a controller crashes, a stale
lock can be replaced after its TTL.

Artifact views distinguish file existence from pipeline completion:

```text
exists      whether the path is present
freshness   fresh, stale, empty, initial, or missing
class       required, phase, post_execution, or optional
producer    expected producer such as local/intent-router, claude/planner, verifier
```

For example, `context_pack.md` can exist while `local-context-compressor` is
still pending; the artifacts view marks that as stale instead of treating the
context phase as complete.

`hive doctor` keeps the original provider/core health check. Scoped doctor
commands expose production-readiness slices from `docs/hive_mind2.md`:

```bash
hive doctor hardware     # CPU, RAM, GPU/VRAM, disk, Python, Node, Docker, local adapter ports
hive doctor providers    # provider capability registry and CLI/API availability
hive doctor models       # local backend inventory and worker role assignments
hive doctor permissions  # project policy/check state and provider risk inventory
hive doctor all          # combined production readiness report
```

The production policy and role registry turn the current working style into
runtime structure:

```bash
hive policy check --write
hive policy explain codex.executor
hive agents roles
hive agents explain claude.planner
hive context build --for codex.executor
hive local setup --auto
hive local benchmark
hive local benchmark --model qwen3:1.7b --role classify --role json_normalizer
hive local checker
hive local checker --execute
npm run backend:ollama:docker
npm run benchmark:local
hive audit
hive workspace --layout dev
```

`hive policy check --write` creates `.hivemind/policy.yaml` and the project-local
`.hivemind/skills/hive-working-method/SKILL.md`. The skill encodes the
user/Claude/Codex/local-LLM loop as a reusable protocol. The quiet internal
thread is `evolution of Single Human Intelligence`; treat it as product
identity, not a scientific claim.

Local benchmark setup uses the Hive Mind local backend protocol. Ollama is an
optional adapter, not a required dependency. The current adapter can be selected
with `HIVE_LOCAL_BACKEND`; `auto` chooses the first available backend with model
inventory.

```bash
hive local benchmark --backend auto --model phi4-mini --role json_normalizer
HIVE_LOCAL_BACKEND=ollama scripts/hive-local-benchmark.sh qwen3:1.7b
HIVE_LOCAL_BACKEND=ollama HIVE_OLLAMA_MODE=docker scripts/hive-local-benchmark.sh qwen3:1.7b
```

The optional Docker path runs `ollama/ollama:latest` as `hivemind-ollama`, binds
`127.0.0.1:11434`, mounts `.local/ollama/models`, and adds `--gpus all` when
`nvidia-smi` is available.

Benchmarks can be role-specific. Use repeated `--role` values to test the same
model against classifier, JSON normalization, memory extraction, capability
extraction, log summary, diff review, handoff, and architecture prompts:

```bash
hive local benchmark \
  --model qwen3:1.7b \
  --model phi4-mini \
  --role classify \
  --role json_normalizer \
  --role memory_extraction
```

`hive orchestrate` is the default prompt path. It asks the local router to split the request into a small agent society, prepares each provider/local worker artifact, writes `society_plan.json`, and reports which member owns which role. `hive ask` remains available for route-only debugging.

Hive Mind keeps `events.jsonl` as a machine/audit log and `hive_events.jsonl` as the human activity feed. The TUI latest-events panel prefers `hive_events.jsonl`, so it shows role assignment and swarm decisions instead of only file-created events.

`hive status` prints the run board: pipeline, agent status, artifact status, and the next recommended command. `hive next` prints only the next action for fast terminal loops.

`hive check run` evaluates markdown policy files under `.hivemind/checks/`. `hive diff`, `hive review-diff`, and `hive commit-summary` provide the first git-aware loop without committing automatically.
`hive prompt` reads a multiline/stdin prompt and routes it through the local intent router. `hive log` shows the current run `transcript.md`.

Provider and local worker activity is mirrored into per-agent log files under
`agents/<provider>/<role>.log`, the human activity feed, and `transcript.md`.
When a provider supports execution, stdout lines are streamed into those logs
while the process is running. Transcript is now primarily a full observer view
instead of a cramped board panel.

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

It also initializes `.runs/`, runs provider detection, writes `.runs/provider_capabilities.json`, scans local backend model manifests, writes `.hivemind/local_runtime.json`, and prints next actions.

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
1-8  switch views
type text  edit the always-visible hive> composer
enter  submit the composer
backspace  edit the composer
esc  clear the composer
/command  run a slash command from the composer
?  show keybinding hint
```

Large terminals render the dashboard as a control plane: run/health summary, pipeline, agents, artifacts, latest events, next actions, keybar, and an always-visible `hive>` composer. The TUI is interactive: type a normal prompt directly at `hive>` and press Enter to create and route a new run, or type slash commands such as `/verify`, `/memory`, `/summary`, `/diff`, `/local`, `/claude`, `/codex`, and `/gemini`.

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

`hive ask` creates or reuses a run, asks the local `intent_router` worker to decompose the prompt, writes `routing_plan.json`, and prepares the matching Claude/Codex/Gemini/local artifacts. If the selected local backend is unreachable, it writes a heuristic fallback route so the run remains usable instead of blocking.

Inside `hive tui`, press `n` to enter a fresh prompt directly. The TUI creates a new run and routes it through the same local intent router. Press `a` to re-route the current run.

`hive invoke local --role ...` writes an artifact even when the selected local backend is unavailable. This keeps the run trace complete and makes infrastructure failures visible in the TUI instead of crashing the harness.

`hive local status` reports local backend state without requiring hosted provider keys. `hive local setup` writes `.hivemind/local_runtime.json` with detected adapters, server state, and model manifests.

DeepSeek and Qwen have two separate paths:

- Local open-weight models through a local backend: no API key required.
- Hosted HTTP providers: require `DEEPSEEK_API_KEY` or `QWEN_API_KEY`.

The current local manifests are detected at runtime with `hive local status`; do
not treat this document as the source of truth for pulled models.

Supported local roles:

- `context`
- `handoff`
- `summarize`
- `memory`
- `review`
- `classify`
- `json`
- `json-normalizer`
- `normalize`

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
