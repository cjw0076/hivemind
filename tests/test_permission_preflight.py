from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hivemind.permission_preflight import build_permission_preflight


ROOT = Path(__file__).resolve().parents[1]


def route_payload(**overrides):
    payload = {
        "contract": "capabilityos.constraint_break_route.v1",
        "task": "AIOS provider is blocked by CLI rules",
        "blocker": "provider PIN gate",
        "permission_questions": [
            {
                "permission_id": "allow_provider_fallback",
                "question": "May Hive Mind route execution to another provider?",
                "default": "ask_user",
                "risk": "model_behavior_drift",
            }
        ],
        "unblock_options": [
            {
                "option_id": "route_to_alternate_provider",
                "executor": "hivemind",
                "requires_permission": True,
            }
        ],
        "execution_policy": {
            "executor": "hivemind",
            "capabilityos_executes_tools": False,
            "requires_user_grant_before_scope_lift": True,
        },
        "privacy_policy": {"do_not_store": ["pins", "tokens", "api_keys"]},
        "risk_notes": ["requires_user_permission"],
    }
    payload.update(overrides)
    return payload


class PermissionPreflightTest(unittest.TestCase):
    def test_preflight_preserves_hive_executor_and_permission_questions(self) -> None:
        report = build_permission_preflight(route_payload())

        self.assertEqual(report["schema_version"], "hivemind.permission_preflight.v1")
        self.assertEqual(report["status"], "operator_checkpoint_required")
        self.assertEqual(report["executor"], "hivemind")
        self.assertFalse(report["execution_policy"]["execute_now"])
        self.assertTrue(report["execution_policy"]["requires_operator_grant"])
        self.assertEqual(report["permission_questions"][0]["permission_id"], "allow_provider_fallback")
        self.assertEqual(report["stop_conditions_triggered"], [])

    def test_preflight_blocks_if_capabilityos_wants_execution(self) -> None:
        route = route_payload(execution_policy={"executor": "hivemind", "capabilityos_executes_tools": True})

        report = build_permission_preflight(route)

        self.assertEqual(report["status"], "blocked")
        self.assertIn("capabilityos_execution_requested", report["stop_conditions_triggered"])

    def test_cli_permission_preflight_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            route = Path(tmp) / "constraint_break_route.json"
            route.write_text(json.dumps(route_payload()), encoding="utf-8")

            result = subprocess.run(
                [sys.executable, "-m", "hivemind.hive", "permission-preflight", "--route-json", route.as_posix(), "--json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["executor"], "hivemind")
        self.assertEqual(payload["status"], "operator_checkpoint_required")


if __name__ == "__main__":
    unittest.main()
