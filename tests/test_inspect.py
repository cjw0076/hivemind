from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from unittest.mock import patch

from hivemind.harness import create_run, invoke_local, provider_passthrough
from hivemind.inspect_run import (
    build_inspect_report,
    compute_verdict,
    format_inspect_report,
    summarize_disagreements,
)


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

    def test_inspect_collects_local_worker_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "inspect local worker")
            worker_output = {
                "runtime": "ollama",
                "model": "deepseek-coder:6.7b",
                "raw": '{"changed": [], "verification": [], "unresolved": [], "memory_update_candidates": [], "needs_followup": false}',
                "parsed": {
                    "changed": [],
                    "verification": [],
                    "unresolved": [],
                    "memory_update_candidates": [],
                    "needs_followup": False,
                },
            }

            with patch("hivemind.harness.run_worker", return_value=worker_output):
                invoke_local(root, "summarize", run_id=paths.run_id)

            report = build_inspect_report(root, paths.run_id)

            self.assertEqual(len(report["local_worker_results"]), 1)
            local = report["local_worker_results"][0]
            self.assertEqual(local["agent"], "local")
            self.assertEqual(local["role"], "summarize")
            self.assertEqual(local["status"], "completed")
            self.assertEqual(local["worker"], "log_summarizer")
            self.assertFalse(local["should_escalate"])

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

    def test_verdict_clean_on_empty_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "verdict clean smoke")
            report = build_inspect_report(root, paths.run_id)
            self.assertEqual(report["verdict"], "clean")
            self.assertIn("verdict", report)

    def test_verdict_escalated_when_high_severity_disagreement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "verdict escalated smoke")
            dis_path = paths.run_dir / "disagreements.json"
            dis_path.write_text(
                json.dumps([
                    {
                        "ts": "2026-05-11T00:00:00Z",
                        "run_id": paths.run_id,
                        "step_id": "step_a",
                        "topology_type": "split",
                        "severity": "high",
                        "axes": ["conclusion", "risk_assessment"],
                        "dominant_axis": "conclusion",
                        "disagreement_count": 2,
                        "disagreement_targets": ["step_b"],
                        "topology_recommended_action": "escalate",
                    }
                ]),
                encoding="utf-8",
            )
            report = build_inspect_report(root, paths.run_id)
            self.assertEqual(report["verdict"], "escalated")
            self.assertEqual(report["disagreements"]["count"], 1)
            self.assertEqual(report["disagreements"]["high_severity_count"], 1)
            self.assertEqual(report["disagreements"]["records"][0]["step_id"], "step_a")

    def test_verdict_clean_when_low_severity_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "verdict low severity")
            dis_path = paths.run_dir / "disagreements.json"
            dis_path.write_text(
                json.dumps([
                    {
                        "ts": "2026-05-11T00:00:00Z",
                        "run_id": paths.run_id,
                        "step_id": "step_x",
                        "topology_type": "isolated",
                        "severity": "low",
                        "axes": ["approach"],
                        "dominant_axis": "approach",
                        "disagreement_count": 1,
                        "disagreement_targets": [],
                        "topology_recommended_action": "accept",
                    }
                ]),
                encoding="utf-8",
            )
            report = build_inspect_report(root, paths.run_id)
            self.assertEqual(report["verdict"], "clean")
            self.assertEqual(report["disagreements"]["count"], 1)
            self.assertEqual(report["disagreements"]["high_severity_count"], 0)

    def test_compute_verdict_chain_tampered_priority(self) -> None:
        ledger = {"ok": False, "hash_chain_ok": False, "record_count": 5}
        verdict = compute_verdict(ledger, {"failed_count": 0}, [], [], {"count": 1, "high_severity_count": 1})
        self.assertEqual(verdict, "chain_tampered")

    def test_compute_verdict_failures_beats_escalated(self) -> None:
        ledger = {"ok": True, "hash_chain_ok": True}
        provider_results = [{"status": "failed"}]
        verdict = compute_verdict(ledger, {"failed_count": 0}, provider_results, [], {"count": 1, "high_severity_count": 1})
        self.assertEqual(verdict, "failures")

    def test_summarize_disagreements_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run_test"
            run_dir.mkdir()
            result = summarize_disagreements(run_dir, show_paths=False)
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["high_severity_count"], 0)
            self.assertEqual(result["records"], [])

    def test_format_inspect_shows_verdict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "format verdict smoke")
            report = build_inspect_report(root, paths.run_id)
            text = format_inspect_report(report)
            self.assertIn("Verdict:", text)
            self.assertIn("CLEAN", text)
            self.assertIn("Disagreements", text)

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
