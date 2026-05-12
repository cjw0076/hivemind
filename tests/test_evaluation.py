from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.evaluation import build_evaluation_report, format_evaluation_report
from hivemind.harness import create_run
from hivemind.run_validation import validate_run_artifacts


class EvaluationReportTest(unittest.TestCase):
    def test_builds_durable_three_persona_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "evaluation report smoke")

            report = build_evaluation_report(root, paths.run_id)
            artifact = root / report["artifact"]
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            roles = {review["role"] for review in payload["reviews"]}

            self.assertEqual(report["kind"], "hive_evaluation_report")
            self.assertEqual(report["schema_version"], "hive.evaluation_report.v1")
            self.assertEqual(report["run_id"], paths.run_id)
            self.assertEqual(roles, {"hive.verifier", "hive.product_evaluator", "persona.actual_user"})
            self.assertTrue(report["paths_hidden"])
            self.assertTrue(report["privacy"]["paths_hidden"])
            self.assertFalse(report["privacy"]["raw_provider_outputs_included"])
            self.assertFalse(report["privacy"]["private_memory_contents_included"])
            self.assertEqual(payload["artifact"], report["artifact"])

    def test_updates_state_and_validation_accepts_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "evaluation validation smoke")

            report = build_evaluation_report(root, paths.run_id)
            state = json.loads(paths.state.read_text(encoding="utf-8"))
            validation = validate_run_artifacts(paths.run_dir, root)

            self.assertEqual(state["artifacts"]["evaluation_report"], report["artifact"])
            self.assertEqual(state["latest_event"], "evaluation_report_created")
            self.assertEqual(validation["verdict"], "pass")

    def test_default_output_hides_absolute_paths_and_raw_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "evaluation privacy smoke")
            agents = paths.run_dir / "agents" / "codex"
            agents.mkdir(parents=True, exist_ok=True)
            (agents / "stdout.txt").write_text("SECRET_PROVIDER_BODY", encoding="utf-8")

            report = build_evaluation_report(root, paths.run_id)
            encoded = json.dumps(report, ensure_ascii=False)

            self.assertNotIn(root.as_posix(), encoded)
            self.assertNotIn("SECRET_PROVIDER_BODY", encoded)

    def test_format_evaluation_report_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "evaluation text smoke")

            text = format_evaluation_report(build_evaluation_report(root, paths.run_id))

            self.assertIn("Hive Evaluation", text)
            self.assertIn("hive.verifier", text)
            self.assertIn("hive.product_evaluator", text)
            self.assertIn("persona.actual_user", text)

    def test_cli_evaluate_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "evaluate cli smoke", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            evaluated = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "evaluate", "--run", run_id, "--json"],
                text=True,
                capture_output=True,
                check=True,
            )

            data = json.loads(evaluated.stdout)
            self.assertEqual(data["kind"], "hive_evaluation_report")
            self.assertEqual(data["run_id"], run_id)
            self.assertTrue((root / data["artifact"]).exists())

    def test_cli_subagents_review_alias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "subagents review smoke", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            reviewed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root,
                    "subagents",
                    "review",
                    "--run",
                    run_id,
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            data = json.loads(reviewed.stdout)
            self.assertEqual(data["schema_version"], "hive.evaluation_report.v1")
            self.assertEqual(data["run_id"], run_id)
            self.assertEqual(len(data["reviews"]), 3)


if __name__ == "__main__":
    unittest.main()
