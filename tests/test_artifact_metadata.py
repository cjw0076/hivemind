from pathlib import Path
import json
import tempfile
import unittest

from hivemind.harness import artifact_status, create_run, set_agent_status


class ArtifactMetadataTest(unittest.TestCase):
    def test_artifacts_report_existence_freshness_producer_and_class(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "artifact metadata smoke", project="Hive Mind")
            state = paths.state.read_text(encoding="utf-8")

            rows = {row["name"]: row for row in artifact_status(paths, json.loads(state))}

            self.assertTrue(rows["context_pack"]["exists"])
            self.assertEqual(rows["context_pack"]["freshness"], "stale")
            self.assertEqual(rows["context_pack"]["producer"], "system/local-context")
            self.assertEqual(rows["routing_plan"]["phase_class"], "required")
            self.assertEqual(rows["checks_report"]["phase_class"], "post_execution")

    def test_context_pack_fresh_after_context_worker_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "fresh context smoke", project="Hive Mind")
            state = set_agent_status(paths, "local-context-compressor", "completed")

            rows = {row["name"]: row for row in artifact_status(paths, state)}

            self.assertEqual(rows["context_pack"]["freshness"], "fresh")


if __name__ == "__main__":
    unittest.main()
