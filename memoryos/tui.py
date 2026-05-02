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
    git_diff_report,
    invoke_external_agent,
    invoke_local,
    load_run,
    read_events,
    run_board,
)


def run_tui(root: Path, run_id: str | None = None) -> None:
    curses.wrapper(lambda screen: draw_loop(screen, root, run_id))


def draw_loop(screen, root: Path, run_id: str | None) -> None:
    curses.curs_set(0)
    init_theme()
    screen.nodelay(True)
    message = "ready"
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        try:
            paths, state = load_run(root, run_id)
            events = read_events(paths, limit=8)
            health = collect_run_health(root, paths, state, events)
            board = run_board(root, paths.run_id)
            draw_state(screen, height, width, state, events, health, board)
        except Exception as exc:  # TUI should show recoverable state instead of crashing.
            add_line(screen, 1, 2, "MemoryOS Harness", curses.A_BOLD)
            add_wrapped(screen, 3, 2, width - 4, str(exc))
        footer = "enter talk  / command  q quit  n new  e context  a route  l local  c claude  x codex  g gemini  v verify  s summary  m memory  d diff"
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
        if key in {10, 13, curses.KEY_ENTER, ord("/")}:
            prefix = "/" if key == ord("/") else ""
            return prompt_and_route(screen, root, run_id=run_id, prefix=prefix)
        if key in {ord("r"), ord("R")}:
            return "refreshed"
        if key in {ord("e"), ord("E")}:
            return edit_context_pack(screen, root, run_id)
        if key in {ord("n"), ord("N")}:
            return prompt_and_route(screen, root, run_id=run_id)
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
        if key in {ord("d"), ord("D")}:
            report = git_diff_report(root, run_id=run_id)
            return f"diff -> {report.get('path')} ({len(report.get('changed_files') or [])} files)"
        if key in {ord("h"), ord("H"), ord("?")}:
            return "keys: n prompt, e edit context, a route, l/c/x/g agents, v verify, s summarize, m memory, d diff"
    except Exception as exc:
        return f"error: {exc}"
    return "unknown key"


def prompt_and_route(screen, root: Path, run_id: str | None = None, prefix: str = "") -> str:
    height, width = screen.getmaxyx()
    curses.echo()
    curses.curs_set(1)
    screen.nodelay(False)
    prompt = ""
    try:
        row = max(0, height - 3)
        screen.move(row, 0)
        screen.clrtoeol()
        label = "mos> "
        add_line(screen, row, 2, label + prefix, curses.A_BOLD)
        screen.refresh()
        raw = screen.getstr(row, 2 + len(label) + len(prefix), max(20, min(1000, width - 8 - len(prefix))))
        prompt = (prefix + raw.decode("utf-8", errors="replace")).strip()
    finally:
        curses.noecho()
        curses.curs_set(0)
        screen.nodelay(True)
    if not prompt:
        return "empty prompt"
    if prompt.startswith("/"):
        return handle_tui_command(root, run_id, prompt)
    path = ask_router(root, prompt, run_id=None, complexity="default")
    return f"new prompt routed -> {path}"


