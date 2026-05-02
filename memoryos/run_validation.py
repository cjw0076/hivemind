"""Validation for MemoryOS harness run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ALLOWED_EVENT_TYPES = {
    "run_created",
    "agent_prompt_created",
    "agent_prepared",
    "agent_started",
    "agent_completed",
    "agent_failed",
    "verification_created",
    "summary_created",
    "memory_drafts_created",
}

REQUIRED_RUN_STATE_KEYS = {
    "run_id",
    "user_request",
    "project",
    "task_type",
    "phase",
    "status",
    "created_at",
    "updated_at",
    "agents",
    "context",
    "latest_event",
    "artifacts",
}

REQUIRED_TASK_KEYS = {"run_id", "user_request", "project", "task_type", "goal", "priority", "status"}
REQUIRED_HANDOFF_KEYS = {"from_agent", "to_agent", "objective", "constraints", "acceptance_criteria"}
REQUIRED_MEMORY_DRAFT_KEYS = {"type", "content", "origin", "project", "confidence", "status", "raw_refs"}


def validate_run_artifacts(run_dir: Path, root: Path) -> dict[str, Any]:
    """Return a structured validation report for a `.runs/<run_id>` folder."""
    checks: dict[str, bool] = {}
    issues: list[str] = []

    run_id = run_dir.name
    paths = {
        "task": run_dir / "task.yaml",
        "context_pack": run_dir / "context_pack.md",
        "handoff": run_dir / "handoff.yaml",
        "events": run_dir / "events.jsonl",
        "run_state": run_dir / "run_state.json",
        "verification": run_dir / "verification.yaml",
        "memory_drafts": run_dir / "memory_drafts.json",
        "final_report": run_dir / "final_report.md",
    }

    for name, path in paths.items():
        checks[f"{name}_exists"] = path.exists()
        if not path.exists() and name not in {"verification", "memory_drafts"}:
            issues.append(f"Missing required artifact: {path.relative_to(root).as_posix()}")

    task = load_yaml(paths["task"], "task", issues)
    handoff = load_yaml(paths["handoff"], "handoff", issues)
    state = load_json(paths["run_state"], "run_state", issues)
    memory = load_json(paths["memory_drafts"], "memory_drafts", issues, required=False)
    events = load_events(paths["events"], run_id, issues)

    checks["task_schema_valid"] = validate_required_keys(task, REQUIRED_TASK_KEYS, "task", issues)
    checks["handoff_schema_valid"] = validate_required_keys(handoff, REQUIRED_HANDOFF_KEYS, "handoff", issues)
    checks["run_state_schema_valid"] = validate_required_keys(state, REQUIRED_RUN_STATE_KEYS, "run_state", issues)
    checks["events_schema_valid"] = bool(events) and not any(issue.startswith("Event") for issue in issues)
    checks["memory_drafts_schema_valid"] = validate_memory_drafts(memory, issues) if memory is not None else True
    checks["final_report_schema_valid"] = validate_final_report(paths["final_report"], run_id, issues)
    checks["state_artifact_refs_valid"] = validate_state_artifact_refs(state, root, issues)

    if isinstance(task, dict) and task.get("run_id") != run_id:
        checks["task_run_id_matches"] = False
        issues.append(f"task.run_id does not match folder name: {task.get('run_id')} != {run_id}")
    else:
        checks["task_run_id_matches"] = isinstance(task, dict)

    if isinstance(state, dict) and state.get("run_id") != run_id:
        checks["state_run_id_matches"] = False
        issues.append(f"run_state.run_id does not match folder name: {state.get('run_id')} != {run_id}")
    else:
        checks["state_run_id_matches"] = isinstance(state, dict)

    return {
        "schema_version": 1,
        "run_id": run_id,
        "verdict": "pass" if all(checks.values()) and not issues else "needs_review",
        "checks": checks,
        "issues": issues,
        "event_taxonomy": sorted(ALLOWED_EVENT_TYPES),
        "risk_level": "low" if not issues else "medium",
    }


def load_yaml(path: Path, label: str, issues: list[str], required: bool = True) -> Any:
    if not path.exists():
        if required:
            issues.append(f"{label} YAML missing: {path}")
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        issues.append(f"{label} YAML parse failed: {exc}")
        return None


def load_json(path: Path, label: str, issues: list[str], required: bool = True) -> Any:
    if not path.exists():
        if required:
            issues.append(f"{label} JSON missing: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        issues.append(f"{label} JSON parse failed: {exc}")
        return None


def load_events(path: Path, run_id: str, issues: list[str]) -> list[dict[str, Any]]:
    if not path.exists():
        issues.append(f"events JSONL missing: {path}")
        return []
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(f"Event line {line_no} JSON parse failed: {exc}")
            continue
        event_type = event.get("type")
        if event_type not in ALLOWED_EVENT_TYPES:
            issues.append(f"Event line {line_no} has unknown type: {event_type}")
        if event.get("run_id") != run_id:
            issues.append(f"Event line {line_no} run_id mismatch: {event.get('run_id')} != {run_id}")
        if not event.get("ts"):
            issues.append(f"Event line {line_no} missing ts")
        events.append(event)
    if not events:
        issues.append("events.jsonl has no events")
    return events


def validate_required_keys(data: Any, keys: set[str], label: str, issues: list[str]) -> bool:
    if not isinstance(data, dict):
        issues.append(f"{label} must be an object")
        return False
    missing = sorted(keys - set(data))
    if missing:
        issues.append(f"{label} missing required keys: {', '.join(missing)}")
        return False
    return True


def validate_memory_drafts(data: Any, issues: list[str]) -> bool:
    if not isinstance(data, dict):
        issues.append("memory_drafts must be an object")
        return False
    drafts = data.get("memory_drafts")
    if not isinstance(drafts, list):
        issues.append("memory_drafts.memory_drafts must be a list")
        return False
    ok = True
    for index, draft in enumerate(drafts):
        if not isinstance(draft, dict):
            issues.append(f"memory_drafts[{index}] must be an object")
            ok = False
            continue
        missing = sorted(REQUIRED_MEMORY_DRAFT_KEYS - set(draft))
        if missing:
            issues.append(f"memory_drafts[{index}] missing required keys: {', '.join(missing)}")
            ok = False
        confidence = draft.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= float(confidence) <= 1:
            issues.append(f"memory_drafts[{index}].confidence must be between 0 and 1")
            ok = False
    return ok


def validate_final_report(path: Path, run_id: str, issues: list[str]) -> bool:
    if not path.exists():
        issues.append(f"final_report missing: {path}")
        return False
    text = path.read_text(encoding="utf-8")
    ok = True
    if not text.startswith(f"# Final Report: {run_id}"):
        issues.append("final_report heading does not match run_id")
        ok = False
    if "## Recent Events" not in text:
        issues.append("final_report missing Recent Events section")
        ok = False
    return ok


def validate_state_artifact_refs(state: Any, root: Path, issues: list[str]) -> bool:
    if not isinstance(state, dict):
        return False
    refs = state.get("artifacts")
    if not isinstance(refs, dict):
        issues.append("run_state.artifacts must be an object")
        return False
    ok = True
    for name, rel_path in refs.items():
        if not isinstance(rel_path, str):
            issues.append(f"run_state.artifacts.{name} must be a path string")
            ok = False
            continue
        if not (root / rel_path).exists():
            issues.append(f"run_state.artifacts.{name} points to missing file: {rel_path}")
            ok = False
    return ok
