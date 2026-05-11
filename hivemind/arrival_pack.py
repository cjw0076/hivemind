"""Incoming-agent arrival brief built from Hive run state."""

from __future__ import annotations

from typing import Any

from .harness import now_iso
from .inspect_run import build_inspect_report


SCHEMA_VERSION = "hive.arrival_pack.v1"


def build_arrival_pack(
    root,
    run_id: str | None = None,
    *,
    role: str = "agent",
    show_paths: bool = False,
) -> dict[str, Any]:
    """Build a compact, privacy-safe brief for an incoming agent."""
    report = build_inspect_report(root, run_id, show_paths=show_paths)
    actual_run_id = str(report.get("run_id") or "")
    live_agents = (report.get("health") or {}) if isinstance(report.get("health"), dict) else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "hive_arrival_pack",
        "generated_at": now_iso(),
        "run_id": actual_run_id,
        "role": role,
        "objective": report.get("task"),
        "status": report.get("status"),
        "phase": report.get("phase"),
        "health": report.get("health"),
        "verdict": report.get("verdict"),
        "owners": build_owners(role),
        "agents": summarize_agents(report, live_agents),
        "blocked_items": blocked_items(report),
        "accepted_claims": accepted_claims(report),
        "contested_claims": contested_claims(report),
        "scope_hints": scope_hints(report, show_paths=show_paths),
        "latest_artifacts": latest_artifacts(report, show_paths=show_paths),
        "suggested_commands": suggested_commands(actual_run_id),
        "privacy": {
            "paths_hidden": not show_paths,
            "raw_stdout_included": False,
            "raw_stderr_included": False,
            "raw_provider_body_included": False,
            "path_debug_flag": "--paths",
        },
        "sources": [
            {"kind": "inspect_report", "command": f"hive inspect {actual_run_id} --json"},
            {"kind": "live_report", "command": f"hive live --run-id {actual_run_id} --json"},
        ],
    }


def build_owners(role: str) -> dict[str, str]:
    return {
        "execution_authority": "Hive Mind",
        "incoming_agent": role,
        "operator": "myworld control plane",
        "memory_owner": "MemoryOS",
        "capability_owner": "CapabilityOS",
    }


def summarize_agents(report: dict[str, Any], health: dict[str, Any]) -> list[dict[str, Any]]:
    agent_summary = []
    missing = health.get("missing_required") if isinstance(health, dict) else None
    if missing:
        agent_summary.append({"name": "required_artifacts", "status": "missing", "items": list(missing)})
    authority = report.get("authority") or {}
    if any(authority.get(key) for key in ("intent_count", "vote_count", "decision_count", "proof_count")):
        agent_summary.append(
            {
                "name": "authority",
                "status": "observed",
                "intents": authority.get("intent_count", 0),
                "votes": authority.get("vote_count", 0),
                "decisions": authority.get("decision_count", 0),
                "proofs": authority.get("proof_count", 0),
            }
        )
    if not agent_summary:
        agent_summary.append({"name": "hive", "status": "planned"})
    return agent_summary


def blocked_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    ledger = report.get("ledger") or {}
    if ledger.get("hash_chain_ok") is False and (ledger.get("record_count") or 0) > 0:
        items.append({"kind": "ledger", "severity": "critical", "reason": "ledger hash chain drift"})
    elif ledger.get("ok") is False and (ledger.get("record_count") or 0) > 0:
        items.append({"kind": "ledger", "severity": "medium", "reason": "ledger replay has issues"})

    for receipt in report.get("provider_results") or []:
        if receipt.get("status") in {"failed", "timeout", "partial"}:
            items.append(
                {
                    "kind": "provider_result",
                    "severity": "medium",
                    "agent": receipt.get("agent"),
                    "role": receipt.get("role"),
                    "status": receipt.get("status"),
                }
            )
    for receipt in report.get("local_worker_results") or []:
        if receipt.get("status") in {"failed", "timeout", "partial", "skipped"} or receipt.get("should_escalate"):
            items.append(
                {
                    "kind": "local_worker_result",
                    "severity": "medium",
                    "role": receipt.get("role"),
                    "status": receipt.get("status"),
                    "reason": receipt.get("escalation_reason") or "",
                }
            )
    if (report.get("proofs") or {}).get("failed_count"):
        items.append({"kind": "execution_proof", "severity": "high", "reason": "failed or flagged proof"})
    if (report.get("disagreements") or {}).get("high_severity_count"):
        items.append({"kind": "disagreement", "severity": "high", "reason": "high/medium disagreement topology"})
    audit = report.get("audit") or {}
    if audit.get("validation_verdict") not in {None, "pass"}:
        items.append({"kind": "validation", "severity": "medium", "reason": "run validation is not passing"})
    return items


def accepted_claims(report: dict[str, Any]) -> list[dict[str, Any]]:
    ledger = report.get("ledger") or {}
    memoryos = report.get("memoryos_context") or {}
    ledger_acceptable = ledger.get("ok") is not False or (ledger.get("record_count") or 0) == 0
    claims = [
        {"claim": "run_state_loaded", "status": "accepted", "evidence": "hive run state"},
        {"claim": "objective_known", "status": "accepted", "value": report.get("task")},
        {"claim": "inspection_verdict", "status": "accepted", "value": report.get("verdict")},
        {
            "claim": "ledger_replayed",
            "status": "accepted" if ledger_acceptable else "needs_review",
            "record_count": ledger.get("record_count"),
            "hash_chain_ok": ledger.get("hash_chain_ok"),
        },
    ]
    if memoryos.get("status") not in {None, "missing"}:
        claims.append(
            {
                "claim": "memoryos_context_attached",
                "status": "accepted",
                "trace_id": memoryos.get("trace_id"),
                "selected_memory_count": memoryos.get("selected_memory_count", 0),
            }
        )
    else:
        claims.append(
            {
                "claim": "memoryos_context_optional_or_absent",
                "status": "accepted",
                "selected_memory_count": 0,
            }
        )
    return claims


