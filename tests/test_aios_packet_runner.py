from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hivemind.aios_packet_runner import run_aios_packet


ROOT = Path(__file__).resolve().parents[1]


def packet_payload(return_to: str = ".aios/outbox/hivemind/asc-test.hivemind.result.json") -> dict:
    return {
        "schema_version": "aios.dispatch.v1",
        "dispatch_id": "asc-test",
        "contract_id": "ASC-TEST",
        "target_repo": "hivemind",
        "agent": "local",
        "goal": "Prove Hive can consume an AIOS packet.",
        "required_reading": ["AGENTS.md", "docs/contracts/ASC-TEST.md"],
        "return_to": return_to,
        "scope": {
            "allowed_files": ["hivemind/hivemind/aios_packet_runner.py"],
            "forbidden_files": [".env", "provider credentials"],
        },
    }


class AiosPacketRunnerTest(unittest.TestCase):
    def test_run_packet_prepares_provider_loop_and_writes_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            hive_root = base / "hive"
            myworld_root = base / "myworld"
            hive_root.mkdir()
            myworld_root.mkdir()
            packet = myworld_root / ".aios" / "inbox" / "hivemind" / "asc-test.hivemind.json"
            packet.parent.mkdir(parents=True)
            packet.write_text(json.dumps(packet_payload()), encoding="utf-8")

            result = run_aios_packet(
                hive_root=hive_root,
                packet_path=packet,
                myworld_root=myworld_root,
                provider="local",
                write_result_packet=True,
            )

            self.assertEqual(result["schema_version"], "hive.aios_packet_runner.v1")
            self.assertEqual(result["status"], "prepared")
            self.assertEqual(result["authority"]["executor"], "hivemind")
            self.assertEqual(result["provider_loop_tick"]["status"], "prepared")
            self.assertTrue((myworld_root / ".aios/outbox/hivemind/asc-test.hivemind.result.json").exists())

    def test_non_hivemind_packet_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            hive_root = base / "hive"
            hive_root.mkdir()
            packet = base / "packet.json"
            payload = packet_payload()
            payload["target_repo"] = "memoryOS"
            packet.write_text(json.dumps(payload), encoding="utf-8")

            result = run_aios_packet(hive_root=hive_root, packet_path=packet, provider="local")

            self.assertEqual(result["status"], "held")
            self.assertIn("target_repo_not_hivemind", result["stop_conditions_triggered"])

    def test_writable_provider_execution_requires_operator_grant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            hive_root = base / "hive"
            hive_root.mkdir()
            packet = base / "packet.json"
            packet.write_text(json.dumps(packet_payload()), encoding="utf-8")

            result = run_aios_packet(
                hive_root=hive_root,
                packet_path=packet,
                provider="codex",
                execute=True,
                writable_provider_execution=True,
            )

            self.assertEqual(result["status"], "held")
            self.assertIn("operator_grant_missing", result["stop_conditions_triggered"])

    def test_writable_provider_execution_uses_workspace_write_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            hive_root = base / "hive"
            hive_root.mkdir()
            packet = base / "packet.json"
            packet.write_text(json.dumps(packet_payload()), encoding="utf-8")
            completed = subprocess.CompletedProcess(args=["codex", "exec"], returncode=0, stdout="done\n", stderr="")

            with patch("hivemind.harness.resolve_provider_binary", return_value="codex"):
                with patch("hivemind.provider_passthrough.subprocess.run", return_value=completed):
                    result = run_aios_packet(
                        hive_root=hive_root,
                        packet_path=packet,
                        provider="codex",
                        execute=True,
                        writable_provider_execution=True,
                        operator_grant="operator approved scoped workspace-write for this AIOS packet",
                    )

            self.assertEqual(result["status"], "executed")
            self.assertEqual(result["provider_loop_tick"]["status"], "completed")
            command_ref = result["provider_loop_tick"]["worker"]["last_result_path"].replace("_result.yaml", "_command.txt")
            command = (hive_root / command_ref).read_text(encoding="utf-8")
            self.assertIn("--sandbox workspace-write", command)

    def test_dangerous_full_access_requires_operator_grant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            hive_root = base / "hive"
            hive_root.mkdir()
            packet = base / "packet.json"
            packet.write_text(json.dumps(packet_payload()), encoding="utf-8")

            result = run_aios_packet(
                hive_root=hive_root,
                packet_path=packet,
                provider="codex",
                execute=True,
                dangerous_full_access=True,
            )

            self.assertEqual(result["status"], "held")
            self.assertIn("operator_grant_missing", result["stop_conditions_triggered"])

    def test_dangerous_full_access_requires_explicit_grant_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            hive_root = base / "hive"
            hive_root.mkdir()
            packet = base / "packet.json"
            packet.write_text(json.dumps(packet_payload()), encoding="utf-8")

            result = run_aios_packet(
                hive_root=hive_root,
                packet_path=packet,
                provider="codex",
                execute=True,
                dangerous_full_access=True,
                operator_grant="ok run it",
            )

            self.assertEqual(result["status"], "held")
            self.assertIn("dangerous_operator_grant_not_explicit", result["stop_conditions_triggered"])

    def test_dangerous_full_access_uses_codex_bypass_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            hive_root = base / "hive"
            hive_root.mkdir()
            packet = base / "packet.json"
            packet.write_text(json.dumps(packet_payload()), encoding="utf-8")
            completed = subprocess.CompletedProcess(args=["codex", "exec"], returncode=0, stdout="done\n", stderr="")

            with patch("hivemind.harness.resolve_provider_binary", return_value="codex"):
                with patch("hivemind.provider_passthrough.subprocess.run", return_value=completed):
                    result = run_aios_packet(
                        hive_root=hive_root,
                        packet_path=packet,
                        provider="codex",
                        execute=True,
                        dangerous_full_access=True,
                        operator_grant="founder approved dangerous full-access autonomous execution",
                    )

            self.assertEqual(result["status"], "executed")
            self.assertEqual(result["provider_loop_tick"]["status"], "completed")
            command_ref = result["provider_loop_tick"]["worker"]["last_result_path"].replace("_result.yaml", "_command.txt")
            command = (hive_root / command_ref).read_text(encoding="utf-8")
            self.assertIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_cli_aios_packet_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            myworld_root = base / "myworld"
            myworld_root.mkdir()
            packet = myworld_root / ".aios" / "inbox" / "hivemind" / "asc-test.hivemind.json"
            packet.parent.mkdir(parents=True)
            packet.write_text(json.dumps(packet_payload()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "hivemind.hive",
                    "--root",
                    (base / "hive").as_posix(),
                    "aios-packet",
                    "--packet",
                    packet.as_posix(),
                    "--myworld-root",
                    myworld_root.as_posix(),
                    "--provider",
                    "local",
                    "--write-result",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "prepared")
            self.assertTrue((myworld_root / ".aios/outbox/hivemind/asc-test.hivemind.result.json").exists())


if __name__ == "__main__":
    unittest.main()
