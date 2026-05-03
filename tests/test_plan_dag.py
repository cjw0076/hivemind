"""Tests for the plan_dag DAG runtime."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import create_run
from hivemind.plan_dag import (
    PlanDAG,
    PlanStep,
    auto_close_barriers,
    build_dag,
    execute_step,
    format_dag,
    load_dag,
    save_dag,
    update_step,
    DAG_TEMPLATES,
)


class PlanDagBuildTest(unittest.TestCase):
    def test_build_implementation_dag(self) -> None:
        dag = build_dag("run_01", "add retry logic", "implementation")
        self.assertEqual(dag.intent, "implementation")
        ids = [s.step_id for s in dag.steps]
        self.assertIn("intake", ids)
        self.assertIn("barrier_context", ids)
        self.assertIn("planner", ids)
        self.assertIn("executor", ids)
        self.assertIn("verify", ids)
        self.assertIn("close", ids)

    def test_intake_starts_completed(self) -> None:
        dag = build_dag("run_02", "review diff", "review")
        intake = dag.by_id("intake")
        self.assertIsNotNone(intake)
        self.assertEqual(intake.status, "completed")

    def test_all_templates_have_intake_and_close(self) -> None:
        for intent in ["implementation", "review", "planning", "debugging"]:
            dag = build_dag(f"run_{intent}", "task", intent)
            self.assertIsNotNone(dag.by_id("intake"), intent)
            self.assertIsNotNone(dag.by_id("close"), intent)

    def test_runnable_returns_only_satisfied_deps(self) -> None:
        dag = build_dag("run_03", "debug crash", "debugging")
        runnable = dag.runnable()
        runnable_ids = {s.step_id for s in runnable}
        # Only steps whose depends_on are all completed (intake is completed, so context/log_review are runnable)
        self.assertIn("context", runnable_ids)
        self.assertIn("log_review", runnable_ids)
        self.assertNotIn("barrier_debug", runnable_ids)
        self.assertNotIn("planner", runnable_ids)

    def test_next_sequential_is_deterministic(self) -> None:
        dag = build_dag("run_04", "plan arch", "planning")
        first = dag.next_sequential()
        self.assertIsNotNone(first)
        second = dag.next_sequential()
        self.assertEqual(first.step_id, second.step_id)

    def test_is_complete_false_initially(self) -> None:
        dag = build_dag("run_05", "task", "review")
        self.assertFalse(dag.is_complete())

    def test_is_complete_when_all_done(self) -> None:
        dag = build_dag("run_06", "task", "review")
        for step in dag.steps:
            step.status = "completed"
        self.assertTrue(dag.is_complete())


class BarrierTest(unittest.TestCase):
    def test_barrier_auto_closes_when_deps_complete(self) -> None:
        dag = build_dag("run_b1", "impl", "implementation")
        for sid in ("context", "diff_review"):
            update_step(dag, sid, status="completed")
        closed = auto_close_barriers(dag)
        self.assertIn("barrier_context", closed)
        self.assertEqual(dag.status_of("barrier_context"), "completed")

    def test_barrier_stays_open_with_incomplete_deps(self) -> None:
        dag = build_dag("run_b2", "impl", "implementation")
        update_step(dag, "context", status="completed")
        # diff_review still pending
        closed = auto_close_barriers(dag)
        self.assertNotIn("barrier_context", closed)
        self.assertEqual(dag.status_of("barrier_context"), "pending")

    def test_runnable_after_barrier_closes(self) -> None:
        dag = build_dag("run_b3", "impl", "implementation")
        for sid in ("context", "diff_review"):
            update_step(dag, sid, status="completed")
        auto_close_barriers(dag)
        runnable_ids = {s.step_id for s in dag.runnable()}
        self.assertIn("planner", runnable_ids)


class PersistenceTest(unittest.TestCase):
    def test_save_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "save load test")
            dag = build_dag(paths.run_id, "save load test", "review")
            saved_path = save_dag(root, dag)
            self.assertTrue(saved_path.exists())

            loaded = load_dag(root, paths.run_id)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.run_id, dag.run_id)
            self.assertEqual(len(loaded.steps), len(dag.steps))
            self.assertEqual(loaded.steps[0].step_id, dag.steps[0].step_id)

    def test_load_returns_none_when_no_dag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "no dag here")
            result = load_dag(root, paths.run_id)
            self.assertIsNone(result)

    def test_step_status_persists_after_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "persist test")
            dag = build_dag(paths.run_id, "persist test", "planning")
            update_step(dag, "context", status="completed")
            save_dag(root, dag)

            loaded = load_dag(root, paths.run_id)
            self.assertEqual(loaded.status_of("context"), "completed")


class ExecuteStepTest(unittest.TestCase):
    def test_execute_verify_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "exec verify")
            dag = build_dag(paths.run_id, "exec verify", "implementation")
            result = execute_step(root, dag, "verify", execute=False)
            self.assertTrue(result.get("ok"), result)
            self.assertEqual(result["status"], "completed")
            self.assertIn("verification.yaml", result.get("artifact", ""))

    def test_execute_barrier_step_waits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "barrier wait test")
            dag = build_dag(paths.run_id, "barrier wait", "implementation")
            result = execute_step(root, dag, "barrier_context", execute=False)
            self.assertFalse(result.get("ok"))
            self.assertEqual(result["status"], "barrier_waiting")

    def test_execute_barrier_closes_when_deps_done(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "barrier close test")
            dag = build_dag(paths.run_id, "barrier close", "implementation")
            update_step(dag, "context", status="completed")
            update_step(dag, "diff_review", status="completed")
            result = execute_step(root, dag, "barrier_context", execute=False)
            self.assertTrue(result.get("ok"), result)
            self.assertEqual(result["status"], "barrier_closed")

    def test_already_completed_step_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "idempotent test")
            dag = build_dag(paths.run_id, "idempotent", "review")
            result = execute_step(root, dag, "intake", execute=False)
            self.assertTrue(result.get("ok"))
            self.assertEqual(result["status"], "already_completed")


class FormatDagTest(unittest.TestCase):
    def test_format_dag_contains_key_elements(self) -> None:
        dag = build_dag("run_fmt1", "test formatting", "implementation")
        output = format_dag(dag)
        self.assertIn("intake", output)
        self.assertIn("barrier_context", output)
        self.assertIn("Next:", output)

    def test_format_dag_shows_complete_when_all_done(self) -> None:
        dag = build_dag("run_fmt2", "all done", "review")
        for step in dag.steps:
            step.status = "completed"
        output = format_dag(dag)
        self.assertIn("All steps complete", output)


if __name__ == "__main__":
    unittest.main()
