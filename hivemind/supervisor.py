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
from .plan_dag import auto_close_barriers, build_dag, execute_fan_out, execute_step, load_dag, save_dag
from .utils import now_iso
from .workloop import append_execution_ledger, format_probe_confidence, replay_execution_ledger


SUPERVISOR_STATE_FILE = "supervisor_state.json"
SUPERVISOR_LOG_FILE = "supervisor.log"
SUPERVISOR_STOP_FILE = "supervisor.stop"
SUPERVISOR_RECEIPTS_DIR = "supervisor_receipts"
HEARTBEAT_STALE_SECONDS = 120.0


def supervisor_paths(root: Path, run_id: str) -> dict[str, Path]:
    run_dir = root / ".runs" / run_id
    return {
        "run_dir": run_dir,
        "state": run_dir / SUPERVISOR_STATE_FILE,
        "log": run_dir / SUPERVISOR_LOG_FILE,
        "stop": run_dir / SUPERVISOR_STOP_FILE,
        "receipts": run_dir / SUPERVISOR_RECEIPTS_DIR,
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
    now_epoch = time.time()
    state["updated_at"] = now_iso()
    state["last_heartbeat_at"] = state["updated_at"]
    state["last_heartbeat_epoch"] = now_epoch
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
    state = mark_stale_supervisor_state(state)
    return state


def mark_stale_supervisor_state(state: dict[str, Any], *, stale_after: float = HEARTBEAT_STALE_SECONDS) -> dict[str, Any]:
    state = dict(state)
    if state.get("status") != "running":
        return state
    if not pid_is_alive(state.get("pid")):
        state["status"] = "stale"
        state["stale_reason"] = "dead_pid"
        return state
    heartbeat_epoch = state.get("last_heartbeat_epoch")
    if isinstance(heartbeat_epoch, (int, float)):
        age = max(0.0, time.time() - float(heartbeat_epoch))
        state["heartbeat_age_seconds"] = round(age, 3)
        if age > stale_after:
            state["status"] = "stale"
            state["stale_reason"] = "heartbeat_timeout"
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


def write_stop_receipt(
    root: Path,
    run_id: str,
    *,
    requested_by: str,
    previous_status: str,
    final_status: str,
    pid: Any,
    signal_sent: str | None,
    reason: str,
) -> dict[str, Any]:
    paths = supervisor_paths(root, run_id)
    paths["receipts"].mkdir(parents=True, exist_ok=True)
    receipt_path = paths["receipts"] / f"stop_{int(time.time() * 1000)}.json"
    receipt = {
        "schema_version": 1,
        "run_id": run_id,
        "kind": "supervisor_stop_receipt",
        "requested_by": requested_by,
        "requested_at": now_iso(),
        "previous_status": previous_status,
        "final_status": final_status,
        "pid": pid,
        "signal_sent": signal_sent,
        "reason": reason,
    }
    atomic_write(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    receipt["artifact"] = receipt_path.relative_to(root).as_posix()
    atomic_write(receipt_path, json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return receipt


def stop_requested(root: Path, run_id: str) -> bool:
    return supervisor_paths(root, run_id)["stop"].exists()


def run_supervisor(
    root: Path,
    run_id: str | None = None,
    *,
    max_rounds: int = 20,
    execute: bool = False,
    interval: float = 0.0,
    scheduler: str = "fanout",
    command: list[str] | None = None,
) -> dict[str, Any]:
    paths_obj, state = load_run(root, run_id)
    run_id = paths_obj.run_id
    paths = supervisor_paths(root, run_id)
    paths["stop"].unlink(missing_ok=True)
    command = command or [
        sys.executable,
        "-m",
        "hivemind.hive",
        "run",
        "start",
        "--run-id",
        run_id,
        "--scheduler",
        scheduler,
    ]

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
        "scheduler": scheduler,
        "kernel_level": "L0" if scheduler == "pingpong" else "L3",
        "log_path": paths["log"].relative_to(root).as_posix(),
        "command": command,
        "command_hash": supervisor_command_hash(command),
        "git_commit": current_git_commit(root),
        "last_result": None,
        "output_artifacts_validated": False,
        "last_heartbeat_at": None,
        "last_heartbeat_epoch": None,
    }
    write_supervisor_state(root, run_id, sup_state)
    append_supervisor_log(root, run_id, f"supervisor started pid={os.getpid()} execute={execute} max_rounds={max_rounds} scheduler={scheduler}")
    append_execution_ledger(
        root,
        run_id,
        "supervisor_started",
        actor="supervisor",
        status="running",
        bypass_mode="execute" if execute else "prepare",
        artifact=paths["state"].relative_to(root).as_posix(),
        artifact_hash_mode="mutable",
        extra={
            "pid": os.getpid(),
            "host": sup_state["host"],
            "command_hash": sup_state["command_hash"],
            "scheduler": scheduler,
            "kernel_level": sup_state["kernel_level"],
        },
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
            result = execute_scheduler_round(root, dag, execute=execute, scheduler=scheduler)
            save_dag(root, dag)
            sup_state["rounds"] = round_index
            sup_state["last_result"] = result
            sup_state["last_probes"] = probe_summaries_from_result(result)
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
        artifact_hash_mode="mutable",
        extra={"rounds": sup_state.get("rounds"), "replay": sup_state.get("replay")},
    )
    return supervisor_status_report(root, run_id)


def execute_scheduler_round(root: Path, dag: Any, *, execute: bool, scheduler: str) -> dict[str, Any]:
    if scheduler == "pingpong":
        return execute_pingpong_round(root, dag, execute=execute)
    return execute_fan_out(root, dag, execute=execute)


def execute_pingpong_round(root: Path, dag: Any, execute: bool = False, force: bool = False) -> dict[str, Any]:
    """Run one serialized L0 turn: one runnable step, then yield.

    This promotes the MemoryOS pingpong loop into Hive's ledger/protocol model:
    the scheduler wakes, claims one bounded step, records proof/evaluation through
    `execute_step()`, closes any newly satisfied barriers, and stops the round.
    """
    from .dag_state import recover_expired_leases

    append_execution_ledger(
        root,
        dag.run_id,
        "scheduler_round_started",
        actor="harness",
        status="running",
        bypass_mode="execute" if execute else "prepare",
        extra={"force": force, "scheduler": "pingpong", "kernel_level": "L0"},
    )
    recovered = recover_expired_leases(root, dag.run_id, dag)
    closed = auto_close_barriers(dag)

    dispatched: list[str] = []
    results: dict[str, Any] = {}
    mode = "idle"
    next_step = dag.next_sequential()
    if next_step:
        mode = "pingpong"
        result = execute_step(root, dag, next_step.step_id, execute=execute, force=force)
        dispatched.append(next_step.step_id)
        results[next_step.step_id] = result
        closed.extend(auto_close_barriers(dag))

    any_hard_fail = False
    for result in results.values():
        if result.get("status") == "failed":
            step = dag.by_id(result.get("step_id", ""))
            if step and step.on_failure == "stop":
                any_hard_fail = True
                break

    next_after = dag.next_sequential()
    report = {
        "ok": not any_hard_fail,
        "mode": mode,
        "scheduler": "pingpong",
        "kernel_level": "L0",
        "turn_owner": next_step.owner_role if next_step else None,
        "dispatched": dispatched,
        "results": results,
        "barriers_closed": closed,
        "recovered_leases": recovered,
        "next": next_after.step_id if next_after else None,
        "dag_complete": dag.is_complete(),
        "dag_blocked": dag.is_blocked(),
    }
    append_execution_ledger(
        root,
        dag.run_id,
        "scheduler_round_completed",
        actor="harness",
        status=mode,
        bypass_mode="execute" if execute else "prepare",
        extra={
            "scheduler": "pingpong",
            "kernel_level": "L0",
            "turn_owner": report["turn_owner"],
            "dispatched": dispatched,
            "barriers_closed": closed,
            "recovered_leases": recovered,
            "next": report["next"],
            "dag_complete": report["dag_complete"],
            "dag_blocked": report["dag_blocked"],
        },
    )
    return report


def supervisor_result_is_waiting(result: dict[str, Any]) -> bool:
    statuses = [str(item.get("status") or "") for item in (result.get("results") or {}).values()]
    probe_actions = [str(item.get("probe_action") or "") for item in (result.get("results") or {}).values()]
    return any(status in {"prepared", "protocol_gate", "reversibility_gate", "barrier_waiting"} for status in statuses) or any(
        action == "override_pending" for action in probe_actions
    )


def probe_summaries_from_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for step_id, item in (result.get("results") or {}).items():
        if not isinstance(item, dict) or "probe_action" not in item:
            continue
        summaries.append(
            {
                "step_id": str(step_id),
                "action": item.get("probe_action"),
                "confidence": item.get("probe_confidence"),
                "passed": item.get("probe_passed"),
                "status": item.get("status"),
                "evidence": item.get("probe_evidence"),
            }
        )
    return summaries


def probe_summaries_from_replay(replay: dict[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for step_id, step in (replay.get("steps") or {}).items():
        if not isinstance(step, dict):
            continue
        probe = step.get("probe")
        if not isinstance(probe, dict):
            continue
        summaries.append(
            {
                "step_id": str(step_id),
                "action": probe.get("action"),
                "confidence": probe.get("confidence"),
                "passed": None,
                "status": probe.get("status"),
                "criteria_count": probe.get("criteria_count"),
                "seq": probe.get("seq"),
            }
        )
    summaries.sort(key=lambda item: int(item.get("seq") or 0))
    return summaries


def start_supervisor_detached(
    root: Path,
    run_id: str,
    *,
    max_rounds: int,
    execute: bool,
    interval: float,
    scheduler: str,
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
        "--scheduler",
        scheduler,
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
        "scheduler": scheduler,
        "kernel_level": "L0" if scheduler == "pingpong" else "L3",
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
    state = mark_stale_supervisor_state(state)
    state["last_probes"] = state.get("last_probes") or probe_summaries_from_result(state.get("last_result") or {})
    if not state["last_probes"]:
        state["last_probes"] = probe_summaries_from_replay(replay)
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
    previous_status = str(state.get("status") or "unknown")
    pid = state.get("pid")
    signal_sent = None
    reason = "stop_requested"
    if pid_is_alive(pid):
        try:
            os.kill(int(pid), signal.SIGTERM)
            signal_sent = "SIGTERM"
            state["status"] = "stop_requested"
        except OSError:
            state["status"] = "stale"
            reason = "pid_signal_failed"
    else:
        state["status"] = "stop_requested"
        reason = "no_live_process"
    receipt = write_stop_receipt(
        root,
        paths_obj.run_id,
        requested_by="operator",
        previous_status=previous_status,
        final_status=str(state.get("status")),
        pid=pid,
        signal_sent=signal_sent,
        reason=reason,
    )
    state["last_stop_receipt"] = receipt.get("artifact")
    write_supervisor_state(root, paths_obj.run_id, state)
    append_supervisor_log(root, paths_obj.run_id, f"stop requested status={state['status']} receipt={receipt.get('artifact')}")
    append_execution_ledger(
        root,
        paths_obj.run_id,
        "supervisor_stop_requested",
        actor="operator",
        status=state["status"],
        artifact=str(receipt.get("artifact") or paths["state"].relative_to(root).as_posix()),
        extra={"previous_status": previous_status, "pid": pid, "signal_sent": signal_sent, "reason": reason},
    )
    return supervisor_status_report(root, paths_obj.run_id)


def format_supervisor_status(report: dict[str, Any]) -> str:
    lines = [
        "Supervisor",
        f"Run: {report.get('run_id')}  Status: {report.get('status')}  PID: {report.get('pid') or '-'}  Host: {report.get('host') or '-'}",
        f"Rounds: {report.get('rounds', 0)}/{report.get('max_rounds', '-')}  Execute: {report.get('execute')}",
        f"Scheduler: {report.get('scheduler') or 'fanout'}  Kernel: {report.get('kernel_level') or '-'}",
        f"Log: {report.get('log_path') or '-'}",
    ]
    if report.get("last_heartbeat_at"):
        lines.append(f"Heartbeat: {report.get('last_heartbeat_at')} age={report.get('heartbeat_age_seconds', 0)}s")
    if report.get("last_stop_receipt"):
        lines.append(f"Stop Receipt: {report.get('last_stop_receipt')}")
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
    probes = report.get("last_probes") or []
    lines.append("Probe:")
    if not probes:
        lines.append("- none")
    else:
        for probe in probes[-3:]:
            criteria = probe.get("criteria_count")
            criteria_part = f" criteria={criteria}" if criteria is not None else ""
            passed = probe.get("passed")
            passed_part = f" passed={passed}" if passed is not None else ""
            lines.append(
                f"- {probe.get('step_id')} action={probe.get('action') or '-'} "
                f"confidence={format_probe_confidence(probe.get('confidence'))} "
                f"status={probe.get('status') or '-'}{criteria_part}{passed_part}"
            )
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
