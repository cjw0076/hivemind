from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import create_run, format_simple_yaml, provider_result_record
from hivemind.provider_disagreements import build_provider_output_disagreements


class ProviderDisagreementsTest(unittest.TestCase):
    def test_build_disagreements_from_executed_provider_outputs_without_raw_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider disagreement from executed outputs")
            self._write_provider_result(
                root,
                paths.run_dir,
                provider="claude",
                output="SECRET_A\nHold the release. This is high risk and weak evidence. Ask user approval.",
            )
            self._write_provider_result(
                root,
                paths.run_dir,
                provider="gemini",
                output="SECRET_B\nShip it. Low risk, verified by tests, implement the patch now.",
            )

            report = build_provider_output_disagreements(root, paths.run_id)
            encoded = json.dumps(report, ensure_ascii=False)

            self.assertEqual(report["schema_version"], "hive.provider_output_disagreements.v1")
            self.assertEqual(report["disagreement_count"], 1)
            self.assertTrue((root / report["artifact"]).exists())
            self.assertFalse(report["privacy"]["raw_provider_output_included"])
            self.assertNotIn("SECRET_A", encoded)
            self.assertNotIn("SECRET_B", encoded)
            record = report["disagreements"][0]
            self.assertEqual(record["source"], "executed_provider_output")
            self.assertEqual(record["severity"], "high")
            self.assertIn("conclusion", record["axes"])
            self.assertIn("risk_assessment", record["axes"])
            self.assertIn("evidence", record["axes"])

    def test_cli_provider_disagreements_json_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider disagreement cli")
            self._write_provider_result(root, paths.run_dir, provider="claude", output="Hold. high risk and weak evidence.")
            self._write_provider_result(root, paths.run_dir, provider="gemini", output="Ship. low risk and verified by tests.")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "provider-disagreements",
                    "--run",
                    paths.run_id,
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["kind"], "hive_provider_output_disagreements")
            self.assertEqual(payload["disagreement_count"], 1)

    def test_partial_provider_output_participates_when_body_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider partial disagreement")
            self._write_provider_result(root, paths.run_dir, provider="claude", output="Hold. high risk and weak evidence.")
            self._write_provider_result(
                root,
                paths.run_dir,
                provider="gemini",
                output="Ship. low risk and verified by tests.",
                status="partial",
            )

            report = build_provider_output_disagreements(root, paths.run_id)

            self.assertEqual(report["provider_output_count"], 2)
            self.assertEqual(report["disagreement_count"], 1)

    def test_stdout_body_is_used_when_output_path_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider stdout disagreement")
            self._write_provider_result(
                root,
                paths.run_dir,
                provider="claude",
                output="Hold. high risk and weak evidence.",
                include_output_path=False,
            )
            self._write_provider_result(
                root,
                paths.run_dir,
                provider="gemini",
                output="Ship. low risk and verified by tests.",
                include_output_path=False,
            )

            report = build_provider_output_disagreements(root, paths.run_id)

            self.assertEqual(report["provider_output_count"], 2)
            self.assertEqual(report["disagreement_count"], 1)

    def _write_provider_result(
        self,
        root: Path,
        run_dir: Path,
        *,
        provider: str,
        output: str,
        status: str = "completed",
        include_output_path: bool = True,
    ) -> Path:
        native = run_dir / "agents" / provider / "native"
        native.mkdir(parents=True, exist_ok=True)
        stdout = native / "passthrough_01_stdout.txt"
        stderr = native / "passthrough_01_stderr.txt"
        output_path = native / "passthrough_01_output.md"
        command = native / "passthrough_01_command.txt"
        result = native / "passthrough_01_result.yaml"
        stdout.write_text(output, encoding="utf-8")
        stderr.write_text("stderr\n", encoding="utf-8")
        if include_output_path:
            output_path.write_text(output, encoding="utf-8")
        command.write_text(f"{provider} run\n", encoding="utf-8")
        record = provider_result_record(
            root,
            agent=provider,
            role="native",
            status=status,
            provider_mode="native_passthrough",
            permission_mode="read_only",
            command_path=command,
            stdout_path=stdout,
            stderr_path=stderr,
            output_path=output_path if include_output_path else None,
            returncode=0,
            commands_run=[f"{provider} run"],
            artifacts_created=[result.relative_to(root).as_posix()],
        )
        result.write_text(format_simple_yaml(record), encoding="utf-8")
        return result


if __name__ == "__main__":
    unittest.main()
