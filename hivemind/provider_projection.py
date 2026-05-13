"""Redacted provider-output projection artifacts for Hive runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import harness as h
from .run_receipts import load_receipt_yaml, provider_result_paths
from .utils import now_iso


SCHEMA_VERSION = "hive.provider_output_projection.v1"
ARTIFACT_NAME = "provider_output_projection.json"
COUNTED_PATH_KEYS = ("stdout_path", "stderr_path", "output_path")


def build_provider_output_projection(
    root: Path,
    run_id: str | None = None,
    *,
    show_paths: bool = False,
) -> dict[str, Any]:
    """Write provider receipt metadata without copying provider output bodies."""
    paths, state = h.load_run(root, run_id)
    rows = [
        project_provider_receipt(root, paths.run_dir, result_path, show_paths=show_paths)
        for result_path in provider_result_paths(paths.run_dir)
    ]
    artifact_path = paths.artifacts / ARTIFACT_NAME
    artifact_ref = artifact_path.relative_to(root).as_posix()
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "hive_provider_output_projection",
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "task": state.get("user_request"),
        "provider_result_count": len(rows),
        "providers": rows,
        "artifact": artifact_ref,
        "paths_hidden": not show_paths,
        "privacy": {
            "raw_provider_output_included": False,
            "stdout_included": False,
            "stderr_included": False,
            "output_body_included": False,
            "path_refs_hidden": not show_paths,
        },
    }
    h.write_json(artifact_path, report)
    artifacts = dict(state.get("artifacts") or {})
    artifacts["provider_output_projection"] = artifact_ref
    h.update_state(paths, artifacts=artifacts, latest_event="provider_output_projection_created")
    h.append_event(
        paths,
        "provider_output_projection_created",
        {
            "artifact": artifact_ref if show_paths else f"artifacts/{ARTIFACT_NAME}",
            "provider_result_count": len(rows),
        },
    )
    return report


def project_provider_receipt(root: Path, run_dir: Path, result_path: Path, *, show_paths: bool) -> dict[str, Any]:
    data = load_receipt_yaml(result_path)
    row: dict[str, Any] = {
        "provider": data.get("provider") or data.get("agent"),
        "agent": data.get("agent"),
        "role": data.get("role"),
        "status": data.get("status"),
        "provider_mode": data.get("provider_mode"),
        "permission_mode": data.get("permission_mode"),
        "returncode": data.get("returncode"),
        "risk_level": data.get("risk_level", "unknown"),
        "policy_violation_count": len(data.get("policy_violations") or []),
        "receipt_ref": _ref(root, result_path, show_paths=show_paths),
        "artifacts_created_count": len(data.get("artifacts_created") or []),
        "commands_run_count": len(data.get("commands_run") or []),
        "tests_run_count": len(data.get("tests_run") or []),
        "privacy": {
            "raw_body_included": False,
            "path_refs_hidden": not show_paths,
        },
    }
    for key in COUNTED_PATH_KEYS:
        row[key.replace("_path", "")] = artifact_stats(
            root,
            data.get(key),
            show_paths=show_paths,
        )
    return row


def artifact_stats(root: Path, raw_ref: Any, *, show_paths: bool) -> dict[str, Any]:
    ref = str(raw_ref or "").strip()
    path = root / ref if ref else None
    exists = bool(path and path.exists() and path.is_file())
    stats: dict[str, Any] = {
        "present": exists,
        "bytes": 0,
        "lines": 0,
        "body_included": False,
    }
    if exists and path is not None:
        try:
            body = path.read_bytes()
        except OSError:
            body = b""
        stats["bytes"] = len(body)
        stats["lines"] = body.count(b"\n") + (1 if body and not body.endswith(b"\n") else 0)
    if show_paths and ref:
        stats["ref"] = ref
    return stats


def _ref(root: Path, path: Path, *, show_paths: bool) -> str:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    if show_paths:
        return rel
    try:
        return path.relative_to(root / h.RUNS_DIR).as_posix()
    except ValueError:
        return path.name


def format_provider_output_projection(report: dict[str, Any]) -> str:
    lines = [
        "Hive Provider Output Projection",
        f"Run: {report.get('run_id')}",
        f"Providers: {report.get('provider_result_count')}",
        f"Artifact: {report.get('artifact')}",
        "",
        "Privacy:",
        f"- raw_provider_output_included: {report.get('privacy', {}).get('raw_provider_output_included')}",
        "",
        "Rows:",
    ]
    for row in report.get("providers") or []:
        lines.append(
            f"- {row.get('provider')} {row.get('role')} {row.get('status')} "
            f"stdout={row.get('stdout', {}).get('bytes')}B "
            f"stderr={row.get('stderr', {}).get('bytes')}B"
        )
    if not report.get("providers"):
        lines.append("- none")
    return "\n".join(lines)
