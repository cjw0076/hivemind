"""Operator inspection surface for Hive run receipts and authority state."""

from __future__ import annotations

import json
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
    disagreements = summarize_disagreements(paths.run_dir, show_paths=show_paths)
    recommendations = inspect_recommendations(live, ledger, audit, provider_results, local_worker_results, proofs, memoryos, disagreements)
    verdict = compute_verdict(ledger, proofs, provider_results, local_worker_results, disagreements)
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
            "artifact_hash_drift_count": sum(1 for issue in ledger.get("issues") or [] if issue.get("type") == "artifact_hash_drift"),
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
        "disagreements": disagreements,
        "verdict": verdict,
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
                "artifact_hash_count": len(data.get("artifact_hashes") or {}),
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


def summarize_disagreements(run_dir: Path, *, show_paths: bool) -> dict[str, Any]:
    dis_path = run_dir / "disagreements.json"
    if not dis_path.exists():
        return {"count": 0, "high_severity_count": 0, "records": []}
    try:
        records = json.loads(dis_path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            records = []
    except Exception:
        records = []
    high = sum(1 for r in records if r.get("severity") in {"high", "medium"})
    summary_records = [
        {
            "step_id": r.get("step_id"),
            "topology_type": r.get("topology_type"),
            "severity": r.get("severity"),
            "axes": r.get("axes"),
            "dominant_axis": r.get("dominant_axis"),
            "recommended_action": r.get("topology_recommended_action"),
            "ts": r.get("ts"),
        }
        for r in records
    ]
    result: dict[str, Any] = {
        "count": len(records),
        "high_severity_count": high,
        "records": summary_records,
    }
    if show_paths:
        result["path"] = dis_path.as_posix()
    return result


# Verdict priority: chain_tampered > failures > escalated > clean
_VERDICT_ORDER = {"clean": 0, "escalated": 1, "failures": 2, "chain_tampered": 3}


def compute_verdict(
    ledger: dict[str, Any],
    proofs: dict[str, Any],
    provider_results: list[dict[str, Any]],
    local_worker_results: list[dict[str, Any]],
    disagreements: dict[str, Any],
) -> str:
    # Only flag tampered if there are actual records with a broken chain
    if ledger.get("hash_chain_ok") is False and (ledger.get("record_count") or 0) > 0:
        return "chain_tampered"
    has_failures = (
        any(r.get("status") in {"failed", "timeout"} for r in provider_results)
        or any(r.get("status") in {"failed", "timeout"} for r in local_worker_results)
        or (proofs.get("failed_count") or 0) > 0
    )
    if has_failures:
        return "failures"
    if (disagreements.get("high_severity_count") or 0) > 0:
        return "escalated"
    return "clean"


def inspect_recommendations(
    live: dict[str, Any],
    ledger: dict[str, Any],
    audit: dict[str, Any],
    provider_results: list[dict[str, Any]],
    local_worker_results: list[dict[str, Any]],
    proofs: dict[str, Any],
    memoryos: dict[str, Any],
    disagreements: dict[str, Any] | None = None,
) -> list[str]:
    recommendations: list[str] = []
    if ledger.get("hash_chain_ok") is False and (ledger.get("record_count") or 0) > 0:
        recommendations.append("CRITICAL: ledger hash chain tampered — do not trust run artifacts")
    elif not ledger.get("ok"):
        recommendations.append("ledger replay needs review")
    if any(item.get("status") in {"failed", "timeout", "partial"} for item in provider_results):
        recommendations.append("inspect failed/timeout/partial provider result receipts")
    if any(item.get("status") in {"failed", "timeout", "partial", "skipped"} or item.get("should_escalate") for item in local_worker_results):
        recommendations.append("inspect failed/skipped/escalating local worker receipts")
    if proofs.get("failed_count"):
        recommendations.append("review failed or flagged execution proofs")
    if disagreements and (disagreements.get("high_severity_count") or 0) > 0:
        high = disagreements["high_severity_count"]
        axes = {axis for r in (disagreements.get("records") or []) for axis in (r.get("axes") or [])}
        recommendations.append(
            f"topology escalation: {high} high/medium disagreement(s) detected — axes: {', '.join(sorted(axes)) or 'unknown'}"
        )
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


def _format_health(health: Any) -> str:
    if isinstance(health, dict):
        label = health.get("label", "unknown")
        missing = health.get("missing_required") or []
        blocked = health.get("blocked_count", 0)
        parts = [label]
        if missing:
            parts.append(f"missing={','.join(missing[:3])}" + ("..." if len(missing) > 3 else ""))
        if blocked:
            parts.append(f"blocked={blocked}")
        return " ".join(parts)
    return str(health) if health is not None else "unknown"


def format_inspect_report(report: dict[str, Any], *, show_paths: bool = False) -> str:
    verdict = report.get("verdict", "unknown")
    verdict_marker = {"clean": "✓", "escalated": "⚠", "failures": "✗", "chain_tampered": "✗✗"}.get(verdict, "?")
    lines = [
        f"Hive Inspect  Run {report.get('run_id')}",
        f"Verdict: {verdict_marker} {verdict.upper()}",
        f"Task: {report.get('task')}",
        f"Status: {report.get('status')}  Phase: {report.get('phase')}  Health: {_format_health(report.get('health'))}",
        "",
        "Ledger",
        f"  ok={report.get('ledger', {}).get('ok')} records={report.get('ledger', {}).get('record_count')} hash_chain={report.get('ledger', {}).get('hash_chain_ok')} seq={report.get('ledger', {}).get('seq_ok')} issues={report.get('ledger', {}).get('issue_count')}",
        f"  artifact_hash_drift={report.get('ledger', {}).get('artifact_hash_drift_count')}",
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
    dis = report.get("disagreements") or {}
    lines.extend(["", "Disagreements"])
    lines.append(f"  count={dis.get('count', 0)} high/medium={dis.get('high_severity_count', 0)}")
    for rec in (dis.get("records") or []):
        lines.append(f"  step={rec.get('step_id')} type={rec.get('topology_type')} severity={rec.get('severity')} axes={rec.get('axes')} action={rec.get('recommended_action')}")
    if not (dis.get("records")):
        lines.append("  none")
    lines.extend(["", "Recommendations"])
    for item in report.get("recommendations") or []:
        lines.append(f"  - {item}")
    return "\n".join(lines)
