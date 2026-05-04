"""Ledger-backed supervisor for advancing Hive Mind DAG runs.

This is intentionally a small foreground/detached process controller, not a
hidden autonomy daemon. It advances a run one scheduler round at a time, writes
`supervisor_state.json`, appends ledger events, and leaves a plain text log.
"""

from __future__ import annotations

import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from .dag_state import STEP_LEASES_DIR, atomic_write
from .harness import load_run
from .plan_dag import build_dag, execute_fan_out, load_dag, save_dag
from .utils import now_iso
from .workloop import append_execution_ledger, replay_execution_ledger


SUPERVISOR_STATE_FILE = "supervisor_state.json"
SUPERVISOR_LOG_FILE = "supervisor.log"
SUPERVISOR_STOP_FILE = "supervisor.stop"


def supervisor_paths(root: Path, run_id: str) -> dict[str, Path]:
    run_dir = root / ".runs" / run_id
    return {
        "run_dir": run_dir,
        "state": run_dir / SUPERVISOR_STATE_FILE,
        "log": run_dir / SUPERVISOR_LOG_FILE,
        "stop": run_dir / SUPERVISOR_STOP_FILE,
    }


def supervisor_command_hash(command: list[str]) -> str:
    payload = json.dumps(command, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def current_git_commit(root: Path) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", root.as_posix(), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


def active_step_leases(root: Path, run_id: str) -> list[dict[str, Any]]:
    leases_dir = root / ".runs" / run_id / STEP_LEASES_DIR
    if not leases_dir.exists():
        return []
    leases: list[dict[str, Any]] = []
    for path in sorted(leases_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {"step_id": path.stem, "status": "invalid"}
        data["path"] = path.relative_to(root).as_posix()
        leases.append(data)
    return leases


def write_supervisor_state(root: Path, run_id: str, state: dict[str, Any]) -> Path:
    paths = supervisor_paths(root, run_id)
    state = dict(state)
    state["updated_at"] = now_iso()
    state["active_leases"] = active_step_leases(root, run_id)
    paths["state"].parent.mkdir(parents=True, exist_ok=True)
    atomic_write(paths["state"], json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
    return paths["state"]


def read_supervisor_state(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths_obj, _ = load_run(root, run_id)
    paths = supervisor_paths(root, paths_obj.run_id)
    if not paths["state"].exists():
        return {
            "schema_version": 1,
            "run_id": paths_obj.run_id,
            "status": "not_started",
            "active_leases": active_step_leases(root, paths_obj.run_id),
            "log_path": paths["log"].relative_to(root).as_posix(),
        }
    try:
        state = json.loads(paths["state"].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        state = {"schema_version": 1, "run_id": paths_obj.run_id, "status": "invalid_state"}
    state["active_leases"] = active_step_leases(root, paths_obj.run_id)
    if state.get("status") == "running" and not pid_is_alive(state.get("pid")):
        state["status"] = "stale"
    return state


def pid_is_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def append_supervisor_log(root: Path, run_id: str, message: str) -> None:
    paths = supervisor_paths(root, run_id)
    paths["log"].parent.mkdir(parents=True, exist_ok=True)
    with paths["log"].open("a", encoding="utf-8") as f:
        f.write(f"{now_iso()} {message}\n")


def stop_requested(root: Path, run_id: str) -> bool:
    return supervisor_paths(root, run_id)["stop"].exists()


def run_supervisor(
    root: Path,
    run_id: str | None = None,
    *,
    max_rounds: int = 20,
    execute: bool = False,
    interval: float = 0.0,
    command: list[str] | None = None,
) -> dict[str, Any]:
    paths_obj, state = load_run(root, run_id)
    run_id = paths_obj.run_id
    paths = supervisor_paths(root, run_id)
    paths["stop"].unlink(missing_ok=True)
    command = command or [sys.executable, "-m", "hivemind.hive", "run", "start", "--run-id", run_id]

    dag = load_dag(root, run_id)
    if dag is None:
        dag = build_dag(run_id, str(state.get("user_request") or ""), str(state.get("task_type") or "implementation"))
        save_dag(root, dag)

    sup_state: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "running",
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started_at": now_iso(),
        "stopped_at": None,
        "rounds": 0,
        "max_rounds": max_rounds,
        "execute": execute,
        "log_path": paths["log"].relative_to(root).as_posix(),
        "command": command,
        "command_hash": supervisor_command_hash(command),
        "git_commit": current_git_commit(root),
        "last_result": None,
        "output_artifacts_validated": False,
    }
    write_supervisor_state(root, run_id, sup_state)
    append_supervisor_log(root, run_id, f"supervisor started pid={os.getpid()} execute={execute} max_rounds={max_rounds}")
    append_execution_ledger(
        root,
        run_id,
        "supervisor_started",
        actor="supervisor",
        status="running",
        bypass_mode="execute" if execute else "prepare",
        artifact=paths["state"].relative_to(root).as_posix(),
        extra={"pid": os.getpid(), "host": sup_state["host"], "command_hash": sup_state["command_hash"]},
    )

    final_status = "max_rounds_reached"
    try:
        for round_index in range(1, max(1, max_rounds) + 1):
            if stop_requested(root, run_id):
                final_status = "stopped"
                break
            dag = load_dag(root, run_id) or dag
            if dag.is_complete():
                final_status = "completed"
                break
            result = execute_fan_out(root, dag, execute=execute)
            save_dag(root, dag)
            sup_state["rounds"] = round_index
            sup_state["last_result"] = result
            append_supervisor_log(
                root,
                run_id,
                f"round={round_index} mode={result.get('mode')} dispatched={result.get('dispatched')} next={result.get('next')}",
            )
            if result.get("dag_complete"):
                final_status = "completed"
                break
            if supervisor_result_is_waiting(result):
                final_status = "waiting"
                break
            if result.get("dag_blocked") or not result.get("ok", True):
                final_status = "blocked"
                break
            if result.get("mode") == "idle":
                final_status = "idle"
                break
            write_supervisor_state(root, run_id, sup_state)
            if interval > 0:
                time.sleep(interval)
    except Exception as exc:
        final_status = "failed"
        sup_state["error"] = str(exc)
        append_supervisor_log(root, run_id, f"supervisor failed: {exc}")

    replay = replay_execution_ledger(root, run_id)
    sup_state["status"] = final_status
    sup_state["stopped_at"] = now_iso()
    sup_state["output_artifacts_validated"] = bool(replay.get("ok"))
    sup_state["replay"] = {
        "ok": replay.get("ok"),
        "hash_chain_ok": replay.get("hash_chain_ok"),
        "seq_ok": replay.get("seq_ok"),
        "issue_count": len(replay.get("issues") or []),
    }
    write_supervisor_state(root, run_id, sup_state)
    append_supervisor_log(root, run_id, f"supervisor stopped status={final_status}")
    append_execution_ledger(
        root,
        run_id,
        "supervisor_stopped",
        actor="supervisor",
        status=final_status,
        bypass_mode="execute" if execute else "prepare",
        artifact=paths["state"].relative_to(root).as_posix(),
        extra={"rounds": sup_state.get("rounds"), "replay": sup_state.get("replay")},
    )
    return supervisor_status_report(root, run_id)


def supervisor_result_is_waiting(result: dict[str, Any]) -> bool:
    statuses = [str(item.get("status") or "") for item in (result.get("results") or {}).values()]
    return any(status in {"prepared", "protocol_gate", "reversibility_gate", "barrier_waiting"} for status in statuses)


def start_supervisor_detached(
    root: Path,
    run_id: str,
    *,
    max_rounds: int,
    execute: bool,
    interval: float,
) -> dict[str, Any]:
    paths = supervisor_paths(root, run_id)
    paths["log"].parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "hivemind.hive",
        "--root",
        root.as_posix(),
        "run",
        "start",
        "--run-id",
        run_id,
        "--max-rounds",
        str(max_rounds),
        "--interval",
        str(interval),
    ]
    if execute:
        cmd.append("--execute")
    with paths["log"].open("a", encoding="utf-8") as log:
        process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    state = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "starting",
        "pid": process.pid,
        "host": socket.gethostname(),
        "started_at": now_iso(),
        "stopped_at": None,
        "rounds": 0,
        "max_rounds": max_rounds,
        "execute": execute,
        "log_path": paths["log"].relative_to(root).as_posix(),
        "command": cmd,
        "command_hash": supervisor_command_hash(cmd),
        "git_commit": current_git_commit(root),
    }
    write_supervisor_state(root, run_id, state)
    return supervisor_status_report(root, run_id)


def supervisor_status_report(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths_obj, _ = load_run(root, run_id)
    state = read_supervisor_state(root, paths_obj.run_id)
    replay = replay_execution_ledger(root, paths_obj.run_id)
    state["run_id"] = paths_obj.run_id
    state["replay"] = {
        "ok": replay.get("ok"),
        "hash_chain_ok": replay.get("hash_chain_ok"),
        "seq_ok": replay.get("seq_ok"),
        "issue_count": len(replay.get("issues") or []),
    }
    state["active_leases"] = active_step_leases(root, paths_obj.run_id)
    return state


def tail_supervisor_log(root: Path, run_id: str | None = None, lines: int = 80) -> dict[str, Any]:
    paths_obj, _ = load_run(root, run_id)
    paths = supervisor_paths(root, paths_obj.run_id)
    if not paths["log"].exists():
        return {"run_id": paths_obj.run_id, "log_path": paths["log"].relative_to(root).as_posix(), "lines": []}
    raw = paths["log"].read_text(encoding="utf-8", errors="replace").splitlines()
    return {"run_id": paths_obj.run_id, "log_path": paths["log"].relative_to(root).as_posix(), "lines": raw[-max(1, lines) :]}


def stop_supervisor(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths_obj, _ = load_run(root, run_id)
    paths = supervisor_paths(root, paths_obj.run_id)
    paths["stop"].write_text(now_iso(), encoding="utf-8")
    state = read_supervisor_state(root, paths_obj.run_id)
    pid = state.get("pid")
    if pid_is_alive(pid):
        try:
            os.kill(int(pid), signal.SIGTERM)
            state["status"] = "stop_requested"
        except OSError:
            state["status"] = "stale"
    else:
        state["status"] = "stop_requested"
    write_supervisor_state(root, paths_obj.run_id, state)
    append_execution_ledger(
        root,
        paths_obj.run_id,
        "supervisor_stopped",
        actor="operator",
        status=state["status"],
        artifact=paths["state"].relative_to(root).as_posix(),
    )
    return supervisor_status_report(root, paths_obj.run_id)


def format_supervisor_status(report: dict[str, Any]) -> str:
    lines = [
        "Supervisor",
        f"Run: {report.get('run_id')}  Status: {report.get('status')}  PID: {report.get('pid') or '-'}  Host: {report.get('host') or '-'}",
        f"Rounds: {report.get('rounds', 0)}/{report.get('max_rounds', '-')}  Execute: {report.get('execute')}",
        f"Log: {report.get('log_path') or '-'}",
    ]
    replay = report.get("replay") or {}
    lines.append(
        "Replay: "
        f"ok={replay.get('ok')} hash={replay.get('hash_chain_ok')} seq={replay.get('seq_ok')} issues={replay.get('issue_count')}"
    )
    leases = report.get("active_leases") or []
    lines.append("Active Leases:")
    if not leases:
        lines.append("- none")
    else:
        for lease in leases:
            lines.append(f"- {lease.get('step_id')} owner={lease.get('owner')} expires={lease.get('expires_at')}")
    last = report.get("last_result") or {}
    if last:
        lines.append(f"Last Round: mode={last.get('mode')} dispatched={last.get('dispatched')} next={last.get('next')}")
    if report.get("error"):
        lines.append(f"Error: {report.get('error')}")
    return "\n".join(lines)


def format_supervisor_tail(report: dict[str, Any]) -> str:
    lines = [f"Supervisor Log: {report.get('run_id')}  {report.get('log_path')}"]
    rows = report.get("lines") or []
    if not rows:
        lines.append("- no supervisor log yet")
    else:
        lines.extend(str(row) for row in rows)
    return "\n".join(lines)
