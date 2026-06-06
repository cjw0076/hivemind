from __future__ import annotations

from typing import Any

from .utils import now_iso


REQUIRED_ROUTER_KEYS = {"intent", "summary", "actions", "confidence", "should_escalate"}


def score_route_quality(
    *,
    prompt: str,
    parsed: dict[str, Any],
    validation: dict[str, Any],
    route_source: str,
    actions: list[dict[str, Any]],
    router_status: str,
) -> dict[str, Any]:
    confidence_value = _clamped_confidence(validation.get("confidence"))
    missing_keys = sorted(key for key in REQUIRED_ROUTER_KEYS if key not in parsed)
    action_pairs = {(str(item.get("provider")), str(item.get("role"))) for item in actions}
    risks: list[str] = []
    score = confidence_value

    schema_valid = bool(validation.get("valid")) and not missing_keys
    if not schema_valid:
        score -= 0.25
        risks.append("router_schema_invalid")
    if route_source != "local_llm":
        risks.append(f"route_source={route_source}")
    if router_status == "fallback" or "fallback" in route_source:
        score -= 0.2
        risks.append("fallback_used")
    if validation.get("should_escalate"):
        risks.append("router_escalation_requested")
    if not actions:
        score -= 0.4
        risks.append("no_actions")

    fallback_candidates = provider_fallback_candidates(str(parsed.get("intent") or "unknown"), action_pairs)
    for candidate in fallback_candidates:
        risk = candidate["reason_code"]
        if risk not in risks:
            risks.append(risk)
    if fallback_candidates:
        score -= 0.2

    score = round(max(0.0, min(1.0, score)), 3)
    if score >= 0.75 and not risks:
        verdict = "pass"
        risk_level = "low"
    elif score >= 0.45:
        verdict = "review"
        risk_level = "medium"
    else:
        verdict = "escalate"
        risk_level = "high"

    return {
        "schema_version": 1,
        "schema_contract": "hive.routing_quality.v1",
        "kind": "routing_quality",
        "generated_at": now_iso(),
        "route_source": route_source,
        "router_status": router_status,
        "intent": parsed.get("intent", "unknown"),
        "score": score,
        "verdict": verdict,
        "risk_level": risk_level,
        "schema_valid": schema_valid,
        "missing_keys": missing_keys,
        "validation_issues": list(validation.get("issues") or []),
        "confidence": confidence_value,
        "should_escalate": bool(validation.get("should_escalate")),
        "escalation_reason": validation.get("escalation_reason") or "",
        "fallback_used": router_status == "fallback" or "fallback" in route_source,
        "provider_fallback": {
            "recommended": bool(fallback_candidates),
            "authority": "prepare_only",
            "candidates": fallback_candidates,
            "stop_conditions": ["provider_truth_without_verifier"] if fallback_candidates else [],
        },
        "action_count": len(actions),
        "action_coverage": [{"provider": item.get("provider"), "role": item.get("role")} for item in actions],
        "risks": risks,
        "prompt_features": {
            "length": len(prompt),
            "has_hangul": _contains_hangul(prompt),
            "has_code_terms": any(token in prompt.lower() for token in ["code", "cli", "api", "test", "bug", "fix", "구현", "수정", "테스트"]),
        },
    }


def provider_fallback_candidates(intent: str, action_pairs: set[tuple[str, str]]) -> list[dict[str, str]]:
    match intent:
        case "implementation":
            if ("codex", "executor") in action_pairs:
                return []
            return [
                {
                    "provider": "codex",
                    "role": "executor",
                    "reason_code": "implementation_without_codex_executor",
                    "reason": "Implementation routes require a Codex executor handoff before execution.",
                }
            ]
        case "debugging" | "review":
            if any(provider in {"claude", "gemini"} for provider, _role in action_pairs):
                return []
            return [
                {
                    "provider": "gemini",
                    "role": "reviewer",
                    "reason_code": "review_intent_without_frontier_reviewer",
                    "reason": "Debugging and review routes need an independent frontier reviewer.",
                }
            ]
        case "memory_import":
            missing: list[dict[str, str]] = []
            if ("local", "memory") not in action_pairs:
                missing.append(
                    {
                        "provider": "local",
                        "role": "memory",
                        "reason_code": "memory_import_without_local_memory_worker",
                        "reason": "Memory import routes need a local memory draft worker.",
                    }
                )
            if ("codex", "executor") not in action_pairs:
                missing.append(
                    {
                        "provider": "codex",
                        "role": "executor",
                        "reason_code": "memory_import_without_codex_executor",
                        "reason": "Memory import implementation needs a Codex executor handoff.",
                    }
                )
            return missing
        case _:
            return []


def _clamped_confidence(value: Any) -> float:
    try:
        confidence = float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        confidence = 0.0
    return max(0.0, min(1.0, confidence))


def _contains_hangul(text: str) -> bool:
    return any("\uac00" <= char <= "\ud7a3" for char in text)
