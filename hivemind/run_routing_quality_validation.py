from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REQUIRED_ROUTING_QUALITY_KEYS = {
    "schema_version",
    "kind",
    "route_source",
    "router_status",
    "intent",
    "score",
    "verdict",
    "risk_level",
    "schema_valid",
    "fallback_used",
    "action_coverage",
    "risks",
}
ALLOWED_ROUTING_QUALITY_VERDICTS = {"pass", "review", "escalate"}
ALLOWED_ROUTING_QUALITY_RISKS = {"low", "medium", "high"}


def validate_routing_quality_artifact(path: Path, issues: list[str]) -> bool:
    if not path.exists():
        return True
    data = load_routing_quality(path, issues)
    if not isinstance(data, dict):
        issues.append("routing_quality must be an object")
        return False

    ok = True
    missing = sorted(REQUIRED_ROUTING_QUALITY_KEYS - set(data))
    if missing:
        issues.append(f"routing_quality missing required keys: {', '.join(missing)}")
        ok = False
    if data.get("kind") != "routing_quality":
        issues.append(f"routing_quality.kind is invalid: {data.get('kind')}")
        ok = False
    score = data.get("score")
    if not isinstance(score, (int, float)) or not 0 <= float(score) <= 1:
        issues.append("routing_quality.score must be between 0 and 1")
        ok = False
    if data.get("verdict") not in ALLOWED_ROUTING_QUALITY_VERDICTS:
        issues.append(f"routing_quality.verdict is invalid: {data.get('verdict')}")
        ok = False
    if data.get("risk_level") not in ALLOWED_ROUTING_QUALITY_RISKS:
        issues.append(f"routing_quality.risk_level is invalid: {data.get('risk_level')}")
        ok = False
    if not isinstance(data.get("schema_valid"), bool):
        issues.append("routing_quality.schema_valid must be a boolean")
        ok = False
    if not isinstance(data.get("fallback_used"), bool):
        issues.append("routing_quality.fallback_used must be a boolean")
        ok = False
    if not isinstance(data.get("action_coverage"), list):
        issues.append("routing_quality.action_coverage must be a list")
        ok = False
    if not isinstance(data.get("risks"), list):
        issues.append("routing_quality.risks must be a list")
        ok = False
    fallback = data.get("provider_fallback")
    if fallback is not None and not validate_provider_fallback(fallback, issues):
        ok = False
    return ok


def load_routing_quality(path: Path, issues: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(f"routing_quality JSON parse failed: {exc}")
        return None


def validate_provider_fallback(data: Any, issues: list[str]) -> bool:
    if not isinstance(data, dict):
        issues.append("routing_quality.provider_fallback must be an object")
        return False
    ok = True
    if not isinstance(data.get("recommended"), bool):
        issues.append("routing_quality.provider_fallback.recommended must be a boolean")
        ok = False
    if data.get("authority") != "prepare_only":
        issues.append(f"routing_quality.provider_fallback.authority is invalid: {data.get('authority')}")
        ok = False
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        issues.append("routing_quality.provider_fallback.candidates must be a list")
        return False
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            issues.append(f"routing_quality.provider_fallback.candidates[{index}] must be an object")
            ok = False
            continue
        for key in ("provider", "role", "reason_code", "reason"):
            if not isinstance(candidate.get(key), str) or not candidate.get(key):
                issues.append(f"routing_quality.provider_fallback.candidates[{index}].{key} must be a non-empty string")
                ok = False
    return ok
