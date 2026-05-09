# Hive Mind CLI/TUI

`hive` is the Hive Mind control plane for the structured agent blackboard described in `docs/tui.md`. It combines already-installed provider CLIs and local LLM workers instead of replacing their native interfaces.

## Commands

```bash
python -m hivemind.hive init
scripts/install-hive-cli.sh
hive
hive "Build Draft Review screen"
hive run -q --json "Build Draft Review screen"
hive run start --max-rounds 8
hive run status
hive run tail
hive run stop
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
hive demo live "Watch Hive Mind agents coordinate in the TUI"
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
python -m hivemind.hive demo live "Watch Hive Mind agents coordinate in the TUI"
```

If installed as a package, `hive` and `hivemind` point to the same command.

`hive "your task"` is shorthand for `hive orchestrate "your task"`.
Bare `hive` opens the Hive Console/TUI when stdin and stdout are interactive.
Use `hive tui` when you want the same console explicitly, `hive chat` for the
plain conversational operator shell, and `hive shell` for the older thin
slash-command shell. In non-interactive pipes, bare `hive` prints help instead
of starting curses.

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

Hive keeps two provider layers. The role adapter path (`hive invoke claude
--role planner`) lets Hive strongly control prompt/result/proof shape for common
swarm roles. The native passthrough path (`hive provider claude --dry-run --
<native args...>`) keeps provider CLI features intact while Hive records command,
policy, stdout, stderr, result, proof, and ledger artifacts.

```bash
hive provider claude --dry-run -- -p "summarize this" --permission-mode plan
hive provider codex --dry-run -- exec --cd . --sandbox read-only "inspect"
hive provider gemini --dry-run -- -p "review" --approval-mode plan
hive provider codex --execute -- exec --cd . --sandbox read-only "inspect"
```

`hive provider` does not interpret native args beyond a small danger gate. It
blocks known bypass/destructive patterns such as Claude
`--dangerously-skip-permissions`, Gemini trust/yolo bypass flags, and Codex
unsafe sandbox plus approval-never combinations. Everything else is preserved as
native CLI surface and wrapped in Hive artifacts.

`hive run start` is the first supervised DAG runner. It is still a ledger client,
not a hidden autonomy daemon: each round calls the DAG scheduler, writes
`supervisor_state.json`, appends `supervisor_started` / `supervisor_stopped`
ledger events, and logs to `supervisor.log`.

```bash
hive run start --max-rounds 8
hive run start --scheduler pingpong --max-rounds 8
hive run start --run-id run_... --detach
hive run status --run-id run_...
hive run tail --run-id run_...
hive run stop --run-id run_...
```

Default mode is prepare-only. `--execute` may run only protocol-approved
provider steps; the existing `ExecutionDecision` gate still applies. Supervisor
status includes PID, host, command hash, git commit, log path, replay health,
active step leases, and scheduler/kernel mode.

