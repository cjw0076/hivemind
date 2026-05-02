from pathlib import Path
import tempfile
import unittest

from memoryos.harness import build_verification, create_run
from memoryos.run_validation import validate_run_artifacts
from memoryos.schema import make_hyperedge, make_memory_object


class RunValidationTest(unittest.TestCase):
    def test_minimal_fixture_passes(self) -> None:
        fixture_root = Path("tests/fixtures/runs")
        report = validate_run_artifacts(fixture_root / "minimal_valid", fixture_root)
        self.assertEqual(report["verdict"], "pass", report["issues"])

    def test_created_run_passes_after_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "test run validation", project="MemoryOS")
            build_verification(root, paths.run_id)
            report = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(report["verdict"], "pass", report["issues"])

    def test_invalid_memory_draft_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "bad memory draft", project="MemoryOS")
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
            paths = create_run(root, "bad provider result", project="MemoryOS")
            result_path = paths.run_dir / "agents" / "claude" / "planner_result.yaml"
            result_path.write_text('agent: claude\nrole: planner\nstatus: "weird"\n', encoding="utf-8")
            report = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(report["verdict"], "needs_review")
            self.assertFalse(report["checks"]["provider_results_schema_valid"])

    def test_memory_object_and_hyperedge_schema(self) -> None:
        memory = make_memory_object("decision", "Keep mos run protocol canonical.", "user", "MemoryOS", ["docs/TODO.md"], 0.9)
        self.assertEqual(memory.status, "draft")
        self.assertEqual(memory.type, "decision")
        hyperedge = make_hyperedge("supports", [memory.id, "node_spec"], "test", confidence=0.8)
        self.assertEqual(hyperedge.members[0], memory.id)
        self.assertEqual(hyperedge.confidence, 0.8)


if __name__ == "__main__":
    unittest.main()
