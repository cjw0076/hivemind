"""Validation for Hive Mind run artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .utils import is_valid_run_id


ALLOWED_EVENT_TYPES = {
    "run_created",
    "agent_prompt_created",
    "agent_prepared",
    "agent_started",
    "agent_completed",
    "agent_failed",
    "provider_passthrough_prepared",
    "provider_passthrough_completed",
    "provider_passthrough_failed",
    "verification_created",
    "summary_created",
    "memory_drafts_created",
    "context_edited",
    "intent_routed",
    "routing_plan_created",
    "society_plan_created",
    "route_action_failed",
    "checks_report_created",
    "git_diff_report_created",
    "git_diff_captured",
    "commit_summary_created",
    "control_lock_acquired",
    "control_lock_released",
    "debate_round_created",
    "debate_convergence_created",
    "memory_context_built",
    "memoryos_context_retrieved",
    "semantic_verification_created",
    "handoff_quality_created",
    "routing_evidence_created",
    "conflict_set_created",
    "operator_decisions_created",
    "auto_loop_step_executed",
    "auto_loop_ready",
    "workflow_advanced",
    "workflow_state_created",
    "demo_started",
    "demo_completed",
}

RUN_ARTIFACT_SPEC = {
    "task": "task.yaml",
    "context_pack": "context_pack.md",
    "handoff": "handoff.yaml",
    "events": "events.jsonl",
    "run_state": "run_state.json",
    "verification": "verification.yaml",
    "memory_drafts": "memory_drafts.json",
    "final_report": "final_report.md",
    "transcript": "transcript.md",
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
ALLOWED_MEMORY_TYPES = {"idea", "decision", "action", "question", "constraint", "preference", "artifact", "reflection"}
ALLOWED_MEMORY_ORIGINS = {"user", "assistant", "mixed", "unknown"}
ALLOWED_MEMORY_STATUSES = {"draft", "reviewed", "accepted", "rejected", "speculative", "stale"}
REQUIRED_PROVIDER_RESULT_KEYS = {
    "schema_version",
    "provider",
    "agent",
    "role",
    "status",
    "provider_mode",
    "permission_mode",
    "prompt_path",
    "command_path",
    "stdout_path",
    "stderr_path",
    "output_path",
    "returncode",
    "started_at",
    "finished_at",
    "duration_ms",
    "files_changed",
    "commands_run",
    "tests_run",
    "artifacts_created",
    "risk_level",
    "policy_violations",
    "memory_refs_used",
    "capability_refs_used",
}
ALLOWED_PROVIDER_STATUSES = {"prepared", "completed", "failed", "fallback"}
ALLOWED_PROVIDER_MODES = {
    "prepare_only",
    "execute_supported",
    "unavailable",
    "local_runtime",
    "http",
    "native_passthrough",
    "policy_blocked",
}


def validate_run_artifacts(run_dir: Path, root: Path) -> dict[str, Any]:
    """Return a structured validation report for a `.runs/<run_id>` folder."""
    checks: dict[str, bool] = {}
    issues: list[str] = []

    run_id = run_dir.name
    paths = {name: run_dir / filename for name, filename in RUN_ARTIFACT_SPEC.items()}

    checks["run_id_format_valid"] = is_valid_run_id(run_id)
    if not checks["run_id_format_valid"]:
        issues.append(f"invalid run_id format: {run_id}")

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
    checks["provider_results_schema_valid"] = validate_provider_results(run_dir, root, issues)
    checks["agent_states_valid"] = validate_agent_states(state, issues)

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


def validate_agent_states(state: Any, issues: list[str]) -> bool:
    if not isinstance(state, dict):
        return False
    agents = state.get("agents")
    if not isinstance(agents, list):
        issues.append("run_state.agents must be a list")
        return False
    failed = [str(agent.get("name") or "unknown") for agent in agents if isinstance(agent, dict) and agent.get("status") == "failed"]
    if failed:
        issues.append(f"failed agent state requires review: {', '.join(failed)}")
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
        if draft.get("type") not in ALLOWED_MEMORY_TYPES:
            issues.append(f"memory_drafts[{index}].type is invalid: {draft.get('type')}")
            ok = False
        if draft.get("origin") not in ALLOWED_MEMORY_ORIGINS:
            issues.append(f"memory_drafts[{index}].origin is invalid: {draft.get('origin')}")
            ok = False
        if draft.get("status") not in ALLOWED_MEMORY_STATUSES:
            issues.append(f"memory_drafts[{index}].status is invalid: {draft.get('status')}")
            ok = False
        if not isinstance(draft.get("content"), str) or not draft.get("content", "").strip():
            issues.append(f"memory_drafts[{index}].content must be a non-empty string")
            ok = False
        if not isinstance(draft.get("project"), str) or not draft.get("project", "").strip():
            issues.append(f"memory_drafts[{index}].project must be a non-empty string")
            ok = False
        raw_refs = draft.get("raw_refs")
        if not isinstance(raw_refs, list) or not all(isinstance(ref, str) and ref for ref in raw_refs):
            issues.append(f"memory_drafts[{index}].raw_refs must be a list of non-empty strings")
            ok = False
    return ok


def validate_provider_results(run_dir: Path, root: Path, issues: list[str]) -> bool:
    ok = True
    result_paths = sorted((run_dir / "agents").glob("*/*_result.yaml"))
    for path in result_paths:
        data = load_yaml(path, "provider_result", issues, required=False)
        if not isinstance(data, dict):
            issues.append(f"provider result must be an object: {path.relative_to(root).as_posix()}")
            ok = False
            continue
        missing = sorted(REQUIRED_PROVIDER_RESULT_KEYS - set(data))
        if missing:
            issues.append(f"{path.relative_to(root).as_posix()} missing required keys: {', '.join(missing)}")
            ok = False
        if data.get("status") not in ALLOWED_PROVIDER_STATUSES:
            issues.append(f"{path.relative_to(root).as_posix()} has invalid status: {data.get('status')}")
            ok = False
        if data.get("provider_mode") not in ALLOWED_PROVIDER_MODES:
            issues.append(f"{path.relative_to(root).as_posix()} has invalid provider_mode: {data.get('provider_mode')}")
            ok = False
        for ref_key in ["prompt_path", "command_path", "stdout_path", "stderr_path", "output_path", "prompt", "command", "output"]:
            ref = data.get(ref_key)
            if isinstance(ref, str) and ref and not (root / ref).exists():
                issues.append(f"{path.relative_to(root).as_posix()} {ref_key} points to missing file: {ref}")
                ok = False
        for list_key in ["files_changed", "commands_run", "tests_run", "artifacts_created", "policy_violations", "memory_refs_used", "capability_refs_used"]:
            if list_key in data and not isinstance(data.get(list_key), list):
                issues.append(f"{path.relative_to(root).as_posix()} {list_key} must be a list")
                ok = False
        if data.get("risk_level") not in {"low", "medium", "high", "unknown"}:
            issues.append(f"{path.relative_to(root).as_posix()} has invalid risk_level: {data.get('risk_level')}")
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
