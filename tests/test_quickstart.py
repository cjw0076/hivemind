import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import load_run
from hivemind.quickstart import memory_loop_demo, quickstart_demo


class QuickstartDemoTest(unittest.TestCase):
    def test_quickstart_demo_creates_public_alpha_value_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = quickstart_demo(root, delay=0)

            self.assertEqual(report["kind"], "hive_quickstart_demo")
            self.assertEqual(report["status"], "ready")
            self.assertEqual(report["inspect_summary"]["verdict"], "clean")
            self.assertGreaterEqual(report["inspect_summary"]["ledger_records"], 1)
            self.assertGreaterEqual(report["memoryos_summary"]["nodes"], 1)
            self.assertTrue(report["memoryos_summary"]["paths_hidden"])
            paths, _state = load_run(root, report["run_id"])
            self.assertTrue((paths.artifacts / "quickstart_report.json").exists())
            self.assertTrue((paths.run_dir / "memory_drafts.json").exists())

    def test_cli_demo_quickstart_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root,
                    "demo",
                    "quickstart",
                    "한글 quickstart",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["kind"], "hive_quickstart_demo")
            self.assertEqual(payload["task"], "한글 quickstart")
            self.assertIn("hive inspect", payload["commands"][0])

    def test_memory_loop_demo_closes_isolated_feedback_loop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = memory_loop_demo(root, delay=0)

            self.assertEqual(report["kind"], "hive_memory_loop_demo")
            self.assertEqual(report["status"], "closed_loop")
            self.assertTrue(report["approved_memory_ids"])
            self.assertEqual(
                report["second_run_context"]["accepted_memory_ids"],
                report["approved_memory_ids"],
            )
            first_paths, _state = load_run(root, report["first_run_id"])
            self.assertTrue((first_paths.artifacts / "memory_loop_report.json").exists())

    def test_cli_demo_memory_loop_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root,
                    "demo",
                    "memory-loop",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["kind"], "hive_memory_loop_demo")
            self.assertEqual(payload["status"], "closed_loop")
            self.assertTrue(payload["second_run_context"]["accepted_memory_ids"])


if __name__ == "__main__":
    unittest.main()
