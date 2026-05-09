from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import create_run, provider_passthrough
from hivemind.inspect_run import build_inspect_report, format_inspect_report


class InspectRunTest(unittest.TestCase):
    def test_inspect_collects_ledger_provider_receipts_and_memory_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "inspect run smoke")
            artifacts = paths.run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "memory_context.json").write_text(
                json.dumps(
                    {
                        "status": "available",
                        "trace_id": "rtrace_test",
                        "selected_memory_ids": ["mem_a", "mem_b"],
                    }
                ),
                encoding="utf-8",
            )
            provider_passthrough(
                root,
                "gemini",
                ["-p", "hello", "--approval-mode", "plan"],
                run_id=paths.run_id,
                execute=False,
            )

            report = build_inspect_report(root, paths.run_id)

            self.assertEqual(report["kind"], "hive_run_inspection")
            self.assertEqual(report["run_id"], paths.run_id)
            self.assertFalse(report["ledger"]["ok"] is None)
            self.assertGreaterEqual(report["ledger"]["record_count"], 1)
            self.assertEqual(report["memoryos_context"]["trace_id"], "rtrace_test")
            self.assertEqual(report["memoryos_context"]["selected_memory_count"], 2)
            self.assertTrue(any(item["provider_mode"] == "native_passthrough" for item in report["provider_results"]))
            self.assertTrue(report["paths_hidden"])
            self.assertNotIn("path", report["provider_results"][0])

    def test_format_inspect_report_is_operator_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "inspect text smoke")
            report = build_inspect_report(root, paths.run_id)

            text = format_inspect_report(report)

            self.assertIn("Hive Inspect", text)
            self.assertIn("Ledger", text)
            self.assertIn("Provider Results", text)
            self.assertIn("MemoryOS Context", text)
            self.assertIn("Recommendations", text)

    def test_cli_inspect_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "inspect cli smoke", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            inspected = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "inspect", run_id, "--json"],
                text=True,
                capture_output=True,
                check=True,
            )

            data = json.loads(inspected.stdout)
            self.assertEqual(data["run_id"], run_id)
            self.assertEqual(data["kind"], "hive_run_inspection")
            self.assertIn("ledger", data)
            self.assertIn("recommendations", data)


if __name__ == "__main__":
    unittest.main()
