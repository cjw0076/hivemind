from pathlib import Path
import json
import tempfile
import unittest

from hivemind.harness import demo_live_run, load_run, read_hive_activity
from hivemind.run_validation import validate_run_artifacts


class DemoLiveRunTest(unittest.TestCase):
    def test_demo_live_run_animates_without_provider_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = demo_live_run(root, delay=0)

            self.assertEqual(report["status"], "demo_complete")
            paths, state = load_run(root, report["run_id"])
            self.assertTrue((paths.run_dir / "routing_plan.json").exists())
            self.assertTrue((paths.run_dir / "society_plan.json").exists())
            self.assertTrue((paths.local_dir / "context.json").exists())
            self.assertTrue((paths.claude_dir / "planner_result.yaml").exists())
            self.assertTrue((paths.codex_dir / "executor_result.yaml").exists())
            self.assertTrue((paths.gemini_dir / "reviewer_result.yaml").exists())
            self.assertEqual(state["status"], "demo_complete")

            activities = read_hive_activity(paths, limit=50)
            self.assertTrue(any(item.get("action") == "demo_started" for item in activities))
            self.assertTrue(any(item.get("action") == "demo_completed" for item in activities))

            validation = validate_run_artifacts(paths.run_dir, root)
            self.assertEqual(validation["verdict"], "pass", validation["issues"])

    def test_demo_live_run_can_animate_existing_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = demo_live_run(root, task="first demo", delay=0)
            second = demo_live_run(root, run_id=first["run_id"], delay=0)

            self.assertEqual(second["run_id"], first["run_id"])
            paths, _ = load_run(root, first["run_id"])
            events = [
                json.loads(line)
                for line in paths.events.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertGreaterEqual(sum(1 for item in events if item.get("type") == "demo_started"), 2)


if __name__ == "__main__":
    unittest.main()