def handle_tui_command(root: Path, run_id: str | None, command: str) -> str:
    parts = command.split()
    name = parts[0].lower()
    if name in {"/help", "/h", "/?"}:
        return "commands: /ask task, /route, /verify, /memory, /summary, /diff, /local, /claude, /codex, /gemini"
    if name == "/ask" and len(parts) > 1:
        path = ask_router(root, " ".join(parts[1:]), run_id=None, complexity="default")
        return f"ask routed -> {path}"
    if name in {"/route", "/autoroute"}:
        paths, state = load_run(root, run_id)
        prompt = str(state.get("user_request") or paths.context_pack.read_text(encoding="utf-8")[:2000])
        path = ask_router(root, prompt, run_id=paths.run_id, complexity="default")
        return f"auto-route -> {path}"
    if name == "/verify":
        return f"verification -> {build_verification(root, run_id=run_id)}"
    if name == "/memory":
        return f"memory draft -> {build_memory_draft(root, run_id=run_id)}"
    if name == "/summary":
        return f"summary -> {build_summary(root, run_id=run_id)}"
    if name == "/diff":
        report = git_diff_report(root, run_id=run_id)
        return f"diff -> {report.get('path')} ({len(report.get('changed_files') or [])} files)"
    if name == "/local":
        role = parts[1] if len(parts) > 1 else "context"
        return f"local {role} -> {invoke_local(root, role, run_id=run_id, complexity='default')}"
    if name in {"/claude", "/codex", "/gemini"}:
        agent = name[1:]
        role = parts[1] if len(parts) > 1 else {"claude": "planner", "codex": "executor", "gemini": "reviewer"}[agent]
        return f"{agent} {role} -> {invoke_external_agent(root, agent, role, run_id=run_id, execute=False)}"
    return f"unknown command: {command}"


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
    board: dict[str, Any],
) -> None:
    if height < 18 or width < 64:
        draw_compact(screen, height, width, state, events, health)
        return
    if width >= 110 and height >= 28:
        draw_dashboard(screen, height, width, state, events, health, board)
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

    pipeline_line = "  ".join(f"{'✓' if item.get('status') == 'done' else '○'} {item.get('step')}" for item in board.get("pipeline", []))
    add_line(screen, 6, 2, truncate(f"Pipeline {pipeline_line}", content_width), curses.A_BOLD)

    panel_top = 8
    events_h = 7
    if width >= 96:
        left_x = 2
        gap = 2
        left_w = max(42, min(56, content_width // 2))
        right_x = left_x + left_w + gap
        right_w = max(32, content_width - left_w - gap)
        panel_h = max(8, footer_row - panel_top - events_h - 1)
        draw_box(screen, panel_top, left_x, panel_h, left_w, "Agents")
        draw_agents(screen, panel_top + 1, left_x + 2, panel_h - 2, left_w - 4, state.get("agents", []))
        draw_box(screen, panel_top, right_x, panel_h, right_w, "Artifacts / Next")
        draw_artifacts(screen, panel_top + 1, right_x + 2, panel_h - 2, right_w - 4, state, health, board)
        events_top = panel_top + panel_h + 1
    elif height >= 28:
        panel_h = max(6, min(9, footer_row - panel_top - events_h - 5))
        draw_box(screen, panel_top, 2, panel_h, content_width, "Agent Pipeline")
        draw_agents(screen, panel_top + 1, 4, panel_h - 2, content_width - 4, state.get("agents", []))
        artifacts_top = panel_top + panel_h + 1
        artifacts_h = 5
        draw_box(screen, artifacts_top, 2, artifacts_h, content_width, "Run Health / Artifacts")
        draw_artifacts(screen, artifacts_top + 1, 4, artifacts_h - 2, content_width - 4, state, health, board)
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


def init_theme() -> None:
    if not curses.has_colors():
        return
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_BLUE, -1)


def color(n: int, extra: int = 0) -> int:
    return (curses.color_pair(n) if curses.has_colors() else 0) | extra


def draw_dashboard(
    screen,
    height: int,
    width: int,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    health: dict[str, Any],
    board: dict[str, Any],
) -> None:
    margin = 2
    content_width = width - 4
    footer_row = height - 3
    add_line(screen, 0, margin, "mos", color(1, curses.A_BOLD))
    add_line(screen, 0, margin + 5, "MemoryOS Harness", curses.A_BOLD)
    clock = time.strftime("%H:%M:%S")
    top_right = f"Local {health.get('providers_available')}/{health.get('providers_total')}   Safe Mode workspace-write   {clock}"
    add_line(screen, 0, max(margin + 24, width - len(top_right) - 2), truncate(top_right, max(10, width - 28)), curses.A_DIM)

    summary_h = 6
    left_w = max(48, content_width // 2 - 1)
    right_w = content_width - left_w - 2
    draw_box(screen, 2, margin, summary_h, left_w, "Run")
    draw_run_summary(screen, 3, margin + 2, summary_h - 2, left_w - 4, state, board)
    draw_box(screen, 2, margin + left_w + 2, summary_h, right_w, "Health")
    draw_health_summary(screen, 3, margin + left_w + 4, summary_h - 2, right_w - 4, state, health, board)

    middle_top = 9
    bottom_h = 7
    footer_h = 2
    middle_h = max(8, footer_row - middle_top - bottom_h - 1)
    gap = 1
    pipeline_w = max(34, content_width // 3 - 1)
    agents_w = max(42, content_width // 3)
    artifacts_w = content_width - pipeline_w - agents_w - (gap * 2)
    pipeline_x = margin
    agents_x = pipeline_x + pipeline_w + gap
    artifacts_x = agents_x + agents_w + gap

    draw_box(screen, middle_top, pipeline_x, middle_h, pipeline_w, "Pipeline")
    draw_pipeline(screen, middle_top + 1, pipeline_x + 2, middle_h - 2, pipeline_w - 4, board.get("pipeline", []))
    draw_box(screen, middle_top, agents_x, middle_h, agents_w, "Agents")
    draw_agent_table(screen, middle_top + 1, agents_x + 2, middle_h - 2, agents_w - 4, board.get("agents", []))
    draw_box(screen, middle_top, artifacts_x, middle_h, artifacts_w, "Artifacts")
    draw_artifact_table(screen, middle_top + 1, artifacts_x + 2, middle_h - 2, artifacts_w - 4, board.get("artifacts", []))

    bottom_top = middle_top + middle_h + 1
    events_w = max(58, content_width // 2 + 10)
    next_w = content_width - events_w - 2
    draw_box(screen, bottom_top, margin, bottom_h, events_w, "Latest Events")
    draw_events(screen, bottom_top + 1, margin + 2, bottom_h - 2, events_w - 4, events)
    draw_box(screen, bottom_top, margin + events_w + 2, bottom_h, next_w, "Next Recommended Actions")
    draw_next_actions(screen, bottom_top + 1, margin + events_w + 4, bottom_h - 2, next_w - 4, board)

    keys = "Keys: n new  a autoroute  l local  c claude  x codex  g gemini  v verify  s summarize  m memory  d diff  h help  q quit"
    draw_box(screen, footer_row, margin, footer_h + 1, content_width, "")
    add_line(screen, footer_row + 1, margin + 2, truncate(keys, content_width - 4), curses.A_DIM)


def draw_run_summary(screen, y: int, x: int, height: int, width: int, state: dict[str, Any], board: dict[str, Any]) -> None:
    phase = state.get("phase")
    status = state.get("status")
    rows = [
        f"Run      {state.get('run_id')}",
        f"Task     {state.get('user_request')}",
        f"Project  {state.get('project')}",
        f"Phase    {phase} -> {status}",
    ]
    for index, row in enumerate(rows[:height]):
        attr = color(5, curses.A_BOLD) if index == 3 else 0
        add_line(screen, y + index, x, truncate(row, width), attr)


def draw_health_summary(
    screen,
    y: int,
    x: int,
    height: int,
    width: int,
    state: dict[str, Any],
    health: dict[str, Any],
    board: dict[str, Any],
) -> None:
    next_action = board.get("next") or {}
    failures = len(health.get("recent_failures", []))
    missing = len([item for item in board.get("artifacts", []) if item.get("status") != "ok"])
    verdict = health.get("verification_verdict")
    health_label = "GOOD" if failures == 0 else "NEEDS REVIEW"
    rows = [
        ("Health", health_label, color(1 if failures == 0 else 3, curses.A_BOLD)),
        ("Latest Event", str(state.get("latest_event", "-")), 0),
        ("Failures", str(failures), color(4) if failures else 0),
        ("Missing Artifacts", str(missing), color(3) if missing else color(1)),
        ("Verify", str(verdict), color(1) if verdict == "pass" else curses.A_DIM),
        ("Next Action", str(next_action.get("command")), color(2)),
    ]
    for index, (label, value, attr) in enumerate(rows[:height]):
        add_line(screen, y + index, x, truncate(f"{label:<18} {value}", width), attr)


def draw_pipeline(screen, y: int, x: int, height: int, width: int, pipeline: list[dict[str, Any]]) -> None:
    for index, item in enumerate(pipeline[:height]):
        status = item.get("status")
        attr = color(1) if status == "done" else curses.A_DIM
        icon = "✓" if status == "done" else "○"
        step = str(item.get("step", "")).title()
        artifact = item.get("path") or item.get("artifact")
        row = f"{icon} {index + 1:<2} {step:<12} {artifact}"
        add_line(screen, y + index, x, truncate(row, width), attr)


def draw_agent_table(screen, y: int, x: int, height: int, width: int, agents: list[dict[str, Any]]) -> None:
    add_line(screen, y, x, truncate("Agent / Role                  Status", width), curses.A_DIM)
    if height <= 1:
        return
    for index, agent in enumerate(agents[: height - 1]):
        status = agent.get("status")
        attr = status_attr(status)
        name = str(agent.get("name", "agent"))
        row = f"{name:<28} {status_icon(status)} {status}"
        add_line(screen, y + index + 1, x, truncate(row, width), attr)


def draw_artifact_table(screen, y: int, x: int, height: int, width: int, artifacts: list[dict[str, Any]]) -> None:
    for index, item in enumerate(artifacts[:height]):
        ok = item.get("status") == "ok"
        attr = color(1) if ok else color(3)
        icon = "✓" if ok else "○"
        row = f"{icon} {item.get('name'):<18} {item.get('status'):<8} {item.get('path')}"
        add_line(screen, y + index, x, truncate(row, width), attr)


def draw_next_actions(screen, y: int, x: int, height: int, width: int, board: dict[str, Any]) -> None:
    next_action = board.get("next") or {}
    rows = [
        f"1. {next_action.get('command')}",
        f"Reason: {next_action.get('reason')}",
        "2. mos status",
        "3. mos check run",
    ]
    for index, row in enumerate(rows[:height]):
        attr = color(5 if index == 0 else 2) if index in {0, 2, 3} else curses.A_DIM
        add_line(screen, y + index, x, truncate(row, width), attr)


def status_attr(status: str | None) -> int:
    if status in {"completed"}:
        return color(1)
    if status in {"running", "in_progress"}:
        return color(2, curses.A_BOLD)
    if status in {"prepared", "ready"}:
        return color(3)
    if status == "failed":
        return color(4, curses.A_BOLD)
    return curses.A_DIM


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


def draw_artifacts(screen, y: int, x: int, height: int, width: int, state: dict[str, Any], health: dict[str, Any], board: dict[str, Any]) -> None:
    context = state.get("context") or {}
    next_action = board.get("next") or {}
    rows = [
        f"next: {next_action.get('command')}",
        f"reason: {next_action.get('reason')}",
        "",
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
