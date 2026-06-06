from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hivemind.harness import create_run
from hivemind.plan_dag import PlanDAG, PlanStep, build_dag, execute_fan_out


def _parallel_step(step_id: str, owner_role: str, provider: str) -> PlanStep:
    return PlanStep(
        step_id=step_id,
        kind="parallel",
        depends_on=["root"],
        owner_role=owner_role,
        provider_candidates=[provider],
        permission_mode="read_only",
        input_artifacts=[],
        expected_output_artifacts=[],
        acceptance_criteria=["status: prepared or completed"],
        timeout=120,
        retry_policy="once",
        on_failure="skip",
        status="pending",
    )


class FanOutSchedulerTest(unittest.TestCase):
    def test_fan_out_respects_max_parallel_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bounded fanout")
            dag = build_dag(paths.run_id, "bounded fanout", "implementation")

            report = execute_fan_out(root, dag, execute=False, max_parallel=1)

            self.assertEqual(report["mode"], "parallel")
            self.assertEqual(report["max_parallel"], 1)
            self.assertEqual(len(report["dispatched"]), 1)
            self.assertEqual(len(report["deferred_parallel"]), 1)
            self.assertEqual(dag.status_of(report["deferred_parallel"][0]), "pending")
            self.assertNotIn("barrier_context", report["barriers_closed"])

    def test_fan_out_defers_provider_parallel_steps_until_provider_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider parallel deferred")
            dag = PlanDAG(
                schema_version=1,
                run_id=paths.run_id,
                task="provider parallel deferred",
                intent="planning",
                created_at="2026-06-06T20:32:00+09:00",
                steps=[
                    PlanStep(
                        step_id="root",
                        kind="sequential",
                        depends_on=[],
                        owner_role="harness",
                        provider_candidates=[],
                        permission_mode="none",
                        input_artifacts=[],
                        expected_output_artifacts=[],
                        acceptance_criteria=[],
                        timeout=0,
                        retry_policy="none",
                        on_failure="stop",
                        status="completed",
                    ),
                    _parallel_step("local_context", "local-context-compressor", "local"),
                    _parallel_step("provider_planner", "claude-planner", "claude"),
                    PlanStep(
                        step_id="join",
                        kind="barrier",
                        depends_on=["local_context", "provider_planner"],
                        owner_role="harness",
                        provider_candidates=[],
                        permission_mode="none",
                        input_artifacts=[],
                        expected_output_artifacts=[],
                        acceptance_criteria=[],
                        timeout=0,
                        retry_policy="none",
                        on_failure="stop",
                        status="pending",
                    ),
                ],
            )

            with patch("hivemind.harness.invoke_external_agent") as invoke_external:
                report = execute_fan_out(root, dag, execute=False, max_parallel=2)

            invoke_external.assert_not_called()
            self.assertEqual(report["dispatched"], ["local_context"])
            self.assertEqual(report["deferred_unsafe_parallel"], ["provider_planner"])
            self.assertEqual(dag.status_of("provider_planner"), "pending")
            self.assertEqual(dag.status_of("join"), "pending")


if __name__ == "__main__":
    unittest.main()
