import curses
import queue
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import create_run, read_control_lock, release_control_lock
from hivemind.tui import (
    ComposerState,
    handle_local_composer_command,
    key_f,
    normalize_paste_text,
    start_submit_job,
    sync_tui_control_lock,
    update_composer,
    view_for_key,
)


class TuiComposerTest(unittest.TestCase):
    def test_printable_keys_append_to_composer(self) -> None:
        action, state = update_composer(ComposerState(), "w")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("w", 1))

        action, state = update_composer(state, "h")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("wh", 2))

    def test_korean_input_appends_as_prompt_text(self) -> None:
        action, state = update_composer(ComposerState(), "한")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("한", 1))

        action, state = update_composer(state, "글")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("한글", 2))

    def test_enter_submits_non_empty_composer(self) -> None:
        action, state = update_composer(ComposerState("who are in there", 17), 10)
        self.assertEqual(action, "submit")
        self.assertEqual(state.text, "who are in there")

    def test_backspace_and_escape_edit_composer(self) -> None:
        action, state = update_composer(ComposerState("abc", 3), curses.KEY_BACKSPACE)
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("ab", 2))

        action, state = update_composer(ComposerState("abc", 3), 27)
        self.assertEqual(action, "cancel")
        self.assertEqual(state, ComposerState())

    def test_cursor_navigation_and_midline_insert(self) -> None:
        action, state = update_composer(ComposerState("ab", 2), curses.KEY_LEFT)
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("ab", 1))

        action, state = update_composer(state, "X")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("aXb", 2))

    def test_ctrl_editing_commands(self) -> None:
        action, state = update_composer(ComposerState("hello world", 11), "\x17")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("hello ", 6))

        action, state = update_composer(ComposerState("hello world", 5), "\x0b")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("hello", 5))

        action, state = update_composer(ComposerState("hello world", 5), "\x15")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState(" world", 0))

    def test_ctrl_v_pastes_clipboard_text(self) -> None:
        action, state = update_composer(
            ComposerState("ask ", 4),
            "\x16",
            clipboard_reader=lambda: "한글\nprompt",
        )
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("ask 한글 prompt", 13))

    def test_ctrl_d_quits_only_when_empty(self) -> None:
        action, state = update_composer(ComposerState(), "\x04")
        self.assertEqual(action, "quit")
        self.assertEqual(state, ComposerState())

        action, state = update_composer(ComposerState("ab", 1), "\x04")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("a", 1))

    def test_printable_q_and_digits_are_prompt_text(self) -> None:
        action, state = update_composer(ComposerState(), "q")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("q", 1))

        action, state = update_composer(ComposerState(), "1")
        self.assertEqual(action, "editing")
        self.assertEqual(state, ComposerState("1", 1))

    def test_local_view_and_quit_commands(self) -> None:
        self.assertEqual(handle_local_composer_command("/view agents"), {"action": "view", "view": "agents"})
        self.assertEqual(handle_local_composer_command("/view 3"), {"action": "view", "view": "transcript"})
        self.assertEqual(handle_local_composer_command("/quit"), {"action": "quit"})

    def test_function_keys_switch_views(self) -> None:
        self.assertEqual(view_for_key(key_f(1)), "board")
        self.assertEqual(view_for_key(key_f(8)), "diff")
        self.assertIsNone(view_for_key(ord("1")))

    def test_paste_normalization_flattens_multiline_text(self) -> None:
        self.assertEqual(normalize_paste_text("a\nb\r\nc"), "a b c")

    def test_start_submit_job_returns_immediately_for_background_work(self) -> None:
        results: queue.Queue[str] = queue.Queue()
        start_submit_job(root=Path("."), run_id=None, prompt="", control=True, results=results)
        self.assertEqual(results.get(timeout=1), "empty prompt")

    def test_control_lock_moves_when_tui_follows_current_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = create_run(root, "first")
            lock_run_id, session_id = sync_tui_control_lock(root, first.run_id, None, None)
            self.assertEqual(lock_run_id, first.run_id)
            self.assertIsNotNone(read_control_lock(first))

            second = create_run(root, "second")
            lock_run_id, session_id = sync_tui_control_lock(root, second.run_id, lock_run_id, session_id)
            self.assertEqual(lock_run_id, second.run_id)
            self.assertIsNone(read_control_lock(first))
            self.assertIsNotNone(read_control_lock(second))
            release_control_lock(root, lock_run_id, session_id)


if __name__ == "__main__":
    unittest.main()
