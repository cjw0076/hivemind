"""Durable subagent review artifacts for Hive runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .harness import append_event, load_run, update_state, write_json
from .inspect_run import build_inspect_report
from .run_validation import validate_run_artifacts
from .semantic_verifier import assess_semantic_risk
from .utils import now_iso


SCHEMA_VERSION = "hive.evaluation_report.v1"
ARTIFACT_NAME = "evaluation_report.json"


def build_evaluation_report(
    root: Path,
    run_id: str | None = None,
    *,
    show_paths: bool = False,
) -> dict[str, Any]:
    """Build and persist a path-hidden evaluation report for a Hive run."""
    paths, state = load_run(root, run_id)
    inspect = build_inspect_report(root, paths.run_id, show_paths=show_paths)
    validation = validate_run_artifacts(paths.run_dir, root)
    semantic = assess_semantic_risk(root, paths.run_id, show_paths=show_paths)
    reviews = [
        verifier_review(validation, inspect, semantic),
        product_evaluator_review(state, inspect, validation),
        actual_user_review(inspect, validation),
    ]
    overall_status = combine_statuses([review["status"] for review in reviews])
    artifact_path = paths.artifacts / ARTIFACT_NAME
    artifact_ref = artifact_path.relative_to(root).as_posix()
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "hive_evaluation_report",
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "task": state.get("user_request"),
        "overall_status": overall_status,
        "paths_hidden": not show_paths,
        "artifact": artifact_ref,
        "inputs": {
            "inspect_kind": inspect.get("kind"),
            "inspect_verdict": inspect.get("verdict"),
            "validation_verdict": validation.get("verdict"),
            "semantic_risk_level": semantic.get("risk_level"),
            "semantic_status": (semantic.get("semantic_verification") or {}).get("status"),
        },
        "semantic_verification": semantic.get("semantic_verification"),
        "reviews": reviews,
        "next_actions": next_actions(reviews, inspect),
        "privacy": {
            "paths_hidden": not show_paths,
            "raw_provider_outputs_included": False,
            "private_memory_contents_included": False,
        },
    }
    write_json(artifact_path, report)
    artifacts = dict(state.get("artifacts") or {})
    artifacts["evaluation_report"] = artifact_ref
    update_state(paths, artifacts=artifacts, latest_event="evaluation_report_created")
    append_event(
        paths,
        "evaluation_report_created",
        {
            "artifact": artifact_ref if show_paths else "artifacts/evaluation_report.json",
            "overall_status": overall_status,
            "review_count": len(reviews),
        },
    )
    return report


def verifier_review(validation: dict[str, Any], inspect: dict[str, Any], semantic: dict[str, Any] | None = None) -> dict[str, Any]:
    findings: list[str] = []
    blockers: list[str] = []
    recommendations: list[str] = []
    semantic = semantic or {}
    semantic_existing = semantic.get("semantic_verification") or {}
    if validation.get("verdict") != "pass":
        findings.extend(validation.get("issues") or ["run validation needs review"])
        recommendations.append("run hive verify or inspect validation issues before publish")
    if inspect.get("verdict") in {"failures", "chain_tampered"}:
        blockers.append(f"inspect verdict is {inspect.get('verdict')}")
    if semantic.get("risk_level") == "high" and semantic_existing.get("status") == "missing":
        blockers.append("high-risk run lacks semantic verifier review")
        recommendations.append("run hive semantic-review before publish or release")
    elif semantic_existing.get("status") in {"review_required", "needs_review", "not_required"}:
        findings.append(f"semantic verifier status is {semantic_existing.get('status')}")
    if not blockers and not findings:
        findings.append("run artifacts validate and inspect verdict is clean")
    return {
        "role": "hive.verifier",
        "status": status_for(blockers, findings, clean_marker="run artifacts validate"),
        "focus": "schema validity, receipts, ledger health, and publish safety",
        "findings": findings,
        "blockers": blockers,
        "recommendations": recommendations or ["continue with closeout or memory draft"],
        "evidence": {
            "validation_verdict": validation.get("verdict"),
            "inspect_verdict": inspect.get("verdict"),
            "ledger_ok": (inspect.get("ledger") or {}).get("ok"),
            "semantic_risk_level": semantic.get("risk_level"),
            "semantic_status": semantic_existing.get("status"),
        },
    }


def product_evaluator_review(
    state: dict[str, Any],
    inspect: dict[str, Any],
    validation: dict[str, Any],
) -> dict[str, Any]:
    findings: list[str] = []
    blockers: list[str] = []
    recommendations: list[str] = []
    if state.get("user_request"):
        findings.append("objective is present")
    else:
        blockers.append("objective is missing")
    if inspect.get("recommendations"):
        findings.append("operator recommendations are available")
    else:
        recommendations.append("add a concrete next recommendation for the operator")
    if validation.get("verdict") != "pass":
        recommendations.append("resolve validation issues before claiming product readiness")
    return {
        "role": "hive.product_evaluator",
        "status": status_for(blockers, recommendations),
        "focus": "operator value, next-step clarity, and readiness claims",
        "findings": findings or ["product surface needs more evidence"],
        "blockers": blockers,
        "recommendations": recommendations or ["use the inspect recommendations to close the run"],
        "evidence": {
            "task_present": bool(state.get("user_request")),
            "recommendation_count": len(inspect.get("recommendations") or []),
            "validation_verdict": validation.get("verdict"),
        },
    }


def actual_user_review(inspect: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    blockers: list[str] = []
    recommendations: list[str] = []
    if inspect.get("paths_hidden"):
        findings.append("default output hides filesystem paths")
    else:
        blockers.append("default output exposes filesystem paths")
    if inspect.get("next") or inspect.get("recommendations"):
        findings.append("next action guidance is available")
    else:
        recommendations.append("surface a clearer next command")
    if validation.get("verdict") != "pass":
        recommendations.append("show validation issues before asking the operator to trust the run")
    return {
        "role": "persona.actual_user",
        "status": status_for(blockers, recommendations),
        "focus": "clear Korean/English operator use, trust, and low-friction next steps",
        "findings": findings or ["operator experience needs review"],
        "blockers": blockers,
        "recommendations": recommendations or ["continue; the run is inspectable without debug paths"],
        "evidence": {
            "paths_hidden": inspect.get("paths_hidden"),
            "recommendation_count": len(inspect.get("recommendations") or []),
            "validation_verdict": validation.get("verdict"),
        },
    }


def status_for(blockers: list[str], warnings: list[str], *, clean_marker: str | None = None) -> str:
    if blockers:
        return "failed"
    if clean_marker and any(clean_marker in item for item in warnings):
        return "passed"
    if warnings:
        return "needs_review"
    return "passed"


def combine_statuses(statuses: list[str]) -> str:
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status == "needs_review" for status in statuses):
        return "needs_review"
    return "passed"


def next_actions(reviews: list[dict[str, Any]], inspect: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for review in reviews:
        if review.get("status") != "passed":
            actions.extend(str(item) for item in review.get("recommendations") or [])
    if not actions:
        actions.extend(str(item) for item in inspect.get("recommendations") or [])
    return dedupe(actions)[:6]


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def format_evaluation_report(report: dict[str, Any]) -> str:
    lines = [
        "Hive Evaluation",
        f"Run: {report.get('run_id')}",
        f"Overall: {str(report.get('overall_status', 'unknown')).upper()}",
        f"Artifact: {report.get('artifact')}",
        "",
        "Reviews:",
    ]
    for review in report.get("reviews") or []:
        lines.append(f"- {review.get('role')}: {str(review.get('status', 'unknown')).upper()}")
        for finding in review.get("findings") or []:
            lines.append(f"  - {finding}")
    actions = report.get("next_actions") or []
    if actions:
        lines.extend(["", "Next Actions:"])
        lines.extend(f"- {action}" for action in actions)
    return "\n".join(lines)
