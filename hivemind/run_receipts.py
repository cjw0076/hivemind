"""Provider/local run receipt helpers for Hive execution artifacts."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import yaml

from .utils import now_iso


WORKING_METHOD_PHRASE = "evolution of Single Human Intelligence"


def rel_or_empty(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def git_changed_files(root: Path) -> list[str]:
    try:
        result = subprocess.run(["git", "status", "--short"], cwd=root, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return []
    files: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        files.append(line[3:].strip() if len(line) > 3 else line.strip())
    return files


def provider_result_record(
    root: Path,
    *,
    agent: str,
    role: str,
    status: str,
    provider_mode: str,
    permission_mode: str,
    prompt_path: Path | None = None,
    command_path: Path | None = None,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    output_path: Path | None = None,
    returncode: int | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    duration_ms: int | None = None,
    files_changed: list[str] | None = None,
    commands_run: list[str] | None = None,
    tests_run: list[str] | None = None,
    artifacts_created: list[str] | None = None,
    risk_level: str = "low",
    policy_violations: list[str] | None = None,
    memory_refs_used: list[str] | None = None,
    capability_refs_used: list[str] | None = None,
    execute: bool | None = None,
    provider_status: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "provider": agent,
        "agent": agent,
        "role": role,
        "status": status,
        "provider_mode": provider_mode,
        "permission_mode": permission_mode,
        "provider_status": provider_status or "",
        "prompt_path": rel_or_empty(root, prompt_path),
        "command_path": rel_or_empty(root, command_path),
        "stdout_path": rel_or_empty(root, stdout_path),
        "stderr_path": rel_or_empty(root, stderr_path),
        "output_path": rel_or_empty(root, output_path),
        "prompt": rel_or_empty(root, prompt_path),
        "command": rel_or_empty(root, command_path),
        "output": rel_or_empty(root, output_path),
        "returncode": returncode,
        "started_at": started_at or "",
        "finished_at": finished_at or now_iso(),
        "duration_ms": duration_ms,
        "files_changed": files_changed if files_changed is not None else git_changed_files(root),
        "commands_run": commands_run or [],
        "tests_run": tests_run or [],
        "artifacts_created": artifacts_created or [],
        "risk_level": risk_level,
        "policy_violations": policy_violations or [],
        "memory_refs_used": memory_refs_used or [],
        "capability_refs_used": capability_refs_used or [],
        "execute": execute,
        "reason": reason or "",
        "working_method": WORKING_METHOD_PHRASE,
    }


def provider_result_paths(run_dir: Path) -> list[Path]:
    agents_dir = run_dir / "agents"
    if not agents_dir.exists():
        return []
    return sorted(agents_dir.rglob("*_result.yaml"))


def load_receipt_yaml(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def collect_provider_results(root: Path, run_dir: Path, *, show_paths: bool) -> list[dict[str, Any]]:
    """Collect provider receipts recursively, including native passthrough runs."""
    results: list[dict[str, Any]] = []
    for result_path in provider_result_paths(run_dir):
        data = load_receipt_yaml(result_path)
        item = {
            "agent": data.get("agent"),
            "role": data.get("role"),
            "status": data.get("status"),
            "provider_mode": data.get("provider_mode"),
            "permission_mode": data.get("permission_mode"),
            "returncode": data.get("returncode"),
            "risk_level": data.get("risk_level", "unknown"),
            "policy_violations": data.get("policy_violations") or [],
            "files_changed": data.get("files_changed") or [],
            "commands_run": data.get("commands_run") or [],
            "tests_run": data.get("tests_run") or [],
        }
        if show_paths:
            item["path"] = result_path.relative_to(root).as_posix()
            for key in ("command_path", "stdout_path", "stderr_path", "output_path", "prompt_path"):
                if data.get(key):
                    item[key] = data.get(key)
        results.append(item)
    return results
