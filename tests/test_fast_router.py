import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hivemind.harness import (
    ask_router,
    format_orchestration_report,
    format_routing_plan,
    normalize_router_actions,
    orchestrate_prompt,
    score_route_quality,
)


class FastRouterTest(unittest.TestCase):
    def test_normalize_router_actions_accepts_provider_role_pairs(self) -> None:
        actions = normalize_router_actions(
            [
                {"provider": "local/context", "role": "context", "reason": "context"},
                {"provider": "claude/planner", "role": "planner", "reason": "plan"},
            ]
        )

        self.assertEqual(actions[0]["provider"], "local")
        self.assertEqual(actions[0]["role"], "context")
        self.assertEqual(actions[1]["provider"], "claude")
        self.assertEqual(actions[1]["role"], "planner")

    def test_fast_router_uses_heuristic_without_local_llm_start_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = ask_router(root, "smooth operator prompt", complexity="fast")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            events = (plan_path.parent / "events.jsonl").read_text(encoding="utf-8")

            self.assertEqual(plan["route_source"], "heuristic_fast")
            self.assertIn("route_quality", plan)
            self.assertTrue((plan_path.parent / "routing_quality.json").exists())
            self.assertEqual(plan["route_quality"]["verdict"], "review")
            self.assertNotIn('"type": "agent_started"', events)

    def test_routing_plan_includes_operator_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_path = ask_router(root, "간단한 JSON validator 만들어줘", complexity="fast")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            summary = plan["operator_summary"]
            rendered = format_routing_plan(plan)

            self.assertEqual(summary["risk_level"], "medium")
            self.assertEqual(summary["next"]["command"], f"hive flow --run-id {plan['run_id']}")
            self.assertTrue(any(item["path"].endswith("routing_plan.json") for item in summary["expected_artifacts"]))
            self.assertTrue(any(item["path"].endswith("routing_quality.json") for item in summary["expected_artifacts"]))
            self.assertIn("위험도: medium", rendered)
            self.assertIn("다음:", rendered)

    def test_orchestration_report_includes_operator_summary_and_korean_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = orchestrate_prompt(root, "간단한 JSON validator 만들어줘", complexity="fast")
            rendered = format_orchestration_report(report)

            self.assertIn("operator_summary", report)
            self.assertEqual(report["operator_summary"]["risk_level"], "medium")
            self.assertIn("위험도: medium", rendered)
            self.assertIn("예상 산출물:", rendered)

    def test_local_llm_router_prepares_local_worker_without_running_it(self) -> None:
        worker_output = {
            "runtime": "ollama",
            "model": "qwen3:1.7b",
            "raw": "{}",
            "parsed": {
                "intent": "planning",
                "summary": "Plan task",
                "complexity": "default",
                "actions": [
                    {"provider": "local", "role": "context", "reason": "Need context", "execute": False},
                    {"provider": "claude", "role": "planner", "reason": "Need plan", "execute": False},
                ],
                "risks": [],
                "open_questions": [],
                "confidence": 0.8,
                "should_escalate": False,
                "escalation_reason": "",
            },
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("hivemind.harness.run_worker", return_value=worker_output):
                plan_path = ask_router(root, "plan this", complexity="default")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            events = (plan_path.parent / "events.jsonl").read_text(encoding="utf-8")

            self.assertEqual(plan["route_source"], "local_llm")
            self.assertEqual(plan["route_quality"]["risk_level"], "low")
            self.assertNotIn('"worker": "context_compressor"', events)
            self.assertFalse((plan_path.parent / "agents" / "local" / "context_result.yaml").exists())
            self.assertIn("claude/planner_result.yaml", "\n".join(plan["prepared_artifacts"]))

    def test_invalid_local_router_output_records_fallback_quality(self) -> None:
        worker_output = {
            "runtime": "ollama",
            "model": "qwen3:1.7b",
            "raw": "{}",
            "parsed": {},
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("hivemind.harness.run_worker", return_value=worker_output):
                plan_path = ask_router(root, "fix failing cli test", complexity="default")
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            quality = json.loads((plan_path.parent / "routing_quality.json").read_text(encoding="utf-8"))

            self.assertEqual(plan["route_source"], "invalid_local_fallback")
            self.assertTrue(quality["fallback_used"])
            self.assertFalse(quality["schema_valid"])
            self.assertEqual(quality["risk_level"], "high")
            self.assertIn("router_schema_invalid", quality["risks"])
            self.assertEqual(plan["route_quality"]["artifact"], f".runs/{plan['run_id']}/routing_quality.json")

    def test_score_route_quality_passes_valid_local_llm_route(self) -> None:
        quality = score_route_quality(
            prompt="plan this task",
            parsed={
                "intent": "planning",
                "summary": "Plan task",
                "actions": [{"provider": "claude", "role": "planner"}],
                "confidence": 0.9,
                "should_escalate": False,
            },
            validation={"valid": True, "issues": [], "confidence": 0.9, "should_escalate": False, "escalation_reason": ""},
            route_source="local_llm",
            actions=[{"provider": "claude", "role": "planner", "reason": "plan", "execute": False}],
            router_status="completed",
        )

        self.assertEqual(quality["verdict"], "pass")
        self.assertEqual(quality["risk_level"], "low")
        self.assertFalse(quality["risks"])


if __name__ == "__main__":
    unittest.main()
