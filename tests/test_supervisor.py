from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from hivemind.dag_state import StepLease
from hivemind.harness import create_run
from hivemind.plan_dag import build_dag, save_dag
from hivemind.supervisor import (
    active_step_leases,
    capture_runtime_snapshot,
    format_supervisor_status,
    probe_summaries_from_result,
    run_supervisor,
    stop_supervisor,
    supervisor_paths,
    supervisor_result_is_waiting,
    supervisor_status_report,
    tail_supervisor_log,
    validate_supervisor_output_artifacts,
    write_supervisor_state,
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

    def test_status_includes_runtime_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor runtime snapshot")

            report = supervisor_status_report(root, paths.run_id)
            snapshot = report["runtime_snapshot"]
            rendered = format_supervisor_status(report)

            self.assertEqual(snapshot["schema_version"], 1)
            self.assertIn("python", snapshot)
            self.assertIn("cpu", snapshot)
            self.assertIn("memory", snapshot)
            self.assertIn("gpu", snapshot)
            self.assertIn("provider_clis", snapshot)
            self.assertIn("Runtime:", rendered)

    def test_write_supervisor_state_persists_runtime_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor runtime persisted")

            write_supervisor_state(root, paths.run_id, {"schema_version": 1, "run_id": paths.run_id, "status": "running", "pid": os.getpid()})
            state = json.loads(supervisor_paths(root, paths.run_id)["state"].read_text(encoding="utf-8"))

            self.assertEqual(state["runtime_snapshot"]["pid"], os.getpid())
            self.assertIn("local_runtime", state["runtime_snapshot"])

    def test_capture_runtime_snapshot_handles_missing_local_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = capture_runtime_snapshot(Path(tmp), pid=123)

            self.assertEqual(snapshot["pid"], 123)
            self.assertEqual(snapshot["local_runtime"]["status"], "missing")
            self.assertIn("claude", snapshot["provider_clis"])

    def test_output_artifact_validation_detects_missing_expected_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor output validation missing")
            dag = build_dag(paths.run_id, "supervisor output validation missing", "implementation")
            step = dag.by_id("intake")
            assert step is not None
            step.status = "completed"
            step.expected_output_artifacts = ["missing-output.json"]
            save_dag(root, dag)

            report = validate_supervisor_output_artifacts(root, paths.run_id)

            self.assertFalse(report["ok"])
            self.assertEqual(report["missing"][0]["step_id"], "intake")
            self.assertEqual(report["missing"][0]["kind"], "expected_output")

    def test_output_artifact_validation_accepts_run_relative_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor output validation ok")
            dag = build_dag(paths.run_id, "supervisor output validation ok", "implementation")
            step = dag.by_id("intake")
            assert step is not None
            artifact_rel = "artifacts/output.json"
            (paths.run_dir / "artifacts").mkdir(exist_ok=True)
            (paths.run_dir / artifact_rel).write_text("{}", encoding="utf-8")
            step.status = "completed"
            step.expected_output_artifacts = [artifact_rel]
            step.artifact = artifact_rel
            save_dag(root, dag)

            report = validate_supervisor_output_artifacts(root, paths.run_id)

            self.assertTrue(report["ok"], report)
            self.assertEqual(report["checked_count"], 1)

    def test_supervisor_status_reports_output_artifact_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor status output validation")
            dag = build_dag(paths.run_id, "supervisor status output validation", "implementation")
            step = dag.by_id("intake")
            assert step is not None
            step.status = "completed"
            step.expected_output_artifacts = ["missing-output.json"]
            save_dag(root, dag)

            report = supervisor_status_report(root, paths.run_id)
            rendered = format_supervisor_status(report)

            self.assertFalse(report["output_artifacts_validated"])
            self.assertFalse(report["output_artifact_validation"]["ok"])
            self.assertIn("Artifacts: ok=False", rendered)

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

    def test_running_dead_pid_is_reported_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor stale pid")
            write_supervisor_state(
                root,
                paths.run_id,
                {
                    "schema_version": 1,
                    "run_id": paths.run_id,
                    "status": "running",
                    "pid": 999999999,
                    "host": "test",
                    "rounds": 0,
                    "max_rounds": 1,
                    "execute": False,
                    "log_path": "supervisor.log",
                },
            )

            report = supervisor_status_report(root, paths.run_id)

            self.assertEqual(report["status"], "stale")
            self.assertEqual(report["stale_reason"], "dead_pid")

    def test_stale_supervisor_writes_recovery_receipt_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor recovery receipt")
            write_supervisor_state(
                root,
                paths.run_id,
                {
                    "schema_version": 1,
                    "run_id": paths.run_id,
                    "status": "running",
                    "pid": 999999999,
                    "host": "test",
                    "rounds": 0,
                    "max_rounds": 1,
                    "execute": False,
                    "log_path": "supervisor.log",
                    "command_hash": "sha256:test",
                },
            )

            first = supervisor_status_report(root, paths.run_id)
            second = supervisor_status_report(root, paths.run_id)
            receipt = first.get("last_recovery_receipt")
            events = [record for record in read_execution_ledger(root, paths.run_id) if record.get("event") == "supervisor_recovery_recorded"]

            self.assertEqual(first["status"], "stale")
            self.assertEqual(first["recovery_status"], "recorded")
            self.assertTrue(receipt)
            self.assertEqual(second.get("last_recovery_receipt"), receipt)
            self.assertTrue((root / receipt).exists())
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["extra"]["stale_reason"], "dead_pid")

    def test_heartbeat_timeout_recovery_preserves_stale_heartbeat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor heartbeat recovery")
            write_supervisor_state(
                root,
                paths.run_id,
                {
                    "schema_version": 1,
                    "run_id": paths.run_id,
                    "status": "running",
                    "pid": os.getpid(),
                    "host": "test",
                    "rounds": 0,
                    "max_rounds": 1,
                    "execute": False,
                    "log_path": "supervisor.log",
                },
            )
            state_path = supervisor_paths(root, paths.run_id)["state"]
            state = json.loads(state_path.read_text(encoding="utf-8"))
            old_epoch = time.time() - 1000
            state["last_heartbeat_epoch"] = old_epoch
            state["last_heartbeat_at"] = "old"
            state_path.write_text(json.dumps(state), encoding="utf-8")

            report = supervisor_status_report(root, paths.run_id)
            recovered_state = json.loads(state_path.read_text(encoding="utf-8"))

            self.assertEqual(report["status"], "stale")
            self.assertEqual(report["stale_reason"], "heartbeat_timeout")
            self.assertEqual(recovered_state["last_heartbeat_at"], "old")
            self.assertGreaterEqual(report["heartbeat_age_seconds"], 900)
            self.assertTrue(report.get("last_recovery_receipt"))

    def test_stop_supervisor_writes_receipt_and_ledger_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "supervisor stop receipt")

            report = stop_supervisor(root, paths.run_id)
            receipt = report.get("last_stop_receipt")
            events = [record.get("event") for record in read_execution_ledger(root, paths.run_id)]

            self.assertEqual(report["status"], "stop_requested")
            self.assertTrue(receipt)
            self.assertTrue((root / receipt).exists())
            self.assertIn("supervisor_stop_requested", events)

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
