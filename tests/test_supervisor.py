from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.dag_state import StepLease
from hivemind.harness import create_run
from hivemind.plan_dag import build_dag, save_dag
from hivemind.supervisor import (
    active_step_leases,
    format_supervisor_status,
    probe_summaries_from_result,
    run_supervisor,
    supervisor_paths,
    supervisor_result_is_waiting,
    supervisor_status_report,
    tail_supervisor_log,
)
from hivemind.workloop import read_execution_ledger


class SupervisorTest(unittest.TestCase):
    def test_run_supervisor_advances_round_and_writes_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervise one round")

            report = run_supervisor(root, paths.run_id, max_rounds=1, execute=False)

            state_path = supervisor_paths(root, paths.run_id)["state"]
            log_path = supervisor_paths(root, paths.run_id)["log"]
            self.assertTrue(state_path.exists())
            self.assertTrue(log_path.exists())
            self.assertEqual(report["run_id"], paths.run_id)
            self.assertIn(report["status"], {"waiting", "max_rounds_reached", "completed"})
            records = read_execution_ledger(root, paths.run_id)
            events = [record.get("event") for record in records]
            self.assertIn("supervisor_started", events)
            self.assertIn("supervisor_stopped", events)

    def test_status_reports_active_leases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor lease status")
            lease = StepLease.acquire(root, paths.run_id, "planner", ttl=60)
            try:
                leases = active_step_leases(root, paths.run_id)
                report = supervisor_status_report(root, paths.run_id)
                self.assertEqual(leases[0]["step_id"], "planner")
                self.assertEqual(report["active_leases"][0]["step_id"], "planner")
            finally:
                lease.release()

    def test_pingpong_scheduler_runs_one_parallel_step_per_round(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "serialized l0 scheduler")
            dag = build_dag(paths.run_id, "serialized l0 scheduler", "implementation")
            save_dag(root, dag)

            report = run_supervisor(root, paths.run_id, max_rounds=1, execute=False, scheduler="pingpong")
            records = read_execution_ledger(root, paths.run_id)
            completed_rounds = [record for record in records if record.get("event") == "scheduler_round_completed"]

            self.assertEqual(report["scheduler"], "pingpong")
            self.assertEqual(report["kernel_level"], "L0")
            self.assertIn("pingpong", report["command"])
            self.assertEqual(len(completed_rounds), 1)
            self.assertEqual(completed_rounds[0]["extra"]["scheduler"], "pingpong")
            self.assertEqual(completed_rounds[0]["extra"]["kernel_level"], "L0")
            self.assertEqual(len(completed_rounds[0]["extra"]["dispatched"]), 1)
            self.assertIn(completed_rounds[0]["extra"]["dispatched"][0], {"context", "diff_review"})

    def test_tail_supervisor_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor tail")
            run_supervisor(root, paths.run_id, max_rounds=1, execute=False)

            report = tail_supervisor_log(root, paths.run_id, lines=2)

            self.assertEqual(report["run_id"], paths.run_id)
            self.assertLessEqual(len(report["lines"]), 2)
            self.assertTrue(any("supervisor" in line for line in report["lines"]))

    def test_cli_run_start_status_tail_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "cli supervisor", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            started = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root,
                    "run",
                    "start",
                    "--run-id",
                    run_id,
                    "--max-rounds",
                    "1",
                    "--scheduler",
                    "pingpong",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            status = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "status", "--run-id", run_id, "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            tail = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "tail", "--run-id", run_id, "--json"],
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertEqual(json.loads(started.stdout)["run_id"], run_id)
            self.assertEqual(json.loads(started.stdout)["scheduler"], "pingpong")
            self.assertEqual(json.loads(status.stdout)["run_id"], run_id)
            self.assertTrue(json.loads(tail.stdout)["lines"])

    def test_probe_summary_from_last_round_is_reported(self) -> None:
        result = {
            "results": {
                "verify": {
                    "status": "failed",
                    "probe_action": "block",
                    "probe_confidence": 0.25,
                    "probe_passed": False,
                    "probe_evidence": "exit_code=1",
                }
            }
        }

        probes = probe_summaries_from_result(result)
        rendered = format_supervisor_status(
            {
                "run_id": "run_test",
                "status": "blocked",
                "rounds": 1,
                "max_rounds": 1,
                "execute": False,
                "replay": {"ok": True, "hash_chain_ok": True, "seq_ok": True, "issue_count": 0},
                "active_leases": [],
                "last_result": result,
                "last_probes": probes,
            }
        )

        self.assertEqual(probes[0]["action"], "block")
        self.assertIn("Probe:", rendered)
        self.assertIn("verify action=block confidence=0.25 status=failed passed=False", rendered)

    def test_override_pending_probe_keeps_supervisor_waiting(self) -> None:
        result = {"results": {"review_gate": {"status": "failed", "probe_action": "override_pending"}}}

        self.assertTrue(supervisor_result_is_waiting(result))


if __name__ == "__main__":
    unittest.main()