def contested_claims(report: dict[str, Any]) -> list[dict[str, Any]]:
    records = (report.get("disagreements") or {}).get("records") or []
    return [
        {
            "step_id": item.get("step_id"),
            "topology_type": item.get("topology_type"),
            "severity": item.get("severity"),
            "axes": item.get("axes") or [],
            "dominant_axis": item.get("dominant_axis"),
            "recommended_action": item.get("recommended_action"),
        }
        for item in records
    ]


def scope_hints(report: dict[str, Any], *, show_paths: bool) -> dict[str, Any]:
    recommendations = list(report.get("recommendations") or [])
    if ((report.get("ledger") or {}).get("record_count") or 0) == 0:
        recommendations = [item for item in recommendations if item != "ledger replay needs review"]
    return {
        "paths_hidden": not show_paths,
        "default_scope": "read current run artifacts before editing",
        "privacy_rule": "do not paste raw provider stdout/stderr or private exports",
        "next_action": report.get("next") or {},
        "recommendations": recommendations,
    }


def latest_artifacts(report: dict[str, Any], *, show_paths: bool) -> list[dict[str, Any]]:
    ledger = report.get("ledger") or {}
    ledger_record_count = ledger.get("record_count") or 0
    ledger_status = "ok" if ledger.get("ok") or ledger_record_count == 0 else "needs_review"
    artifacts: list[dict[str, Any]] = [
        {
            "kind": "ledger",
            "status": ledger_status,
            "record_count": ledger_record_count,
            "issue_count": ledger.get("issue_count", 0),
        },
        {
            "kind": "memoryos_context",
            "status": (report.get("memoryos_context") or {}).get("status"),
            "trace_id": (report.get("memoryos_context") or {}).get("trace_id"),
            "selected_memory_count": (report.get("memoryos_context") or {}).get("selected_memory_count", 0),
        },
        {
            "kind": "execution_proofs",
            "status": "present" if (report.get("proofs") or {}).get("count") else "missing",
            "count": (report.get("proofs") or {}).get("count", 0),
            "failed_count": (report.get("proofs") or {}).get("failed_count", 0),
        },
        {
            "kind": "disagreements",
            "status": "present" if (report.get("disagreements") or {}).get("count") else "none",
            "count": (report.get("disagreements") or {}).get("count", 0),
            "high_severity_count": (report.get("disagreements") or {}).get("high_severity_count", 0),
        },
    ]
    for receipt in report.get("provider_results") or []:
        item = {
            "kind": "provider_result",
            "agent": receipt.get("agent"),
            "role": receipt.get("role"),
            "status": receipt.get("status"),
            "provider_mode": receipt.get("provider_mode"),
            "risk_level": receipt.get("risk_level"),
        }
        if show_paths and receipt.get("path"):
            item["path"] = receipt.get("path")
        artifacts.append(item)
    for receipt in report.get("local_worker_results") or []:
        item = {
            "kind": "local_worker_result",
            "role": receipt.get("role"),
            "status": receipt.get("status"),
            "runtime": receipt.get("runtime"),
            "worker": receipt.get("worker"),
            "output_valid": receipt.get("output_valid"),
        }
        if show_paths and receipt.get("path"):
            item["path"] = receipt.get("path")
        artifacts.append(item)
    return artifacts


def suggested_commands(run_id: str) -> list[dict[str, str]]:
    return [
        {"command": f"hive inspect {run_id} --json", "reason": "full receipt and verdict inspection"},
        {"command": f"hive live --run-id {run_id} --json", "reason": "prompt/log state without raw artifacts"},
        {"command": f"hive next --run-id {run_id} --json", "reason": "grounded next operator action"},
    ]


def format_arrival_pack(pack: dict[str, Any], *, show_paths: bool = False) -> str:
    lines = [
        f"Hive Arrival Pack  Run {pack.get('run_id')}",
        f"Objective: {pack.get('objective')}",
        f"Status: {pack.get('status')}  Phase: {pack.get('phase')}  Verdict: {pack.get('verdict')}",
        f"Role: {pack.get('role')}  Paths hidden: {pack.get('privacy', {}).get('paths_hidden')}",
        "",
        "Blocked Items",
    ]
    blocked = pack.get("blocked_items") or []
    if blocked:
        for item in blocked:
            lines.append(f"  - {item.get('kind')} severity={item.get('severity')} reason={item.get('reason') or item.get('status')}")
    else:
        lines.append("  none")
    lines.extend(["", "Accepted Claims"])
    for item in pack.get("accepted_claims") or []:
        value = item.get("value")
        suffix = f" value={value}" if value is not None else ""
        lines.append(f"  - {item.get('claim')} status={item.get('status')}{suffix}")
    lines.extend(["", "Contested Claims"])
    contested = pack.get("contested_claims") or []
    if contested:
        for item in contested:
            lines.append(f"  - step={item.get('step_id')} severity={item.get('severity')} axes={item.get('axes')}")
    else:
        lines.append("  none")
    lines.extend(["", "Latest Artifacts"])
    for item in pack.get("latest_artifacts") or []:
        path = f" path={item.get('path')}" if show_paths and item.get("path") else ""
        lines.append(f"  - {item.get('kind')} status={item.get('status')}{path}")
    lines.extend(["", "Suggested Commands"])
    for item in pack.get("suggested_commands") or []:
        lines.append(f"  - {item.get('command')}  reason={item.get('reason')}")
    return "\n".join(lines)
