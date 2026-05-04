import curses
import queue
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import create_run, read_control_lock, release_control_lock
from hivemind.plan_dag import build_dag
from hivemind.protocol import build_execution_intent, check_intent, decide_intent, save_intent
from hivemind.workloop import append_execution_ledger
from hivemind.tui import (
    ComposerState,
    build_probe_authority_rows,
    build_ledger_view_rows,
    build_protocol_authority_rows,
    handle_tui_command,
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

    def test_demo_command_creates_visible_demo_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = handle_tui_command(root, None, "/demo 0")
            self.assertIn("demo ->", result)
            self.assertIn("status=demo_complete", result)

    def test_function_keys_switch_views(self) -> None:
        self.assertEqual(view_for_key(key_f(1)), "board")
        self.assertEqual(view_for_key(key_f(8)), "diff")
        self.assertEqual(view_for_key(key_f(9)), "ledger")
        self.assertIsNone(view_for_key(ord("1")))

    def test_ledger_view_command(self) -> None:
        self.assertEqual(handle_local_composer_command("/ledger"), {"action": "view", "view": "ledger"})
        self.assertEqual(handle_local_composer_command("/view 9"), {"action": "view", "view": "ledger"})

    def test_protocol_authority_rows_show_active_gate(self) -> None:
        replay = {
            "ok": False,
            "hash_chain_ok": True,
            "seq_ok": True,
            "record_count": 4,
            "issues": [{"type": "missing_artifact"}],
            "authority": {
                "intents": {
                    "intent_1": {
                        "intent_id": "intent_1",
                        "step_id": "planner",
                        "authority_class": "provider_bypass",
                        "risk_level": "medium",
                    }
                },
                "decisions": {
                    "intent_1": {
                        "decision": "needs_vote",
                        "missing_voters": ["verifier"],
                    }
                },
                "votes": {"intent_1": {"policy-gate": "approve_with_conditions"}},
                "proofs": {},
            },
        }

        rows = build_protocol_authority_rows(replay)
        text = "\n".join(rows)

        self.assertIn("Authority", rows[0])
        self.assertIn("Active Intent: intent_1", text)
        self.assertIn("missing=verifier", text)
        self.assertIn("policy-gate=approve_with_conditions", text)
        self.assertIn("Replay Issues: missing_artifact", text)

    def test_probe_authority_rows_show_latest_probe_gate(self) -> None:
        replay = {
            "steps": {
                "context": {"probe": {"step_id": "context", "action": "accept", "confidence": 0.9, "criteria_count": 1, "status": "completed", "seq": 1}},
                "verify": {"probe": {"step_id": "verify", "action": "block", "confidence": 0.25, "criteria_count": 2, "status": "failed", "seq": 2}},
            }
        }

        rows = build_probe_authority_rows(replay)
        text = "\n".join(rows)

        self.assertIn("Probe: verify", text)
        self.assertIn("action=block", text)
        self.assertIn("confidence=0.25", text)
        self.assertIn("criteria=2", text)

    def test_ledger_view_rows_include_protocol_panel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "tui protocol panel")
            dag = build_dag(paths.run_id, "tui protocol panel", "implementation")
            intent = build_execution_intent(root, dag, "planner", execute=True)
            save_intent(root, intent)
            check_intent(root, paths.run_id, intent.intent_id)
            decide_intent(root, paths.run_id, intent.intent_id)

            rows = build_ledger_view_rows(root, paths, 20)
            text = "\n".join(rows)

            self.assertIn("Authority", text)
            self.assertIn("Active Intent:", text)
            self.assertIn("Decision:", text)
            self.assertIn("Recent Ledger", text)
            self.assertIn("intent_proposed", text)

    def test_ledger_view_rows_include_probe_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "tui probe panel")
            append_execution_ledger(
                root,
                paths.run_id,
                "step_failed",
                actor="harness",
                step_id="verify",
                status="failed",
                extra={"probe_action": "block", "probe_confidence": 0.25, "criteria_count": 2},
            )

            rows = build_ledger_view_rows(root, paths, 20)
            text = "\n".join(rows)

            self.assertIn("Probe: verify", text)
            self.assertIn("action=block", text)
            self.assertIn("probe=block conf=0.25 criteria=2", text)

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
