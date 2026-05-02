from pathlib import Path
import tempfile
import unittest

from memoryos.cli import build_run_import
from memoryos.harness import build_memory_draft, create_run


class ImportRunTest(unittest.TestCase):
    def test_build_run_import_from_memory_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "import run fixture", project="MemoryOS")
            build_memory_draft(root, paths.run_id)
            nodes, edges = build_run_import(root, paths.run_id)
            self.assertGreaterEqual(len(nodes), 3)
            self.assertGreaterEqual(len(edges), 2)
            self.assertTrue(any(node.attrs.get("kind") == "agent_run" for node in nodes))
            self.assertTrue(any(node.attrs.get("run_id") == paths.run_id for node in nodes))


if __name__ == "__main__":
    unittest.main()
