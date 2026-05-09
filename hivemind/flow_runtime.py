"""Prompt-to-workflow runtime advancement for Hive runs."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .utils import now_iso


SAFE_LOCAL_TASK_ROLES = {
    "context",
    "context-compressor",
    "summarize",
    "log-summarizer",
    "memory",
    "memory-curator",
    "review",
    "diff-reviewer",
    "classify",
    "handoff",
    "handoff-drafter",
}


def flow_advance(
    root: Path,
    task: str | None = None,
    run_id: str | None = None,
    complexity: str = "fast",
    execute_local: bool = False,
) -> dict[str, Any]:
    """Advance a run through the safe, event-driven prepare-only workflow slice."""
    from . import harness as h
    from .plan_dag import build_dag_from_actions, load_dag, save_dag

    if task and run_id:
        raise ValueError("flow_advance accepts either task or run_id, not both")
    paths = h.create_run(root, task, project="Hive Mind", task_type="workflow") if task else h.load_run(root, run_id)[0]
    paths.artifacts.mkdir(parents=True, exist_ok=True)
    actions_taken: list[dict[str, Any]] = []

    paths, state = h.load_run(root, paths.run_id)
    memory_context = h.ensure_memoryos_context(root, paths.run_id)
    if memory_context.get("status") in {"available", "empty"}:
        actions_taken.append(
            {
                "action": "memoryos_context",
                "artifact": memory_context.get("artifact"),
                "status": memory_context.get("status"),
                "trace_id": memory_context.get("trace_id"),
            }
        )
    paths, state = h.load_run(root, paths.run_id)
    plan_path = paths.run_dir / "routing_plan.json"
    if not plan_path.exists():
        plan_path = h.ask_router(root, str(state.get("user_request") or ""), run_id=paths.run_id, complexity=complexity)
        actions_taken.append({"action": "route", "artifact": plan_path.relative_to(root).as_posix(), "status": "created"})
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    society_path = paths.run_dir / "society_plan.json"
    if not society_path.exists():
        society = build_society_plan_from_routing(root, paths, state, plan, execute=False)
        h.write_json(society_path, society)
        h.add_state_artifact(paths, "society_plan", society_path)
        h.append_event(paths, "society_plan_created", {"artifact": society_path.relative_to(root).as_posix(), "members": len(society.get("members") or [])})
        actions_taken.append({"action": "society", "artifact": society_path.relative_to(root).as_posix(), "status": "created"})

    dag_path = paths.run_dir / "plan_dag.json"
    dag = load_dag(root, paths.run_id)
    if dag is None:
        intent = plan.get("intent") or state.get("task_type") or "implementation"
        dag = build_dag_from_actions(paths.run_id, str(state.get("user_request") or ""), intent, plan.get("actions") or [])
        sync_dag_with_run_state(root, paths.run_id, dag)
        save_dag(root, dag)
        actions_taken.append({"action": "plan_dag", "artifact": dag_path.relative_to(root).as_posix(), "status": "created"})
    else:
        sync_dag_with_run_state(root, paths.run_id, dag)
        save_dag(root, dag)

    if execute_local and dag is not None:
        local_results = execute_ready_local_steps(root, dag)
        if local_results:
            actions_taken.extend(local_results)
            sync_dag_with_run_state(root, paths.run_id, dag)
            save_dag(root, dag)

    paths, state = h.load_run(root, paths.run_id)
    if execute_local and h.agent_status(state, h.local_agent_name("context")) == "completed":
        for action in plan.get("actions") or []:
            provider = str(action.get("provider"))
            role = str(action.get("role"))
            if provider in {"claude", "codex", "gemini"}:
                result_path = h.invoke_external_agent(root, provider, role, run_id=paths.run_id, execute=False)
                actions_taken.append(
                    {
                        "action": "reprepare-after-context",
                        "provider": provider,
                        "role": role,
                        "artifact": result_path.relative_to(root).as_posix(),
                    }
                )
        sync_dag_with_run_state(root, paths.run_id, dag)
        save_dag(root, dag)

    workflow = build_workflow_state(root, paths.run_id, actions_taken=actions_taken, execute_local=execute_local)
    out_path = paths.artifacts / "workflow_state.json"
    workflow["artifact"] = out_path.relative_to(root).as_posix()
    h.write_json(out_path, workflow)
    h.add_state_artifact(paths, "workflow_state", out_path)
    h.append_event(paths, "workflow_state_created", {"artifact": out_path.relative_to(root).as_posix(), "status": workflow.get("status")})
    h.append_event(paths, "workflow_advanced", {"artifact": out_path.relative_to(root).as_posix(), "actions": len(actions_taken)})
    h.append_hive_activity(
        paths,
        "hive-mind",
        "workflow_advanced",
        f"Workflow advanced to {workflow.get('status')}; next: {(workflow.get('next') or {}).get('command')}",
        {"workflow": out_path.relative_to(root).as_posix(), "next": workflow.get("next")},
    )
    return workflow


def sync_dag_with_run_state(root: Path, run_id: str, dag: Any) -> None:
    """Mark route-action DAG steps satisfied when prepared artifacts already exist."""
    from . import harness as h

    paths, state = h.load_run(root, run_id)
    for step in dag.steps:
        if step.status not in {"pending", "running"}:
            continue
        local_role = local_role_for_owner(step.owner_role)
        if local_role:
            status = h.agent_status(state, h.local_agent_name(local_role))
            artifact = paths.local_dir / f"{local_role.replace('-', '_')}.json"
            if status == "completed" and artifact.exists():
                step.status = "completed"
                step.finished_at = step.finished_at or now_iso()
                step.artifact = artifact.relative_to(root).as_posix()
            elif status == "failed" and artifact.exists():
                step.status = "skipped" if step.on_failure != "stop" else "failed"
                step.finished_at = step.finished_at or now_iso()
                step.artifact = artifact.relative_to(root).as_posix()
            continue
        external = external_role_for_owner(step.owner_role)
        if external:
            provider, role = external
            status = h.agent_status(state, f"{provider}-{role}")
            artifact = paths.run_dir / "agents" / provider / f"{role}_result.yaml"
            if status in {"prepared", "completed"} and artifact.exists():
                step.status = "prepared" if status == "prepared" else "completed"
                step.finished_at = step.finished_at or now_iso()
                step.artifact = artifact.relative_to(root).as_posix()
            elif status == "failed" and artifact.exists():
                step.status = "failed" if step.on_failure == "stop" else "skipped"
                step.finished_at = step.finished_at or now_iso()
                step.artifact = artifact.relative_to(root).as_posix()


def execute_ready_local_steps(root: Path, dag: Any) -> list[dict[str, Any]]:
    """Execute runnable safe local steps through the DAG/ledger path."""
    from .plan_dag import execute_step

    actions: list[dict[str, Any]] = []
    progressed = True
    while progressed:
        progressed = False
        for step in list(dag.runnable()):
            local_role = local_role_for_owner(step.owner_role)
            if local_role not in SAFE_LOCAL_TASK_ROLES:
                continue
            result = execute_step(root, dag, step.step_id, execute=True)
            actions.append({"action": f"local-{local_role}", "step_id": step.step_id, **result})
            progressed = True
            if result.get("status") in {"failed", "reversibility_gate", "protocol_gate", "lease_conflict"}:
                return actions
            break
    return actions


def local_role_for_owner(owner_role: str) -> str | None:
    return {
        "local-context-compressor": "context",
        "local-diff-reviewer": "review",
        "local-log-summarizer": "summarize",
        "local-memory-curator": "memory",
        "local-classifier": "classify",
        "local-handoff-drafter": "handoff",
    }.get(owner_role)


def external_role_for_owner(owner_role: str) -> tuple[str, str] | None:
    return {
        "claude-planner": ("claude", "planner"),
        "claude-reviewer": ("claude", "reviewer"),
        "codex-executor": ("codex", "executor"),
        "codex-reviewer": ("codex", "reviewer"),
        "gemini-planner": ("gemini", "planner"),
        "gemini-reviewer": ("gemini", "reviewer"),
    }.get(owner_role)


def build_society_plan_from_routing(
    root: Path,
    paths: Any,
    state: dict[str, Any],
    plan: dict[str, Any],
    execute: bool = False,
) -> dict[str, Any]:
    from . import harness as h

    providers = h.detect_agents(root, write=True).get("providers") or {}
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
                "status": h.agent_status(state, f"{provider}-{role}") or ("ready" if provider != "local" else h.agent_status(state, h.local_agent_name(role))),
                "reason": action.get("reason", ""),
                "command": command,
                "artifact_prefix": (paths.run_dir / "agents" / provider).relative_to(root).as_posix()
                if provider != "local"
                else paths.local_dir.relative_to(root).as_posix(),
            }
        )
    return {
        "schema_version": 1,
        "run_id": paths.run_id,
        "prompt": plan.get("prompt") or state.get("user_request"),
        "intent": plan.get("intent", "unknown"),
        "summary": plan.get("summary", ""),
        "route_source": plan.get("route_source", "unknown"),
        "execute_requested": execute,
        "members": members,
        "prepared_artifacts": plan.get("prepared_artifacts", []),
        "next": h.recommend_next_action(paths, state, h.pipeline_status(paths), h.artifact_status(paths, state)),
    }


def build_workflow_state(
    root: Path,
    run_id: str,
    actions_taken: list[dict[str, Any]] | None = None,
    execute_local: bool = False,
) -> dict[str, Any]:
    from . import harness as h
    from .plan_dag import load_dag

    paths, state = h.load_run(root, run_id)
    plan_path = paths.run_dir / "routing_plan.json"
    society_path = paths.run_dir / "society_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {"actions": []}
    actions = plan.get("actions") if isinstance(plan.get("actions"), list) else []
    external = [action for action in actions if action.get("provider") in {"claude", "codex", "gemini"}]
    local = [action for action in actions if action.get("provider") == "local"]
    external_states = [workflow_member_state(root, paths, action) for action in external]
    local_states = [workflow_member_state(root, paths, action) for action in local]
    failed = [item for item in [*external_states, *local_states] if item.get("status") == "failed"]
    waiting_external = [item for item in external_states if item.get("status") in {"prepared", "ready", "pending"}]
    local_waiting = [item for item in local_states if item.get("status") in {"ready", "pending", None}]
    provider_barrier_status = "not_required"
    if external_states:
        provider_barrier_status = "satisfied" if not waiting_external and not failed else "waiting"
    next_action = h.recommend_next_action(paths, state, h.pipeline_status(paths), h.artifact_status(paths, state))
    if failed:
        status = "blocked"
        next_action = {"command": "hive audit", "reason": "workflow has failed members"}
    elif local_waiting and not execute_local:
        waiting_roles = {str(item.get("role")) for item in local_waiting}
        status = "waiting_for_local_context" if waiting_roles <= {"context", "context-compressor"} else "waiting_for_local_workers"
        next_action = {"command": f"hive flow --run-id {paths.run_id} --execute-local", "reason": "safe local worker task is ready but not executed"}
    elif provider_barrier_status == "waiting":
        status = "waiting_for_provider_outputs"
        next_action = {"command": f"hive events --run-id {paths.run_id}", "reason": "provider prompts are prepared; wait for provider results or run explicit invokes"}
    else:
        status = "ready_for_verification"

    dag = load_dag(root, run_id)
    dag_file = paths.run_dir / "plan_dag.json"
    dag_steps: list[dict[str, Any]] = []
    if dag is not None:
        dag_steps = [asdict(s) for s in dag.steps]
        dag_next = dag.next_sequential()
        if dag_next:
            next_action = {
                "command": f"hive step run {dag_next.step_id}",
                "reason": f"DAG step {dag_next.step_id} is next [{dag_next.owner_role}]",
            }
        elif dag.is_complete():
            status = "complete"
        elif dag.is_blocked():
            status = "blocked"
            next_action = {"command": "hive step list", "reason": "DAG is blocked — check failed steps"}

    return {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "mode": "prepare_only",
        "status": status,
        "scheduler": "plan_dag" if dag is not None else "workflow_state_legacy",
        "plan_dag_path": dag_file.relative_to(root).as_posix() if dag_file.exists() else None,
        "actions_taken": actions_taken or [],
        "dag_steps": dag_steps,
        "legacy_steps": [
            {"step_id": "intake", "kind": "sequential", "status": "done", "artifact": paths.task.relative_to(root).as_posix()},
            {"step_id": "route", "kind": "sequential", "status": "done" if plan_path.exists() else "pending", "artifact": plan_path.relative_to(root).as_posix()},
            {"step_id": "society", "kind": "sequential", "status": "done" if society_path.exists() else "pending", "artifact": society_path.relative_to(root).as_posix()},
            {"step_id": "local_context", "kind": "sequential", "status": workflow_group_status(local_states), "members": local_states},
            {"step_id": "provider_prepare", "kind": "parallel", "status": workflow_group_status(external_states), "members": external_states},
        ],
        "barriers": [
            {
                "barrier_id": "provider_outputs",
                "kind": "parallel_join",
                "status": provider_barrier_status,
                "waiting_on": [item for item in external_states if item.get("status") != "completed"],
            }
        ],
        "next": next_action,
        "policy": {
            "provider_cli_execution": "blocked_without_explicit_invoke_execute",
            "local_execution": "allowed_only_with_--execute-local",
            "memory_commit": "blocked",
        },
    }


def workflow_member_state(root: Path, paths: Any, action: dict[str, Any]) -> dict[str, Any]:
    from . import harness as h

    provider = str(action.get("provider"))
    role = str(action.get("role"))
    if provider == "local":
        status = h.agent_status(json.loads(paths.state.read_text(encoding="utf-8")), h.local_agent_name(role)) or "pending"
        artifact = paths.local_dir / f"{role.replace('-', '_')}.json"
    else:
        status = h.agent_status(json.loads(paths.state.read_text(encoding="utf-8")), f"{provider}-{role}") or "pending"
        artifact = paths.run_dir / "agents" / provider / f"{role}_result.yaml"
    return {
        "provider": provider,
        "role": role,
        "status": status,
        "artifact": artifact.relative_to(root).as_posix(),
        "artifact_exists": artifact.exists(),
        "reason": action.get("reason", ""),
    }


def workflow_group_status(members: list[dict[str, Any]]) -> str:
    if not members:
        return "not_required"
    statuses = {str(member.get("status")) for member in members}
    if "failed" in statuses:
        return "failed"
    if statuses <= {"completed"}:
        return "done"
    if statuses <= {"prepared", "ready", "completed"}:
        return "ready"
    return "pending"


def format_flow_report(report: dict[str, Any]) -> str:
    lines = [
        f"Hive Mind Flow: {report.get('run_id')}",
        f"Status: {report.get('status')} | Mode: {report.get('mode')}",
        f"Artifact: {report.get('artifact')}",
        "",
        "Steps:",
    ]
    for step in report.get("steps") or []:
        lines.append(f"- {step.get('step_id')}: {step.get('status')} [{step.get('kind')}]")
    lines.append("")
    lines.append("Barriers:")
    for barrier in report.get("barriers") or []:
        lines.append(f"- {barrier.get('barrier_id')}: {barrier.get('status')} waiting={len(barrier.get('waiting_on') or [])}")
    next_action = report.get("next") or {}
    lines.extend(["", "Next:", f"  {next_action.get('command')}", f"  Reason: {next_action.get('reason')}"])
    return "\n".join(lines)
