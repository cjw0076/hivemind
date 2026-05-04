"""Tests for dag_state transaction primitives."""
from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from hivemind.dag_state import (
    STEP_LEASES_DIR,
    StepLease,
    atomic_write,
    guard_transition,
    recover_expired_leases,
)
from hivemind.harness import create_run
from hivemind.plan_dag import build_dag, execute_step, load_dag, save_dag, update_step


class AtomicWriteTest(unittest.TestCase):
    def test_writes_file_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            atomic_write(path, '{"ok": true}')
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text())["ok"], True)

    def test_no_tmp_file_left_on_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.json"
            atomic_write(path, "hello")
            tmp_path = path.with_suffix(".json.tmp")
            self.assertFalse(tmp_path.exists())

    def test_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "out.txt"
            path.write_text("old")
            atomic_write(path, "new")
            self.assertEqual(path.read_text(), "new")


class GuardTransitionTest(unittest.TestCase):
    def test_pending_to_running_allowed(self):
        guard_transition("s1", "pending", "running")

    def test_running_to_completed_allowed(self):
        guard_transition("s1", "running", "completed")

    def test_running_to_failed_allowed(self):
        guard_transition("s1", "running", "failed")

    def test_running_to_skipped_allowed(self):
        guard_transition("s1", "running", "skipped")

    def test_completed_to_running_blocked(self):
        with self.assertRaises(ValueError) as ctx:
            guard_transition("s1", "completed", "running")
        self.assertIn("terminal", str(ctx.exception))

    def test_pending_to_completed_blocked(self):
        with self.assertRaises(ValueError):
            guard_transition("s1", "pending", "completed")

    def test_force_bypasses_guard(self):
        # No exception even for illegal transition
        guard_transition("s1", "completed", "running", force=True)

    def test_error_includes_step_id(self):
        with self.assertRaises(ValueError) as ctx:
            guard_transition("my_step", "skipped", "running")
        self.assertIn("my_step", str(ctx.exception))


class StepLeaseTest(unittest.TestCase):
    def test_acquire_creates_lease_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "lease test")
            lease = StepLease.acquire(root, paths.run_id, "planner")
            lease_file = paths.run_dir / STEP_LEASES_DIR / "planner.json"
            self.assertTrue(lease_file.exists())
            data = json.loads(lease_file.read_text())
            self.assertEqual(data["step_id"], "planner")
            self.assertEqual(data["run_id"], paths.run_id)
            lease.release()

    def test_release_removes_lease_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "release test")
            lease = StepLease.acquire(root, paths.run_id, "planner")
            lease.release()
            lease_file = paths.run_dir / STEP_LEASES_DIR / "planner.json"
            self.assertFalse(lease_file.exists())

    def test_second_acquire_raises_while_live(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "double lease test")
            lease = StepLease.acquire(root, paths.run_id, "planner")
            try:
                with self.assertRaises(RuntimeError) as ctx:
                    StepLease.acquire(root, paths.run_id, "planner")
                self.assertIn("leased by", str(ctx.exception))
            finally:
                lease.release()

    def test_expired_lease_can_be_reacquired(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "expire test")
            # Write a manually expired lease
            leases_dir = paths.run_dir / STEP_LEASES_DIR
            leases_dir.mkdir(exist_ok=True)
            expired_data = {
                "run_id": paths.run_id,
                "step_id": "planner",
                "idempotency_key": "old-key",
                "acquired_at": "2020-01-01T00:00:00Z",
                "expires_at": "2020-01-01T00:05:00Z",  # in the past
                "owner": "99999@oldhost",
            }
            (leases_dir / "planner.json").write_text(json.dumps(expired_data))
            # Should succeed despite existing file
            lease = StepLease.acquire(root, paths.run_id, "planner")
            self.assertNotEqual(lease.idempotency_key, "old-key")
            lease.release()

    def test_idempotency_key_is_unique_per_acquire(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "idempotency test")
            lease1 = StepLease.acquire(root, paths.run_id, "planner")
            key1 = lease1.idempotency_key
            lease1.release()
            lease2 = StepLease.acquire(root, paths.run_id, "planner")
            key2 = lease2.idempotency_key
            lease2.release()
            self.assertNotEqual(key1, key2)

    def test_heartbeat_extends_expiry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "heartbeat test")
            lease = StepLease.acquire(root, paths.run_id, "planner", ttl=10)
            old_expires = lease.expires_at
            lease.heartbeat(ttl=600)
            self.assertNotEqual(lease.expires_at, old_expires)
            lease.release()


