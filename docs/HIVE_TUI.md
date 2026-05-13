# Hive TUI

`hive tui` provides an interactive terminal interface for monitoring and controlling Hive Mind runs.

## Views

| Key | View | Description |
|-----|------|-------------|
| F1 | board | Dashboard with pipeline, agents, health, events |
| F2 | events | Full event stream |
| F3 | transcript | Human-readable run log |
| F4 | agents | Provider/worker detail |
| F5 | artifacts | Artifact status and freshness |
| F6 | memory | Draft memory records |
| F7 | society | Multi-agent plan and disagreements |
| F8 | diff | Git diff for current run |
| F9 | ledger | Execution ledger and authority state |
| F10 | explore | Unified 5-pane exploration view |

## Explore View (ASC-0097)

The explore view (`F10` or `hive tui --explore`) combines five separate
CLI commands into one screen:

```
+----------+--------------+------------------------+
| Agents   | Runs         | Inspect                |
|          |              |                        |
|          |              |                        |
+----------+--------------+------------------------+
| Events                                           |
+--------------------------------------------------+
| hive> [ask input]                                |
+--------------------------------------------------+
```

### Navigation

- **Tab** / **Shift+Tab**: cycle active pane (agents -> runs -> inspect -> events)
- **Up / Down** or **k / j**: scroll within pane; select item in Agents/Runs
- **Enter**: select highlighted run or agent
- **Composer**: type a prompt and press Enter to submit via `hive ask`

### Shared State

- **selected_run_id**: set by selecting a run in the Runs pane; Inspect and Events update automatically
- **selected_agent_id**: set by selecting an agent in the Agents pane

### Launch

```bash
hive tui --explore              # start in explore view
hive tui                        # start in board view, press F10 for explore
hive tui --explore --observer   # read-only explore
```

### Composer Commands

Type in the bottom composer line:

- `/explore` — switch to explore view
- `/board`, `/events`, etc. — switch to other views
- `/view 0` — switch to explore via number
- `/quit` — exit
- Any other text — submitted as `hive ask` prompt; result appears in Inspect pane

## Modes

- **Controller** (default): can submit prompts and trigger actions
- **Observer** (`--observer`): read-only, no actions allowed
