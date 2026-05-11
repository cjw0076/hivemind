from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import create_run, next_grounded_action


class NextGroundedActionTest(unittest.TestCase):
    def test_returns_pipeline_action_for_fresh_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "next grounded smoke")
            action = next_grounded_action(root, paths.run_id)
            self.assertIn("command", action)
            self.assertIn("reason", action)
            self.assertIn("source", action)
            self.assertEqual(action["run_id"], paths.run_id)

    def test_escalation_takes_priority_over_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "next escalation priority")
            dis_path = paths.run_dir / "disagreements.json"
            dis_path.write_text(
                json.dumps([
                    {
                        "ts": "2026-05-11T00:00:00Z",
                        "run_id": paths.run_id,
                        "step_id": "step_a",
                        "topology_type": "split",
                        "severity": "high",
                        "axes": ["conclusion"],
                        "dominant_axis": "conclusion",
                        "disagreement_count": 2,
                        "disagreement_targets": ["step_b"],
                        "topology_recommended_action": "escalate",
                    }
                ]),
                encoding="utf-8",
            )
            action = next_grounded_action(root, paths.run_id)
            self.assertEqual(action["source"], "disagreement_topology")
            self.assertIn("inspect", action["command"])
            self.assertIn("escalation", action["reason"])

    def test_low_severity_disagreement_does_not_escalate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "next low severity")
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
            action = next_grounded_action(root, paths.run_id)
            self.assertNotEqual(action["source"], "disagreement_topology")

    def test_cli_hive_next_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "cli next smoke", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            result = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "next", "--run-id", run_id, "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            data = json.loads(result.stdout)
            self.assertIn("command", data)
            self.assertIn("reason", data)
            self.assertIn("source", data)
            self.assertEqual(data["run_id"], run_id)

    def test_cli_hive_next_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "cli next text smoke", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            result = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "next", "--run-id", run_id],
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("#", result.stdout)


if __name__ == "__main__":
    unittest.main()
