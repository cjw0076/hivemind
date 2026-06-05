from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final


@dataclass(frozen=True, slots=True)
class StepResultDecision:
    status: str
    ok: bool
    ledger_event: str
    reason: str
    rewrite_artifact_status: str | None = None


SUCCESS_STATUSES: Final[frozenset[str]] = frozenset({"completed", "prepared"})
FAILURE_STATUSES: Final[frozenset[str]] = frozenset({"failed", "timeout", "error", "cancelled", "aborted"})


def read_artifact_status(artifact_path: Path) -> str | None:
    if not artifact_path.exists():
        return None
    try:
        text = artifact_path.read_text(encoding="utf-8")
    except OSError:
        return None
    if artifact_path.suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(data, dict):
            raw_status = data.get("status")
            return str(raw_status).strip().lower() if raw_status else None
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("status:"):
            raw_status = stripped.split(":", 1)[1].strip().strip('"').strip("'")
            return raw_status.lower() or None
    return None


def execution_score_from_status(artifact_status: str | None) -> float:
    status = normalized_status(artifact_status)
    if status in {"completed", "prepared"}:
        return 1.0
    if status == "partial":
        return 0.5
    if status in FAILURE_STATUSES or status in {"skipped", ""}:
        return 0.0
    return 0.0


def decide_step_result(artifact_status: str | None, *, execute: bool, on_failure: str) -> StepResultDecision:
    status = normalized_status(artifact_status)
    if status == "completed":
        return StepResultDecision("completed", True, "step_completed", "artifact reported status=completed")
    if status == "prepared" and not execute:
        return StepResultDecision("prepared", True, "step_completed", "artifact reported status=prepared")
    if status == "skipped":
        return StepResultDecision("skipped", False, "step_skipped", "artifact reported status=skipped")

    failure_status = failed_step_status(on_failure)
    ledger_event = "step_failed" if failure_status == "failed" else "step_skipped"
    reason = failure_reason(status, execute)
    rewrite_status = "skipped" if failure_status == "skipped" else None
    return StepResultDecision(failure_status, False, ledger_event, reason, rewrite_status)


def normalized_status(artifact_status: str | None) -> str:
    return (artifact_status or "").strip().lower()


def failed_step_status(on_failure: str) -> str:
    if on_failure == "skip":
        return "skipped"
    return "failed"


def failure_reason(status: str, execute: bool) -> str:
    if not status:
        return "artifact missing terminal status"
    if status == "prepared" and execute:
        return "execute path returned prepared artifact"
    if status in FAILURE_STATUSES:
        return f"artifact reported status={status}"
    return f"artifact reported non-success status={status}"
