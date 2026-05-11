import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from hivemind.hive import _main
from hivemind.radar_classifier import RATIONALE_LIMIT, VERDICTS, review_radar


RADAR_TEMPLATE = """# AIOS Task Radar

## Summary

- root: `{workspace}`

## Top Task Signals

| Score | Domain | Path | Signals | Candidate Task |
| ---: | --- | --- | --- | --- |
| 364 | hivemind | `myworld/hivemind/docs/AGENT_WORKLOG.md` | `blocker:4,contract:6,gap:5,hivemind:12,next:12,todo:12,verify:10` | issue a Hive Mind packet |
| 315 | memoryOS | `myworld/memoryOS/docs/TODO.md` | `capabilityos:12,contract:12,gap:8,hivemind:12,memoryos:12,next:4,todo:12,verify:8` | issue a MemoryOS packet |
| 303 | _from_desktop | `_from_desktop/project/CHANGELOG.md` | `blocker:12,gap:12,next:12,verify:12` | triage external context |
| 299 | myworld | `myworld/docs/contracts/ASC-0002-example.md` | `aios:10,capabilityos:12,contract:12,stop_condition:4,verify:12` | promote control-plane signal |
| 88 | hivemind | `myworld/hivemind/docs/MISSING.md` | `hivemind:12,next:12,verify:12` | stale path |
"""


class RadarReviewTest(unittest.TestCase):
    def make_workspace(self, tmp: Path) -> tuple[Path, Path, Path]:
        workspace = tmp / "jaewon"
        hive_root = workspace / "myworld" / "hivemind"
        (hive_root / "hivemind").mkdir(parents=True)
        (hive_root / "docs").mkdir(parents=True)
        (hive_root / "pyproject.toml").write_text("[project]\nname='hivemind'\n", encoding="utf-8")
        (hive_root / "docs" / "AGENT_WORKLOG.md").write_text("# log\n", encoding="utf-8")
        (workspace / "myworld" / "memoryOS" / "docs").mkdir(parents=True)
        (workspace / "myworld" / "memoryOS" / "docs" / "TODO.md").write_text("# todo\n", encoding="utf-8")
        (workspace / "myworld" / "docs" / "contracts").mkdir(parents=True)
        (workspace / "myworld" / "docs" / "contracts" / "ASC-0002-example.md").write_text("# contract\n", encoding="utf-8")
        radar_path = workspace / "myworld" / "docs" / "AIOS_TASK_RADAR.md"
        radar_path.write_text(RADAR_TEMPLATE.format(workspace=workspace.as_posix()), encoding="utf-8")
        return workspace, hive_root, radar_path

    def test_review_classifies_top_rows_without_source_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _, _, radar_path = self.make_workspace(Path(tmp_dir))

            report = review_radar(radar_path, top=5)

        self.assertEqual(len(report["entries"]), 5)
        verdicts = [entry["verdict"] for entry in report["entries"]]
        self.assertEqual(verdicts, ["executable", "needs_context", "out_of_scope", "ambiguous", "needs_context"])
        self.assertTrue(set(verdicts).issubset(VERDICTS))
        for entry in report["entries"]:
            self.assertLessEqual(len(entry["rationale"]), RATIONALE_LIMIT)
            self.assertIn(entry["path"], entry["rationale"])
            self.assertNotIn("issue a Hive Mind packet", entry["rationale"])

    def test_cli_writes_json_and_markdown_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _, hive_root, radar_path = self.make_workspace(Path(tmp_dir))
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                _main(["--root", hive_root.as_posix(), "radar-review", "--radar", radar_path.as_posix(), "--top", "4", "--json"])

            payload = json.loads(stdout.getvalue())
            json_path = hive_root / "docs" / "radar_review.json"
            md_path = hive_root / "docs" / "RADAR_REVIEW.md"

            self.assertEqual(len(payload["entries"]), 4)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8"))["schema"], "hivemind.radar_review.v1")
            self.assertIn("No external LLM provider", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
