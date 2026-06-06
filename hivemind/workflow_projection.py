from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .plan_dag import PlanDAG, PlanStep
from .utils import now_iso


SATISFIED_STEP_STATUSES = {"completed", "prepared", "skipped"}


def workflow_state_from_plan_dag(
    root: Path,
    dag: PlanDAG,
    dag_path: Path,
    actions_taken: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    next_step = dag.next_sequential()
    relative_dag_path = dag_path.relative_to(root).as_posix() if dag_path.exists() else None
    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": dag.run_id,
        "mode": "prepare_only",
        "status": workflow_status_from_dag(dag, next_step),
        "scheduler": "plan_dag",
        "scheduler_authority": "plan_dag.json",
        "surface_role": "read_model",
        "plan_dag_path": relative_dag_path,
        "read_model_of": relative_dag_path,
        "actions_taken": actions_taken or [],
        "steps": [asdict(step) for step in dag.steps],
        "barriers": barrier_states_from_dag(dag),
        "next": next_action_from_dag(dag, next_step),
        "policy": {
            "provider_cli_execution": "blocked_without_explicit_invoke_execute",
            "local_execution": "allowed_only_with_--execute-local",
            "memory_commit": "blocked",
        },
    }


def workflow_status_from_dag(dag: PlanDAG, next_step: PlanStep | None) -> str:
    if dag.is_complete():
        return "complete"
    if dag.is_blocked():
        return "blocked"
    if next_step is not None:
        if next_step.kind == "verify":
            return "ready_for_verification"
        return "waiting_for_dag_step"
    return "waiting_for_dependencies"


def next_action_from_dag(dag: PlanDAG, next_step: PlanStep | None) -> dict[str, Any]:
    if next_step is not None:
        return {
            "command": f"hive step run {next_step.step_id}",
            "reason": f"DAG step {next_step.step_id} is next [{next_step.owner_role}]",
            "source": "plan_dag",
        }
    if dag.is_complete():
        return {
            "command": "hive verify",
            "reason": "DAG is complete; verify run artifacts",
            "source": "plan_dag",
        }
    if dag.is_blocked():
        return {
            "command": "hive step list",
            "reason": "DAG is blocked; inspect failed steps",
            "source": "plan_dag",
        }
    return {
        "command": "hive step list",
        "reason": "DAG has no runnable step; inspect dependencies",
        "source": "plan_dag",
    }


def barrier_states_from_dag(dag: PlanDAG) -> list[dict[str, Any]]:
    barriers: list[dict[str, Any]] = []
    for step in dag.steps:
        if step.kind != "barrier":
            continue
        waiting_on = [
            {"step_id": dep, "status": dag.status_of(dep)}
            for dep in step.depends_on
            if dag.status_of(dep) not in SATISFIED_STEP_STATUSES
        ]
        barriers.append(
            {
                "barrier_id": step.step_id,
                "kind": "parallel_join",
                "status": "satisfied" if not waiting_on and step.status in SATISFIED_STEP_STATUSES else "waiting",
                "waiting_on": waiting_on,
            }
        )
    return barriers
