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
    evaluate_step_output,
    execute_fan_out,
    execute_step,
    format_dag,
    load_dag,
    save_dag,
    save_step_evaluation,
    update_step,
    DAG_TEMPLATES,
    _compute_evaluator_votes,
    _compute_agreement,
    _evaluate_syntax,
    _evaluate_execution,
    _evaluate_claim,
    _evaluate_risk,
    _evaluate_disagreement,
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


class EvaluatorUnitTest(unittest.TestCase):
    """Unit tests for individual evaluator helpers."""

    def _make_step(self, kind="sequential", on_failure="stop", owner_role="claude-planner"):
        from hivemind.plan_dag import _step
        return _step("test_step", kind, [], owner_role, [],
                     on_failure=on_failure, status="completed")

    def test_syntax_no_artifact_path_no_required_outputs(self):
        step = self._make_step()
        step.expected_output_artifacts = []
        result = _evaluate_syntax(step, None)
        self.assertTrue(result["schema_valid"])
        self.assertFalse(result["artifact_exists"])

    def test_syntax_no_artifact_path_with_required_outputs(self):
        step = self._make_step()
        step.expected_output_artifacts = ["something.yaml"]
        result = _evaluate_syntax(step, None)
        self.assertFalse(result["schema_valid"])

    def test_execution_score_by_status(self):
        self.assertEqual(_evaluate_execution("completed")["execution_score"], 1.0)
        self.assertEqual(_evaluate_execution("prepared")["execution_score"], 1.0)
        self.assertEqual(_evaluate_execution("failed")["execution_score"], 0.0)
        self.assertEqual(_evaluate_execution("partial")["execution_score"], 0.5)
        self.assertEqual(_evaluate_execution(None)["execution_score"], 0.0)

    def test_claim_no_artifact(self):
        result = _evaluate_claim(None)
        self.assertEqual(result["unsupported_claims"], 0)
        self.assertEqual(result["evidence_score"], 1.0)

    def test_risk_codex_executor_is_high(self):
        step = self._make_step(owner_role="codex-executor")
        result = _evaluate_risk(step)
        self.assertEqual(result["risk_level"], "high")
        self.assertIn("write_access", result["risk_factors"])

    def test_risk_verify_step_is_medium(self):
        # gate_step factor requires on_failure="escalate" (matching DAG template)
        from hivemind.plan_dag import _step as make_step
        step = make_step("verify_s", "verify", [], "verifier", [], on_failure="escalate", status="pending")
        result = _evaluate_risk(step)
        self.assertEqual(result["risk_level"], "medium")
        self.assertIn("gate_step", result["risk_factors"])

    def test_risk_local_step_is_low(self):
        step = self._make_step(owner_role="local-context-compressor")
        result = _evaluate_risk(step)
        self.assertEqual(result["risk_level"], "low")

    def test_disagreement_no_parallel_siblings(self):
        dag = build_dag("run_dis1", "task", "implementation")
        step = dag.by_id("planner")
        result = _evaluate_disagreement(dag, step)
        self.assertEqual(result["disagreement_count"], 0)


class EvaluatorVoteTest(unittest.TestCase):
    def _votes(self, **kwargs):
        from hivemind.plan_dag import _step
        step = _step("s", "sequential", [], "claude-planner", [], on_failure="stop", status="completed")
        syntax = {"schema_valid": kwargs.get("schema_valid", True), "artifact_exists": True, "artifact_parseable": True, "missing_keys": []}
        execution = {"execution_score": kwargs.get("exec_score", 1.0), "artifact_status": "completed"}
        claim = {"evidence_score": kwargs.get("evid_score", 1.0), "unsupported_claims": kwargs.get("unsupported", 0)}
        risk = {"risk_level": kwargs.get("risk", "low"), "risk_factors": []}
        disagreement = {"disagreement_count": kwargs.get("disagree", 0), "disagreement_targets": []}
        return _compute_evaluator_votes(step, syntax, execution, claim, risk, disagreement,
                                        kwargs.get("confidence", None), {}, {})

    def test_all_positive_votes_accept(self):
        votes = self._votes()
        self.assertEqual(votes["syntax"], "accept")
        self.assertEqual(votes["execution"], "accept")
        self.assertEqual(votes["claim"], "accept")
        self.assertEqual(votes["risk"], "accept")
        self.assertEqual(votes["disagreement"], "accept")

    def test_agreement_perfect_when_all_accept(self):
        votes = self._votes()
        agreement = _compute_agreement(votes, "accept")
        self.assertEqual(agreement, 1.0)

    def test_agreement_low_when_action_minority(self):
        votes = {"syntax": "accept", "execution": "accept", "claim": "accept", "risk": "add_review", "disagreement": "accept"}
        agreement = _compute_agreement(votes, "add_review")
        self.assertAlmostEqual(agreement, 0.2)

    def test_high_risk_vote_is_add_review(self):
        votes = self._votes(risk="high")
        self.assertEqual(votes["risk"], "add_review")

    def test_schema_invalid_vote_is_escalate(self):
        votes = self._votes(schema_valid=False)
        self.assertEqual(votes["syntax"], "escalate")


