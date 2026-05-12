"""Provider loop worker artifacts for Claude/Codex/local workers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from . import harness as h
from .provider_passthrough import provider_passthrough
from .utils import now_iso, stable_id


SCHEMA_VERSION = "hive.provider_loop.v1"
PROVIDERS = {"claude", "codex", "local"}


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

    worker.update(
        {
            "status": "active",
            "updated_at": now_iso(),
            "tick_count": tick_count,
            "last_tick_at": now_iso(),
            "last_status": last_status,
            "last_result_path": result_ref,
            "next_action": "tick" if last_status in {"prepared", "completed"} else "review",
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
