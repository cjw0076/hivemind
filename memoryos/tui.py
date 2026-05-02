"""Minimal stdlib TUI for MemoryOS harness run status."""

from __future__ import annotations

import curses
import json
import os
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any

import yaml

from .harness import (
    build_memory_draft,
    build_summary,
    build_verification,
    append_event,
    ask_router,
    invoke_external_agent,
    invoke_local,
    load_run,
    read_events,
)


def run_tui(root: Path, run_id: str | None = None) -> None:
    curses.wrapper(lambda screen: draw_loop(screen, root, run_id))


def draw_loop(screen, root: Path, run_id: str | None) -> None:
    curses.curs_set(0)
    screen.nodelay(True)
    message = "ready"
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        try:
            paths, state = load_run(root, run_id)
            events = read_events(paths, limit=8)
            health = collect_run_health(root, paths, state, events)
            draw_state(screen, height, width, state, events, health)
        except Exception as exc:  # TUI should show recoverable state instead of crashing.
            add_line(screen, 1, 2, "MemoryOS Harness", curses.A_BOLD)
            add_wrapped(screen, 3, 2, width - 4, str(exc))
        footer = "q quit  n new-prompt  e edit-context  a auto-route  l local  c claude  x codex  g gemini  v verify"
        add_line(screen, height - 2, 2, truncate(footer, max(10, width - 4)), curses.A_DIM)
        add_line(screen, height - 1, 2, truncate(message, max(10, width - 4)), curses.A_DIM)
        screen.refresh()
        key = screen.getch()
        if key in {ord("q"), ord("Q"), 27}:
            return
        if key != -1:
            message = handle_key(screen, root, run_id, key)
        time.sleep(0.5)


def handle_key(screen, root: Path, run_id: str | None, key: int) -> str:
    try:
        if key in {ord("r"), ord("R")}:
            return "refreshed"
        if key in {ord("e"), ord("E")}:
            return edit_context_pack(screen, root, run_id)
        if key in {ord("n"), ord("N")}:
            return prompt_and_route(screen, root)
        if key in {ord("a"), ord("A")}:
            paths, state = load_run(root, run_id)
            prompt = str(state.get("user_request") or paths.context_pack.read_text(encoding="utf-8")[:2000])
            path = ask_router(root, prompt, run_id=paths.run_id, complexity="default")
            return f"auto-route -> {path}"
        if key in {ord("l"), ord("L")}:
            path = invoke_local(root, "context", run_id=run_id, complexity="default")
            return f"local context -> {path}"
        if key in {ord("c"), ord("C")}:
            path = invoke_external_agent(root, "claude", "planner", run_id=run_id, execute=False)
            return f"claude planner prompt -> {path}"
        if key in {ord("x"), ord("X")}:
            path = invoke_external_agent(root, "codex", "executor", run_id=run_id, execute=False)
            return f"codex executor prompt -> {path}"
        if key in {ord("g"), ord("G")}:
            path = invoke_external_agent(root, "gemini", "reviewer", run_id=run_id, execute=False)
            return f"gemini reviewer prompt -> {path}"
        if key in {ord("v"), ord("V")}:
            path = build_verification(root, run_id=run_id)
            return f"verification -> {path}"
        if key in {ord("s"), ord("S")}:
            path = build_summary(root, run_id=run_id)
            return f"summary -> {path}"
        if key in {ord("m"), ord("M")}:
            path = build_memory_draft(root, run_id=run_id)
            return f"memory draft -> {path}"
    except Exception as exc:
        return f"error: {exc}"
    return "unknown key"


def prompt_and_route(screen, root: Path) -> str:
    height, width = screen.getmaxyx()
    curses.echo()
    curses.curs_set(1)
    screen.nodelay(False)
    prompt = ""
    try:
        row = max(0, height - 3)
        screen.move(row, 0)
        screen.clrtoeol()
        add_line(screen, row, 2, "New prompt: ", curses.A_BOLD)
        screen.refresh()
        raw = screen.getstr(row, 14, max(20, min(1000, width - 16)))
        prompt = raw.decode("utf-8", errors="replace").strip()
    finally:
        curses.noecho()
        curses.curs_set(0)
        screen.nodelay(True)
    if not prompt:
        return "empty prompt"
    path = ask_router(root, prompt, run_id=None, complexity="default")
    return f"new prompt routed -> {path}"


