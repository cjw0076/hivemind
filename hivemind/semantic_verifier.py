"""Semantic verifier review artifacts for high-risk Hive runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .harness import append_event, load_run, update_state, write_json
from .inspect_run import build_inspect_report
from .run_receipts import collect_local_worker_results, collect_provider_results
from .run_validation import validate_run_artifacts
from .utils import now_iso


SCHEMA_VERSION = "hive.semantic_verification.v1"
ARTIFACT_NAME = "semantic_verification.json"
PROMPT_NAME = "semantic_verifier_prompt.md"
HIGH_RISK_WORDS = {
    "credential",
    "credentials",
    "delete",
    "financial",
    "governance",
    "legal",
    "medical",
    "migration",
    "payment",
    "private",
    "production",
    "public",
    "publish",
    "release",
    "security",
    "sovereign",
}
HIGH_RISK_LEVELS = {"high", "critical", "severe"}
MEDIUM_RISK_LEVELS = {"medium", "review"}


def build_semantic_verification(
    root: Path,
    run_id: str | None = None,
    *,
    show_paths: bool = False,
) -> dict[str, Any]:
    """Write a provider-free semantic verifier artifact for one run."""
    paths, state = load_run(root, run_id)
    assessment = assess_semantic_risk(root, paths.run_id, show_paths=show_paths)
    prompt_path = paths.artifacts / PROMPT_NAME
    prompt_path.write_text(format_semantic_prompt(assessment), encoding="utf-8")
    prompt_ref = prompt_path.relative_to(root).as_posix()
    artifact_path = paths.artifacts / ARTIFACT_NAME
    artifact_ref = artifact_path.relative_to(root).as_posix()
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "hive_semantic_verification",
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "task": state.get("user_request"),
        "status": semantic_status(assessment),
        "risk_level": assessment["risk_level"],
        "risk_signals": assessment["risk_signals"],
        "review_mode": "prepared_llm_review",
        "provider_executed": False,
        "prompt_artifact": prompt_ref,
        "artifact": artifact_ref,
        "criteria": semantic_criteria(assessment),
        "recommendations": semantic_recommendations(assessment),
        "paths_hidden": not show_paths,
        "privacy": {
            "paths_hidden": not show_paths,
            "raw_provider_outputs_included": False,
            "private_memory_contents_included": False,
        },
    }
    write_json(artifact_path, report)
    artifacts = dict(state.get("artifacts") or {})
    artifacts["semantic_verification"] = artifact_ref
    artifacts["semantic_verifier_prompt"] = prompt_ref
    update_state(paths, artifacts=artifacts, latest_event="semantic_verification_created")
    append_event(
        paths,
        "semantic_verification_created",
        {
            "artifact": artifact_ref if show_paths else "artifacts/semantic_verification.json",
            "risk_level": report["risk_level"],
            "status": report["status"],
        },
    )
    return report


def assess_semantic_risk(root: Path, run_id: str | None = None, *, show_paths: bool = False) -> dict[str, Any]:
    """Return risk signals for semantic verification without writing artifacts."""
    paths, state = load_run(root, run_id)
    inspect = build_inspect_report(root, paths.run_id, show_paths=show_paths)
    validation = validate_run_artifacts(paths.run_dir, root)
    provider_results = collect_provider_results(root, paths.run_dir, show_paths=False)
    local_results = collect_local_worker_results(root, paths.run_dir, show_paths=False)
    signals = risk_signals(state, inspect, validation, provider_results, local_results)
    risk_level = combine_risk(signals)
    existing = load_semantic_verification(root, paths.run_id, show_paths=show_paths)
    return {
        "schema_version": "hive.semantic_risk_assessment.v1",
        "run_id": paths.run_id,
        "task": state.get("user_request"),
        "risk_level": risk_level,
        "risk_signals": signals,
        "semantic_verification": existing,
        "inspect_verdict": inspect.get("verdict"),
        "validation_verdict": validation.get("verdict"),
        "paths_hidden": not show_paths,
    }


def load_semantic_verification(root: Path, run_id: str | None = None, *, show_paths: bool = False) -> dict[str, Any]:
    paths, _ = load_run(root, run_id)
    artifact = paths.artifacts / ARTIFACT_NAME
    if not artifact.exists():
        return {"status": "missing", "artifact": None}
    try:
        data = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"status": "invalid", "artifact": None}
    summary = {
        "status": data.get("status") or "unknown",
        "risk_level": data.get("risk_level") or "unknown",
        "review_mode": data.get("review_mode"),
        "provider_executed": bool(data.get("provider_executed")),
        "risk_signal_count": len(data.get("risk_signals") or []),
        "artifact": data.get("artifact"),
    }
    if show_paths:
        summary["path"] = artifact.as_posix()
    return summary


def risk_signals(
    state: dict[str, Any],
    inspect: dict[str, Any],
    validation: dict[str, Any],
    provider_results: list[dict[str, Any]],
    local_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    task = str(state.get("user_request") or "")
    lowered = task.lower()
    matched_words = sorted(word for word in HIGH_RISK_WORDS if word in lowered)
    if matched_words:
        signals.append({"source": "task", "severity": "high", "reason": "high_risk_task_terms", "terms": matched_words})
    if validation.get("verdict") != "pass":
        signals.append({"source": "validation", "severity": "medium", "reason": "validation_needs_review"})
    if inspect.get("verdict") in {"failures", "chain_tampered"}:
        signals.append({"source": "inspect", "severity": "high", "reason": f"inspect_{inspect.get('verdict')}"})
    elif inspect.get("verdict") == "escalated":
        signals.append({"source": "inspect", "severity": "medium", "reason": "inspect_escalated"})
    disagreements = inspect.get("disagreements") or {}
    if (disagreements.get("high_severity_count") or 0) > 0:
        signals.append({"source": "disagreements", "severity": "high", "reason": "high_severity_disagreement"})
    for result in provider_results:
        maybe_add_receipt_signal(signals, "provider", result)
    for result in local_results:
        maybe_add_receipt_signal(signals, "local_worker", result)
    return signals


def maybe_add_receipt_signal(signals: list[dict[str, Any]], source: str, result: dict[str, Any]) -> None:
    risk = str(result.get("risk_level") or "").lower()
    status = str(result.get("status") or "").lower()
    if risk in HIGH_RISK_LEVELS:
        signals.append({"source": source, "severity": "high", "reason": "receipt_high_risk", "role": result.get("role")})
    elif risk in MEDIUM_RISK_LEVELS:
        signals.append({"source": source, "severity": "medium", "reason": "receipt_medium_risk", "role": result.get("role")})
    if status in {"failed", "timeout", "partial"}:
        signals.append({"source": source, "severity": "medium", "reason": f"receipt_{status}", "role": result.get("role")})
    if result.get("should_escalate"):
        signals.append({"source": source, "severity": "medium", "reason": "worker_escalation", "role": result.get("role")})


def combine_risk(signals: list[dict[str, Any]]) -> str:
    severities = {str(signal.get("severity")) for signal in signals}
    if "high" in severities:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


def semantic_status(assessment: dict[str, Any]) -> str:
    risk = assessment.get("risk_level")
    if risk == "high":
        return "review_required"
    if risk == "medium":
        return "needs_review"
    return "not_required"


def semantic_criteria(assessment: dict[str, Any]) -> list[dict[str, str]]:
    risk = assessment.get("risk_level")
    required = risk in {"high", "medium"}
    status = "needs_llm_review" if required else "not_required"
    return [
        {"name": "claim_support", "status": status, "question": "Are user-facing claims supported by run evidence?"},
        {"name": "risk_and_reversibility", "status": status, "question": "Are risky or irreversible actions blocked or reviewed?"},
        {"name": "privacy_boundary", "status": status, "question": "Does the run avoid raw provider/private memory disclosure?"},
        {"name": "acceptance_fit", "status": status, "question": "Does the run satisfy the operator goal and acceptance criteria?"},
    ]


def semantic_recommendations(assessment: dict[str, Any]) -> list[str]:
    risk = assessment.get("risk_level")
    if risk == "high":
        return [
            "run an explicitly approved semantic verifier LLM/provider review before publish or release",
            "treat this run as blocked for public/production claims until reviewer evidence is attached",
        ]
    if risk == "medium":
        return ["review semantic verifier prompt before closeout if the result will be published"]
    return ["semantic verifier LLM review is not required for this low-risk run"]


def format_semantic_prompt(assessment: dict[str, Any]) -> str:
    lines = [
        "# Hive Semantic Verifier Prompt",
        "",
        "Review this Hive run for semantic correctness, overclaim risk, privacy, acceptance fit, and missing evidence.",
        "Do not assume provider stdout/stderr or private memory bodies are available.",
        "",
        f"- run_id: `{assessment.get('run_id')}`",
        f"- task: {assessment.get('task')}",
        f"- risk_level: `{assessment.get('risk_level')}`",
        f"- inspect_verdict: `{assessment.get('inspect_verdict')}`",
        f"- validation_verdict: `{assessment.get('validation_verdict')}`",
        "",
        "## Risk Signals",
    ]
    signals = assessment.get("risk_signals") or []
    if signals:
        for signal in signals:
            reason = signal.get("reason")
            severity = signal.get("severity")
            source = signal.get("source")
            lines.append(f"- `{severity}` from `{source}`: {reason}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "Return JSON with: status, blockers, unsupported_claims, privacy_risks, missing_tests, recommendations, confidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def format_semantic_verification(report: dict[str, Any]) -> str:
    lines = [
        "Hive Semantic Verification",
        f"Run: {report.get('run_id')}",
        f"Status: {str(report.get('status', 'unknown')).upper()}",
        f"Risk: {str(report.get('risk_level', 'unknown')).upper()}",
        f"Artifact: {report.get('artifact')}",
        f"Prompt: {report.get('prompt_artifact')}",
        "",
        "Signals:",
    ]
    signals = report.get("risk_signals") or []
    if signals:
        for signal in signals:
            lines.append(f"- {signal.get('severity')} {signal.get('source')}: {signal.get('reason')}")
    else:
        lines.append("- none")
    recommendations = report.get("recommendations") or []
    if recommendations:
        lines.extend(["", "Recommendations:"])
        lines.extend(f"- {item}" for item in recommendations)
    return "\n".join(lines)
