from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import flow_advance
from hivemind.plan_dag import load_dag


class WorkflowSchedulerSurfaceTest(unittest.TestCase):
    def test_workflow_state_is_plan_dag_read_model_when_flow_creates_dag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = flow_advance(root, task="build feature", complexity="fast")
            run_dir = root / ".runs" / report["run_id"]
            dag = load_dag(root, report["run_id"])
            workflow = json.loads((run_dir / "artifacts" / "workflow_state.json").read_text(encoding="utf-8"))

            self.assertIsNotNone(dag)
            self.assertEqual(workflow["scheduler"], "plan_dag")
            self.assertEqual(workflow["scheduler_authority"], "plan_dag.json")
            self.assertEqual(workflow["surface_role"], "read_model")
            self.assertEqual(workflow["read_model_of"], workflow["plan_dag_path"])
            self.assertEqual([step["step_id"] for step in workflow["steps"]], [step.step_id for step in dag.steps])
            self.assertNotIn("legacy_steps", workflow)
            self.assertNotIn("dag_steps", workflow)

    def test_workflow_state_status_and_next_come_from_plan_dag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = flow_advance(root, task="build feature", complexity="fast")
            dag = load_dag(root, report["run_id"])
            workflow = json.loads(
                (root / ".runs" / report["run_id"] / "artifacts" / "workflow_state.json").read_text(encoding="utf-8")
            )

            self.assertIsNotNone(dag)
            self.assertEqual(workflow["status"], "waiting_for_dag_step")
            self.assertEqual(workflow["next"]["command"], f"hive step run {dag.next_sequential().step_id}")
            self.assertEqual(workflow["next"]["source"], "plan_dag")


if __name__ == "__main__":
    unittest.main()