def edit_context_pack(screen, root: Path, run_id: str | None) -> str:
    paths, _ = load_run(root, run_id)
    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "nano"
    curses.def_prog_mode()
    curses.endwin()
    try:
        completed = subprocess.run([editor, paths.context_pack.as_posix()], cwd=root)
    finally:
        curses.reset_prog_mode()
        curses.curs_set(0)
        screen.nodelay(True)
        screen.clear()
    if completed.returncode == 0:
        append_event(paths, "context_edited", {"artifact": paths.context_pack.relative_to(root).as_posix()})
        return f"context edited -> {paths.context_pack}"
    return f"context editor exited {completed.returncode}: {paths.context_pack}"


def draw_state(
    screen,
    height: int,
    width: int,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    health: dict[str, Any],
) -> None:
    if height < 18 or width < 64:
        draw_compact(screen, height, width, state, events, health)
        return

    content_width = max(40, width - 4)
    footer_row = max(0, height - 2)
    top_status = f"MemoryOS Harness  {state.get('project')}  {state.get('phase')} / {state.get('status')}"
    add_line(screen, 0, 2, truncate(top_status, content_width), curses.A_BOLD)
    add_line(screen, 1, 2, "─" * min(content_width, 100), curses.A_DIM)

    add_line(screen, 2, 2, f"Run  {state.get('run_id')}", curses.A_BOLD)
    add_wrapped(screen, 3, 2, content_width, f"Task {state.get('user_request')}")
    health_line = (
        f"Latest {state.get('latest_event', '-')}  "
        f"Verify {health.get('verification_verdict')}  "
        f"Providers {health.get('providers_available')}/{health.get('providers_total')}  "
        f"Missing {len(health.get('missing_artifacts', []))}  "
        f"Failures {len(health.get('recent_failures', []))}"
    )
    add_line(screen, 5, 2, truncate(health_line, content_width), curses.A_DIM)

    panel_top = 7
    events_h = 7
    if width >= 96:
        left_x = 2
        gap = 2
        left_w = max(42, min(56, content_width // 2))
        right_x = left_x + left_w + gap
        right_w = max(32, content_width - left_w - gap)
        panel_h = max(8, footer_row - panel_top - events_h - 1)
        draw_box(screen, panel_top, left_x, panel_h, left_w, "Agent Pipeline")
        draw_agents(screen, panel_top + 1, left_x + 2, panel_h - 2, left_w - 4, state.get("agents", []))
        draw_box(screen, panel_top, right_x, panel_h, right_w, "Run Health / Artifacts")
        draw_artifacts(screen, panel_top + 1, right_x + 2, panel_h - 2, right_w - 4, state, health)
        events_top = panel_top + panel_h + 1
    elif height >= 28:
        panel_h = max(6, min(9, footer_row - panel_top - events_h - 5))
        draw_box(screen, panel_top, 2, panel_h, content_width, "Agent Pipeline")
        draw_agents(screen, panel_top + 1, 4, panel_h - 2, content_width - 4, state.get("agents", []))
        artifacts_top = panel_top + panel_h + 1
        artifacts_h = 5
        draw_box(screen, artifacts_top, 2, artifacts_h, content_width, "Run Health / Artifacts")
        draw_artifacts(screen, artifacts_top + 1, 4, artifacts_h - 2, content_width - 4, state, health)
        events_top = artifacts_top + artifacts_h + 1
    else:
        context = state.get("context") or {}
        context_line = (
            f"Context  memories {context.get('memories_used', 0)} / "
            f"decisions {context.get('active_decisions', 0)} / "
            f"questions {context.get('open_questions', 0)}"
        )
        add_line(screen, 6, max(2, min(width - len(context_line) - 2, 34)), truncate(context_line, max(20, width - 36)), curses.A_DIM)
        panel_h = max(5, min(7, footer_row - panel_top - 8))
        draw_box(screen, panel_top, 2, panel_h, content_width, "Agent Pipeline")
        draw_agents(screen, panel_top + 1, 4, panel_h - 2, content_width - 4, state.get("agents", []))
        events_top = panel_top + panel_h + 1

    draw_box(screen, events_top, 2, max(3, footer_row - events_top), content_width, "Recent Events")
    draw_events(screen, events_top + 1, 4, max(1, footer_row - events_top - 2), content_width - 4, events)


def status_icon(status: str | None) -> str:
    return {
        "completed": "✓",
        "running": "●",
        "in_progress": "●",
        "failed": "!",
        "pending": "○",
        "prepared": "◐",
    }.get(status or "", "○")


def draw_compact(
    screen,
    height: int,
    width: int,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    health: dict[str, Any],
) -> None:
    inner = max(20, width - 4)
    row = 1
    add_line(screen, row, 2, "MemoryOS Harness", curses.A_BOLD)
    row += 1
    add_line(screen, row, 2, f"{state.get('run_id')} [{state.get('status')}]", curses.A_DIM)
    row += 1
    add_line(
        screen,
        row,
        2,
        truncate(
            f"verify {health.get('verification_verdict')} | missing {len(health.get('missing_artifacts', []))} | failures {len(health.get('recent_failures', []))}",
            inner,
        ),
        curses.A_DIM,
    )
    row += 1
    row = add_wrapped(screen, row, 2, inner, str(state.get("user_request")))
    row += 1
    add_line(screen, row, 2, "Agents", curses.A_BOLD)
    for agent in state.get("agents", [])[: max(1, height // 4)]:
        row += 1
        add_line(screen, row, 4, truncate(f"{status_icon(agent.get('status'))} {agent.get('name')} [{agent.get('status')}]", inner - 2))
    row += 2
    add_line(screen, row, 2, "Events", curses.A_BOLD)
    draw_events(screen, row + 1, 4, max(1, height - row - 4), inner - 2, events)


def draw_agents(screen, y: int, x: int, height: int, width: int, agents: list[dict[str, Any]]) -> None:
    if not agents:
        add_line(screen, y, x, "No agents yet.", curses.A_DIM)
        return
    visible_count = height
    hidden = len(agents) - visible_count
    if hidden > 0:
        visible_count = max(0, height - 1)
    for index, agent in enumerate(agents[:visible_count]):
        icon = status_icon(agent.get("status"))
        text = f"{icon} {agent.get('name')}  {agent.get('status')}"
        attr = curses.A_BOLD if agent.get("status") in {"running", "in_progress"} else 0
        if agent.get("status") == "failed":
            attr = curses.A_REVERSE
        add_line(screen, y + index, x, truncate(text, width), attr)
    if hidden > 0:
        add_line(screen, y + height - 1, x, f"... {hidden} more", curses.A_DIM)


def draw_artifacts(screen, y: int, x: int, height: int, width: int, state: dict[str, Any], health: dict[str, Any]) -> None:
    context = state.get("context") or {}
    rows = [
        f"verify: {health.get('verification_verdict')}",
        f"providers: {health.get('providers_available')}/{health.get('providers_total')} available",
        f"route: {health.get('route_intent')} via {health.get('route_source')}",
        f"route actions: {health.get('route_actions')}",
        f"missing artifacts: {len(health.get('missing_artifacts', []))}",
        f"recent failures: {len(health.get('recent_failures', []))}",
        f"memories {context.get('memories_used', 0)}",
        f"decisions {context.get('active_decisions', 0)}",
        f"questions {context.get('open_questions', 0)}",
        "",
    ]
    artifacts = state.get("artifacts") or {}
    rows.extend(f"{name}: {path}" for name, path in artifacts.items())
    for index, row in enumerate(rows[:height]):
        add_line(screen, y + index, x, truncate(row, width), curses.A_DIM if not row else 0)


def collect_run_health(root: Path, paths: Any, state: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    artifacts = state.get("artifacts") or {}
    missing = [name for name, rel_path in artifacts.items() if isinstance(rel_path, str) and not (root / rel_path).exists()]
    recent_failures = [event for event in events if event.get("type") == "agent_failed"]
    verification_verdict = "not_run"
    verification_issues: list[str] = []
    verification_path = paths.run_dir / "verification.yaml"
    if verification_path.exists():
        try:
            data = yaml.safe_load(verification_path.read_text(encoding="utf-8")) or {}
            verification_verdict = str(data.get("verdict", "unknown"))
            issues = data.get("issues") or []
            if isinstance(issues, list):
                verification_issues = [str(item) for item in issues]
        except yaml.YAMLError as exc:
            verification_verdict = "invalid"
            verification_issues = [str(exc)]
    providers_path = root / ".runs" / "provider_capabilities.json"
    providers: dict[str, Any] = {}
    if providers_path.exists():
        try:
            providers = json.loads(providers_path.read_text(encoding="utf-8")).get("providers") or {}
        except json.JSONDecodeError:
            providers = {}
    providers_available = sum(1 for item in providers.values() if item.get("status") in {"available", "configured"})
    route_intent = "none"
    route_source = "none"
    route_actions = 0
    routing_plan = paths.run_dir / "routing_plan.json"
    if routing_plan.exists():
        try:
            route_data = json.loads(routing_plan.read_text(encoding="utf-8"))
            route_intent = str(route_data.get("intent", "unknown"))
            route_source = str(route_data.get("route_source", "unknown"))
            route_actions = len(route_data.get("actions") or [])
        except json.JSONDecodeError:
            route_intent = "invalid"
            route_source = "invalid"
    return {
        "missing_artifacts": missing,
        "recent_failures": recent_failures,
        "verification_verdict": verification_verdict,
        "verification_issues": verification_issues,
        "providers_available": providers_available,
        "providers_total": len(providers),
        "route_intent": route_intent,
        "route_source": route_source,
        "route_actions": route_actions,
    }


def draw_events(screen, y: int, x: int, height: int, width: int, events: list[dict[str, Any]]) -> None:
    if not events:
        add_line(screen, y, x, "No events yet.", curses.A_DIM)
        return
    for index, event in enumerate(events[-height:]):
        ts = short_time(str(event.get("ts", "")))
        event_type = str(event.get("type", ""))
        artifact = event.get("artifact")
        suffix = f"  {artifact}" if artifact else ""
        add_line(screen, y + index, x, truncate(f"{ts}  {event_type}{suffix}", width))


def draw_box(screen, y: int, x: int, height: int, width: int, title: str) -> None:
    if height < 3 or width < 10:
        return
    add_line(screen, y, x, "┌" + "─" * (width - 2) + "┐", curses.A_DIM)
    add_line(screen, y, x + 2, f" {title} ", curses.A_BOLD)
    for row in range(y + 1, y + height - 1):
        add_line(screen, row, x, "│", curses.A_DIM)
        add_line(screen, row, x + width - 1, "│", curses.A_DIM)
    add_line(screen, y + height - 1, x, "└" + "─" * (width - 2) + "┘", curses.A_DIM)


def truncate(text: str, width: int) -> str:
    if width <= 1:
        return ""
    if len(text) <= width:
        return text
    return text[: max(1, width - 1)] + "…"


def short_time(ts: str) -> str:
    if "T" in ts:
        return ts.split("T", 1)[1].split("+", 1)[0]
    return ts


def print_status(root: Path, run_id: str | None = None, json_output: bool = False) -> None:
    paths, state = load_run(root, run_id)
    events = read_events(paths, limit=5)
    health = collect_run_health(root, paths, state, events)
    if json_output:
        print(json.dumps({"state": state, "recent_events": events, "health": health}, ensure_ascii=False, indent=2))
        return
    print(f"MemoryOS Harness: {state.get('run_id')}")
    print(f"Task: {state.get('user_request')}")
    print(f"Project: {state.get('project')} | Phase: {state.get('phase')} | Status: {state.get('status')}")
    print(
        f"Health: verify={health.get('verification_verdict')} "
        f"providers={health.get('providers_available')}/{health.get('providers_total')} "
        f"route={health.get('route_intent')}/{health.get('route_actions')} "
        f"missing={len(health.get('missing_artifacts', []))} "
        f"failures={len(health.get('recent_failures', []))}"
    )
    print("")
    print("Agents:")
    for agent in state.get("agents", []):
        print(f"  {status_icon(agent.get('status'))} {agent.get('name')} [{agent.get('status')}]")
    print("")
    print(f"Run folder: {paths.run_dir}")
    print("Recent events:")
    for event in events:
        print(f"  - {event.get('ts')} {event.get('type')}")


def add_line(screen, y: int, x: int, text: str, attr: int = 0) -> None:
    height, width = screen.getmaxyx()
    if y >= height or x >= width:
        return
    screen.addnstr(y, x, text, max(0, width - x - 1), attr)


def add_wrapped(screen, y: int, x: int, width: int, text: str, attr: int = 0) -> int:
    row = y
    for line in textwrap.wrap(text, width=max(10, width)) or [""]:
        add_line(screen, row, x, line, attr)
        row += 1
    return row
