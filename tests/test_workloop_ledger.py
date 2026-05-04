from __future__ import annotations

import subprocess
import tempfile
import unittest
import json
from pathlib import Path

from hivemind.harness import create_run
from hivemind.plan_dag import build_dag, execute_step
from hivemind.protocol import build_execution_intent, check_intent, decide_intent, save_intent
from hivemind.workloop import (
    append_execution_ledger,
    capture_worktree_snapshot,
    execution_ledger_path,
    read_execution_ledger,
    replay_execution_ledger,
)


class WorkloopLedgerTest(unittest.TestCase):
    def test_append_records_are_hash_chained(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "ledger chain")

            first = append_execution_ledger(root, paths.run_id, "step_started", actor="codex", step_id="executor")
            second = append_execution_ledger(root, paths.run_id, "step_completed", actor="codex", step_id="executor")

            records = read_execution_ledger(root, paths.run_id)
            self.assertEqual([record["seq"] for record in records], [1, 2])
            self.assertEqual(second["previous_hash"], first["hash"])
            self.assertEqual(records[-1]["hash"], second["hash"])

    def test_git_snapshot_tracks_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / "README.md").write_text("draft\n", encoding="utf-8")

            snapshot = capture_worktree_snapshot(root)
            self.assertIn("README.md", snapshot)

    def test_execute_step_writes_visible_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "ledger step")
            dag = build_dag(paths.run_id, "ledger step", "implementation")

            result = execute_step(root, dag, "verify", execute=False)
            self.assertTrue(result.get("ok"), result)

            records = read_execution_ledger(root, paths.run_id)
            events = [record.get("event") for record in records]
            self.assertIn("step_started", events)
            self.assertIn("step_completed", events)
            completed = next(record for record in records if record.get("event") == "step_completed")
            self.assertEqual(completed.get("step_id"), "verify")
            self.assertIn(".runs/", ",".join(completed.get("files_touched") or []))

    def test_replay_validates_hash_chain_and_reconstructs_steps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "ledger replay")

            append_execution_ledger(root, paths.run_id, "step_started", actor="harness", step_id="verify", status="running")
            append_execution_ledger(root, paths.run_id, "step_completed", actor="harness", step_id="verify", status="completed")

            report = replay_execution_ledger(root, paths.run_id)

            self.assertTrue(report["ok"], report)
            self.assertTrue(report["hash_chain_ok"])
            self.assertTrue(report["seq_ok"])
            self.assertTrue(report["steps"]["verify"]["started"])
            self.assertTrue(report["steps"]["verify"]["completed"])

    def test_replay_detects_hash_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "ledger tamper")
            append_execution_ledger(root, paths.run_id, "step_started", actor="harness", step_id="verify", status="running")

            ledger_path = execution_ledger_path(root, paths.run_id)
            record = json.loads(ledger_path.read_text(encoding="utf-8").splitlines()[0])
            record["status"] = "tampered"
            ledger_path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

            report = replay_execution_ledger(root, paths.run_id)
            issue_types = {issue["type"] for issue in report["issues"]}

            self.assertFalse(report["ok"])
            self.assertIn("hash_mismatch", issue_types)

    def test_replay_detects_missing_artifact_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "ledger artifact drift")
            append_execution_ledger(
                root,
                paths.run_id,
                "intent_proposed",
                actor="harness",
                step_id="planner",
                status="proposed",
                artifact=f".runs/{paths.run_id}/execution_intents/missing.json",
                extra={"intent_id": "intent_missing"},
            )

            report = replay_execution_ledger(root, paths.run_id)
            issue_types = {issue["type"] for issue in report["issues"]}

            self.assertFalse(report["ok"])
            self.assertIn("missing_artifact", issue_types)

    def test_replay_reconstructs_protocol_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "ledger authority")
            dag = build_dag(paths.run_id, "ledger authority", "implementation")
            intent = build_execution_intent(root, dag, "planner", execute=True)
            save_intent(root, intent)
            check_intent(root, paths.run_id, intent.intent_id)
            decision = decide_intent(root, paths.run_id, intent.intent_id)

            report = replay_execution_ledger(root, paths.run_id)
            authority = report["authority"]

            self.assertIn(intent.intent_id, authority["intents"])
            self.assertIn(intent.intent_id, authority["decisions"])
            self.assertEqual(authority["decisions"][intent.intent_id]["decision"], decision.decision)
            self.assertEqual(authority["by_step"]["planner"]["latest_intent"], intent.intent_id)

    def test_cli_ledger_replay_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "ledger replay cli")
            append_execution_ledger(root, paths.run_id, "step_completed", actor="harness", step_id="verify", status="completed")
            completed = subprocess.run(
                [
                    "python",
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "ledger",
                    "replay",
                    "--run-id",
                    paths.run_id,
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )
            data = json.loads(completed.stdout)
            self.assertTrue(data["ok"], data)
            self.assertIn("verify", data["steps"])


if __name__ == "__main__":
    unittest.main()
