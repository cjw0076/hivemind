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
from pathlib import Path
from typing import Any

import yaml

from .local_workers import choose_model, read_input, run_worker, validate_worker_result, worker_route_table
from .run_validation import validate_run_artifacts
from .utils import now_iso, stable_id


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
            path.write_text(content, encoding="utf-8")
            created.append(path.as_posix())

    providers = detect_agents(root, write=True)
    local_runtime = local_runtime_report(root, write=True)
    settings_profile = write_settings_profile(root, providers=providers, local_runtime=local_runtime)
    report = doctor_report(root)
    return {
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
    ollama = local_runtime.get("ollama") or {}
    lines.extend(["", "Local Models:"])
    models = ollama.get("models") or []
    if models:
        for model in models:
            lines.append(f"✓ {model}")
    else:
        lines.append("○ no local model manifests found")
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
    lines.extend(
        [
            "",
            "Next:",
            "1. hive doctor",
            '2. hive run "your task"',
            "3. hive tui",
            "4. optional: eval \"$(hive settings shell)\"",
            "5. optional: hive local setup",
            "6. optional: hive mcp install --for all",
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
    paths.context_pack.write_text(default_context_pack(state), encoding="utf-8")
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
    paths = RunPaths(root=root, run_id=actual_run_id)
    if not paths.state.exists():
        raise FileNotFoundError(f"Run state not found: {paths.state}")
    return paths, json.loads(paths.state.read_text(encoding="utf-8"))


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
    heartbeat = lock.get("last_heartbeat_epoch")
    if not isinstance(heartbeat, (int, float)):
        return True
    return (now or time.time()) - float(heartbeat) > ttl_seconds


def list_runs(root: Path) -> list[dict[str, Any]]:
    runs_dir = root / RUNS_DIR
    if not runs_dir.exists():
        return []
    runs = []
    for state_path in sorted(runs_dir.glob("run_*/run_state.json"), reverse=True):
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
    if agent_status(state, "local-context-compressor") not in {"completed"}:
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
    runs_dir = init_harness(root)
    (runs_dir / CURRENT_FILE).write_text(run_id + "\n", encoding="utf-8")


def get_current(root: Path) -> str | None:
    current = root / RUNS_DIR / CURRENT_FILE
    if not current.exists():
        return None
    value = current.read_text(encoding="utf-8").strip()
    return value or None


def detect_agents(root: Path, write: bool = True) -> dict[str, Any]:
    init_harness(root)
    providers = {
        "claude": probe_command("claude", ["--version"], roles=["planner", "reviewer", "claim-auditor"]),
        "codex": probe_command("codex", ["--version"], roles=["executor", "test-fixer", "diff-reviewer"], mode="execute_supported"),
        "gemini": probe_command("gemini", ["--version"], roles=["reviewer", "alternate-planner", "multimodal-reviewer"]),
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
        "ollama": probe_binary_version("ollama", ["--version"]),
    }
    warnings = []
    if not gpus:
        warnings.append("no NVIDIA GPU detected through nvidia-smi")
    if runtime["node"].get("status") != "available":
        warnings.append("node is unavailable")
    if runtime["docker"].get("status") != "available":
        warnings.append("docker is unavailable")
    if runtime["ollama"].get("status") != "available":
        warnings.append("ollama binary is unavailable")
    ports = {
        "ollama": probe_tcp_port("127.0.0.1", 11434),
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
    ollama = local_runtime.get("ollama") or {}
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
                "available": selected in set(ollama.get("models") or []),
            }
        )
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "status": "ready" if ollama.get("models") else "needs_setup",
        "local_runtime": local_runtime,
        "role_assignments": role_assignments,
    }


def local_model_profile(root: Path, write: bool = True) -> dict[str, Any]:
    local_runtime = local_runtime_report(root, write=True)
    ollama = local_runtime.get("ollama") or {}
    present = set(ollama.get("models") or [])
    routes = worker_route_table()
    models: dict[str, dict[str, Any]] = {}
    for role, route in routes.items():
        model_names = route.get("models") or {}
        for complexity, model in model_names.items():
            item = models.setdefault(
                model,
                {
                    "available": model in present,
                    "recommended_roles": [],
                    "json_validity": None,
                    "latency_ms": None,
                    "benchmark_status": "not_run",
                },
            )
            item["recommended_roles"].append(f"{role}:{complexity}")
    profile = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "runtime": "ollama",
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
    limit: int = 4,
    timeout: int = 90,
    write: bool = True,
) -> dict[str, Any]:
    runtime = local_runtime_report(root, write=True)
    ollama = runtime.get("ollama") or {}
    available = list(ollama.get("models") or [])
    selected = models or available[:limit]
    results = []
    for model in selected:
        results.append(benchmark_ollama_model(model, timeout=timeout))
    valid = [item for item in results if item.get("json_valid")]
    report = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "runtime": "ollama",
        "server": ollama.get("server"),
        "status": "completed" if results else "needs_setup",
        "models_tested": selected,
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
                model_entry["json_validity"] = 1.0 if result.get("json_valid") else 0.0
                model_entry["latency_ms"] = result.get("latency_ms")
                model_entry["benchmark_status"] = result.get("status")
        write_json(project_dir / "local_model_profile.json", profile)
    return report