`--scheduler pingpong` is the L0 serialized kernel lifted from the MemoryOS
pingpong loop. It runs exactly one runnable DAG step per round, then yields. That
keeps the simple shared-state/current-turn/worklog rhythm while making the turn
auditable through `execution_ledger.jsonl`, leases, probes, proof, and replay.
The default `fanout` scheduler remains available for later L3 coordination where
parallel branches and barrier joins are useful.

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
F1-F9  switch views
type text  edit the always-visible hive> composer, including UTF-8/Hangul text
enter  submit the composer
left/right  move within the composer
home/end or ctrl-a/ctrl-e  jump to start/end
backspace/delete  edit the composer
ctrl-u/ctrl-k  clear before/after cursor
ctrl-w  delete previous word
ctrl-c or esc  cancel the composer
ctrl-v  paste from the system clipboard when wl-paste, xclip, xsel, or pbpaste is available
ctrl-d  quit when the composer is empty
/command  run a slash command from the composer
/view board|events|transcript|agents|artifacts|memory|society|diff|ledger  switch views
/demo [delay]  animate a safe multi-agent run without executing providers
/quit  quit
F10  show keybinding hint
```

Large terminals render the dashboard as a control plane: run/health summary, pipeline, agents, artifacts, latest events, next actions, keybar, and an always-visible `hive>` composer. The TUI is interactive: type a normal prompt directly at `hive>` and press Enter to create and route a new run, or type slash commands such as `/verify`, `/memory`, `/summary`, `/diff`, `/ledger`, `/local`, `/claude`, `/codex`, and `/gemini`. Printable keys are treated as prompt text first, so prompts can naturally start with `q`, digits, punctuation, or Hangul.

Prompt submission runs in the background so slow local/provider routing does not freeze the console. The status line reports active submissions and then replaces it with the completed run or error message.

Normal TUI prompts use the fast heuristic router first. This keeps the operator console responsive; explicit CLI or slash-command workflows can still run local/provider workers when deeper routing is needed.

To watch the TUI update while multiple roles move through the board, open two
terminals:

```bash
hive tui
```

```bash
hive demo live "TUI live swarm demo" --delay 0.4
```

The same safe animation can be launched from inside the TUI with `/demo 0.4`.
The demo writes real run artifacts and human activity events for local context,
Claude planner, Codex executor, Gemini reviewer, local summarizer, verifier,
memory, and close. It intentionally keeps provider CLIs in prepare-only mode, so
it is a UI/read-model smoke test rather than an autonomous execution path.

Normal prompt intake now connects to the lifecycle core. `hive "task"` and
`hive orchestrate "task"` still create routing and society artifacts, but they
also create `plan_dag.json` and `artifacts/workflow_state.json`. The intent
router chooses provider/local roles; the DAG owns lifecycle state, ledger
records, probes, evaluations, and supervisor progression. This is the same core
state that a future desktop/chatbot UI should read.

Safe local workers can also act as bounded task processors for simple work.
Use `--execute-local` to let local workers such as summarize, classify, memory,
review, handoff, and context run through DAG/ledger execution. Frontier provider
execution remains explicit and policy-gated.

`hive ledger --follow` opens the same TUI directly on the ledger view. The ledger
is an append-only `execution_ledger.jsonl` per run: scheduler round, step start,
step completion, reversibility gate, permission mode, bypass mode, output
artifact, and touched-file hints. This is the TUI equivalent of the user's shared
folder/log method: agents still coordinate through files, but the chair has a
live read-model instead of asking the operator to stare at multiple terminals.

`hive ledger replay` validates the ledger instead of only tailing it. It checks
the hash chain, sequence continuity, referenced JSON artifacts, and protocol
intent/vote/decision/proof records, then reconstructs step and authority state.
Use it when a run looks stale, blocked, or suspicious:

```bash
hive ledger replay
hive ledger replay --json
```

The TUI ledger view renders the same replayed authority state at the top of the
panel: replay health, active intent, latest decision, missing voters, votes,
proof status, and replay issues. This makes policy/protocol stalls visible
without asking the operator to inspect `execution_intents/`,
`execution_votes/`, `execution_decisions/`, or `execution_proofs/` by hand.
Typed ProbeStep gates are surfaced there too: the latest probe step shows its
action, confidence, criteria count, and status, and recent ledger rows include a
compact `probe=... conf=... criteria=...` suffix. `hive run status` reports the
same last-probe summary so a supervised run can explain whether it is waiting on
human override, blocked by a falsification criterion, or safe to continue.

`hive live` is the prompt/log surface over the same substrate:

```bash
hive live "ship the next safe slice"
hive live --follow
hive live --memoryos
```

It hides run-folder and artifact paths by default and shows task state, next
action, authority/protocol state, blocked gates, agent status, and live log
events. Use `--paths` only for debugging/export.

`hive live --memoryos` emits the first MemoryOS-facing neural-map read model as
JSON. The shape is intentionally graph-oriented: `graph.nodes`,
`graph.edges`, and `events` cover the Hive run, agent turns, workflow steps,
authority gates, votes, memory drafts, disagreements, and live log records.
MemoryOS can poll or import this contract and decide how to render the neural
map without Hive growing a second visual UI.

For durable MemoryOS ingest, each event also carries the `HiveLiveEventV1`
fields: `event_id`, `event_type`, `run_id`, `timestamp`, `agent_id`, and
`payload`. Ledger-backed rows derive `event_id` from the execution ledger
`seq/hash` pair so tail size changes do not change dedupe identity. Older
`hive_events.jsonl` activity uses a content fingerprint fallback. The legacy
read-model aliases (`id`, `type`, `ts`, `actor`, `summary`, `refs`) remain for
UI consumers, but durable import should prefer the `HiveLiveEventV1` fields.

This is still a read model, not the final accepted-memory protocol. MemoryOS can
render or validate it now, but accepted context injection is a separate pre-run
bridge: Hive should eventually call `memoryos context build --for hive --json`
instead of only writing a planned command placeholder.

The TUI is not the final UX. It is a transitional operator/debug surface while
the run substrate hardens. The desired AIOS UX is prompt input plus live
log/decision output: no directory browsing, no manual run-folder inspection, and
no app shell required for normal work. Files, folders, JSONL, and protocol
artifacts remain internal infrastructure and export/debug surfaces.

## MemoryOS UI Boundary

Hive Mind keeps `hive tui` as a local operator cockpit, but the MemoryOS
integration should not make Hive's TUI the main user interface. In the combined
system, Hive receives prompts, coordinates provider/local agents, writes
ledger/protocol/run artifacts, and emits a stable live read model. MemoryOS owns
the neural-map observability UI that renders agent activity, authority gates,
claims, decisions, disagreements, evidence, and accepted memory over time.

This boundary keeps Hive focused on orchestration correctness and replayable
state. It also prevents the terminal dashboard from becoming a second product UI
that competes with MemoryOS.

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
    execution_ledger.jsonl
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
python -m hivemind.hive provider claude --dry-run -- -p "..." --permission-mode plan
python -m hivemind.hive provider codex --execute -- exec --cd . --sandbox read-only --ask-for-approval never "review this run"
```

These commands create:

```text
agents/<provider>/<role>_prompt.md
agents/<provider>/<role>_command.txt
agents/<provider>/native/passthrough_XX_command.txt
agents/<provider>/native/passthrough_XX_result.yaml
agents/<provider>/native/passthrough_XX_stdout.txt
agents/<provider>/native/passthrough_XX_stderr.txt
```

`hive invoke` is the role adapter path: Hive builds the prompt contract and role
output shape. `hive provider` is the native passthrough path: Hive does not
reinterpret provider flags, but records the command, creates an
`ExecutionIntent`, runs policy/vote/decision/proof records, captures
stdout/stderr/output, and blocks known dangerous bypass combinations by default.
Claude should periodically review the hard-block list and approval boundary as
provider CLIs evolve.

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