class RecoverExpiredLeasesTest(unittest.TestCase):
    def test_recover_resets_running_step_to_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "recover test")
            dag = build_dag(paths.run_id, "recover test", "implementation")
            # Simulate a crashed worker: step is running but lease is expired
            planner = dag.by_id("planner")
            planner.status = "running"
            leases_dir = paths.run_dir / STEP_LEASES_DIR
            leases_dir.mkdir(exist_ok=True)
            expired = {
                "run_id": paths.run_id,
                "step_id": "planner",
                "idempotency_key": "crashed",
                "acquired_at": "2020-01-01T00:00:00Z",
                "expires_at": "2020-01-01T00:05:00Z",
                "owner": "dead@worker",
            }
            (leases_dir / "planner.json").write_text(json.dumps(expired))
            recovered = recover_expired_leases(root, paths.run_id, dag)
            self.assertIn("planner", recovered)
            self.assertEqual(dag.by_id("planner").status, "pending")
            self.assertIsNone(dag.by_id("planner").started_at)

    def test_live_lease_not_recovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "live lease test")
            dag = build_dag(paths.run_id, "live lease test", "implementation")
            planner = dag.by_id("planner")
            planner.status = "running"
            # Create a live lease
            lease = StepLease.acquire(root, paths.run_id, "planner")
            recovered = recover_expired_leases(root, paths.run_id, dag)
            self.assertNotIn("planner", recovered)
            self.assertEqual(dag.by_id("planner").status, "running")
            lease.release()

    def test_no_leases_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "no leases test")
            dag = build_dag(paths.run_id, "no leases test", "review")
            result = recover_expired_leases(root, paths.run_id, dag)
            self.assertEqual(result, [])


class SaveDagCasTest(unittest.TestCase):
    def test_save_dag_increments_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "version test")
            dag = build_dag(paths.run_id, "version test", "review")
            self.assertEqual(dag.version, 0)
            save_dag(root, dag)
            self.assertEqual(dag.version, 1)
            save_dag(root, dag)
            self.assertEqual(dag.version, 2)

    def test_load_dag_preserves_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "version persist")
            dag = build_dag(paths.run_id, "version persist", "review")
            save_dag(root, dag)
            loaded = load_dag(root, paths.run_id)
            self.assertEqual(loaded.version, 1)

    def test_cas_succeeds_with_correct_expected_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "cas success")
            dag = build_dag(paths.run_id, "cas success", "review")
            save_dag(root, dag)                        # version → 1
            save_dag(root, dag, expected_version=1)    # CAS: expect 1, writes 2
            self.assertEqual(dag.version, 2)

    def test_cas_raises_on_stale_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "cas conflict")
            dag = build_dag(paths.run_id, "cas conflict", "review")
            save_dag(root, dag)    # version → 1
            with self.assertRaises(RuntimeError) as ctx:
                save_dag(root, dag, expected_version=0)  # expects 0, disk has 1
            self.assertIn("CAS conflict", str(ctx.exception))


class ExecuteStepTransactionTest(unittest.TestCase):
    def test_execute_step_leaves_lease_released(self):
        """After execute_step, no lease file should remain."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "lease cleanup")
            dag = build_dag(paths.run_id, "lease cleanup", "implementation")
            execute_step(root, dag, "verify", execute=False)
            lease_file = paths.run_dir / STEP_LEASES_DIR / "verify.json"
            self.assertFalse(lease_file.exists())

    def test_execute_step_returns_idempotency_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "idem key")
            dag = build_dag(paths.run_id, "idem key", "implementation")
            result = execute_step(root, dag, "verify", execute=False)
            self.assertIn("idempotency_key", result)
            self.assertTrue(result["idempotency_key"])

    def test_transition_blocked_for_completed_step_when_not_terminal(self):
        """A skipped step cannot be re-run without force."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "transition block")
            dag = build_dag(paths.run_id, "transition block", "review")
            update_step(dag, "context", status="skipped")
            result = execute_step(root, dag, "context", execute=False)
            self.assertFalse(result.get("ok"))
            self.assertEqual(result["status"], "transition_blocked")

    def test_force_overrides_transition_block(self):
        """force=True allows re-running a skipped step."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "force retry")
            dag = build_dag(paths.run_id, "force retry", "review")
            update_step(dag, "context", status="skipped")
            # Should not raise or return transition_blocked
            result = execute_step(root, dag, "context", execute=False, force=True)
            self.assertNotEqual(result.get("status"), "transition_blocked")


if __name__ == "__main__":
    unittest.main()
