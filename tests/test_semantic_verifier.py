from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.evaluation import build_evaluation_report
from hivemind.harness import create_run
from hivemind.run_validation import validate_run_artifacts
from hivemind.semantic_verifier import build_semantic_verification


class SemanticVerifierTest(unittest.TestCase):
    def test_high_risk_run_requires_review_and_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "release public high-risk security claim")

            report = build_semantic_verification(root, paths.run_id)
            state = json.loads(paths.state.read_text(encoding="utf-8"))

            self.assertEqual(report["kind"], "hive_semantic_verification")
            self.assertEqual(report["schema_version"], "hive.semantic_verification.v1")
            self.assertEqual(report["status"], "review_required")
            self.assertEqual(report["risk_level"], "high")
            self.assertFalse(report["provider_executed"])
            self.assertEqual(state["artifacts"]["semantic_verification"], report["artifact"])
            self.assertEqual(state["artifacts"]["semantic_verifier_prompt"], report["prompt_artifact"])
            self.assertTrue((root / report["artifact"]).exists())
            self.assertTrue((root / report["prompt_artifact"]).exists())

    def test_low_risk_run_records_not_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "summarize local notes")

            report = build_semantic_verification(root, paths.run_id)

            self.assertEqual(report["risk_level"], "low")
            self.assertEqual(report["status"], "not_required")
            self.assertEqual(report["risk_signals"], [])

    def test_default_output_hides_absolute_paths_and_raw_provider_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "release public high-risk privacy claim")
            agents = paths.run_dir / "agents" / "codex"
            agents.mkdir(parents=True, exist_ok=True)
            (agents / "stdout.txt").write_text("SECRET_PROVIDER_STDOUT", encoding="utf-8")

            report = build_semantic_verification(root, paths.run_id)
            encoded = json.dumps(report, ensure_ascii=False)
            prompt = (root / report["prompt_artifact"]).read_text(encoding="utf-8")

            self.assertNotIn(root.as_posix(), encoded)
            self.assertNotIn("SECRET_PROVIDER_STDOUT", encoded)
            self.assertNotIn("SECRET_PROVIDER_STDOUT", prompt)

    def test_validation_accepts_semantic_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "release public high-risk claim")

            build_semantic_verification(root, paths.run_id)
            validation = validate_run_artifacts(paths.run_dir, root)

            self.assertEqual(validation["verdict"], "pass")

    def test_evaluate_blocks_high_risk_without_semantic_review_then_cites_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "release public high-risk claim")

            before = build_evaluation_report(root, paths.run_id)
            verifier_before = [r for r in before["reviews"] if r["role"] == "hive.verifier"][0]
            self.assertEqual(verifier_before["status"], "failed")
            self.assertIn("high-risk run lacks semantic verifier review", verifier_before["blockers"])

            semantic = build_semantic_verification(root, paths.run_id)
            after = build_evaluation_report(root, paths.run_id)
            verifier_after = [r for r in after["reviews"] if r["role"] == "hive.verifier"][0]

            self.assertEqual(semantic["status"], "review_required")
            self.assertNotIn("high-risk run lacks semantic verifier review", verifier_after["blockers"])
            self.assertEqual(after["semantic_verification"]["status"], "review_required")

    def test_cli_semantic_review_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "release public high-risk claim", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            reviewed = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "semantic-review", "--run", run_id, "--json"],
                text=True,
                capture_output=True,
                check=True,
            )

            data = json.loads(reviewed.stdout)
            self.assertEqual(data["kind"], "hive_semantic_verification")
            self.assertEqual(data["run_id"], run_id)
            self.assertEqual(data["status"], "review_required")
            self.assertTrue((root / data["artifact"]).exists())


if __name__ == "__main__":
    unittest.main()
