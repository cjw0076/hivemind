from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


PROVIDERS = {"claude", "codex", "gemini", "local"}
FAILURE_CATEGORIES = {
    "rate_limit",
    "quota_exhausted",
    "auth_denied",
    "pin_required_noninteractive",
    "policy_blocked",
    "timeout",
    "context_exhausted",
    "provider_unavailable",
    "unknown_provider_failure",
}


def classify_provider_failure(result: dict[str, Any], root: Path) -> str | None:
    status = str(result.get("status") or "").lower()
    if status in {"prepared", "completed"}:
        return None
    provider_mode = str(result.get("provider_mode") or "").lower()
    reason = str(result.get("reason") or "")
    policy_violations = " ".join(str(item) for item in (result.get("policy_violations") or []))
    stderr_text = ""
    stderr_path = result.get("stderr_path")
    if isinstance(stderr_path, str) and stderr_path:
        path = root / stderr_path
        try:
            stderr_text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            stderr_text = ""
    text = " ".join([status, provider_mode, reason, policy_violations, stderr_text]).lower()
    if "틀렸습니다" in text or "접근 거부" in text:
        return "pin_required_noninteractive"
    if "policy_blocked" in text or "policy blocked" in text or "allowlist" in text:
        return "policy_blocked"
    if status == "timeout" or "timed out" in text or "timeout" in text:
        return "timeout"
    if "rate limit" in text or "rate_limit" in text or "429" in text or "too many requests" in text:
        return "rate_limit"
    if "quota" in text or "insufficient credits" in text or "billing" in text:
        return "quota_exhausted"
    if "auth" in text or "unauthorized" in text or "forbidden" in text or "access denied" in text or "로그인" in text:
        return "auth_denied"
    if "context length" in text or "context exhausted" in text or "maximum context" in text:
        return "context_exhausted"
    if "not found" in text or "no such file" in text or "connection refused" in text or "unavailable" in text:
        return "provider_unavailable"
    return "unknown_provider_failure"


def cooldown_until(category: str) -> str:
    minutes = {
        "rate_limit": 30,
        "quota_exhausted": 240,
        "auth_denied": 120,
        "pin_required_noninteractive": 120,
        "policy_blocked": 0,
        "timeout": 10,
        "context_exhausted": 0,
        "provider_unavailable": 15,
        "unknown_provider_failure": 15,
    }.get(category, 15)
    return (datetime.now(timezone.utc).astimezone() + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def fallback_candidates(provider: str, category: str) -> list[str]:
    match category:
        case "policy_blocked":
            order = {
                "claude": ["codex", "gemini", "local"],
                "codex": ["claude", "gemini", "local"],
                "gemini": ["claude", "codex", "local"],
                "local": ["codex", "claude", "gemini"],
            }
        case _:
            order = {
                "claude": ["codex", "gemini", "local"],
                "codex": ["claude", "gemini", "local"],
                "gemini": ["claude", "codex", "local"],
                "local": ["codex", "claude", "gemini"],
            }
    return [item for item in order.get(provider, ["local"]) if item in PROVIDERS and item != provider]