def benchmark_ollama_model(model: str, timeout: int = 90) -> dict[str, Any]:
    server_models = ollama_server_models()
    if server_models is not None and model not in server_models:
        return {
            "model": model,
            "status": "skipped_model_not_loaded",
            "latency_ms": 0,
            "json_valid": False,
            "parsed": {},
            "error": (
                f"{model} is not loaded in the running Ollama server. "
                "Start the workspace server with scripts/start-ollama-local.sh or pull/load the model first."
            ),
        }
    prompt = (
        "Return valid JSON only. No markdown. "
        'Use exactly this shape: {"ok": true, "task": "json_validity_smoke", "confidence": 0.75}.'
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.0, "num_predict": 80},
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
        return {
            "model": model,
            "status": "completed",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "json_valid": json_valid,
            "parsed": parsed,
            "raw_response": raw[:2000],
            "parse_error": parse_error,
            "error": parse_error,
        }
    except Exception as exc:
        return {
            "model": model,
            "status": "failed",
            "latency_ms": int((time.monotonic() - started) * 1000),
            "json_valid": False,
            "parsed": {},
            "raw_response": "",
            "parse_error": "",
            "error": str(exc),
        }


def ollama_server_models() -> list[str] | None:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as response:
            body = json.loads(response.read().decode("utf-8"))
        return [item.get("name", "") for item in body.get("models", []) if item.get("name")]
    except Exception:
        return None


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
        marker = "✓" if item.get("json_valid") else "!"
        lines.append(f"{marker} {item.get('model')}: {item.get('status')} latency_ms={item.get('latency_ms')} json_valid={item.get('json_valid')}")
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
                "Hive Mind owns orchestration, provider adapters, TUI, and run artifacts.",
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
    provider_results = []
    for result_path in sorted((paths.run_dir / "agents").glob("*/*_result.yaml")):
        data = safe_load_yaml(result_path)
        provider_results.append(
            {
                "path": result_path.relative_to(root).as_posix(),
                "agent": data.get("agent"),
                "role": data.get("role"),
                "status": data.get("status"),
                "risk_level": data.get("risk_level", "unknown"),
                "policy_violations": data.get("policy_violations") or [],
            }
        )
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


