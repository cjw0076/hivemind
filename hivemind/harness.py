"""Structured blackboard run folders for the Hive Mind harness."""

from __future__ import annotations

import json
import os
import platform
import shlex
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

import yaml

from .local_workers import choose_model, read_input, run_worker, validate_worker_result, worker_route_table
from .capability_bridge import build_capabilityos_recommendation_report
from .memory_bridge import (
    build_memoryos_context_report,
    extract_memoryos_context_ids,
    write_memoryos_context_pack,
)
from .run_receipts import (
    collect_provider_results,
    git_changed_files,
    provider_result_paths,
    provider_result_record,
    rel_or_empty,
)
from .run_validation import validate_run_artifacts
from .utils import ensure_valid_run_id, is_valid_run_id, now_iso, stable_id


RUNS_DIR = ".runs"
CURRENT_FILE = "current"
CONTROL_LOCK_FILE = "control.lock"
PROVIDER_CAPABILITIES = "provider_capabilities.json"
GLOBAL_DIR = ".hivemind"
PROJECT_DIR = ".hivemind"
SETTINGS_PROFILE = "settings_profile.json"
CHECKS_DIR = "checks"
POLICY_FILE = "policy.yaml"
WORKING_METHOD_SKILL_DIR = "hive-working-method"
WORKING_METHOD_PHRASE = "evolution of Single Human Intelligence"
LLM_CHECKER_REPO = "https://github.com/Pavelevich/llm-checker"
LLM_CHECKER_NPM = "llm-checker"
AUTO_LOOP_ALLOWED_ACTIONS = {
    "audit",
    "verify",
    "memory-draft",
    "summarize",
    "diff",
    "check-run",
    "local-context",
    "local-review",
}

PIPELINE_SPEC = [
    ("intake", "task.yaml", "task"),
    ("route", "routing_plan.json", "routing_plan"),
    ("context", "context_pack.md", "context_pack"),
    ("deliberate", "agents/claude/planner_result.yaml", "claude_planner"),
    ("handoff", "handoff.yaml", "handoff"),
    ("execute", "agents/codex/executor_result.yaml", "codex_executor"),
    ("verify", "verification.yaml", "verification"),
    ("memory", "memory_drafts.json", "memory_drafts"),
    ("close", "final_report.md", "final_report"),
]


@dataclass(frozen=True)
class RunPaths:
    root: Path
    run_id: str

    def __post_init__(self) -> None:
        ensure_valid_run_id(self.run_id)

    @property
    def run_dir(self) -> Path:
        return self.root / RUNS_DIR / self.run_id

    @property
    def task(self) -> Path:
        return self.run_dir / "task.yaml"

    @property
    def context_pack(self) -> Path:
        return self.run_dir / "context_pack.md"

    @property
    def handoff(self) -> Path:
        return self.run_dir / "handoff.yaml"

    @property
    def events(self) -> Path:
        return self.run_dir / "events.jsonl"

    @property
    def state(self) -> Path:
        return self.run_dir / "run_state.json"

    @property
    def final_report(self) -> Path:
        return self.run_dir / "final_report.md"

    @property
    def transcript(self) -> Path:
        return self.run_dir / "transcript.md"

    @property
    def hive_events(self) -> Path:
        return self.run_dir / "hive_events.jsonl"

    @property
    def artifacts(self) -> Path:
        return self.run_dir / "artifacts"

    @property
    def control_lock(self) -> Path:
        return self.run_dir / CONTROL_LOCK_FILE

    @property
    def local_dir(self) -> Path:
        return self.run_dir / "agents" / "local"

    @property
    def claude_dir(self) -> Path:
        return self.run_dir / "agents" / "claude"

    @property
    def codex_dir(self) -> Path:
        return self.run_dir / "agents" / "codex"

    @property
    def gemini_dir(self) -> Path:
        return self.run_dir / "agents" / "gemini"


def init_harness(root: Path) -> Path:
    runs_dir = root / RUNS_DIR
    runs_dir.mkdir(parents=True, exist_ok=True)
    readme = runs_dir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Hive Mind Runs\n\n"
            "This directory is the structured blackboard for Hive Mind `hive` runs.\n"
            "Each run stores task, context, handoff, events, verification, and memory draft artifacts.\n",
            encoding="utf-8",
        )
    return runs_dir


def init_onboarding(root: Path) -> dict[str, Any]:
    """Initialize global/project Hive Mind state and detect provider runtimes."""
    runs_dir = init_harness(root)
    global_dir = Path.home() / GLOBAL_DIR
    project_dir = root / PROJECT_DIR
    created: list[str] = []
    existing: list[str] = []

    for directory in [
        global_dir,
        global_dir / "skills",
        global_dir / "runs",
        global_dir / "imports",
        global_dir / "db",
        global_dir / "logs",
        global_dir / "mcp",
        global_dir / "cache",
        project_dir,
        project_dir / "runs",
        project_dir / "context",
        project_dir / "skills",
        project_dir / CHECKS_DIR,
    ]:
        if directory.exists():
            existing.append(directory.as_posix())
        else:
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory.as_posix())

    files = {
        global_dir / "config.yaml": default_global_config(root),
        global_dir / "agents.yaml": default_agents_yaml(),
        global_dir / "routing.yaml": default_routing_yaml(),
        project_dir / "project.yaml": default_project_yaml(root),
        project_dir / "routing.yaml": default_routing_yaml(),
        project_dir / "README.md": default_project_readme(),
        project_dir / POLICY_FILE: default_policy_yaml(),
        project_dir / "skills" / WORKING_METHOD_SKILL_DIR / "SKILL.md": default_working_method_skill(),
        project_dir / CHECKS_DIR / "memory-policy.md": default_check_memory_policy(),
        project_dir / CHECKS_DIR / "no-raw-export-leak.md": default_check_no_raw_export_leak(),
        project_dir / CHECKS_DIR / "implementation-handoff.md": default_check_implementation_handoff(),
    }
    for path, content in files.items():
        if path.exists():
            existing.append(path.as_posix())
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            created.append(path.as_posix())

    providers = detect_agents(root, write=True)
    local_runtime = local_runtime_report(root, write=True)
    settings_profile = write_settings_profile(root, providers=providers, local_runtime=local_runtime)
    report = doctor_report(root)
    next_actions = [
        {
            "command": "hive demo quickstart",
            "reason": "see the audited run, receipts, memory draft, and MemoryOS read model without provider keys",
        },
        {
            "command": "hive demo memory-loop",
            "reason": "optional: prove Hive can feed MemoryOS and use accepted memory in the next run",
        },
        {
            "command": 'hive run "your task"',
            "reason": "start a real bounded run after the demos",
        },
        {
            "command": "hive inspect <run_id>",
            "reason": "inspect receipts, ledger replay, provider/local results, and next action",
        },
        {
            "command": "hive goal",
            "reason": "show the active production-v0 goal, validation loop, and reviewer attack prompt",
        },
    ]
    return {
        "schema_version": 1,
        "kind": "hive_onboarding",
        "generated_at": now_iso(),
        "global_dir": global_dir.as_posix(),
        "project_dir": project_dir.as_posix(),
        "runs_dir": runs_dir.as_posix(),
        "created": created,
        "existing": existing,
        "providers": providers["providers"],
        "local_runtime": local_runtime,
        "settings_profile": settings_profile,
        "doctor": report,
        "next_actions": next_actions,
    }


def format_onboarding(report: dict[str, Any]) -> str:
    lines = [
        "Welcome to Hive Mind.",
        "",
        "Initialized:",
        f"✓ Global home: {report['global_dir']}",
        f"✓ Project config: {report['project_dir']}",
        f"✓ Run blackboard: {report['runs_dir']}",
        "",
        "Provider Detection:",
    ]
    for name, provider in report["providers"].items():
        ok = provider.get("status") in {"available", "configured"}
        gated = provider.get("status") == "gated"
        icon = "✓" if ok else ("!" if gated else "○")
        detail = provider.get("version") or provider.get("path") or provider.get("reason", "")
        lines.append(f"{icon} {name}: {provider.get('status')} {detail}")
    local_runtime = report.get("local_runtime") or {}
    backend = active_local_backend(local_runtime)
    lines.extend(["", "Local Models:"])
    models = backend.get("models") or []
    if models:
        for model in models:
            lines.append(f"✓ {model}")
    else:
        lines.append("○ no local backend model manifests found")
    missing = local_runtime.get("missing_recommended_models") or []
    if missing:
        lines.append("Missing recommended:")
        for model in missing:
            lines.append(f"○ {model}")
    if local_runtime.get("open_weight_note"):
        lines.append(local_runtime["open_weight_note"])
    settings_profile = report.get("settings_profile") or {}
    lines.extend(["", "Settings Profile:"])
    lines.append(f"✓ project: {settings_profile.get('project_profile')}")
    lines.append(f"✓ global: {settings_profile.get('global_profile')}")
    if settings_profile.get("warnings"):
        lines.append("Warnings:")
        for warning in settings_profile["warnings"]:
            lines.append(f"! {warning}")
    lines.extend(["", "Recommended Path:"])
    for index, item in enumerate(report.get("next_actions") or [], start=1):
        lines.append(f"{index}. {item.get('command')} — {item.get('reason')}")
    lines.extend(
        [
            "",
            "Optional setup:",
            "• hive doctor",
            "• eval \"$(hive settings shell)\"",
            "• hive local setup",
            "• hive mcp install --for all",
        ]
    )
    return "\n".join(lines)


def create_run(root: Path, user_request: str, project: str = "Hive Mind", task_type: str = "implementation") -> RunPaths:
    init_harness(root)
    run_id = make_run_id(user_request)
    paths = RunPaths(root=root, run_id=run_id)
    paths.local_dir.mkdir(parents=True, exist_ok=True)
    paths.artifacts.mkdir(parents=True, exist_ok=True)
    (paths.run_dir / "agents" / "claude").mkdir(parents=True, exist_ok=True)
    (paths.run_dir / "agents" / "codex").mkdir(parents=True, exist_ok=True)
    (paths.run_dir / "agents" / "gemini").mkdir(parents=True, exist_ok=True)

    state = {
        "run_id": run_id,
        "user_request": user_request,
        "project": project,
        "task_type": task_type,
        "phase": "planned",
        "status": "planned",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "agents": [
            {"name": "local-context-compressor", "status": "pending"},
            {"name": "claude-planner", "status": "pending"},
            {"name": "codex-executor", "status": "pending"},
            {"name": "gemini-reviewer", "status": "pending"},
            {"name": "local-log-summarizer", "status": "pending"},
            {"name": "verifier", "status": "pending"},
        ],
        "context": {"memories_used": 0, "active_decisions": 0, "open_questions": 0},
        "latest_event": "Run created.",
        "artifacts": {
            "task": paths.task.relative_to(root).as_posix(),
            "context_pack": paths.context_pack.relative_to(root).as_posix(),
            "handoff": paths.handoff.relative_to(root).as_posix(),
            "events": paths.events.relative_to(root).as_posix(),
            "verification": (paths.run_dir / "verification.yaml").relative_to(root).as_posix(),
            "memory_drafts": (paths.run_dir / "memory_drafts.json").relative_to(root).as_posix(),
            "final_report": paths.final_report.relative_to(root).as_posix(),
            "transcript": paths.transcript.relative_to(root).as_posix(),
            "hive_events": paths.hive_events.relative_to(root).as_posix(),
        },
    }
    write_json(paths.state, state)
    paths.task.write_text(format_task_yaml(state), encoding="utf-8")
    paths.context_pack.write_text(default_context_pack(state, root), encoding="utf-8")
    paths.handoff.write_text(default_handoff_yaml(state), encoding="utf-8")
    (paths.run_dir / "verification.yaml").write_text(default_verification_yaml(state), encoding="utf-8")
    write_json(paths.run_dir / "memory_drafts.json", {"memory_drafts": []})
    paths.final_report.write_text(default_final_report(state), encoding="utf-8")
    append_event(paths, "run_created", {"task": user_request})
    append_transcript(paths, "Run", f'Created `{run_id}` for task: {user_request}')
    append_hive_activity(paths, "user", "task_received", f"Task received: {user_request}", {"task": user_request})
    set_current(root, run_id)
    return paths


def load_run(root: Path, run_id: str | None = None) -> tuple[RunPaths, dict[str, Any]]:
    actual_run_id = run_id or get_current(root)
    if not actual_run_id:
        raise FileNotFoundError("No current run. Create one with: hive run \"task\"")
    actual_run_id = ensure_valid_run_id(actual_run_id)
    paths = RunPaths(root=root, run_id=actual_run_id)
    if not paths.state.exists():
        raise FileNotFoundError(f"Run state not found: {paths.state}")
    try:
        return paths, json.loads(paths.state.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"run state corrupted ({paths.run_id}): {exc}. "
            "Recover with: hive audit --run-id " + paths.run_id
        ) from exc


def acquire_control_lock(root: Path, run_id: str | None = None, role: str = "controller", ttl_seconds: int = 120) -> dict[str, Any]:
    """Acquire the single write-capable controller lock for a run."""
    paths, _ = load_run(root, run_id)
    now = time.time()
    existing = read_control_lock(paths)
    if existing and not is_control_lock_stale(existing, now, ttl_seconds):
        holder = existing.get("session_id") or "unknown"
        pid = existing.get("pid") or "unknown"
        raise RuntimeError(f"run already has an active controller: {holder} pid={pid}")
    session_id = stable_id("sess", paths.run_id, os.getpid(), now)
    lock = {
        "schema_version": 1,
        "session_id": session_id,
        "role": role,
        "pid": os.getpid(),
        "started_at": now_iso(),
        "last_heartbeat": now_iso(),
        "last_heartbeat_epoch": now,
        "ttl_seconds": ttl_seconds,
    }
    write_json(paths.control_lock, lock)
    append_event(paths, "control_lock_acquired", {"session_id": session_id, "role": role})
    return lock


def heartbeat_control_lock(root: Path, run_id: str | None, session_id: str) -> None:
    paths, _ = load_run(root, run_id)
    lock = read_control_lock(paths)
    if not lock or lock.get("session_id") != session_id:
        raise RuntimeError("controller lock lost")
    lock["last_heartbeat"] = now_iso()
    lock["last_heartbeat_epoch"] = time.time()
    write_json(paths.control_lock, lock)


def release_control_lock(root: Path, run_id: str | None, session_id: str) -> None:
    paths, _ = load_run(root, run_id)
    lock = read_control_lock(paths)
    if lock and lock.get("session_id") == session_id:
        paths.control_lock.unlink(missing_ok=True)
        append_event(paths, "control_lock_released", {"session_id": session_id})


