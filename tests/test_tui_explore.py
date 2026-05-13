"""Tests for the unified explore TUI view (ASC-0097)."""

import curses
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from hivemind.tui_explore import (
    EXPLORE_PANES,
    ExploreState,
    draw_explore_view,
    refresh_explore_data,
    update_explore_navigation,
    _draw_agents_pane,
    _draw_runs_pane,
    _draw_inspect_pane,
    _draw_events_pane,
)


def _mock_add_line(screen, y, x, text, attr=0):
    screen.lines.append((y, x, text, attr))


def _mock_draw_box(screen, y, x, h, w, title):
    screen.boxes.append((y, x, h, w, title))


def _mock_truncate(text, width):
    return text[:width] if len(text) > width else text


def _mock_color(n, extra=0):
    return n | extra


def _mock_clear_line(screen, y):
    pass


def _make_screen(height=40, width=120):
    screen = MagicMock()
    screen.lines = []
    screen.boxes = []
    screen.getmaxyx.return_value = (height, width)
    return screen


def _sample_agents():
    return {
        "generated_at": "2026-05-13T00:00:00Z",
        "providers": {
            "claude": {"status": "available", "roles": ["planner"]},
            "codex": {"status": "available", "roles": ["executor"]},
            "gemini": {"status": "not_found", "roles": ["reviewer"]},
        },
    }


def _sample_runs():
    return [
        {"run_id": "run-001", "status": "closed", "user_request": "first task"},
        {"run_id": "run-002", "status": "running", "user_request": "second task"},
        {"run_id": "run-003", "status": "pending", "user_request": "third task"},
    ]


def _sample_events():
    return [
        {"ts": "2026-05-13T10:00:00+09:00", "type": "intake_created", "artifact": "task.yaml"},
        {"ts": "2026-05-13T10:01:00+09:00", "type": "route_completed"},
    ]


class ExploreStateTest(unittest.TestCase):
    def test_initial_state(self):
        state = ExploreState()
        self.assertEqual(state.active_pane, "runs")
        self.assertIsNone(state.selected_run_id)
        self.assertIsNone(state.selected_agent_id)

    def test_cycle_pane_forward(self):
        state = ExploreState(active_pane="agents")
        state.cycle_pane(1)
        self.assertEqual(state.active_pane, "runs")
        state.cycle_pane(1)
        self.assertEqual(state.active_pane, "inspect")
        state.cycle_pane(1)
        self.assertEqual(state.active_pane, "events")
        state.cycle_pane(1)
        self.assertEqual(state.active_pane, "agents")

    def test_cycle_pane_backward(self):
        state = ExploreState(active_pane="agents")
        state.cycle_pane(-1)
        self.assertEqual(state.active_pane, "events")

    def test_select_run(self):
        state = ExploreState()
        state.runs_cache = _sample_runs()
        state.selected_run_index = 1
        state.select_run()
        self.assertEqual(state.selected_run_id, "run-002")

    def test_select_agent(self):
        state = ExploreState()
        state.agents_cache = _sample_agents()
        state.selected_agent_index = 0
        state.select_agent()
        self.assertIn(state.selected_agent_id, ["claude", "codex", "gemini"])

    def test_select_run_out_of_range(self):
        state = ExploreState()
        state.runs_cache = []
        state.selected_run_index = 5
        state.select_run()
        self.assertIsNone(state.selected_run_id)