class ConfidenceHistoryTest(unittest.TestCase):
    def test_confidence_history_empty_initially(self):
        dag = build_dag("run_ch1", "task", "review")
        step = dag.by_id("context")
        self.assertEqual(step.confidence_history, [])

    def test_confidence_history_grows_after_evaluate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "ch test")
            dag = build_dag(paths.run_id, "ch test", "implementation")
            step = dag.by_id("verify")
            step.status = "completed"
            # Inject an artifact with confidence
            import json
            artifact_dir = (root / paths.run_id / "agents" / "harness")
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact = artifact_dir / "verify_result.json"
            artifact.write_text(json.dumps({"status": "completed", "confidence": 0.75}))
            step.artifact = str(artifact.relative_to(root))
            evaluate_step_output(root, dag, step)
            self.assertEqual(len(step.confidence_history), 1)
            self.assertAlmostEqual(step.confidence_history[0]["value"], 0.75)
            self.assertEqual(step.confidence_history[0]["attempt"], 1)

    def test_evi_computed_after_two_evaluations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "evi test")
            dag = build_dag(paths.run_id, "evi test", "implementation")
            step = dag.by_id("verify")
            step.status = "completed"
            import json
            artifact_dir = (root / paths.run_id / "agents" / "harness")
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact = artifact_dir / "verify_result.json"
            artifact.write_text(json.dumps({"status": "completed", "confidence": 0.55}))
            step.artifact = str(artifact.relative_to(root))
            evaluate_step_output(root, dag, step)
            # Simulate retry with improved confidence
            artifact.write_text(json.dumps({"status": "completed", "confidence": 0.82}))
            eval2 = evaluate_step_output(root, dag, step)
            self.assertIsNotNone(eval2["evi"])
            self.assertGreater(eval2["evi"]["confidence_delta"], 0)
            self.assertEqual(eval2["evi"]["estimated_value"], "positive")

    def test_confidence_history_persists_through_save_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "hist persist")
            dag = build_dag(paths.run_id, "hist persist", "review")
            import json
            artifact_dir = (root / paths.run_id / "agents" / "harness")
            artifact_dir.mkdir(parents=True, exist_ok=True)
            artifact = artifact_dir / "verify_result.json"
            artifact.write_text(json.dumps({"status": "completed", "confidence": 0.9}))
            step = dag.by_id("verify")
            step.status = "completed"
            step.artifact = str(artifact.relative_to(root))
            evaluate_step_output(root, dag, step)
            save_dag(root, dag)
            loaded = load_dag(root, paths.run_id)
            loaded_step = loaded.by_id("verify")
            self.assertEqual(len(loaded_step.confidence_history), 1)
            self.assertAlmostEqual(loaded_step.confidence_history[0]["value"], 0.9)


class StepEvaluationArtifactTest(unittest.TestCase):
    def test_save_step_evaluation_writes_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "eval artifact test")
            evaluation = {"evaluated_at": "2025-01-01T00:00:00Z", "recommended_action": "accept"}
            out = save_step_evaluation(root, paths.run_id, "planner", evaluation)
            self.assertTrue(out.exists())
            data = json.loads(out.read_text())
            self.assertEqual(data["recommended_action"], "accept")

    def test_evaluate_step_output_writes_artifact_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "eval artifact auto")
            dag = build_dag(paths.run_id, "eval artifact auto", "implementation")
            step = dag.by_id("verify")
            step.status = "completed"
            evaluate_step_output(root, dag, step)
            # run_dir is paths.run_dir, not root/run_id
            artifact = paths.run_dir / "step_evaluations" / "verify.json"
            self.assertTrue(artifact.exists(), f"Expected {artifact}")
            data = json.loads(artifact.read_text())
            self.assertIn("evaluator_votes", data)
            self.assertIn("evaluator_agreement", data)


