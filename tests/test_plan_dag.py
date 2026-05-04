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
    StepCriterion,
    ProbeResult,
    REVERSIBILITY_BLOCK_THRESHOLD,
    REVERSIBILITY_REVIEW_THRESHOLD,
    _REFEREE_AGREEMENT_THRESHOLD,
    auto_close_barriers,
    build_dag,
    evaluate_step_output,
    execute_fan_out,
    execute_step,
    format_dag,
    load_dag,
    save_dag,
    save_probe_result,
    save_step_evaluation,
    update_step,
    DAG_TEMPLATES,
    _compute_evaluator_votes,
    _compute_agreement,
    _estimate_reversibility,
    _evaluate_syntax,
    _evaluate_execution,
    _evaluate_claim,
    _evaluate_risk,
    _evaluate_disagreement,
    _evaluation_to_verifier_status,
    _post_execution_bridge,
    _eval_artifact_field_check,
    _eval_command_exit,
    _eval_human_review,
    _compare_field,
    _navigate_field,
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


class ReversibilityGradientTest(unittest.TestCase):
    """Unit tests for _estimate_reversibility and the pre-execution gate."""

    def _make_step(self, owner_role="claude-planner", permission_mode="read_only",
                   input_artifacts=None):
        from hivemind.plan_dag import _step
        s = _step("s", "sequential", [], owner_role, [],
                  permission_mode=permission_mode, status="pending")
        s.input_artifacts = input_artifacts or []
        return s

    # --- estimation ---

    def test_default_read_only_step_is_fully_reversible(self):
        step = self._make_step()
        score, factors = _estimate_reversibility(step, Path("/nonexistent_root"))
        self.assertEqual(score, 1.0)
        self.assertEqual(factors, [])

    def test_workspace_write_permission_reduces_score(self):
        step = self._make_step(permission_mode="workspace_write_with_policy")
        score, factors = _estimate_reversibility(step, Path("/nonexistent_root"))
        self.assertLess(score, 1.0)
        self.assertTrue(any("permission" in f for f in factors))

    def test_codex_executor_role_reduces_score(self):
        step = self._make_step(owner_role="codex-executor",
                               permission_mode="workspace_write_with_policy")
        score, _ = _estimate_reversibility(step, Path("/nonexistent_root"))
        # baseline 0.5 + permission penalty -0.3 = 0.2
        self.assertLessEqual(score, 0.3)

    def test_destructive_pattern_rm_rf_reduces_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "handoff.yaml"
            artifact.write_text("command: rm -rf /build/output")
            step = self._make_step(input_artifacts=["handoff.yaml"])
            score, factors = _estimate_reversibility(step, root)
            self.assertLess(score, 1.0)
            self.assertTrue(any("destructive_pattern" in f for f in factors))

    def test_destructive_pattern_drop_table_reduces_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "plan.sql"
            artifact.write_text("DROP TABLE users;")
            step = self._make_step(input_artifacts=["plan.sql"])
            score, factors = _estimate_reversibility(step, root)
            self.assertLess(score, 1.0)
            self.assertIn("destructive_pattern:drop_table", factors)

    def test_missing_artifact_does_not_crash(self):
        step = self._make_step(input_artifacts=["missing_file.yaml"])
        score, _ = _estimate_reversibility(step, Path("/nonexistent_root"))
        # Should still return a valid score without crashing
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)

    def test_score_clamped_between_zero_and_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Multiple destructive patterns in one artifact
            artifact = root / "script.sh"
            artifact.write_text("rm -rf /data\nDROP DATABASE prod;\nshutil.rmtree(path)")
            step = self._make_step(owner_role="codex-executor",
                                   permission_mode="workspace_write_with_policy",
                                   input_artifacts=["script.sh"])
            score, _ = _estimate_reversibility(step, root)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    # --- reversibility stored on PlanStep ---

    def test_default_reversibility_fields_on_planstep(self):
        dag = build_dag("run_rv1", "task", "implementation")
        step = dag.by_id("planner")
        self.assertEqual(step.reversibility, 1.0)
        self.assertEqual(step.reversibility_source, "default")

    def test_reversibility_persists_through_save_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "rv persist")
            dag = build_dag(paths.run_id, "rv persist", "review")
            step = dag.by_id("context")
            step.reversibility = 0.25
            step.reversibility_source = "declared"
            save_dag(root, dag)
            loaded = load_dag(root, paths.run_id)
            ls = loaded.by_id("context")
            self.assertAlmostEqual(ls.reversibility, 0.25)
            self.assertEqual(ls.reversibility_source, "declared")

    # --- pre-execution gate ---

    def test_execute_step_estimates_reversibility_when_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "rv estimate")
            dag = build_dag(paths.run_id, "rv estimate", "implementation")
            step = dag.by_id("verify")
            self.assertEqual(step.reversibility_source, "default")
            execute_step(root, dag, "verify", execute=False)
            self.assertEqual(step.reversibility_source, "estimated")

    def test_execute_step_reestimates_stale_estimated_reversibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "rv stale estimate")
            dag = build_dag(paths.run_id, "rv stale estimate", "implementation")
            step = dag.by_id("executor")
            step.reversibility = 0.95
            step.reversibility_source = "estimated"
            step.reversibility_factors = []
            paths.handoff.write_text("command: rm -rf /tmp/build-output\n", encoding="utf-8")

            result = execute_step(root, dag, "executor", execute=False, force=False)

            self.assertEqual(result["status"], "reversibility_gate")
            self.assertLess(step.reversibility, REVERSIBILITY_BLOCK_THRESHOLD)
            self.assertIn("destructive_pattern:rm_recursive_force", result["reversibility_factors"])

    def test_declared_reversibility_is_not_overwritten_by_estimator(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "rv declared")
            dag = build_dag(paths.run_id, "rv declared", "implementation")
            step = dag.by_id("executor")
            step.reversibility = 0.8
            step.reversibility_source = "declared"
            paths.handoff.write_text("command: rm -rf /tmp/build-output\n", encoding="utf-8")

            result = execute_step(root, dag, "executor", execute=False, force=False)

            self.assertNotEqual(result.get("status"), "reversibility_gate")
            self.assertEqual(step.reversibility, 0.8)
            self.assertEqual(step.reversibility_source, "declared")

    def test_execute_step_blocks_irreversible_step_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "rv block")
            dag = build_dag(paths.run_id, "rv block", "implementation")
            step = dag.by_id("verify")
            step.reversibility = 0.05   # below REVERSIBILITY_BLOCK_THRESHOLD
            step.reversibility_source = "declared"
            result = execute_step(root, dag, "verify", execute=False, force=False)
            self.assertFalse(result.get("ok"))
            self.assertEqual(result["status"], "reversibility_gate")
            self.assertAlmostEqual(result["reversibility"], 0.05)
            self.assertEqual(result["reversibility_source"], "declared")
            self.assertIn("reversibility_factors", result)

    def test_execute_step_force_bypasses_reversibility_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "rv force")
            dag = build_dag(paths.run_id, "rv force", "implementation")
            step = dag.by_id("verify")
            step.reversibility = 0.05
            step.reversibility_source = "declared"
            result = execute_step(root, dag, "verify", execute=False, force=True)
            # Should proceed past the gate (may complete or skip, not "reversibility_gate")
            self.assertNotEqual(result.get("status"), "reversibility_gate")

    def test_execute_step_gate_releases_lease(self):
        """After reversibility gate blocks, no lease file should remain."""
        from hivemind.dag_state import STEP_LEASES_DIR
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "rv lease release")
            dag = build_dag(paths.run_id, "rv lease release", "implementation")
            step = dag.by_id("verify")
            step.reversibility = 0.05
            step.reversibility_source = "declared"
            execute_step(root, dag, "verify", execute=False, force=False)
            lease_file = paths.run_dir / STEP_LEASES_DIR / "verify.json"
            self.assertFalse(lease_file.exists())

    def test_fan_out_reports_reversibility_gate_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "rv fanout gate")
            dag = build_dag(paths.run_id, "rv fanout gate", "implementation")
            for sid in ("context", "diff_review", "barrier_context", "planner"):
                update_step(dag, sid, status="completed")
            step = dag.by_id("executor")
            step.reversibility = 0.95
            step.reversibility_source = "estimated"
            paths.handoff.write_text("command: rm -rf /tmp/build-output\n", encoding="utf-8")

            result = execute_fan_out(root, dag, execute=False)

            gates = result.get("reversibility_gates", [])
            self.assertEqual(len(gates), 1)
            self.assertEqual(gates[0]["step_id"], "executor")
            self.assertIn("destructive_pattern:rm_recursive_force", gates[0]["factors"])

    # --- evaluate_risk integration ---

    def test_risk_elevates_to_high_on_low_reversibility(self):
        from hivemind.plan_dag import _step
        step = _step("s", "sequential", [], "local-context-compressor", [], status="pending")
        step.reversibility = 0.05
        step.reversibility_source = "estimated"
        result = _evaluate_risk(step)
        self.assertEqual(result["risk_level"], "high")
        self.assertIn("low_reversibility", result["risk_factors"])

    def test_risk_elevates_to_medium_on_medium_reversibility(self):
        from hivemind.plan_dag import _step
        step = _step("s", "sequential", [], "local-context-compressor", [], status="pending")
        step.reversibility = 0.2
        step.reversibility_source = "estimated"
        result = _evaluate_risk(step)
        self.assertEqual(result["risk_level"], "medium")
        self.assertIn("medium_reversibility", result["risk_factors"])

    def test_risk_not_elevated_when_reversibility_source_is_default(self):
        """Default source means estimation hasn't run yet; risk evaluator ignores it."""
        from hivemind.plan_dag import _step
        step = _step("s", "sequential", [], "local-context-compressor", [], status="pending")
        # reversibility=1.0 (default) and reversibility_source="default"
        result = _evaluate_risk(step)
        self.assertNotIn("low_reversibility", result["risk_factors"])
        self.assertNotIn("medium_reversibility", result["risk_factors"])


