import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import load_run
from hivemind.quickstart import quickstart_demo


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


if __name__ == "__main__":
    unittest.main()
