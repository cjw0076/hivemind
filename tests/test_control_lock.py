from pathlib import Path
import tempfile
import time
import unittest

from hivemind.harness import (
    acquire_control_lock,
    create_run,
    heartbeat_control_lock,
    release_control_lock,
    write_json,
)


class ControlLockTest(unittest.TestCase):
    def test_single_controller_lock_blocks_second_controller(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "lock smoke", project="Hive Mind")
            lock = acquire_control_lock(root, paths.run_id)

            with self.assertRaises(RuntimeError):
                acquire_control_lock(root, paths.run_id)

            release_control_lock(root, paths.run_id, lock["session_id"])
            self.assertFalse(paths.control_lock.exists())

    def test_heartbeat_updates_lock(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "heartbeat smoke", project="Hive Mind")
            lock = acquire_control_lock(root, paths.run_id)
            first = lock["last_heartbeat_epoch"]
            time.sleep(0.01)

            heartbeat_control_lock(root, paths.run_id, lock["session_id"])
            updated = paths.control_lock.read_text(encoding="utf-8")

            self.assertIn(lock["session_id"], updated)
            self.assertNotIn(str(first + 999), updated)

    def test_stale_lock_can_be_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "stale lock smoke", project="Hive Mind")
            write_json(
                paths.control_lock,
                {
                    "schema_version": 1,
                    "session_id": "old",
                    "role": "controller",
                    "pid": 1,
                    "started_at": "old",
                    "last_heartbeat": "old",
                    "last_heartbeat_epoch": 0,
                    "ttl_seconds": 1,
                },
            )

            lock = acquire_control_lock(root, paths.run_id, ttl_seconds=1)

            self.assertNotEqual(lock["session_id"], "old")

    def test_dead_pid_lock_can_be_replaced_before_ttl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "dead pid lock smoke", project="Hive Mind")
            write_json(
                paths.control_lock,
                {
                    "schema_version": 1,
                    "session_id": "dead",
                    "role": "controller",
                    "pid": 999999999,
                    "started_at": "old",
                    "last_heartbeat": "old",
                    "last_heartbeat_epoch": time.time(),
                    "ttl_seconds": 120,
                },
            )

            lock = acquire_control_lock(root, paths.run_id, ttl_seconds=120)

            self.assertNotEqual(lock["session_id"], "dead")


if __name__ == "__main__":
    unittest.main()
