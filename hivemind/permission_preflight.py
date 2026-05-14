from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "hivemind.permission_preflight.v1"
CONSTRAINT_BREAK_CONTRACT = "capabilityos.constraint_break_route.v1"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_route(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("route JSON must be an object")
    return data


def build_permission_preflight(route: dict[str, Any]) -> dict[str, Any]:
    if route.get("contract") != CONSTRAINT_BREAK_CONTRACT:
        raise ValueError("expected capabilityos.constraint_break_route.v1")
    execution_policy = route.get("execution_policy") if isinstance(route.get("execution_policy"), dict) else {}
    permission_questions = route.get("permission_questions") if isinstance(route.get("permission_questions"), list) else []
    capabilityos_executes = bool(execution_policy.get("capabilityos_executes_tools"))
    executor = str(execution_policy.get("executor") or "")
    stop_conditions: list[str] = []
    if capabilityos_executes:
        stop_conditions.append("capabilityos_execution_requested")
    if executor != "hivemind":
        stop_conditions.append("hive_executor_missing")
    if not permission_questions:
        stop_conditions.append("permission_questions_missing")
    status = "blocked" if capabilityos_executes else "operator_checkpoint_required"
    if stop_conditions and not capabilityos_executes:
        status = "held"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "status": status,
        "executor": "hivemind",
        "source_contract": route.get("contract"),
        "task": route.get("task"),
        "blocker": route.get("blocker"),
        "permission_questions": permission_questions,
        "unblock_options": route.get("unblock_options") if isinstance(route.get("unblock_options"), list) else [],
        "execution_policy": {
            "executor": "hivemind",
            "execute_now": False,
            "requires_operator_grant": True,
            "capabilityos_executes_tools": capabilityos_executes,
        },
        "privacy_policy": route.get("privacy_policy") if isinstance(route.get("privacy_policy"), dict) else {},
        "risk_notes": route.get("risk_notes") if isinstance(route.get("risk_notes"), list) else [],
        "stop_conditions_triggered": stop_conditions,
    }


def build_permission_preflight_from_path(path: str | Path) -> dict[str, Any]:
    return build_permission_preflight(load_route(path))


def format_permission_preflight(payload: dict[str, Any]) -> str:
    lines = [
        f"status: {payload.get('status')}",
        f"executor: {payload.get('executor')}",
        f"task: {payload.get('task')}",
        f"blocker: {payload.get('blocker')}",
        "permission_questions:",
    ]
    for question in payload.get("permission_questions") or []:
        if isinstance(question, dict):
            lines.append(f"- {question.get('permission_id')}: {question.get('question')}")
    return "\n".join(lines)
