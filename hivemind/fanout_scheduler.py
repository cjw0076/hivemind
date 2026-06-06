from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .workloop import append_execution_ledger

if TYPE_CHECKING:
    from .plan_dag import PlanDAG, PlanStep


SAFE_PARALLEL_OWNER_PREFIX = "local-"
SAFE_PARALLEL_OWNER_ROLES = {"harness", "verifier"}
DEFAULT_MAX_PARALLEL = 2


@dataclass(frozen=True, slots=True)
class FanOutSelection:
    selected: list["PlanStep"]
    deferred_parallel: list[str]
    deferred_unsafe_parallel: list[str]


def is_safe_parallel_step(step: "PlanStep") -> bool:
    if step.kind != "parallel":
        return False
    return step.owner_role.startswith(SAFE_PARALLEL_OWNER_PREFIX) or step.owner_role in SAFE_PARALLEL_OWNER_ROLES


def select_fan_out_steps(dag: "PlanDAG", max_parallel: int) -> FanOutSelection:
    parallel_steps = [step for step in dag.runnable() if step.kind == "parallel"]
    safe_steps = [step for step in parallel_steps if is_safe_parallel_step(step)]
    unsafe_steps = [step for step in parallel_steps if not is_safe_parallel_step(step)]
    bounded_limit = max(1, max_parallel)
    selected = safe_steps[:bounded_limit]
    deferred_safe = [step.step_id for step in safe_steps[bounded_limit:]]
    return FanOutSelection(
        selected=selected,
        deferred_parallel=deferred_safe,
        deferred_unsafe_parallel=[step.step_id for step in unsafe_steps],
    )


def execute_bounded_fan_out(
    root: Path,
    dag: "PlanDAG",
    *,
    execute: bool = False,
    force: bool = False,
    max_parallel: int = DEFAULT_MAX_PARALLEL,
) -> dict[str, Any]:
    from .dag_state import recover_expired_leases
    from .plan_dag import auto_close_barriers, execute_step

    append_execution_ledger(
        root,
        dag.run_id,
        "scheduler_round_started",
        actor="harness",
        status="running",
        bypass_mode="execute" if execute else "prepare",
        extra={
            "force": force,
            "scheduler": "fanout",
            "kernel_level": "L3",
            "max_parallel": max(1, max_parallel),
            "safe_parallel_only": True,
        },
    )
    recovered = recover_expired_leases(root, dag.run_id, dag)
    selection = select_fan_out_steps(dag, max_parallel)

    dispatched: list[str] = []
    results: dict[str, Any] = {}
    mode = "idle"

    if selection.selected:
        mode = "parallel"
        for step in selection.selected:
            result = execute_step(root, dag, step.step_id, execute=execute, force=force)
            dispatched.append(step.step_id)
            results[step.step_id] = result

    closed = auto_close_barriers(dag)

    if not selection.selected:
        next_step = dag.next_sequential()
        if next_step and next_step.kind != "parallel":
            mode = "sequential"
            result = execute_step(root, dag, next_step.step_id, execute=execute, force=force)
            dispatched.append(next_step.step_id)
            results[next_step.step_id] = result
            closed.extend(auto_close_barriers(dag))

    if not dispatched and not closed:
        mode = "idle"

    report = _build_report(dag, mode, dispatched, results, closed, recovered, selection, max_parallel)
    append_execution_ledger(
        root,
        dag.run_id,
        "scheduler_round_completed",
        actor="harness",
        status=mode,
        bypass_mode="execute" if execute else "prepare",
        extra={
            "scheduler": "fanout",
            "kernel_level": "L3",
            "max_parallel": report["max_parallel"],
            "safe_parallel_only": True,
            "dispatched": dispatched,
            "deferred_parallel": report["deferred_parallel"],
            "deferred_unsafe_parallel": report["deferred_unsafe_parallel"],
            "barriers_closed": closed,
            "recovered_leases": recovered,
            "next": report["next"],
            "dag_complete": report["dag_complete"],
            "dag_blocked": report["dag_blocked"],
        },
    )
    return report


def _build_report(
    dag: "PlanDAG",
    mode: str,
    dispatched: list[str],
    results: dict[str, Any],
    closed: list[str],
    recovered: list[str],
    selection: FanOutSelection,
    max_parallel: int,
) -> dict[str, Any]:
    any_hard_fail = False
    for result in results.values():
        if result.get("status") == "failed":
            step = dag.by_id(result.get("step_id", ""))
            if step and step.on_failure == "stop":
                any_hard_fail = True
                break
    reversibility_gates = [
        {
            "step_id": result.get("step_id"),
            "reversibility": result.get("reversibility"),
            "source": result.get("reversibility_source"),
            "factors": result.get("reversibility_factors", []),
            "error": result.get("error", ""),
        }
        for result in results.values()
        if result.get("status") == "reversibility_gate"
    ]
    next_step = dag.next_sequential()
    return {
        "ok": not any_hard_fail,
        "mode": mode,
        "scheduler": "fanout",
        "kernel_level": "L3",
        "max_parallel": max(1, max_parallel),
        "safe_parallel_only": True,
        "dispatched": dispatched,
        "results": results,
        "barriers_closed": closed,
        "recovered_leases": recovered,
        "deferred_parallel": selection.deferred_parallel,
        "deferred_unsafe_parallel": selection.deferred_unsafe_parallel,
        "reversibility_gates": reversibility_gates,
        "next": next_step.step_id if next_step else None,
        "dag_complete": dag.is_complete(),
        "dag_blocked": dag.is_blocked(),
    }