class FanOutTest(unittest.TestCase):
    def test_fan_out_dispatches_parallel_steps(self):
        """Both parallel steps in the implementation DAG are dispatched in one round."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "fan out parallel")
            dag = build_dag(paths.run_id, "fan out parallel", "implementation")
            result = execute_fan_out(root, dag, execute=False)
            save_dag(root, dag)
            self.assertEqual(result["mode"], "parallel")
            self.assertIn("context", result["dispatched"])
            self.assertIn("diff_review", result["dispatched"])
            self.assertEqual(len(result["dispatched"]), 2)

    def test_fan_out_closes_barrier_when_one_parallel_completed(self):
        """completed + skipped is enough for barrier to close after fan-out."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "fan out barrier")
            dag = build_dag(paths.run_id, "fan out barrier", "implementation")
            # Pre-complete one parallel dep; the other will be dispatched and skip
            update_step(dag, "context", status="completed")
            result = execute_fan_out(root, dag, execute=False)
            save_dag(root, dag)
            # diff_review dispatched (skips), context already completed → barrier closes
            self.assertIn("diff_review", result["dispatched"])
            self.assertIn("barrier_context", result.get("barriers_closed", []))
            self.assertEqual(dag.status_of("barrier_context"), "completed")

    def test_fan_out_sequential_when_no_parallel_runnable(self):
        """With no runnable parallel steps, fan-out runs the next sequential step."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "fan out seq")
            dag = build_dag(paths.run_id, "fan out seq", "implementation")
            # Force all parallel and barrier steps to completed
            for sid in ("context", "diff_review", "barrier_context"):
                update_step(dag, sid, status="completed")
            result = execute_fan_out(root, dag, execute=False)
            save_dag(root, dag)
            self.assertEqual(result["mode"], "sequential")
            self.assertIn("planner", result["dispatched"])

    def test_fan_out_idle_when_dag_is_blocked(self):
        """If a stop-failure step has blocked the DAG, fan-out returns idle."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "fan out blocked")
            dag = build_dag(paths.run_id, "fan out blocked", "implementation")
            # Force barrier_context to failed (on_failure=stop → blocks DAG)
            update_step(dag, "context", status="completed")
            update_step(dag, "diff_review", status="completed")
            update_step(dag, "barrier_context", status="completed")
            update_step(dag, "planner", status="failed")
            result = execute_fan_out(root, dag, execute=False)
            self.assertEqual(result["mode"], "idle")
            self.assertEqual(result["dispatched"], [])
            self.assertTrue(result["dag_blocked"])

    def test_fan_out_all_skipped_barrier_stays_open(self):
        """If all parallel deps are skipped (no completed), barrier must NOT close."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "fan out all skip")
            dag = build_dag(paths.run_id, "fan out all skip", "implementation")
            # Mark parallel steps as skipped before fan-out
            update_step(dag, "context", status="skipped")
            update_step(dag, "diff_review", status="skipped")
            result = execute_fan_out(root, dag, execute=False)
            # No parallel steps were runnable (already terminal), no barrier should close
            self.assertNotIn("barrier_context", result.get("barriers_closed", []))
            self.assertEqual(dag.status_of("barrier_context"), "pending")

    def test_fan_out_partial_skip_closes_barrier(self):
        """One completed + one skipped is sufficient for barrier to close."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "fan out partial skip")
            dag = build_dag(paths.run_id, "fan out partial skip", "implementation")
            update_step(dag, "context", status="completed")
            update_step(dag, "diff_review", status="skipped")
            result = execute_fan_out(root, dag, execute=False)
            self.assertIn("barrier_context", result.get("barriers_closed", []))

    def test_fan_out_result_persists_after_save_load(self):
        """Barrier closed by fan-out is visible after save + reload."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "fan out persist")
            dag = build_dag(paths.run_id, "fan out persist", "implementation")
            update_step(dag, "context", status="completed")  # one dep pre-completed
            execute_fan_out(root, dag, execute=False)
            save_dag(root, dag)
            loaded = load_dag(root, paths.run_id)
            self.assertEqual(loaded.status_of("barrier_context"), "completed")

    def test_fan_out_next_points_to_sequential_step_after_barrier(self):
        """After barrier closes, 'next' should point to the step after the barrier."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "fan out next")
            dag = build_dag(paths.run_id, "fan out next", "implementation")
            # Pre-complete one dep so barrier can close after fan-out
            update_step(dag, "context", status="completed")
            result = execute_fan_out(root, dag, execute=False)
            # diff_review dispatched (skip) + context completed → barrier closes → next=planner
            self.assertIn("barrier_context", result.get("barriers_closed", []))
            self.assertEqual(result.get("next"), "planner")


if __name__ == "__main__":
    unittest.main()
