from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.arrival_pack import build_arrival_pack, format_arrival_pack
from hivemind.harness import create_run


class ArrivalPackTest(unittest.TestCase):
    def test_builds_incoming_agent_brief_without_raw_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "arrival pack smoke")
            agents = paths.run_dir / "agents" / "codex"
            agents.mkdir(parents=True, exist_ok=True)
            (agents / "stdout.txt").write_text("SECRET_STDOUT_BODY", encoding="utf-8")
            (agents / "executor_result.yaml").write_text(
                "\n".join(
                    [
                        "agent: codex",
                        "role: executor",
                        "status: completed",
                        "provider_mode: prepare_only",
                        "permission_mode: default",
                        "stdout_path: stdout.txt",
                    ]
                ),
                encoding="utf-8",
            )

            pack = build_arrival_pack(root, paths.run_id, role="codex")
            encoded = json.dumps(pack, ensure_ascii=False)

            self.assertEqual(pack["kind"], "hive_arrival_pack")
            self.assertEqual(pack["schema_version"], "hive.arrival_pack.v1")
            self.assertEqual(pack["run_id"], paths.run_id)
            self.assertEqual(pack["role"], "codex")
            self.assertEqual(pack["objective"], "arrival pack smoke")
            self.assertTrue(pack["privacy"]["paths_hidden"])
            self.assertFalse(pack["privacy"]["raw_stdout_included"])
            self.assertFalse(pack["privacy"]["raw_stderr_included"])
            self.assertIn("accepted_claims", pack)
            self.assertIn("blocked_items", pack)
            self.assertIn("scope_hints", pack)
            self.assertTrue(any(item["kind"] == "provider_result" for item in pack["latest_artifacts"]))
            self.assertTrue(any("hive inspect" in item["command"] for item in pack["suggested_commands"]))
            self.assertNotIn("SECRET_STDOUT_BODY", encoded)
            self.assertNotIn("stdout.txt", encoded)

    def test_contested_claims_include_disagreement_topology(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "arrival contested smoke")
            (paths.run_dir / "disagreements.json").write_text(
                json.dumps(
                    [
                        {
                            "ts": "2026-05-12T00:00:00Z",
                            "run_id": paths.run_id,
                            "step_id": "step_a",
                            "topology_type": "split",
                            "severity": "high",
                            "axes": ["conclusion", "risk"],
                            "dominant_axis": "conclusion",
                            "topology_recommended_action": "escalate",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            pack = build_arrival_pack(root, paths.run_id)

            self.assertEqual(len(pack["contested_claims"]), 1)
            self.assertEqual(pack["contested_claims"][0]["step_id"], "step_a")
            self.assertEqual(pack["contested_claims"][0]["severity"], "high")
            self.assertTrue(any(item["kind"] == "disagreement" for item in pack["blocked_items"]))

    def test_paths_flag_exposes_debug_paths_only_when_requested(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "arrival paths smoke")
            agents = paths.run_dir / "agents" / "codex"
            agents.mkdir(parents=True, exist_ok=True)
            (agents / "executor_result.yaml").write_text(
                "\n".join(
                    [
                        "agent: codex",
                        "role: executor",
                        "status: completed",
                        "provider_mode: prepare_only",
                        "permission_mode: default",
                    ]
                ),
                encoding="utf-8",
            )

            pack = build_arrival_pack(root, paths.run_id, show_paths=True)

            self.assertFalse(pack["privacy"]["paths_hidden"])
            provider_items = [item for item in pack["latest_artifacts"] if item["kind"] == "provider_result"]
            self.assertIn("path", provider_items[0])

    def test_format_arrival_pack_is_readable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = create_run(root, "arrival text smoke")
            text = format_arrival_pack(build_arrival_pack(root, paths.run_id))

            self.assertIn("Hive Arrival Pack", text)
            self.assertIn("Blocked Items", text)
            self.assertIn("Accepted Claims", text)
            self.assertIn("Suggested Commands", text)

    def test_cli_arrival_pack_json_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            created = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "run", "arrival cli smoke", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            run_id = json.loads(created.stdout)["run_id"]

            arrived = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "--root", root, "arrival-pack", "--run", run_id, "--json"],
                text=True,
                capture_output=True,
                check=True,
            )

            data = json.loads(arrived.stdout)
            self.assertEqual(data["kind"], "hive_arrival_pack")
            self.assertEqual(data["run_id"], run_id)
            self.assertEqual(data["objective"], "arrival cli smoke")
            self.assertTrue(data["privacy"]["paths_hidden"])


if __name__ == "__main__":
    unittest.main()
