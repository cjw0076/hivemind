from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from hivemind.harness import doctor_scope_report, format_doctor_scope, hardware_report


FAKE_PROVIDERS = {
    "providers": {
        "codex": {
            "status": "available",
            "command": "codex",
            "path": "/usr/bin/codex",
            "version": "codex 1.0",
            "risks": ["repo_write_modes_require_explicit_approval"],
        }
    }
}


class DoctorScopesTest(unittest.TestCase):
    def test_hardware_report_contains_runtime_and_provider_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("hivemind.harness.detect_agents", return_value=FAKE_PROVIDERS),
                patch("hivemind.harness.probe_gpus", return_value=[]),
                patch(
                    "hivemind.harness.probe_binary_version",
                    return_value={"status": "available", "path": "/usr/bin/tool", "version": "tool 1.0"},
                ),
                patch("hivemind.harness.probe_network", return_value={"status": "reachable", "target": "1.1.1.1:53"}),
            ):
                report = hardware_report(root)

            self.assertEqual(report["schema_version"], 1)
            self.assertIn("python", report["runtime"])
            self.assertEqual(report["provider_cli_paths"]["codex"]["path"], "/usr/bin/codex")
            self.assertIn("ollama", report["ports"])

    def test_doctor_scope_all_combines_providers_hardware_models_and_permissions(self) -> None:
        local_runtime = {
            "generated_at": "test",
            "ollama": {"models": ["qwen3:8b"], "server": "running", "model_source": "server"},
            "recommended_models": ["qwen3:8b"],
            "missing_recommended_models": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (
                patch("hivemind.harness.detect_agents", return_value=FAKE_PROVIDERS),
                patch("hivemind.harness.probe_gpus", return_value=[]),
                patch(
                    "hivemind.harness.probe_binary_version",
                    return_value={"status": "available", "path": "/usr/bin/tool", "version": "tool 1.0"},
                ),
                patch("hivemind.harness.probe_network", return_value={"status": "reachable", "target": "1.1.1.1:53"}),
                patch("hivemind.harness.local_runtime_report", return_value=local_runtime),
            ):
                report = doctor_scope_report(root, "all")
                formatted = format_doctor_scope(report)

            self.assertEqual(report["scope"], "all")
            self.assertIn("providers", report["reports"])
            self.assertIn("hardware", report["reports"])
            self.assertIn("models", report["reports"])
            self.assertIn("permissions", report["reports"])
            self.assertIn("Hardware:", formatted)
            self.assertIn("Permissions:", formatted)


if __name__ == "__main__":
    unittest.main()
