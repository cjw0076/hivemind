"""Operator inspection surface for Hive run receipts and authority state."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .harness import load_run, run_audit_report, safe_load_yaml
from .live import build_live_report
from .run_receipts import collect_local_worker_results, collect_provider_results
from .workloop import replay_execution_ledger


def build_inspect_report(
    root: Path,
    run_id: str | None = None,
    *,
    show_paths: bool = False,
) -> dict[str, Any]:
    """Build a path-hidden, production-oriented summary for one run."""
    paths, state = load_run(root, run_id)
    live = build_live_report(root, paths.run_id, tail=12, show_paths=show_paths)
    ledger = replay_execution_ledger(root, paths.run_id)
    audit = run_audit_report(root, paths.run_id)
    provider_results = collect_provider_results(root, paths.run_dir, show_paths=show_paths)
    local_worker_results = collect_local_worker_results(root, paths.run_dir, show_paths=show_paths)
    proofs = summarize_proofs(paths.run_dir, show_paths=show_paths)
    memoryos = summarize_memoryos_context(paths.run_dir, show_paths=show_paths)
    recommendations = inspect_recommendations(live, ledger, audit, provider_results, local_worker_results, proofs, memoryos)
    return {
        "schema_version": 1,
        "kind": "hive_run_inspection",
        "run_id": paths.run_id,
        "task": state.get("user_request"),
        "phase": state.get("phase"),
        "status": state.get("status"),
        "health": live.get("health"),
        "next": live.get("next") or {},
        "paths_hidden": not show_paths,
        "ledger": {
            "ok": ledger.get("ok"),
            "record_count": ledger.get("record_count"),
            "hash_chain_ok": ledger.get("hash_chain_ok"),
            "seq_ok": ledger.get("seq_ok"),
            "issue_count": len(ledger.get("issues") or []),
            "issues": ledger.get("issues") or [],
        },
        "authority": summarize_authority(ledger.get("authority") or {}),
        "provider_results": provider_results,
        "local_worker_results": local_worker_results,
        "proofs": proofs,
        "memoryos_context": memoryos,
        "audit": {
            "status": audit.get("status"),
            "validation_verdict": (audit.get("validation") or {}).get("verdict"),
            "stale_artifact_count": len(audit.get("stale_artifacts") or []),
            "provider_failure_count": len(audit.get("provider_failures") or []),
            "policy_status": (audit.get("policy") or {}).get("status"),
        },
        "recommendations": recommendations,
    }


def summarize_authority(authority: dict[str, Any]) -> dict[str, Any]:
    intents = authority_items(authority.get("intents"))
    decisions = authority_items(authority.get("decisions"))
    proofs = authority_items(authority.get("proofs"))
    votes = authority_items(authority.get("votes"))
    latest_decision = decisions[-1] if decisions else {}
    latest_proof = proofs[-1] if proofs else {}
    return {
        "intent_count": len(intents),
        "vote_count": len(votes),
        "decision_count": len(decisions),
        "proof_count": len(proofs),
        "latest_decision": latest_decision.get("decision"),
        "latest_proof_status": latest_proof.get("status"),
        "missing_voters": latest_decision.get("missing_voters") or [],
    }


def authority_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def summarize_proofs(run_dir: Path, *, show_paths: bool) -> dict[str, Any]:
    proof_dir = run_dir / "execution_proofs"
    items: list[dict[str, Any]] = []
    if proof_dir.exists():
        for proof_path in sorted(proof_dir.glob("*.json")):
            data = safe_load_yaml(proof_path)
            if not isinstance(data, dict):
                data = {}
            item = {
                "intent_id": data.get("intent_id"),
                "step_id": data.get("step_id"),
                "status": data.get("status"),
                "verifier_status": data.get("verifier_status"),
                "artifact_count": len(data.get("artifacts") or []),
            }
            if show_paths:
                item["path"] = proof_path.as_posix()
            items.append(item)
    return {
        "count": len(items),
        "failed_count": sum(1 for item in items if item.get("verifier_status") in {"failed", "flagged", "conflict"}),
        "items": items,
    }


def summarize_memoryos_context(run_dir: Path, *, show_paths: bool) -> dict[str, Any]:
    context_path = run_dir / "artifacts" / "memory_context.json"
    if not context_path.exists():
        return {"status": "missing", "selected_memory_count": 0, "trace_id": None}
    data = safe_load_yaml(context_path)
    if not isinstance(data, dict):
        return {"status": "invalid", "selected_memory_count": 0, "trace_id": None}
    selected = data.get("selected_memory_ids") or data.get("memory_ids") or []
    report = {
        "status": data.get("status") or "available",
        "trace_id": data.get("trace_id"),
        "selected_memory_count": len(selected) if isinstance(selected, list) else 0,
    }
    if show_paths:
        report["path"] = context_path.as_posix()
    return report


def inspect_recommendations(
    live: dict[str, Any],
    ledger: dict[str, Any],
    audit: dict[str, Any],
    provider_results: list[dict[str, Any]],
    local_worker_results: list[dict[str, Any]],
    proofs: dict[str, Any],
    memoryos: dict[str, Any],
) -> list[str]:
    recommendations: list[str] = []
    if not ledger.get("ok"):
        recommendations.append("ledger replay needs review")
    if any(item.get("status") in {"failed", "timeout", "partial"} for item in provider_results):
        recommendations.append("inspect failed/timeout/partial provider result receipts")
    if any(item.get("status") in {"failed", "timeout", "partial", "skipped"} or item.get("should_escalate") for item in local_worker_results):
        recommendations.append("inspect failed/skipped/escalating local worker receipts")
    if proofs.get("failed_count"):
        recommendations.append("review failed or flagged execution proofs")
    if (audit.get("validation") or {}).get("verdict") not in {None, "pass"}:
        recommendations.append("run hive check run before publishing")
    if memoryos.get("status") in {"missing", "invalid"}:
        recommendations.append("MemoryOS context was not attached; continue only if optional for this run")
    next_action = (live.get("next") or {}).get("actions") or []
    if next_action:
        recommendations.append("continue with the next action from the live board")
    if not recommendations:
        recommendations.append("run inspection is clean; proceed with close or memory draft")
    return recommendations


def format_inspect_report(report: dict[str, Any], *, show_paths: bool = False) -> str:
    lines = [
        f"Hive Inspect  Run {report.get('run_id')}",
        f"Task: {report.get('task')}",
        f"Status: {report.get('status')}  Phase: {report.get('phase')}  Health: {report.get('health')}",
        "",
        "Ledger",
        f"  ok={report.get('ledger', {}).get('ok')} records={report.get('ledger', {}).get('record_count')} hash_chain={report.get('ledger', {}).get('hash_chain_ok')} seq={report.get('ledger', {}).get('seq_ok')} issues={report.get('ledger', {}).get('issue_count')}",
        "",
        "Authority",
        f"  intents={report.get('authority', {}).get('intent_count')} votes={report.get('authority', {}).get('vote_count')} decisions={report.get('authority', {}).get('decision_count')} proofs={report.get('authority', {}).get('proof_count')}",
        f"  latest_decision={report.get('authority', {}).get('latest_decision')} latest_proof={report.get('authority', {}).get('latest_proof_status')}",
        "",
        "Provider Results",
    ]
    for item in report.get("provider_results") or []:
        suffix = f" path={item.get('path')}" if show_paths and item.get("path") else ""
        lines.append(
            f"  {item.get('agent')}/{item.get('role')} status={item.get('status')} mode={item.get('provider_mode')} permission={item.get('permission_mode')} risk={item.get('risk_level')}{suffix}"
        )
    if not report.get("provider_results"):
        lines.append("  none")
    lines.extend(["", "Local Worker Results"])
    for item in report.get("local_worker_results") or []:
        suffix = f" path={item.get('path')}" if show_paths and item.get("path") else ""
        lines.append(
            f"  {item.get('role')} worker={item.get('worker')} status={item.get('status')} runtime={item.get('runtime')} valid={item.get('output_valid')} confidence={item.get('confidence')}{suffix}"
        )
    if not report.get("local_worker_results"):
        lines.append("  none")
    memoryos = report.get("memoryos_context") or {}
    lines.extend(
        [
            "",
            "MemoryOS Context",
            f"  status={memoryos.get('status')} trace_id={memoryos.get('trace_id')} selected={memoryos.get('selected_memory_count')}",
            "",
            "Next",
        ]
    )
    next_items = (report.get("next") or {}).get("actions") or []
    if next_items:
        for index, item in enumerate(next_items, start=1):
            lines.append(f"  {index}. {item.get('command')}  reason={item.get('reason')}")
    else:
        lines.append("  none")
    lines.extend(["", "Recommendations"])
    for item in report.get("recommendations") or []:
        lines.append(f"  - {item}")
    return "\n".join(lines)
