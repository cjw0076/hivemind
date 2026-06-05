from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hivemind.harness import create_run
from hivemind.plan_dag import build_dag, execute_step, save_dag, update_step


class StepResultHardeningTest(unittest.TestCase):
    def test_provider_timeout_artifact_cannot_complete_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider timeout is failed")
            dag = build_dag(paths.run_id, "provider timeout is failed", "implementation")
            for step_id in ("context", "diff_review", "barrier_context"):
                update_step(dag, step_id, status="completed")
            artifact = paths.run_dir / "agents" / "claude" / "planner_result.yaml"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("status: timeout\nreason: provider did not finish\n", encoding="utf-8")

            with patch("hivemind.harness.invoke_external_agent", return_value=artifact):
                result = execute_step(root, dag, "planner", execute=False)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["status"], "failed")
            self.assertNotEqual(dag.status_of("planner"), "completed")

    def test_missing_status_artifact_cannot_complete_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "missing status artifact")
            dag = build_dag(paths.run_id, "missing status artifact", "implementation")
            for step_id in ("context", "diff_review", "barrier_context"):
                update_step(dag, step_id, status="completed")
            artifact = paths.run_dir / "agents" / "claude" / "planner_result.yaml"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text("prompt: missing status is not success\n", encoding="utf-8")

            with patch("hivemind.harness.invoke_external_agent", return_value=artifact):
                result = execute_step(root, dag, "planner", execute=False)

            self.assertFalse(result["ok"], result)
            self.assertEqual(result["status"], "failed")
            self.assertNotEqual(dag.status_of("planner"), "completed")

    def test_saved_dag_sync_does_not_promote_failed_artifact_to_completed(self) -> None:
        from hivemind.flow_runtime import sync_dag_with_run_state
        from hivemind.harness import set_agent_status

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "sync failed artifact")
            dag = build_dag(paths.run_id, "sync failed artifact", "implementation")
            artifact = paths.local_dir / "context.json"
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_text('{"status": "failed", "reason": "backend missing"}', encoding="utf-8")
            set_agent_status(paths, "local-context-compressor", "completed")
            save_dag(root, dag)

            sync_dag_with_run_state(root, paths.run_id, dag)

            self.assertEqual(dag.status_of("context"), "skipped")
            self.assertNotEqual(dag.status_of("context"), "completed")


if __name__ == "__main__":
    unittest.main()