class EvaluationProtocolBridgeTest(unittest.TestCase):
    """Tests for the evaluation-to-protocol bridge (_post_execution_bridge)."""

    def _make_approved_decision(self, root, paths, dag, step_id="planner"):
        from hivemind.protocol import (
            build_execution_intent, cast_vote, check_intent,
            decide_intent, save_intent,
        )
        intent = build_execution_intent(root, dag, step_id, execute=True)
        save_intent(root, intent)
        check_intent(root, paths.run_id, intent.intent_id)
        cast_vote(root, paths.run_id, intent.intent_id,
                  voter_role="verifier", vote="approve")
        cast_vote(root, paths.run_id, intent.intent_id,
                  voter_role="independent-reviewer", vote="approve")
        decide_intent(root, paths.run_id, intent.intent_id)
        return intent

    def test_verifier_status_mapping(self):
        self.assertEqual(_evaluation_to_verifier_status("accept"), "passed")
        self.assertEqual(_evaluation_to_verifier_status("retry"), "low_confidence")
        self.assertEqual(_evaluation_to_verifier_status("add_review"), "review_required")
        self.assertEqual(_evaluation_to_verifier_status("escalate"), "flagged")
        self.assertEqual(_evaluation_to_verifier_status("referee"), "conflict")
        self.assertEqual(_evaluation_to_verifier_status("block"), "blocked")
        self.assertEqual(_evaluation_to_verifier_status("skip"), "skipped")
        self.assertEqual(_evaluation_to_verifier_status("unknown"), "not_run")

    def test_bridge_creates_proof_when_approved_decision_exists(self):
        from hivemind.protocol import proof_path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bridge proof test")
            dag = build_dag(paths.run_id, "bridge proof test", "implementation")
            save_dag(root, dag)
            update_step(dag, "planner", status="completed")
            intent = self._make_approved_decision(root, paths, dag, "planner")

            step = dag.by_id("planner")
            evaluation = {"recommended_action": "accept", "confidence": 0.9,
                          "risk_level": "low", "evaluator_agreement": 1.0}
            _post_execution_bridge(root, dag, step, evaluation, [])

            ppath = proof_path(root, paths.run_id, intent.intent_id)
            self.assertTrue(ppath.exists(), "proof file should be written")
            import json
            proof = json.loads(ppath.read_text())
            self.assertEqual(proof["verifier_status"], "passed")

    def test_bridge_sets_verifier_status_from_recommended_action(self):
        from hivemind.protocol import proof_path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bridge status test")
            dag = build_dag(paths.run_id, "bridge status test", "implementation")
            save_dag(root, dag)
            update_step(dag, "planner", status="completed")
            intent = self._make_approved_decision(root, paths, dag, "planner")

            step = dag.by_id("planner")
            evaluation = {"recommended_action": "add_review", "confidence": 0.5,
                          "risk_level": "high", "evaluator_agreement": 0.6}
            _post_execution_bridge(root, dag, step, evaluation, [])

            ppath = proof_path(root, paths.run_id, intent.intent_id)
            proof = json.loads(ppath.read_text())
            self.assertEqual(proof["verifier_status"], "review_required")

    def test_bridge_noop_when_no_approved_decision(self):
        from hivemind.protocol import proof_path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bridge noop test")
            dag = build_dag(paths.run_id, "bridge noop test", "implementation")
            save_dag(root, dag)
            update_step(dag, "planner", status="completed")

            step = dag.by_id("planner")
            evaluation = {"recommended_action": "accept", "evaluator_agreement": 1.0}
            # Should not raise even with no decision present
            _post_execution_bridge(root, dag, step, evaluation, [])

            # No proof file should exist since no intent was created
            proofs_dir = root / ".runs" / paths.run_id / "execution_proofs"
            proof_files = list(proofs_dir.glob("*.json")) if proofs_dir.exists() else []
            self.assertEqual(len(proof_files), 0,
                             "no proof should be created when no approved decision exists")

    def test_bridge_casts_needs_referee_vote_on_low_agreement(self):
        from hivemind.protocol import load_votes
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bridge referee test")
            dag = build_dag(paths.run_id, "bridge referee test", "implementation")
            save_dag(root, dag)
            update_step(dag, "planner", status="completed")
            intent = self._make_approved_decision(root, paths, dag, "planner")

            step = dag.by_id("planner")
            low_agreement = max(0.0, _REFEREE_AGREEMENT_THRESHOLD - 0.1)
            evaluation = {"recommended_action": "accept", "confidence": 0.8,
                          "risk_level": "low", "evaluator_agreement": low_agreement}
            _post_execution_bridge(root, dag, step, evaluation, [])

            votes = load_votes(root, paths.run_id, intent.intent_id)
            referee_votes = [v for v in votes if v.vote == "needs_referee"]
            self.assertTrue(len(referee_votes) >= 1,
                            "needs_referee vote should be cast on low evaluator agreement")

    def test_bridge_casts_needs_referee_vote_on_zero_agreement(self):
        from hivemind.protocol import load_votes
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bridge zero agreement test")
            dag = build_dag(paths.run_id, "bridge zero agreement test", "implementation")
            save_dag(root, dag)
            update_step(dag, "planner", status="completed")
            intent = self._make_approved_decision(root, paths, dag, "planner")

            step = dag.by_id("planner")
            evaluation = {"recommended_action": "accept", "confidence": 0.2,
                          "risk_level": "medium", "evaluator_agreement": 0.0}
            _post_execution_bridge(root, dag, step, evaluation, [])

            votes = load_votes(root, paths.run_id, intent.intent_id)
            referee_votes = [v for v in votes if v.vote == "needs_referee"]
            self.assertTrue(referee_votes,
                            "needs_referee vote should be cast on zero evaluator agreement")
            self.assertEqual(referee_votes[-1].confidence, 0.0)

    def test_bridge_casts_needs_referee_vote_on_referee_action(self):
        from hivemind.protocol import load_votes
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bridge referee action test")
            dag = build_dag(paths.run_id, "bridge referee action test", "implementation")
            save_dag(root, dag)
            update_step(dag, "planner", status="completed")
            intent = self._make_approved_decision(root, paths, dag, "planner")

            step = dag.by_id("planner")
            evaluation = {"recommended_action": "referee", "confidence": 0.6,
                          "risk_level": "medium", "evaluator_agreement": 0.8,
                          "escalation_reason": "disagreement_count=3>=2"}
            _post_execution_bridge(root, dag, step, evaluation, [])

            votes = load_votes(root, paths.run_id, intent.intent_id)
            referee_votes = [v for v in votes if v.vote == "needs_referee"]
            self.assertTrue(len(referee_votes) >= 1,
                            "needs_referee vote should be cast when action=referee")

    def test_evaluation_complete_ledger_event_emitted(self):
        from hivemind.workloop import read_execution_ledger
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "eval complete event")
            dag = build_dag(paths.run_id, "eval complete event", "implementation")
            save_dag(root, dag)
            execute_step(root, dag, "verify", execute=False)
            records = read_execution_ledger(root, paths.run_id)
            events = [r["event"] for r in records]
            self.assertIn("evaluation_complete", events,
                          "evaluation_complete should appear in ledger after execute_step")


