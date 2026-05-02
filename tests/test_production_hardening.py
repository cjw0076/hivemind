from pathlib import Path
import json
import tempfile
import unittest

import yaml

from hivemind.harness import (
    agent_roles_report,
    build_context_pack_for_role,
    close_gap_loop,
    create_run,
    debate_topic,
    invoke_external_agent,
    llm_checker_report,
    local_benchmark_report,
    local_model_profile,
    policy_report,
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


if __name__ == "__main__":
    unittest.main()
