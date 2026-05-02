from pathlib import Path
import tempfile
import unittest

from hivemind.harness import RunPaths, create_run, get_current, list_runs, load_run, set_current
from hivemind.run_validation import validate_run_artifacts
from hivemind.utils import is_valid_run_id


class RunIdValidationTest(unittest.TestCase):
    def test_run_id_allows_generated_and_fixture_ids(self) -> None:
        self.assertTrue(is_valid_run_id("run_20260502_153217_56f73f"))
        self.assertTrue(is_valid_run_id("minimal_valid"))
        self.assertTrue(is_valid_run_id("invalid-provider-result"))

    def test_run_id_rejects_path_traversal_and_hidden_paths(self) -> None:
        for value in ["../secret", "run/secret", ".hidden", "bad id", "", "x" * 129]:
            self.assertFalse(is_valid_run_id(value), value)

    def test_load_run_rejects_invalid_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            create_run(root, "safe run", project="Hive Mind")

            with self.assertRaises(ValueError):
                load_run(root, "../outside")

            with self.assertRaises(ValueError):
                set_current(root, "../outside")

            with self.assertRaises(ValueError):
                RunPaths(root=root, run_id="../outside")

    def test_get_current_rejects_invalid_stored_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".runs").mkdir()
            (root / ".runs" / "current").write_text("../outside\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                get_current(root)

    def test_list_runs_skips_invalid_folder_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "safe run", project="Hive Mind")
            bad = root / ".runs" / "bad id"
            bad.mkdir(parents=True, exist_ok=True)
            (bad / "run_state.json").write_text('{"run_id": "bad id", "status": "bad"}', encoding="utf-8")

            run_ids = [item.get("run_id") for item in list_runs(root)]
            self.assertIn(paths.run_id, run_ids)
            self.assertNotIn("bad id", run_ids)

    def test_validate_run_artifacts_rejects_invalid_folder_name(self) -> None:
        fixture_root = Path("tests/fixtures/runs")
        report = validate_run_artifacts(fixture_root / "bad run id", fixture_root)
        self.assertEqual(report["verdict"], "needs_review")
        self.assertFalse(report["checks"]["run_id_format_valid"])


if __name__ == "__main__":
    unittest.main()
