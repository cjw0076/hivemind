from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from hivemind.harness import create_run
from hivemind.provider_loop import (
    classify_provider_failure,
    prepare_provider_loop,
    provider_loop_status,
    stop_provider_loop,
    tick_provider_loop,
    verify_provider_fallback,
)


class ProviderLoopTest(unittest.TestCase):
    def test_prepare_records_codex_as_one_shot_tick_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            worker = prepare_provider_loop(root, "codex", "inspect status")

            self.assertEqual(worker["schema_version"], "hive.provider_loop.v1")
            self.assertEqual(worker["provider"], "codex")
            self.assertEqual(worker["loop_mode"], "one_shot_tick")
            self.assertEqual(worker["status"], "prepared")
            self.assertTrue((root / worker["path"]).exists())

    def test_prepare_records_claude_as_monitor_plan_not_required_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            worker = prepare_provider_loop(root, "claude", "monitor this")
            status = provider_loop_status(root)

            self.assertEqual(worker["loop_mode"], "monitor_plan")
            self.assertEqual(status["workers"][0]["provider"], "claude")
            self.assertEqual(status["workers"][0]["status"], "prepared")

    def test_tick_codex_uses_existing_provider_passthrough_prepare_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker = prepare_provider_loop(root, "codex", "inspect status")

            result = tick_provider_loop(root, worker_id=worker["worker_id"])

            self.assertTrue(result["tick_executed"])
            self.assertEqual(result["worker"]["tick_count"], 1)
            self.assertEqual(result["worker"]["last_status"], "prepared")
            receipt = yaml.safe_load((root / result["worker"]["last_result_path"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["provider"], "codex")
            self.assertEqual(receipt["provider_mode"], "native_passthrough")
            self.assertFalse(receipt["execute"])

    def test_local_worker_tick_shares_status_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker = prepare_provider_loop(root, "local", "summarize context")

            result = tick_provider_loop(root, worker_id=worker["worker_id"])
            status = provider_loop_status(root)

            self.assertEqual(result["status"], "prepared")
            self.assertEqual(status["workers"][0]["provider"], "local")
            self.assertEqual(status["workers"][0]["loop_mode"], "local_worker_tick")
            self.assertTrue((root / result["worker"]["last_result_path"]).exists())

    def test_prepare_records_gemini_as_one_shot_tick_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            worker = prepare_provider_loop(root, "gemini", "review status")
            result = tick_provider_loop(root, worker_id=worker["worker_id"])

            self.assertEqual(worker["provider"], "gemini")
            self.assertEqual(worker["loop_mode"], "one_shot_tick")
            self.assertEqual(result["worker"]["last_status"], "prepared")
            receipt = yaml.safe_load((root / result["worker"]["last_result_path"]).read_text(encoding="utf-8"))
            self.assertEqual(receipt["provider"], "gemini")
            self.assertEqual(receipt["provider_mode"], "native_passthrough")

    def test_stop_writes_stop_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker = prepare_provider_loop(root, "codex", "inspect")

            stopped = stop_provider_loop(root, worker_id=worker["worker_id"])

            self.assertEqual(stopped["status"], "stopped")
            self.assertTrue((root / stopped["receipt"]).exists())
            self.assertEqual(provider_loop_status(root)["workers"][0]["status"], "stopped")

    def test_execute_failure_is_returned_as_degraded_fallback_next_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker = prepare_provider_loop(root, "codex", "inspect")
            completed = subprocess.CompletedProcess(args=["codex"], returncode=7, stdout="", stderr="denied")
            with patch("hivemind.harness.resolve_provider_binary", return_value="codex"):
                with patch("hivemind.provider_passthrough.subprocess.run", return_value=completed):
                    result = tick_provider_loop(root, worker_id=worker["worker_id"], execute=True)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["worker"]["status"], "degraded")
            self.assertEqual(result["worker"]["next_action"], "fallback")
            self.assertEqual(result["worker"]["failure_category"], "unknown_provider_failure")
            self.assertIn("claude", result["worker"]["fallback_candidates"])
            self.assertEqual(result["worker"]["role_capsule"]["provider"], "codex")

    def test_policy_blocked_failure_is_classified_for_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker = prepare_provider_loop(root, "claude", "inspect")

            result = tick_provider_loop(root, worker_id=worker["worker_id"], execute=True)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["worker"]["status"], "degraded")
            self.assertEqual(result["worker"]["failure_category"], "policy_blocked")
            self.assertEqual(result["worker"]["next_action"], "fallback")
            self.assertIn("codex", result["worker"]["fallback_candidates"])
            self.assertIn("gemini", result["worker"]["fallback_candidates"])

    def test_rate_limit_text_is_classified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stderr = root / "stderr.txt"
            stderr.write_text("429 rate limit exceeded", encoding="utf-8")

            category = classify_provider_failure(
                {
                    "status": "failed",
                    "provider_mode": "native_passthrough",
                    "stderr_path": "stderr.txt",
                },
                root,
            )

            self.assertEqual(category, "rate_limit")

    def test_verify_fallback_promotes_completed_non_local_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = prepare_provider_loop(root, "codex", "implement bounded task")
            completed = subprocess.CompletedProcess(args=["codex"], returncode=7, stdout="", stderr="access denied")
            with patch("hivemind.harness.resolve_provider_binary", return_value="codex"):
                with patch("hivemind.provider_passthrough.subprocess.run", return_value=completed):
                    tick_provider_loop(root, worker_id=original["worker_id"], execute=True)
            fallback = prepare_provider_loop(root, "gemini", "implement bounded task", run_id=original["run_id"])
            self._mark_worker_completed(root, fallback["path"], "completed")

            receipt = verify_provider_fallback(
                root,
                original_worker_id=original["worker_id"],
                fallback_worker_id=fallback["worker_id"],
                run_id=original["run_id"],
            )

            self.assertEqual(receipt["schema_version"], "hive.provider_fallback_verification.v1")
            self.assertEqual(receipt["status"], "passed")
            self.assertTrue(receipt["promoted"])
            self.assertEqual(receipt["fallback_provider"], "gemini")
            self.assertEqual(receipt["stop_conditions_triggered"], [])
            self.assertTrue((root / receipt["path"]).exists())

    def test_verify_fallback_holds_local_without_independent_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = prepare_provider_loop(root, "codex", "summarize private context")
            completed = subprocess.CompletedProcess(args=["codex"], returncode=7, stdout="", stderr="access denied")
            with patch("hivemind.harness.resolve_provider_binary", return_value="codex"):
                with patch("hivemind.provider_passthrough.subprocess.run", return_value=completed):
                    tick_provider_loop(root, worker_id=original["worker_id"], execute=True)
            fallback = prepare_provider_loop(root, "local", "summarize private context", run_id=original["run_id"])
            self._mark_worker_completed(root, fallback["path"], "done")

            receipt = verify_provider_fallback(
                root,
                original_worker_id=original["worker_id"],
                fallback_worker_id=fallback["worker_id"],
                run_id=original["run_id"],
            )

            self.assertEqual(receipt["status"], "held")
            self.assertFalse(receipt["promoted"])
            self.assertIn("local_fallback_without_independent_verifier", receipt["stop_conditions_triggered"])
            self.assertEqual(receipt["privacy"]["raw_provider_output_read"], False)

    def test_cli_verify_fallback_json_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = prepare_provider_loop(root, "codex", "review fallback")
            completed = subprocess.CompletedProcess(args=["codex"], returncode=7, stdout="", stderr="access denied")
            with patch("hivemind.harness.resolve_provider_binary", return_value="codex"):
                with patch("hivemind.provider_passthrough.subprocess.run", return_value=completed):
                    tick_provider_loop(root, worker_id=original["worker_id"], execute=True)
            fallback = prepare_provider_loop(root, "claude", "review fallback", run_id=original["run_id"])
            self._mark_worker_completed(root, fallback["path"], "completed")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "provider-loop",
                    "verify-fallback",
                    "--run-id",
                    original["run_id"],
                    "--original-worker",
                    original["worker_id"],
                    "--fallback-worker",
                    fallback["worker_id"],
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["schema_version"], "hive.provider_fallback_verification.v1")
            self.assertEqual(payload["status"], "passed")
            self.assertTrue(payload["promoted"])

    def test_cli_prepare_and_status_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "provider-loop",
                    "prepare",
                    "--provider",
                    "codex",
                    "--prompt",
                    "inspect status",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            status = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "provider-loop",
                    "status",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertEqual(json.loads(prepared.stdout)["provider"], "codex")
            self.assertEqual(json.loads(status.stdout)["count"], 1)

    def _mark_worker_completed(self, root: Path, worker_ref: str, last_status: str) -> None:
        path = root / worker_ref
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["status"] = "active"
        payload["last_status"] = last_status
        payload["last_result_path"] = "synthetic/fallback_result.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
