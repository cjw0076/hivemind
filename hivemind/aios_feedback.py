"""Friction/needs feedback channel from Hive AIOS contracts to the myworld big-brain.

Each AIOS contract surfaces what HiveMind, MemoryOS, and CapabilityOS *couldn't*
do for the goal — empty recommendations, missing memories, route mismatches.
This module turns those gaps into structured ``friction`` items and writes a
feedback packet to ``../.aios/outbox/myworld/`` so the AIOS control plane can
absorb them into the next contract iteration.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .utils import now_iso


SCHEMA_VERSION = 1
KIND = "aios_feedback_report"
COMPLETION_FILENAME = "aios_completion.json"


def extract_friction(contract: dict[str, Any]) -> dict[str, Any]:
    """Build a per-OS friction/needs report from an AIOS contract."""
    proposals = contract.get("proposals") or {}
    conflicts = contract.get("conflicts") or []
    return {
        "hivemind": _hivemind_friction(proposals.get("hivemind") or {}, conflicts),
        "memoryos": _memoryos_friction(proposals.get("memoryos") or {}),
        "capabilityos": _capabilityos_friction(
            proposals.get("capabilityos") or {}, proposals.get("hivemind") or {}
        ),
    }


def _hivemind_friction(hivemind: dict[str, Any], conflicts: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    if hivemind.get("status") != "ok":
        items.append({
            "kind": "empty_society_plan",
            "severity": "high",
            "detail": "HiveMind produced no society members for the goal.",
            "need": "router heuristics or provider catalog do not cover this goal type — operator should review intent classification.",
        })
    for conflict in conflicts:
        if conflict.get("kind") == "provider_route_mismatch":
            items.append({
                "kind": "provider_route_mismatch",
                "severity": conflict.get("severity", "medium"),
                "detail": conflict.get("detail"),
                "need": "align CapabilityOS provider hints with HiveMind society plan, or adjust router to surface the recommended providers.",
            })
    return {
        "items": items,
        "providers": list(hivemind.get("providers") or []),
        "member_count": hivemind.get("member_count", 0),
    }


def _memoryos_friction(memoryos: dict[str, Any]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    status = memoryos.get("status")
    if status in {"unavailable", "failed"}:
        items.append({
            "kind": "memoryos_unavailable",
            "severity": "low",
            "detail": f"MemoryOS bridge status={status}.",
            "need": "ensure ../memoryOS source exists and HIVE_MEMORYOS_SOURCE_ROOT resolves, or accept that runs proceed without accepted memory.",
        })
    accepted = memoryos.get("accepted_memory_ids") or []
    context_items = memoryos.get("context_items") or 0
    if status in {"available", "empty"} and not accepted:
        items.append({
            "kind": "no_accepted_memory",
            "severity": "medium",
            "detail": f"MemoryOS returned 0 accepted memories (context_items={context_items}).",
            "need": "operator should review and approve relevant memory drafts, or import a primer for this domain.",
        })
    return {
        "items": items,
        "context_items": context_items,
        "accepted_memory_ids": list(accepted),
    }


def _capabilityos_friction(
    capabilityos: dict[str, Any], hivemind: dict[str, Any]
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    status = capabilityos.get("status")
    if status in {"unavailable", "failed"}:
        items.append({
            "kind": "capabilityos_unavailable",
            "severity": "medium",
            "detail": f"CapabilityOS bridge status={status}.",
            "need": "ensure ../CapabilityOS source exists and HIVE_CAPABILITYOS_SOURCE_ROOT resolves.",
        })
    recommendation_count = capabilityos.get("recommendation_count") or 0
    if status in {"ok", "empty"} and recommendation_count == 0:
        items.append({
            "kind": "no_capability_card",
            "severity": "medium",
            "detail": "CapabilityOS returned 0 recommendations for the goal kind.",
            "need": "add a CapabilityCard whose kind/keywords match this goal, or extend the recommend heuristic.",
        })
    cap_providers = set(capabilityos.get("providers") or [])
    hive_providers = set(hivemind.get("providers") or [])
    if cap_providers and not (cap_providers & hive_providers):
        items.append({
            "kind": "providers_not_routed",
            "severity": "low",
            "detail": f"CapabilityOS hints {sorted(cap_providers)} not present in HiveMind plan {sorted(hive_providers)}.",
            "need": "either accept the divergence or update the router so suggested providers participate.",
        })
    return {
        "items": items,
        "recommendation_count": recommendation_count,
        "kinds": list(capabilityos.get("kinds") or []),
    }


def aggregate_needs(friction: dict[str, Any]) -> list[dict[str, str]]:
    """Flatten per-OS friction into a single needs list for the big brain."""
    needs: list[dict[str, str]] = []
    for source, payload in friction.items():
        for item in payload.get("items") or []:
            need = item.get("need")
            if not need:
                continue
            needs.append({
                "source": source,
                "kind": item.get("kind", "unknown"),
                "severity": item.get("severity", "low"),
                "need": need,
            })
    return needs


def has_blocking_friction(friction: dict[str, Any]) -> bool:
    """True when any OS reports a medium/high-severity friction item."""
    for payload in friction.values():
        for item in payload.get("items") or []:
            if item.get("severity") in {"medium", "high"}:
                return True
    return False


def write_feedback_packet(
    root: Path,
    contract: dict[str, Any],
    friction: dict[str, Any],
    generation: int,
) -> dict[str, Any]:
    """Write a feedback packet to ``../.aios/outbox/myworld/`` if myworld is reachable.

    Returns a dict describing whether the packet was written and where.
    """
    needs = aggregate_needs(friction)
    packet = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "source": "hivemind",
        "target_repo": "myworld",
        "agent": "claude@hivemind",
        "generated_at": now_iso(),
        "generation": generation,
        "run_id": contract.get("run_id"),
        "contract_id": contract.get("contract_id"),
        "goal": contract.get("goal"),
        "status": contract.get("status"),
        "signed_by": contract.get("signed_by"),
        "friction": friction,
        "needs": needs,
        "completion_signal": _completion_signal_hint(root),
    }
    outbox = _myworld_outbox(root)
    if outbox is None:
        return {"written": False, "reason": "myworld_outbox_unreachable", "packet": packet}
    outbox.mkdir(parents=True, exist_ok=True)
    filename = f"aios-feedback-{contract.get('run_id') or 'unknown'}-gen{generation:02d}.hivemind.report.json"
    out_path = outbox / filename
    out_path.write_text(
        json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "written": True,
        "path": str(out_path),
        "needs_count": len(needs),
        "friction_kinds": sorted({
            item.get("kind")
            for payload in friction.values()
            for item in payload.get("items") or []
        }),
        "packet": packet,
    }


def is_complete(root: Path, goal: str) -> dict[str, Any]:
    """Inspect ``.hivemind/aios_completion.json`` for a big-brain completion signal.

    The completion file is operator-written. It can be a global mark or list of
    goal patterns. Auto-convergence is decided elsewhere (zero friction).
    """
    completion_path = root / ".hivemind" / COMPLETION_FILENAME
    if not completion_path.exists():
        return {"complete": False, "reason": "no_completion_file", "path": str(completion_path)}
    try:
        payload = json.loads(completion_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"complete": False, "reason": f"completion_file_unreadable: {exc}", "path": str(completion_path)}
    if not isinstance(payload, dict):
        return {"complete": False, "reason": "completion_file_not_object", "path": str(completion_path)}
    if payload.get("all_goals") is True:
        return {"complete": True, "reason": "all_goals_marked_complete", "payload": payload}
    patterns = payload.get("goal_patterns") or []
    if not isinstance(patterns, list):
        return {"complete": False, "reason": "goal_patterns_not_list", "payload": payload}
    for pattern in patterns:
        if not isinstance(pattern, str):
            continue
        try:
            if re.search(pattern, goal, flags=re.IGNORECASE):
                return {"complete": True, "reason": "goal_pattern_match", "matched": pattern, "payload": payload}
        except re.error:
            if pattern.lower() in goal.lower():
                return {"complete": True, "reason": "goal_substring_match", "matched": pattern, "payload": payload}
    return {"complete": False, "reason": "no_pattern_match", "payload": payload}


def _completion_signal_hint(root: Path) -> dict[str, str]:
    return {
        "path": (root / ".hivemind" / COMPLETION_FILENAME).as_posix(),
        "schema": "{ all_goals?: bool, goal_patterns?: [regex|substring] }",
        "writer": "operator (big brain)",
    }


def _myworld_outbox(root: Path) -> Path | None:
    """Resolve the myworld outbox path next to the hivemind workspace, if present."""
    override = os.environ.get("HIVE_MYWORLD_AIOS_ROOT")
    if override:
        candidate = Path(override).resolve() / ".aios" / "outbox" / "myworld"
        return candidate
    candidate = root.parent / ".aios" / "outbox" / "myworld"
    if (root.parent / ".aios").exists():
        return candidate
    return None