def workspace_layout_report(layout: str = "dev") -> dict[str, Any]:
    layouts = {
        "dev": [
            "hive board",
            "hive events --follow",
            "hive transcript --tui",
            "hive diff --tui",
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
        ollama = local_runtime.get("ollama") or {}
        lines.extend(["", "Models:", f"Ollama server: {ollama.get('server')}", f"Model source: {ollama.get('model_source')}"])
        for model in ollama.get("models") or []:
            lines.append(f"✓ {model}")
        if not ollama.get("models"):
            lines.append("○ no local model manifests found")
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


def read_ollama_manifest_models(root: Path) -> list[str]:
    manifests = root / ".local" / "ollama" / "models" / "manifests" / "registry.ollama.ai" / "library"
    if not manifests.exists():
        return []
    models = []
    for model_dir in sorted(path for path in manifests.iterdir() if path.is_dir()):
        for tag_path in sorted(path for path in model_dir.iterdir() if path.is_file()):
            models.append(f"{model_dir.name}:{tag_path.name}")
    return models


def local_runtime_report(root: Path, write: bool = False) -> dict[str, Any]:
    ollama = probe_ollama(root)
    recommended = ["qwen3:1.7b", "qwen3:8b", "deepseek-coder:6.7b", "deepseek-coder-v2:16b"]
    present = set(ollama.get("models") or [])
    missing = [model for model in recommended if model not in present]
    report = {
        "generated_at": now_iso(),
        "ollama": ollama,
        "recommended_models": recommended,
        "missing_recommended_models": missing,
        "open_weight_note": (
            "DeepSeek and Qwen can run locally through Ollama/open weights without API keys. "
            "DEEPSEEK_API_KEY and QWEN_API_KEY are only needed for hosted HTTP providers."
        ),
    }
    if write:
        project_dir = root / PROJECT_DIR
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "local_runtime.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def format_local_runtime(report: dict[str, Any]) -> str:
    ollama = report["ollama"]
    lines = [
        "Hive Mind Local Runtime",
        "",
        f"Ollama wrapper: {ollama.get('status')} {ollama.get('path') or ''}",
        f"Ollama server: {ollama.get('server')}",
        f"Model source: {ollama.get('model_source')}",
        "",
        "Models:",
    ]
    for model in ollama.get("models") or []:
        lines.append(f"✓ {model}")
    if not ollama.get("models"):
        lines.append("○ no local model manifests found")
    lines.extend(["", "Missing recommended models:"])
    missing = report.get("missing_recommended_models") or []
    if missing:
        for model in missing:
            lines.append(f"○ {model}")
    else:
        lines.append("✓ none")
    lines.extend(["", report["open_weight_note"]])
    return "\n".join(lines)


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
    status = run_git(root, ["status", "--short"])
    diff_stat = run_git(root, ["diff", "--stat"])
    diff_name = run_git(root, ["diff", "--name-only"])
    staged_name = run_git(root, ["diff", "--cached", "--name-only"])
    report = {
        "schema_version": 1,
        "run_id": paths.run_id,
        "status_short": status["stdout"].splitlines(),
        "changed_files": [line for line in diff_name["stdout"].splitlines() if line.strip()],
        "staged_files": [line for line in staged_name["stdout"].splitlines() if line.strip()],
        "diff_stat": diff_stat["stdout"].splitlines(),
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
    return "\n".join(lines)


def review_diff(root: Path, run_id: str | None = None) -> Path:
    paths, _ = load_run(root, run_id)
    ensure_ollama_server(root)
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
    ensure_ollama_server(root)
    router_input = (
        "# User Prompt\n"
        f"{prompt.strip()}\n\n"
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
    set_agent_status(paths, "local-intent-router", "running")
    append_event(paths, "agent_started", {"agent": "local", "role": "intent-router", "worker": "intent_router"})
    model = choose_model("intent_router", complexity)
    try:
        worker_output = run_worker("intent_router", router_input, model=model, source_ref="user_prompt")
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
        worker_output = {"runtime": "fallback", "model": model, "parsed": parsed, "raw": "", "error": str(exc)}
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
        "route_source": route_source,
        "output_valid": validation["valid"],
        "output_issues": validation["issues"],
        "confidence": validation["confidence"],
        "should_escalate": validation["should_escalate"],
        "escalation_reason": validation["escalation_reason"],
        "output": worker_output,
        "normalized_actions": actions,
    }
    router_path = paths.local_dir / "intent_router.json"
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

    prepared: list[str] = []
    for action in actions:
        provider = action["provider"]
        role = action["role"]
        try:
            if provider == "local":
                # Only run cheap context preparation automatically. Other local roles can be triggered from the prepared plan.
                if role == "context" and route_source == "local_llm":
                    out = invoke_local(root, role, run_id=paths.run_id, complexity=complexity)
                    prepared.append(out.relative_to(root).as_posix())
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
    write_json(
        plan_path,
        {
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
        },
    )
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
) -> dict[str, Any]:
    """Turn a prompt into a multi-agent society plan and prepare worker/provider artifacts."""
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
    return report


def format_orchestration_report(report: dict[str, Any]) -> str:
    lines = [
        f"Hive Mind Society: {report.get('run_id')}",
        f"Intent: {report.get('intent')} via {report.get('route_source')}",
        f"Summary: {report.get('summary')}",
        "",
        "Members:",
    ]
    for member in report.get("members") or []:
        lines.append(
            f"- {member.get('order')}. {member.get('provider')}/{member.get('role')} "
            f"[{member.get('mode')}] -> {member.get('status') or 'planned'}"
        )
        if member.get("reason"):
            lines.append(f"  reason: {member.get('reason')}")
        lines.append(f"  command: {member.get('command')}")
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
    lines = [
        f"Routing Plan: {plan.get('run_id')}",
        f"Intent: {plan.get('intent', 'unknown')}",
        f"Source: {plan.get('route_source', 'unknown')}",
        f"Summary: {plan.get('summary', '')}",
        "",
        "Actions:",
    ]
    for item in plan.get("actions") or []:
        lines.append(f"- {item.get('provider')}/{item.get('role')}: {item.get('reason', '')}")
    prepared = plan.get("prepared_artifacts") or []
    if prepared:
        lines.extend(["", "Prepared Artifacts:"])
        for artifact in prepared:
            lines.append(f"- {artifact}")
    return "\n".join(lines)


def ensure_ollama_server(root: Path) -> None:
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
    if any(token in lowered for token in ["implement", "fix", "build", "code", "tui", "cli", "구현", "수정", "만들"]):
        intent = "implementation"
        actions.extend(
            [
                {"provider": "claude", "role": "planner", "reason": "Clarify plan and risks.", "execute": False},
                {"provider": "codex", "role": "executor", "reason": "Prepare implementation artifact.", "execute": False},
                {"provider": "gemini", "role": "reviewer", "reason": "Prepare independent review.", "execute": False},
            ]
        )
    elif any(token in lowered for token in ["review", "audit", "검토", "리뷰"]):
        intent = "review"
        actions.extend(
            [
                {"provider": "local", "role": "review", "reason": "First-pass risk scan.", "execute": False},
                {"provider": "claude", "role": "reviewer", "reason": "Conceptual risk review.", "execute": False},
                {"provider": "gemini", "role": "reviewer", "reason": "Alternate review.", "execute": False},
            ]
        )
    elif any(token in lowered for token in ["memory", "import", "parser", "메모리", "가져"]):
        intent = "memory_import"
        actions.extend(
            [
                {"provider": "local", "role": "memory", "reason": "Draft memory extraction.", "execute": False},
                {"provider": "codex", "role": "executor", "reason": "Prepare parser/import implementation.", "execute": False},
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
    try:
        worker_output = run_worker(worker, input_text, model=model, source_ref=source_ref)
        validation = validate_worker_result(worker, worker_output)
        result = {
            "schema_version": 1,
            "agent": "local",
            "role": role,
            "status": "completed",
            "provider_mode": "local_runtime",
            "runtime": "ollama",
            "worker": worker,
            "model": model,
            "source_ref": source_ref,
            "output_valid": validation["valid"],
            "output_issues": validation["issues"],
            "confidence": validation["confidence"],
            "should_escalate": validation["should_escalate"],
            "escalation_reason": validation["escalation_reason"],
            "output": worker_output,
        }
        event_type = "agent_completed"
        agent_status = "completed"
        run_status = "in_progress"
    except Exception as exc:
        result = {
            "schema_version": 1,
            "agent": "local",
            "role": role,
            "status": "failed",
            "provider_mode": "local_runtime",
            "runtime": "ollama",
            "worker": worker,
            "model": model,
            "source_ref": source_ref,
            "output_valid": False,
            "output_issues": [str(exc)],
            "confidence": 0.0,
            "should_escalate": True,
            "escalation_reason": str(exc),
            "error": str(exc),
            "needs_followup": True,
        }
        event_type = "agent_failed"
        agent_status = "failed"
        run_status = "needs_attention"
    out_path = paths.local_dir / f"{role.replace('-', '_')}.json"
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


def invoke_external_agent(
    root: Path,
    agent: str,
    role: str,
    run_id: str | None = None,
    execute: bool = False,
) -> Path:
    paths, state = load_run(root, run_id)
    if agent not in {"claude", "codex", "gemini"}:
        raise ValueError("external agent must be one of: claude, codex, gemini")
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
    command = external_command(agent, agent_bin, prompt_path.read_text(encoding="utf-8"))
    started = time.monotonic()
    started_at = now_iso()
    returncode = run_provider_with_live_log(paths, root, agent, role, command, output_path, timeout=600)
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


def provider_result_record(
    root: Path,
    *,
    agent: str,
    role: str,
    status: str,
    provider_mode: str,
    permission_mode: str,
    prompt_path: Path | None = None,
    command_path: Path | None = None,
    stdout_path: Path | None = None,
    stderr_path: Path | None = None,
    output_path: Path | None = None,
    returncode: int | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    duration_ms: int | None = None,
    files_changed: list[str] | None = None,
    commands_run: list[str] | None = None,
    tests_run: list[str] | None = None,
    artifacts_created: list[str] | None = None,
    risk_level: str = "low",
    policy_violations: list[str] | None = None,
    memory_refs_used: list[str] | None = None,
    capability_refs_used: list[str] | None = None,
    execute: bool | None = None,
    provider_status: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "provider": agent,
        "agent": agent,
        "role": role,
        "status": status,
        "provider_mode": provider_mode,
        "permission_mode": permission_mode,
        "provider_status": provider_status or "",
        "prompt_path": rel_or_empty(root, prompt_path),
        "command_path": rel_or_empty(root, command_path),
        "stdout_path": rel_or_empty(root, stdout_path),
        "stderr_path": rel_or_empty(root, stderr_path),
        "output_path": rel_or_empty(root, output_path),
        "prompt": rel_or_empty(root, prompt_path),
        "command": rel_or_empty(root, command_path),
        "output": rel_or_empty(root, output_path),
        "returncode": returncode,
        "started_at": started_at or "",
        "finished_at": finished_at or "",
        "duration_ms": duration_ms,
        "files_changed": files_changed if files_changed is not None else git_changed_files(root),
        "commands_run": commands_run or [],
        "tests_run": tests_run or [],
        "artifacts_created": artifacts_created or [],
        "risk_level": risk_level,
        "policy_violations": policy_violations or [],
        "memory_refs_used": memory_refs_used or [],
        "capability_refs_used": capability_refs_used or [],
        "execute": execute,
        "reason": reason or "",
        "working_method": WORKING_METHOD_PHRASE,
    }


def rel_or_empty(root: Path, path: Path | None) -> str:
    if path is None:
        return ""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


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


def git_changed_files(root: Path) -> list[str]:
    try:
        completed = subprocess.run(["git", "status", "--short"], cwd=root, text=True, capture_output=True, timeout=5)
    except Exception:
        return []
    if completed.returncode != 0:
        return []
    files = []
    for line in completed.stdout.splitlines():
        value = line[3:].strip()
        if value:
            files.append(value)
    return files


def run_provider_with_live_log(
    paths: RunPaths,
    root: Path,
    agent: str,
    role: str,
    command: list[str],
    output_path: Path,
    timeout: int,
) -> int:
    deadline = time.monotonic() + timeout
    with output_path.open("w", encoding="utf-8") as output:
        process = subprocess.Popen(
            command,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        assert process.stdout is not None
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
    role_contract = {
        "planner": "Create a concise implementation handoff with risks, files, acceptance criteria, and unresolved questions.",
        "reviewer": "Review the current run artifacts for risk, missing tests, overclaims, and next actions.",
        "executor": "Implement only the scoped task. Update result artifacts with changed files, commands, and unresolved issues.",
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
        f"## Current Handoff\n```yaml\n{handoff}\n```\n\n"
        f"## Recent Events\n```jsonl\n{events[-8000:]}\n```\n"
    )


def resolve_provider_binary(root: Path, agent: str) -> str | None:
    provider = detect_agents(root, write=True)["providers"].get(agent, {})
    return provider.get("path") or shutil.which(agent)


def suggest_external_command(agent: str, prompt_path: Path, root: Path | None = None) -> str:
    binary = resolve_provider_binary(root, agent) if root else shutil.which(agent)
    cmd = shlex.quote(binary or agent)
    prompt = shlex.quote(prompt_path.as_posix())
    if agent == "claude":
        return f"{cmd} -p \"$(cat {prompt})\" --permission-mode plan --output-format text\n"
    if agent == "gemini":
        return f"{cmd} -p \"$(cat {prompt})\" --approval-mode plan --output-format text --skip-trust\n"
    return f"{cmd} exec --cd . --sandbox read-only --ask-for-approval never \"$(cat {prompt})\"\n"


def external_command(agent: str, binary: str, prompt: str) -> list[str]:
    if agent == "claude":
        return [binary, "-p", prompt, "--permission-mode", "plan", "--output-format", "text"]
    if agent == "gemini":
        return [binary, "-p", prompt, "--approval-mode", "plan", "--output-format", "text", "--skip-trust"]
    if agent == "codex":
        return [binary, "exec", "--cd", ".", "--sandbox", "read-only", "--ask-for-approval", "never", prompt]
    raise ValueError(f"Unsupported executable external agent: {agent}")


def choose_local_input(paths: RunPaths, role: str) -> Path:
    if role in {"context", "context-compressor", "memory", "memory-curator", "classify"}:
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


def default_context_pack(state: dict[str, Any]) -> str:
    return (
        "# Context Pack\n\n"
        "## User Request\n"
        f"{state['user_request']}\n\n"
        "## Project State\n"
        "- MemoryOS is currently file-first: JSONL graph, run folders, local workers, and audit reports.\n"
        "- The current priority is structured blackboard + wrapper CLI/TUI before Desktop.\n\n"
        "## Active Decisions\n"
        "- Agents communicate through artifacts, not direct free-form chat.\n"
        "- Every task should have a run_id and event log.\n"
        "- Local LLMs summarize and draft; Claude/Codex handle judgment and implementation.\n\n"
        "## Open Questions\n"
        "- Which artifacts need human approval before memory commit?\n"
    )


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
        "hive tui\n"
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
        os.system(f'xdg-open "{paths.run_dir}" >/dev/null 2>&1 &')
