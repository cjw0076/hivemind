from pathlib import Path
import tempfile
import unittest

from hivemind.hive import resolve_root


class RootResolutionTest(unittest.TestCase):
    def test_repo_root_resolves_to_self(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("[project]\nname = 'hivemind'\n", encoding="utf-8")
            (root / "hivemind").mkdir()
            (root / ".runs").mkdir()

            self.assertEqual(resolve_root(root.as_posix()), root.resolve())

    def test_umbrella_root_prefers_hivemind_child_even_with_runs_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".runs").mkdir()
            child = root / "hivemind"
            child.mkdir()
            (child / "pyproject.toml").write_text("[project]\nname = 'hivemind'\n", encoding="utf-8")
            (child / "hivemind").mkdir()
            (child / ".runs").mkdir()

            self.assertEqual(resolve_root(root.as_posix()), child.resolve())


if __name__ == "__main__":
    unittest.main()