class ProbeStepTest(unittest.TestCase):
    """Tests for typed StepCriterion, ProbeResult, and probe step execution."""

    def _probe_step(self, criteria=None, owner_role="harness", on_failure="stop"):
        from hivemind.plan_dag import _step
        s = _step("probe_check", "probe", [], owner_role, [],
                  permission_mode="read_only", status="pending")
        s.typed_criteria = criteria or []
        s.on_failure = on_failure
        return s

    # --- StepCriterion schema ---

    def test_step_criterion_defaults(self):
        c = StepCriterion(criterion_type="artifact_field_check", criterion_value="status == completed")
        self.assertIsNone(c.evaluator)
        self.assertEqual(c.timeout, 60)
        self.assertEqual(c.on_failure, "block")

    def test_typed_criteria_field_default_empty(self):
        dag = build_dag("run_probe_default", "task", "implementation")
        step = dag.by_id("planner")
        self.assertEqual(step.typed_criteria, [])

    def test_typed_criteria_persists_through_save_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "probe persist")
            dag = build_dag(paths.run_id, "probe persist", "review")
            step = dag.by_id("context")
            step.kind = "probe"
            step.typed_criteria = [
                StepCriterion(criterion_type="command_exit", criterion_value="echo ok",
                              timeout=30, on_failure="warn"),
            ]
            save_dag(root, dag)
            loaded = load_dag(root, paths.run_id)
            ls = loaded.by_id("context")
            self.assertEqual(len(ls.typed_criteria), 1)
            self.assertIsInstance(ls.typed_criteria[0], StepCriterion)
            self.assertEqual(ls.typed_criteria[0].criterion_type, "command_exit")
            self.assertEqual(ls.typed_criteria[0].timeout, 30)

    # --- Field navigation and comparison ---

    def test_navigate_field_simple_key(self):
        data = {"status": "completed", "confidence": 0.9}
        self.assertEqual(_navigate_field(data, "status"), "completed")

    def test_navigate_field_nested(self):
        data = {"output": {"parsed": {"confidence": 0.85}}}
        self.assertEqual(_navigate_field(data, "output.parsed.confidence"), 0.85)

    def test_navigate_field_missing_returns_none(self):
        data = {"status": "completed"}
        self.assertIsNone(_navigate_field(data, "output.missing"))

    def test_compare_field_string_equal(self):
        self.assertTrue(_compare_field("completed", "==", "completed"))
        self.assertFalse(_compare_field("failed", "==", "completed"))

    def test_compare_field_numeric_gte(self):
        self.assertTrue(_compare_field(0.9, ">=", "0.7"))
        self.assertFalse(_compare_field(0.5, ">=", "0.7"))

    def test_compare_field_exists(self):
        self.assertTrue(_compare_field("anything", "exists", ""))
        self.assertFalse(_compare_field(None, "exists", ""))

    # --- artifact_field_check evaluator ---

    def test_eval_artifact_field_check_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "afc pass")
            artifact = root / ".runs" / paths.run_id / "result.json"
            artifact.write_text(json.dumps({"status": "completed", "confidence": 0.9}))
            step = self._probe_step()
            step.input_artifacts = ["result.json"]
            criterion = StepCriterion(criterion_type="artifact_field_check",
                                      criterion_value="status == completed")
            r = _eval_artifact_field_check(root, paths.run_id, step, criterion)
            self.assertTrue(r.passed)
            self.assertEqual(r.status, "completed")
            self.assertEqual(r.next_action, "accept")

    def test_eval_artifact_field_check_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "afc fail")
            artifact = root / ".runs" / paths.run_id / "result.json"
            artifact.write_text(json.dumps({"status": "failed"}))
            step = self._probe_step()
            step.input_artifacts = ["result.json"]
            criterion = StepCriterion(criterion_type="artifact_field_check",
                                      criterion_value="status == completed",
                                      on_failure="block")
            r = _eval_artifact_field_check(root, paths.run_id, step, criterion)
            self.assertFalse(r.passed)
            self.assertEqual(r.status, "failed")
            self.assertEqual(r.failure_disposition, "block")

    def test_eval_artifact_field_check_numeric_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "afc numeric")
            artifact = root / ".runs" / paths.run_id / "result.json"
            artifact.write_text(json.dumps({"confidence": 0.45}))
            step = self._probe_step()
            step.input_artifacts = ["result.json"]
            criterion = StepCriterion(criterion_type="artifact_field_check",
                                      criterion_value="confidence >= 0.7")
            r = _eval_artifact_field_check(root, paths.run_id, step, criterion)
            self.assertFalse(r.passed)
            self.assertIn("0.45", r.observed)

    def test_eval_artifact_field_check_no_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "afc no artifact")
            step = self._probe_step()
            criterion = StepCriterion(criterion_type="artifact_field_check",
                                      criterion_value="status == completed")
            r = _eval_artifact_field_check(root, paths.run_id, step, criterion)
            self.assertFalse(r.passed)
            self.assertIn("no_artifact", r.observed)

    # --- command_exit evaluator ---

    def test_eval_command_exit_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "cmd pass")
            step = self._probe_step()
            criterion = StepCriterion(criterion_type="command_exit",
                                      criterion_value="true")
            r = _eval_command_exit(root, paths.run_id, step, criterion)
            self.assertTrue(r.passed)
            self.assertEqual(r.observed, "0")

    def test_eval_command_exit_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "cmd fail")
            step = self._probe_step()
            criterion = StepCriterion(criterion_type="command_exit",
                                      criterion_value="false")
            r = _eval_command_exit(root, paths.run_id, step, criterion)
            self.assertFalse(r.passed)
            self.assertNotEqual(r.observed, "0")

    # --- human_review evaluator ---

    def test_eval_human_review_pending_without_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "human pending")
            step = self._probe_step()
            criterion = StepCriterion(criterion_type="human_review",
                                      criterion_value="Please verify the output.")
            r = _eval_human_review(root, paths.run_id, step, criterion)
            self.assertIsNone(r.passed)
            self.assertEqual(r.next_action, "override_pending")
            self.assertEqual(r.status, "failed")

    def test_eval_human_review_passes_with_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "human override")
            probes_dir = root / ".runs" / paths.run_id / "step_probes"
            probes_dir.mkdir(parents=True, exist_ok=True)
            override = probes_dir / "probe_check_override.json"
            override.write_text(json.dumps({"approved": True, "notes": "LGTM"}))
            step = self._probe_step()
            criterion = StepCriterion(criterion_type="human_review",
                                      criterion_value="Review output.")
            r = _eval_human_review(root, paths.run_id, step, criterion)
            self.assertTrue(r.passed)
            self.assertEqual(r.next_action, "accept")
            self.assertIn("LGTM", r.evidence)

    # --- probe step execution ---

    def test_probe_step_trivially_passes_no_criteria(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "probe trivial")
            dag = build_dag(paths.run_id, "probe trivial", "implementation")
            save_dag(root, dag)
            step = dag.by_id("verify")
            step.kind = "probe"
            step.typed_criteria = []
            result = execute_step(root, dag, "verify", execute=False)
            self.assertTrue(result.get("ok"))
            self.assertEqual(result["status"], "completed")
            self.assertTrue(result.get("probe_passed"))
            self.assertEqual(result.get("probe_action"), "accept")

    def test_probe_step_passes_with_command_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "probe cmd pass")
            dag = build_dag(paths.run_id, "probe cmd pass", "implementation")
            save_dag(root, dag)
            step = dag.by_id("verify")
            step.kind = "probe"
            step.typed_criteria = [
                StepCriterion(criterion_type="command_exit", criterion_value="true")
            ]
            result = execute_step(root, dag, "verify", execute=False)
            self.assertTrue(result.get("ok"))
            self.assertEqual(result["probe_action"], "accept")

    def test_probe_step_fails_with_failing_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "probe cmd fail")
            dag = build_dag(paths.run_id, "probe cmd fail", "implementation")
            save_dag(root, dag)
            step = dag.by_id("verify")
            step.kind = "probe"
            step.on_failure = "stop"
            step.typed_criteria = [
                StepCriterion(criterion_type="command_exit", criterion_value="false",
                              on_failure="block")
            ]
            result = execute_step(root, dag, "verify", execute=False)
            self.assertFalse(result.get("ok"))
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["probe_action"], "block")

    def test_probe_step_warn_still_completes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "probe warn")
            dag = build_dag(paths.run_id, "probe warn", "implementation")
            save_dag(root, dag)
            step = dag.by_id("verify")
            step.kind = "probe"
            step.typed_criteria = [
                StepCriterion(criterion_type="command_exit", criterion_value="false",
                              on_failure="warn")
            ]
            result = execute_step(root, dag, "verify", execute=False)
            self.assertTrue(result.get("ok"))
            self.assertEqual(result["status"], "completed")

    def test_probe_step_downstream_blocked_when_probe_fails(self):
        """When probe step fails, steps that depend on it cannot run."""
        dag = build_dag("run_probe_block", "task", "implementation")
        # Inject a probe step at the barrier position
        step = dag.by_id("verify")
        step.kind = "probe"
        step.status = "failed"
        step.on_failure = "stop"
        # close step should be blocked (depends on memory → verify chain)
        runnable = {s.step_id for s in dag.runnable()}
        self.assertNotIn("close", runnable)

    def test_probe_result_artifact_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "probe artifact")
            dag = build_dag(paths.run_id, "probe artifact", "implementation")
            save_dag(root, dag)
            step = dag.by_id("verify")
            step.kind = "probe"
            step.typed_criteria = [
                StepCriterion(criterion_type="command_exit", criterion_value="true")
            ]
            execute_step(root, dag, "verify", execute=False)
            probe_file = root / ".runs" / paths.run_id / "step_probes" / "verify.json"
            self.assertTrue(probe_file.exists(), "probe result artifact should be written")
            data = json.loads(probe_file.read_text())
            self.assertIn("passed", data)
            self.assertIn("next_action", data)
            self.assertIn("confidence", data)
            self.assertIn("evidence", data)

    def test_probe_step_emits_evaluation_complete_ledger_event(self):
        from hivemind.workloop import read_execution_ledger
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "probe ledger event")
            dag = build_dag(paths.run_id, "probe ledger event", "implementation")
            save_dag(root, dag)
            step = dag.by_id("verify")
            step.kind = "probe"
            step.typed_criteria = [
                StepCriterion(criterion_type="command_exit", criterion_value="true")
            ]
            execute_step(root, dag, "verify", execute=False)
            records = read_execution_ledger(root, paths.run_id)
            events = [r["event"] for r in records]
            self.assertIn("evaluation_complete", events)
            self.assertIn("step_completed", events)

    def test_save_probe_result_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "probe save roundtrip")
            result = ProbeResult(
                schema_version=1, step_id="s1", run_id=paths.run_id,
                criterion_type="command_exit", criterion_value="true",
                status="completed", passed=True,
                observed="0", expected="0", evidence="exit_code=0",
                confidence=1.0, failure_disposition="block",
                next_action="accept", evaluated_at="2026-01-01T00:00:00",
            )
            path = save_probe_result(root, paths.run_id, "s1", result)
            self.assertTrue(path.exists())
            data = json.loads(path.read_text())
            self.assertEqual(data["passed"], True)
            self.assertEqual(data["status"], "completed")
            self.assertEqual(data["next_action"], "accept")


if __name__ == "__main__":
    unittest.main()
