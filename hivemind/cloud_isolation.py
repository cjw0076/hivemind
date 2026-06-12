"""Hosted runtime isolation receipts for Hive execution.

The receipt is intentionally separate from provider stdout/stderr artifacts.
It describes the execution boundary a hosted worker is allowed to use and
fails closed when the sandbox boundary is not proven.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .dag_state import atomic_write
from .utils import now_iso


SCHEMA_VERSION = "aios.hive_runtime_isolation_receipt.v1"

ALLOWED_NETWORK_POLICIES = {"denied", "loopback_only", "egress_allowlist", "unrestricted_with_override"}
ALLOWED_STATUSES = {"success", "degraded", "blocked"}
RAW_BODY_FIELDS = {"raw_prompt", "raw_output", "raw_transcript", "provider_stdout", "provider_stderr"}
SECRET_LIKE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|AKIA[0-9A-Z]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class RuntimeIsolationReceipt:
    schema_version: str
    run_id: str
    work_id: str
    provider: str
    model_or_worker: str
    filesystem_scope: dict[str, Any]
    process_scope: dict[str, Any]
    network_policy: str
    package_manifest: dict[str, Any]
    timeout_s: int
    credential_refs: list[str]
    sandbox_backend: str
    started_at: str
    ended_at: str
    status: str
    degraded_reason: str
    verification_refs: list[str] = field(default_factory=list)
    override_reason: str = ""


def build_runtime_isolation_receipt(
    *,
    run_id: str,
    work_id: str,
    provider: str,
    model_or_worker: str,
    filesystem_scope: dict[str, Any],
    process_scope: dict[str, Any],
    network_policy: str,
    package_manifest: dict[str, Any],
    timeout_s: int,
    credential_refs: list[str] | None = None,
    sandbox_backend: str = "",
    started_at: str | None = None,
    ended_at: str | None = None,
    verification_refs: list[str] | None = None,
    override_reason: str = "",
) -> RuntimeIsolationReceipt:
    """Build a fail-closed hosted isolation receipt.

    A missing sandbox backend means Hive cannot prove hosted isolation. The
    only way to avoid `blocked` is an explicit override reason naming that risk.
    """
    status = "success"
    degraded_reason = ""
    if not sandbox_backend.strip():
        if override_reason.strip():
            status = "degraded"
            degraded_reason = "sandbox_backend_missing_with_explicit_override"
        else:
            status = "blocked"
            degraded_reason = "sandbox_backend_missing_fail_closed"
    elif network_policy == "unrestricted_with_override" and not override_reason.strip():
        status = "blocked"
        degraded_reason = "unrestricted_network_requires_override"

    return RuntimeIsolationReceipt(
        schema_version=SCHEMA_VERSION,
        run_id=run_id,
        work_id=work_id,
        provider=provider,
        model_or_worker=model_or_worker,
        filesystem_scope=filesystem_scope,
        process_scope=process_scope,
        network_policy=network_policy,
        package_manifest=package_manifest,
        timeout_s=timeout_s,
        credential_refs=credential_refs or [],
        sandbox_backend=sandbox_backend,
        started_at=started_at or now_iso(),
        ended_at=ended_at or now_iso(),
        status=status,
        degraded_reason=degraded_reason,
        verification_refs=verification_refs or [],
        override_reason=override_reason,
    )


def receipt_path(run_dir: Path, work_id: str) -> Path:
    safe_work_id = work_id.replace("/", "_").replace(" ", "_")
    return run_dir / "runtime_isolation" / f"{safe_work_id}.json"


def write_runtime_isolation_receipt(run_dir: Path, receipt: RuntimeIsolationReceipt) -> Path:
    path = receipt_path(run_dir, receipt.work_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(asdict(receipt), ensure_ascii=False, indent=2, sort_keys=True))
    return path


def validate_runtime_isolation_receipt(data: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required = set(RuntimeIsolationReceipt.__dataclass_fields__)
    missing = sorted(required - set(data))
    if missing:
        issues.append(f"missing required keys: {', '.join(missing)}")
        return issues
    if data.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"invalid schema_version: {data.get('schema_version')}")
    if data.get("network_policy") not in ALLOWED_NETWORK_POLICIES:
        issues.append(f"invalid network_policy: {data.get('network_policy')}")
    if data.get("status") not in ALLOWED_STATUSES:
        issues.append(f"invalid status: {data.get('status')}")
    if not isinstance(data.get("timeout_s"), int) or data.get("timeout_s") <= 0:
        issues.append("timeout_s must be a positive integer")
    if not isinstance(data.get("filesystem_scope"), dict) or not data.get("filesystem_scope"):
        issues.append("filesystem_scope must be a non-empty object")
    if not isinstance(data.get("process_scope"), dict) or not data.get("process_scope"):
        issues.append("process_scope must be a non-empty object")
    if not isinstance(data.get("package_manifest"), dict) or not data.get("package_manifest"):
        issues.append("package_manifest must be a non-empty object")
    credential_refs = data.get("credential_refs")
    if not isinstance(credential_refs, list) or not all(isinstance(ref, str) and ref for ref in credential_refs):
        issues.append("credential_refs must be a list of non-empty strings")
    else:
        for ref in credential_refs:
            if _looks_like_secret_value(ref):
                issues.append("credential_refs must contain references, not credential values")
                break
    if not data.get("sandbox_backend") and data.get("status") != "blocked" and not data.get("override_reason"):
        issues.append("missing sandbox_backend must fail closed or include override_reason")
    if data.get("network_policy") == "unrestricted_with_override" and not data.get("override_reason"):
        issues.append("unrestricted network policy requires override_reason")
    for field in RAW_BODY_FIELDS:
        if field in data:
            issues.append(f"raw private/provider body field is forbidden: {field}")
    for key, value in data.items():
        if key in {"credential_refs", "schema_version"}:
            continue
        if isinstance(value, str) and _looks_like_secret_value(value):
            issues.append(f"secret-like value is forbidden in field: {key}")
    return issues


def load_runtime_isolation_receipt(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _looks_like_secret_value(value: str) -> bool:
    if value.startswith(("vault://", "env://", "secretref://", "credential://")):
        return False
    return bool(SECRET_LIKE.search(value))
