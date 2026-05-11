import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import format_onboarding, init_onboarding


class OnboardingTest(unittest.TestCase):
    def test_init_onboarding_recommends_public_alpha_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            report = init_onboarding(root)
            commands = [item["command"] for item in report["next_actions"]]
            text = format_onboarding(report)

            self.assertEqual(commands[0], "hive demo quickstart")
            self.assertIn("hive demo memory-loop", commands)
            self.assertIn('hive run "your task"', commands)
            self.assertIn("hive inspect <run_id>", commands)
            self.assertIn("Recommended Path:", text)
            self.assertIn("Optional setup:", text)

    def test_cli_init_json_includes_next_actions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            completed = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root.as_posix(), "init", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            commands = [item["command"] for item in payload["next_actions"]]
            self.assertEqual(commands[:2], ["hive demo quickstart", "hive demo memory-loop"])


if __name__ == "__main__":
    unittest.main()
