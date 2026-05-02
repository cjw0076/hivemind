"""Structured blackboard run folders for the MemoryOS harness."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .local_workers import choose_model, read_input, run_worker, validate_worker_result, worker_route_table
from .run_validation import validate_run_artifacts
from .schema import now_iso, stable_id


RUNS_DIR = ".runs"
CURRENT_FILE = "current"
PROVIDER_CAPABILITIES = "provider_capabilities.json"
GLOBAL_DIR = ".memoryos"
PROJECT_DIR = ".memoryos"
SETTINGS_PROFILE = "settings_profile.json"


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
    def artifacts(self) -> Path:
        return self.run_dir / "artifacts"

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
            "# MemoryOS Runs\n\n"
            "This directory is the structured blackboard for `mos` runs.\n"
            "Each run stores task, context, handoff, events, verification, and memory draft artifacts.\n",
            encoding="utf-8",
        )
    return runs_dir


def init_onboarding(root: Path) -> dict[str, Any]:
    """Initialize global/project MemoryOS state and detect provider runtimes."""
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
        "Welcome to MemoryOS.",
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
            "1. mos doctor",
            '2. mos run "your task"',
            "3. mos tui",
            "4. optional: eval \"$(mos settings shell)\"",
            "5. optional: mos local setup",
            "6. optional: mos mcp install --for all",
        ]
    )
    return "\n".join(lines)


def create_run(root: Path, user_request: str, project: str = "MemoryOS", task_type: str = "implementation") -> RunPaths:
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
    set_current(root, run_id)
    return paths


def load_run(root: Path, run_id: str | None = None) -> tuple[RunPaths, dict[str, Any]]:
    actual_run_id = run_id or get_current(root)
    if not actual_run_id:
        raise FileNotFoundError("No current run. Create one with: mos run \"task\"")
    paths = RunPaths(root=root, run_id=actual_run_id)
    if not paths.state.exists():
        raise FileNotFoundError(f"Run state not found: {paths.state}")
    return paths, json.loads(paths.state.read_text(encoding="utf-8"))


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
        "MEMORYOS_ROOT": root.as_posix(),
        "MEMORYOS_RUNS_DIR": (root / RUNS_DIR).as_posix(),
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
            shell_exports[f"MOS_{name.upper()}_BIN"] = command_path
        if item.get("status") == "gated":
            warnings.append(f"{name} first candidate is gated: {item.get('reason', '')}".strip())
    codex = provider_items.get("codex") or {}
    codex_path = codex.get("path") or ""
    path_codex = shutil.which("codex") or ""
    if codex_path and path_codex and codex_path != path_codex:
        warnings.append(f"codex PATH resolves to {path_codex}, but usable binary is {codex_path}")
    ollama = (local_runtime.get("ollama") or {}) if isinstance(local_runtime, dict) else {}
    if ollama.get("path"):
        shell_exports["MOS_OLLAMA_BIN"] = ollama["path"]
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
    lines = ["MemoryOS Settings Profile", "", f"Root: {report.get('root')}"]
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
    lines.append('eval "$(mos settings shell)"')
    if report.get("warnings"):
        lines.extend(["", "Warnings:"])
        for warning in report["warnings"]:
            lines.append(f"! {warning}")
    return "\n".join(lines)


def format_settings_shell(report: dict[str, Any]) -> str:
    lines = ["# MemoryOS shell profile"]
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


def format_doctor(report: dict[str, Any]) -> str:
    lines = ["MemoryOS Doctor", "", "Core:"]
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


def probe_command(name: str, version_args: list[str], roles: list[str], mode: str | None = None) -> dict[str, Any]:
    candidates = command_candidates(name)
    if not candidates:
        return {"status": "unavailable", "command": name, "roles": roles, "reason": "not found on PATH"}
    gated_probe: dict[str, Any] | None = None
    try:
        for path in candidates:
            completed = subprocess.run([path, *version_args], text=True, capture_output=True, timeout=10)
            raw = (completed.stdout or completed.stderr).strip()
            if completed.returncode != 0 or "접근 거부" in raw or "틀렸습니다" in raw:
                gated_probe = {
                    "status": "gated",
                    "command": name,
                    "path": path,
                    "version": "",
                    "roles": roles,
                    "mode": "prepare_only",
                    "reason": raw.splitlines()[0] if raw else f"{name} probe exited {completed.returncode}",
                }
                continue
            version = raw.splitlines()[0] if raw else ""
            return {
                "status": "available",
                "command": name,
                "path": path,
                "version": version,
                "roles": roles,
                "mode": mode or ("execute_supported" if name in {"claude", "gemini"} else "prepare_only"),
            }
    except Exception as exc:
        return {
            "status": "gated",
            "command": name,
            "path": candidates[0],
            "version": "",
            "roles": roles,
            "mode": "prepare_only",
            "reason": f"version probe failed: {exc}",
        }
    return gated_probe or {"status": "unavailable", "command": name, "roles": roles, "reason": "no usable candidate"}


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


def probe_env_provider(name: str, env_var: str, roles: list[str]) -> dict[str, Any]:
    return {
        "status": "configured" if os.environ.get(env_var) else "unconfigured",
        "command": None,
        "env_var": env_var,
        "roles": roles,
        "mode": "http",
        "reason": "" if os.environ.get(env_var) else f"{env_var} is not set",
    }


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
        "status": status,
        "command": wrapper.as_posix() if wrapper.exists() else "ollama",
        "path": wrapper.as_posix() if wrapper.exists() else None,
        "server": server,
        "models": server_models or manifest_models,
        "manifest_models": manifest_models,
        "model_source": "server" if server_models else "manifest",
        "roles": ["classifier", "context-compressor", "memory-extractor", "log-summarizer"],
        "mode": "local_runtime",
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
        "MemoryOS Local Runtime",
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
        result = {
            "schema_version": 1,
            "agent": agent,
            "role": role,
            "status": "prepared",
            "provider_mode": provider.get("mode", "prepare_only"),
            "provider_status": provider.get("status", "unknown"),
            "prompt": prompt_path.relative_to(root).as_posix(),
            "command": command_path.relative_to(root).as_posix(),
            "execute": False,
        }
        result_path.write_text(format_simple_yaml(result), encoding="utf-8")
        set_agent_status(paths, agent_name, "prepared")
        append_event(paths, "agent_prepared", {"agent": agent, "role": role, "artifact": result_path.relative_to(root).as_posix()})
        return result_path

    output_path = agent_dir / f"{role}_output.md"
    result_path = agent_dir / f"{role}_result.yaml"
    if agent == "codex":
        command_path = agent_dir / f"{role}_command.txt"
        command_path.write_text(suggest_external_command(agent, prompt_path, root), encoding="utf-8")
        result = {
            "schema_version": 1,
            "agent": agent,
            "role": role,
            "status": "failed",
            "provider_mode": "prepare_only",
            "reason": "codex execution is disabled until the non-interactive CLI contract is stable",
            "prompt": prompt_path.relative_to(root).as_posix(),
            "command": command_path.relative_to(root).as_posix(),
            "execute": False,
        }
        result_path.write_text(format_simple_yaml(result), encoding="utf-8")
        set_agent_status(paths, agent_name, "failed")
        append_event(paths, "agent_failed", {"agent": agent, "role": role, "artifact": result_path.relative_to(root).as_posix()})
        update_state(paths, phase="handoff", status="needs_attention")
        return result_path

    agent_bin = resolve_provider_binary(root, agent)
    if not agent_bin:
        result = {
            "schema_version": 1,
            "agent": agent,
            "role": role,
            "status": "failed",
            "provider_mode": "unavailable",
            "reason": f"{agent} binary not found",
        }
        result_path.write_text(format_simple_yaml(result), encoding="utf-8")
        set_agent_status(paths, agent_name, "failed")
        append_event(paths, "agent_failed", {"agent": agent, "role": role, "artifact": result_path.relative_to(root).as_posix()})
        update_state(paths, phase="handoff", status="needs_attention")
        return result_path

    set_agent_status(paths, agent_name, "running")
    append_event(paths, "agent_started", {"agent": agent, "role": role})
    command = external_command(agent, agent_bin, prompt_path.read_text(encoding="utf-8"))
    completed = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=600)
    output_path.write_text(completed.stdout or completed.stderr, encoding="utf-8")
    status = "completed" if completed.returncode == 0 else "failed"
    result = {
        "schema_version": 1,
        "agent": agent,
        "role": role,
        "status": status,
        "provider_mode": "execute_supported",
        "returncode": completed.returncode,
        "prompt": prompt_path.relative_to(root).as_posix(),
        "output": output_path.relative_to(root).as_posix(),
    }
    result_path.write_text(format_simple_yaml(result), encoding="utf-8")
    set_agent_status(paths, agent_name, status)
    append_event(paths, f"agent_{status}", {"agent": agent, "role": role, "artifact": result_path.relative_to(root).as_posix()})
    update_state(paths, phase="handoff", status="in_progress" if status == "completed" else "needs_attention")
    return result_path


def build_verification(root: Path, run_id: str | None = None) -> Path:
    paths, _ = load_run(root, run_id)
    report = validate_run_artifacts(paths.run_dir, root)
    out_path = paths.run_dir / "verification.yaml"
    out_path.write_text(format_simple_yaml(report), encoding="utf-8")
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
        "project": state.get("project", "MemoryOS"),
        "confidence": 0.8,
        "status": "draft",
        "raw_refs": [paths.final_report.relative_to(root).as_posix(), paths.events.relative_to(root).as_posix()],
    }
    out_path = paths.run_dir / "memory_drafts.json"
    write_json(out_path, {"memory_drafts": [draft]})
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
        f"# MemoryOS Harness Prompt\n\n"
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


def default_project_readme() -> str:
    return (
        "# Project MemoryOS\n\n"
        "This directory stores project-local MemoryOS config, context, skills, and run references.\n\n"
        "Start with:\n\n"
        "```bash\n"
        "mos doctor\n"
        "mos run \"your task\"\n"
        "mos tui\n"
        "```\n"
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
