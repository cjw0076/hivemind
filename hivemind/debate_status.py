"""Read model for Hive debate artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TERMINAL_DEBATE_STATUSES = {"prepared", "completed", "failed", "timeout", "skipped"}


def summarize_debate_status(run_dir: Path, *, show_paths: bool = False) -> dict[str, Any]:
    """Summarize debate rounds and participant readiness without raw provider output."""
    report_path = run_dir / "debate_report.json"
    if not report_path.exists():
        return {
            "status": "none",
            "topic": None,
            "barrier": None,
            "round_count": 0,
            "participant_count": 0,
            "completed_output_count": 0,
            "prepared_output_count": 0,
            "failed_count": 0,
            "pending_participants": [],
            "manual_followup_participants": [],
            "readiness": [],
        }
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "status": "invalid",
            "topic": None,
            "barrier": None,
            "round_count": 0,
            "participant_count": 0,
            "completed_output_count": 0,
            "prepared_output_count": 0,
            "failed_count": 0,
            "pending_participants": [],
            "manual_followup_participants": [],
            "readiness": [],
        }
    if not isinstance(report, dict):
        return {
            "status": "invalid",
            "topic": None,
            "barrier": None,
            "round_count": 0,
            "participant_count": 0,
            "completed_output_count": 0,
            "prepared_output_count": 0,
            "failed_count": 0,
            "pending_participants": [],
            "manual_followup_participants": [],
            "readiness": [],
        }
    rounds = [item for item in (report.get("rounds") or []) if isinstance(item, dict)]
    participants = [str(item) for item in (report.get("participants") or []) if item]
    readiness = summarize_participant_readiness(participants, rounds, show_paths=show_paths)
    pending = [item["participant"] for item in readiness if not item.get("barrier_ready")]
    manual = [item["participant"] for item in readiness if item.get("requires_manual_followup")]
    completed = sum(1 for item in readiness for status in (item.get("round_statuses") or {}).values() if status == "completed")
    prepared = sum(1 for item in readiness for status in (item.get("round_statuses") or {}).values() if status == "prepared")
    failed = sum(1 for item in readiness for status in (item.get("round_statuses") or {}).values() if status in {"failed", "timeout"})
    status = "waiting" if pending else ("review_ready" if manual else "complete")
    result: dict[str, Any] = {
        "status": status,
        "topic": report.get("topic"),
        "barrier": report.get("barrier"),
        "round_count": len(rounds),
        "participant_count": len(participants),
        "completed_output_count": completed,
        "prepared_output_count": prepared,
        "failed_count": failed,
        "pending_participants": pending,
        "manual_followup_participants": manual,
        "readiness": readiness,
        "next": report.get("next") or {},
    }
    if show_paths:
        result["path"] = report_path.as_posix()
        result["artifacts"] = report.get("artifacts") or {}
    return result


def summarize_participant_readiness(participants: list[str], rounds: list[dict[str, Any]], *, show_paths: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    expected_rounds = [str(round_report.get("role") or f"round_{index}") for index, round_report in enumerate(rounds, start=1)]
    for participant in participants:
        statuses: dict[str, str] = {}
        provider_modes: set[str] = set()
        has_output = False
        result_paths: dict[str, str] = {}
        for round_report in rounds:
            role = str(round_report.get("role") or "round")
            match = next(
                (
                    item for item in (round_report.get("participants") or [])
                    if isinstance(item, dict) and item.get("participant") == participant
                ),
                None,
            )
            if not match:
                statuses[role] = "missing"
                continue
            status = str(match.get("status") or "unknown")
            statuses[role] = status
            if match.get("provider_mode"):
                provider_modes.add(str(match.get("provider_mode")))
            has_output = has_output or bool(match.get("has_output"))
            if show_paths and match.get("result_path"):
                result_paths[role] = str(match.get("result_path"))
        terminal_rounds = sum(1 for status in statuses.values() if status in TERMINAL_DEBATE_STATUSES)
        barrier_ready = terminal_rounds == len(expected_rounds) and bool(expected_rounds)
        requires_manual_followup = any(status == "prepared" for status in statuses.values()) and not has_output
        row: dict[str, Any] = {
            "participant": participant,
            "round_statuses": statuses,
            "terminal_rounds": terminal_rounds,
            "expected_rounds": len(expected_rounds),
            "barrier_ready": barrier_ready,
            "evidence_ready": has_output,
            "requires_manual_followup": requires_manual_followup,
            "provider_modes": sorted(provider_modes),
        }
        if show_paths:
            row["result_paths"] = result_paths
        rows.append(row)
    return rows
