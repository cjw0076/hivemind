"""Minimal stdlib TUI for Hive Mind run status."""

from __future__ import annotations

import curses
import json
import locale
import os
import shutil
import subprocess
import textwrap
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml

from .harness import (
    build_memory_draft,
    build_summary,
    build_verification,
    append_event,
    acquire_control_lock,
    ask_router,
    git_diff_report,
    invoke_external_agent,
    invoke_local,
    load_run,
    read_events,
    read_hive_activity,
    read_transcript,
    heartbeat_control_lock,
    release_control_lock,
    run_board,
    orchestrate_prompt,
)

TUI_VIEWS = {"board", "events", "transcript", "agents", "artifacts", "memory", "society", "diff"}

CTRL_A = "\x01"
CTRL_C = "\x03"
CTRL_D = "\x04"
CTRL_E = "\x05"
CTRL_K = "\x0b"
CTRL_U = "\x15"
CTRL_V = "\x16"
CTRL_W = "\x17"


@dataclass(frozen=True)
class ComposerState:
    text: str = ""
    cursor: int = 0

    def clamp(self) -> "ComposerState":
        cursor = max(0, min(self.cursor, len(self.text)))
        return ComposerState(self.text, cursor)


def run_tui(root: Path, run_id: str | None = None, view: str = "board", control: bool = True) -> None:
    if view not in TUI_VIEWS:
        raise SystemExit(f"unknown TUI view: {view}")
    locale.setlocale(locale.LC_ALL, "")
    lock: dict[str, Any] | None = None
    if control:
        lock = acquire_control_lock(root, run_id)
    try:
        curses.wrapper(lambda screen: draw_loop(screen, root, run_id, view, control, lock.get("session_id") if lock else None))
    except KeyboardInterrupt:
        return
    except curses.error as exc:
        raise SystemExit(f"hive tui requires an interactive terminal: {exc}") from exc
    finally:
        if lock:
            release_control_lock(root, run_id, str(lock.get("session_id")))


def draw_loop(screen, root: Path, run_id: str | None, initial_view: str, control: bool, lock_session_id: str | None) -> None:
    curses.raw()
    curses.curs_set(0)
    init_theme()
    screen.keypad(True)
    screen.nodelay(True)
    message = "ready"
    view = initial_view
    composer = ComposerState()
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        try:
            if lock_session_id:
                heartbeat_control_lock(root, run_id, lock_session_id)
            paths, state = load_run(root, run_id)
            event_limit = 80 if view == "events" else 12
            transcript_limit = 160 if view == "transcript" else 24
            events = read_events(paths, limit=event_limit)
            activities = read_hive_activity(paths, limit=event_limit) or events
            transcript_lines = [line for line in read_transcript(root, paths.run_id, tail=transcript_limit).splitlines() if line.strip()]
            health = collect_run_health(root, paths, state, events)
            board = run_board(root, paths.run_id)
            draw_view(screen, height, width, root, paths, state, activities, transcript_lines, health, board, view, control)
        except Exception as exc:  # TUI should show recoverable state instead of crashing.
            add_line(screen, 1, 2, "Hive Mind Harness", curses.A_BOLD)
            add_wrapped(screen, 3, 2, width - 4, str(exc))
        draw_global_composer(screen, height, width, message, view, control, composer)
        screen.refresh()
        for key in read_input_events(screen):
            if not composer.text:
                key_code = ord(key) if isinstance(key, str) and len(key) == 1 else key
                next_view = view_for_key(key_code) if isinstance(key_code, int) else None
                if next_view:
                    view = next_view
                    message = f"view -> {view}"
                    continue
                if key_code == key_f(10):
                    message = handle_key(screen, root, run_id, ord("?"), control)
                    continue
            composer_action, composer = update_composer(composer, key)
            if composer_action == "submit":
                local_action = handle_local_composer_command(composer.text)
                if local_action.get("action") == "quit":
                    return
                if local_action.get("action") == "view":
                    view = str(local_action["view"])
                    message = f"view -> {view}"
                else:
                    message = submit_composer(root, run_id, composer.text, control)
                composer = ComposerState()
            elif composer_action == "cancel":
                message = "composer cancelled"
            elif composer_action == "quit":
                return
            elif composer_action == "clipboard_unavailable":
                message = "clipboard unavailable; use terminal paste or install wl-paste/xclip/xsel"
            elif composer_action == "editing":
                message = "typing prompt; Enter submits, Ctrl+C cancels, Ctrl+V pastes"
            else:
                key_code = ord(key) if isinstance(key, str) and len(key) == 1 else key
                if key_code in {10, 13, curses.KEY_ENTER}:
                    message = prompt_and_route(screen, root, run_id=run_id)
                else:
                    message = handle_key(screen, root, run_id, key_code if isinstance(key_code, int) else -1, control)
        time.sleep(0.05)