class ExploreNavigationTest(unittest.TestCase):
    def test_tab_cycles_pane(self):
        state = ExploreState(active_pane="runs")
        action = update_explore_navigation(state, ord("\t"))
        self.assertEqual(action, "pane_changed")
        self.assertEqual(state.active_pane, "inspect")

    def test_down_arrow_increments_run_index(self):
        state = ExploreState(active_pane="runs")
        state.runs_cache = _sample_runs()
        state.selected_run_index = 0
        action = update_explore_navigation(state, curses.KEY_DOWN)
        self.assertEqual(action, "scrolled")
        self.assertEqual(state.selected_run_index, 1)

    def test_up_arrow_decrements_run_index(self):
        state = ExploreState(active_pane="runs")
        state.runs_cache = _sample_runs()
        state.selected_run_index = 2
        action = update_explore_navigation(state, curses.KEY_UP)
        self.assertEqual(action, "scrolled")
        self.assertEqual(state.selected_run_index, 1)

    def test_up_arrow_clamps_at_zero(self):
        state = ExploreState(active_pane="runs")
        state.runs_cache = _sample_runs()
        state.selected_run_index = 0
        update_explore_navigation(state, curses.KEY_UP)
        self.assertEqual(state.selected_run_index, 0)

    def test_enter_selects_run(self):
        state = ExploreState(active_pane="runs")
        state.runs_cache = _sample_runs()
        state.selected_run_index = 1
        action = update_explore_navigation(state, 10)
        self.assertEqual(action, "run_selected")
        self.assertEqual(state.selected_run_id, "run-002")

    def test_enter_selects_agent(self):
        state = ExploreState(active_pane="agents")
        state.agents_cache = _sample_agents()
        state.selected_agent_index = 0
        action = update_explore_navigation(state, 10)
        self.assertEqual(action, "agent_selected")
        self.assertIsNotNone(state.selected_agent_id)

    def test_scroll_inspect_pane(self):
        state = ExploreState(active_pane="inspect")
        action = update_explore_navigation(state, curses.KEY_DOWN)
        self.assertEqual(action, "scrolled")
        self.assertEqual(state.scroll_offsets["inspect"], 1)

    def test_j_k_navigation(self):
        state = ExploreState(active_pane="events")
        update_explore_navigation(state, ord("j"))
        self.assertEqual(state.scroll_offsets["events"], 1)
        update_explore_navigation(state, ord("k"))
        self.assertEqual(state.scroll_offsets["events"], 0)

    def test_unhandled_key_returns_none(self):
        state = ExploreState()
        action = update_explore_navigation(state, ord("z"))
        self.assertIsNone(action)


class ExplorePaneRenderTest(unittest.TestCase):
    def test_agents_pane_renders_providers(self):
        screen = _make_screen()
        state = ExploreState(active_pane="agents")
        state.agents_cache = _sample_agents()
        _draw_agents_pane(screen, 2, 2, 10, 30, state, _mock_add_line, _mock_truncate, _mock_color)
        texts = [line[2] for line in screen.lines]
        self.assertTrue(any("claude" in t for t in texts))
        self.assertTrue(any("codex" in t for t in texts))
        self.assertTrue(any("gemini" in t for t in texts))

    def test_runs_pane_renders_run_list(self):
        screen = _make_screen()
        state = ExploreState(active_pane="runs")
        state.runs_cache = _sample_runs()
        state.selected_run_id = "run-001"
        _draw_runs_pane(screen, 2, 2, 10, 40, state, _mock_add_line, _mock_truncate, _mock_color)
        texts = [line[2] for line in screen.lines]
        self.assertTrue(any("run-001" in t for t in texts))
        self.assertTrue(any("run-002" in t for t in texts))

    def test_inspect_pane_renders_lines(self):
        screen = _make_screen()
        state = ExploreState()
        state.inspect_lines = ["Hive Inspect  Run test-001", "Verdict: CLEAN", "Task: do stuff"]
        _draw_inspect_pane(screen, 2, 2, 10, 50, state, _mock_add_line, _mock_truncate, _mock_color)
        texts = [line[2] for line in screen.lines]
        self.assertTrue(any("Hive Inspect" in t for t in texts))

    def test_inspect_pane_shows_ask_result(self):
        screen = _make_screen()
        state = ExploreState()
        state.inspect_lines = ["Hive Inspect  Run test-001"]
        state.last_ask_result = "society plan -> run-999 (3 members)"
        _draw_inspect_pane(screen, 2, 2, 10, 60, state, _mock_add_line, _mock_truncate, _mock_color)
        texts = [line[2] for line in screen.lines]
        self.assertTrue(any("Ask Result" in t for t in texts))

    def test_events_pane_renders_events(self):
        screen = _make_screen()
        state = ExploreState()
        state.events_cache = _sample_events()
        _draw_events_pane(screen, 2, 2, 5, 60, state, _mock_add_line, _mock_truncate, _mock_color)
        texts = [line[2] for line in screen.lines]
        self.assertTrue(any("intake_created" in t for t in texts))

    def test_empty_state_renders_without_crash(self):
        screen = _make_screen()
        state = ExploreState()
        _draw_agents_pane(screen, 2, 2, 10, 30, state, _mock_add_line, _mock_truncate, _mock_color)
        _draw_runs_pane(screen, 2, 2, 10, 30, state, _mock_add_line, _mock_truncate, _mock_color)
        _draw_inspect_pane(screen, 2, 2, 10, 30, state, _mock_add_line, _mock_truncate, _mock_color)
        _draw_events_pane(screen, 2, 2, 5, 30, state, _mock_add_line, _mock_truncate, _mock_color)

    def test_full_explore_view_renders(self):
        screen = _make_screen(height=40, width=120)
        state = ExploreState()
        state.agents_cache = _sample_agents()
        state.runs_cache = _sample_runs()
        state.selected_run_id = "run-001"
        state.inspect_lines = ["Hive Inspect  Run run-001", "Verdict: CLEAN"]
        state.events_cache = _sample_events()
        draw_explore_view(
            screen, 40, 120, Path("/tmp/fake"),
            state, _mock_add_line, _mock_draw_box, _mock_truncate, _mock_color, _mock_clear_line,
        )
        self.assertTrue(len(screen.boxes) >= 4, "expected 4 pane boxes")
        box_titles = [b[4] for b in screen.boxes]
        self.assertTrue(any("Agents" in t for t in box_titles))
        self.assertTrue(any("Runs" in t for t in box_titles))
        self.assertTrue(any("Inspect" in t for t in box_titles))
        self.assertTrue(any("Events" in t for t in box_titles))

    def test_small_terminal_shows_message(self):
        screen = _make_screen(height=8, width=40)
        state = ExploreState()
        draw_explore_view(
            screen, 8, 40, Path("/tmp/fake"),
            state, _mock_add_line, _mock_draw_box, _mock_truncate, _mock_color, _mock_clear_line,
        )
        texts = [line[2] for line in screen.lines]
        self.assertTrue(any("too small" in t.lower() for t in texts))


