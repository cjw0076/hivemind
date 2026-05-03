from pathlib import Path
import json
import tempfile
import unittest

import yaml

from hivemind.harness import (
    RunPaths,
    agent_roles_report,
    auto_loop,
    build_context_pack_for_role,
    close_gap_loop,
    create_run,
    debate_topic,
    flow_advance,
    invoke_external_agent,
    llm_checker_report,
    local_benchmark_report,
    local_model_profile,
    policy_report,
    set_agent_status,
)
from hivemind.run_validation import validate_run_artifacts
from unittest.mock import patch


class ProductionHardeningTest(unittest.TestCase):
    def test_policy_report_writes_default_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = policy_report(root, write=True)

            self.assertEqual(report["status"], "ready", report["issues"])
            self.assertTrue((root / ".hivemind" / "policy.yaml").exists())
            self.assertIn("codex.executor", report["policy"]["roles"])

    def test_agent_roles_include_user_claude_codex_and_local(self) -> None:
        roles = agent_roles_report()["roles"]

        self.assertIn("user.director", roles)
        self.assertIn("claude.planner", roles)
        self.assertIn("codex.executor", roles)
        self.assertIn("local.context", roles)
        self.assertIn("hive.verifier", roles)
        self.assertIn("hive.product_evaluator", roles)
        self.assertIn("persona.actual_user", roles)

    def test_context_build_writes_agent_specific_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "build context pack", project="Hive Mind")
            policy_report(root, write=True)

            report = build_context_pack_for_role(root, "codex.executor", paths.run_id)

            output = root / report["path"]
            self.assertTrue(output.exists())
            text = output.read_text(encoding="utf-8")
            self.assertIn("forbidden_scope", text)
            self.assertIn("evolution of Single Human Intelligence", text)

    def test_local_model_profile_writes_role_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = local_model_profile(root, write=True)

            self.assertTrue((root / ".hivemind" / "local_model_profile.json").exists())
            self.assertIn("role_assignments", report)
            self.assertIn("models", report)

    def test_policy_fixtures_capture_safe_and_unsafe_danger_modes(self) -> None:
        fixture_root = Path("tests/fixtures/policies")
        safe = yaml.safe_load((fixture_root / "default_policy.yaml").read_text(encoding="utf-8"))
        unsafe = yaml.safe_load((fixture_root / "invalid_danger_mode.yaml").read_text(encoding="utf-8"))

        self.assertFalse(safe["danger_modes"]["allowed"])
        self.assertTrue(unsafe["danger_modes"]["allowed"])

    def test_local_backend_fixtures_use_backend_protocol(self) -> None:
        fixture_root = Path("tests/fixtures/local_backends")
        available = json.loads((fixture_root / "ollama_available.json").read_text(encoding="utf-8"))
        unavailable = json.loads((fixture_root / "no_backend.json").read_text(encoding="utf-8"))

        self.assertEqual(available["protocol"], "hive-local-backend-v1")
        self.assertEqual(available["backends"]["ollama"]["status"], "available")
        self.assertIn("phi4-mini", unavailable["missing_recommended_models"])

    def test_debate_prepare_only_writes_barrier_and_convergence_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = debate_topic(root, "choose safer release gate", participants=["claude", "gemini"], execute=False)

            self.assertEqual(report["barrier"], "all_participants_processed_before_convergence")
            self.assertTrue((root / ".runs" / report["run_id"] / "debate_convergence.md").exists())
            self.assertTrue(all(round_report["barrier"] == "complete" for round_report in report["rounds"]))

    def test_gap_closure_writes_learning_operator_loop_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "close hive mind gaps", project="Hive Mind")
            report = close_gap_loop(root, paths.run_id)

            self.assertEqual(report["status"], "ready")
            for name in [
                "memory_context",
                "semantic_verification",
                "handoff_quality",
                "routing_evidence",
                "conflict_set",
                "operator_decisions",
            ]:
                self.assertTrue((root / report["artifacts"][name]).exists(), name)

    def test_prepared_provider_result_uses_expanded_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider schema", project="Hive Mind")

            result_path = invoke_external_agent(root, "claude", "planner", run_id=paths.run_id, execute=False)
            self.assertTrue(result_path.exists())
            report = validate_run_artifacts(paths.run_dir, root)

            self.assertEqual(report["verdict"], "pass", report["issues"])

    def test_llm_checker_adapter_writes_plan_without_requiring_install(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = llm_checker_report(root, write=True)

            self.assertTrue((root / ".hivemind" / "llm_checker_report.json").exists())
            self.assertIn("github.com/Pavelevich/llm-checker", report["source"]["repo"])
            self.assertIn("recommend", report["commands"])

    def test_local_benchmark_writes_results_and_profile_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "hivemind.harness.benchmark_local_model",
                return_value={
                    "model": "qwen3:1.7b",
                    "role": "json_normalizer",
                    "runtime": "test",
                    "status": "completed",
                    "latency_ms": 123,
                    "json_valid": True,
                    "schema_valid": True,
                    "parsed": {"ok": True, "normalized": {"status": "ok"}, "confidence": 0.75},
                    "raw_response": '{"ok": true, "normalized": {"status": "ok"}, "confidence": 0.75}',
                    "parse_error": "",
                    "error": "",
                },
            ):
                report = local_benchmark_report(root, models=["qwen3:1.7b"], roles=["json_normalizer"], write=True)

            self.assertTrue((root / ".hivemind" / "local_benchmark.json").exists())
            self.assertEqual(report["json_validity"], 1.0)
            self.assertEqual(report["roles_tested"], ["json_normalizer"])
            self.assertEqual(report["results"][0]["latency_ms"], 123)

    def test_auto_loop_dry_run_only_writes_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = prepare_run_until_verification(root)

            report = auto_loop(root, paths.run_id, max_steps=3, execute=False, allowed_actions=["verify"])

            self.assertEqual(report["mode"], "dry_run")
            self.assertEqual(report["status"], "planned")
            self.assertEqual(report["proposed_steps"][0]["action"], "verify")
            self.assertEqual(report["blocked_steps"][0]["block_reason"], "dry_run_requires_--execute")
            self.assertTrue((paths.artifacts / "auto_loop_plan.json").exists())
            self.assertIn("not_run", (paths.run_dir / "verification.yaml").read_text(encoding="utf-8"))

    def test_auto_loop_execute_requires_allowlisted_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = prepare_run_until_verification(root)

            blocked = auto_loop(root, paths.run_id, execute=True, allowed_actions=[])
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual(blocked["blocked_steps"][0]["block_reason"], "action_not_allowlisted")

            executed = auto_loop(root, paths.run_id, execute=True, allowed_actions=["verify"])
            self.assertEqual(executed["executed_steps"][0]["action"], "verify")
            self.assertNotIn("not_run", (paths.run_dir / "verification.yaml").read_text(encoding="utf-8"))
            validation = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(validation["verdict"], "pass", validation["issues"])

    def test_auto_loop_blocks_external_provider_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider should not auto execute", project="Hive Mind")
            (paths.run_dir / "routing_plan.json").write_text('{"intent":"implementation","actions":[]}\n', encoding="utf-8")
            set_agent_status(paths, "local-context-compressor", "completed")

            report = auto_loop(root, paths.run_id, execute=True, allowed_actions=["verify"])

            self.assertEqual(report["proposed_steps"][0]["action"], "provider-invoke")
            self.assertEqual(report["blocked_steps"][0]["block_reason"], "provider_cli_execution_blocked")

    def test_auto_loop_stops_after_failed_local_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "local action failure", project="Hive Mind")
            (paths.run_dir / "routing_plan.json").write_text('{"intent":"implementation","actions":[]}\n', encoding="utf-8")

            with patch("hivemind.harness.run_worker", side_effect=RuntimeError("local backend unavailable")):
                report = auto_loop(root, paths.run_id, max_steps=3, execute=True, allowed_actions=["local-context"])

            self.assertEqual(len(report["executed_steps"]), 1)
            self.assertEqual(report["executed_steps"][0]["result"], "failed")
            self.assertEqual(report["blocked_steps"][0]["block_reason"], "executed_action_failed")
            self.assertEqual(report["status"], "blocked")

    def test_flow_advance_prepares_workflow_barrier_without_provider_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = flow_advance(root, task="한글 입력 버그 고치고 테스트 추가", complexity="fast")
            run_dir = root / ".runs" / report["run_id"]

            self.assertEqual(report["mode"], "prepare_only")
            self.assertEqual(report["status"], "waiting_for_local_context")
            self.assertTrue((run_dir / "routing_plan.json").exists())
            self.assertTrue((run_dir / "society_plan.json").exists())
            self.assertTrue((run_dir / "artifacts" / "workflow_state.json").exists())
            self.assertTrue((run_dir / "agents" / "claude" / "planner_result.yaml").exists())
            self.assertTrue((run_dir / "agents" / "codex" / "executor_result.yaml").exists())
            claude_result = yaml.safe_load((run_dir / "agents" / "claude" / "planner_result.yaml").read_text(encoding="utf-8"))
            self.assertEqual(claude_result["status"], "prepared")
            validation = validate_run_artifacts(run_dir, root)
            self.assertEqual(validation["verdict"], "pass", validation["issues"])

    def test_flow_advance_injects_completed_local_context_into_provider_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            worker_output = {
                "runtime": "ollama",
                "model": "qwen3:1.7b",
                "raw": '{"summary": "LOCAL-CONTEXT-SENTINEL"}',
                "parsed": {
                    "summary": "LOCAL-CONTEXT-SENTINEL",
                    "key_decisions": [],
                    "open_questions": [],
                    "constraints": [],
                    "risks": [],
                    "handoff_notes": [],
                    "confidence": 0.9,
                    "should_escalate": False,
                    "escalation_reason": "",
                },
            }

            with patch("hivemind.harness.run_worker", return_value=worker_output):
                report = flow_advance(root, task="build feature", complexity="fast", execute_local=True)

            prompt_path = root / ".runs" / report["run_id"] / "agents" / "claude" / "planner_prompt.md"
            self.assertIn("LOCAL-CONTEXT-SENTINEL", prompt_path.read_text(encoding="utf-8"))


def prepare_run_until_verification(root: Path) -> RunPaths:
    paths = create_run(root, "auto loop verification", project="Hive Mind")
    (paths.run_dir / "routing_plan.json").write_text('{"intent":"implementation","actions":[]}\n', encoding="utf-8")
    set_agent_status(paths, "local-context-compressor", "completed")
    set_agent_status(paths, "claude-planner", "prepared")
    set_agent_status(paths, "codex-executor", "prepared")
    return paths


if __name__ == "__main__":
    unittest.main()
