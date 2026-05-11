import json
import tempfile
import unittest
from pathlib import Path

from hivemind.goal import build_goal_report, format_goal_report, write_attack_pack


class GoalReportTest(unittest.TestCase):
    def test_goal_report_reads_latest_benchmark_and_release_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "GOAL.md").write_text("# Goal\n", encoding="utf-8")
            benchmarks = root / ".hivemind" / "benchmarks"
            benchmarks.mkdir(parents=True)
            (benchmarks / "user-value-20260511_010000.json").write_text(
                json.dumps(
                    {
                        "summary": {
                            "verdict": "pass",
                            "direct_cli_for_trivial": True,
                            "hive_for_audited_multi_agent": True,
                            "required_failures": [],
                        }
                    }
                ),
                encoding="utf-8",
            )
            release = root / ".hivemind" / "release" / "20260511_020000"
            release.mkdir(parents=True)
            (release / "user-value-benchmark.json").write_text(
                json.dumps({"summary": {"verdict": "pass"}}),
                encoding="utf-8",
            )
            (release / "test.log").write_text("Ran 281 tests\nOK\n", encoding="utf-8")

            report = build_goal_report(root)

            self.assertEqual(report["latest_value_benchmark"]["verdict"], "pass")
            self.assertEqual(report["latest_release_gate"]["user_value_verdict"], "pass")
            self.assertIn("docs/GOAL.md", report["claude_attack_prompt"])

    def test_format_goal_report_surfaces_attack_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "GOAL.md").write_text("# Goal\n", encoding="utf-8")

            text = format_goal_report(build_goal_report(root))

            self.assertIn("Hive Mind Goal Sprint", text)
            self.assertIn("Claude attack prompt", text)
            self.assertIn("scripts/public-release-check.sh", text)
            self.assertIn("hive goal --write-attack-pack", text)

    def test_write_attack_pack_creates_markdown_for_reviewer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "docs").mkdir()
            (root / "docs" / "GOAL.md").write_text("# Goal\n", encoding="utf-8")

            result = write_attack_pack(root)

            path = root / result["path"]
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("Hive Mind Production-v0 Attack Pack", text)
            self.assertIn("Finding Format", text)
            self.assertIn("provider passthrough", text)


if __name__ == "__main__":
    unittest.main()
