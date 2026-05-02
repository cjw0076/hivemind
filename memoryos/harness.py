"""Structured blackboard run folders for the MemoryOS harness."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
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
CHECKS_DIR = "checks"


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


def checks_report(root: Path) -> dict[str, Any]:
    check_dir = root / PROJECT_DIR / CHECKS_DIR
    checks = []
    if check_dir.exists():
        for path in sorted(check_dir.glob("*.md")):
            checks.append(parse_check_file(path, root))
    return {"schema_version": 1, "checks_dir": check_dir.as_posix(), "checks": checks}


def format_checks_report(report: dict[str, Any]) -> str:
    lines = [f"MemoryOS Checks: {report.get('checks_dir')}", ""]
    checks = report.get("checks") or []
    if not checks:
        lines.append("No checks found. Run: mos init")
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
    append_event(paths, "commit_summary_created", {"artifact": out_path.relative_to(root).as_posix()})
    return out_path


def run_git(root: Path, args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=30)
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def proposed_commit_message(state: dict[str, Any], report: dict[str, Any]) -> str:
    request = str(state.get("user_request") or "Update MemoryOS")
    first = request.strip().splitlines()[0][:72]
    if first:
        return first[0].upper() + first[1:]
    changed = report.get("changed_files") or []
    if changed:
        return f"Update {changed[0]}"
    return "Update MemoryOS"


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
    paths = create_run(root, prompt, project="MemoryOS", task_type="routed") if run_id is None else load_run(root, run_id)[0]
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
    set_agent_status(paths, "local-intent-router", "completed" if router_status in {"completed", "fallback"} else "failed")
    append_event(paths, "intent_routed", {"agent": "local", "role": "intent-router", "artifact": router_path.relative_to(root).as_posix(), "source": route_source})

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
        except Exception as exc:
            append_event(paths, "route_action_failed", {"provider": provider, "role": role, "error": str(exc)})

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
    append_event(paths, "routing_plan_created", {"artifact": plan_path.relative_to(root).as_posix(), "prepared": len(prepared)})
    update_state(paths, phase="routing", status="ready")
    return plan_path


def load_routing_plan(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, _ = load_run(root, run_id)
    plan_path = paths.run_dir / "routing_plan.json"
    if not plan_path.exists():
        return {
            "run_id": paths.run_id,
            "status": "missing",
            "path": plan_path.as_posix(),
            "message": "No routing plan yet. Run: mos ask \"your task\"",
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