def read_input_events(screen, limit: int = 512) -> list[int | str]:
    events: list[int | str] = []
    for _ in range(limit):
        try:
            key = screen.get_wch()
        except curses.error:
            break
        events.append(key)
    return events


def update_composer(
    composer: ComposerState | str,
    key: int | str,
    clipboard_reader: Callable[[], str | None] | None = None,
) -> tuple[str | None, ComposerState]:
    """Return `(action, state)` for the always-visible TUI composer."""
    state = composer if isinstance(composer, ComposerState) else ComposerState(str(composer), len(str(composer)))
    state = state.clamp()
    text = state.text
    cursor = state.cursor
    reader = clipboard_reader or read_clipboard_text

    if key in {10, 13, curses.KEY_ENTER, "\n", "\r"}:
        return ("submit", state) if text.strip() else (None, state)
    if key in {27, "\x1b"}:
        return ("cancel", ComposerState())
    if key in {CTRL_C}:
        return "cancel", ComposerState()
    if key in {CTRL_D}:
        if not text:
            return "quit", state
        return "editing", ComposerState(text[:cursor] + text[cursor + 1 :], cursor).clamp()
    if key in {curses.KEY_LEFT}:
        return ("editing", ComposerState(text, cursor - 1).clamp()) if cursor > 0 else (None, state)
    if key in {curses.KEY_RIGHT}:
        return ("editing", ComposerState(text, cursor + 1).clamp()) if cursor < len(text) else (None, state)
    if key in {curses.KEY_HOME, CTRL_A}:
        return ("editing", ComposerState(text, 0)) if cursor else (None, state)
    if key in {curses.KEY_END, CTRL_E}:
        return ("editing", ComposerState(text, len(text))) if cursor != len(text) else (None, state)
    if key in {curses.KEY_BACKSPACE, 127, 8, "\x7f", "\b"}:
        if cursor <= 0:
            return None, state
        return "editing", ComposerState(text[: cursor - 1] + text[cursor:], cursor - 1)
    if key == curses.KEY_DC:
        if cursor >= len(text):
            return None, state
        return "editing", ComposerState(text[:cursor] + text[cursor + 1 :], cursor)
    if key in {CTRL_U}:
        return ("editing", ComposerState(text[cursor:], 0)) if cursor else (None, state)
    if key in {CTRL_K}:
        return ("editing", ComposerState(text[:cursor], cursor)) if cursor < len(text) else (None, state)
    if key in {CTRL_W}:
        start = previous_word_start(text, cursor)
        return ("editing", ComposerState(text[:start] + text[cursor:], start)) if start != cursor else (None, state)
    if key in {CTRL_V}:
        pasted = reader()
        if not pasted:
            return "clipboard_unavailable", state
        cleaned = normalize_paste_text(pasted)
        if not cleaned:
            return None, state
        return "editing", ComposerState(text[:cursor] + cleaned + text[cursor:], cursor + len(cleaned))
    if isinstance(key, str) and key and all(is_printable_input(ch) for ch in key):
        return "editing", ComposerState(text[:cursor] + key + text[cursor:], cursor + len(key))
    if isinstance(key, int) and 32 <= key <= 126:
        ch = chr(key)
        return "editing", ComposerState(text[:cursor] + ch + text[cursor:], cursor + 1)
    return None, state


