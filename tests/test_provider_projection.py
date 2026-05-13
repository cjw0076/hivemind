from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.harness import create_run, format_simple_yaml, provider_result_record
from hivemind.provider_projection import build_provider_output_projection


class ProviderProjectionTest(unittest.TestCase):
    def test_projection_excludes_raw_provider_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "review provider output projection")
            result_path = self._write_provider_receipt(root, paths.run_dir, secret="SECRET_PROVIDER_BODY")

            report = build_provider_output_projection(root, paths.run_id)
            encoded = json.dumps(report, ensure_ascii=False)

            self.assertEqual(report["schema_version"], "hive.provider_output_projection.v1")
            self.assertEqual(report["provider_result_count"], 1)
            self.assertTrue((root / report["artifact"]).exists())
            self.assertNotIn("SECRET_PROVIDER_BODY", encoded)
            self.assertFalse(report["privacy"]["raw_provider_output_included"])
            row = report["providers"][0]
            self.assertEqual(row["provider"], "codex")
            self.assertEqual(row["status"], "completed")
            self.assertGreater(row["stdout"]["bytes"], 0)
            self.assertGreater(row["stderr"]["bytes"], 0)
            self.assertFalse(row["stdout"]["body_included"])
            self.assertFalse(row["stderr"]["body_included"])
            self.assertIn(result_path.name, row["receipt_ref"])

    def test_projection_can_show_relative_path_refs_without_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "debug provider output projection paths")
            self._write_provider_receipt(root, paths.run_dir, secret="SECRET_PATH_DEBUG")

            report = build_provider_output_projection(root, paths.run_id, show_paths=True)
            encoded = json.dumps(report, ensure_ascii=False)
            row = report["providers"][0]

            self.assertNotIn("SECRET_PATH_DEBUG", encoded)
            self.assertIn("ref", row["stdout"])
            self.assertTrue(row["stdout"]["ref"].endswith("_stdout.txt"))
            self.assertFalse(row["privacy"]["path_refs_hidden"])

    def test_cli_provider_output_projection_json_surface(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "provider projection cli")
            self._write_provider_receipt(root, paths.run_dir, secret="SECRET_CLI_BODY")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    root.as_posix(),
                    "provider-output-projection",
                    "--run",
                    paths.run_id,
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=True,
            )

            payload = json.loads(completed.stdout)
            encoded = json.dumps(payload, ensure_ascii=False)
            self.assertEqual(payload["kind"], "hive_provider_output_projection")
            self.assertNotIn("SECRET_CLI_BODY", encoded)
            self.assertEqual(payload["provider_result_count"], 1)

    def _write_provider_receipt(self, root: Path, run_dir: Path, *, secret: str) -> Path:
        native = run_dir / "agents" / "codex" / "native"
        native.mkdir(parents=True, exist_ok=True)
        stdout = native / "passthrough_01_stdout.txt"
        stderr = native / "passthrough_01_stderr.txt"
        output = native / "passthrough_01_output.md"
        command = native / "passthrough_01_command.txt"
        result = native / "passthrough_01_result.yaml"
        stdout.write_text(f"{secret}\nvisible stdout body must stay private\n", encoding="utf-8")
        stderr.write_text(f"{secret}\nvisible stderr body must stay private\n", encoding="utf-8")
        output.write_text(f"{secret}\nvisible output body must stay private\n", encoding="utf-8")
        command.write_text("codex exec inspect\n", encoding="utf-8")
        record = provider_result_record(
            root,
            agent="codex",
            role="native",
            status="completed",
            provider_mode="native_passthrough",
            permission_mode="read_only",
            command_path=command,
            stdout_path=stdout,
            stderr_path=stderr,
            output_path=output,
            returncode=0,
            commands_run=["codex exec inspect"],
            artifacts_created=[result.relative_to(root).as_posix()],
        )
        result.write_text(format_simple_yaml(record), encoding="utf-8")
        return result


if __name__ == "__main__":
    unittest.main()