class SharedStateTest(unittest.TestCase):
    def test_run_selection_propagates_to_inspect(self):
        state = ExploreState(active_pane="runs")
        state.runs_cache = _sample_runs()
        state.selected_run_index = 2
        update_explore_navigation(state, 10)
        self.assertEqual(state.selected_run_id, "run-003")
        screen = _make_screen()
        state.inspect_lines = [f"Run: {state.selected_run_id}"]
        _draw_inspect_pane(screen, 0, 0, 5, 40, state, _mock_add_line, _mock_truncate, _mock_color)
        texts = [line[2] for line in screen.lines]
        self.assertTrue(any("run-003" in t for t in texts))

    def test_agent_selection_updates_state(self):
        state = ExploreState(active_pane="agents")
        state.agents_cache = _sample_agents()
        state.selected_agent_index = 1
        update_explore_navigation(state, 10)
        self.assertIsNotNone(state.selected_agent_id)

    @patch("hivemind.tui_explore.read_events")
    @patch("hivemind.tui_explore.load_run")
    @patch("hivemind.tui_explore.format_inspect_report")
    @patch("hivemind.tui_explore.build_inspect_report")
    @patch("hivemind.tui_explore.detect_agents")
    @patch("hivemind.tui_explore.list_runs")
    def test_refresh_uses_selected_run_for_inspect_and_events(
        self,
        list_runs_mock,
        detect_agents_mock,
        build_inspect_mock,
        format_inspect_mock,
        load_run_mock,
        read_events_mock,
    ):
        state = ExploreState(selected_run_id="run-002")
        list_runs_mock.return_value = _sample_runs()
        detect_agents_mock.return_value = _sample_agents()
        build_inspect_mock.return_value = {"run_id": "run-002"}
        format_inspect_mock.return_value = "Hive Inspect  Run run-002"
        load_run_mock.return_value = (MagicMock(), {})
        read_events_mock.return_value = _sample_events()

        refresh_explore_data(Path("/tmp/fake"), state, force=True)

        build_inspect_mock.assert_called_once_with(Path("/tmp/fake"), "run-002")
        self.assertEqual(state.inspect_lines, ["Hive Inspect  Run run-002"])
        self.assertEqual(state.events_cache, _sample_events())


class ExploreViewIntegrationTest(unittest.TestCase):
    def test_explore_in_tui_views(self):
        from hivemind.tui import TUI_VIEWS
        self.assertIn("explore", TUI_VIEWS)

    def test_explore_panes_tuple(self):
        self.assertEqual(len(EXPLORE_PANES), 4)
        self.assertIn("agents", EXPLORE_PANES)
        self.assertIn("runs", EXPLORE_PANES)
        self.assertIn("inspect", EXPLORE_PANES)
        self.assertIn("events", EXPLORE_PANES)


if __name__ == "__main__":
    unittest.main()
