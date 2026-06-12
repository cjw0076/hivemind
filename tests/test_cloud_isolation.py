import json
import tempfile
import unittest
from pathlib import Path

from hivemind.cloud_isolation import (
    SCHEMA_VERSION,
    build_runtime_isolation_receipt,
    load_runtime_isolation_receipt,
    validate_runtime_isolation_receipt,
    write_runtime_isolation_receipt,
)


def base_receipt(**overrides):
    params = {
        "run_id": "run_20260612_000000_abcdef",
        "work_id": "asc-0240-smoke",
        "provider": "codex",
        "model_or_worker": "codex-cli",
        "filesystem_scope": {
            "mode": "workspace",
            "read_roots": ["."],
            "write_roots": [".runs/run_20260612_000000_abcdef"],
        },
        "process_scope": {"max_processes": 4, "kill_tree_on_timeout": True},
        "network_policy": "denied",
        "package_manifest": {"python": "3.12", "packages": []},
        "timeout_s": 60,
        "credential_refs": ["vault://github/pat"],
        "sandbox_backend": "local-subprocess-policy",
        "verification_refs": ["tests/test_cloud_isolation.py"],
    }
    params.update(overrides)
    return build_runtime_isolation_receipt(**params)


class CloudIsolationTest(unittest.TestCase):
    def test_local_sandboxed_run_emits_runtime_scope_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / ".runs" / "run_20260612_000000_abcdef"
            receipt = base_receipt()
            path = write_runtime_isolation_receipt(run_dir, receipt)
            data = load_runtime_isolation_receipt(path)

        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["network_policy"], "denied")
        self.assertEqual(validate_runtime_isolation_receipt(data), [])

    def test_network_denied_policy_is_recorded(self) -> None:
        data = json.loads(json.dumps(base_receipt(), default=lambda obj: obj.__dict__))

        self.assertEqual(data["network_policy"], "denied")
        self.assertEqual(validate_runtime_isolation_receipt(data), [])

    def test_missing_sandbox_backend_fails_closed_without_override(self) -> None:
        receipt = base_receipt(sandbox_backend="")
        data = json.loads(json.dumps(receipt, default=lambda obj: obj.__dict__))

        self.assertEqual(data["status"], "blocked")
        self.assertEqual(data["degraded_reason"], "sandbox_backend_missing_fail_closed")
        self.assertEqual(validate_runtime_isolation_receipt(data), [])

    def test_missing_sandbox_backend_can_degrade_with_explicit_override(self) -> None:
        receipt = base_receipt(
            sandbox_backend="",
            override_reason="operator accepted missing sandbox backend for dry-run receipt only",
        )
        data = json.loads(json.dumps(receipt, default=lambda obj: obj.__dict__))

        self.assertEqual(data["status"], "degraded")
        self.assertEqual(data["degraded_reason"], "sandbox_backend_missing_with_explicit_override")
        self.assertEqual(validate_runtime_isolation_receipt(data), [])

    def test_credential_refs_allow_refs_and_reject_values(self) -> None:
        ok = json.loads(json.dumps(base_receipt(credential_refs=["env://OPENAI_API_KEY"]), default=lambda obj: obj.__dict__))
        bad = json.loads(json.dumps(base_receipt(credential_refs=["sk-this-is-a-secret-value"]), default=lambda obj: obj.__dict__))

        self.assertEqual(validate_runtime_isolation_receipt(ok), [])
        self.assertIn("credential_refs must contain references", "\n".join(validate_runtime_isolation_receipt(bad)))

    def test_raw_provider_body_fields_are_rejected(self) -> None:
        data = json.loads(json.dumps(base_receipt(), default=lambda obj: obj.__dict__))
        data["raw_transcript"] = "private provider body"

        self.assertIn("raw private/provider body field is forbidden", "\n".join(validate_runtime_isolation_receipt(data)))


if __name__ == "__main__":
    unittest.main()
