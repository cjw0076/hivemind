import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import create_run, git_guard_report
from hivemind.workloop import append_execution_ledger


class GitGuardTest(unittest.TestCase):
    def init_git(self, root: Path) -> None:
        subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)

    def stage(self, root: Path, path: str, content: str = "x\n") -> None:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", path], cwd=root, check=True, capture_output=True)

    def test_blocks_staged_files_outside_explicit_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_git(root)
            paths = create_run(root, "guard scope")
            self.stage(root, "README.md")
            self.stage(root, "src/app.py")

            report = git_guard_report(root, paths.run_id, scopes=["src/"])

            self.assertEqual(report["verdict"], "blocked")
            self.assertFalse(report["can_commit"])
            self.assertEqual(report["scoped_files"], ["src/app.py"])
            self.assertEqual(report["out_of_scope_files"], ["README.md"])
            self.assertTrue((paths.run_dir / "git_guard_report.json").exists())

    def test_override_allows_out_of_scope_with_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_git(root)
            paths = create_run(root, "guard override")
            self.stage(root, "README.md")

            report = git_guard_report(root, paths.run_id, scopes=["src/"], approve_out_of_scope=True)

            self.assertEqual(report["verdict"], "approved_with_override")
            self.assertTrue(report["can_commit"])
            self.assertEqual(report["status"], "warn")

    def test_infers_scope_from_ledger_touched_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_git(root)
            paths = create_run(root, "guard ledger")
            self.stage(root, "src/app.py")
            append_execution_ledger(
                root,
                paths.run_id,
                "step_completed",
                actor="codex",
                step_id="executor",
                status="completed",
                files_touched=["src/app.py"],
            )

            report = git_guard_report(root, paths.run_id)

            self.assertEqual(report["verdict"], "pass")
            self.assertEqual(report["scope_source"], "ledger_touched_files")
            self.assertEqual(report["out_of_scope_files"], [])

    def test_cli_exits_nonzero_when_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.init_git(root)
            paths = create_run(root, "guard cli")
            self.stage(root, "README.md")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    str(root),
                    "git",
                    "guard",
                    "--run-id",
                    paths.run_id,
                    "--scope",
                    "src/",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertEqual(report["verdict"], "blocked")


if __name__ == "__main__":
    unittest.main()
