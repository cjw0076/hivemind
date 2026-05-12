"""Provider loop worker artifacts for Claude/Codex/local workers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from . import harness as h
from .provider_passthrough import provider_passthrough
from .utils import now_iso, stable_id


SCHEMA_VERSION = "hive.provider_loop.v1"
PROVIDERS = {"claude", "codex", "local"}
FAILURE_CATEGORIES = {
    "rate_limit",
    "quota_exhausted",
    "auth_denied",
    "policy_blocked",
    "timeout",
    "context_exhausted",
    "provider_unavailable",
    "unknown_provider_failure",
}


def loop_mode(provider: str) -> str:
    if provider == "codex":
        return "one_shot_tick"
    if provider == "claude":
        return "monitor_plan"
    if provider == "local":
        return "local_worker_tick"
    raise ValueError(f"unsupported provider loop provider: {provider}")


def loops_dir(paths: h.RunPaths) -> Path:
    path = paths.run_dir / "provider_loops"
    path.mkdir(parents=True, exist_ok=True)
    return path


def worker_path(paths: h.RunPaths, worker_id: str) -> Path:
    return loops_dir(paths) / f"{worker_id}.json"


def stop_receipt_path(paths: h.RunPaths, worker_id: str) -> Path:
    return loops_dir(paths) / f"{worker_id}.stop.json"


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _load_paths(root: Path, run_id: str | None) -> h.RunPaths:
    paths, _ = h.load_run(root, run_id)
    return paths


def _latest_worker_path(root: Path, run_id: str | None = None) -> Path:
    candidates: list[Path] = []
    if run_id:
        paths = _load_paths(root, run_id)
        candidates = sorted(loops_dir(paths).glob("*.json"))
    else:
        candidates = sorted((root / h.RUNS_DIR).glob("*/provider_loops/*.json"))
    candidates = [path for path in candidates if not path.name.endswith(".stop.json")]
    if not candidates:
        raise FileNotFoundError("no provider loop worker found")
    return candidates[-1]


def provider_native_args(provider: str, prompt: str) -> list[str]:
    if provider == "codex":
        return ["exec", "--cd", ".", "--sandbox", "read-only", prompt]
    if provider == "claude":
        return ["--print", prompt]
    raise ValueError(f"provider {provider} has no native CLI args")


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
        "policy_blocked": 0,
        "timeout": 10,
        "context_exhausted": 0,
        "provider_unavailable": 15,
        "unknown_provider_failure": 15,
    }.get(category, 15)
    return (datetime.now(timezone.utc).astimezone() + timedelta(minutes=minutes)).isoformat(timespec="seconds")


def fallback_candidates(provider: str, category: str) -> list[str]:
    if category == "policy_blocked":
        order = {
            "claude": ["codex", "local"],
            "codex": ["claude", "local"],
            "local": ["codex", "claude"],
        }
    else:
        order = {
            "claude": ["codex", "local"],
            "codex": ["claude", "local"],
            "local": ["codex", "claude"],
        }
    return [item for item in order.get(provider, ["local"]) if item in PROVIDERS and item != provider]


def role_capsule(worker: dict[str, Any], category: str) -> dict[str, Any]:
    return {
        "schema_version": "hive.provider_role_capsule.v1",
        "run_id": worker.get("run_id"),
        "worker_id": worker.get("worker_id"),
        "provider": worker.get("provider"),
        "loop_mode": worker.get("loop_mode"),
        "prompt": worker.get("prompt"),
        "failure_category": category,
        "acceptance_rubric": [
            "preserve original prompt intent",
            "respect stop conditions",
            "write provider-loop receipt",
            "do not claim equivalence without verification",
        ],
        "stop_conditions": [
            "provider_secret_leak",
            "raw_private_data_leak",
            "fallback_executes_without_contract",
        ],
    }


def prepare_provider_loop(root: Path, provider: str, prompt: str, *, run_id: str | None = None) -> dict[str, Any]:
    if provider not in PROVIDERS:
        raise ValueError(f"provider must be one of: {', '.join(sorted(PROVIDERS))}")
    if run_id:
        paths, _ = h.load_run(root, run_id)
    else:
        paths = h.create_run(root, f"provider loop: {prompt}", task_type="provider_loop")
    worker_id = stable_id("ploop", paths.run_id, provider, prompt)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "worker_id": worker_id,
        "run_id": paths.run_id,
        "provider": provider,
        "loop_mode": loop_mode(provider),
        "prompt": prompt,
        "status": "prepared",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "tick_count": 0,
        "last_tick_at": None,
        "last_status": None,
        "last_result_path": None,
        "stopped_at": None,
        "next_action": "tick",
    }
    path = worker_path(paths, worker_id)
    _write(path, payload)
    h.append_event(paths, "provider_loop_prepared", {"worker_id": worker_id, "provider": provider, "loop_mode": payload["loop_mode"]})
    h.set_agent_status(paths, f"{provider}-loop", "prepared")
    payload["path"] = _rel(root, path)
    return payload


def _read_provider_result(path: Path) -> dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def tick_provider_loop(
    root: Path,
    *,
    worker_id: str | None = None,
    run_id: str | None = None,
    execute: bool = False,
    timeout: int = 600,
) -> dict[str, Any]:
    path = worker_path(_load_paths(root, run_id), worker_id) if worker_id else _latest_worker_path(root, run_id)
    worker = _read(path)
    paths = _load_paths(root, str(worker["run_id"]))
    if worker.get("status") == "stopped":
        return {"schema_version": SCHEMA_VERSION, "worker_id": worker["worker_id"], "status": "stopped", "tick_executed": False}

    provider = str(worker["provider"])
    prompt = str(worker["prompt"])
    tick_count = int(worker.get("tick_count") or 0) + 1
    if provider in {"claude", "codex"}:
        result_path = provider_passthrough(
            root,
            provider,
            provider_native_args(provider, prompt),
            run_id=paths.run_id,
            execute=execute,
            timeout=timeout,
        )
        result = _read_provider_result(result_path)
        last_status = str(result.get("status") or "unknown")
        result_ref = _rel(root, result_path)
    else:
        result_path = paths.local_dir / f"{worker['worker_id']}_tick_{tick_count}.json"
        result = {
            "schema_version": "hive.local_provider_loop_tick.v1",
            "worker_id": worker["worker_id"],
            "run_id": paths.run_id,
            "provider": "local",
            "provider_mode": "local_worker_tick",
            "status": "prepared",
            "prompt": prompt,
            "created_at": now_iso(),
            "execute": execute,
        }
        _write(result_path, result)
        last_status = "prepared"
        result_ref = _rel(root, result_path)

    failure_category = classify_provider_failure(result, root)
    if failure_category:
        worker.update(
            {
                "status": "degraded",
                "updated_at": now_iso(),
                "tick_count": tick_count,
                "last_tick_at": now_iso(),
                "last_status": last_status,
                "last_result_path": result_ref,
                "failure_category": failure_category,
                "cooldown_until": cooldown_until(failure_category),
                "fallback_candidates": fallback_candidates(provider, failure_category),
                "role_capsule": role_capsule(worker, failure_category),
                "next_action": "fallback",
            }
        )
    else:
        worker.update(
            {
                "status": "active",
                "updated_at": now_iso(),
                "tick_count": tick_count,
                "last_tick_at": now_iso(),
                "last_status": last_status,
                "last_result_path": result_ref,
                "failure_category": None,
                "cooldown_until": None,
                "fallback_candidates": [],
                "role_capsule": None,
                "next_action": "tick",
            }
        )
    _write(path, worker)
    h.append_event(paths, "provider_loop_tick", {"worker_id": worker["worker_id"], "provider": provider, "status": last_status, "result": result_ref})
    h.set_agent_status(paths, f"{provider}-loop", last_status)
    return {"schema_version": SCHEMA_VERSION, "worker_id": worker["worker_id"], "status": last_status, "tick_executed": True, "worker": {**worker, "path": _rel(root, path)}}


def provider_loop_status(root: Path, *, run_id: str | None = None) -> dict[str, Any]:
    worker_paths = []
    if run_id:
        paths = _load_paths(root, run_id)
        worker_paths = sorted(loops_dir(paths).glob("*.json"))
    elif (root / h.RUNS_DIR).exists():
        worker_paths = sorted((root / h.RUNS_DIR).glob("*/provider_loops/*.json"))
    workers = []
    for path in worker_paths:
        if path.name.endswith(".stop.json"):
            continue
        data = _read(path)
        data["path"] = _rel(root, path)
        workers.append(data)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "workers": workers,
        "count": len(workers),
        "next_action": "prepare" if not workers else "tick_or_stop",
    }


def stop_provider_loop(root: Path, *, worker_id: str | None = None, run_id: str | None = None) -> dict[str, Any]:
    path = worker_path(_load_paths(root, run_id), worker_id) if worker_id else _latest_worker_path(root, run_id)
    worker = _read(path)
    paths = _load_paths(root, str(worker["run_id"]))
    worker.update({"status": "stopped", "updated_at": now_iso(), "stopped_at": now_iso(), "next_action": "none"})
    _write(path, worker)
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "kind": "provider_loop_stop_receipt",
        "worker_id": worker["worker_id"],
        "run_id": paths.run_id,
        "provider": worker["provider"],
        "stopped_at": worker["stopped_at"],
    }
    receipt_path = stop_receipt_path(paths, worker["worker_id"])
    _write(receipt_path, receipt)
    h.append_event(paths, "provider_loop_stopped", {"worker_id": worker["worker_id"], "provider": worker["provider"], "receipt": _rel(root, receipt_path)})
    h.set_agent_status(paths, f"{worker['provider']}-loop", "stopped")
    return {"schema_version": SCHEMA_VERSION, "worker_id": worker["worker_id"], "status": "stopped", "receipt": _rel(root, receipt_path), "worker": {**worker, "path": _rel(root, path)}}
