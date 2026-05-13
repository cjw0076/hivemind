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


if __name__ == "__main__":
    unittest.main()
