from pathlib import Path
import tempfile
import unittest

from hivemind.harness import (
    agent_roles_report,
    build_context_pack_for_role,
    create_run,
    invoke_external_agent,
    llm_checker_report,
    local_model_profile,
    policy_report,
)
from hivemind.run_validation import validate_run_artifacts


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


if __name__ == "__main__":
    unittest.main()
