"""AIOS three-OS consensus contract for a Hive run.

A Hive run becomes an AIOS contract when HiveMind, MemoryOS, and CapabilityOS
each contribute a proposal for the same goal, sign a shared artifact, and gate
workflow execution on the joint sign. This module owns the runtime loop that
produces and resumes that contract.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .aios_feedback import (
    aggregate_needs,
    extract_friction,
    has_blocking_friction,
    is_complete,
    write_feedback_packet,
)
from .harness import (
    create_run,
    ensure_capabilityos_recommendation,
    ensure_memoryos_context,
    flow_advance,
    load_run,
    orchestrate_prompt,
    update_state,
)
from .utils import ensure_valid_run_id, now_iso


SCHEMA_VERSION = 3
KIND = "hive_aios_contract"
CONTRACT_FILENAME = "aios_contract.json"
EVOLUTION_STATE_DIR = ".hivemind/aios_evolution"
MAX_EVOLUTION_ITERATIONS = 8


# Severities that block automatic execution.
_BLOCKING_SEVERITIES = {"medium", "high"}


def build_aios_contract(
    root: Path,
    goal: str,
    *,
    run_id: str | None = None,
    complexity: str = "default",
    execute_local: bool = False,
    force: bool = False,
    generation: int = 0,
    prior_feedback: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run the three-OS proposal phase and write a shared contract.

    ``force=True`` advances the workflow even when conflicts would normally
    require an operator checkpoint — used for ``hive aios resume`` after an
    operator has reviewed the contract.
    """
    goal = (goal or "").strip()
    if not goal:
        raise ValueError("aios contract goal must be a non-empty string")

    if run_id:
        run_id = ensure_valid_run_id(run_id)
        paths, _ = load_run(root, run_id)
    else:
        paths = create_run(root, user_request=goal)

    # Proposal phase: each OS contributes without executing. HiveMind defers
    # workflow advance so the contract can gate it.
    hivemind_report = orchestrate_prompt(
        root,
        goal,
        run_id=paths.run_id,
        complexity=complexity,
        advance_workflow=False,
    )
    memoryos_report = ensure_memoryos_context(root, paths.run_id, force=True)
    capabilityos_report = ensure_capabilityos_recommendation(root, paths.run_id, force=True)

    hivemind_proposal = _hivemind_proposal(hivemind_report)
    memoryos_proposal = _memoryos_proposal(memoryos_report)
    capabilityos_proposal = _capabilityos_proposal(capabilityos_report)

    conflicts = _check_conflicts(hivemind_proposal, memoryos_proposal, capabilityos_proposal)
    signed_by = _signers(hivemind_proposal, memoryos_proposal, capabilityos_proposal)
    blocking = _has_blocking_conflict(conflicts) or "hivemind" not in signed_by
    operator_checkpoint = bool(blocking) and not force
    status = "operator_checkpoint" if operator_checkpoint else "ready"

    execution: dict[str, Any] | None = None
    if not operator_checkpoint:
        execution = _advance_execution(root, paths.run_id, complexity, execute_local)

    contract = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND,
        "contract_id": f"asc_{paths.run_id}",
        "run_id": paths.run_id,
        "goal": goal,
        "generated_at": now_iso(),
        "status": status,
        "operator_checkpoint": operator_checkpoint,
        "force_resumed": bool(force and blocking),
        "signed_by": signed_by,
        "conflicts": conflicts,
        "proposals": {
            "hivemind": hivemind_proposal,
            "memoryos": memoryos_proposal,
            "capabilityos": capabilityos_proposal,
        },
        "execution": execution,
        "generation": generation,
        "prior_feedback_count": len(prior_feedback or []),
    }

    friction = extract_friction(contract)
    contract["friction"] = friction
    contract["needs"] = aggregate_needs(friction)
    contract["friction_blocking"] = has_blocking_friction(friction)

    feedback_result = write_feedback_packet(root, contract, friction, generation)
    contract["feedback_packet"] = {
        "written": feedback_result.get("written"),
        "path": feedback_result.get("path"),
        "needs_count": feedback_result.get("needs_count"),
        "friction_kinds": feedback_result.get("friction_kinds"),
        "reason": feedback_result.get("reason"),
    }

    contract_path = paths.run_dir / CONTRACT_FILENAME
    contract_path.write_text(
        json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    contract["artifact"] = contract_path.relative_to(root).as_posix()

    update_state(
        paths,
        aios_contract={
            "status": status,
            "artifact": contract["artifact"],
            "operator_checkpoint": operator_checkpoint,
            "signed_by": signed_by,
            "conflicts": conflicts,
            "force_resumed": contract["force_resumed"],
            "execution_status": (execution or {}).get("status"),
        },
    )
    return contract


def evolve_aios_contract(
    root: Path,
    goal: str,
    *,
    max_iterations: int = 3,
    complexity: str = "default",
    execute_local: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Run the AIOS contract loop until the big brain signals completion.

    Each iteration:
      1. Build a fresh AIOS contract (new run_id) with prior friction injected.
      2. Extract friction/needs from the three OSes, write a feedback packet.
      3. Check the operator-controlled completion signal at .hivemind/aios_completion.json.
      4. Stop when complete, friction-free, or max_iterations is reached.
    """
    goal = (goal or "").strip()
    if not goal:
        raise ValueError("aios evolution goal must be a non-empty string")
    if max_iterations < 1:
        raise ValueError("max_iterations must be >= 1")
    if max_iterations > MAX_EVOLUTION_ITERATIONS:
        max_iterations = MAX_EVOLUTION_ITERATIONS

    history: list[dict[str, Any]] = []
    prior_feedback: list[dict[str, Any]] = []
    stop_reason = "max_iterations_reached"
    final_contract: dict[str, Any] | None = None

    for generation in range(max_iterations):
        completion = is_complete(root, goal)
        if completion.get("complete"):
            stop_reason = f"completion_signal:{completion.get('reason')}"
            break

        iteration_goal = _compose_iteration_goal(goal, prior_feedback)
        contract = build_aios_contract(
            root,
            iteration_goal,
            complexity=complexity,
            execute_local=execute_local,
            force=force,
            generation=generation,
            prior_feedback=prior_feedback,
        )
        history.append({
            "generation": generation,
            "run_id": contract.get("run_id"),
            "status": contract.get("status"),
            "needs_count": len(contract.get("needs") or []),
            "friction_blocking": contract.get("friction_blocking"),
            "feedback_written": (contract.get("feedback_packet") or {}).get("written"),
        })
        final_contract = contract
        prior_feedback = (contract.get("needs") or [])[:]

        if not contract.get("friction_blocking"):
            stop_reason = "auto_converged_no_blocking_friction"
            break
        if contract.get("operator_checkpoint") and not force:
            stop_reason = "operator_checkpoint_blocked_evolution"
            break

    state_dir = root / EVOLUTION_STATE_DIR
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / f"evolution_{(final_contract or {}).get('run_id', 'none')}.json"
    summary = {
        "schema_version": 1,
        "kind": "hive_aios_evolution",
        "goal": goal,
        "generated_at": now_iso(),
        "iterations": len(history),
        "max_iterations": max_iterations,
        "stop_reason": stop_reason,
        "history": history,
        "final_contract_artifact": (final_contract or {}).get("artifact"),
        "final_run_id": (final_contract or {}).get("run_id"),
        "final_status": (final_contract or {}).get("status"),
        "final_needs": (final_contract or {}).get("needs") or [],
    }
    state_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    summary["artifact"] = state_path.relative_to(root).as_posix()
    return summary


def _compose_iteration_goal(goal: str, prior_feedback: list[dict[str, Any]]) -> str:
    """Inject the prior generation's needs into the next iteration's goal."""
    if not prior_feedback:
        return goal
    feedback_lines = ["", "# AIOS evolution feedback from prior iteration"]
    for item in prior_feedback[:8]:  # cap to keep the goal readable
        source = item.get("source", "?")
        kind = item.get("kind", "?")
        need = item.get("need", "")
        feedback_lines.append(f"- [{source}/{kind}] {need}")
    return goal + "\n" + "\n".join(feedback_lines)


def resume_aios_contract(
    root: Path,
    run_id: str,
    *,
    complexity: str = "default",
    execute_local: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Resume an AIOS contract after operator review.

    Re-runs proposal collection (so newly-available siblings can sign) and
    advances execution if the contract now clears — or if ``force`` is set,
    overrides remaining conflicts.
    """
    run_id = ensure_valid_run_id(run_id)
    paths, state = load_run(root, run_id)
    prior = state.get("aios_contract") or {}
    contract_path = paths.run_dir / CONTRACT_FILENAME
    if not contract_path.exists():
        raise FileNotFoundError(
            f"no AIOS contract found for run {run_id}: run `hive aios <goal>` first"
        )
    prior_contract = json.loads(contract_path.read_text(encoding="utf-8"))
    goal = prior_contract.get("goal") or state.get("user_request") or ""
    if not goal:
        raise ValueError(f"cannot resume AIOS contract for run {run_id}: goal is missing")
    return build_aios_contract(
        root,
        goal,
        run_id=run_id,
        complexity=complexity,
        execute_local=execute_local,
        force=force,
    )


def _advance_execution(
    root: Path,
    run_id: str,
    complexity: str,
    execute_local: bool,
) -> dict[str, Any]:
    """Advance the Hive workflow now that the contract is signed."""
    workflow = flow_advance(root, run_id=run_id, complexity=complexity, execute_local=execute_local)
    return {
        "status": workflow.get("status"),
        "scheduler": workflow.get("scheduler"),
        "artifact": workflow.get("artifact"),
        "next": workflow.get("next"),
        "actions_taken": workflow.get("actions_taken", []),
    }


def _hivemind_proposal(report: dict[str, Any]) -> dict[str, Any]:
    members = report.get("members") or []
    return {
        "status": "ok" if members else "empty",
        "intent": report.get("intent"),
        "summary": report.get("summary"),
        "member_count": len(members),
        "providers": sorted({str(m.get("provider")) for m in members if m.get("provider")}),
        "roles": sorted({str(m.get("role")) for m in members if m.get("role")}),
        "society_plan_artifact": f".runs/{report.get('run_id')}/society_plan.json",
    }


def _memoryos_proposal(report: dict[str, Any]) -> dict[str, Any]:
    accepted = report.get("accepted_memory_ids") or []
    return {
        "status": report.get("status"),
        "artifact": report.get("artifact"),
        "trace_id": report.get("trace_id"),
        "context_items": report.get("context_items", 0),
        "accepted_memory_ids": list(accepted),
    }


def _capabilityos_proposal(report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(report, dict):
        return {
            "status": "unavailable",
            "bridge_status": "unavailable",
            "top_recommendation": None,
            "recommendation_count": 0,
            "kinds": [],
            "providers": [],
            "artifact": None,
        }
    recommendation = report.get("recommendation")
    recommendations = report.get("recommendations") or []
    return {
        "status": report.get("status"),
        "bridge_status": report.get("bridge_status"),
        "top_recommendation": (
            (recommendation or {}).get("recommended_capability")
            or (recommendation or {}).get("capability_name")
            or (recommendation or {}).get("id")
        ) if isinstance(recommendation, dict) else None,
        "recommendation_count": len(recommendations),
        "kinds": sorted({
            str(item.get("kind"))
            for item in recommendations
            if isinstance(item, dict) and item.get("kind")
        }),
        "providers": sorted(_capability_providers(recommendations)),
        "artifact": report.get("artifact"),
    }


def _capability_providers(recommendations: list[dict[str, Any]]) -> set[str]:
    """Extract provider hints from CapabilityOS recommendation rows."""
    providers: set[str] = set()
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        cap_name = " ".join(
            str(item.get(field, ""))
            for field in ("capability_name", "recommended_capability", "id", "kind")
        ).lower()
        for hint in ("claude", "codex", "gemini", "ollama", "local"):
            if hint in cap_name:
                providers.add("local" if hint == "ollama" else hint)
    return providers


def _signers(
    hivemind: dict[str, Any],
    memoryos: dict[str, Any],
    capabilityos: dict[str, Any],
) -> list[str]:
    signed: list[str] = []
    if hivemind.get("status") == "ok":
        signed.append("hivemind")
    if memoryos.get("status") in {"available", "empty"}:
        signed.append("memoryos")
    if capabilityos.get("status") in {"ok", "empty"}:
        signed.append("capabilityos")
    return signed


def _has_blocking_conflict(conflicts: list[dict[str, Any]]) -> bool:
    return any(c.get("severity") in _BLOCKING_SEVERITIES for c in conflicts)


def _check_conflicts(
    hivemind: dict[str, Any],
    memoryos: dict[str, Any],
    capabilityos: dict[str, Any],
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    if hivemind.get("status") != "ok":
        conflicts.append({
            "kind": "hivemind_empty_plan",
            "severity": "high",
            "detail": "HiveMind produced no society members for the goal.",
        })
    if memoryos.get("status") in {"failed", "unavailable"}:
        conflicts.append({
            "kind": "memoryos_unavailable",
            "severity": "low",
            "detail": "MemoryOS context could not be retrieved; run proceeds without accepted memory.",
        })
    cap_status = capabilityos.get("status")
    if cap_status in {"failed", "unavailable"}:
        conflicts.append({
            "kind": "capabilityos_unavailable",
            "severity": "medium",
            "detail": "CapabilityOS recommendation could not be retrieved; route is HiveMind default.",
        })
    elif (capabilityos.get("recommendation_count") or 0) == 0:
        conflicts.append({
            "kind": "capabilityos_empty_recommendation",
            "severity": "medium",
            "detail": "CapabilityOS returned zero recommendations for the goal.",
        })

    # Provider-route alignment: when CapabilityOS surfaces provider hints, the
    # HiveMind society plan should include at least one of them. Mismatch is a
    # medium conflict that operators should sanity-check before execution.
    hive_providers = set(hivemind.get("providers") or [])
    capability_providers = set(capabilityos.get("providers") or [])
    if capability_providers and hive_providers.isdisjoint(capability_providers):
        conflicts.append({
            "kind": "provider_route_mismatch",
            "severity": "medium",
            "detail": (
                f"HiveMind providers={sorted(hive_providers) or '[]'} do not intersect "
                f"CapabilityOS hints={sorted(capability_providers)}; operator should pick one route."
            ),
        })

    return conflicts


def format_aios_contract(contract: dict[str, Any]) -> str:
    """Human-readable summary of an AIOS contract artifact."""
    lines = [
        f"AIOS Contract  {contract.get('contract_id')}",
        f"Run: {contract.get('run_id')}",
        f"Goal: {contract.get('goal')}",
        f"Status: {contract.get('status')}",
        f"Signed by: {', '.join(contract.get('signed_by') or []) or '(none)'}",
    ]
    if contract.get("force_resumed"):
        lines.append("Note: force-resumed by operator (blocking conflicts overridden).")
    conflicts = contract.get("conflicts") or []
    if conflicts:
        lines.append(f"Conflicts ({len(conflicts)}):")
        for item in conflicts:
            lines.append(f"  - [{item.get('severity')}] {item.get('kind')}: {item.get('detail')}")
    else:
        lines.append("Conflicts: none")
    proposals = contract.get("proposals") or {}
    hivemind = proposals.get("hivemind") or {}
    memoryos = proposals.get("memoryos") or {}
    capabilityos = proposals.get("capabilityos") or {}
    lines.append("Proposals:")
    lines.append(
        f"  hivemind     status={hivemind.get('status')} members={hivemind.get('member_count')} "
        f"providers={','.join(hivemind.get('providers') or []) or '-'}"
    )
    lines.append(
        f"  memoryos     status={memoryos.get('status')} context_items={memoryos.get('context_items')} "
        f"accepted={len(memoryos.get('accepted_memory_ids') or [])}"
    )
    lines.append(
        f"  capabilityos status={capabilityos.get('status')} "
        f"recommendations={capabilityos.get('recommendation_count')} top={capabilityos.get('top_recommendation') or '-'}"
    )
    execution = contract.get("execution")
    if execution:
        lines.append(
            f"Execution: status={execution.get('status')} scheduler={execution.get('scheduler')} "
            f"actions={len(execution.get('actions_taken') or [])}"
        )
    else:
        lines.append("Execution: deferred (operator checkpoint)")
    needs = contract.get("needs") or []
    if needs:
        lines.append(f"Needs reported to big brain ({len(needs)}):")
        for item in needs[:6]:
            lines.append(
                f"  - [{item.get('source')}/{item.get('kind')}] {item.get('need')}"
            )
        if len(needs) > 6:
            lines.append(f"  ... and {len(needs) - 6} more")
    feedback = contract.get("feedback_packet") or {}
    if feedback.get("written"):
        lines.append(f"Feedback packet -> {feedback.get('path')}")
    elif feedback.get("reason"):
        lines.append(f"Feedback packet: not written ({feedback.get('reason')})")
    if contract.get("artifact"):
        lines.append(f"Artifact: {contract['artifact']}")
    return "\n".join(lines)


def format_aios_evolution(summary: dict[str, Any]) -> str:
    """Human-readable rendering of an AIOS evolution summary."""
    lines = [
        f"AIOS Evolution  goal={summary.get('goal')}",
        f"Iterations: {summary.get('iterations')}/{summary.get('max_iterations')}",
        f"Stop reason: {summary.get('stop_reason')}",
        f"Final status: {summary.get('final_status')}",
        f"Final run: {summary.get('final_run_id')}",
    ]
    history = summary.get("history") or []
    if history:
        lines.append("History:")
        for entry in history:
            lines.append(
                f"  gen={entry.get('generation')} run={entry.get('run_id')} "
                f"status={entry.get('status')} needs={entry.get('needs_count')} "
                f"blocking={entry.get('friction_blocking')}"
            )
    final_needs = summary.get("final_needs") or []
    if final_needs:
        lines.append(f"Open needs (final iteration, {len(final_needs)}):")
        for item in final_needs[:6]:
            lines.append(f"  - [{item.get('source')}/{item.get('kind')}] {item.get('need')}")
    if summary.get("artifact"):
        lines.append(f"Artifact: {summary['artifact']}")
    return "\n".join(lines)
