"""Unified explore view: Agents / Runs / Inspect / Events in one screen."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .harness import detect_agents, list_runs, load_run, read_events
from .inspect_run import build_inspect_report, format_inspect_report


EXPLORE_PANES = ("agents", "runs", "inspect", "events")
_DATA_REFRESH_INTERVAL = 3.0


@dataclass
class ExploreState:
    active_pane: str = "runs"
    selected_run_index: int = 0
    selected_run_id: str | None = None
    selected_agent_index: int = 0
    selected_agent_id: str | None = None
    scroll_offsets: dict[str, int] = field(default_factory=lambda: {p: 0 for p in EXPLORE_PANES})
    runs_cache: list[dict[str, Any]] = field(default_factory=list)
    agents_cache: dict[str, Any] = field(default_factory=dict)
    inspect_cache: dict[str, Any] = field(default_factory=dict)
    events_cache: list[dict[str, Any]] = field(default_factory=list)
    inspect_lines: list[str] = field(default_factory=list)
    last_refresh: float = 0.0
    last_ask_result: str | None = None

    def cycle_pane(self, direction: int = 1) -> None:
        idx = EXPLORE_PANES.index(self.active_pane) if self.active_pane in EXPLORE_PANES else 0
        self.active_pane = EXPLORE_PANES[(idx + direction) % len(EXPLORE_PANES)]

    def select_run(self) -> None:
        if 0 <= self.selected_run_index < len(self.runs_cache):
            self.selected_run_id = self.runs_cache[self.selected_run_index].get("run_id")

    def select_agent(self) -> None:
        providers = self.agents_cache.get("providers") or {}
        names = sorted(providers.keys())
        if 0 <= self.selected_agent_index < len(names):
            self.selected_agent_id = names[self.selected_agent_index]


def refresh_explore_data(root: Path, state: ExploreState, force: bool = False) -> None:
    now = time.monotonic()
    if not force and now - state.last_refresh < _DATA_REFRESH_INTERVAL:
        return
    state.last_refresh = now
    try:
        state.runs_cache = list_runs(root)[:40]
    except Exception:
        state.runs_cache = []
    try:
        state.agents_cache = detect_agents(root, write=False)
    except Exception:
        state.agents_cache = {}
    run_id = state.selected_run_id
    if not run_id and state.runs_cache:
        run_id = state.runs_cache[0].get("run_id")
        state.selected_run_id = run_id
    if run_id:
        try:
            report = build_inspect_report(root, run_id)
            state.inspect_cache = report
            state.inspect_lines = format_inspect_report(report).splitlines()
        except Exception as exc:
            state.inspect_cache = {}
            state.inspect_lines = [f"Error loading inspect: {exc}"]
        try:
            paths, _ = load_run(root, run_id)
            state.events_cache = read_events(paths, limit=60)
        except Exception:
            state.events_cache = []
    else:
        state.inspect_cache = {}
        state.inspect_lines = ["No run selected."]
        state.events_cache = []


def update_explore_navigation(state: ExploreState, key: int | str) -> str | None:
    """Process a key in explore mode. Returns action string or None."""
    import curses

    if key == ord("\t") or key == curses.KEY_BTAB:
        direction = -1 if key == curses.KEY_BTAB else 1
        state.cycle_pane(direction)
        return "pane_changed"

    if key in {curses.KEY_UP, ord("k")}:
        return _scroll_up(state)
    if key in {curses.KEY_DOWN, ord("j")}:
        return _scroll_down(state)
    if key in {10, 13, curses.KEY_ENTER}:
        return _select_item(state)
    return None


def _scroll_up(state: ExploreState) -> str:
    pane = state.active_pane
    if pane == "runs":
        state.selected_run_index = max(0, state.selected_run_index - 1)
    elif pane == "agents":
        state.selected_agent_index = max(0, state.selected_agent_index - 1)
    else:
        state.scroll_offsets[pane] = max(0, state.scroll_offsets.get(pane, 0) - 1)
    return "scrolled"


def _scroll_down(state: ExploreState) -> str:
    pane = state.active_pane
    if pane == "runs":
        state.selected_run_index = min(len(state.runs_cache) - 1, state.selected_run_index + 1)
    elif pane == "agents":
        providers = state.agents_cache.get("providers") or {}
        state.selected_agent_index = min(len(providers) - 1, state.selected_agent_index + 1)
    else:
        state.scroll_offsets[pane] = state.scroll_offsets.get(pane, 0) + 1
    return "scrolled"


def _select_item(state: ExploreState) -> str:
    pane = state.active_pane
    if pane == "runs":
        state.select_run()
        return "run_selected"
    if pane == "agents":
        state.select_agent()
        return "agent_selected"
    return "noop"


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------

def draw_explore_view(
    screen,
    height: int,
    width: int,
    root: Path,
    explore: ExploreState,
    add_line_fn,
    draw_box_fn,
    truncate_fn,
    color_fn,
    clear_line_fn,
) -> None:
    """Render the unified explore view with 4 visible panes + composer."""
    import curses

    if height < 12 or width < 60:
        add_line_fn(screen, 1, 2, "Terminal too small for explore view (need 60x12+)", curses.A_BOLD)
        return

    margin = 1
    content_w = width - margin * 2
    composer_rows = 3
    usable_h = height - composer_rows

    header_h = 2
    _draw_explore_header(screen, margin, content_w, explore, add_line_fn, truncate_fn, color_fn)

    top_h = max(6, (usable_h - header_h) * 2 // 3)
    bottom_h = max(4, usable_h - header_h - top_h)
    top_y = header_h
    bottom_y = top_y + top_h

    agents_w = max(20, content_w // 4)
    runs_w = max(22, content_w // 4)
    inspect_w = content_w - agents_w - runs_w - 2

    agents_x = margin
    runs_x = agents_x + agents_w + 1
    inspect_x = runs_x + runs_w + 1

    is_active = lambda p: p == explore.active_pane

    draw_box_fn(screen, top_y, agents_x, top_h, agents_w, "Agents" + (" *" if is_active("agents") else ""))
    _draw_agents_pane(screen, top_y + 1, agents_x + 2, top_h - 2, agents_w - 4, explore, add_line_fn, truncate_fn, color_fn)

    draw_box_fn(screen, top_y, runs_x, top_h, runs_w, "Runs" + (" *" if is_active("runs") else ""))
    _draw_runs_pane(screen, top_y + 1, runs_x + 2, top_h - 2, runs_w - 4, explore, add_line_fn, truncate_fn, color_fn)

    draw_box_fn(screen, top_y, inspect_x, top_h, inspect_w, "Inspect" + (" *" if is_active("inspect") else ""))
    _draw_inspect_pane(screen, top_y + 1, inspect_x + 2, top_h - 2, inspect_w - 4, explore, add_line_fn, truncate_fn, color_fn)

    draw_box_fn(screen, bottom_y, margin, bottom_h, content_w, "Events" + (" *" if is_active("events") else ""))
    _draw_events_pane(screen, bottom_y + 1, margin + 2, bottom_h - 2, content_w - 4, explore, add_line_fn, truncate_fn, color_fn)


def _draw_explore_header(screen, x: int, width: int, explore: ExploreState, add_line_fn, truncate_fn, color_fn) -> None:
    import curses
    clock = time.strftime("%H:%M")
    run_label = explore.selected_run_id or "-"
    agent_label = explore.selected_agent_id or "-"
    title = f"Hive Explore  Run:{run_label}  Agent:{agent_label}  {clock}"
    add_line_fn(screen, 0, x, truncate_fn(title, width), color_fn(1, curses.A_BOLD))
    nav_help = "Tab:pane  Up/Down:select  Enter:pick  Ask:type in composer"
    add_line_fn(screen, 1, x, truncate_fn(nav_help, width), curses.A_DIM)


def _draw_agents_pane(screen, y: int, x: int, height: int, width: int, explore: ExploreState, add_line_fn, truncate_fn, color_fn) -> None:
    import curses
    providers = explore.agents_cache.get("providers") or {}
    if not providers:
        add_line_fn(screen, y, x, "No providers detected.", curses.A_DIM)
        return
    names = sorted(providers.keys())
    for i, name in enumerate(names[:height]):
        info = providers[name]
        status = info.get("status", "unknown")
        icon = "+" if status in {"available", "configured"} else "-"
        selected = i == explore.selected_agent_index
        prefix = "> " if selected and explore.active_pane == "agents" else "  "
        line = f"{prefix}{icon} {name} [{status}]"
        attr = color_fn(1) if status in {"available", "configured"} else curses.A_DIM
        if selected and explore.active_pane == "agents":
            attr = color_fn(2, curses.A_BOLD)
        add_line_fn(screen, y + i, x, truncate_fn(line, width), attr)


def _draw_runs_pane(screen, y: int, x: int, height: int, width: int, explore: ExploreState, add_line_fn, truncate_fn, color_fn) -> None:
    import curses
    runs = explore.runs_cache
    if not runs:
        add_line_fn(screen, y, x, "No runs found.", curses.A_DIM)
        return
    visible = runs[:height]
    for i, run in enumerate(visible):
        run_id = run.get("run_id", "?")
        status = run.get("status", "?")
        task = run.get("user_request", "")
        selected = i == explore.selected_run_index
        is_current = run_id == explore.selected_run_id
        prefix = "> " if selected and explore.active_pane == "runs" else "  "
        marker = "*" if is_current else " "
        line = f"{prefix}{marker}{run_id[:12]} [{status}]"
        if width > 30:
            remaining = width - len(line) - 1
            if remaining > 4:
                line += " " + task[:remaining]
        attr = curses.A_DIM
        if is_current:
            attr = color_fn(1, curses.A_BOLD)
        elif selected and explore.active_pane == "runs":
            attr = color_fn(2, curses.A_BOLD)
        add_line_fn(screen, y + i, x, truncate_fn(line, width), attr)


def _draw_inspect_pane(screen, y: int, x: int, height: int, width: int, explore: ExploreState, add_line_fn, truncate_fn, color_fn) -> None:
    import curses
    lines = explore.inspect_lines
    if explore.last_ask_result:
        lines = [f"Ask Result: {explore.last_ask_result}", ""] + lines
    offset = explore.scroll_offsets.get("inspect", 0)
    offset = min(offset, max(0, len(lines) - height))
    explore.scroll_offsets["inspect"] = offset
    visible = lines[offset : offset + height]
    if not visible:
        add_line_fn(screen, y, x, "No inspection data.", curses.A_DIM)
        return
    for i, line in enumerate(visible):
        attr = curses.A_BOLD if i == 0 and offset == 0 else 0
        add_line_fn(screen, y + i, x, truncate_fn(line, width), attr)


def _draw_events_pane(screen, y: int, x: int, height: int, width: int, explore: ExploreState, add_line_fn, truncate_fn, color_fn) -> None:
    import curses
    events = explore.events_cache
    if not events:
        add_line_fn(screen, y, x, "No events.", curses.A_DIM)
        return
    offset = explore.scroll_offsets.get("events", 0)
    tail = events[-max(1, height + offset) :]
    visible = tail[:height]
    for i, event in enumerate(visible):
        ts = _short_time(str(event.get("ts", "")))
        if "summary" in event:
            line = f"{ts}  {event.get('actor', 'hive')}  {event.get('action', '')}  {event.get('summary', '')}"
        else:
            etype = str(event.get("type", ""))
            artifact = event.get("artifact")
            line = f"{ts}  {etype}" + (f"  {artifact}" if artifact else "")
        add_line_fn(screen, y + i, x, truncate_fn(line, width), 0)


def _short_time(ts: str) -> str:
    if "T" in ts:
        return ts.split("T", 1)[1].split("+", 1)[0]
    return ts
