from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from hivemind.harness import create_run, provider_passthrough
from hivemind.run_validation import validate_run_artifacts
from hivemind.workloop import read_execution_ledger


class ProviderPassthroughTest(unittest.TestCase):
    def test_dry_run_records_native_command_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider passthrough dry run")

            result_path = provider_passthrough(
                root,
                "codex",
                ["exec", "--cd", ".", "--sandbox", "read-only", "inspect"],
                run_id=paths.run_id,
                execute=False,
            )

            data = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "prepared")
            self.assertEqual(data["provider_mode"], "native_passthrough")
            self.assertEqual(data["permission_mode"], "read_only")
            command = (root / data["command_path"]).read_text(encoding="utf-8")
            self.assertIn("exec", command)
            self.assertIn("--sandbox", command)
            report = validate_run_artifacts(paths.run_dir, root)
            self.assertTrue(report["checks"]["events_schema_valid"])
            self.assertTrue(report["checks"]["provider_results_schema_valid"])
            events = [record.get("event") for record in read_execution_ledger(root, paths.run_id)]
            self.assertIn("intent_proposed", events)
            self.assertIn("execution_proof_created", events)

    def test_dangerous_native_flag_is_blocked_with_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider passthrough danger")

            result_path = provider_passthrough(
                root,
                "claude",
                ["--dangerously-skip-permissions", "--output-format", "text"],
                run_id=paths.run_id,
                execute=True,
            )

            data = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "failed")
            self.assertEqual(data["provider_mode"], "policy_blocked")
            self.assertIn("--dangerously-skip-permissions", data["reason"])
            events = [record.get("event") for record in read_execution_ledger(root, paths.run_id)]
            self.assertIn("policy_blocked", events)
            self.assertIn("execution_proof_created", events)

    def test_safe_read_only_execute_runs_and_captures_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider passthrough execute")
            completed = subprocess.CompletedProcess(
                args=["codex", "exec"],
                returncode=0,
                stdout="native output\n",
                stderr="",
            )
            with patch("hivemind.harness.resolve_provider_binary", return_value="codex"):
                with patch("hivemind.provider_passthrough.subprocess.run", return_value=completed) as run:
                    result_path = provider_passthrough(
                        root,
                        "codex",
                        ["exec", "--cd", ".", "--sandbox", "read-only", "inspect"],
                        run_id=paths.run_id,
                        execute=True,
                    )

            data = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "completed")
            self.assertEqual(data["returncode"], 0)
            self.assertEqual((root / data["stdout_path"]).read_text(encoding="utf-8"), "native output\n")
            self.assertEqual(run.call_args.kwargs["cwd"], root)

    def test_execute_timeout_writes_timeout_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider passthrough timeout")
            timeout = subprocess.TimeoutExpired(cmd=["codex", "exec"], timeout=1, output="partial out", stderr="partial err")
            with patch("hivemind.harness.resolve_provider_binary", return_value="codex"):
                with patch("hivemind.provider_passthrough.subprocess.run", side_effect=timeout):
                    result_path = provider_passthrough(
                        root,
                        "codex",
                        ["exec", "--cd", ".", "--sandbox", "read-only", "inspect"],
                        run_id=paths.run_id,
                        execute=True,
                        timeout=1,
                    )

            data = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "timeout")
            self.assertEqual(data["returncode"], 124)
            self.assertIn("timed out", data["reason"])
            self.assertIn("partial out", (root / data["stdout_path"]).read_text(encoding="utf-8"))
            self.assertIn("partial err", (root / data["stderr_path"]).read_text(encoding="utf-8"))
            report = validate_run_artifacts(paths.run_dir, root)
            self.assertTrue(report["checks"]["provider_results_schema_valid"], report["issues"])
            records = read_execution_ledger(root, paths.run_id)
            self.assertTrue(any(record.get("event") == "execution_proof_created" and record.get("status") == "timeout" for record in records))

    def test_execute_blocks_native_command_outside_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider passthrough allowlist")

            result_path = provider_passthrough(
                root,
                "codex",
                ["exec", "--cd", ".", "--sandbox", "workspace-write", "inspect"],
                run_id=paths.run_id,
                execute=True,
            )

            data = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "failed")
            self.assertEqual(data["provider_mode"], "policy_blocked")
            self.assertIn("outside Codex allowlist", data["reason"])
            events = [record.get("event") for record in read_execution_ledger(root, paths.run_id)]
            self.assertIn("policy_blocked", events)

    def test_execute_blocks_destructive_shell_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider passthrough shell danger")

            result_path = provider_passthrough(
                root,
                "codex",
                ["bash", "-c", "rm -rf .runs"],
                run_id=paths.run_id,
                execute=True,
            )

            data = yaml.safe_load(result_path.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "failed")
            self.assertEqual(data["provider_mode"], "policy_blocked")
            self.assertIn("destructive shell wrapper", data["reason"])
            events = [record.get("event") for record in read_execution_ledger(root, paths.run_id)]
            self.assertIn("policy_blocked", events)

    def test_cli_provider_dry_run_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "provider cli smoke", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root,
                    "provider",
                    "gemini",
                    "--run-id",
                    run_id,
                    "--dry-run",
                    "--json",
                    "--",
                    "-p",
                    "hello",
                    "--approval-mode",
                    "plan",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            data = json.loads(completed.stdout)
            self.assertEqual(data["provider"], "gemini")
            self.assertEqual(data["role"], "native")
            self.assertEqual(data["status"], "prepared")
            self.assertIn("result_path", data)


if __name__ == "__main__":
    unittest.main()