def read_control_lock(paths: RunPaths) -> dict[str, Any] | None:
    if not paths.control_lock.exists():
        return None
    try:
        data = json.loads(paths.control_lock.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {
            "schema_version": 1,
            "session_id": "invalid",
            "role": "controller",
            "last_heartbeat_epoch": 0,
        }
    return data if isinstance(data, dict) else None


def is_control_lock_stale(lock: dict[str, Any], now: float | None = None, ttl_seconds: int = 120) -> bool:
    pid = lock.get("pid")
    if isinstance(pid, int) and pid > 0 and not process_is_alive(pid):
        return True
    heartbeat = lock.get("last_heartbeat_epoch")
    if not isinstance(heartbeat, (int, float)):
        return True
    return (now or time.time()) - float(heartbeat) > ttl_seconds


def process_is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def list_runs(root: Path) -> list[dict[str, Any]]:
    runs_dir = root / RUNS_DIR
    if not runs_dir.exists():
        return []
    runs = []
    for state_path in sorted(runs_dir.glob("*/run_state.json"), reverse=True):
        if not is_valid_run_id(state_path.parent.name):
            continue
        try:
            runs.append(json.loads(state_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            runs.append({"run_id": state_path.parent.name, "status": "corrupt"})
    return runs


def run_board(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    artifacts = artifact_status(paths, state)
    pipeline = pipeline_status(paths)
    next_action = recommend_next_action(paths, state, pipeline, artifacts)
    return {
        "schema_version": 1,
        "run_id": paths.run_id,
        "task": state.get("user_request"),
        "project": state.get("project"),
        "phase": state.get("phase"),
        "status": state.get("status"),
        "pipeline": pipeline,
        "agents": state.get("agents", []),
        "artifacts": artifacts,
        "next": next_action,
    }


def artifact_status(paths: RunPaths, state: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for name, rel_path in (state.get("artifacts") or {}).items():
        path = paths.root / rel_path if isinstance(rel_path, str) else None
        exists = bool(path and path.exists())
        rows.append(build_artifact_row(name, rel_path, exists, path, state))
    extra = {
        "routing_plan": paths.run_dir / "routing_plan.json",
        "society_plan": paths.run_dir / "society_plan.json",
        "hive_events": paths.hive_events,
        "checks_report": paths.run_dir / "checks_report.json",
        "git_diff_report": paths.run_dir / "git_diff_report.json",
        "commit_summary": paths.run_dir / "commit_summary.md",
    }
    known = {row["name"] for row in rows}
    for name, path in extra.items():
        if name not in known:
            rows.append(build_artifact_row(name, path.relative_to(paths.root).as_posix(), path.exists(), path, state))
    return rows


def build_artifact_row(name: str, rel_path: Any, exists: bool, path: Path | None, state: dict[str, Any]) -> dict[str, Any]:
    freshness = artifact_freshness(name, exists, path, state)
    return {
        "name": name,
        "path": rel_path,
        "status": "ok" if exists else "missing",
        "exists": exists,
        "phase_class": artifact_phase_class(name),
        "producer": artifact_producer(name),
        "freshness": freshness,
        "validated": freshness in {"fresh", "initial"},
    }


def artifact_phase_class(name: str) -> str:
    if name in {"task", "events", "run_state", "routing_plan", "society_plan"}:
        return "required"
    if name in {"context_pack", "handoff", "verification", "memory_drafts", "final_report", "hive_events"}:
        return "phase"
    if name in {"checks_report", "git_diff_report", "commit_summary"}:
        return "post_execution"
    return "optional"


def artifact_producer(name: str) -> str:
    return {
        "task": "system",
        "context_pack": "system/local-context",
        "handoff": "claude/planner",
        "events": "system",
        "run_state": "system",
        "verification": "verifier",
        "memory_drafts": "hive/memory-draft",
        "final_report": "hive/summary",
        "transcript": "system",
        "hive_events": "hive",
        "routing_plan": "local/intent-router",
        "society_plan": "hive/orchestrator",
        "checks_report": "hive/check",
        "git_diff_report": "git",
        "commit_summary": "hive/commit-summary",
    }.get(name, "unknown")


def artifact_freshness(name: str, exists: bool, path: Path | None, state: dict[str, Any]) -> str:
    if not exists:
        return "missing"
    if name == "context_pack" and agent_status(state, "local-context-compressor") != "completed":
        return "stale"
    if name == "verification" and path and "not_run" in path.read_text(encoding="utf-8", errors="replace"):
        return "stale"
    if name == "memory_drafts" and path and memory_draft_count(path) == 0:
        return "empty"
    if name == "final_report" and path and "Status: planned" in path.read_text(encoding="utf-8", errors="replace"):
        return "initial"
    return "fresh"


def pipeline_status(paths: RunPaths) -> list[dict[str, Any]]:
    rows = []
    for name, rel_path, artifact_id in PIPELINE_SPEC:
        path = paths.run_dir / rel_path
        status = "done" if path.exists() else "pending"
        if name == "verify" and path.exists():
            text = path.read_text(encoding="utf-8")
            status = "pending" if "not_run" in text else "done"
        if name == "memory" and path.exists():
            status = "done" if memory_draft_count(path) > 0 else "pending"
        if name == "close" and path.exists():
            text = path.read_text(encoding="utf-8")
            status = "pending" if "Status: planned" in text else "done"
        rows.append(
            {
                "step": name,
                "artifact": artifact_id,
                "path": path.relative_to(paths.root).as_posix(),
                "status": status,
            }
        )
    return rows


def recommend_next_action(
    paths: RunPaths,
    state: dict[str, Any],
    pipeline: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, str]:
    by_step = {item["step"]: item for item in pipeline}
    if by_step["route"]["status"] != "done":
        return {"command": f'hive ask "{state.get("user_request", "")}"', "reason": "routing_plan.json is missing"}
    local_context_status = agent_status(state, "local-context-compressor")
    if local_context_status == "failed":
        return {"command": "hive audit", "reason": "local context worker failed and needs review before retry"}
    if local_context_status not in {"completed"}:
        return {"command": "hive invoke local --role context", "reason": "context compression has not completed"}
    if agent_status(state, "claude-planner") not in {"prepared", "completed"}:
        return {"command": "hive invoke claude --role planner", "reason": "planner artifact is not prepared"}
    if agent_status(state, "codex-executor") not in {"prepared", "completed"}:
        return {"command": "hive invoke codex --role executor", "reason": "executor artifact is not prepared"}
    verification = paths.run_dir / "verification.yaml"
    if not verification.exists() or "not_run" in verification.read_text(encoding="utf-8"):
        return {"command": "hive verify", "reason": "verification is missing or has not run"}
    memory_drafts = paths.run_dir / "memory_drafts.json"
    try:
        drafts = json.loads(memory_drafts.read_text(encoding="utf-8")).get("memory_drafts") or []
    except (OSError, json.JSONDecodeError):
        drafts = []
    if not drafts:
        return {"command": "hive memory draft", "reason": "memory_drafts.json has no drafts"}
    final_report = paths.final_report
    if "Status: planned" in final_report.read_text(encoding="utf-8"):
        return {"command": "hive summarize", "reason": "final_report.md is still the initial report"}
    return {"command": "hive check run", "reason": "run artifacts are ready for policy checks"}


def next_grounded_action(root: Path, run_id: str | None = None) -> dict[str, Any]:
    """One-line operator decision grounded in run state, escalations, and DAG."""
    from .plan_dag import load_dag

    paths, state = load_run(root, run_id)
    run_id = paths.run_id

    # 1. Topology escalation overrides everything
    dis_path = paths.run_dir / "disagreements.json"
    if dis_path.exists():
        try:
            records = json.loads(dis_path.read_text(encoding="utf-8"))
            high = [r for r in records if isinstance(r, dict) and r.get("severity") in {"high", "medium"}]
            if high:
                return {
                    "source": "disagreement_topology",
                    "run_id": run_id,
                    "command": f"hive inspect {run_id}",
                    "reason": f"{len(high)} topology escalation(s): {', '.join(r.get('dominant_axis','?') for r in high[:3])}",
                }
        except Exception:
            pass

    # 2. DAG next step (if plan_dag is active)
    dag = load_dag(root, run_id)
    if dag is not None and not dag.is_complete():
        if dag.is_blocked():
            return {
                "source": "plan_dag",
                "run_id": run_id,
                "command": "hive step list",
                "reason": "DAG is blocked — check failed steps",
            }
        next_step = dag.next_sequential()
        if next_step:
            provider = "/".join(next_step.provider_candidates) or "harness"
            return {
                "source": "plan_dag",
                "run_id": run_id,
                "command": f"hive step run {next_step.step_id}",
                "reason": f"{next_step.owner_role} via {provider}",
            }

    # 3. Provider/local failures → inspect
    agents_dir = paths.run_dir / "agents"
    if agents_dir.exists():
        for result_path in agents_dir.rglob("*.yaml"):
            try:
                data = yaml.safe_load(result_path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict) and data.get("status") == "failed":
                    return {
                        "source": "provider_failure",
                        "run_id": run_id,
                        "command": f"hive inspect {run_id} --verbose",
                        "reason": f"provider failure: {data.get('provider','?')}/{data.get('role','?')}",
                    }
            except Exception:
                pass

    # 4. Pipeline-based recommendation
    pipeline = pipeline_status(paths)
    artifacts = artifact_status(paths, state)
    action = recommend_next_action(paths, state, pipeline, artifacts)
    return {"source": "pipeline", "run_id": run_id, **action}


def memory_draft_count(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    drafts = data.get("memory_drafts") if isinstance(data, dict) else None
    return len(drafts) if isinstance(drafts, list) else 0


def agent_status(state: dict[str, Any], name: str) -> str | None:
    for agent in state.get("agents", []):
        if agent.get("name") == name:
            return agent.get("status")
    return None


def format_run_board(board: dict[str, Any]) -> str:
    lines = [
        f"Hive Mind Run: {board.get('run_id')}",
        f"Task: {board.get('task')}",
        f"Project: {board.get('project')} | Phase: {board.get('phase')} | Status: {board.get('status')}",
        "",
        "Pipeline:",
    ]
    lines.append("  " + "  ".join(f"{pipeline_icon(item['status'])} {item['step']}" for item in board["pipeline"]))
    lines.extend(["", "Agents:"])
    for agent in board.get("agents") or []:
        lines.append(f"  {agent_icon(agent.get('status'))} {agent.get('name')} [{agent.get('status')}]")
    lines.extend(["", "Artifacts:"])
    for item in board.get("artifacts") or []:
        lines.append(f"  {pipeline_icon('done' if item.get('status') == 'ok' else 'pending')} {item.get('name')}: {item.get('path')} [{item.get('status')}]")
    next_action = board.get("next") or {}
    lines.extend(["", "Next:", f"  {next_action.get('command')}", f"  Reason: {next_action.get('reason')}"])
    return "\n".join(lines)


def pipeline_icon(status: str | None) -> str:
    return "✓" if status in {"done", "ok", "completed"} else "○"


def agent_icon(status: str | None) -> str:
    return {
        "completed": "✓",
        "prepared": "◐",
        "running": "●",
        "in_progress": "●",
        "failed": "!",
        "pending": "○",
    }.get(status or "", "○")


def format_agents_status(report: dict[str, Any]) -> str:
    lines = ["Hive Mind Agents", "", "Provider        Mode               Status        Roles"]
    for name, provider in (report.get("providers") or {}).items():
        status = str(provider.get("status") or "unknown")
        mode = str(provider.get("mode") or "-")
        roles = ", ".join(str(role) for role in (provider.get("roles") or []))
        icon = "✓" if status in {"available", "configured"} else ("!" if status == "gated" else "○")
        lines.append(f"{icon} {name:<13} {mode:<18} {status:<13} {roles}")
    lines.extend(["", f"Registry: {report.get('trusted_root')}/.runs/{PROVIDER_CAPABILITIES}"])
    return "\n".join(lines)


def memory_drafts_report(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, _ = load_run(root, run_id)
    draft_path = paths.run_dir / "memory_drafts.json"
    drafts: list[dict[str, Any]] = []
    if draft_path.exists():
        try:
            data = json.loads(draft_path.read_text(encoding="utf-8"))
            raw = data.get("memory_drafts") if isinstance(data, dict) else []
            if isinstance(raw, list):
                drafts = [item for item in raw if isinstance(item, dict)]
        except json.JSONDecodeError:
            drafts = []
    return {
        "run_id": paths.run_id,
        "path": draft_path.relative_to(root).as_posix(),
        "count": len(drafts),
        "drafts": drafts,
    }


def format_memory_drafts(report: dict[str, Any]) -> str:
    lines = [f"Memory Drafts: {report.get('run_id')}", f"Path: {report.get('path')}", f"Count: {report.get('count')}", ""]
    drafts = report.get("drafts") or []
    if not drafts:
        lines.append("No memory drafts yet. Next: hive memory draft")
        return "\n".join(lines)
    for index, draft in enumerate(drafts, start=1):
        kind = draft.get("type") or "memory"
        status = draft.get("status") or "draft"
        confidence = draft.get("confidence", "-")
        content = str(draft.get("content") or "").replace("\n", " ")
        if len(content) > 140:
            content = content[:139] + "…"
        lines.append(f"{index}. [{status}] {kind} confidence={confidence}")
        lines.append(f"   {content}")
    return "\n".join(lines)


def set_current(root: Path, run_id: str) -> None:
    run_id = ensure_valid_run_id(run_id)
    runs_dir = init_harness(root)
    (runs_dir / CURRENT_FILE).write_text(run_id + "\n", encoding="utf-8")


def get_current(root: Path) -> str | None:
    current = root / RUNS_DIR / CURRENT_FILE
    if not current.exists():
        return None
    value = current.read_text(encoding="utf-8").strip()
    return ensure_valid_run_id(value) if value else None


_detect_agents_cache: tuple[str, float, dict[str, Any]] | None = None
_DETECT_AGENTS_CACHE_TTL = 30.0  # seconds (in-process)
_DETECT_AGENTS_FILE_TTL = 300.0  # seconds (on-disk)


def detect_agents(root: Path, write: bool = True) -> dict[str, Any]:
    global _detect_agents_cache
    root_key = root.as_posix()
    now = time.time()
    # 1. In-process cache (30s TTL — fastest)
    if (
        _detect_agents_cache is not None
        and _detect_agents_cache[0] == root_key
        and now - _detect_agents_cache[1] < _DETECT_AGENTS_CACHE_TTL
    ):
        cached = _detect_agents_cache[2]
        if write:
            write_json(root / RUNS_DIR / PROVIDER_CAPABILITIES, cached)
        return cached
    # 2. On-disk cache (5min TTL — skip subprocess probes if recent)
    caps_path = root / RUNS_DIR / PROVIDER_CAPABILITIES
    if caps_path.exists():
        try:
            cached_file = json.loads(caps_path.read_text(encoding="utf-8"))
            if isinstance(cached_file, dict) and "generated_at" in cached_file:
                from datetime import datetime, timezone
                gen_ts = datetime.fromisoformat(cached_file["generated_at"].replace("Z", "+00:00"))
                age = (datetime.now(timezone.utc) - gen_ts).total_seconds()
                if age < _DETECT_AGENTS_FILE_TTL:
                    _detect_agents_cache = (root_key, now, cached_file)
                    return cached_file
        except Exception:
            pass
    init_harness(root)
    providers = {
        "claude": probe_command("claude", ["--version"], roles=["planner", "reviewer", "claim-auditor"]),
        "codex": probe_command("codex", ["--version"], roles=["executor", "test-fixer", "diff-reviewer"], mode="execute_supported"),
        "gemini": probe_command("gemini", ["--version"], roles=["reviewer", "alternate-planner", "multimodal-reviewer"]),
        "local_backend": probe_local_backend(root),
        "ollama": probe_ollama(root),
        "deepseek_api": probe_env_provider("deepseek_api", "DEEPSEEK_API_KEY", roles=["cheap-critic", "batch-summarizer", "code-review-draft"]),
        "qwen_api": probe_env_provider("qwen_api", "QWEN_API_KEY", roles=["open-coder-reviewer", "cheap-planner", "capability-extractor"]),
        "opencode": probe_optional_cli("opencode", roles=["executor", "reviewer", "github-runner"]),
        "goose": probe_optional_cli("goose", roles=["agent-runtime", "desktop-bridge", "mcp-extension-runtime"]),
        "openclaude": probe_optional_cli("openclaude", roles=["multi-provider-shell", "mcp-tool-runner"]),
    }
    result = {
        "generated_at": now_iso(),
        "trusted_root": root.as_posix(),
        "providers": providers,
    }
    _detect_agents_cache = (root_key, now, result)
    if write:
        write_json(root / RUNS_DIR / PROVIDER_CAPABILITIES, result)
    return result


def build_settings_profile(
    root: Path,
    providers: dict[str, Any] | None = None,
    local_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create the persisted settings profile used by scripts and provider launchers."""
    providers = providers or detect_agents(root, write=True)
    local_runtime = local_runtime or local_runtime_report(root, write=False)
    provider_items = providers.get("providers", {})
    warnings = []
    shell_exports: dict[str, str] = {
        "HIVE_ROOT": root.as_posix(),
        "HIVE_RUNS_DIR": (root / RUNS_DIR).as_posix(),
    }
    tracked_providers: dict[str, Any] = {}
    for name, item in provider_items.items():
        command_path = item.get("path") or item.get("command")
        tracked = {
            "status": item.get("status"),
            "command": item.get("command"),
            "path": command_path,
            "version": item.get("version", ""),
            "mode": item.get("mode"),
            "roles": item.get("roles", []),
            "reason": item.get("reason", ""),
        }
        tracked_providers[name] = tracked
        if command_path:
            shell_exports[f"HIVE_{name.upper()}_BIN"] = command_path
        if item.get("status") == "gated":
            warnings.append(f"{name} first candidate is gated: {item.get('reason', '')}".strip())
    codex = provider_items.get("codex") or {}
    codex_path = codex.get("path") or ""
    path_codex = shutil.which("codex") or ""
    if codex_path and path_codex and codex_path != path_codex:
        warnings.append(f"codex PATH resolves to {path_codex}, but usable binary is {codex_path}")
    backend = active_local_backend(local_runtime) if isinstance(local_runtime, dict) else {}
    if backend.get("path"):
        shell_exports["HIVE_LOCAL_BACKEND_BIN"] = backend["path"]
    ollama = (local_runtime.get("ollama") or {}) if isinstance(local_runtime, dict) else {}
    if ollama.get("path"):
        shell_exports["HIVE_OLLAMA_BIN"] = ollama["path"]
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "root": root.as_posix(),
        "providers": tracked_providers,
        "local_runtime": local_runtime,
        "shell_exports": shell_exports,
        "warnings": warnings,
    }


def write_settings_profile(
    root: Path,
    providers: dict[str, Any] | None = None,
    local_runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = build_settings_profile(root, providers=providers, local_runtime=local_runtime)
    project_dir = root / PROJECT_DIR
    global_dir = Path.home() / GLOBAL_DIR
    project_dir.mkdir(parents=True, exist_ok=True)
    global_dir.mkdir(parents=True, exist_ok=True)
    project_profile = project_dir / SETTINGS_PROFILE
    global_profile = global_dir / SETTINGS_PROFILE
    write_json(project_profile, profile)
    write_json(global_profile, profile)
    return {
        "project_profile": project_profile.as_posix(),
        "global_profile": global_profile.as_posix(),
        "warnings": profile.get("warnings", []),
        "shell_exports": profile.get("shell_exports", {}),
    }


def settings_report(root: Path, write: bool = True) -> dict[str, Any]:
    providers = detect_agents(root, write=True)
    local_runtime = local_runtime_report(root, write=True)
    profile_summary = write_settings_profile(root, providers=providers, local_runtime=local_runtime) if write else {}
    profile = build_settings_profile(root, providers=providers, local_runtime=local_runtime)
    profile.update(profile_summary)
    return profile


def format_settings(report: dict[str, Any]) -> str:
    lines = ["Hive Mind Settings Profile", "", f"Root: {report.get('root')}"]
    if report.get("project_profile"):
        lines.append(f"Project profile: {report.get('project_profile')}")
    if report.get("global_profile"):
        lines.append(f"Global profile: {report.get('global_profile')}")
    lines.extend(["", "Providers:"])
    for name, provider in (report.get("providers") or {}).items():
        detail = provider.get("version") or provider.get("path") or provider.get("reason", "")
        icon = "✓" if provider.get("status") in {"available", "configured"} else ("!" if provider.get("status") == "gated" else "○")
        lines.append(f"{icon} {name}: {provider.get('status')} {detail}")
    lines.extend(["", "Shell:"])
    lines.append('eval "$(hive settings shell)"')
    if report.get("warnings"):
        lines.extend(["", "Warnings:"])
        for warning in report["warnings"]:
            lines.append(f"! {warning}")
    return "\n".join(lines)


def format_settings_shell(report: dict[str, Any]) -> str:
    lines = ["# Hive Mind shell profile"]
    for key, value in sorted((report.get("shell_exports") or {}).items()):
        lines.append(f"export {key}={shlex.quote(str(value))}")
    return "\n".join(lines)


def doctor_report(root: Path) -> dict[str, Any]:
    runs_dir = init_harness(root)
    current = get_current(root)
    providers = detect_agents(root, write=True)
    checks = {
        "runs_dir": {"status": "ok", "path": runs_dir.as_posix()},
        "current_run": {"status": "ok" if current else "missing", "run_id": current},
        "provider_capabilities": {
            "status": "ok",
            "path": (runs_dir / PROVIDER_CAPABILITIES).as_posix(),
        },
    }
    available = [name for name, item in providers["providers"].items() if item.get("status") in {"available", "configured"}]
    missing = [name for name, item in providers["providers"].items() if item.get("status") not in {"available", "configured"}]
    return {
        "generated_at": now_iso(),
        "status": "ready" if {"claude", "codex", "gemini"}.intersection(available) else "needs_setup",
        "checks": checks,
        "available_providers": available,
        "missing_or_unconfigured_providers": missing,
        "providers": providers["providers"],
    }


def doctor_scope_report(root: Path, scope: str = "all") -> dict[str, Any]:
    if scope not in {"hardware", "providers", "models", "permissions", "all"}:
        raise ValueError(f"unknown doctor scope: {scope}")
    generated_at = now_iso()
    reports: dict[str, Any] = {}
    if scope in {"providers", "all"}:
        reports["providers"] = doctor_report(root)
    if scope in {"hardware", "all"}:
        reports["hardware"] = hardware_report(root)
    if scope in {"models", "all"}:
        reports["models"] = models_report(root)
    if scope in {"permissions", "all"}:
        reports["permissions"] = permissions_report(root)
    statuses = [item.get("status") for item in reports.values() if isinstance(item, dict)]
    status = "ready" if statuses and all(item == "ready" for item in statuses) else "needs_setup"
    return {
        "schema_version": 1,
        "generated_at": generated_at,
        "scope": scope,
        "status": status,
        "reports": reports,
    }


def hardware_report(root: Path) -> dict[str, Any]:
    providers = detect_agents(root, write=True)
    disk = shutil.disk_usage(root)
    gpus = probe_gpus()
    runtime = {
        "python": {
            "status": "available",
            "path": sys.executable,
            "version": platform.python_version(),
        },
        "node": probe_binary_version("node", ["--version"]),
        "docker": probe_binary_version("docker", ["--version"]),
        "ollama_adapter": probe_binary_version("ollama", ["--version"]),
        "llama_cpp_adapter": probe_binary_version("llama-cli", ["--version"]),
    }
    warnings = []
    if not gpus:
        warnings.append("no NVIDIA GPU detected through nvidia-smi")
    if runtime["node"].get("status") != "available":
        warnings.append("node is unavailable")
    if runtime["docker"].get("status") != "available":
        warnings.append("docker is unavailable")
    if runtime["ollama_adapter"].get("status") != "available" and runtime["llama_cpp_adapter"].get("status") != "available":
        warnings.append("no local model adapter binary found on PATH; optional workspace adapters may still work")
    ports = {
        "local_ollama_adapter": probe_tcp_port("127.0.0.1", 11434),
        "dev_8000": probe_tcp_port("127.0.0.1", 8000),
        "dev_8080": probe_tcp_port("127.0.0.1", 8080),
    }
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "status": "ready" if runtime["python"].get("status") == "available" else "needs_setup",
        "system": {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "cpu": {
            "logical_count": os.cpu_count(),
        },
        "memory": memory_profile(),
        "gpu": gpus,
        "disk": {
            "path": root.as_posix(),
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
        },
        "runtime": runtime,
        "provider_cli_paths": provider_cli_paths(providers),
        "network": probe_network(),
        "ports": ports,
        "warnings": warnings,
    }


def models_report(root: Path) -> dict[str, Any]:
    local_runtime = local_runtime_report(root, write=True)
    backend = active_local_backend(local_runtime)
    present = set(backend.get("models") or [])
    routes = worker_route_table()
    role_assignments = []
    for role, route in routes.items():
        selected = choose_model(role, "default")
        role_assignments.append(
            {
                "role": role,
                "complexity": "default",
                "primary": (route.get("models") or {}).get("default"),
                "fallback": (route.get("models") or {}).get("fast"),
                "selected": selected,
                "available": local_model_available(selected, present),
            }
        )
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "status": "ready" if backend.get("models") else "needs_setup",
        "local_runtime": local_runtime,
        "role_assignments": role_assignments,
    }


def local_model_profile(root: Path, write: bool = True) -> dict[str, Any]:
    local_runtime = local_runtime_report(root, write=True)
    backend = active_local_backend(local_runtime)
    present = set(backend.get("models") or [])
    routes = worker_route_table()
    models: dict[str, dict[str, Any]] = {}
    for role, route in routes.items():
        model_names = route.get("models") or {}
        for complexity, model in model_names.items():
            item = models.setdefault(
                model,
                {
                    "available": local_model_available(model, present),
                    "recommended_roles": [],
                    "json_validity": None,
                    "latency_ms": None,
                    "benchmark_status": "not_run",
                    "benchmarks_by_role": {},
                },
            )
            item["recommended_roles"].append(f"{role}:{complexity}")
    profile = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "runtime": backend.get("id") or local_runtime.get("active_backend") or "none",
        "runtime_protocol": "hive-local-backend-v1",
        "status": "ready" if present else "needs_setup",
        "models": models,
        "role_assignments": models_report(root).get("role_assignments", []),
        "external_checker": llm_checker_detection(),
        "notes": [
            "Benchmark fields are placeholders until hive local benchmark runs real prompts.",
            "Optional llm-checker adapter can provide hardware-aware recommendations and calibration artifacts.",
            WORKING_METHOD_PHRASE,
        ],
    }
    if write:
        project_dir = root / PROJECT_DIR
        project_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_dir / "local_model_profile.json", profile)
    return profile


def format_local_model_profile(report: dict[str, Any]) -> str:
    lines = ["Hive Mind Local Model Profile", "", f"Status: {report.get('status')}"]
    for model, item in sorted((report.get("models") or {}).items()):
        marker = "✓" if item.get("available") else "○"
        roles = ", ".join(item.get("recommended_roles") or [])
        lines.append(f"{marker} {model}: {roles}")
    lines.extend(["", f"Thread: {WORKING_METHOD_PHRASE}"])
    return "\n".join(lines)


def llm_checker_detection(use_npx: bool = False) -> dict[str, Any]:
    path = shutil.which("llm-checker")
    npx = shutil.which("npx")
    if path:
        return {
            "status": "available",
            "command": [path],
            "path": path,
            "repo": LLM_CHECKER_REPO,
            "npm": LLM_CHECKER_NPM,
        }
    if use_npx and npx:
        return {
            "status": "npx_available",
            "command": [npx, "--yes", LLM_CHECKER_NPM],
            "path": npx,
            "repo": LLM_CHECKER_REPO,
            "npm": LLM_CHECKER_NPM,
        }
    return {
        "status": "unavailable",
        "command": [],
        "path": None,
        "repo": LLM_CHECKER_REPO,
        "npm": LLM_CHECKER_NPM,
        "install": "npm install -g llm-checker",
        "npx": "npx llm-checker hw-detect",
    }


def llm_checker_report(
    root: Path,
    category: str = "coding",
    use_npx: bool = False,
    execute: bool = False,
    write: bool = True,
) -> dict[str, Any]:
    detection = llm_checker_detection(use_npx=use_npx)
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "status": detection["status"],
        "source": {
            "repo": LLM_CHECKER_REPO,
            "npm": LLM_CHECKER_NPM,
            "checked_at": "2026-05-02",
            "capabilities": [
                "hardware-aware local model recommendation",
                "Ollama installed-model ranking",
                "calibration policy generation",
                "policy validation and audit export",
                "benchmark via CLI/MCP where installed",
            ],
        },
        "category": category,
        "detection": detection,
        "commands": {
            "detect": "llm-checker hw-detect",
            "installed": "llm-checker installed",
            "recommend": f"llm-checker recommend --category {category}",
            "calibrate": "llm-checker calibrate --suite <jsonl> --models <models...> --runtime ollama --objective balanced --output .hivemind/llm_checker_calibration.json --policy-out .hivemind/llm_checker_policy.yaml",
        },
        "executed": execute,
        "results": {},
        "working_method": WORKING_METHOD_PHRASE,
    }
    command = detection.get("command") or []
    if execute and command:
        report["results"] = {
            "version": run_llm_checker_command(command, ["--version"]),
            "hw_detect": run_llm_checker_command(command, ["hw-detect"]),
            "installed": run_llm_checker_command(command, ["installed"]),
            "recommend": run_llm_checker_command(command, ["recommend", "--category", category]),
        }
        failed = [name for name, item in report["results"].items() if item.get("returncode") not in {0, None}]
        report["status"] = "executed_with_errors" if failed else "executed"
    elif execute and not command:
        report["status"] = "unavailable"
        report["results"] = {"error": "llm-checker is not installed; pass --use-npx or install npm package"}
    if write:
        project_dir = root / PROJECT_DIR
        project_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_dir / "llm_checker_report.json", report)
    return report


def run_llm_checker_command(command: list[str], args: list[str], timeout: int = 60) -> dict[str, Any]:
    started = time.monotonic()
    try:
        completed = subprocess.run([*command, *args], text=True, capture_output=True, timeout=timeout)
        return {
            "command": [*command, *args],
            "returncode": completed.returncode,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "stdout": completed.stdout.strip()[-8000:],
            "stderr": completed.stderr.strip()[-4000:],
        }
    except Exception as exc:
        return {
            "command": [*command, *args],
            "returncode": None,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "stdout": "",
            "stderr": str(exc),
        }


def format_llm_checker_report(report: dict[str, Any]) -> str:
    source = report.get("source") or {}
    detection = report.get("detection") or {}
    lines = [
        "Hive Mind LLM Checker Adapter",
        "",
        f"Status: {report.get('status')}",
        f"Repo: {source.get('repo')}",
        f"NPM: {source.get('npm')}",
        f"Detected: {detection.get('status')}",
        "",
        "Planned commands:",
    ]
    for name, command in (report.get("commands") or {}).items():
        lines.append(f"- {name}: {command}")
    results = report.get("results") or {}
    if results:
        lines.extend(["", "Execution:"])
        for name, item in results.items():
            if isinstance(item, dict):
                lines.append(f"- {name}: returncode={item.get('returncode')} duration_ms={item.get('duration_ms')}")
            else:
                lines.append(f"- {name}: {item}")
    if detection.get("install"):
        lines.extend(["", "Install:", f"  {detection.get('install')}", f"  {detection.get('npx')}"])
    lines.extend(["", f"Thread: {report.get('working_method')}"])
    return "\n".join(lines)


def local_benchmark_report(
    root: Path,
    models: list[str] | None = None,
    roles: list[str] | None = None,
    backend: str = "auto",
    limit: int = 4,
    timeout: int = 90,
    write: bool = True,
) -> dict[str, Any]:
    runtime = local_runtime_report(root, write=True)
    active = resolve_benchmark_backend(runtime, backend)
    backend_info = (runtime.get("backends") or {}).get(active, {})
    available = list(backend_info.get("models") or [])
    selected = models or available[:limit]
    selected_roles = roles or ["json_normalizer"]
    results = []
    for model in selected:
        for role in selected_roles:
            results.append(benchmark_local_model(model, role=role, backend=active, timeout=timeout))
    valid = [item for item in results if item.get("schema_valid")]
    report = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "runtime": active,
        "runtime_protocol": "hive-local-backend-v1",
        "server": backend_info.get("server"),
        "status": "completed" if results else "needs_setup",
        "models_tested": selected,
        "roles_tested": selected_roles,
        "json_validity": (len(valid) / len(results)) if results else 0.0,
        "results": results,
        "working_method": WORKING_METHOD_PHRASE,
    }
    if write:
        project_dir = root / PROJECT_DIR
        project_dir.mkdir(parents=True, exist_ok=True)
        write_json(project_dir / "local_benchmark.json", report)
        profile = local_model_profile(root, write=False)
        for result in results:
            model_entry = (profile.get("models") or {}).get(result.get("model"))
            if model_entry is not None:
                model_entry["json_validity"] = 1.0 if result.get("schema_valid") else 0.0
                model_entry["latency_ms"] = result.get("latency_ms")
                model_entry["benchmark_status"] = result.get("status")
                role = result.get("role") or "unknown"
                model_entry.setdefault("benchmarks_by_role", {})[role] = {
                    "schema_valid": result.get("schema_valid"),
                    "json_valid": result.get("json_valid"),
                    "latency_ms": result.get("latency_ms"),
                    "status": result.get("status"),
                    "error": result.get("error", ""),
                }
        write_json(project_dir / "local_model_profile.json", profile)
    return report


def resolve_benchmark_backend(runtime: dict[str, Any], requested: str = "auto") -> str:
    if requested != "auto":
        return requested
    return runtime.get("active_backend") or "none"


def benchmark_local_model(model: str, role: str = "json_normalizer", backend: str = "auto", timeout: int = 90) -> dict[str, Any]:
    backend = backend if backend != "auto" else os.environ.get("HIVE_LOCAL_BACKEND", "ollama")
    if backend == "ollama":
        return benchmark_ollama_model(model, role=role, timeout=timeout)
    return {
        "model": model,
        "role": role,
        "runtime": backend,
        "status": "skipped_backend_not_supported",
        "latency_ms": 0,
        "json_valid": False,
        "schema_valid": False,
        "parsed": {},
        "raw_response": "",
        "parse_error": "",
        "error": f"Local backend adapter '{backend}' is not implemented yet.",
    }


def benchmark_ollama_model(model: str, role: str = "json_normalizer", timeout: int = 90) -> dict[str, Any]:
    server_models = ollama_server_models()
    if server_models is not None and not local_model_available(model, set(server_models)):
        return {
            "model": model,
            "role": role,
            "runtime": "ollama",
            "status": "skipped_model_not_loaded",
            "latency_ms": 0,
            "json_valid": False,
            "schema_valid": False,
            "parsed": {},
            "error": (
                f"{model} is not loaded in the running Ollama adapter. "
                "Start an Ollama-compatible adapter or choose another HIVE_LOCAL_BACKEND."
            ),
        }
    suite = benchmark_suite(role)
    prompt = suite["prompt"]
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": "0s",
        "options": {"temperature": 0.0, "num_ctx": 2048, "num_predict": 80},
    }
    started = time.monotonic()
    try:
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
        raw = str(body.get("response") or "")
        parse_error = ""
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            parsed = {}
            parse_error = str(exc)
        json_valid = isinstance(parsed, dict) and parsed.get("ok") is True and "confidence" in parsed
        schema_valid = benchmark_schema_valid(parsed, suite)
        return {
            "model": model,
            "role": role,
            "runtime": "ollama",
            "status": "completed",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "json_valid": json_valid,
            "schema_valid": schema_valid,
            "parsed": parsed,
            "raw_response": raw[:2000],
            "parse_error": parse_error,
            "error": parse_error,
        }
    except Exception as exc:
        return {
            "model": model,
            "role": role,
            "runtime": "ollama",
            "status": "failed",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "json_valid": False,
            "schema_valid": False,
            "parsed": {},
            "raw_response": "",
            "parse_error": "",
            "error": str(exc),
        }


def benchmark_suite(role: str) -> dict[str, Any]:
    suites = {
        "classify": {
            "required": ["task_type", "project", "confidence"],
            "prompt": (
                "Return valid JSON only. Classify this snippet for Hive Mind.\n"
                "Snippet: `Fix provider result validation and add tests.`\n"
                'Shape: {"ok": true, "task_type": "implementation", "project": "Hive Mind", "confidence": 0.8}.'
            ),
        },
        "json_normalizer": {
            "required": ["normalized", "confidence"],
            "prompt": (
                "Return valid JSON only. Normalize rough input into strict JSON.\n"
                "Input: status ok; owner local; needs review false.\n"
                'Shape: {"ok": true, "normalized": {"status": "ok", "owner": "local", "needs_review": false}, "confidence": 0.8}.'
            ),
        },
        "memory_extraction": {
            "required": ["memory_drafts"],
            "prompt": (
                "Return valid JSON only. Extract reviewable memory drafts.\n"
                "Text: User decided Hive Mind owns orchestration while MemoryOS owns accepted memory.\n"
                'Shape: {"ok": true, "memory_drafts": [{"type": "decision", "content": "...", "origin": "user", "confidence": 0.8, "raw_refs": ["bench"]}], "needs_human_or_claude_review": false}.'
            ),
        },
        "capability_extraction": {
            "required": ["technology_card"],
            "prompt": (
                "Return valid JSON only. Extract a CapabilityOS technology card.\n"
                "Text: llm-checker recommends local models based on hardware and can calibrate policies.\n"
                'Shape: {"ok": true, "technology_card": {"name": "llm-checker", "category": "local-model-eval", "capabilities": ["recommend"], "risks": [], "confidence": 0.8}}.'
            ),
        },
        "log_summary": {
            "required": ["changed", "verification"],
            "prompt": (
                "Return valid JSON only. Summarize this log.\n"
                "Log: npm test passed 20 tests. qwen3:1.7b failed strict JSON with raw response {}.\n"
                'Shape: {"ok": true, "changed": ["..."], "verification": ["..."], "unresolved": []}.'
            ),
        },
        "diff_review": {
            "required": ["risk_summary", "findings", "confidence"],
            "prompt": (
                "Return valid JSON only. Review this diff summary.\n"
                "Diff: added shell script that may pull models and start Docker if requested.\n"
                'Shape: {"ok": true, "risk_summary": "low", "findings": [], "missing_tests": [], "confidence": 0.8}.'
            ),
        },
        "handoff": {
            "required": ["handoff"],
            "prompt": (
                "Return valid JSON only. Draft an implementation handoff.\n"
                "Task: Add role-specific local benchmark suites.\n"
                'Shape: {"ok": true, "handoff": {"objective": "...", "steps": ["..."], "acceptance_criteria": ["..."], "risks": []}}.'
            ),
        },
        "architecture": {
            "required": ["architecture", "risks"],
            "prompt": (
                "Return valid JSON only. Draft local architecture notes.\n"
                "Topic: Hive Mind routes local models by role and escalates to Claude/Codex.\n"
                'Shape: {"ok": true, "architecture": {"components": ["router", "benchmark", "policy"]}, "risks": [], "confidence": 0.8}.'
            ),
        },
    }
    return suites.get(role, suites["json_normalizer"])


def benchmark_schema_valid(parsed: dict[str, Any], suite: dict[str, Any]) -> bool:
    if not isinstance(parsed, dict):
        return False
    if parsed.get("ok") is not True:
        return False
    for key in suite.get("required", []):
        if key not in parsed:
            return False
    return True


def ollama_server_models() -> list[str] | None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
        return [item.get("name", "") for item in body.get("models", []) if item.get("name")]
    except Exception:
        return None


def local_model_available(model: str, present: set[str]) -> bool:
    if model in present:
        return True
    if ":" not in model and f"{model}:latest" in present:
        return True
    if model.endswith(":latest") and model.removesuffix(":latest") in present:
        return True
    return False


def format_local_benchmark(report: dict[str, Any]) -> str:
    lines = [
        "Hive Mind Local Benchmark",
        "",
        f"Runtime: {report.get('runtime')} server={report.get('server')}",
        f"Status: {report.get('status')}",
        f"JSON validity: {report.get('json_validity')}",
        "",
        "Results:",
    ]
    for item in report.get("results") or []:
        marker = "✓" if item.get("schema_valid") else "!"
        lines.append(
            f"{marker} {item.get('model')} [{item.get('role')}]: {item.get('status')} "
            f"latency_ms={item.get('latency_ms')} schema_valid={item.get('schema_valid')}"
        )
        if item.get("error"):
            lines.append(f"  error: {item.get('error')}")
    lines.extend(["", f"Thread: {report.get('working_method')}"])
    return "\n".join(lines)


def build_context_pack_for_role(root: Path, role: str, run_id: str | None = None) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    context_dir = paths.run_dir / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    registry = agent_role_registry().get(role, {})
    policy = (load_policy(root).get("roles") or {}).get(role, {})
    task = safe_load_yaml(paths.task)
    pack = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "agent_role": role,
        "context_pack": {
            "objective": state.get("user_request"),
            "project_state": {
                "project": state.get("project"),
                "phase": state.get("phase"),
                "status": state.get("status"),
            },
            "active_decisions": [
                "Hive Mind owns orchestration, provider adapters, prompt/log runtime, and run artifacts.",
                "MemoryOS owns accepted memory graph and review/approval.",
                "CapabilityOS owns capability/workflow recommendations.",
            ],
            "constraints": task.get("constraints", []) if isinstance(task, dict) else [],
            "relevant_memories": [],
            "capability_recommendations": [],
            "open_questions": [],
            "risks": role_context_risks(role),
            "forbidden_scope": registry.get("forbidden_actions", []),
            "raw_refs": [
                paths.task.relative_to(root).as_posix(),
                paths.state.relative_to(root).as_posix(),
                "docs/hive_mind2.md",
                "docs/TODO.md",
            ],
            "output_contract": role_output_contract(role),
            "policy": policy,
            "working_method": WORKING_METHOD_PHRASE,
        },
    }
    safe_role = role.replace(".", "_").replace("/", "_")
    output_path = context_dir / f"{safe_role}_context_pack.yaml"
    output_path.write_text(format_simple_yaml(pack) + "\n", encoding="utf-8")
    append_event(paths, "context_edited", {"agent_role": role, "artifact": output_path.relative_to(root).as_posix()})
    append_hive_activity(paths, "hive/context", "built_context", f"Built context pack for {role}.", {"artifact": output_path.relative_to(root).as_posix()})
    return {
        "schema_version": 1,
        "run_id": paths.run_id,
        "role": role,
        "path": output_path.relative_to(root).as_posix(),
        "pack": pack,
    }


def role_context_risks(role: str) -> list[str]:
    if role.startswith("codex."):
        return ["unrelated_user_changes", "unsafe_shell", "missing_tests", "scope_creep"]
    if role.startswith("claude."):
        return ["unsupported_claims", "overbroad_plan", "memory_boundary_confusion"]
    if role.startswith("local."):
        return ["invalid_json", "low_confidence", "draft_misread_as_decision"]
    return ["ambiguous_role"]


def role_output_contract(role: str) -> dict[str, Any]:
    if role == "claude.planner":
        return {"artifact": "handoff.yaml", "must_include": ["objective", "constraints", "risks", "acceptance_criteria"]}
    if role == "codex.executor":
        return {"artifact": "executor_result.yaml", "must_include": ["files_changed", "commands_run", "tests_run", "risk_level"]}
    if role.startswith("local."):
        return {"artifact": "worker_json", "must_include": ["confidence", "should_escalate", "escalation_reason"]}
    return {"artifact": "role_result", "must_include": ["status", "evidence", "next"]}


def safe_load_yaml(path: Path) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def run_audit_report(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    validation = validate_run_artifacts(paths.run_dir, root)
    board = run_board(root, paths.run_id)
    artifacts = board.get("artifacts") or []
    stale = [item for item in artifacts if item.get("freshness") in {"stale", "missing", "empty"}]
    provider_results = collect_provider_results(root, paths.run_dir, show_paths=True)
    failures = [item for item in provider_results if item.get("status") == "failed"]
    policy = policy_report(root, write=False)
    recommendations = []
    if validation.get("verdict") != "pass":
        recommendations.append("run verification needs review")
    if stale:
        recommendations.append("refresh stale/missing/empty artifacts")
    if failures:
        recommendations.append("inspect failed provider results")
    if policy.get("status") != "ready":
        recommendations.append("run hive policy check --write")
    if not recommendations:
        recommendations.append("run is audit-clean; continue with next action or summary")
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "status": (
            "ready"
            if validation.get("verdict") == "pass" and not failures and not stale and policy.get("status") == "ready"
            else "needs_review"
        ),
        "validation": validation,
        "stale_artifacts": stale,
        "provider_results": provider_results,
        "provider_failures": failures,
        "policy": {"status": policy.get("status"), "path": policy.get("path"), "issues": policy.get("issues", [])},
        "recommendations": recommendations,
        "working_method": WORKING_METHOD_PHRASE,
    }


def demo_live_run(root: Path, task: str = "Watch Hive Mind agents coordinate", run_id: str | None = None, delay: float = 0.45) -> dict[str, Any]:
    """Create or animate a safe demo run so live/inspect surfaces show agents moving.

    This intentionally does not execute external provider CLIs or local LLM
    backends. It writes normal Hive artifacts with short delays so the board,
    events, agents, artifacts, transcript, society, and memory views can prove
    that the internal blackboard is alive.
    """
    delay = max(0.0, min(float(delay), 5.0))
    paths = create_run(root, task, project="Hive Mind", task_type="demo") if run_id is None else load_run(root, run_id)[0]
    paths, state = load_run(root, paths.run_id)
    append_event(paths, "demo_started", {"task": state.get("user_request"), "delay": delay})
    append_hive_activity(paths, "hive-mind", "demo_started", "Live coordination demo started", {"delay": delay})
    update_state(paths, phase="route", status="demo_running", latest_event="Demo started.")
    _demo_pause(delay)

    routing_plan = {
        "schema_version": 1,
        "intent": "implementation",
        "route_source": "demo",
        "confidence": 0.99,
        "should_escalate": False,
        "actions": [
            {"provider": "local", "role": "context", "reason": "compress run context"},
            {"provider": "claude", "role": "planner", "reason": "prepare plan prompt"},
            {"provider": "codex", "role": "executor", "reason": "prepare execution handoff"},
            {"provider": "gemini", "role": "reviewer", "reason": "prepare independent review"},
        ],
    }
    routing_path = paths.run_dir / "routing_plan.json"
    write_json(routing_path, routing_plan)
    add_state_artifact(paths, "routing_plan", routing_path)
    append_event(paths, "routing_plan_created", {"artifact": routing_path.relative_to(root).as_posix(), "source": "demo"})
    ensure_capabilityos_recommendation(root, paths.run_id)
    paths, state = load_run(root, paths.run_id)
    append_hive_activity(paths, "hive-mind", "route", "Demo route assigned local, Claude, Codex, Gemini, and verifier roles")
    update_state(paths, phase="route", status="ready", latest_event="Demo route ready.")
    _demo_pause(delay)

    society_path = paths.run_dir / "society_plan.json"
    society = build_society_plan_from_routing(root, paths, state, routing_plan, execute=False)
    write_json(society_path, society)
    add_state_artifact(paths, "society_plan", society_path)
    append_event(paths, "society_plan_created", {"artifact": society_path.relative_to(root).as_posix(), "members": len(society.get("members") or [])})
    append_hive_activity(paths, "hive-mind", "society", "Demo society plan created; watch agent rows change status")
    _demo_pause(delay)

    _demo_local_context(root, paths, delay)
    _demo_prepare_external(root, paths, "claude", "planner", delay)
    _demo_prepare_external(root, paths, "codex", "executor", delay)
    _demo_prepare_external(root, paths, "gemini", "reviewer", delay)
    _demo_local_summary(root, paths, delay)

    set_agent_status(paths, "verifier", "running")
    append_event(paths, "agent_started", {"agent": "verifier", "role": "run"})
    append_hive_activity(paths, "verifier", "running", "Verifier checks the demo run artifacts")
    _demo_pause(delay)
    verification_path = build_verification(root, paths.run_id)

    memory_path = build_memory_draft(root, paths.run_id)
    summary_path = build_summary(root, paths.run_id)
    update_state(paths, phase="close", status="demo_complete", latest_event="Demo complete.")
    append_event(paths, "demo_completed", {"verification": verification_path.relative_to(root).as_posix()})
    append_hive_activity(paths, "hive-mind", "demo_completed", "Live coordination demo completed", {"run_id": paths.run_id})

    return {
        "schema_version": 1,
        "run_id": paths.run_id,
        "status": "demo_complete",
        "delay": delay,
        "artifacts": {
            "routing_plan": routing_path.relative_to(root).as_posix(),
            "society_plan": society_path.relative_to(root).as_posix(),
            "verification": verification_path.relative_to(root).as_posix(),
            "memory_drafts": memory_path.relative_to(root).as_posix(),
            "final_report": summary_path.relative_to(root).as_posix(),
        },
        "next": {
            "command": f"hive live --run-id {paths.run_id}",
            "reason": "open the completed demo run in the Hive prompt/log surface",
        },
    }


def _demo_pause(delay: float) -> None:
    if delay > 0:
        time.sleep(delay)


def _demo_local_context(root: Path, paths: RunPaths, delay: float) -> None:
    role = "context"
    agent_name = local_agent_name(role)
    set_agent_status(paths, agent_name, "running")
    append_event(paths, "agent_started", {"agent": "local", "role": role, "worker": "context_compressor"})
    append_hive_activity(paths, "local/context", "running", "Local context worker compresses project/run context")
    _demo_pause(delay)
    out_path = paths.local_dir / "context.json"
    result = {
        "schema_version": 1,
        "agent": "local",
        "role": role,
        "status": "completed",
        "provider_mode": "demo_runtime",
        "runtime": "demo",
        "worker": "context_compressor",
        "model": "demo",
        "source_ref": paths.context_pack.relative_to(root).as_posix(),
        "artifacts_created": [out_path.relative_to(root).as_posix()],
        "output_valid": True,
        "output_issues": [],
        "confidence": 0.92,
        "should_escalate": False,
        "escalation_reason": "",
        "output": {
            "summary": "Demo context pack prepared for Claude/Codex/Gemini coordination.",
            "key_files": ["hivemind/live.py", "hivemind/harness.py", "hivemind/plan_dag.py"],
        },
    }
    write_json(out_path, result)
    add_state_artifact(paths, "local_context", out_path)
    set_agent_status(paths, agent_name, "completed")
    append_event(paths, "agent_completed", {"agent": "local", "role": role, "worker": "context_compressor", "artifact": out_path.relative_to(root).as_posix()})
    append_hive_activity(paths, "local/context", "completed", "Local context artifact ready", {"artifact": out_path.relative_to(root).as_posix()})
    update_state(paths, phase="context", status="in_progress", latest_event="Local context completed.")
    _demo_pause(delay)


def _demo_prepare_external(root: Path, paths: RunPaths, agent: str, role: str, delay: float) -> None:
    agent_name = f"{agent}-{role}"
    set_agent_status(paths, agent_name, "running")
    append_event(paths, "agent_started", {"agent": agent, "role": role, "mode": "demo_prepare"})
    append_hive_activity(paths, f"{agent}/{role}", "running", f"{agent}/{role} prepares a provider prompt artifact")
    update_state(paths, phase="handoff", status="in_progress", latest_event=f"{agent}/{role} running.")
    _demo_pause(delay)
    result_path = invoke_external_agent(root, agent, role, run_id=paths.run_id, execute=False)
    append_hive_activity(paths, f"{agent}/{role}", "prepared", f"{agent}/{role} prepared prompt/result artifacts", {"artifact": result_path.relative_to(root).as_posix()})
    _demo_pause(delay)


def _demo_local_summary(root: Path, paths: RunPaths, delay: float) -> None:
    role = "summarize"
    agent_name = local_agent_name(role)
    set_agent_status(paths, agent_name, "running")
    append_event(paths, "agent_started", {"agent": "local", "role": role, "worker": "log_summarizer"})
    append_hive_activity(paths, "local/summarize", "running", "Local summarizer watches the shared activity log")
    _demo_pause(delay)
    out_path = paths.local_dir / "summarize.json"
    result = {
        "schema_version": 1,
        "agent": "local",
        "role": role,
        "status": "completed",
        "provider_mode": "demo_runtime",
        "runtime": "demo",
        "worker": "log_summarizer",
        "model": "demo",
        "source_ref": paths.events.relative_to(root).as_posix(),
        "artifacts_created": [out_path.relative_to(root).as_posix()],
        "output_valid": True,
        "output_issues": [],
        "confidence": 0.88,
        "should_escalate": False,
        "escalation_reason": "",
        "output": {"summary": "Demo run shows local, Claude, Codex, Gemini, and verifier coordination."},
    }
    write_json(out_path, result)
    add_state_artifact(paths, "local_summary", out_path)
    set_agent_status(paths, agent_name, "completed")
    append_event(paths, "agent_completed", {"agent": "local", "role": role, "worker": "log_summarizer", "artifact": out_path.relative_to(root).as_posix()})
    append_hive_activity(paths, "local/summarize", "completed", "Local summary artifact ready", {"artifact": out_path.relative_to(root).as_posix()})
    update_state(paths, phase="verify", status="in_progress", latest_event="Local summary completed.")
    _demo_pause(delay)


def format_demo_report(report: dict[str, Any]) -> str:
    lines = [
        f"Hive Mind live demo: {report.get('run_id')}",
        f"Status: {report.get('status')}",
        "",
        "Artifacts:",
    ]
    for name, path in (report.get("artifacts") or {}).items():
        lines.append(f"- {name}: {path}")
    next_action = report.get("next") or {}
    lines.extend(["", "Next:", f"  {next_action.get('command')}", f"  Reason: {next_action.get('reason')}"])
    return "\n".join(lines)


def auto_loop(
    root: Path,
    run_id: str | None = None,
    max_steps: int = 1,
    execute: bool = False,
    allowed_actions: list[str] | None = None,
    goal: str | None = None,
) -> dict[str, Any]:
    """Plan, and optionally run, a bounded loop over safe Hive internal actions.

    Self-judgment: after each executed step, evaluate progress toward `goal`
    using verification verdict + artifact coverage. Stops early if the run
    is judged complete (verdict=pass, no required artifacts missing).
    """
    if max_steps < 1:
        raise ValueError("max_steps must be >= 1")
    max_steps = min(max_steps, 10)
    allowed = set(allowed_actions or [])
    unknown = sorted(allowed - AUTO_LOOP_ALLOWED_ACTIONS)
    if unknown:
        raise ValueError(f"unknown auto-loop actions: {', '.join(unknown)}")

    paths, _ = load_run(root, run_id)
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "goal": goal or "complete all pending required actions",
        "mode": "execute" if execute else "dry_run",
        "execute_requested": execute,
        "max_steps": max_steps,
        "allowed_actions": sorted(allowed),
        "risk_level": "medium" if execute else "low",
        "policy": {
            "default": "dry_run",
            "provider_cli_execution": "blocked",
            "arbitrary_shell_execution": "blocked",
            "memory_commit": "blocked",
            "memory_draft": "allowlisted",
        },
        "self_judgments": [],
        "proposed_steps": [],
        "executed_steps": [],
        "blocked_steps": [],
    }

    for index in range(max_steps):
        board = run_board(root, paths.run_id)
        next_action = board.get("next") or {}

        # Self-judgment before each step: evaluate if goal is already met
        judgment = auto_loop_self_judge(root, paths, board, goal, index)
        report["self_judgments"].append(judgment)
        if judgment["goal_met"]:
            report["early_stop_reason"] = judgment["reason"]
            break

        decision = classify_auto_loop_action(str(next_action.get("command") or ""), str(next_action.get("reason") or ""))
        step = {
            "step": index + 1,
            "command": next_action.get("command"),
            "reason": next_action.get("reason"),
            "action": decision["action"],
            "risk_level": decision["risk_level"],
            "auto_executable": decision["auto_executable"],
        }
        report["proposed_steps"].append(step)

        if not execute:
            report["blocked_steps"].append({**step, "block_reason": "dry_run_requires_--execute"})
            break
        if not decision["auto_executable"]:
            report["blocked_steps"].append({**step, "block_reason": decision["block_reason"]})
            break
        if decision["action"] not in allowed:
            report["blocked_steps"].append({**step, "block_reason": "action_not_allowlisted"})
            break

        result = execute_auto_loop_action(root, paths.run_id, str(decision["action"]))
        report["executed_steps"].append({**step, **result})
        append_event(paths, "auto_loop_step_executed", {"action": decision["action"], "result": result})
        if result.get("result") == "failed" or result.get("status") == "failed":
            report["blocked_steps"].append({**step, **result, "block_reason": "executed_action_failed"})
            break

    # Final self-judgment
    final_judgment = auto_loop_self_judge(root, paths, run_board(root, paths.run_id), goal, max_steps)
    report["final_judgment"] = final_judgment

    report["status"] = "executed" if report["executed_steps"] else "planned"
    if report["blocked_steps"]:
        report["status"] = "blocked" if execute else "planned"
    if report.get("early_stop_reason"):
        report["status"] = "complete"
    report["verdict"] = "pass" if final_judgment["goal_met"] else ("needs_human" if not execute else "incomplete")

    out_path = paths.artifacts / "auto_loop_plan.json"
    report["artifact"] = out_path.relative_to(root).as_posix()
    write_json(out_path, report)
    add_state_artifact(paths, "auto_loop_plan", out_path)
    append_event(
        paths,
        "auto_loop_ready",
        {
            "artifact": out_path.relative_to(root).as_posix(),
            "mode": report["mode"],
            "status": report["status"],
            "executed_steps": len(report["executed_steps"]),
            "blocked_steps": len(report["blocked_steps"]),
        },
    )
    return report


def flow_advance(
    root: Path,
    task: str | None = None,
    run_id: str | None = None,
    complexity: str = "fast",
    execute_local: bool = False,
) -> dict[str, Any]:
    """Backward-compatible wrapper for the extracted flow runtime."""
    from .flow_runtime import flow_advance as run_flow_advance

    return run_flow_advance(root, task=task, run_id=run_id, complexity=complexity, execute_local=execute_local)


def sync_dag_with_run_state(root: Path, run_id: str, dag: Any) -> None:
    from .flow_runtime import sync_dag_with_run_state as sync

    sync(root, run_id, dag)


def execute_ready_local_steps(root: Path, dag: Any) -> list[dict[str, Any]]:
    from .flow_runtime import execute_ready_local_steps as execute

    return execute(root, dag)


def local_role_for_owner(owner_role: str) -> str | None:
    from .flow_runtime import local_role_for_owner as local_role

    return local_role(owner_role)


def external_role_for_owner(owner_role: str) -> tuple[str, str] | None:
    from .flow_runtime import external_role_for_owner as external_role

    return external_role(owner_role)


def build_society_plan_from_routing(
    root: Path,
    paths: RunPaths,
    state: dict[str, Any],
    plan: dict[str, Any],
    execute: bool = False,
) -> dict[str, Any]:
    from .flow_runtime import build_society_plan_from_routing as build_society

    return build_society(root, paths, state, plan, execute=execute)


def build_workflow_state(
    root: Path,
    run_id: str,
    actions_taken: list[dict[str, Any]] | None = None,
    execute_local: bool = False,
) -> dict[str, Any]:
    from .flow_runtime import build_workflow_state as build_state

    return build_state(root, run_id, actions_taken=actions_taken, execute_local=execute_local)


def workflow_member_state(root: Path, paths: RunPaths, action: dict[str, Any]) -> dict[str, Any]:
    from .flow_runtime import workflow_member_state as member_state

    return member_state(root, paths, action)


def workflow_group_status(members: list[dict[str, Any]]) -> str:
    from .flow_runtime import workflow_group_status as group_status

    return group_status(members)


def format_flow_report(report: dict[str, Any]) -> str:
    from .flow_runtime import format_flow_report as format_report

    return format_report(report)

def auto_loop_self_judge(
    root: Path,
    paths: "RunPaths",
    board: dict[str, Any],
    goal: str | None,
    iteration: int,
) -> dict[str, Any]:
    """Evaluate whether the loop goal is met. Heuristic — no LLM call."""
    pipeline = board.get("pipeline") or []
    artifacts = board.get("artifacts") or []
    done_steps = sum(1 for s in pipeline if s.get("status") == "done")
    total_steps = len(pipeline) or 1
    pipeline_pct = done_steps / total_steps
    required_missing = [a for a in artifacts if a.get("phase_class") == "required" and a.get("status") != "ok"]
    agents = board.get("agents") or []
    failed_agents = [a for a in agents if a.get("status") == "failed"]
    verification_verdict = "not_run"
    verification_path = paths.run_dir / "verification.yaml"
    if verification_path.exists():
        try:
            data = yaml.safe_load(verification_path.read_text(encoding="utf-8")) or {}
            verification_verdict = str(data.get("verdict", "unknown"))
        except yaml.YAMLError:
            verification_verdict = "invalid"
    goal_met = (
        verification_verdict == "pass"
        and not required_missing
        and not failed_agents
        and pipeline_pct >= 0.5
    )
    if goal_met:
        reason = f"Verification passed, {done_steps}/{total_steps} pipeline steps done, no required artifacts missing."
    elif failed_agents:
        reason = f"{len(failed_agents)} agent(s) failed: {', '.join(a.get('name', '?') for a in failed_agents[:3])}"
    elif required_missing:
        reason = f"{len(required_missing)} required artifact(s) missing: {', '.join(a.get('name', '?') for a in required_missing[:3])}"
    else:
        reason = f"Pipeline {done_steps}/{total_steps} steps done, verification={verification_verdict}."
    return {
        "iteration": iteration,
        "goal": goal or "complete all pending required actions",
        "goal_met": goal_met,
        "verification_verdict": verification_verdict,
        "pipeline_pct": round(pipeline_pct, 2),
        "required_missing": len(required_missing),
        "failed_agents": len(failed_agents),
        "reason": reason,
    }


def classify_auto_loop_action(command: str, reason: str) -> dict[str, Any]:
    command = command.strip()
    if command == "hive verify":
        return {"action": "verify", "auto_executable": True, "risk_level": "low", "block_reason": ""}
    if command == "hive memory draft":
        return {"action": "memory-draft", "auto_executable": True, "risk_level": "low", "block_reason": ""}
    if command == "hive summarize":
        return {"action": "summarize", "auto_executable": True, "risk_level": "low", "block_reason": ""}
    if command == "hive check run":
        return {"action": "check-run", "auto_executable": True, "risk_level": "low", "block_reason": ""}
    if command == "hive audit":
        return {"action": "audit", "auto_executable": True, "risk_level": "low", "block_reason": ""}
    if command == "hive diff":
        return {"action": "diff", "auto_executable": True, "risk_level": "low", "block_reason": ""}
    if command == "hive invoke local --role context":
        return {"action": "local-context", "auto_executable": True, "risk_level": "medium", "block_reason": ""}
    if command == "hive invoke local --role review":
        return {"action": "local-review", "auto_executable": True, "risk_level": "medium", "block_reason": ""}
    if command.startswith("hive invoke "):
        return {
            "action": "provider-invoke",
            "auto_executable": False,
            "risk_level": "high",
            "block_reason": "provider_cli_execution_blocked",
        }
    if command.startswith("hive ask ") or command.startswith("hive orchestrate "):
        return {
            "action": "route",
            "auto_executable": False,
            "risk_level": "medium",
            "block_reason": "new_routing_requires_operator_prompt_boundary",
        }
    return {
        "action": "unknown",
        "auto_executable": False,
        "risk_level": "medium",
        "block_reason": f"no_safe_executor_for_command: {command or reason}",
    }


def execute_auto_loop_action(root: Path, run_id: str, action: str) -> dict[str, Any]:
    if action == "verify":
        path = build_verification(root, run_id)
        return {"result": "created", "artifact": path.relative_to(root).as_posix()}
    if action == "memory-draft":
        path = build_memory_draft(root, run_id)
        return {"result": "created", "artifact": path.relative_to(root).as_posix()}
    if action == "summarize":
        path = build_summary(root, run_id)
        return {"result": "created", "artifact": path.relative_to(root).as_posix()}
    if action == "diff":
        git_diff_report(root, run_id)
        return {"result": "created", "artifact": (RunPaths(root, run_id).run_dir / "git_diff_report.json").relative_to(root).as_posix()}
    if action == "check-run":
        report = run_checks(root, run_id)
        return {"result": "checked", "status": report.get("status"), "failed": report.get("failed")}
    if action == "audit":
        report = run_audit_report(root, run_id)
        return {"result": "checked", "status": report.get("status"), "recommendations": report.get("recommendations", [])}
    if action == "local-context":
        path = invoke_local(root, "context", run_id=run_id)
        return local_action_result(root, path)
    if action == "local-review":
        path = invoke_local(root, "review", run_id=run_id)
        return local_action_result(root, path)
    raise ValueError(f"unsupported auto-loop action: {action}")


def local_action_result(root: Path, path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"result": "failed", "status": "failed", "artifact": path.relative_to(root).as_posix(), "error": str(exc)}
    status = str(data.get("status") or "unknown")
    if status != "completed":
        return {
            "result": "failed",
            "status": status,
            "artifact": path.relative_to(root).as_posix(),
            "error": data.get("error") or data.get("escalation_reason") or "local action did not complete",
        }
    return {
        "result": "created",
        "status": status,
        "artifact": path.relative_to(root).as_posix(),
        "should_escalate": bool(data.get("should_escalate")),
    }


def format_auto_loop_report(report: dict[str, Any]) -> str:
    lines = [
        f"Hive Mind Auto Loop: {report.get('run_id')}",
        f"Mode: {report.get('mode')} | Status: {report.get('status')} | Risk: {report.get('risk_level')}",
        f"Artifact: {report.get('artifact')}",
        "",
        "Policy:",
    ]
    policy = report.get("policy") or {}
    for key in ["default", "provider_cli_execution", "arbitrary_shell_execution", "memory_commit", "memory_draft"]:
        lines.append(f"  {key}: {policy.get(key)}")
    lines.append("")
    lines.append("Proposed:")
    for step in report.get("proposed_steps") or []:
        lines.append(f"  {step.get('step')}. {step.get('command')} [{step.get('action')}, {step.get('risk_level')}]")
        lines.append(f"     Reason: {step.get('reason')}")
    if report.get("executed_steps"):
        lines.append("")
        lines.append("Executed:")
        for step in report.get("executed_steps") or []:
            artifact = f" -> {step.get('artifact')}" if step.get("artifact") else ""
            lines.append(f"  {step.get('step')}. {step.get('action')} {step.get('result')}{artifact}")
    if report.get("blocked_steps"):
        lines.append("")
        lines.append("Blocked:")
        for step in report.get("blocked_steps") or []:
            lines.append(f"  {step.get('step')}. {step.get('action')}: {step.get('block_reason')}")
    return "\n".join(lines)


def close_gap_loop(root: Path, run_id: str | None = None) -> dict[str, Any]:
    """Build the artifacts needed to close the MemoryOS-side Hive Mind gaps."""
    paths, _ = load_run(root, run_id)
    memory_context = build_memory_context_artifact(root, paths.run_id)
    semantic_verification = build_semantic_verification_artifact(root, paths.run_id)
    handoff_quality = build_handoff_quality_artifact(root, paths.run_id)
    routing_evidence = build_routing_evidence_artifact(root, paths.run_id)
    conflict_set = build_conflict_set_artifact(root, paths.run_id)
    operator_decisions = build_operator_decisions_artifact(root, paths.run_id)
    report = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "source": "docs/HIVE_MIND_GAPS.md",
        "status": "ready",
        "artifacts": {
            "memory_context": memory_context["path"],
            "semantic_verification": semantic_verification["path"],
            "handoff_quality": handoff_quality["path"],
            "routing_evidence": routing_evidence["path"],
            "conflict_set": conflict_set["path"],
            "operator_decisions": operator_decisions["path"],
        },
        "next_actions": operator_decisions.get("decisions", []),
        "working_method": WORKING_METHOD_PHRASE,
    }
    gap_path = paths.artifacts / "gap_closure.json"
    write_json(gap_path, report)
    add_state_artifact(paths, "gap_closure", gap_path)
    append_hive_activity(paths, "hive-mind", "gap_closure_ready", "Built gap-closure artifacts from HIVE_MIND_GAPS.", {"artifact": gap_path.relative_to(root).as_posix()})
    update_state(paths, phase="gap_closure", status="ready")
    return report


def build_memory_context_artifact(root: Path, run_id: str | None = None) -> dict[str, Any]:
    report = ensure_memoryos_context(root, run_id, force=True)
    paths, _ = load_run(root, run_id)
    return {"path": report.get("artifact") or (paths.artifacts / "memory_context.json").relative_to(root).as_posix(), "artifact": report}


def ensure_memoryos_context(root: Path, run_id: str | None = None, force: bool = False) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    existing = state.get("memoryos_context")
    if (
        not force
        and isinstance(existing, dict)
        and existing.get("status") in {"available", "empty", "unavailable", "failed"}
        and (root / str(existing.get("artifact", ""))).exists()
    ):
        return dict(existing)
    report = run_memoryos_context_build(root, paths, state)
    update_state(
        paths,
        memoryos_context=report,
        accepted_memories_used=report.get("accepted_memory_ids", []),
    )
    append_event(
        paths,
        "memoryos_context_retrieved",
        {
            "artifact": report.get("artifact"),
            "status": report.get("status"),
            "trace_id": report.get("trace_id"),
            "accepted_memory_ids": report.get("accepted_memory_ids", []),
            "context_items": report.get("context_items", 0),
        },
    )
    append_hive_activity(
        paths,
        "memoryos",
        "context_retrieved",
        f"MemoryOS context {report.get('status')}; selected={len(report.get('accepted_memory_ids') or [])}; trace={report.get('trace_id') or 'none'}",
        {
            "artifact": report.get("artifact"),
            "trace_id": report.get("trace_id"),
            "accepted_memory_ids": report.get("accepted_memory_ids", []),
            "context_items": report.get("context_items", 0),
        },
    )
    return report


def run_memoryos_context_build(root: Path, paths: RunPaths, state: dict[str, Any]) -> dict[str, Any]:
    return _persist_memoryos_context_report(root, paths, build_memoryos_context_report(root, paths, state))


def _persist_memoryos_context_report(root: Path, paths: RunPaths, artifact: dict[str, Any]) -> dict[str, Any]:
    path = paths.artifacts / "memory_context.json"
    receipt_path = paths.artifacts / "memory_context_receipt.json"
    write_json(path, artifact)
    add_state_artifact(paths, "memory_context", path)
    artifact["artifact"] = path.relative_to(root).as_posix()
    artifact["receipt_artifact"] = receipt_path.relative_to(root).as_posix()
    write_json(path, artifact)
    write_json(receipt_path, artifact)
    add_state_artifact(paths, "memory_context_receipt", receipt_path)
    return artifact


def ensure_capabilityos_recommendation(root: Path, run_id: str | None = None, force: bool = False) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    existing = state.get("capability_bridge")
    if (
        not force
        and isinstance(existing, dict)
        and existing.get("bridge_status") in {"ok", "unavailable", "failed"}
        and (root / str(existing.get("artifact", ""))).exists()
    ):
        return dict(existing)
    report = run_capabilityos_recommendation(root, paths, state)
    recommendation = report.get("recommendation") if report.get("bridge_status") == "ok" else None
    update_state(
        paths,
        capability_bridge=report,
        capability_recommendation=recommendation,
    )
    append_event(
        paths,
        "capability_recommendation_retrieved",
        {
            "artifact": report.get("artifact"),
            "bridge_status": report.get("bridge_status"),
            "status": report.get("status"),
            "recommended_capability": (recommendation or {}).get("recommended_capability") if isinstance(recommendation, dict) else None,
            "score": (recommendation or {}).get("score") if isinstance(recommendation, dict) else None,
        },
    )
    append_hive_activity(
        paths,
        "capabilityos",
        "recommendation_retrieved",
        f"CapabilityOS bridge {report.get('bridge_status')}; recommendation={(recommendation or {}).get('recommended_capability') if isinstance(recommendation, dict) else 'none'}",
        {
            "artifact": report.get("artifact"),
            "bridge_status": report.get("bridge_status"),
            "status": report.get("status"),
            "recommended_capability": (recommendation or {}).get("recommended_capability") if isinstance(recommendation, dict) else None,
        },
    )
    return report


def run_capabilityos_recommendation(root: Path, paths: RunPaths, state: dict[str, Any]) -> dict[str, Any]:
    return _persist_capabilityos_recommendation_report(root, paths, build_capabilityos_recommendation_report(root, paths, state))


def _persist_capabilityos_recommendation_report(root: Path, paths: RunPaths, artifact: dict[str, Any]) -> dict[str, Any]:
    path = paths.artifacts / "capability_recommendation.json"
    write_json(path, artifact)
    add_state_artifact(paths, "capability_recommendation", path)
    artifact["artifact"] = path.relative_to(root).as_posix()
    write_json(path, artifact)
    return artifact


def build_semantic_verification_artifact(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    handoff = safe_load_yaml(paths.handoff)
    acceptance = handoff.get("acceptance_criteria") if isinstance(handoff, dict) else []
    changed_files = git_changed_files(root)
    checks = [
        {"id": "objective_present", "status": "pass" if state.get("user_request") else "fail", "evidence": state.get("user_request", "")},
        {"id": "acceptance_criteria_present", "status": "pass" if acceptance else "warn", "evidence": acceptance or []},
        {"id": "changed_files_recorded", "status": "pass" if changed_files else "manual", "evidence": changed_files},
        {"id": "provider_results_present", "status": "pass" if provider_result_paths(paths.run_dir) else "warn", "evidence": [p.relative_to(root).as_posix() for p in provider_result_paths(paths.run_dir)]},
    ]
    status = "pass" if all(item["status"] == "pass" for item in checks[:2]) else "needs_review"
    artifact = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "gap": "semantic_verification",
        "status": status,
        "checks": checks,
        "claim": "Artifact checks are necessary but not sufficient; this file records objective/scope/acceptance evidence for review.",
        "raw_refs": ["docs/HIVE_MIND_GAPS.md", paths.task.relative_to(root).as_posix(), paths.handoff.relative_to(root).as_posix()],
    }
    path = paths.artifacts / "semantic_verification.json"
    write_json(path, artifact)
    add_state_artifact(paths, "semantic_verification", path)
    append_event(paths, "semantic_verification_created", {"artifact": path.relative_to(root).as_posix(), "status": status})
    return {"path": path.relative_to(root).as_posix(), "artifact": artifact}


def build_handoff_quality_artifact(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, _ = load_run(root, run_id)
    handoff = safe_load_yaml(paths.handoff)
    required = {
        "objective": handoff.get("objective") if isinstance(handoff, dict) else None,
        "constraints": handoff.get("constraints") if isinstance(handoff, dict) else None,
        "acceptance_criteria": handoff.get("acceptance_criteria") if isinstance(handoff, dict) else None,
        "risks": handoff.get("risks") if isinstance(handoff, dict) else None,
        "files_or_domains": handoff.get("files_or_domains") or handoff.get("files") if isinstance(handoff, dict) else None,
        "suggested_commands": handoff.get("suggested_commands") if isinstance(handoff, dict) else None,
        "suggested_tests": handoff.get("suggested_tests") if isinstance(handoff, dict) else None,
    }
    checks = [
        {"field": field, "status": "pass" if value else "warn", "value": value or []}
        for field, value in required.items()
    ]
    status = "pass" if all(item["status"] == "pass" for item in checks[:3]) else "needs_review"
    artifact = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "gap": "handoff_quality_gate",
        "status": status,
        "checks": checks,
        "required_for_strong_handoff": list(required),
        "raw_refs": ["docs/HIVE_MIND_GAPS.md", paths.handoff.relative_to(root).as_posix()],
    }
    path = paths.artifacts / "handoff_quality.json"
    write_json(path, artifact)
    add_state_artifact(paths, "handoff_quality", path)
    append_event(paths, "handoff_quality_created", {"artifact": path.relative_to(root).as_posix(), "status": status})
    return {"path": path.relative_to(root).as_posix(), "artifact": artifact}


def build_routing_evidence_artifact(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    plan_path = paths.run_dir / "routing_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {"actions": []}
    providers = detect_agents(root, write=True).get("providers") or {}
    local_profile = local_model_profile(root, write=False)
    evidence = []
    for action in plan.get("actions") or []:
        provider = action.get("provider")
        role = action.get("role")
        provider_info = providers.get(provider, {}) if provider != "local" else {"status": "available", "mode": "local_runtime"}
        evidence.append(
            {
                "provider": provider,
                "role": role,
                "reason": action.get("reason", ""),
                "task_type": state.get("task_type"),
                "provider_status": provider_info.get("status"),
                "provider_mode": provider_info.get("mode"),
                "risk": "medium" if role in {"executor", "reviewer", "debate_review"} else "low",
                "local_profile_ref": ".hivemind/local_model_profile.json" if provider == "local" else "",
            }
        )
    artifact = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "gap": "routing_evidence",
        "status": "pass" if evidence else "needs_routing",
        "route_source": plan.get("route_source", "missing"),
        "local_profile_status": local_profile.get("status"),
        "assignments": evidence,
        "raw_refs": ["docs/HIVE_MIND_GAPS.md", plan_path.relative_to(root).as_posix() if plan_path.exists() else paths.task.relative_to(root).as_posix()],
    }
    path = paths.artifacts / "routing_evidence.json"
    write_json(path, artifact)
    add_state_artifact(paths, "routing_evidence", path)
    append_event(paths, "routing_evidence_created", {"artifact": path.relative_to(root).as_posix(), "assignments": len(evidence)})
    return {"path": path.relative_to(root).as_posix(), "artifact": artifact}


def build_conflict_set_artifact(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, _ = load_run(root, run_id)
    results = []
    for result_path in provider_result_paths(paths.run_dir):
        data = safe_load_yaml(result_path)
        output_path = data.get("output_path") if isinstance(data, dict) else ""
        preview = ""
        if output_path and (root / output_path).exists():
            preview = (root / output_path).read_text(encoding="utf-8", errors="replace").strip()[:800]
        results.append(
            {
                "agent": data.get("agent"),
                "role": data.get("role"),
                "status": data.get("status"),
                "risk_level": data.get("risk_level", "unknown"),
                "result_path": result_path.relative_to(root).as_posix(),
                "output_preview": preview,
            }
        )
    status_groups: dict[str, list[str]] = {}
    for item in results:
        status_groups.setdefault(str(item.get("status")), []).append(str(item.get("agent")))
    conflicts = []
    if len(status_groups) > 1:
        conflicts.append({"type": "status_disagreement", "groups": status_groups})
    high_risk = [item for item in results if item.get("risk_level") == "high"]
    if high_risk:
        conflicts.append({"type": "high_risk_provider_result", "items": high_risk})
    artifact = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "gap": "cross_agent_conflict",
        "status": "needs_review" if conflicts else "clear",
        "results": results,
        "conflicts": conflicts,
        "reviewer_assignment": "claude.reviewer" if conflicts else "",
        "resolution_states": ["accepted", "rejected", "superseded", "needs_more_evidence"],
        "raw_refs": ["docs/HIVE_MIND_GAPS.md"],
    }
    path = paths.artifacts / "conflict_set.json"
    write_json(path, artifact)
    add_state_artifact(paths, "conflict_set", path)
    append_event(paths, "conflict_set_created", {"artifact": path.relative_to(root).as_posix(), "conflicts": len(conflicts)})
    return {"path": path.relative_to(root).as_posix(), "artifact": artifact}


def build_operator_decisions_artifact(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    board = run_board(root, paths.run_id)
    artifacts = state.get("artifacts") or {}
    decisions = []
    for name in ["memory_context", "semantic_verification", "handoff_quality", "routing_evidence", "conflict_set"]:
        rel = artifacts.get(name)
        if not rel:
            decisions.append({"priority": "P0", "command": f"hive gaps --run-id {paths.run_id}", "reason": f"{name} artifact is missing"})
    conflict_path = artifacts.get("conflict_set")
    if conflict_path and (root / conflict_path).exists():
        conflict = json.loads((root / conflict_path).read_text(encoding="utf-8"))
        if conflict.get("status") == "needs_review":
            decisions.append({"priority": "P0", "command": f"hive invoke claude --role reviewer --run-id {paths.run_id}", "reason": "cross-agent conflict needs review"})
    next_action = board.get("next") or {}
    if next_action.get("command"):
        decisions.append({"priority": "P1", "command": next_action.get("command"), "reason": next_action.get("reason")})
    if not decisions:
        decisions.append({"priority": "P2", "command": f"hive summarize --run-id {paths.run_id}", "reason": "gap artifacts are present; summarize or continue"})
    artifact = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "gap": "operator_decision_surface",
        "status": "ready",
        "decisions": decisions,
        "chair": "Hive Mind",
        "raw_refs": ["docs/HIVE_MIND_GAPS.md", paths.state.relative_to(root).as_posix()],
    }
    path = paths.artifacts / "operator_decisions.json"
    write_json(path, artifact)
    add_state_artifact(paths, "operator_decisions", path)
    append_event(paths, "operator_decisions_created", {"artifact": path.relative_to(root).as_posix(), "decisions": len(decisions)})
    return {"path": path.relative_to(root).as_posix(), "artifact": artifact, "decisions": decisions}


def format_gap_closure_report(report: dict[str, Any]) -> str:
    lines = [
        f"Hive Mind Gap Closure: {report.get('run_id')}",
        f"Source: {report.get('source')}",
        f"Status: {report.get('status')}",
        "",
        "Artifacts:",
    ]
    for name, path in (report.get("artifacts") or {}).items():
        lines.append(f"- {name}: {path}")
    lines.extend(["", "Next Decisions:"])
    for item in report.get("next_actions") or []:
        lines.append(f"- [{item.get('priority')}] {item.get('command')} - {item.get('reason')}")
    lines.extend(["", f"Thread: {report.get('working_method')}"])
    return "\n".join(lines)


def format_run_audit(report: dict[str, Any]) -> str:
    lines = [f"Hive Mind Audit: {report.get('run_id')}", "", f"Status: {report.get('status')}"]
    validation = report.get("validation") or {}
    lines.append(f"Verification: {validation.get('verdict')}")
    lines.extend(["", "Stale / Missing Artifacts:"])
    stale = report.get("stale_artifacts") or []
    if stale:
        for item in stale:
            lines.append(f"! {item.get('name')} freshness={item.get('freshness')} producer={item.get('producer')}")
    else:
        lines.append("✓ none")
    lines.extend(["", "Provider Results:"])
    results = report.get("provider_results") or []
    if results:
        for item in results:
            lines.append(f"- {item.get('agent')}/{item.get('role')}: {item.get('status')} risk={item.get('risk_level')}")
    else:
        lines.append("○ none")
    lines.extend(["", "Recommendations:"])
    for item in report.get("recommendations") or []:
        lines.append(f"- {item}")
    lines.extend(["", f"Thread: {report.get('working_method')}"])
    return "\n".join(lines)


def inspect_run(root: "Path", run_id: str | None = None, *, verbose: bool = False) -> dict[str, Any]:
    """Deep audit of a run: ledger chain, step evaluations, disagreements, ProbeStep results, provider receipts.

    Returns a machine-readable dict. Use format_inspect_run() for operator output.
    """
    from .workloop import read_execution_ledger, replay_steps
    from .plan_dag import load_dag

    paths, state = load_run(root, run_id)
    run_id = paths.run_id

    # ── Ledger ────────────────────────────────────────────────────────────────
    ledger: list[dict[str, Any]] = []
    chain_ok = True
    try:
        ledger = read_execution_ledger(root, run_id)
        # basic hash chain check: each entry's prev_hash matches prior entry's hash
        for i, entry in enumerate(ledger):
            if i > 0 and entry.get("prev_hash") != ledger[i - 1].get("hash"):
                chain_ok = False
                break
    except Exception:
        chain_ok = False

    # ── DAG step evaluations ──────────────────────────────────────────────────
    step_evals: list[dict[str, Any]] = []
    evals_dir = paths.run_dir / "step_evaluations"
    if evals_dir.exists():
        for f in sorted(evals_dir.glob("*.json")):
            try:
                ev = json.loads(f.read_text(encoding="utf-8"))
                ev["_step_id"] = f.stem
                step_evals.append(ev)
            except Exception:
                pass

    # ── Disagreements ─────────────────────────────────────────────────────────
    disagreements: list[dict[str, Any]] = []
    dis_path = paths.run_dir / "disagreements.json"
    if dis_path.exists():
        try:
            disagreements = json.loads(dis_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    # ── ProbeStep results ─────────────────────────────────────────────────────
    probes: list[dict[str, Any]] = []
    probes_dir = paths.run_dir / "step_probes"
    if probes_dir.exists():
        for f in sorted(probes_dir.glob("*.json")):
            if "_override" in f.name:
                continue
            try:
                pr = json.loads(f.read_text(encoding="utf-8"))
                probes.append(pr)
            except Exception:
                pass

    # ── Provider receipts (agents/) ───────────────────────────────────────────
    receipts: list[dict[str, Any]] = []
    for result_path in provider_result_paths(paths.run_dir):
        data = safe_load_yaml(result_path)
        receipts.append({
            "path": result_path.relative_to(root).as_posix(),
            "provider": data.get("provider"),
            "role": data.get("role"),
            "status": data.get("status"),
            "risk_level": data.get("risk_level"),
            "artifacts": data.get("artifacts") or [],
            "commands_run": data.get("commands_run") or [],
            "tests_run": data.get("tests_run") or [],
            "policy_violations": data.get("policy_violations") or [],
        })

    # ── Protocol proofs (artifacts/decisions/) ────────────────────────────────
    proofs: list[dict[str, Any]] = []
    proofs_dir = paths.run_dir / "artifacts" / "proofs"
    if proofs_dir.exists():
        for f in sorted(proofs_dir.glob("*.json")):
            try:
                proofs.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                pass

    # ── DAG summary ───────────────────────────────────────────────────────────
    dag = load_dag(root, run_id)
    dag_summary: dict[str, Any] = {}
    if dag:
        by_status: dict[str, list[str]] = {}
        for s in dag.steps:
            by_status.setdefault(s.status, []).append(s.step_id)
        dag_summary = {
            "step_count": len(dag.steps),
            "by_status": by_status,
            "runnable": [s.step_id for s in dag.steps if dag.runnable()[:1] == [s]],
        }

    # ── Synthesis ─────────────────────────────────────────────────────────────
    escalated = [e for e in step_evals if e.get("escalation_triggered")]
    probe_failures = [p for p in probes if not p.get("passed")]
    receipt_failures = [r for r in receipts if r.get("status") == "failed"]
    verdict = "clean"
    if not chain_ok:
        verdict = "chain_tampered"
    elif probe_failures or receipt_failures:
        verdict = "failures"
    elif escalated or disagreements:
        verdict = "escalated"

    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": run_id,
        "task": state.get("user_request"),
        "phase": state.get("current_phase"),
        "verdict": verdict,
        "ledger": {
            "entry_count": len(ledger),
            "chain_ok": chain_ok,
            "events": [e.get("event") for e in ledger] if verbose else [],
            "last_event": ledger[-1].get("event") if ledger else None,
        },
        "dag": dag_summary,
        "step_evaluations": step_evals if verbose else [
            {"step_id": e["_step_id"], "recommended_action": e.get("recommended_action"),
             "escalation_triggered": e.get("escalation_triggered"), "risk_level": e.get("risk_level")}
            for e in step_evals
        ],
        "disagreements": disagreements,
        "probes": probes if verbose else [
            {"step_id": p.get("step_id"), "passed": p.get("passed"), "criterion_type": p.get("criterion_type"),
             "next_action": p.get("next_action")}
            for p in probes
        ],
        "receipts": receipts,
        "proofs": proofs,
        "summary": {
            "ledger_entries": len(ledger),
            "step_evals": len(step_evals),
            "escalated_steps": len(escalated),
            "disagreement_records": len(disagreements),
            "probe_results": len(probes),
            "probe_failures": len(probe_failures),
            "provider_receipts": len(receipts),
            "receipt_failures": len(receipt_failures),
            "proofs": len(proofs),
        },
    }


def format_inspect_run(report: dict[str, Any]) -> str:
    """Human-readable operator output for hive inspect."""
    lines = [
        f"Hive Inspect: {report.get('run_id')}",
        f"Task:    {(report.get('task') or '')[:80]}",
        f"Phase:   {report.get('phase')}",
        f"Verdict: {report.get('verdict').upper()}",
        "",
    ]
    # Ledger
    ledger = report.get("ledger") or {}
    chain_sym = "✓" if ledger.get("chain_ok") else "✗"
    lines.append(f"Ledger  {chain_sym} {ledger.get('entry_count')} entries  last={ledger.get('last_event')}")

    # DAG
    dag = report.get("dag") or {}
    if dag:
        status_summary = "  ".join(f"{k}={len(v)}" for k, v in sorted((dag.get("by_status") or {}).items()))
        lines.append(f"DAG     {dag.get('step_count')} steps  {status_summary}")

    # Step evaluations
    evals = report.get("step_evaluations") or []
    lines.append(f"\nStep Evaluations ({len(evals)}):")
    if evals:
        for e in evals:
            esc = "⬆" if e.get("escalation_triggered") else " "
            lines.append(f"  {esc} {e.get('step_id') or e.get('_step_id'):22}  {e.get('recommended_action'):12}  risk={e.get('risk_level')}")
    else:
        lines.append("  ○ none")

    # Disagreements
    disags = report.get("disagreements") or []
    lines.append(f"\nDisagreements ({len(disags)}):")
    if disags:
        for d in disags:
            lines.append(f"  ⚡ {d.get('step_id'):22}  {d.get('topology_type'):10}  severity={d.get('severity')}  axes={d.get('axes')}")
    else:
        lines.append("  ○ none")

    # Probes
    probes = report.get("probes") or []
    lines.append(f"\nProbe Results ({len(probes)}):")
    if probes:
        for p in probes:
            sym = "✓" if p.get("passed") else "✗"
            lines.append(f"  {sym} {p.get('step_id'):22}  {p.get('criterion_type'):20}  next={p.get('next_action')}")
    else:
        lines.append("  ○ none")

    # Provider receipts
    receipts = report.get("receipts") or []
    lines.append(f"\nProvider Receipts ({len(receipts)}):")
    if receipts:
        for r in receipts:
            sym = "✓" if r.get("status") != "failed" else "✗"
            lines.append(f"  {sym} {r.get('provider')}/{r.get('role'):20}  {r.get('status')}  risk={r.get('risk_level')}")
    else:
        lines.append("  ○ none")

    # Summary
    s = report.get("summary") or {}
    lines.extend(["", "Summary:"])
    for k, v in s.items():
        if v:
            lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def workspace_layout_report(layout: str = "dev") -> dict[str, Any]:
    layouts = {
        "dev": [
            "hive board",
            "hive events --follow",
            "hive transcript",
            "hive diff",
        ],
        "dual": [
            "hive board",
            "hive agents view",
            "hive artifacts",
            "hive memory view",
            "hive society",
        ],
    }
    if layout not in layouts:
        raise ValueError("layout must be one of: dev, dual")
    return {
        "schema_version": 1,
        "layout": layout,
        "commands": layouts[layout],
        "tmux_hint": " | ".join(layouts[layout]),
        "working_method": WORKING_METHOD_PHRASE,
    }


def format_workspace_layout(report: dict[str, Any]) -> str:
    lines = [f"Hive Workspace Layout: {report.get('layout')}", ""]
    for index, command in enumerate(report.get("commands") or [], start=1):
        lines.append(f"{index}. {command}")
    lines.extend(["", f"Thread: {report.get('working_method')}"])
    return "\n".join(lines)


def permissions_report(root: Path) -> dict[str, Any]:
    project_dir = root / PROJECT_DIR
    policy_path = project_dir / POLICY_FILE
    checks_dir = project_dir / CHECKS_DIR
    providers = detect_agents(root, write=True).get("providers", {})
    risks = {
        name: item.get("risks", [])
        for name, item in providers.items()
        if item.get("risks")
    }
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "status": "ready" if policy_path.exists() else "needs_setup",
        "policy": {
            "path": policy_path.as_posix(),
            "exists": policy_path.exists(),
        },
        "checks_dir": {
            "path": checks_dir.as_posix(),
            "exists": checks_dir.exists(),
            "count": len(list(checks_dir.glob("*.md"))) if checks_dir.exists() else 0,
        },
        "provider_risks": risks,
        "warnings": [] if policy_path.exists() else ["project policy.yaml is missing"],
    }


def load_policy(root: Path) -> dict[str, Any]:
    policy_path = root / PROJECT_DIR / POLICY_FILE
    if not policy_path.exists():
        return yaml.safe_load(default_policy_yaml()) or {}
    loaded = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
    return loaded if isinstance(loaded, dict) else {}


def policy_report(root: Path, write: bool = False) -> dict[str, Any]:
    project_dir = root / PROJECT_DIR
    policy_path = project_dir / POLICY_FILE
    created = False
    if write and not policy_path.exists():
        project_dir.mkdir(parents=True, exist_ok=True)
        policy_path.write_text(default_policy_yaml(), encoding="utf-8")
        created = True
    skill_path = ensure_working_method_skill(root, write=write)
    policy = load_policy(root)
    issues = []
    if not policy_path.exists():
        issues.append("policy file is missing")
    if not isinstance(policy.get("roles"), dict):
        issues.append("policy.roles must be an object")
    if (policy.get("danger_modes") or {}).get("allowed") is not False:
        issues.append("danger_modes.allowed must stay false by default")
    for role in ["claude.planner", "codex.executor", "local.memory_extractor"]:
        if role not in (policy.get("roles") or {}):
            issues.append(f"missing required role policy: {role}")
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "status": "ready" if not issues else "needs_setup",
        "path": policy_path.as_posix(),
        "working_method_skill": skill_path.as_posix(),
        "working_method_skill_exists": skill_path.exists(),
        "created": created,
        "issues": issues,
        "policy": policy,
    }


def ensure_working_method_skill(root: Path, write: bool = False) -> Path:
    skill_path = root / PROJECT_DIR / "skills" / WORKING_METHOD_SKILL_DIR / "SKILL.md"
    if write and not skill_path.exists():
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text(default_working_method_skill(), encoding="utf-8")
    return skill_path


def explain_policy(root: Path, role: str) -> dict[str, Any]:
    report = policy_report(root, write=False)
    policy = report.get("policy") or {}
    role_policy = (policy.get("roles") or {}).get(role)
    role_meta = agent_role_registry().get(role)
    return {
        "schema_version": 1,
        "role": role,
        "found": bool(role_policy or role_meta),
        "policy_path": report.get("path"),
        "policy": role_policy or {},
        "role": role,
        "registry": role_meta or {},
        "danger_modes": policy.get("danger_modes") or {},
    }


def format_policy_report(report: dict[str, Any]) -> str:
    lines = ["Hive Mind Policy", "", f"Path: {report.get('path')}", f"Status: {report.get('status')}"]
    if report.get("created"):
        lines.append("Created default policy.")
    issues = report.get("issues") or []
    if issues:
        lines.extend(["", "Issues:"])
        for issue in issues:
            lines.append(f"! {issue}")
    else:
        lines.append("✓ policy gate ready")
    lines.extend(["", f"Hidden thread: {WORKING_METHOD_PHRASE}"])
    return "\n".join(lines)


def format_policy_explain(report: dict[str, Any]) -> str:
    lines = [f"Policy Explain: {report.get('role')}", "", f"Found: {report.get('found')}"]
    registry = report.get("registry") or {}
    policy = report.get("policy") or {}
    if registry:
        lines.append(f"Purpose: {registry.get('purpose')}")
        lines.append(f"Default mode: {registry.get('default_mode')}")
    if policy:
        lines.extend(["", "Allowed:"])
        for name, value in policy.items():
            if name == "description":
                continue
            lines.append(f"- {name}: {value}")
    danger = report.get("danger_modes") or {}
    lines.extend(["", f"Danger modes allowed: {danger.get('allowed')}"])
    return "\n".join(lines)


def agent_role_registry() -> dict[str, dict[str, Any]]:
    return {
        "user.director": {
            "provider": "human",
            "purpose": "Final direction, taste, acceptance, and boundary decisions.",
            "default_mode": "approve_or_redirect",
            "allowed_actions": ["set_goal", "accept", "reject", "change_boundary"],
            "forbidden_actions": ["silent_auto_acceptance"],
            "handoff_outputs": ["decision", "taste_signal", "boundary_update"],
        },
        "claude.planner": {
            "provider": "claude",
            "purpose": "Conceptual planning, critique, claim discipline, and unresolved-risk surfacing.",
            "default_mode": "plan",
            "allowed_actions": ["read_context", "write_handoff", "critique", "surface_risks"],
            "forbidden_actions": ["repo_write", "memory_commit", "danger_bypass"],
            "handoff_outputs": ["handoff.yaml", "planner_result.yaml"],
        },
        "codex.executor": {
            "provider": "codex",
            "purpose": "Repository-aware implementation, tests, and verification logs.",
            "default_mode": "workspace_write_with_policy",
            "allowed_actions": ["repo_read", "repo_write_with_approval", "run_tests", "write_provider_result"],
            "forbidden_actions": ["memory_commit", "raw_export_access", "destructive_git"],
            "handoff_outputs": ["executor_result.yaml", "diff_report", "verification"],
        },
        "gemini.reviewer": {
            "provider": "gemini",
            "purpose": "Alternate review, multimodal review, and second-opinion critique.",
            "default_mode": "read_only",
            "allowed_actions": ["read_context", "review_outputs", "challenge_plan"],
            "forbidden_actions": ["repo_write", "memory_commit", "danger_bypass"],
            "handoff_outputs": ["reviewer_result.yaml"],
        },
        "hive.verifier": {
            "provider": "code/local",
            "purpose": "Check run safety, schema validity, packaging health, provider execution boundaries, and test evidence.",
            "default_mode": "read_only_or_allowlisted_internal_actions",
            "allowed_actions": ["read_artifacts", "run_tests", "validate_schema", "check_policy", "write_verification"],
            "forbidden_actions": ["provider_cli_execute", "arbitrary_shell", "memory_commit", "final_acceptance"],
            "handoff_outputs": ["verification.yaml", "auto_loop_plan.json", "verifier_findings.md"],
        },
        "hive.product_evaluator": {
            "provider": "reviewer",
            "purpose": "Judge product value against direct-agent use and manual shared-folder coordination.",
            "default_mode": "read_only",
            "allowed_actions": ["inspect_cli_surface", "compare_workflows", "name_blockers", "rank_p0"],
            "forbidden_actions": ["repo_write", "provider_cli_execute", "memory_commit", "overclaim_release_status"],
            "handoff_outputs": ["product_evaluation.md", "p0_recommendations"],
        },
        "persona.actual_user": {
            "provider": "persona",
            "purpose": "Pressure-test Hive Mind from a demanding real operator's UX, Korean prompt, and trust perspective.",
            "default_mode": "read_only_temp_workspace_smoke",
            "allowed_actions": ["try_safe_cli", "report_friction", "report_trust_gap", "suggest_keep_using_threshold"],
            "forbidden_actions": ["repo_write", "provider_cli_execute", "memory_commit", "accept_product_claims"],
            "handoff_outputs": ["user_persona_report.md", "ux_blockers", "trust_threshold"],
        },
        "local.context": {
            "provider": "local",
            "purpose": "Cheap-first context compression and routing support.",
            "default_mode": "draft_only",
            "allowed_actions": ["compress_context", "classify", "draft_memory", "summarize_log"],
            "forbidden_actions": ["repo_write", "final_decision", "memory_commit"],
            "handoff_outputs": ["context_pack", "worker_json"],
        },
        "local.memory_extractor": {
            "provider": "local",
            "purpose": "Extract reviewable memory drafts without accepting them.",
            "default_mode": "draft_only",
            "allowed_actions": ["draft_memory", "attach_raw_refs"],
            "forbidden_actions": ["memory_commit", "repo_write", "final_decision"],
            "handoff_outputs": ["memory_drafts.json"],
        },
    }


def agent_roles_report() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "roles": agent_role_registry(),
        "working_method": WORKING_METHOD_PHRASE,
    }


def explain_agent_role(root: Path, role: str) -> dict[str, Any]:
    registry = agent_role_registry()
    policy = load_policy(root)
    return {
        "schema_version": 1,
        "role": role,
        "found": role in registry,
        "registry": registry.get(role, {}),
        "policy": (policy.get("roles") or {}).get(role, {}),
        "working_method": WORKING_METHOD_PHRASE,
    }


def format_agent_roles(report: dict[str, Any]) -> str:
    lines = ["Hive Mind Agent Roles", "", f"Thread: {report.get('working_method')}", ""]
    for role, item in sorted((report.get("roles") or {}).items()):
        lines.append(f"{role}: {item.get('purpose')} [{item.get('default_mode')}]")
    return "\n".join(lines)


def format_agent_explain(report: dict[str, Any]) -> str:
    item = report.get("registry") or {}
    policy = report.get("policy") or {}
    lines = [f"Agent Explain: {report.get('role')}", "", f"Found: {report.get('found')}"]
    if item:
        lines.append(f"Provider: {item.get('provider')}")
        lines.append(f"Purpose: {item.get('purpose')}")
        lines.append(f"Default mode: {item.get('default_mode')}")
        lines.extend(["Allowed actions:"])
        lines.extend(f"- {action}" for action in item.get("allowed_actions") or [])
        lines.extend(["Forbidden actions:"])
        lines.extend(f"- {action}" for action in item.get("forbidden_actions") or [])
    if policy:
        lines.extend(["", "Policy:"])
        for key, value in policy.items():
            lines.append(f"- {key}: {value}")
    lines.extend(["", f"Thread: {report.get('working_method')}"])
    return "\n".join(lines)


def memory_profile() -> dict[str, Any]:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return {"status": "unknown", "total_bytes": None, "available_bytes": None}
    values: dict[str, int] = {}
    for line in meminfo.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        parts = raw.strip().split()
        if parts and parts[0].isdigit():
            values[key] = int(parts[0]) * 1024
    return {
        "status": "available" if values.get("MemTotal") else "unknown",
        "total_bytes": values.get("MemTotal"),
        "available_bytes": values.get("MemAvailable"),
    }


def probe_gpus() -> list[dict[str, Any]]:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return []
    try:
        completed = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            text=True,
            capture_output=True,
            timeout=5,
        )
    except Exception:
        return []
    if completed.returncode != 0:
        return []
    gpus = []
    for index, line in enumerate(completed.stdout.splitlines()):
        parts = [part.strip() for part in line.split(",")]
        if not parts or not parts[0]:
            continue
        memory_mb = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
        gpus.append({"index": index, "name": parts[0], "memory_total_mb": memory_mb})
    return gpus


def probe_binary_version(command: str, args: list[str]) -> dict[str, Any]:
    path = shutil.which(command)
    if not path:
        return {"status": "unavailable", "command": command, "path": None, "version": ""}
    try:
        completed = subprocess.run([path, *args], text=True, capture_output=True, timeout=5)
    except Exception as exc:
        return {"status": "gated", "command": command, "path": path, "version": "", "reason": str(exc)}
    raw = (completed.stdout or completed.stderr).strip()
    if completed.returncode != 0:
        return {"status": "gated", "command": command, "path": path, "version": raw.splitlines()[0] if raw else ""}
    return {"status": "available", "command": command, "path": path, "version": raw.splitlines()[0] if raw else ""}


def probe_tcp_port(host: str, port: int) -> dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=0.2):
            status = "open"
    except OSError:
        status = "closed"
    return {"host": host, "port": port, "status": status}


def probe_network() -> dict[str, Any]:
    target = ("1.1.1.1", 53)
    try:
        with socket.create_connection(target, timeout=1.0):
            status = "reachable"
    except OSError:
        status = "unreachable"
    return {"status": status, "target": f"{target[0]}:{target[1]}"}


def provider_cli_paths(providers: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result = {}
    for name, item in (providers.get("providers") or {}).items():
        result[name] = {
            "status": item.get("status"),
            "command": item.get("command"),
            "path": item.get("path"),
            "version": item.get("version", ""),
        }
    return result


def format_doctor(report: dict[str, Any]) -> str:
    lines = ["Hive Mind Doctor", "", "Core:"]
    for name, check in report["checks"].items():
        icon = "✓" if check.get("status") == "ok" else "!"
        value = check.get("path") or check.get("run_id") or check.get("status")
        lines.append(f"{icon} {name}: {value}")
    lines.extend(["", "Agents / Providers:"])
    for name, provider in report["providers"].items():
        icon = "✓" if provider.get("status") in {"available", "configured"} else "○"
        detail = provider.get("version") or provider.get("path") or provider.get("reason", "")
        lines.append(f"{icon} {name}: {provider.get('status')} {detail}")
    lines.extend(["", f"Status: {report['status']}"])
    return "\n".join(lines)


def format_doctor_scope(report: dict[str, Any]) -> str:
    scope = report.get("scope")
    reports = report.get("reports") or {}
    lines = [f"Hive Mind Doctor [{scope}]", "", f"Status: {report.get('status')}"]
    if "providers" in reports:
        provider_report = reports["providers"]
        lines.extend(["", "Providers:"])
        for name, provider in provider_report.get("providers", {}).items():
            icon = "✓" if provider.get("status") in {"available", "configured"} else "○"
            detail = provider.get("version") or provider.get("path") or provider.get("reason", "")
            lines.append(f"{icon} {name}: {provider.get('status')} {detail}")
    if "hardware" in reports:
        hardware = reports["hardware"]
        disk = hardware.get("disk") or {}
        memory = hardware.get("memory") or {}
        lines.extend(
            [
                "",
                "Hardware:",
                f"System: {(hardware.get('system') or {}).get('platform')}",
                f"CPU logical: {(hardware.get('cpu') or {}).get('logical_count')}",
                f"RAM: {format_bytes(memory.get('available_bytes'))} available / {format_bytes(memory.get('total_bytes'))} total",
                f"Disk: {format_bytes(disk.get('free_bytes'))} free / {format_bytes(disk.get('total_bytes'))} total",
            ]
        )
        gpus = hardware.get("gpu") or []
        if gpus:
            for gpu in gpus:
                lines.append(f"GPU: {gpu.get('name')} {gpu.get('memory_total_mb') or '?'} MB")
        else:
            lines.append("GPU: none detected")
        lines.extend(["Runtime:"])
        for name, item in (hardware.get("runtime") or {}).items():
            detail = item.get("version") or item.get("path") or item.get("status")
            lines.append(f"  {name}: {item.get('status')} {detail}")
        lines.extend(["Ports:"])
        for name, item in (hardware.get("ports") or {}).items():
            lines.append(f"  {name}: {item.get('status')} {item.get('host')}:{item.get('port')}")
        if hardware.get("warnings"):
            lines.extend(["Warnings:"])
            for warning in hardware["warnings"]:
                lines.append(f"! {warning}")
    if "models" in reports:
        models = reports["models"]
        local_runtime = models.get("local_runtime") or {}
        backend = active_local_backend(local_runtime)
        lines.extend(
            [
                "",
                "Models:",
                f"Active backend: {local_runtime.get('active_backend')}",
                f"Backend status: {backend.get('status')} server={backend.get('server', 'n/a')}",
                f"Model source: {backend.get('model_source')}",
            ]
        )
        for model in backend.get("models") or []:
            lines.append(f"✓ {model}")
        if not backend.get("models"):
            lines.append("○ no local backend model manifests found")
        missing = local_runtime.get("missing_recommended_models") or []
        if missing:
            lines.append("Missing recommended:")
            for model in missing:
                lines.append(f"○ {model}")
    if "permissions" in reports:
        permissions = reports["permissions"]
        policy = permissions.get("policy") or {}
        checks_dir = permissions.get("checks_dir") or {}
        lines.extend(
            [
                "",
                "Permissions:",
                f"Policy: {'present' if policy.get('exists') else 'missing'} {policy.get('path')}",
                f"Checks: {checks_dir.get('count', 0)} files at {checks_dir.get('path')}",
            ]
        )
        for warning in permissions.get("warnings") or []:
            lines.append(f"! {warning}")
    return "\n".join(lines)


def format_bytes(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return "unknown"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def probe_command(name: str, version_args: list[str], roles: list[str], mode: str | None = None) -> dict[str, Any]:
    candidates = command_candidates(name)
    if not candidates:
        return {
            "status": "unavailable",
            "id": name,
            "kind": "provider_cli",
            "command": name,
            "roles": roles,
            "mode": "prepare_only",
            "risks": ["not_installed"],
            "reason": "not found on PATH",
        }
    gated_probe: dict[str, Any] | None = None
    try:
        for path in candidates:
            completed = subprocess.run([path, *version_args], text=True, capture_output=True, timeout=10)
            raw = (completed.stdout or completed.stderr).strip()
            if completed.returncode != 0 or "접근 거부" in raw or "틀렸습니다" in raw:
                gated_probe = {
                    "status": "gated",
                    "id": name,
                    "kind": "provider_cli",
                    "command": name,
                    "path": path,
                    "version": "",
                    "roles": roles,
                    "mode": "prepare_only",
                    "risks": ["access_gate", "execution_not_available"],
                    "reason": raw.splitlines()[0] if raw else f"{name} probe exited {completed.returncode}",
                }
                continue
            version = raw.splitlines()[0] if raw else ""
            return {
                "status": "available",
                "id": name,
                "kind": "provider_cli",
                "command": name,
                "path": path,
                "version": version,
                "roles": roles,
                "mode": mode or ("execute_supported" if name in {"claude", "gemini"} else "prepare_only"),
                "risks": provider_risks(name),
            }
    except Exception as exc:
        return {
            "status": "gated",
            "id": name,
            "kind": "provider_cli",
            "command": name,
            "path": candidates[0],
            "version": "",
            "roles": roles,
            "mode": "prepare_only",
            "risks": ["probe_failed"],
            "reason": f"version probe failed: {exc}",
        }
    return gated_probe or {
        "status": "unavailable",
        "id": name,
        "kind": "provider_cli",
        "command": name,
        "roles": roles,
        "mode": "prepare_only",
        "risks": ["not_installed"],
        "reason": "no usable candidate",
    }


def command_candidates(name: str) -> list[str]:
    paths: list[str] = []
    first = shutil.which(name)
    if first:
        paths.append(first)
    if name == "codex":
        candidate = Path.home() / ".nvm" / "versions" / "node" / "v22.22.2" / "bin" / "codex"
        if candidate.exists():
            paths.append(candidate.as_posix())
    seen = set()
    unique = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            unique.append(path)
    return unique


def provider_risks(name: str) -> list[str]:
    return {
        "claude": ["can_edit_when_permissions_allow", "dangerous_bypass_forbidden"],
        "codex": ["repo_write_modes_require_explicit_approval", "local_path_wrapper_possible"],
        "gemini": ["yolo_mode_forbidden", "trust_bypass_requires_root_policy"],
    }.get(name, [])


def probe_env_provider(name: str, env_var: str, roles: list[str]) -> dict[str, Any]:
    return {
        "id": name,
        "kind": "http_api",
        "status": "configured" if os.environ.get(env_var) else "unconfigured",
        "command": None,
        "base_url": provider_base_url(name),
        "env_var": env_var,
        "roles": roles,
        "mode": "http",
        "risks": ["hosted_cost", "secret_required", "network_dependency"],
        "reason": "" if os.environ.get(env_var) else f"{env_var} is not set",
    }


def probe_optional_cli(name: str, roles: list[str]) -> dict[str, Any]:
    path = shutil.which(name)
    if not path:
        return {
            "id": name,
            "kind": "provider_cli",
            "status": "unavailable",
            "command": name,
            "path": None,
            "version": "",
            "roles": roles,
            "mode": "prepare_only",
            "risks": ["not_installed", "adapter_stub"],
            "reason": "not found on PATH",
        }
    version = ""
    for args in (["--version"], ["version"]):
        try:
            completed = subprocess.run([path, *args], text=True, capture_output=True, timeout=5)
            raw = (completed.stdout or completed.stderr).strip()
            if completed.returncode == 0 and raw:
                version = raw.splitlines()[0]
                break
        except Exception:
            continue
    return {
        "id": name,
        "kind": "provider_cli",
        "status": "available",
        "command": name,
        "path": path,
        "version": version,
        "roles": roles,
        "mode": "prepare_only",
        "risks": ["adapter_stub", "execution_not_integrated"],
        "reason": "",
    }


def provider_base_url(name: str) -> str | None:
    return {
        "deepseek_api": "https://api.deepseek.com",
        "qwen_api": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    }.get(name)


def probe_ollama(root: Path) -> dict[str, Any]:
    wrapper = root / "scripts" / "ollama-local.sh"
    status = "available" if wrapper.exists() else "unavailable"
    manifest_models = read_ollama_manifest_models(root)
    server_models: list[str] = []
    server = "unreachable"
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
            server_models = [item.get("name", "") for item in body.get("models", []) if item.get("name")]
            server = "running"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        server = "unreachable"
    return {
        "id": "ollama",
        "kind": "local_runtime",
        "status": status,
        "command": wrapper.as_posix() if wrapper.exists() else "ollama",
        "path": wrapper.as_posix() if wrapper.exists() else None,
        "server": server,
        "models": server_models or manifest_models,
        "manifest_models": manifest_models,
        "model_source": "server" if server_models else "manifest",
        "roles": ["classifier", "context-compressor", "memory-extractor", "log-summarizer"],
        "mode": "local_runtime",
        "risks": ["local_resource_pressure", "model_load_failures_possible"],
    }


def probe_local_backend(root: Path) -> dict[str, Any]:
    """Backend-agnostic local model runtime facade.

    Ollama is only one adapter behind this facade. The rest of Hive Mind should
    depend on this protocol shape, not on Ollama-specific commands.
    """
    runtime = local_runtime_report(root, write=False, _skip_facade=True)
    return active_local_backend(runtime)


def read_ollama_manifest_models(root: Path) -> list[str]:
    manifests = root / ".local" / "ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
    if not manifests.exists():
        return []
    models = []
    for model_dir in sorted(path for path in manifests.iterdir() if path.is_dir()):
        for tag_path in sorted(path for path in model_dir.iterdir() if path.is_file()):
            models.append(f"{model_dir.name}:{tag_path.name}")
    return models


def local_runtime_report(root: Path, write: bool = False, _skip_facade: bool = False) -> dict[str, Any]:
    ollama = probe_ollama(root)
    backends = {
        "ollama": ollama,
        "llama_cpp": probe_cli_backend("llama_cpp", "llama-cli", roles=["local-worker", "benchmark"]),
        "vllm": probe_http_backend("vllm", "http://127.0.0.1:8000/v1/models", roles=["local-worker", "benchmark"]),
    }
    active_backend = select_active_backend(backends)
    active = backends.get(active_backend, {})
    recommended = ["qwen3:1.7b", "phi4-mini", "qwen3:8b", "deepseek-coder:6.7b", "deepseek-coder-v2:16b", "qwen3-coder:30b"]
    present = set(active.get("models") or [])
    missing = [model for model in recommended if not local_model_available(model, present)]
    report = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "protocol": "hive-local-backend-v1",
        "active_backend": active_backend,
        "backends": backends,
        "ollama": ollama,
        "recommended_models": recommended,
        "missing_recommended_models": missing,
        "open_weight_note": (
            "DeepSeek and Qwen can run locally through optional local backends without API keys. "
            "DEEPSEEK_API_KEY and QWEN_API_KEY are only needed for hosted HTTP providers."
        ),
    }
    if write:
        project_dir = root / PROJECT_DIR
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "local_runtime.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def format_local_runtime(report: dict[str, Any]) -> str:
    backend = active_local_backend(report)
    lines = [
        "Hive Mind Local Runtime",
        "",
        f"Protocol: {report.get('protocol')}",
        f"Active backend: {report.get('active_backend')}",
        f"Backend status: {backend.get('status')} {backend.get('path') or backend.get('command') or ''}",
        f"Backend server: {backend.get('server', 'n/a')}",
        f"Model source: {backend.get('model_source')}",
        "",
        "Models:",
    ]
    for model in backend.get("models") or []:
        lines.append(f"✓ {model}")
    if not backend.get("models"):
        lines.append("○ no local backend model manifests found")
    backends = report.get("backends") or {}
    if backends:
        lines.extend(["", "Adapters:"])
        for name, item in backends.items():
            lines.append(f"- {name}: {item.get('status')} mode={item.get('mode')} server={item.get('server', 'n/a')}")
    lines.extend(["", "Missing recommended models:"])
    missing = report.get("missing_recommended_models") or []
    if missing:
        for model in missing:
            lines.append(f"○ {model}")
    else:
        lines.append("✓ none")
    lines.extend(["", report["open_weight_note"]])
    return "\n".join(lines)


def probe_cli_backend(name: str, binary: str, roles: list[str]) -> dict[str, Any]:
    found = shutil.which(binary)
    return {
        "id": name,
        "kind": "local_runtime",
        "status": "available" if found else "unavailable",
        "command": binary,
        "path": found,
        "server": "n/a",
        "models": [],
        "manifest_models": [],
        "model_source": "none",
        "roles": roles,
        "mode": "local_runtime",
        "risks": ["adapter_not_integrated"] if found else ["not_installed", "adapter_not_integrated"],
    }


def probe_http_backend(name: str, models_url: str, roles: list[str]) -> dict[str, Any]:
    models: list[str] = []
    server = "unreachable"
    try:
        with urllib.request.urlopen(models_url, timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
        raw_models = body.get("data") or body.get("models") or []
        for item in raw_models:
            if isinstance(item, dict) and item.get("id"):
                models.append(str(item["id"]))
            elif isinstance(item, str):
                models.append(item)
        server = "running"
    except Exception:
        server = "unreachable"
    return {
        "id": name,
        "kind": "local_runtime",
        "status": "available" if server == "running" else "unavailable",
        "command": models_url,
        "path": None,
        "server": server,
        "models": models,
        "manifest_models": models,
        "model_source": "server" if models else "none",
        "roles": roles,
        "mode": "local_runtime",
        "risks": ["openai_compatible_adapter", "model_load_failures_possible"],
    }


def select_active_backend(backends: dict[str, dict[str, Any]]) -> str:
    requested = os.environ.get("HIVE_LOCAL_BACKEND") or os.environ.get("HIVE_LOCAL_RUNTIME")
    if requested and requested in backends:
        return requested
    for name, item in backends.items():
        if item.get("status") == "available" and item.get("models"):
            return name
    for name, item in backends.items():
        if item.get("status") == "available":
            return name
    return "none"


def active_local_backend(runtime: dict[str, Any]) -> dict[str, Any]:
    active = runtime.get("active_backend")
    backends = runtime.get("backends") or {}
    if active in backends:
        return backends[active]
    if runtime.get("ollama"):
        return runtime["ollama"]
    return {"id": "none", "status": "unavailable", "models": [], "model_source": "none", "server": "n/a"}


def local_routes_report() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "routes": worker_route_table(),
    }


def checks_report(root: Path) -> dict[str, Any]:
    check_dir = root / PROJECT_DIR / CHECKS_DIR
    checks = []
    if check_dir.exists():
        for path in sorted(check_dir.glob("*.md")):
            checks.append(parse_check_file(path, root))
    return {"schema_version": 1, "checks_dir": check_dir.as_posix(), "checks": checks}


def format_checks_report(report: dict[str, Any]) -> str:
    lines = [f"Hive Mind Checks: {report.get('checks_dir')}", ""]
    checks = report.get("checks") or []
    if not checks:
        lines.append("No checks found. Run: hive init")
        return "\n".join(lines)
    for check in checks:
        lines.append(f"- {check.get('id')} [{check.get('severity')}] {check.get('title')}")
    return "\n".join(lines)


def run_checks(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    report = checks_report(root)
    results = []
    for check in report["checks"]:
        result = evaluate_check(root, paths, state, check)
        results.append(result)
    verdict = "pass"
    if any(item["status"] == "fail" for item in results):
        verdict = "fail"
    elif any(item["status"] == "warn" for item in results):
        verdict = "warn"
    out = {
        "schema_version": 1,
        "run_id": paths.run_id,
        "verdict": verdict,
        "results": results,
    }
    out_path = paths.run_dir / "checks_report.json"
    write_json(out_path, out)
    append_transcript(paths, "Ran", f"`hive check run` -> `{out_path.relative_to(root).as_posix()}` verdict={verdict}")
    append_event(paths, "checks_report_created", {"artifact": out_path.relative_to(root).as_posix(), "verdict": verdict})
    return out


def git_diff_report(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, _ = load_run(root, run_id)
    from .workloop import replay_execution_ledger

    status = run_git(root, ["status", "--short"])
    diff_stat = run_git(root, ["diff", "--stat"])
    diff_name = run_git(root, ["diff", "--name-only"])
    staged_name = run_git(root, ["diff", "--cached", "--name-only"])
    ledger = replay_execution_ledger(root, paths.run_id)
    ledger_touched = sorted(
        {
            str(item)
            for step in (ledger.get("steps") or {}).values()
            for item in (step.get("files_touched") or [])
            if item
        }
    )
    ledger_summary = {
        "ok": ledger.get("ok"),
        "record_count": ledger.get("record_count"),
        "hash_chain_ok": ledger.get("hash_chain_ok"),
        "seq_ok": ledger.get("seq_ok"),
        "issue_count": len(ledger.get("issues") or []),
        "artifact_hash_drift_count": sum(1 for issue in ledger.get("issues") or [] if issue.get("type") == "artifact_hash_drift"),
        "touched_files": ledger_touched,
    }
    report = {
        "schema_version": 1,
        "run_id": paths.run_id,
        "status_short": status["stdout"].splitlines(),
        "changed_files": [line for line in diff_name["stdout"].splitlines() if line.strip()],
        "staged_files": [line for line in staged_name["stdout"].splitlines() if line.strip()],
        "diff_stat": diff_stat["stdout"].splitlines(),
        "ledger": ledger_summary,
        "git_available": status["returncode"] == 0,
    }
    out_path = paths.run_dir / "git_diff_report.json"
    write_json(out_path, report)
    append_transcript(paths, "Ran", f"`git diff --stat` and `git diff --name-only` -> `{out_path.relative_to(root).as_posix()}`")
    append_event(paths, "git_diff_report_created", {"artifact": out_path.relative_to(root).as_posix(), "changed": len(report["changed_files"])})
    return report


def format_git_diff_report(report: dict[str, Any]) -> str:
    lines = [f"Git Diff: {report.get('run_id')}", ""]
    lines.append("Changed files:")
    for path in report.get("changed_files") or []:
        lines.append(f"- {path}")
    if not report.get("changed_files"):
        lines.append("- none")
    if report.get("diff_stat"):
        lines.extend(["", "Diff stat:"])
        lines.extend(str(line) for line in report["diff_stat"])
    ledger = report.get("ledger") or {}
    lines.extend(
        [
            "",
            "Ledger:",
            f"- ok={ledger.get('ok')} records={ledger.get('record_count')} hash_chain={ledger.get('hash_chain_ok')} seq={ledger.get('seq_ok')} issues={ledger.get('issue_count')}",
            f"- artifact_hash_drift={ledger.get('artifact_hash_drift_count')}",
            "- touched files:",
        ]
    )
    for path in ledger.get("touched_files") or []:
        lines.append(f"  - {path}")
    if not ledger.get("touched_files"):
        lines.append("  - none")
    return "\n".join(lines)


def git_guard_report(
    root: Path,
    run_id: str | None = None,
    *,
    scopes: list[str] | None = None,
    approve_out_of_scope: bool = False,
) -> dict[str, Any]:
    paths, _ = load_run(root, run_id)
    from .workloop import replay_execution_ledger

    staged = [line for line in run_git(root, ["diff", "--cached", "--name-only"])["stdout"].splitlines() if line.strip()]
    explicit_scopes = [scope.strip() for scope in (scopes or []) if scope and scope.strip()]
    ledger = replay_execution_ledger(root, paths.run_id)
    ledger_scopes = sorted(
        {
            str(item)
            for step in (ledger.get("steps") or {}).values()
            for item in (step.get("files_touched") or [])
            if item
        }
    )
    allowed_scopes = explicit_scopes or ledger_scopes
    scoped = [path for path in staged if path_matches_scope(path, allowed_scopes)]
    out_of_scope = [path for path in staged if path not in scoped]
    if out_of_scope and not approve_out_of_scope:
        verdict = "blocked"
        status = "fail"
    elif out_of_scope and approve_out_of_scope:
        verdict = "approved_with_override"
        status = "warn"
    else:
        verdict = "pass"
        status = "pass"
    report = {
        "schema_version": 1,
        "kind": "hive_git_guard",
        "run_id": paths.run_id,
        "verdict": verdict,
        "status": status,
        "staged_files": staged,
        "allowed_scopes": allowed_scopes,
        "scope_source": "explicit" if explicit_scopes else "ledger_touched_files",
        "scoped_files": scoped,
        "out_of_scope_files": out_of_scope,
        "approve_out_of_scope": approve_out_of_scope,
        "can_commit": verdict in {"pass", "approved_with_override"},
        "reason": git_guard_reason(staged, allowed_scopes, out_of_scope, approve_out_of_scope),
    }
    out_path = paths.run_dir / "git_guard_report.json"
    write_json(out_path, report)
    add_state_artifact(paths, "git_guard_report", out_path)
    append_transcript(paths, "Ran", f"`hive git guard` -> `{out_path.relative_to(root).as_posix()}` verdict={verdict}")
    append_event(paths, "git_guard_report_created", {"artifact": out_path.relative_to(root).as_posix(), "verdict": verdict, "out_of_scope": len(out_of_scope)})
    return report


def path_matches_scope(path: str, scopes: list[str]) -> bool:
    if not scopes:
        return False
    normalized = path.strip().lstrip("./")
    for scope in scopes:
        item = scope.strip().lstrip("./")
        if not item:
            continue
        if item.endswith("/"):
            if normalized.startswith(item):
                return True
            continue
        if any(ch in item for ch in "*?[]") and fnmatch(normalized, item):
            return True
        if normalized == item or normalized.startswith(item.rstrip("/") + "/"):
            return True
    return False


def git_guard_reason(staged: list[str], scopes: list[str], out_of_scope: list[str], approved: bool) -> str:
    if not staged:
        return "no staged files"
    if not scopes:
        return "staged files exist but no allowed scope was provided or inferred from the run ledger"
    if out_of_scope and approved:
        return "out-of-scope staged files allowed by explicit operator override"
    if out_of_scope:
        return "out-of-scope staged files require --approve-out-of-scope"
    return "all staged files are within allowed scope"


def format_git_guard_report(report: dict[str, Any]) -> str:
    lines = [
        f"Git Guard: {report.get('run_id')}",
        f"Verdict: {report.get('verdict')}  Can commit: {report.get('can_commit')}",
        f"Reason: {report.get('reason')}",
        "",
        "Allowed scopes:",
    ]
    scopes = report.get("allowed_scopes") or []
    lines.extend(f"- {scope}" for scope in scopes) if scopes else lines.append("- none")
    lines.extend(["", "Staged files:"])
    staged = report.get("staged_files") or []
    lines.extend(f"- {path}" for path in staged) if staged else lines.append("- none")
    out_of_scope = report.get("out_of_scope_files") or []
    if out_of_scope:
        lines.extend(["", "Out of scope:"])
        lines.extend(f"- {path}" for path in out_of_scope)
    return "\n".join(lines)


def review_diff(root: Path, run_id: str | None = None) -> Path:
    paths, _ = load_run(root, run_id)
    ensure_local_backend(root)
    diff = run_git(root, ["diff", "--", "."])["stdout"]
    diff_path = paths.artifacts / "git_diff.patch"
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.write_text(diff[:120000], encoding="utf-8")
    append_transcript(paths, "Ran", f"`git diff -- .` -> `{diff_path.relative_to(root).as_posix()}`")
    paths.context_pack.write_text(
        paths.context_pack.read_text(encoding="utf-8")
        + "\n\n## Git Diff For Review\n"
        + f"Diff artifact: `{diff_path.relative_to(root).as_posix()}`\n",
        encoding="utf-8",
    )
    append_event(paths, "git_diff_captured", {"artifact": diff_path.relative_to(root).as_posix()})
    return invoke_local(root, "review", run_id=paths.run_id, complexity="fast")


def commit_summary(root: Path, run_id: str | None = None) -> Path:
    paths, state = load_run(root, run_id)
    report = git_diff_report(root, paths.run_id)
    lines = [
        f"# Commit Summary Proposal: {paths.run_id}",
        "",
        f"Task: {state.get('user_request')}",
        "",
        "## Changed Files",
    ]
    for path in report.get("changed_files") or []:
        lines.append(f"- {path}")
    if not report.get("changed_files"):
        lines.append("- none")
    lines.extend(["", "## Proposed Commit Message", "", proposed_commit_message(state, report)])
    out_path = paths.run_dir / "commit_summary.md"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    append_transcript(paths, "Edited", f"`{out_path.relative_to(root).as_posix()}` proposed commit summary")
    append_event(paths, "commit_summary_created", {"artifact": out_path.relative_to(root).as_posix()})
    return out_path


def run_git(root: Path, args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=30)
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def proposed_commit_message(state: dict[str, Any], report: dict[str, Any]) -> str:
    request = str(state.get("user_request") or "Update Hive Mind")
    first = request.strip().splitlines()[0][:72]
    if first:
        return first[0].upper() + first[1:]
    changed = report.get("changed_files") or []
    if changed:
        return f"Update {changed[0]}"
    return "Update Hive Mind"


def format_checks_run(report: dict[str, Any]) -> str:
    lines = [f"Checks: {report.get('run_id')} verdict={report.get('verdict')}", ""]
    for result in report.get("results") or []:
        lines.append(f"- {result.get('status')} {result.get('id')}: {result.get('message')}")
    return "\n".join(lines)


def parse_check_file(path: Path, root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---\n"):
        _, raw_meta, body = text.split("---", 2)
        for line in raw_meta.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip().strip('"')
    return {
        "id": meta.get("id") or path.stem,
        "title": meta.get("title") or first_heading(body) or path.stem,
        "severity": meta.get("severity", "medium"),
        "type": meta.get("type", "manual"),
        "path": path.relative_to(root).as_posix(),
        "body": body.strip(),
    }


def evaluate_check(root: Path, paths: RunPaths, state: dict[str, Any], check: dict[str, Any]) -> dict[str, Any]:
    check_id = check.get("id")
    severity = check.get("severity", "medium")
    if check_id == "no-raw-export-leak":
        risky = []
        for rel_path in state.get("artifacts", {}).values():
            if isinstance(rel_path, str) and ("data/" in rel_path or rel_path.startswith("data")):
                risky.append(rel_path)
        status = "fail" if risky else "pass"
        message = "raw data artifact referenced" if risky else "no raw data artifacts referenced"
        return {"id": check_id, "severity": severity, "status": status, "message": message, "evidence": risky}
    if check_id == "implementation-handoff":
        missing = []
        for path in [paths.task, paths.context_pack, paths.handoff]:
            if not path.exists() or not path.read_text(encoding="utf-8").strip():
                missing.append(path.relative_to(root).as_posix())
        has_codex = any(agent.get("name") == "codex-executor" and agent.get("status") in {"prepared", "completed"} for agent in state.get("agents", []))
        if not has_codex:
            missing.append("codex-executor prepared/completed")
        status = "warn" if missing else "pass"
        message = "missing implementation handoff inputs" if missing else "handoff inputs present"
        return {"id": check_id, "severity": severity, "status": status, "message": message, "evidence": missing}
    if check_id == "memory-policy":
        drafts = paths.run_dir / "memory_drafts.json"
        status = "pass" if drafts.exists() else "warn"
        message = "memory drafts artifact exists" if drafts.exists() else "memory drafts artifact missing"
        return {"id": check_id, "severity": severity, "status": status, "message": message, "evidence": [drafts.relative_to(root).as_posix()]}
    return {"id": check_id, "severity": severity, "status": "manual", "message": "manual check only", "evidence": [check.get("path")]}


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return None


def ask_router(root: Path, prompt: str, run_id: str | None = None, complexity: str = "default") -> Path:
    """Route one user prompt through the local intent router and prepare provider artifacts."""
    paths = create_run(root, prompt, project="Hive Mind", task_type="routed") if run_id is None else load_run(root, run_id)[0]
    paths.local_dir.mkdir(parents=True, exist_ok=True)
    ensure_local_backend(root)
    method_profile = load_router_method_profile()
    router_input = (
        "# User Prompt\n"
        f"{prompt.strip()}\n\n"
        "# Operator Method Profile\n"
        f"{method_profile}\n\n"
        "# Available Harness Roles\n"
        "- local/context: compress context for handoff\n"
        "- local/handoff: draft implementation handoff\n"
        "- local/memory: extract memory drafts\n"
        "- local/summarize: summarize logs/events\n"
        "- local/review: first-pass risk review\n"
        "- claude/planner: conceptual plan and risk discipline\n"
        "- codex/executor: implementation prompt artifact\n"
        "- gemini/reviewer: alternate/multimodal review prompt artifact\n"
    )
    model = choose_model("intent_router", complexity)
    local_runtime = "none"
    use_fast_heuristic = complexity == "fast" or os.environ.get("HIVE_ROUTER_MODE") == "heuristic"
    if use_fast_heuristic:
        parsed = heuristic_route_prompt(prompt)
        validation = {
            "valid": True,
            "issues": [],
            "confidence": parsed.get("confidence"),
            "should_escalate": parsed.get("should_escalate", False),
            "escalation_reason": parsed.get("escalation_reason", ""),
        }
        worker_output = {"runtime": "heuristic", "model": "code", "parsed": parsed, "raw": ""}
        router_status = "completed"
        route_source = "heuristic_fast"
        actions = normalize_router_actions(parsed.get("actions"))
    else:
        set_agent_status(paths, "local-intent-router", "running")
        append_event(paths, "agent_started", {"agent": "local", "role": "intent-router", "worker": "intent_router"})
        local_runtime = local_runtime_report(root, write=True).get("active_backend", "none")
        try:
            worker_output = run_worker("intent_router", router_input, model=model, runtime=local_runtime, source_ref="user_prompt")
            parsed = worker_output.get("parsed") if isinstance(worker_output.get("parsed"), dict) else {}
            validation = validate_worker_result("intent_router", worker_output)
            if validation["valid"]:
                router_status = "completed"
                route_source = "local_llm"
                actions = normalize_router_actions(parsed.get("actions"))
            else:
                parsed = heuristic_route_prompt(prompt)
                router_status = "fallback"
                route_source = "invalid_local_fallback"
                actions = normalize_router_actions(parsed.get("actions"))
        except Exception as exc:
            parsed = heuristic_route_prompt(prompt)
            validation = {
                "valid": False,
                "issues": [str(exc)],
                "confidence": parsed.get("confidence"),
                "should_escalate": True,
                "escalation_reason": f"local intent router failed; used heuristic fallback: {exc}",
            }
            worker_output = {"runtime": local_runtime, "model": model, "parsed": parsed, "raw": "", "error": str(exc)}
            router_status = "fallback"
            route_source = "heuristic_fallback"
            actions = normalize_router_actions(parsed.get("actions"))

    result = {
        "schema_version": 1,
        "agent": "local",
        "role": "intent-router",
        "status": router_status,
        "provider_mode": "local_runtime",
        "runtime": worker_output.get("runtime"),
        "worker": "intent_router",
        "model": model,
        "source_ref": "user_prompt",
        "route_source": route_source,
        "output_valid": validation["valid"],
        "output_issues": validation["issues"],
        "confidence": validation["confidence"],
        "should_escalate": validation["should_escalate"],
        "escalation_reason": validation["escalation_reason"],
        "artifacts_created": [],
        "output": worker_output,
        "normalized_actions": actions,
    }
    router_path = paths.local_dir / "intent_router.json"
    result["artifacts_created"] = [router_path.relative_to(root).as_posix()]
    write_json(router_path, result)
    append_transcript(paths, "Ran", f"`hive ask` routed prompt via {route_source} -> `{router_path.relative_to(root).as_posix()}`")
    set_agent_status(paths, "local-intent-router", "completed" if router_status in {"completed", "fallback"} else "failed")
    append_event(paths, "intent_routed", {"agent": "local", "role": "intent-router", "artifact": router_path.relative_to(root).as_posix(), "source": route_source})
    append_hive_activity(
        paths,
        "local/intent-router",
        "decomposed_prompt",
        f"Intent `{parsed.get('intent', 'unknown')}` via {route_source}; {len(actions)} member actions proposed.",
        {"intent": parsed.get("intent", "unknown"), "route_source": route_source, "actions": actions},
    )
    ensure_capabilityos_recommendation(root, paths.run_id)

    prepared: list[str] = []
    for action in actions:
        provider = action["provider"]
        role = action["role"]
        try:
            if provider == "local":
                append_agent_log(paths, "local", role, f"prepared worker request from {route_source}; execution requires hive invoke local --role {role}")
                set_agent_status(paths, local_agent_name(role), "ready")
            elif provider in {"claude", "codex", "gemini"}:
                out = invoke_external_agent(root, provider, role, run_id=paths.run_id, execute=False)
                prepared.append(out.relative_to(root).as_posix())
            append_hive_activity(
                paths,
                f"{provider}/{role}",
                "prepared_member",
                action.get("reason") or f"{provider}/{role} prepared for hive work.",
                {"provider": provider, "role": role},
            )
        except Exception as exc:
            append_event(paths, "route_action_failed", {"provider": provider, "role": role, "error": str(exc)})
            append_hive_activity(
                paths,
                f"{provider}/{role}",
                "member_prepare_failed",
                str(exc),
                {"provider": provider, "role": role},
            )

    plan_path = paths.run_dir / "routing_plan.json"
    plan = {
        "schema_version": 1,
        "run_id": paths.run_id,
        "prompt": prompt,
        "intent": parsed.get("intent", "unknown"),
        "summary": parsed.get("summary", ""),
        "route_source": route_source,
        "actions": actions,
        "prepared_artifacts": prepared,
        "risks": parsed.get("risks", []),
        "open_questions": parsed.get("open_questions", []),
    }
    plan["operator_summary"] = build_operator_summary_from_plan(plan)
    write_json(plan_path, plan)
    append_transcript(paths, "Edited", f"`{plan_path.relative_to(root).as_posix()}` with {len(actions)} route actions")
    append_event(paths, "routing_plan_created", {"artifact": plan_path.relative_to(root).as_posix(), "prepared": len(prepared)})
    update_state(paths, phase="routing", status="ready")
    return plan_path


def orchestrate_prompt(
    root: Path,
    prompt: str,
    run_id: str | None = None,
    complexity: str = "default",
    execute: bool = False,
    execute_local: bool = False,
    advance_workflow: bool = True,
) -> dict[str, Any]:
    """Turn a prompt into a multi-agent society plan and prepare worker/provider artifacts.

    When ``advance_workflow`` is False the function stops after writing the
    society plan and updating run state — useful for AIOS contract gating
    where execution must wait for the three-OS consensus to sign.
    """
    plan_path = ask_router(root, prompt, run_id=run_id, complexity=complexity)
    paths, state = load_run(root, plan_path.parent.name)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    providers = detect_agents(root, write=True).get("providers") or {}
    members: list[dict[str, Any]] = []
    for index, action in enumerate(plan.get("actions") or [], start=1):
        provider = str(action.get("provider"))
        role = str(action.get("role"))
        mode = "local_runtime" if provider == "local" else (providers.get(provider) or {}).get("mode", "prepare_only")
        command = (
            f"hive invoke local --role {role}"
            if provider == "local"
            else f"hive invoke {provider} --role {role}" + (" --execute" if execute and provider != "codex" else "")
        )
        members.append(
            {
                "order": index,
                "provider": provider,
                "role": role,
                "mode": mode,
                "status": agent_status(state, f"{provider}-{role}") or ("ready" if provider != "local" else agent_status(state, local_agent_name(role))),
                "reason": action.get("reason", ""),
                "command": command,
                "artifact_prefix": (paths.run_dir / "agents" / provider).relative_to(root).as_posix()
                if provider != "local"
                else paths.local_dir.relative_to(root).as_posix(),
            }
        )

    society_path = paths.run_dir / "society_plan.json"
    report = {
        "schema_version": 1,
        "run_id": paths.run_id,
        "prompt": prompt,
        "intent": plan.get("intent", "unknown"),
        "summary": plan.get("summary", ""),
        "route_source": plan.get("route_source", "unknown"),
        "execute_requested": execute,
        "members": members,
        "prepared_artifacts": plan.get("prepared_artifacts", []),
        "next": recommend_next_action(paths, state, pipeline_status(paths), artifact_status(paths, state)),
    }
    write_json(society_path, report)
    append_transcript(paths, "Prepared", f"`{society_path.relative_to(root).as_posix()}` with {len(members)} society members")
    append_event(paths, "society_plan_created", {"artifact": society_path.relative_to(root).as_posix(), "members": len(members)})
    append_hive_activity(
        paths,
        "hive-mind",
        "society_plan_ready",
        f"{len(members)} provider/local members assigned; next: {(report.get('next') or {}).get('command')}",
        {"members": members, "next": report.get("next")},
    )
    update_state(paths, phase="orchestration", status="ready")
    if not advance_workflow:
        report["operator_summary"] = build_operator_summary_from_plan(plan, workflow_next=report.get("next"))
        report["workflow"] = {
            "status": "deferred",
            "scheduler": None,
            "artifact": None,
            "next": report.get("next"),
            "actions_taken": [],
            "reason": "advance_workflow=False (e.g. AIOS contract awaits operator sign)",
        }
        return report
    workflow = flow_advance(root, run_id=paths.run_id, complexity=complexity, execute_local=execute_local)
    report["workflow"] = {
        "status": workflow.get("status"),
        "scheduler": workflow.get("scheduler"),
        "artifact": workflow.get("artifact"),
        "next": workflow.get("next"),
        "actions_taken": workflow.get("actions_taken", []),
    }
    report["next"] = workflow.get("next") or report.get("next")
    report["operator_summary"] = build_operator_summary_from_plan(plan, workflow_next=report.get("next"))
    return report


def debate_topic(
    root: Path,
    topic: str,
    run_id: str | None = None,
    participants: list[str] | None = None,
    execute: bool = False,
) -> dict[str, Any]:
    """Run a provider deliberation barrier: first opinions, review, convergence."""
    selected = participants or ["claude", "gemini", "codex"]
    allowed = {"claude", "gemini", "codex"}
    invalid = sorted(set(selected) - allowed)
    if invalid:
        raise ValueError(f"Unsupported debate participants: {', '.join(invalid)}")

    paths = create_run(root, f"Provider debate: {topic}", project="Hive Mind", task_type="deliberation") if run_id is None else load_run(root, run_id)[0]
    topic_path = paths.run_dir / "debate_topic.md"
    topic_path.write_text(f"# Debate Topic\n\n{topic.strip()}\n", encoding="utf-8")
    add_state_artifact(paths, "debate_topic", topic_path)
    append_transcript(paths, "Debate", f"Topic recorded at `{topic_path.relative_to(root).as_posix()}`")

    rounds: list[dict[str, Any]] = []
    round1 = run_debate_round(root, paths, selected, "debate_initial", execute=execute)
    rounds.append(round1)
    snapshot1 = write_debate_snapshot(root, paths, "debate_round1.md", topic, round1)
    append_context_section(paths, "Debate Round 1 Snapshot", snapshot1.read_text(encoding="utf-8"))

    round2 = run_debate_round(root, paths, selected, "debate_review", execute=execute)
    rounds.append(round2)
    snapshot2 = write_debate_snapshot(root, paths, "debate_round2.md", topic, round2)

    convergence = write_debate_convergence(root, paths, topic, rounds)
    report_path = paths.run_dir / "debate_report.json"
    report = {
        "schema_version": 1,
        "run_id": paths.run_id,
        "topic": topic,
        "participants": selected,
        "execute_requested": execute,
        "barrier": "all_participants_processed_before_convergence",
        "rounds": rounds,
        "artifacts": {
            "topic": topic_path.relative_to(root).as_posix(),
            "round1": snapshot1.relative_to(root).as_posix(),
            "round2": snapshot2.relative_to(root).as_posix(),
            "convergence": convergence.relative_to(root).as_posix(),
        },
        "next": {"command": f"hive transcript --run-id {paths.run_id}", "reason": "inspect debate and convergence artifacts"},
    }
    write_json(report_path, report)
    add_state_artifact(paths, "debate_report", report_path)
    append_event(paths, "debate_convergence_created", {"artifact": convergence.relative_to(root).as_posix(), "participants": selected})
    append_hive_activity(
        paths,
        "hive-mind",
        "debate_converged",
        f"{len(selected)} participants processed through two debate rounds",
        {"debate_report": report_path.relative_to(root).as_posix()},
    )
    update_state(paths, phase="deliberation", status="ready")
    return report


def run_debate_round(root: Path, paths: RunPaths, participants: list[str], role: str, execute: bool) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for participant in participants:
        result_path = invoke_external_agent(
            root,
            participant,
            role,
            run_id=paths.run_id,
            execute=execute and participant != "codex",
        )
        result = yaml.safe_load(result_path.read_text(encoding="utf-8")) or {}
        output_path = result.get("output_path")
        output_text = ""
        if isinstance(output_path, str) and output_path and (root / output_path).exists():
            output_text = (root / output_path).read_text(encoding="utf-8", errors="replace")
        results.append(
            {
                "participant": participant,
                "role": role,
                "status": result.get("status", "unknown"),
                "provider_mode": result.get("provider_mode", "unknown"),
                "result_path": result_path.relative_to(root).as_posix(),
                "output_path": output_path or "",
                "has_output": bool(output_text.strip()),
                "output_preview": output_text.strip()[:1200],
            }
        )
    append_event(paths, "debate_round_created", {"role": role, "participants": participants})
    return {"role": role, "barrier": "complete", "participants": results}


def write_debate_snapshot(root: Path, paths: RunPaths, filename: str, topic: str, round_report: dict[str, Any]) -> Path:
    path = paths.run_dir / filename
    lines = [f"# {round_report.get('role')} Snapshot", "", f"Topic: {topic}", ""]
    for item in round_report.get("participants") or []:
        lines.append(f"## {item.get('participant')}")
        lines.append(f"- status: {item.get('status')}")
        lines.append(f"- result: `{item.get('result_path')}`")
        if item.get("output_path"):
            lines.append(f"- output: `{item.get('output_path')}`")
        preview = item.get("output_preview") or "(prepared; no executed output)"
        lines.extend(["", preview, ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    add_state_artifact(paths, filename.removesuffix(".md"), path)
    return path


def write_debate_convergence(root: Path, paths: RunPaths, topic: str, rounds: list[dict[str, Any]]) -> Path:
    path = paths.run_dir / "debate_convergence.md"
    participants = sorted({item.get("participant") for round_report in rounds for item in round_report.get("participants", []) if item.get("participant")})
    completed = [
        item
        for round_report in rounds
        for item in round_report.get("participants", [])
        if item.get("status") == "completed"
    ]
    prepared = [
        item
        for round_report in rounds
        for item in round_report.get("participants", [])
        if item.get("status") == "prepared"
    ]
    lines = [
        "# Debate Convergence",
        "",
        f"Topic: {topic}",
        "",
        "## Barrier",
        "",
        "All selected participants reached a terminal prepared/completed/failed result before this convergence artifact was written.",
        "",
        "## Participants",
        "",
    ]
    for participant in participants:
        lines.append(f"- {participant}")
    lines.extend(
        [
            "",
            "## Convergence",
            "",
            "- Treat completed provider outputs as evidence.",
            "- Treat prepared-only participants as pending manual or later CLI execution.",
            "- Resolve by comparing concrete risks, acceptance criteria, and reversible next actions.",
            "",
            "## Status",
            "",
            f"- completed outputs: {len(completed)}",
            f"- prepared outputs: {len(prepared)}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    add_state_artifact(paths, "debate_convergence", path)
    return path


def append_context_section(paths: RunPaths, title: str, body: str) -> None:
    with paths.context_pack.open("a", encoding="utf-8") as f:
        f.write(f"\n## {title}\n\n{body.rstrip()}\n")


def add_state_artifact(paths: RunPaths, name: str, path: Path) -> None:
    state = json.loads(paths.state.read_text(encoding="utf-8"))
    artifacts = state.get("artifacts") if isinstance(state.get("artifacts"), dict) else {}
    artifacts[name] = path.relative_to(paths.root).as_posix()
    state["artifacts"] = artifacts
    state["updated_at"] = now_iso()
    write_json(paths.state, state)


def format_orchestration_report(report: dict[str, Any]) -> str:
    workflow = report.get("workflow") or {}
    korean = contains_hangul(str(report.get("prompt") or report.get("summary") or ""))
    labels = operator_labels(korean)
    summary = report.get("operator_summary") or {}
    lines = [
        f"Hive Mind Society: {report.get('run_id')}",
        f"{labels['intent']}: {report.get('intent')} via {report.get('route_source')}",
        f"Lifecycle: {workflow.get('scheduler', 'not_started')} / {workflow.get('status', 'not_started')}",
        f"{labels['summary']}: {report.get('summary')}",
        f"{labels['risk']}: {summary.get('risk_level', 'unknown')}",
        "",
        f"{labels['actions']}:",
    ]
    for member in report.get("members") or []:
        lines.append(
            f"- {member.get('order')}. {member.get('provider')}/{member.get('role')} "
            f"[{member.get('mode')}] -> {member.get('status') or 'planned'}"
        )
        if member.get("reason"):
            lines.append(f"  {labels['reason']}: {localize_operator_text(str(member.get('reason') or ''), korean)}")
        lines.append(f"  command: {member.get('command')}")
    next_action = report.get("next") or {}
    lines.extend(["", f"{labels['next']}:", f"  {next_action.get('command')}", f"  {labels['reason']}: {localize_operator_text(str(next_action.get('reason') or ''), korean)}"])
    expected = summary.get("expected_artifacts") or []
    if expected:
        lines.extend(["", f"{labels['expected_artifacts']}:"])
        for artifact in expected[:8]:
            if isinstance(artifact, dict):
                lines.append(f"- {artifact.get('path')} ({artifact.get('status')})")
            else:
                lines.append(f"- {artifact}")
    risks = summary.get("risks") or []
    if risks:
        lines.extend(["", f"{labels['risks']}:"])
        for risk in risks:
            lines.append(f"- {localize_operator_text(str(risk), korean)}")
    return "\n".join(lines)


def format_debate_report(report: dict[str, Any]) -> str:
    lines = [
        f"Hive Mind Debate: {report.get('run_id')}",
        f"Topic: {report.get('topic')}",
        f"Barrier: {report.get('barrier')}",
        "",
        "Participants:",
    ]
    for participant in report.get("participants") or []:
        lines.append(f"- {participant}")
    for round_report in report.get("rounds") or []:
        lines.extend(["", f"Round: {round_report.get('role')}"])
        for item in round_report.get("participants") or []:
            marker = "output" if item.get("has_output") else "prepared"
            lines.append(f"- {item.get('participant')}: {item.get('status')} ({marker}) -> {item.get('result_path')}")
    artifacts = report.get("artifacts") or {}
    lines.extend(
        [
            "",
            "Artifacts:",
            f"- report: {report.get('run_id')}/debate_report.json",
            f"- round1: {artifacts.get('round1')}",
            f"- round2: {artifacts.get('round2')}",
            f"- convergence: {artifacts.get('convergence')}",
        ]
    )
    next_action = report.get("next") or {}
    lines.extend(["", "Next:", f"  {next_action.get('command')}", f"  Reason: {next_action.get('reason')}"])
    return "\n".join(lines)


def load_routing_plan(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, _ = load_run(root, run_id)
    plan_path = paths.run_dir / "routing_plan.json"
    if not plan_path.exists():
        return {
            "run_id": paths.run_id,
            "status": "missing",
            "path": plan_path.as_posix(),
            "message": "No routing plan yet. Run: hive ask \"your task\"",
        }
    return json.loads(plan_path.read_text(encoding="utf-8"))


def format_routing_plan(plan: dict[str, Any]) -> str:
    if plan.get("status") == "missing":
        return f"Routing Plan: missing\n{plan.get('message')}\n{plan.get('path')}"
    korean = contains_hangul(str(plan.get("prompt") or plan.get("summary") or ""))
    labels = operator_labels(korean)
    summary = plan.get("operator_summary") or build_operator_summary_from_plan(plan)
    lines = [
        f"{labels['routing_plan']}: {plan.get('run_id')}",
        f"{labels['intent']}: {plan.get('intent', 'unknown')}",
        f"{labels['source']}: {plan.get('route_source', 'unknown')}",
        f"{labels['summary']}: {plan.get('summary', '')}",
        f"{labels['risk']}: {summary.get('risk_level', 'unknown')}",
        "",
        f"{labels['actions']}:",
    ]
    for item in plan.get("actions") or []:
        lines.append(f"- {item.get('provider')}/{item.get('role')}: {localize_operator_text(str(item.get('reason') or ''), korean)}")
    next_action = summary.get("next") or {}
    if next_action:
        lines.extend(["", f"{labels['next']}:", f"  {next_action.get('command')}", f"  {labels['reason']}: {localize_operator_text(str(next_action.get('reason') or ''), korean)}"])
    prepared = plan.get("prepared_artifacts") or []
    if prepared:
        lines.extend(["", f"{labels['prepared_artifacts']}:"])
        for artifact in prepared:
            lines.append(f"- {artifact}")
    expected = summary.get("expected_artifacts") or []
    if expected:
        lines.extend(["", f"{labels['expected_artifacts']}:"])
        for artifact in expected:
            if isinstance(artifact, dict):
                lines.append(f"- {artifact.get('path')} ({artifact.get('status')})")
            else:
                lines.append(f"- {artifact}")
    risks = summary.get("risks") or []
    if risks:
        lines.extend(["", f"{labels['risks']}:"])
        for risk in risks:
            lines.append(f"- {localize_operator_text(str(risk), korean)}")
    return "\n".join(lines)


def contains_hangul(text: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in text)


def operator_labels(korean: bool) -> dict[str, str]:
    if korean:
        return {
            "routing_plan": "라우팅 계획",
            "operator_summary": "작업 요약",
            "intent": "의도",
            "source": "라우팅 소스",
            "summary": "요약",
            "risk": "위험도",
            "actions": "작업자",
            "next": "다음",
            "reason": "이유",
            "prepared_artifacts": "준비된 산출물",
            "expected_artifacts": "예상 산출물",
            "risks": "리스크",
        }
    return {
        "routing_plan": "Routing Plan",
        "operator_summary": "Operator Summary",
        "intent": "Intent",
        "source": "Source",
        "summary": "Summary",
        "risk": "Risk",
        "actions": "Actions",
        "next": "Next",
        "reason": "Reason",
        "prepared_artifacts": "Prepared Artifacts",
        "expected_artifacts": "Expected Artifacts",
        "risks": "Risks",
    }


def localize_operator_text(text: str, korean: bool) -> str:
    if not korean:
        return text
    translations = {
        "Prepare context before provider handoff.": "provider handoff 전에 context를 준비합니다.",
        "Clarify plan and risks.": "계획과 리스크를 먼저 명확히 합니다.",
        "Prepare implementation artifact.": "구현용 provider 산출물을 준비합니다.",
        "Prepare independent review.": "독립 리뷰 산출물을 준비합니다.",
        "turn routing plan into a DAG lifecycle": "라우팅 계획을 DAG 실행 lifecycle로 전환합니다.",
        "route_quality: heuristic_fallback should be verified before high-risk execution": "route_quality: heuristic fallback이므로 고위험 실행 전 검증이 필요합니다.",
    }
    return translations.get(text, text)


def build_operator_summary_from_plan(plan: dict[str, Any], *, workflow_next: dict[str, Any] | None = None) -> dict[str, Any]:
    run_id = str(plan.get("run_id") or "")
    actions = [item for item in (plan.get("actions") or []) if isinstance(item, dict)]
    risks = list(plan.get("risks") or [])
    route_source = str(plan.get("route_source") or "")
    if route_source != "local_llm":
        risks.append(f"route_quality: {route_source} should be verified before high-risk execution")
    risk_level = "low"
    if risks:
        risk_level = "medium"
    if any(str(item).lower().startswith(("danger", "high", "irreversible")) for item in risks):
        risk_level = "high"
    expected = [
        {"path": f".runs/{run_id}/routing_plan.json", "status": "written"},
        {"path": f".runs/{run_id}/society_plan.json", "status": "expected_after_orchestrate"},
        {"path": f".runs/{run_id}/plan_dag.json", "status": "expected_after_flow"},
    ]
    for artifact in plan.get("prepared_artifacts") or []:
        expected.append({"path": artifact, "status": "prepared"})
    for action in actions:
        provider = str(action.get("provider") or "")
        role = str(action.get("role") or "")
        if provider == "local":
            expected.append({"path": f".runs/{run_id}/agents/local/{role.replace('-', '_')}.json", "status": "expected_after_local_invoke"})
    next_action = workflow_next or {"command": f"hive flow --run-id {run_id}", "reason": "turn routing plan into a DAG lifecycle"}
    return {
        "risk_level": risk_level,
        "risks": risks,
        "next": next_action,
        "expected_artifacts": expected,
    }


def ensure_local_backend(root: Path) -> None:
    runtime = local_runtime_report(root, write=False)
    backend = runtime.get("active_backend") or "none"
    if backend != "ollama":
        return
    if os.environ.get("HIVE_LOCAL_AUTOSTART", "0") not in {"1", "true", "yes"}:
        return
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1):
            return
    except (urllib.error.URLError, TimeoutError):
        pass
    starter = root / "scripts" / "start-ollama-local.sh"
    if not starter.exists():
        return
    log_dir = root / PROJECT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = (log_dir / "ollama.log").open("ab")
    subprocess.Popen([starter.as_posix()], cwd=root, stdout=log_file, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(10):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1):
                return
        except (urllib.error.URLError, TimeoutError):
            continue


def normalize_router_actions(raw_actions: Any) -> list[dict[str, Any]]:
    allowed = {
        "local": {"context", "handoff", "memory", "summarize", "review", "classify"},
        "claude": {"planner", "reviewer"},
        "codex": {"executor", "reviewer"},
        "gemini": {"reviewer", "planner"},
    }
    actions: list[dict[str, Any]] = []
    if isinstance(raw_actions, list):
        for item in raw_actions:
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider", "")).strip().lower()
            role = str(item.get("role", "")).strip().lower()
            if "/" in provider:
                provider_part, role_part = provider.split("/", 1)
                provider = provider_part.strip()
                role = role or role_part.strip()
            if provider in allowed and role in allowed[provider]:
                actions.append(
                    {
                        "provider": provider,
                        "role": role,
                        "reason": str(item.get("reason", "")),
                        "execute": False,
                    }
                )
    if not actions:
        actions = [
            {"provider": "local", "role": "context", "reason": "Prepare compact context.", "execute": False},
            {"provider": "claude", "role": "planner", "reason": "Plan and identify risks.", "execute": False},
            {"provider": "codex", "role": "executor", "reason": "Prepare implementation handoff.", "execute": False},
            {"provider": "gemini", "role": "reviewer", "reason": "Prepare alternate review.", "execute": False},
        ]
    deduped: list[dict[str, Any]] = []
    seen = set()
    for action in actions:
        key = (action["provider"], action["role"])
        if key not in seen:
            seen.add(key)
            deduped.append(action)
    return deduped[:6]


def heuristic_route_prompt(prompt: str) -> dict[str, Any]:
    lowered = prompt.lower()
    actions = [{"provider": "local", "role": "context", "reason": "Prepare context before provider handoff.", "execute": False}]
    intent = "planning"
    if any(token in lowered for token in ["summarize", "summary", "요약", "로그 정리", "정리해줘"]):
        intent = "local_task"
        actions = [
            {"provider": "local", "role": "summarize", "reason": "Cheap local summary task.", "execute": False}
        ]
    elif any(token in lowered for token in ["classify", "classification", "분류", "라벨", "label"]):
        intent = "local_task"
        actions = [
            {"provider": "local", "role": "classify", "reason": "Cheap local classification task.", "execute": False}
        ]
    elif any(token in lowered for token in ["handoff draft", "handoff", "인수인계", "작업지시"]):
        intent = "local_task"
        actions = [
            {"provider": "local", "role": "handoff", "reason": "Draft a local handoff before provider work.", "execute": False}
        ]
    elif any(token in lowered for token in ["debug", "trace", "왜", "원인", "오류", "에러", "멈추", "안됨", "안 돼", "error", "exception"]):
        intent = "debugging"
        actions.extend(
            [
                {"provider": "claude", "role": "planner", "reason": "Diagnose root cause.", "execute": False},
                {"provider": "local", "role": "review", "reason": "First-pass log scan.", "execute": False},
            ]
        )
    elif any(token in lowered for token in ["implement", "fix", "build", "code", "tui", "cli", "bug",
                                          "구현", "수정", "만들", "고쳐", "버그", "추가", "작성"]):
        intent = "implementation"
        actions.extend(
            [
                {"provider": "claude", "role": "planner", "reason": "Clarify plan and risks.", "execute": False},
                {"provider": "codex", "role": "executor", "reason": "Prepare implementation artifact.", "execute": False},
                {"provider": "gemini", "role": "reviewer", "reason": "Prepare independent review.", "execute": False},
            ]
        )
    elif any(token in lowered for token in ["refactor", "리팩토링", "리팩터", "정리", "개선", "cleanup"]):
        intent = "implementation"
        actions.extend(
            [
                {"provider": "claude", "role": "planner", "reason": "Clarify refactoring plan.", "execute": False},
                {"provider": "codex", "role": "executor", "reason": "Prepare refactoring implementation.", "execute": False},
            ]
        )
    elif any(token in lowered for token in ["review", "audit", "검토", "리뷰", "점검"]):
        intent = "review"
        actions.extend(
            [
                {"provider": "local", "role": "review", "reason": "First-pass risk scan.", "execute": False},
                {"provider": "claude", "role": "reviewer", "reason": "Conceptual risk review.", "execute": False},
                {"provider": "gemini", "role": "reviewer", "reason": "Alternate review.", "execute": False},
            ]
        )
    elif any(token in lowered for token in ["memory", "import", "parser", "메모리", "가져", "저장"]):
        intent = "memory_import"
        actions.extend(
            [
                {"provider": "local", "role": "memory", "reason": "Draft memory extraction.", "execute": False},
                {"provider": "codex", "role": "executor", "reason": "Prepare parser/import implementation.", "execute": False},
            ]
        )
    elif any(token in lowered for token in ["design", "architect", "설계", "아키텍처", "구조", "plan", "계획"]):
        intent = "planning"
        actions.extend(
            [
                {"provider": "claude", "role": "planner", "reason": "Lead design discussion.", "execute": False},
                {"provider": "gemini", "role": "reviewer", "reason": "Alternate design perspective.", "execute": False},
            ]
        )
    else:
        actions.append({"provider": "claude", "role": "planner", "reason": "Clarify ambiguous task.", "execute": False})
    return {
        "intent": intent,
        "summary": prompt.strip()[:200],
        "complexity": "default",
        "actions": actions,
        "risks": [],
        "open_questions": [],
        "confidence": 0.45,
        "should_escalate": True,
        "escalation_reason": "Heuristic fallback is less reliable than local intent router.",
    }


def update_state(paths: RunPaths, **updates: Any) -> dict[str, Any]:
    state = json.loads(paths.state.read_text(encoding="utf-8"))
    state.update(updates)
    state["updated_at"] = now_iso()
    write_json(paths.state, state)
    return state


def set_agent_status(paths: RunPaths, agent_name: str, status: str) -> dict[str, Any]:
    state = json.loads(paths.state.read_text(encoding="utf-8"))
    agents = state.get("agents") or []
    for agent in agents:
        if agent.get("name") == agent_name:
            agent["status"] = status
            break
    else:
        agents.append({"name": agent_name, "status": status})
    state["agents"] = agents
    state["updated_at"] = now_iso()
    write_json(paths.state, state)
    return state


def append_event(paths: RunPaths, event_type: str, payload: dict[str, Any] | None = None) -> None:
    payload = payload or {}
    event = {"ts": now_iso(), "type": event_type, "run_id": paths.run_id, **payload}
    with paths.events.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    update_state(paths, latest_event=event_type)
    append_transcript(paths, "Event", f"{event_type} {json.dumps(payload, ensure_ascii=False, sort_keys=True)}")


def append_hive_activity(
    paths: RunPaths,
    actor: str,
    action: str,
    summary: str,
    payload: dict[str, Any] | None = None,
) -> None:
    payload = payload or {}
    event = {
        "ts": now_iso(),
        "run_id": paths.run_id,
        "actor": actor,
        "action": action,
        "summary": summary,
        "payload": payload,
    }
    with paths.hive_events.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    append_transcript(paths, "Hive", f"{actor} {action}: {summary}")


def append_agent_log(paths: RunPaths, agent: str, role: str, message: str) -> Path:
    agent_dir = paths.run_dir / "agents" / agent
    agent_dir.mkdir(parents=True, exist_ok=True)
    log_path = agent_dir / f"{role.replace('-', '_')}.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{now_iso()} {message.rstrip()}\n")
    append_hive_activity(
        paths,
        f"{agent}/{role}",
        "log",
        message.strip()[:240],
        {"log": log_path.relative_to(paths.root).as_posix() if log_path.is_relative_to(paths.root) else log_path.as_posix()},
    )
    return log_path


def append_transcript(paths: RunPaths, title: str, body: str) -> None:
    if not paths.transcript.exists():
        paths.transcript.write_text(f"# Transcript: {paths.run_id}\n\n", encoding="utf-8")
    with paths.transcript.open("a", encoding="utf-8") as f:
        f.write(f"## {now_iso()} - {title}\n")
        f.write(body.rstrip() + "\n\n")


def read_transcript(root: Path, run_id: str | None = None, tail: int = 80) -> str:
    paths, _ = load_run(root, run_id)
    ensure_transcript(paths)
    if not paths.transcript.exists():
        return f"No transcript yet: {paths.transcript}"
    lines = paths.transcript.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-tail:]) + "\n"


def ensure_transcript(paths: RunPaths) -> None:
    if paths.transcript.exists():
        return
    paths.transcript.write_text(
        f"# Transcript: {paths.run_id}\n\n"
        f"## {now_iso()} - Transcript\n"
        "Created transcript for existing run.\n\n",
        encoding="utf-8",
    )


def read_events(paths: RunPaths, limit: int = 20) -> list[dict[str, Any]]:
    if not paths.events.exists():
        return []
    rows = []
    for line in paths.events.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"type": "malformed_event", "raw": line})
    return rows[-limit:]


def read_hive_activity(paths: RunPaths, limit: int = 20) -> list[dict[str, Any]]:
    if not paths.hive_events.exists():
        return []
    rows = []
    for line in paths.hive_events.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"actor": "system", "action": "malformed_activity", "summary": line})
    return rows[-limit:]


def format_hive_activity(root: Path, run_id: str | None = None, limit: int = 30) -> str:
    paths, _ = load_run(root, run_id)
    rows = read_hive_activity(paths, limit=limit)
    lines = [f"Hive Mind Activity: {paths.run_id}", ""]
    if not rows:
        lines.append("No hive activity yet.")
        return "\n".join(lines)
    for row in rows:
        ts = short_timestamp(str(row.get("ts", "")))
        actor = row.get("actor", "system")
        action = row.get("action", "event")
        summary = row.get("summary", "")
        lines.append(f"{ts}  {actor:<18} {action:<20} {summary}")
    return "\n".join(lines)


def short_timestamp(ts: str) -> str:
    if "T" in ts:
        return ts.split("T", 1)[1].split("+", 1)[0]
    return ts


def invoke_local(root: Path, role: str, run_id: str | None = None, complexity: str = "default") -> Path:
    paths, state = load_run(root, run_id)
    role_to_worker = {
        "context": "context_compressor",
        "context-compressor": "context_compressor",
        "handoff": "handoff_drafter",
        "handoff-drafter": "handoff_drafter",
        "summarize": "log_summarizer",
        "log-summarizer": "log_summarizer",
        "memory": "memory_extractor",
        "memory-curator": "memory_extractor",
        "review": "diff_reviewer",
        "diff-reviewer": "diff_reviewer",
        "classify": "classifier",
        "json": "json_normalizer",
        "json-normalizer": "json_normalizer",
        "normalize": "json_normalizer",
    }
    worker = role_to_worker.get(role)
    if not worker:
        available = ", ".join(sorted(role_to_worker))
        raise ValueError(f"Unknown local role '{role}'. Available: {available}")

    input_path = choose_local_input(paths, role)
    input_text, source_ref = read_input(input_path, 12000)
    agent_name = local_agent_name(role)
    model = choose_model(worker, complexity)
    set_agent_status(paths, agent_name, "running")
    append_agent_log(paths, "local", role, f"started worker={worker} model={model} source={source_ref}")
    append_event(paths, "agent_started", {"agent": "local", "role": role, "worker": worker})
    local_runtime = local_runtime_report(root, write=True).get("active_backend", "none")
    started_at = now_iso()
    started = time.monotonic()
    try:
        worker_output = run_worker(worker, input_text, model=model, runtime=local_runtime, source_ref=source_ref)
        validation = validate_worker_result(worker, worker_output)
        finished_at = now_iso()
        duration_ms = int((time.monotonic() - started) * 1000)
        result = {
            "schema_version": 1,
            "agent": "local",
            "role": role,
            "status": "completed",
            "provider_mode": "local_runtime",
            "runtime": worker_output.get("runtime", os.environ.get("HIVE_LOCAL_BACKEND", "auto")),
            "worker": worker,
            "model": model,
            "source_ref": source_ref,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": duration_ms,
            "output_valid": validation["valid"],
            "output_issues": validation["issues"],
            "confidence": validation["confidence"],
            "should_escalate": validation["should_escalate"],
            "escalation_reason": validation["escalation_reason"],
            "artifacts_created": [],
            "output": worker_output,
        }
        event_type = "agent_completed"
        agent_status = "completed"
        run_status = "in_progress"
    except Exception as exc:
        finished_at = now_iso()
        duration_ms = int((time.monotonic() - started) * 1000)
        result = {
            "schema_version": 1,
            "agent": "local",
            "role": role,
            "status": "failed",
            "provider_mode": "local_runtime",
            "runtime": local_runtime,
            "worker": worker,
            "model": model,
            "source_ref": source_ref,
            "started_at": started_at,
            "finished_at": finished_at,
            "duration_ms": duration_ms,
            "output_valid": False,
            "output_issues": [str(exc)],
            "confidence": 0.0,
            "should_escalate": True,
            "escalation_reason": str(exc),
            "error": str(exc),
            "needs_followup": True,
            "artifacts_created": [],
        }
        event_type = "agent_failed"
        agent_status = "failed"
        run_status = "needs_attention"
    out_path = paths.local_dir / f"{role.replace('-', '_')}.json"
    result["artifacts_created"] = [out_path.relative_to(root).as_posix()]
    write_json(out_path, result)
    append_agent_log(paths, "local", role, f"{agent_status} artifact={out_path.relative_to(root).as_posix()}")
    append_transcript(paths, "Ran", f"`hive invoke local --role {role}` -> `{out_path.relative_to(root).as_posix()}` status={agent_status}")
    set_agent_status(paths, agent_name, agent_status)
    append_event(
        paths,
        event_type,
        {"agent": "local", "role": role, "worker": worker, "artifact": out_path.relative_to(root).as_posix()},
    )
    update_state(paths, phase="local", status=run_status)
    return out_path


EXTERNAL_AGENT_ROLES: dict[str, set[str]] = {
    "claude": {"planner", "reviewer", "claim-auditor", "debate_initial", "debate_review"},
    "codex": {"executor", "reviewer", "debate_initial", "debate_review"},
    "gemini": {"reviewer", "planner", "alternate-planner", "multimodal-reviewer", "debate_initial", "debate_review"},
}

PROVIDER_PASSTHROUGH_AGENTS = {"claude", "codex", "gemini"}


def invoke_external_agent(
    root: Path,
    agent: str,
    role: str,
    run_id: str | None = None,
    execute: bool = False,
) -> Path:
    paths, state = load_run(root, run_id)
    ensure_memoryos_context(root, paths.run_id)
    ensure_capabilityos_recommendation(root, paths.run_id)
    paths, state = load_run(root, paths.run_id)
    if agent not in EXTERNAL_AGENT_ROLES:
        raise ValueError(f"external agent must be one of: {', '.join(sorted(EXTERNAL_AGENT_ROLES))}")
    allowed_roles = EXTERNAL_AGENT_ROLES[agent]
    if role not in allowed_roles:
        raise ValueError(f"role '{role}' not valid for {agent}; allowed: {', '.join(sorted(allowed_roles))}")
    agent_dir = {"claude": paths.claude_dir, "codex": paths.codex_dir, "gemini": paths.gemini_dir}[agent]
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_name = f"{agent}-{role}"
    prompt_path = agent_dir / f"{role}_prompt.md"
    prompt_path.write_text(build_external_prompt(paths, state, agent, role), encoding="utf-8")
    append_agent_log(paths, agent, role, f"prompt_created artifact={prompt_path.relative_to(root).as_posix()}")
    append_transcript(paths, "Edited", f"`{prompt_path.relative_to(root).as_posix()}` for {agent}/{role}")
    set_agent_status(paths, agent_name, "ready")
    append_event(
        paths,
        "agent_prompt_created",
        {"agent": agent, "role": role, "artifact": prompt_path.relative_to(root).as_posix()},
    )
    update_state(paths, phase="handoff", status="ready")

    if not execute:
        command_path = agent_dir / f"{role}_command.txt"
        command_path.write_text(suggest_external_command(agent, prompt_path, root), encoding="utf-8")
        result_path = agent_dir / f"{role}_result.yaml"
        provider = detect_agents(root, write=True)["providers"].get(agent, {})
        result = provider_result_record(
            root,
            agent=agent,
            role=role,
            status="prepared",
            provider_mode=provider.get("mode", "prepare_only"),
            permission_mode=role_permission_mode(agent, role),
            prompt_path=prompt_path,
            command_path=command_path,
            execute=False,
            provider_status=provider.get("status", "unknown"),
        )
        result_path.write_text(format_simple_yaml(result), encoding="utf-8")
        append_agent_log(paths, agent, role, f"prepared result={result_path.relative_to(root).as_posix()} mode={result['provider_mode']}")
        append_transcript(paths, "Prepared", f"{agent}/{role} -> `{result_path.relative_to(root).as_posix()}`")
        set_agent_status(paths, agent_name, "prepared")
        append_event(paths, "agent_prepared", {"agent": agent, "role": role, "artifact": result_path.relative_to(root).as_posix()})
        return result_path

    output_path = agent_dir / f"{role}_output.md"
    result_path = agent_dir / f"{role}_result.yaml"
    if agent == "codex":
        command_path = agent_dir / f"{role}_command.txt"
        command_path.write_text(suggest_external_command(agent, prompt_path, root), encoding="utf-8")
        result = provider_result_record(
            root,
            agent=agent,
            role=role,
            status="failed",
            provider_mode="prepare_only",
            permission_mode=role_permission_mode(agent, role),
            prompt_path=prompt_path,
            command_path=command_path,
            execute=False,
            reason="codex execution is disabled until the non-interactive CLI contract is stable",
            risk_level="medium",
        )
        result_path.write_text(format_simple_yaml(result), encoding="utf-8")
        append_agent_log(paths, agent, role, f"blocked prepare_only result={result_path.relative_to(root).as_posix()}")
        append_transcript(paths, "Prepared", f"{agent}/{role} blocked as prepare-only -> `{result_path.relative_to(root).as_posix()}`")
        set_agent_status(paths, agent_name, "failed")
        append_event(paths, "agent_failed", {"agent": agent, "role": role, "artifact": result_path.relative_to(root).as_posix()})
        update_state(paths, phase="handoff", status="needs_attention")
        return result_path

    # Policy gate: danger_modes must be explicitly enabled before execute path.
    policy = load_policy(root)
    danger = policy.get("danger_modes") or {}
    if danger.get("allowed") is not True:
        reason = (
            f"Execute mode for {agent}/{role} requires danger_modes: allowed: true "
            f"in .hivemind/policy.yaml. "
            f"Required flags per policy: {danger.get('require_flags', [])}. "
            f"See: hive policy explain {agent}.{role}"
        )
        result = provider_result_record(
            root, agent=agent, role=role, status="failed",
            provider_mode="policy_blocked", permission_mode=role_permission_mode(agent, role),
            prompt_path=prompt_path, reason=reason, risk_level="high",
        )
        result_path.write_text(format_simple_yaml(result), encoding="utf-8")
        set_agent_status(paths, agent_name, "failed")
        append_event(paths, "agent_failed", {"agent": agent, "role": role, "reason": "policy_blocked"})
        update_state(paths, phase="handoff", status="needs_attention")
        raise PermissionError(reason)

    agent_bin = resolve_provider_binary(root, agent)
    if not agent_bin:
        result = provider_result_record(
            root,
            agent=agent,
            role=role,
            status="failed",
            provider_mode="unavailable",
            permission_mode=role_permission_mode(agent, role),
            prompt_path=prompt_path,
            reason=f"{agent} binary not found",
            risk_level="medium",
        )
        result_path.write_text(format_simple_yaml(result), encoding="utf-8")
        append_agent_log(paths, agent, role, f"failed unavailable result={result_path.relative_to(root).as_posix()}")
        append_transcript(paths, "Prepared", f"{agent}/{role} unavailable -> `{result_path.relative_to(root).as_posix()}`")
        set_agent_status(paths, agent_name, "failed")
        append_event(paths, "agent_failed", {"agent": agent, "role": role, "artifact": result_path.relative_to(root).as_posix()})
        update_state(paths, phase="handoff", status="needs_attention")
        return result_path

    set_agent_status(paths, agent_name, "running")
    append_agent_log(paths, agent, role, f"started execute binary={agent_bin}")
    append_event(paths, "agent_started", {"agent": agent, "role": role})
    command, stdin_text = external_command(agent, agent_bin, prompt_path.read_text(encoding="utf-8"))
    started = time.monotonic()
    started_at = now_iso()
    returncode = run_provider_with_live_log(paths, root, agent, role, command, output_path, timeout=600, stdin_text=stdin_text)
    finished_at = now_iso()
    duration_ms = int((time.monotonic() - started) * 1000)
    append_agent_log(
        paths,
        agent,
        role,
        f"{'completed' if returncode == 0 else 'failed'} returncode={returncode} output={output_path.relative_to(root).as_posix()}",
    )
    status = "completed" if returncode == 0 else "failed"
    result = provider_result_record(
        root,
        agent=agent,
        role=role,
        status=status,
        provider_mode="execute_supported",
        permission_mode=role_permission_mode(agent, role),
        prompt_path=prompt_path,
        output_path=output_path,
        returncode=returncode,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        commands_run=[" ".join(shlex.quote(part) for part in command)],
        artifacts_created=[result_path.relative_to(root).as_posix(), output_path.relative_to(root).as_posix()],
        risk_level="low" if status == "completed" else "medium",
    )
    result_path.write_text(format_simple_yaml(result), encoding="utf-8")
    append_transcript(paths, "Ran", f"{agent}/{role} execute -> `{result_path.relative_to(root).as_posix()}` status={status}")
    set_agent_status(paths, agent_name, status)
    append_event(paths, f"agent_{status}", {"agent": agent, "role": role, "artifact": result_path.relative_to(root).as_posix()})
    update_state(paths, phase="handoff", status="in_progress" if status == "completed" else "needs_attention")
    return result_path


def provider_passthrough(
    root: Path,
    agent: str,
    native_args: list[str],
    *,
    run_id: str | None = None,
    execute: bool = False,
    timeout: int = 600,
    allow_workspace_write: bool = False,
    workspace_write_grant: str | None = None,
    allow_dangerous_full_access: bool = False,
    dangerous_grant: str | None = None,
) -> Path:
    """Backward-compatible wrapper for the extracted provider passthrough module."""
    from .provider_passthrough import provider_passthrough as run_provider_passthrough

    return run_provider_passthrough(
        root,
        agent,
        native_args,
        run_id=run_id,
        execute=execute,
        timeout=timeout,
        allow_workspace_write=allow_workspace_write,
        workspace_write_grant=workspace_write_grant,
        allow_dangerous_full_access=allow_dangerous_full_access,
        dangerous_grant=dangerous_grant,
    )


def role_permission_mode(agent: str, role: str) -> str:
    if agent == "claude":
        return "plan"
    if agent == "codex" and role == "executor":
        return "workspace_write_with_policy"
    if agent == "codex":
        return "read_only"
    if agent == "gemini":
        return "read_only"
    return "draft_only"


def run_provider_with_live_log(
    paths: RunPaths,
    root: Path,
    agent: str,
    role: str,
    command: list[str],
    output_path: Path,
    timeout: int,
    stdin_text: str | None = None,
) -> int:
    deadline = time.monotonic() + timeout
    with output_path.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            command,
            cwd=root,
            text=True,
            stdin=subprocess.PIPE if stdin_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        assert process.stdout is not None
        if stdin_text is not None and process.stdin is not None:
            process.stdin.write(stdin_text)
            process.stdin.close()
        try:
            for line in process.stdout:
                output.write(line)
                output.flush()
                clean = line.strip()
                if clean:
                    append_agent_log(paths, agent, role, f"stdout {clean[:220]}")
                if time.monotonic() > deadline:
                    process.kill()
                    append_agent_log(paths, agent, role, f"timeout after {timeout}s")
                    return process.wait()
            return process.wait()
        finally:
            if process.poll() is None:
                process.kill()


def build_verification(root: Path, run_id: str | None = None) -> Path:
    paths, _ = load_run(root, run_id)
    ensure_transcript(paths)
    report = validate_run_artifacts(paths.run_dir, root)
    out_path = paths.run_dir / "verification.yaml"
    out_path.write_text(format_simple_yaml(report), encoding="utf-8")
    append_transcript(paths, "Ran", f"`hive verify` -> `{out_path.relative_to(root).as_posix()}` verdict={report.get('verdict')}")
    append_event(paths, "verification_created", {"artifact": out_path.relative_to(root).as_posix()})
    set_agent_status(paths, "verifier", "completed")
    update_state(paths, phase="verification", status="needs_review")
    return out_path


def build_memory_draft(root: Path, run_id: str | None = None) -> Path:
    paths, state = load_run(root, run_id)
    draft = {
        "type": "artifact",
        "content": f"Run {paths.run_id} created structured blackboard artifacts for: {state.get('user_request')}",
        "origin": "mixed",
        "project": state.get("project", "Hive Mind"),
        "confidence": 0.8,
        "status": "draft",
        "raw_refs": [paths.final_report.relative_to(root).as_posix(), paths.events.relative_to(root).as_posix()],
    }
    out_path = paths.run_dir / "memory_drafts.json"
    write_json(out_path, {"memory_drafts": [draft]})
    append_transcript(paths, "Edited", f"`{out_path.relative_to(root).as_posix()}` with 1 memory draft")
    append_event(paths, "memory_drafts_created", {"count": 1, "artifact": out_path.relative_to(root).as_posix()})
    return out_path


def build_summary(root: Path, run_id: str | None = None) -> Path:
    paths, state = load_run(root, run_id)
    events = read_events(paths, limit=50)
    lines = [
        f"# Final Report: {paths.run_id}",
        "",
        f"- Task: {state.get('user_request')}",
        f"- Project: {state.get('project')}",
        f"- Status: {state.get('status')}",
        f"- Phase: {state.get('phase')}",
        "",
        "## Artifacts",
    ]
    for name, rel_path in (state.get("artifacts") or {}).items():
        lines.append(f"- {name}: `{rel_path}`")
    lines.extend(["", "## Recent Events"])
    for event in events:
        lines.append(f"- {event.get('ts')} `{event.get('type')}`")
    paths.final_report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    append_transcript(paths, "Edited", f"`{paths.final_report.relative_to(root).as_posix()}` summary")
    append_event(paths, "summary_created", {"artifact": paths.final_report.relative_to(root).as_posix()})
    return paths.final_report


def build_external_prompt(paths: RunPaths, state: dict[str, Any], agent: str, role: str) -> str:
    events = paths.events.read_text(encoding="utf-8") if paths.events.exists() else ""
    context = paths.context_pack.read_text(encoding="utf-8") if paths.context_pack.exists() else ""
    handoff = paths.handoff.read_text(encoding="utf-8") if paths.handoff.exists() else ""
    local_context = ""
    local_context_path = paths.local_dir / "context.json"
    if local_context_path.exists():
        local_context = local_context_path.read_text(encoding="utf-8", errors="replace")[-8000:]
    capability_recommendation = state.get("capability_recommendation")
    capability_bridge = state.get("capability_bridge") if isinstance(state.get("capability_bridge"), dict) else {}
    capability_context = {
        "bridge_status": capability_bridge.get("bridge_status"),
        "status": capability_bridge.get("status"),
        "reason": capability_bridge.get("reason"),
        "recommendation": capability_recommendation if isinstance(capability_recommendation, dict) else None,
        "authority": "recommendation_only; Hive Mind keeps execution authority",
    }
    role_contract = {
        "planner": "Create a concise implementation handoff with risks, files, acceptance criteria, and unresolved questions.",
        "reviewer": "Review the current run artifacts for risk, missing tests, overclaims, and next actions.",
        "executor": "Implement only the scoped task. Update result artifacts with changed files, commands, and unresolved issues.",
        "debate_initial": "Give your independent position on the debate topic. Include assumptions, risks, and what would change your mind.",
        "debate_review": "Review the first-round debate snapshot. Name agreements, disagreements, weak evidence, and the best convergence point.",
    }.get(role, "Work only through structured artifacts and return a concise result.")
    return (
        f"# Hive Mind Harness Prompt\n\n"
        f"Agent: {agent}\n"
        f"Role: {role}\n"
        f"Run: {paths.run_id}\n"
        f"Task: {state.get('user_request')}\n\n"
        f"## Contract\n{role_contract}\n\n"
        "Do not bypass the harness. Treat files under this run folder as the communication boundary.\n"
        "Prefer structured outputs that can be saved as handoff/result/verification artifacts.\n\n"
        f"## Required Output\n"
        "- Summary\n"
        "- Decisions or recommendations\n"
        "- Risks / missing evidence\n"
        "- Next concrete action\n"
        "- Artifact updates needed\n\n"
        f"## Context Pack\n{context}\n\n"
        f"## Local Context Worker Output\n```json\n{local_context}\n```\n\n"
        f"## CapabilityOS Recommendation\n```json\n{json.dumps(capability_context, ensure_ascii=False, indent=2, sort_keys=True)}\n```\n\n"
        f"## Current Handoff\n```yaml\n{handoff}\n```\n\n"
        f"## Recent Events\n```jsonl\n{events[-8000:]}\n```\n"
    )


def resolve_provider_binary(root: Path, agent: str) -> str | None:
    provider = detect_agents(root, write=True)["providers"].get(agent, {})
    return provider.get("path") or shutil.which(agent)


def load_operator_method_profile(root: Path) -> str:
    candidates = [
        root / "docs" / "OPERATOR_METHOD_PROFILE.md",
        root / "docs" / "HIVE_WORKING_METHOD.md",
    ]
    for path in candidates:
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            return text[:5000]
    return (
        "Classify intent first, decompose into concrete tasks, preserve disagreement, "
        "let Claude critique/planning and Codex execution stay separate, verify with commands, "
        "then write memory-ready artifacts."
    )


def load_router_method_profile() -> str:
    return (
        "- Classify intent before choosing providers.\n"
        "- Keep provider execution prepare-only unless explicitly requested.\n"
        "- Use local/context for context compression, not final judgment.\n"
        "- Use claude/planner for ambiguous plans, risks, and claim discipline.\n"
        "- Use codex/executor only when implementation is clearly needed.\n"
        "- Use gemini/reviewer for optional independent review.\n"
        "- Preserve disagreement and route risky decisions to review.\n"
        "- Return the smallest useful action list."
    )


def suggest_external_command(agent: str, prompt_path: Path, root: Path | None = None) -> str:
    binary = resolve_provider_binary(root, agent) if root else shutil.which(agent)
    cmd = shlex.quote(binary or agent)
    prompt = shlex.quote(prompt_path.as_posix())
    if agent == "claude":
        return f"{cmd} -p \"$(cat {prompt})\" --permission-mode plan --output-format text\n"
    if agent == "gemini":
        return f"{cmd} -p \"$(cat {prompt})\" --approval-mode plan --output-format text --skip-trust\n"
    return f"{cmd} exec --cd . --sandbox read-only --ask-for-approval never \"$(cat {prompt})\"\n"


def external_command(agent: str, binary: str, prompt: str) -> tuple[list[str], str | None]:
    """Return (argv, stdin_text). stdin_text is None when prompt is passed as an arg."""
    if agent == "claude":
        # Pass prompt via stdin to avoid ARG_MAX issues and --permission-mode plan
        # blocking on approval prompts in non-TTY mode (produces empty output).
        return ([binary, "--dangerously-skip-permissions", "--output-format", "text"], prompt)
    if agent == "gemini":
        return ([binary, "-p", prompt, "--approval-mode", "plan", "--output-format", "text", "--skip-trust"], None)
    if agent == "codex":
        return ([binary, "exec", "--cd", ".", "--sandbox", "read-only", "--ask-for-approval", "never", prompt], None)
    raise ValueError(f"Unsupported executable external agent: {agent}")


def choose_local_input(paths: RunPaths, role: str) -> Path:
    if role in {"context", "context-compressor", "memory", "memory-curator", "classify", "json", "json-normalizer", "normalize"}:
        return paths.context_pack
    if role in {"handoff", "handoff-drafter"}:
        return paths.task
    if role in {"review", "diff-reviewer"} and (paths.artifacts / "git_diff.patch").exists():
        return paths.artifacts / "git_diff.patch"
    if role in {"summarize", "log-summarizer", "review", "diff-reviewer"}:
        return paths.events
    return paths.task


def local_agent_name(role: str) -> str:
    return {
        "context": "local-context-compressor",
        "context-compressor": "local-context-compressor",
        "handoff": "local-handoff-drafter",
        "handoff-drafter": "local-handoff-drafter",
        "summarize": "local-log-summarizer",
        "log-summarizer": "local-log-summarizer",
        "memory": "local-memory-curator",
        "memory-curator": "local-memory-curator",
        "review": "local-diff-reviewer",
        "diff-reviewer": "local-diff-reviewer",
        "classify": "local-classifier",
        "json": "local-json-normalizer",
        "json-normalizer": "local-json-normalizer",
        "normalize": "local-json-normalizer",
    }.get(role, f"local-{role}")


def make_run_id(user_request: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = stable_id("r", user_request, stamp).split("_", 1)[1][:6]
    return f"run_{stamp}_{suffix}"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def format_task_yaml(state: dict[str, Any]) -> str:
    return (
        f"run_id: {state['run_id']}\n"
        f"user_request: {json.dumps(state['user_request'], ensure_ascii=False)}\n"
        f"project: {state['project']}\n"
        f"task_type: {state['task_type']}\n"
        "goal: \"Clarify, execute, verify, and preserve this task through structured artifacts.\"\n"
        "priority: high\n"
        f"status: {state['status']}\n"
    )


def default_context_pack(state: dict[str, Any], root: Path | None = None) -> str:
    sections: list[str] = [
        "# Context Pack\n",
        "## User Request",
        state["user_request"],
        "",
    ]
    if root is not None:
        file_lines = _scan_project_files(root)
        if file_lines:
            sections.append("## Project Files")
            sections.extend(file_lines)
            sections.append("")
        git_summary = _git_status_summary(root)
        if git_summary:
            sections.append("## Git Status")
            sections.append(git_summary)
            sections.append("")
    sections.extend([
        "## Active Decisions",
        "- Agents communicate through artifacts, not direct free-form chat.",
        "- Every task should have a run_id and event log.",
        "- Local LLMs summarize and draft; Claude/Codex handle judgment and implementation.",
        "",
        "## Open Questions",
        "- Which artifacts need human approval before memory commit?",
    ])
    return "\n".join(sections) + "\n"


def _scan_project_files(root: Path, max_files: int = 40) -> list[str]:
    skip_dirs = {".git", ".runs", "__pycache__", ".mypy_cache", ".pytest_cache", "node_modules", ".venv", "venv", "dist", "build", ".eggs", "*.egg-info"}
    interesting_exts = {".py", ".md", ".yaml", ".yml", ".toml", ".json", ".txt", ".sh"}
    entries: list[tuple[int, str]] = []
    try:
        for path in sorted(root.rglob("*")):
            if path.is_dir():
                continue
            parts = path.parts
            if any(p.startswith(".") and p not in (".runs",) or p in skip_dirs for p in parts[len(root.parts):]):
                continue
            if path.suffix.lower() not in interesting_exts:
                continue
            try:
                size = path.stat().st_size
            except OSError:
                continue
            rel = path.relative_to(root).as_posix()
            entries.append((size, rel))
            if len(entries) >= max_files * 3:
                break
    except Exception:
        return []
    entries.sort(key=lambda x: x[1])
    lines = []
    for size, rel in entries[:max_files]:
        kb = size / 1024
        lines.append(f"- {rel} ({kb:.1f}KB)")
    if len(entries) > max_files:
        lines.append(f"... and {len(entries) - max_files} more files")
    return lines


def _git_status_summary(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=root, text=True, capture_output=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            return "\n".join(lines[:20])
    except Exception:
        pass
    return ""


def default_handoff_yaml(state: dict[str, Any]) -> str:
    return (
        "from_agent: harness\n"
        "to_agent: codex\n"
        f"objective: {json.dumps(state['user_request'], ensure_ascii=False)}\n"
        "constraints:\n"
        "  - Use structured artifacts for handoff and results.\n"
        "  - Preserve run_id and event log for traceability.\n"
        "  - Do not auto-commit memory drafts without review.\n"
        "acceptance_criteria:\n"
        "  - Required run artifacts exist.\n"
        "  - Events record meaningful state transitions.\n"
        "  - Final report summarizes outcome and unresolved work.\n"
    )


def default_final_report(state: dict[str, Any]) -> str:
    return (
        f"# Final Report: {state['run_id']}\n\n"
        f"- Task: {state['user_request']}\n"
        "- Status: planned\n\n"
        "## Recent Events\n"
    )


def default_verification_yaml(state: dict[str, Any]) -> str:
    return (
        "schema_version: 1\n"
        f"run_id: {json.dumps(state['run_id'])}\n"
        "verdict: \"not_run\"\n"
        "checks: {}\n"
        "issues: []\n"
        "event_taxonomy: []\n"
        "risk_level: \"unknown\"\n"
    )


def default_global_config(root: Path) -> str:
    return (
        "version: 1\n"
        "mode: local_first\n"
        f"default_project_root: {json.dumps(root.as_posix())}\n"
        "raw_exports_policy: local_only\n"
        "memory:\n"
        "  global_scope: true\n"
        "  project_scope: true\n"
        "providers:\n"
        "  detect_on_init: true\n"
    )


def default_project_yaml(root: Path) -> str:
    return (
        "version: 1\n"
        f"name: {json.dumps(root.name)}\n"
        f"root: {json.dumps(root.as_posix())}\n"
        "scope: project\n"
        "runs_dir: .runs\n"
        "memory_dir: memory\n"
        "ontology_dir: ontology\n"
    )


def default_agents_yaml() -> str:
    return (
        "version: 1\n"
        "agents:\n"
        "  claude:\n"
        "    role: planner_reviewer\n"
        "    mode: plan\n"
        "  codex:\n"
        "    role: executor\n"
        "    mode: read_only_until_approved\n"
        "  gemini:\n"
        "    role: alternate_reviewer\n"
        "    mode: plan\n"
        "  local:\n"
        "    role: worker_layer\n"
        "    mode: draft_only\n"
    )


def default_routing_yaml() -> str:
    return (
        "version: 1\n"
        "routes:\n"
        "  planner: claude\n"
        "  executor: codex\n"
        "  reviewer: gemini\n"
        "  context_compressor: local\n"
        "  memory_extractor: local\n"
        "  log_summarizer: local\n"
        "policy:\n"
        "  local_outputs_are_drafts: true\n"
        "  edit_capable_execution_requires_explicit_approval: true\n"
        "  destructive_commands_forbidden_by_default: true\n"
    )


def default_policy_yaml() -> str:
    return (
        "version: 1\n"
        "default:\n"
        "  repo_write: deny\n"
        "  shell: deny\n"
        "  memory_commit: deny\n"
        "  raw_export_access: deny\n"
        "roles:\n"
        "  user.director:\n"
        "    description: Final direction, taste, acceptance, and project boundary.\n"
        "    repo_read: allow\n"
        "    repo_write: allow_with_intent\n"
        "    memory_commit: approve_only\n"
        "  claude.planner:\n"
        "    repo_read: allow\n"
        "    repo_write: deny\n"
        "    memory_draft: allow\n"
        "    memory_commit: deny\n"
        "    default_mode: plan\n"
        "  codex.executor:\n"
        "    repo_read: allow\n"
        "    repo_write: allow_with_approval\n"
        "    shell: allowlist\n"
        "    memory_commit: deny\n"
        "    raw_export_access: deny\n"
        "    default_mode: workspace_write_with_policy\n"
        "  gemini.reviewer:\n"
        "    repo_read: allow\n"
        "    repo_write: deny\n"
        "    memory_commit: deny\n"
        "    default_mode: read_only\n"
        "  hive.verifier:\n"
        "    repo_read: allow\n"
        "    repo_write: deny\n"
        "    shell: allowlist\n"
        "    provider_cli_execute: deny\n"
        "    memory_commit: deny\n"
        "    default_mode: read_only_or_allowlisted_internal_actions\n"
        "  hive.product_evaluator:\n"
        "    repo_read: allow\n"
        "    repo_write: deny\n"
        "    provider_cli_execute: deny\n"
        "    memory_commit: deny\n"
        "    default_mode: read_only\n"
        "  persona.actual_user:\n"
        "    repo_read: allow\n"
        "    repo_write: deny\n"
        "    provider_cli_execute: deny\n"
        "    memory_commit: deny\n"
        "    default_mode: read_only_temp_workspace_smoke\n"
        "  local.context:\n"
        "    compress_context: allow\n"
        "    classify: allow\n"
        "    repo_write: deny\n"
        "    final_decision: deny\n"
        "  local.memory_extractor:\n"
        "    memory_draft: allow\n"
        "    repo_write: deny\n"
        "    memory_commit: deny\n"
        "danger_modes:\n"
        "  allowed: false\n"
        "  require_flags:\n"
        "    - --confirm-danger\n"
        "    - --isolated-worktree\n"
        "working_method:\n"
        f"  hidden_thread: {json.dumps(WORKING_METHOD_PHRASE)}\n"
        "  principle: user_direction_plus_claude_critique_plus_codex_execution_plus_local_drafts\n"
    )


def default_working_method_skill() -> str:
    return (
        "---\n"
        "name: hive-working-method\n"
        "description: Use when a Hive Mind run needs the native working method: user direction, Claude critique, Codex execution, local LLM draft work, policy gates, verification, and memory handoff.\n"
        "---\n\n"
        "# Hive Working Method\n\n"
        "This skill captures the operating pattern that Hive Mind should reproduce as product behavior.\n\n"
        "## Loop\n\n"
        "1. User sets direction, taste, acceptance, and boundary.\n"
        "2. Claude or planner role critiques assumptions, risks, and claim discipline.\n"
        "3. Codex or executor role edits files, runs checks, and records reproducible evidence.\n"
        "4. Local LLM roles classify, compress, draft memory, summarize logs, and escalate uncertainty.\n"
        "5. Hive Mind stores artifacts, policy decisions, disagreements, verification, and next actions.\n\n"
        "## Rules\n\n"
        "- Do not collapse critique into agreement.\n"
        "- Keep MemoryOS acceptance separate from Hive Mind memory drafts.\n"
        "- Keep CapabilityOS recommendations separate from execution results.\n"
        "- Treat prompt, routing, role, and skill mutations as proposals until reviewed.\n"
        "- Preserve the hidden product thread: evolution of Single Human Intelligence.\n"
    )


def default_project_readme() -> str:
    return (
        "# Project Hive Mind\n\n"
        "This directory stores project-local Hive Mind config, context, skills, and run references.\n\n"
        "Start with:\n\n"
        "```bash\n"
        "hive doctor\n"
        "hive run \"your task\"\n"
        "hive live\n"
        "```\n"
    )


def default_check_memory_policy() -> str:
    return (
        "---\n"
        "id: memory-policy\n"
        "title: Memory Draft Policy\n"
        "severity: medium\n"
        "type: run-artifact\n"
        "---\n\n"
        "# Memory Draft Policy\n\n"
        "Runs should keep memory updates as reviewable drafts. No run-derived memory should be accepted without review.\n"
    )


def default_check_no_raw_export_leak() -> str:
    return (
        "---\n"
        "id: no-raw-export-leak\n"
        "title: No Raw Export Leak\n"
        "severity: high\n"
        "type: privacy\n"
        "---\n\n"
        "# No Raw Export Leak\n\n"
        "Prompt, command, event, and result artifacts should not reference raw private exports under `data/`.\n"
    )


def default_check_implementation_handoff() -> str:
    return (
        "---\n"
        "id: implementation-handoff\n"
        "title: Implementation Handoff Completeness\n"
        "severity: medium\n"
        "type: run-artifact\n"
        "---\n\n"
        "# Implementation Handoff Completeness\n\n"
        "Implementation runs should have task, context, handoff, and Codex executor artifacts before execution.\n"
    )


def format_simple_yaml(data: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(data, dict):
        if not data:
            return f"{pad}{{}}"
        lines = []
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(format_simple_yaml(value, indent + 2))
            else:
                lines.append(f"{pad}{key}: {json.dumps(value, ensure_ascii=False)}")
        return "\n".join(lines)
    if isinstance(data, list):
        if not data:
            return f"{pad}[]"
        lines = []
        for value in data:
            if isinstance(value, (dict, list)):
                lines.append(f"{pad}-")
                lines.append(format_simple_yaml(value, indent + 2))
            else:
                lines.append(f"{pad}- {json.dumps(value, ensure_ascii=False)}")
        return "\n".join(lines)
    return f"{pad}{json.dumps(data, ensure_ascii=False)}"


def open_run_folder(paths: RunPaths) -> None:
    print(paths.run_dir)
    if os.environ.get("DISPLAY"):
        subprocess.Popen(
            ["xdg-open", str(paths.run_dir)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
