from pathlib import Path
import tempfile
import unittest

from hivemind.harness import build_verification, create_run, set_agent_status
from hivemind.run_validation import validate_run_artifacts


class RunValidationTest(unittest.TestCase):
    def test_minimal_fixture_passes(self) -> None:
        fixture_root = Path("tests/fixtures/runs")
        report = validate_run_artifacts(fixture_root / "minimal_valid", fixture_root)
        self.assertEqual(report["verdict"], "pass", report["issues"])

    def test_complete_minimal_fixture_with_provider_result_passes(self) -> None:
        fixture_root = Path("tests/fixtures/runs")
        report = validate_run_artifacts(fixture_root / "complete_minimal", fixture_root)
        self.assertEqual(report["verdict"], "pass", report["issues"])

    def test_invalid_provider_result_fixture_fails(self) -> None:
        fixture_root = Path("tests/fixtures/runs")
        report = validate_run_artifacts(fixture_root / "invalid_provider_result", fixture_root)
        self.assertEqual(report["verdict"], "needs_review")
        self.assertFalse(report["checks"]["provider_results_schema_valid"])

    def test_created_run_passes_after_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "test run validation", project="Hive Mind")
            self.assertTrue(paths.transcript.exists())
            build_verification(root, paths.run_id)
            report = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(report["verdict"], "pass", report["issues"])

    def test_invalid_memory_draft_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bad memory draft", project="Hive Mind")
            (paths.run_dir / "memory_drafts.json").write_text(
                '{"memory_drafts":[{"type":"bad","content":"","origin":"robot","project":"","confidence":2,"status":"done","raw_refs":[1]}]}',
                encoding="utf-8",
            )
            report = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(report["verdict"], "needs_review")
            self.assertFalse(report["checks"]["memory_drafts_schema_valid"])

    def test_invalid_provider_result_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bad provider result", project="Hive Mind")
            result_path = paths.run_dir / "agents" / "claude" / "planner_result.yaml"
            result_path.write_text('agent: claude\nrole: planner\nstatus: "weird"\n', encoding="utf-8")
            report = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(report["verdict"], "needs_review")
            self.assertFalse(report["checks"]["provider_results_schema_valid"])

    def test_nested_native_provider_result_is_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bad nested provider result", project="Hive Mind")
            result_dir = paths.run_dir / "agents" / "codex" / "native"
            result_dir.mkdir(parents=True, exist_ok=True)
            result_path = result_dir / "passthrough_01_result.yaml"
            result_path.write_text('agent: codex\nrole: native\nstatus: "weird"\n', encoding="utf-8")
            report = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(report["verdict"], "needs_review")
            self.assertFalse(report["checks"]["provider_results_schema_valid"])

    def test_failed_agent_state_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "failed agent state", project="Hive Mind")
            set_agent_status(paths, "local-context-compressor", "failed")
            report = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(report["verdict"], "needs_review")
            self.assertFalse(report["checks"]["agent_states_valid"])

if __name__ == "__main__":
    unittest.main()
