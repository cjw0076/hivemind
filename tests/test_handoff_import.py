from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.handoff_import import import_handoff
from hivemind.inspect_run import build_inspect_report
from hivemind.run_validation import validate_run_artifacts


class HandoffImportTest(unittest.TestCase):
    def test_imports_handoff_json_into_inspectable_run_without_raw_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hive"
            source = Path(tmp) / "shared" / "HANDOFF.json"
            self.write_handoff(source)

            report = import_handoff(root, source)

            self.assertEqual(report["kind"], "hive_handoff_import")
            self.assertEqual(report["status"], "imported")
            self.assertIn("run_", report["run_id"])
            inspect = build_inspect_report(root, report["run_id"])
            self.assertEqual(inspect["kind"], "hive_run_inspection")
            self.assertEqual(inspect["status"], "imported")
            artifact = root / report["artifact"]
            payload = json.loads(artifact.read_text(encoding="utf-8"))
            encoded = json.dumps(payload, ensure_ascii=False)
            self.assertEqual(payload["schema_version"], "hive.handoff_import.v1")
            self.assertFalse(payload["privacy"]["raw_source_body_stored"])
            self.assertTrue(payload["privacy"]["paths_hidden"])
            self.assertNotIn("SECRET_PROVIDER_STDOUT", encoded)
            self.assertNotIn(source.as_posix(), encoded)
            validation = validate_run_artifacts((root / ".runs" / report["run_id"]), root)
            self.assertEqual(validation["verdict"], "pass")

    def test_import_accepts_directory_containing_handoff_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hive"
            source_dir = Path(tmp) / "shared"
            self.write_handoff(source_dir / "HANDOFF.json")

            report = import_handoff(root, source_dir)

            self.assertEqual(report["source"]["file_name"], "HANDOFF.json")

    def test_malformed_json_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "HANDOFF.json"
            source.write_text("{bad json", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "malformed HANDOFF.json"):
                import_handoff(Path(tmp) / "hive", source)

    def test_cli_import_json_and_inspect_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hive"
            source = Path(tmp) / "shared" / "HANDOFF.json"
            self.write_handoff(source)

            imported = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root.as_posix(), "handoff", "import", source.as_posix(), "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            payload = json.loads(imported.stdout)

            inspected = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root.as_posix(), "inspect", payload["run_id"], "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            inspect = json.loads(inspected.stdout)
            self.assertEqual(inspect["run_id"], payload["run_id"])
            self.assertEqual(inspect["status"], "imported")

    def write_handoff(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "protocol_version": 1,
                    "turn": "codex",
                    "locked": False,
                    "updated_at": "2026-05-12T20:00:00+09:00",
                    "phase": "test-phase",
                    "north_star": "Hive runtime loop",
                    "task": {
                        "id": "H-P0.test",
                        "title": "Import legacy handoff",
                        "description": "Replay legacy handoff into Hive artifacts.",
                        "owner": "codex",
                        "turn_type": "implementation",
                        "files_to_touch": ["hivemind/handoff_import.py"],
                        "acceptance_criteria": ["import is inspectable", "raw body is not copied"],
                        "status": "done",
                        "notes": "SECRET_PROVIDER_STDOUT",
                    },
                    "task_queue": [
                        {"id": "H-P0.1", "title": "First", "owner": "codex", "status": "done", "notes": "SECRET_PROVIDER_STDOUT"},
                        {"id": "H-P0.2", "title": "Second", "owner": "claude", "status": "pending"},
                    ],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
