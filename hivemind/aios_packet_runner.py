from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .provider_loop import prepare_provider_loop, tick_provider_loop


SCHEMA_VERSION = "hive.aios_packet_runner.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_packet(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("AIOS packet must be a JSON object")
    return payload


def packet_prompt(packet: dict[str, Any]) -> str:
    reading = "\n".join(f"- {item}" for item in packet.get("required_reading") or [])
    allowed = json.dumps(packet.get("scope", {}).get("allowed_files", []), ensure_ascii=False)
    forbidden = json.dumps(packet.get("scope", {}).get("forbidden_files", []), ensure_ascii=False)
    return "\n".join(
        [
            "You are Hive Mind executing an AIOS dispatch packet.",
            "",
            f"Contract: {packet.get('contract_id')}",
            f"Dispatch: {packet.get('dispatch_id')}",
            f"Target repo: {packet.get('target_repo')}",
            "",
            "Goal:",
            str(packet.get("goal") or "").strip(),
            "",
            "Required reading:",
            reading,
            "",
            "Allowed files JSON:",
            allowed,
            "",
            "Forbidden files JSON:",
            forbidden,
            "",
            "Rules:",
            "- Work only inside the target repo and allowed files.",
            "- Preserve user and agent changes you did not make.",
            "- Do not store secrets, raw private exports, provider credentials, or private transcripts.",
            "- Run the packet verification commands when implementation is complete.",
            "- Write concise evidence for the result packet.",
            "- Stop at a checkpoint if ownership, scope, or authority is ambiguous.",
        ]
    )


def resolve_return_path(packet: dict[str, Any], myworld_root: Path | None) -> Path | None:
    value = packet.get("return_to")
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    if myworld_root is None:
        return None
    return myworld_root / path


def write_result(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_aios_packet(
    *,
    hive_root: Path,
    packet_path: str | Path,
    myworld_root: Path | None = None,
    provider: str | None = None,
    execute: bool = False,
    writable_provider_execution: bool = False,
    dangerous_full_access: bool = False,
    operator_grant: str | None = None,
    write_result_packet: bool = False,
) -> dict[str, Any]:
    packet = read_packet(packet_path)
    stop_conditions: list[str] = []
    if packet.get("target_repo") != "hivemind":
        stop_conditions.append("target_repo_not_hivemind")
    selected_provider = provider or str(packet.get("agent") or "local")
    grant = str(operator_grant or "").strip()
    if writable_provider_execution and not execute:
        stop_conditions.append("writable_requires_execute")
    if dangerous_full_access and not execute:
        stop_conditions.append("dangerous_requires_execute")
    if writable_provider_execution and dangerous_full_access:
        stop_conditions.append("conflicting_provider_permission_modes")
    if writable_provider_execution and selected_provider != "codex":
        stop_conditions.append("writable_provider_only_codex_supported")
    if dangerous_full_access and selected_provider != "codex":
        stop_conditions.append("dangerous_provider_only_codex_supported")
    if (writable_provider_execution or dangerous_full_access) and not grant:
        stop_conditions.append("operator_grant_missing")
    if dangerous_full_access and grant and not _explicit_dangerous_grant(grant):
        stop_conditions.append("dangerous_operator_grant_not_explicit")
    prompt = packet_prompt(packet)
    prepared = None
    tick = None
    status = "held" if stop_conditions else "prepared"
    if not stop_conditions:
        prepared = prepare_provider_loop(hive_root, selected_provider, prompt)
        tick = tick_provider_loop(
            hive_root,
            worker_id=prepared["worker_id"],
            execute=execute,
            allow_workspace_write=writable_provider_execution,
            workspace_write_grant=grant or None,
            allow_dangerous_full_access=dangerous_full_access,
            dangerous_grant=grant or None,
        )
        status = "executed" if execute and tick.get("status") in {"completed", "done", "passed"} else "prepared"
        if tick.get("status") in {"failed", "timeout"}:
            status = "held"
            stop_conditions.append("provider_tick_failed")
    result = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "status": status,
        "packet": str(packet_path),
        "contract_id": packet.get("contract_id"),
        "dispatch_id": packet.get("dispatch_id"),
        "target_repo": packet.get("target_repo"),
        "provider": selected_provider,
        "execute_requested": execute,
        "writable_provider_execution": writable_provider_execution,
        "dangerous_full_access": dangerous_full_access,
        "operator_grant": grant or None,
        "provider_loop_prepared": prepared,
        "provider_loop_tick": tick,
        "stop_conditions_triggered": stop_conditions,
        "authority": {
            "executor": "hivemind",
            "writes_child_source_directly": False,
            "uses_provider_loop": True,
            "writable_provider_requires_operator_grant": True,
            "dangerous_full_access_requires_operator_grant": True,
        },
    }
    if write_result_packet:
        return_path = resolve_return_path(packet, myworld_root)
        if return_path is None:
            result["status"] = "held"
            result["stop_conditions_triggered"].append("return_path_missing")
        else:
            write_result(return_path, result)
            result["result_path"] = return_path.as_posix()
    return result


def _explicit_dangerous_grant(grant: str) -> bool:
    lowered = grant.lower()
    return "dangerous" in lowered and ("full-access" in lowered or "full access" in lowered)
