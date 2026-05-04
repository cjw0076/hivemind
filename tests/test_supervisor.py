from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.dag_state import StepLease
from hivemind.harness import create_run
from hivemind.supervisor import (
    active_step_leases,
    run_supervisor,
    supervisor_paths,
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
            self.assertEqual(json.loads(status.stdout)["run_id"], run_id)
            self.assertTrue(json.loads(tail.stdout)["lines"])


if __name__ == "__main__":
    unittest.main()
