from pathlib import Path
import tempfile
import unittest

from memoryos.harness import build_verification, create_run
from memoryos.run_validation import validate_run_artifacts


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


if __name__ == "__main__":
    unittest.main()