def previous_word_start(text: str, cursor: int) -> int:
    index = max(0, min(cursor, len(text)))
    while index > 0 and text[index - 1].isspace():
        index -= 1
    while index > 0 and not text[index - 1].isspace():
        index -= 1
    return index


def is_printable_input(ch: str) -> bool:
    return ch in {"\t"} or (ch.isprintable() and unicodedata.category(ch)[0] != "C")


def normalize_paste_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return " ".join(line.strip() for line in normalized.splitlines() if line.strip()).strip()


def read_clipboard_text() -> str | None:
    commands = [
        ["wl-paste", "-n"],
        ["xclip", "-selection", "clipboard", "-o"],
        ["xsel", "-b", "-o"],
        ["pbpaste"],
    ]
    for command in commands:
        if shutil.which(command[0]) is None:
            continue
        try:
            completed = subprocess.run(command, text=True, capture_output=True, timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if completed.returncode == 0 and completed.stdout:
            return completed.stdout
    return None


def submit_composer(root: Path, run_id: str | None, prompt: str, control: bool = True) -> str:
    prompt = prompt.strip()
    if not prompt:
        return "empty prompt"
    if not control:
        return "observer mode: use controller mode to run actions"
    try:
        if prompt.startswith("/"):
            return handle_tui_command(root, run_id, prompt)
        report = orchestrate_prompt(root, prompt, run_id=None, complexity="default")
        return f"society plan -> {report.get('run_id')} ({len(report.get('members') or [])} members)"
    except Exception as exc:
        return f"error: {exc}"


def view_for_key(key: int) -> str | None:
    return {
        key_f(1): "board",
        key_f(2): "events",
        key_f(3): "transcript",
        key_f(4): "agents",
        key_f(5): "artifacts",
        key_f(6): "memory",
        key_f(7): "society",
        key_f(8): "diff",
    }.get(key)


def key_f(index: int) -> int:
    return curses.KEY_F0 + index


def handle_local_composer_command(prompt: str) -> dict[str, Any]:
    parts = prompt.strip().split()
    if not parts:
        return {}
    name = parts[0].lower()
    if name in {"/quit", "/exit"}:
        return {"action": "quit"}
    if name == "/view" and len(parts) > 1:
        view = {
            "1": "board",
            "2": "events",
            "3": "transcript",
            "4": "agents",
            "5": "artifacts",
            "6": "memory",
            "7": "society",
            "8": "diff",
        }.get(parts[1].lower(), parts[1].lower())
        if view in TUI_VIEWS:
            return {"action": "view", "view": view}
    if name in {"/board", "/events", "/transcript", "/agents", "/artifacts", "/memory", "/society", "/diff"}:
        return {"action": "view", "view": name[1:]}
    return {}


def handle_key(screen, root: Path, run_id: str | None, key: int, control: bool = True) -> str:
    try:
        if not control and key not in {ord("r"), ord("R"), ord("h"), ord("H"), ord("?")}:
            return "observer mode: use --control to run actions"
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
            return "views: F1 board F2 events F3 transcript F4 agents F5 artifacts F6 memory F7 society F8 diff"
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
        row = max(0, height - 2)
        clear_line(screen, row)
        label = "hive> "
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
    report = orchestrate_prompt(root, prompt, run_id=None, complexity="default")
    return f"society plan -> {report.get('run_id')} ({len(report.get('members') or [])} members)"


def handle_tui_command(root: Path, run_id: str | None, command: str) -> str:
    parts = command.split()
    name = parts[0].lower()
    if name in {"/help", "/h", "/?"}:
        return "commands: /ask task, /route, /verify, /memory, /summary, /diff, /local, /claude, /codex, /gemini, /view, /quit"
    if name == "/ask" and len(parts) > 1:
        report = orchestrate_prompt(root, " ".join(parts[1:]), run_id=None, complexity="default")
        return f"society plan -> {report.get('run_id')} ({len(report.get('members') or [])} members)"
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


def draw_view(
    screen,
    height: int,
    width: int,
    root: Path,
    paths: Any,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    transcript_lines: list[str],
    health: dict[str, Any],
    board: dict[str, Any],
    view: str,
    control: bool,
) -> None:
    if view == "events":
        draw_full_events_view(screen, height, width, state, events)
        return
    if view == "transcript":
        draw_full_transcript_view(screen, height, width, state, transcript_lines)
        return
    if view == "agents":
        draw_full_agents_view(screen, height, width, root, paths, state, board)
        return
    if view == "artifacts":
        draw_full_artifacts_view(screen, height, width, state, board)
        return
    if view == "memory":
        draw_memory_view(screen, height, width, paths)
        return
    if view == "society":
        draw_society_view(screen, height, width, paths, board)
        return
    if view == "diff":
        draw_diff_view(screen, height, width, paths)
        return
    draw_board_view(screen, height, width, state, events, health, board, control)


def draw_state(
    screen,
    height: int,
    width: int,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    transcript_lines: list[str],
    health: dict[str, Any],
    board: dict[str, Any],
) -> None:
    if height < 18 or width < 64:
        draw_compact(screen, height, width, state, events, health)
        return
    if width >= 110 and height >= 28:
        draw_dashboard(screen, height, width, state, events, transcript_lines, health, board)
        return

    content_width = max(40, width - 4)
    footer_row = max(0, height - 2)
    top_status = f"Hive Mind Harness  {state.get('project')}  {state.get('phase')} / {state.get('status')}"
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


def draw_global_composer(screen, height: int, width: int, message: str, view: str = "board", control: bool = True, composer: ComposerState | str = "") -> None:
    if height < 4:
        return
    state = composer if isinstance(composer, ComposerState) else ComposerState(str(composer), len(str(composer)))
    state = state.clamp()
    mode = "controller" if control else "observer"
    help_text = (
        f"view:{view} mode:{mode}  Enter submits  Ctrl+C cancels  Ctrl+V pastes  Ctrl+D quits  "
        "F1-F8 views"
    )
    clear_line(screen, height - 2)
    clear_line(screen, height - 1)
    prompt_prefix = "hive> "
    prompt = prompt_prefix + state.text
    add_line(screen, height - 2, 2, truncate(prompt, max(10, width - 4)), color(1, curses.A_BOLD))
    add_line(screen, height - 1, 2, truncate(f"{message}  |  {help_text}", max(10, width - 4)), color(2) if message != "ready" else curses.A_DIM)
    try:
        cursor_x = 2 + display_width(prompt_prefix + state.text[: state.cursor])
        screen.move(height - 2, min(max(2, width - 2), cursor_x))
        curses.curs_set(1)
    except curses.error:
        pass


def display_width(text: str) -> int:
    width = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in {"F", "W"} else 1
    return width


def draw_board_view(
    screen,
    height: int,
    width: int,
    state: dict[str, Any],
    events: list[dict[str, Any]],
    health: dict[str, Any],
    board: dict[str, Any],
    control: bool,
) -> None:
    if height < 18 or width < 64:
        draw_compact(screen, height, width, state, events, health)
        return
    margin = 2
    content_width = width - 4
    footer_row = height - 3
    mode = "controller" if control else "observer"
    clock = time.strftime("%H:%M")
    top = f"Hive Mind  Run {state.get('run_id')}  Project {state.get('project')}  Mode {mode}  {clock}"
    add_line(screen, 0, margin, truncate(top, content_width), color(1, curses.A_BOLD))

    current_h = 7
    next_h = current_h
    current_w = max(38, content_width // 2 - 1)
    next_w = content_width - current_w - 2
    draw_box(screen, 2, margin, current_h, current_w, "Current")
    draw_current_panel(screen, 3, margin + 2, current_h - 2, current_w - 4, state, health, board)
    draw_box(screen, 2, margin + current_w + 2, next_h, next_w, "Next")
    draw_next_actions(screen, 3, margin + current_w + 4, next_h - 2, next_w - 4, board)

    pipeline_top = 10
    draw_box(screen, pipeline_top, margin, 4, content_width, "Pipeline")
    draw_pipeline_bar(screen, pipeline_top + 1, margin + 2, 2, content_width - 4, board.get("pipeline", []))

    agents_top = 15
    events_h = 6
    decision_h = 5
    agents_h = max(7, footer_row - agents_top - events_h - decision_h - 2)
    draw_box(screen, agents_top, margin, agents_h, content_width, "Agents")
    draw_agent_reason_table(screen, agents_top + 1, margin + 2, agents_h - 2, content_width - 4, board.get("agents", []), health)

    decision_top = agents_top + agents_h + 1
    draw_box(screen, decision_top, margin, decision_h, content_width, "Decisions / Open Questions")
    draw_decisions_panel(screen, decision_top + 1, margin + 2, decision_h - 2, content_width - 4, state, board, health)

    events_top = decision_top + decision_h + 1
    draw_box(screen, events_top, margin, max(3, footer_row - events_top), content_width, "Latest Events")
    draw_events(screen, events_top + 1, margin + 2, max(1, footer_row - events_top - 2), content_width - 4, events)


def draw_current_panel(screen, y: int, x: int, height: int, width: int, state: dict[str, Any], health: dict[str, Any], board: dict[str, Any]) -> None:
    required, optional = classify_missing(board)
    phase = phase_label(board, state)
    failures = len(health.get("recent_failures", []))
    health_label = "GOOD" if failures == 0 and not required else "NEEDS REVIEW"
    rows = [
        f"Task: {state.get('user_request')}",
        f"Phase: {phase}",
        f"Health: {health_label}",
        f"Missing: {len(required)} required / {len(optional)} optional",
        f"Workers: {health.get('providers_available')}/{health.get('providers_total')} ready",
    ]
    for index, row in enumerate(rows[:height]):
        attr = color(1, curses.A_BOLD) if index == 2 and health_label == "GOOD" else (color(3, curses.A_BOLD) if index == 2 else 0)
        add_line(screen, y + index, x, truncate(row, width), attr)


def draw_pipeline_bar(screen, y: int, x: int, height: int, width: int, pipeline: list[dict[str, Any]]) -> None:
    done = [item for item in pipeline if item.get("status") == "done"]
    pending = [item for item in pipeline if item.get("status") != "done"]
    lines = [
        "  ".join(f"✓ {str(item.get('step')).title()}" for item in done),
        "  ".join(f"○ {str(item.get('step')).title()}" for item in pending),
    ]
    for index, line in enumerate(lines[:height]):
        add_line(screen, y + index, x, truncate(line or "-", width), color(1 if index == 0 else 3))


def draw_agent_reason_table(screen, y: int, x: int, height: int, width: int, agents: list[dict[str, Any]], health: dict[str, Any]) -> None:
    add_line(screen, y, x, truncate("Agent/Role              Status      Provider        Reason", width), curses.A_DIM)
    for index, agent in enumerate(agents[: max(0, height - 1)]):
        status = str(agent.get("status") or "pending")
        name = str(agent.get("name") or "agent")
        provider = name.split("-", 1)[0]
        reason = agent_reason(name, status, health)
        row = f"{name:<23} {status_icon(status)} {status:<10} {provider:<14} {reason}"
        add_line(screen, y + index + 1, x, truncate(row, width), status_attr(status))


def draw_decisions_panel(screen, y: int, x: int, height: int, width: int, state: dict[str, Any], board: dict[str, Any], health: dict[str, Any]) -> None:
    next_action = board.get("next") or {}
    rows = [
        "Decision: keep Hive Mind as the controller; MemoryOS owns accepted memory.",
        f"Decision: next action is {next_action.get('command')}",
        f"Open: should Codex execute or remain prepare-only? route={health.get('route_intent')}",
        "Open: is context fresh, or only context_pack.md present?",
    ]
    for index, row in enumerate(rows[:height]):
        add_line(screen, y + index, x, truncate(row, width), color(2) if row.startswith("Decision") else color(3))


def draw_full_events_view(screen, height: int, width: int, state: dict[str, Any], events: list[dict[str, Any]]) -> None:
    draw_view_header(screen, width, "Events", state, "Live event stream from hive_events.jsonl/events.jsonl")
    draw_events(screen, 4, 2, max(1, height - 7), width - 4, events)


def draw_full_transcript_view(screen, height: int, width: int, state: dict[str, Any], transcript_lines: list[str]) -> None:
    draw_view_header(screen, width, "Transcript", state, "Human-readable run log; raw JSON hidden by default")
    draw_log_lines(screen, 4, 2, max(1, height - 7), width - 4, transcript_lines)


def draw_full_agents_view(screen, height: int, width: int, root: Path, paths: Any, state: dict[str, Any], board: dict[str, Any]) -> None:
    draw_view_header(screen, width, "Agents", state, "Provider/local worker detail board")
    rows = ["Agent/Role                  Status      Mode              Last Artifact"]
    for agent in board.get("agents", []):
        name = str(agent.get("name") or "")
        status = str(agent.get("status") or "pending")
        artifact = find_agent_artifact(paths, name)
        rows.append(f"{name:<27} {status:<11} {agent_mode(name):<17} {artifact}")
    draw_rows(screen, 4, 2, height - 7, width - 4, rows)


def draw_full_artifacts_view(screen, height: int, width: int, state: dict[str, Any], board: dict[str, Any]) -> None:
    draw_view_header(screen, width, "Artifacts", state, "Exists vs current-phase completion are separate")
    rows = ["Artifact                 Exists  Freshness  Class            Producer              Path"]
    for item in board.get("artifacts", []):
        name = str(item.get("name") or "")
        exists = "yes" if item.get("exists") else "no"
        rows.append(
            f"{name:<24} {exists:<7} {str(item.get('freshness')):<10} "
            f"{str(item.get('phase_class')):<16} {str(item.get('producer')):<21} {item.get('path')}"
        )
    required, optional = classify_missing(board)
    rows.extend(["", f"Required missing: {', '.join(required) if required else 'none'}", f"Optional/post-execution missing: {', '.join(optional) if optional else 'none'}"])
    draw_rows(screen, 4, 2, height - 7, width - 4, rows)


def draw_memory_view(screen, height: int, width: int, paths: Any) -> None:
    draw_view_header(screen, width, "Memory Drafts", {"run_id": paths.run_id}, "Hive Mind drafts; MemoryOS owns review/acceptance")
    rows = ["No memory drafts yet."]
    draft_path = paths.run_dir / "memory_drafts.json"
    if draft_path.exists():
        try:
            data = json.loads(draft_path.read_text(encoding="utf-8"))
            drafts = data.get("memory_drafts") if isinstance(data, dict) else []
            rows = []
            for index, draft in enumerate(drafts or []):
                rows.append(f"[{index}] {draft.get('type')} {draft.get('status')} confidence={draft.get('confidence')}")
                rows.append(f"    {draft.get('content')}")
                rows.append(f"    refs: {', '.join(draft.get('raw_refs') or [])}")
            if not rows:
                rows = ["memory_drafts.json exists, but contains no drafts."]
        except (json.JSONDecodeError, OSError) as exc:
            rows = [f"Invalid memory_drafts.json: {exc}"]
    draw_rows(screen, 4, 2, height - 7, width - 4, rows)


def draw_society_view(screen, height: int, width: int, paths: Any, board: dict[str, Any]) -> None:
    draw_view_header(screen, width, "Society", {"run_id": paths.run_id}, "Roles, disagreements, peer review placeholders")
    rows = ["Members"]
    society_path = paths.run_dir / "society_plan.json"
    if society_path.exists():
        try:
            data = json.loads(society_path.read_text(encoding="utf-8"))
            for member in data.get("members") or []:
                rows.append(f"- {member.get('id') or member.get('agent')} role={member.get('role')} status={member.get('status')}")
        except (json.JSONDecodeError, OSError) as exc:
            rows.append(f"Invalid society_plan.json: {exc}")
    else:
        rows.append("- no society_plan.json")
    rows.extend(["", "Disagreements", "- not extracted yet", "", "Open Questions", "- should Codex execute or remain prepare-only?", "- should local context be rerun?"])
    draw_rows(screen, 4, 2, height - 7, width - 4, rows)


def draw_diff_view(screen, height: int, width: int, paths: Any) -> None:
    draw_view_header(screen, width, "Diff", {"run_id": paths.run_id}, "Git-first observer view")
    report_path = paths.run_dir / "git_diff_report.json"
    rows = ["No git diff report yet. Run: hive diff"]
    if report_path.exists():
        try:
            data = json.loads(report_path.read_text(encoding="utf-8"))
            rows = ["Changed Files"]
            rows.extend(f"- {path}" for path in data.get("changed_files") or [])
            rows.extend(["", "Next", "hive review-diff", "hive check run", "hive commit-summary"])
        except (json.JSONDecodeError, OSError) as exc:
            rows = [f"Invalid git_diff_report.json: {exc}"]
    draw_rows(screen, 4, 2, height - 7, width - 4, rows)


def draw_view_header(screen, width: int, title: str, state: dict[str, Any], subtitle: str) -> None:
    run_id = state.get("run_id", "-")
    add_line(screen, 0, 2, f"Hive Mind / {title}", color(1, curses.A_BOLD))
    add_line(screen, 1, 2, truncate(f"Run {run_id}  {subtitle}", max(10, width - 4)), curses.A_DIM)
    add_line(screen, 2, 2, "─" * max(0, width - 4), curses.A_DIM)


def draw_rows(screen, y: int, x: int, height: int, width: int, rows: list[str]) -> None:
    for index, row in enumerate(rows[: max(0, height)]):
        attr = curses.A_BOLD if index == 0 and row else 0
        add_line(screen, y + index, x, truncate(row, width), attr)


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
    transcript_lines: list[str],
    health: dict[str, Any],
    board: dict[str, Any],
) -> None:
    margin = 2
    content_width = width - 4
    composer_top = height - 3
    add_line(screen, 0, margin, "hive", color(1, curses.A_BOLD))
    add_line(screen, 0, margin + 5, "Hive Mind Harness", curses.A_BOLD)
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
    middle_h = max(8, composer_top - middle_top - bottom_h - 1)
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
    events_w = max(40, content_width // 3)
    logs_w = max(44, content_width // 3)
    next_w = content_width - events_w - logs_w - 4
    if next_w < 28:
        events_w = max(44, content_width // 2)
        logs_w = content_width - events_w - 2
        next_w = 0
    draw_box(screen, bottom_top, margin, bottom_h, events_w, "Latest Events")
    draw_events(screen, bottom_top + 1, margin + 2, bottom_h - 2, events_w - 4, events)
    logs_x = margin + events_w + 2
    draw_box(screen, bottom_top, logs_x, bottom_h, logs_w, "Live Transcript")
    draw_log_lines(screen, bottom_top + 1, logs_x + 2, bottom_h - 2, logs_w - 4, transcript_lines)
    if next_w >= 28:
        next_x = logs_x + logs_w + 2
        draw_box(screen, bottom_top, next_x, bottom_h, next_w, "Next")
        draw_next_actions(screen, bottom_top + 1, next_x + 2, bottom_h - 2, next_w - 4, board)

    keys = "Keys: enter talk  / command  n new  a route  c claude  x codex  g gemini  v verify  m memory  d diff  q quit"
    add_line(screen, composer_top - 1, margin, truncate(keys, content_width), curses.A_DIM)


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
        "2. hive status",
        "3. hive check run",
    ]
    for index, row in enumerate(rows[:height]):
        attr = color(5 if index == 0 else 2) if index in {0, 2, 3} else curses.A_DIM
        add_line(screen, y + index, x, truncate(row, width), attr)


def classify_missing(board: dict[str, Any]) -> tuple[list[str], list[str]]:
    required: list[str] = []
    optional: list[str] = []
    for item in board.get("artifacts", []):
        if item.get("status") == "ok":
            continue
        name = str(item.get("name") or "")
        if item.get("phase_class") == "required":
            required.append(name)
        else:
            optional.append(name)
    return required, optional


def phase_label(board: dict[str, Any], state: dict[str, Any]) -> str:
    pipeline = board.get("pipeline") or []
    pending = [str(item.get("step")) for item in pipeline if item.get("status") != "done"]
    if pending:
        return f"{pending[0]}.pending"
    return f"{state.get('phase')}.{state.get('status')}"


def agent_reason(name: str, status: str, health: dict[str, Any]) -> str:
    if status == "completed":
        return "artifact ready"
    if status == "prepared":
        return "prompt/result prepared"
    if "context" in name and status == "pending":
        return "local context not run"
    if "codex" in name and status == "pending":
        return "waiting for validated handoff"
    if "gemini" in name and status == "pending":
        return "optional review not run"
    if status == "failed":
        return "see events/transcript"
    return "pending"


def agent_mode(name: str) -> str:
    if name.startswith("local"):
        return "local worker"
    if name.startswith("claude"):
        return "planner/read-only"
    if name.startswith("codex"):
        return "executor/approval"
    if name.startswith("gemini"):
        return "reviewer/read-only"
    return "provider"


def find_agent_artifact(paths: Any, name: str) -> str:
    parts = name.split("-", 1)
    provider = parts[0] if parts else name
    role_hint = parts[1] if len(parts) > 1 else ""
    agent_dir = paths.run_dir / "agents" / provider
    if not agent_dir.exists():
        return "-"
    results = sorted(agent_dir.glob("*_result.yaml"))
    if role_hint:
        for path in results:
            if role_hint.split("-", 1)[0] in path.name:
                return path.relative_to(paths.root).as_posix()
    return results[-1].relative_to(paths.root).as_posix() if results else "-"


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
    add_line(screen, row, 2, "Hive Mind Harness", curses.A_BOLD)
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
        if "summary" in event:
            actor = str(event.get("actor", "hive"))
            action = str(event.get("action", "activity"))
            summary = str(event.get("summary", ""))
            add_line(screen, y + index, x, truncate(f"{ts}  {actor}  {action}  {summary}", width))
            continue
        event_type = str(event.get("type", ""))
        artifact = event.get("artifact")
        suffix = f"  {artifact}" if artifact else ""
        add_line(screen, y + index, x, truncate(f"{ts}  {event_type}{suffix}", width))


def draw_log_lines(screen, y: int, x: int, height: int, width: int, lines: list[str]) -> None:
    if not lines:
        add_line(screen, y, x, "No transcript yet.", curses.A_DIM)
        return
    compact = [line.strip("# ").strip() for line in lines if line.strip()]
    for index, line in enumerate(compact[-height:]):
        add_line(screen, y + index, x, truncate(line, width))


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
    print(f"Hive Mind Harness: {state.get('run_id')}")
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


def clear_line(screen, y: int) -> None:
    height, width = screen.getmaxyx()
    if y >= height:
        return
    screen.move(y, 0)
    screen.clrtoeol()


def add_wrapped(screen, y: int, x: int, width: int, text: str, attr: int = 0) -> int:
    row = y
    for line in textwrap.wrap(text, width=max(10, width)) or [""]:
        add_line(screen, row, x, line, attr)
        row += 1
    return row
