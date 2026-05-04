"""Prompt/log live surface for AIOS-style operation.

This is the user-facing read model over the run substrate: prompt in, live log
out. It intentionally hides directory and artifact paths unless requested.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .harness import load_run, now_iso, orchestrate_prompt, read_hive_activity, run_board, short_timestamp
from .workloop import read_execution_ledger


def start_live_prompt(root: Path, prompt: str, *, complexity: str = "default") -> dict[str, Any]:
    """Create a prompt-driven run and return the orchestration report."""
    return orchestrate_prompt(root, prompt, complexity=complexity)


def build_live_report(
    root: Path,
    run_id: str | None = None,
    *,
    tail: int = 16,
    show_paths: bool = False,
) -> dict[str, Any]:
    paths, state = load_run(root, run_id)
    board = run_board(root, paths.run_id)
    ledger = read_execution_ledger(root, paths.run_id, limit=tail)
    activity = read_hive_activity(paths, limit=tail)
    protocol = collect_protocol_state(paths.run_dir)
    return {
        "schema_version": 1,
        "run_id": paths.run_id,
        "task": state.get("user_request"),
        "phase": state.get("phase"),
        "status": state.get("status"),
        "health": summarize_health(board, ledger, protocol),
        "next": board.get("next") or {},
        "authority": summarize_authority(protocol, ledger),
        "agents": summarize_agents(board),
        "blocked": summarize_blocks(ledger, protocol),
        "log": build_log_rows(activity, ledger, tail=tail, show_paths=show_paths),
        "paths_hidden": not show_paths,
    }


def build_memoryos_observability_report(
    root: Path,
    run_id: str | None = None,
    *,
    tail: int = 64,
    show_paths: bool = False,
) -> dict[str, Any]:
    """Build a graph/event read model that MemoryOS can render as a neural map."""
    paths, state = load_run(root, run_id)
    board = run_board(root, paths.run_id)
    ledger = read_execution_ledger(root, paths.run_id, limit=tail)
    activity = read_hive_activity(paths, limit=tail)
    protocol = collect_protocol_state(paths.run_dir)
    live = build_live_report(root, paths.run_id, tail=tail, show_paths=show_paths)

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    run_node_id = stable_node_id("run", paths.run_id)
    nodes.append(
        {
            "id": run_node_id,
            "type": "hive_run",
            "label": str(state.get("user_request") or paths.run_id),
            "status": str(state.get("status") or "unknown"),
            "properties": {
                "run_id": paths.run_id,
                "project": state.get("project"),
                "task": state.get("user_request"),
                "phase": state.get("phase"),
                "health": live.get("health"),
                "next": safe_projection(live.get("next") or {}, show_paths=show_paths),
            },
        }
    )

    for agent in board.get("agents", []) or []:
        name = str(agent.get("name") or "agent")
        agent_node_id = stable_node_id("run", paths.run_id, "agent", name)
        nodes.append(
            {
                "id": agent_node_id,
                "type": "agent_turn",
                "label": name,
                "status": str(agent.get("status") or "pending"),
                "properties": safe_projection(agent, show_paths=show_paths),
            }
        )
        edges.append({"source": agent_node_id, "target": run_node_id, "type": "participates_in"})

    add_protocol_projection(nodes, edges, protocol, run_node_id, paths.run_id, show_paths=show_paths)
    add_memory_draft_projection(nodes, edges, paths.run_dir, run_node_id, paths.run_id, show_paths=show_paths)
    add_disagreement_projection(nodes, edges, paths.run_dir, run_node_id, paths.run_id, show_paths=show_paths)

    for index, row in enumerate(build_log_rows(activity, ledger, tail=tail, show_paths=show_paths)):
        event_id = stable_node_id("run", paths.run_id, "event", str(index), row.get("ts"), row.get("kind"))
        events.append(
            {
                "id": event_id,
                "type": str(row.get("kind") or "event"),
                "ts": row.get("ts"),
                "actor": row.get("actor"),
                "summary": row.get("summary"),
                "refs": [run_node_id],
            }
        )

    for record in ledger:
        step = record.get("step_id")
        if step:
            step_node_id = stable_node_id("run", paths.run_id, "step", str(step))
            if not any(node.get("id") == step_node_id for node in nodes):
                nodes.append(
                    {
                        "id": step_node_id,
                        "type": "workflow_step",
                        "label": str(step),
                        "status": str(record.get("status") or "observed"),
                        "properties": {"step_id": step},
                    }
                )
                edges.append({"source": step_node_id, "target": run_node_id, "type": "part_of"})

    return {
        "schema_version": 1,
        "kind": "memoryos_neural_map_read_model",
        "producer": "hive",
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "paths_hidden": not show_paths,
        "run": {
            "id": paths.run_id,
            "task": state.get("user_request"),
            "project": state.get("project"),
            "phase": state.get("phase"),
            "status": state.get("status"),
            "health": live.get("health"),
            "next": safe_projection(live.get("next") or {}, show_paths=show_paths),
            "authority": safe_projection(live.get("authority") or {}, show_paths=show_paths),
            "blocked": live.get("blocked") or [],
        },
        "graph": {"nodes": nodes, "edges": edges},
        "events": events,
        "summary": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "event_count": len(events),
            "memory_draft_count": sum(1 for node in nodes if node.get("type") == "memory_draft"),
            "disagreement_count": sum(1 for node in nodes if node.get("type") == "disagreement"),
            "authority_gate_count": sum(1 for node in nodes if node.get("type") == "authority_gate"),
        },
    }


def add_protocol_projection(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    protocol: dict[str, Any],
    run_node_id: str,
    run_id: str,
    *,
    show_paths: bool,
) -> None:
    for intent in protocol.get("intents") or []:
        intent_id = str(intent.get("intent_id") or "intent")
        node_id = stable_node_id("run", run_id, "authority", intent_id)
        decision = next((item for item in protocol.get("decisions") or [] if item.get("intent_id") == intent_id), {})
        proof = next((item for item in protocol.get("proofs") or [] if item.get("intent_id") == intent_id), {})
        nodes.append(
            {
                "id": node_id,
                "type": "authority_gate",
                "label": str(intent.get("step_id") or intent_id),
                "status": str(decision.get("decision") or "proposed"),
                "properties": {
                    "intent_id": intent_id,
                    "step_id": intent.get("step_id"),
                    "owner_role": intent.get("owner_role"),
                    "provider": intent.get("provider"),
                    "authority_class": intent.get("authority_class"),
                    "risk_level": intent.get("risk_level"),
                    "bypass_mode": intent.get("bypass_mode"),
                    "decision": decision.get("decision"),
                    "missing_voters": decision.get("missing_voters") or [],
                    "proof_status": proof.get("status"),
                },
            }
        )
        edges.append({"source": node_id, "target": run_node_id, "type": "gates"})

        for vote in votes_for_intent(protocol, intent_id):
            voter = str(vote.get("voter_role") or "voter")
            vote_node_id = stable_node_id("run", run_id, "vote", intent_id, voter)
            nodes.append(
                {
                    "id": vote_node_id,
                    "type": "authority_vote",
                    "label": voter,
                    "status": str(vote.get("vote") or "unknown"),
                    "properties": safe_projection(vote, show_paths=show_paths),
                }
            )
            edges.append({"source": vote_node_id, "target": node_id, "type": "votes_on"})


def votes_for_intent(protocol: dict[str, Any], intent_id: str) -> list[dict[str, Any]]:
    latest = protocol.get("latest_intent") or {}
    if latest.get("intent_id") == intent_id:
        return [vote for vote in protocol.get("votes") or [] if isinstance(vote, dict)]
    return []


def add_memory_draft_projection(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    run_dir: Path,
    run_node_id: str,
    run_id: str,
    *,
    show_paths: bool,
) -> None:
    for index, draft in enumerate(read_memory_drafts(run_dir), start=1):
        node_id = stable_node_id("run", run_id, "memory_draft", str(index))
        nodes.append(
            {
                "id": node_id,
                "type": "memory_draft",
                "label": str(draft.get("type") or "memory_draft"),
                "status": str(draft.get("status") or "draft"),
                "properties": safe_projection(draft, show_paths=show_paths),
            }
        )
        edges.append({"source": node_id, "target": run_node_id, "type": "drafted_from"})


def add_disagreement_projection(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    run_dir: Path,
    run_node_id: str,
    run_id: str,
    *,
    show_paths: bool,
) -> None:
    for index, disagreement in enumerate(read_disagreements(run_dir), start=1):
        node_id = stable_node_id("run", run_id, "disagreement", str(index))
        nodes.append(
            {
                "id": node_id,
                "type": "disagreement",
                "label": str(disagreement.get("axis") or disagreement.get("topic") or "disagreement"),
                "status": str(disagreement.get("status") or "open"),
                "properties": safe_projection(disagreement, show_paths=show_paths),
            }
        )
        edges.append({"source": node_id, "target": run_node_id, "type": "contests"})


def read_memory_drafts(run_dir: Path) -> list[dict[str, Any]]:
    data = read_json_file(run_dir / "memory_drafts.json")
    raw = data.get("memory_drafts") if isinstance(data, dict) else []
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def read_disagreements(run_dir: Path) -> list[dict[str, Any]]:
    for path in (run_dir / "disagreements.json", run_dir / "artifacts" / "disagreements.json"):
        data = read_json_file(path)
        raw = data.get("disagreements") if isinstance(data, dict) else data
        if isinstance(raw, list):
            return [item for item in raw if isinstance(item, dict)]
    return []


def read_json_file(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def safe_projection(value: Any, *, show_paths: bool) -> Any:
    if isinstance(value, dict):
        return {str(key): safe_projection(item, show_paths=show_paths) for key, item in value.items()}
    if isinstance(value, list):
        return [safe_projection(item, show_paths=show_paths) for item in value]
    if isinstance(value, str):
        return sanitize_summary(value, show_paths=show_paths)
    return value


def stable_node_id(*parts: Any) -> str:
    clean = [slug(str(part)) for part in parts if part is not None and str(part) != ""]
    return "hive:" + ":".join(clean)


def slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return text.strip("_") or "item"


def collect_protocol_state(run_dir: Path) -> dict[str, Any]:
    intents = read_json_dir(run_dir / "execution_intents")
    decisions = {str(item.get("intent_id")): item for item in read_json_dir(run_dir / "execution_decisions")}
    proofs = {str(item.get("intent_id")): item for item in read_json_dir(run_dir / "execution_proofs")}
    votes_by_intent: dict[str, list[dict[str, Any]]] = {}
    votes_root = run_dir / "execution_votes"
    if votes_root.exists():
        for intent_dir in sorted(path for path in votes_root.iterdir() if path.is_dir()):
            votes_by_intent[intent_dir.name] = read_json_dir(intent_dir)
    latest = sorted(intents, key=lambda item: str(item.get("created_at") or ""))[-1:] or []
    latest_intent = latest[0] if latest else None
    latest_id = str(latest_intent.get("intent_id")) if latest_intent else None
    return {
        "latest_intent": latest_intent,
        "latest_decision": decisions.get(latest_id) if latest_id else None,
        "latest_proof": proofs.get(latest_id) if latest_id else None,
        "votes": votes_by_intent.get(latest_id, []) if latest_id else [],
        "intents": intents,
        "decisions": list(decisions.values()),
        "proofs": list(proofs.values()),
    }


def read_json_dir(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for item in sorted(path.glob("*.json")):
        try:
            data = json.loads(item.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            rows.append(data)
    return rows


def summarize_health(board: dict[str, Any], ledger: list[dict[str, Any]], protocol: dict[str, Any]) -> dict[str, Any]:
    missing_required = [
        item.get("name")
        for item in board.get("artifacts", [])
        if item.get("status") != "ok" and item.get("phase_class") == "required"
    ]
    hard_blocks = [record for record in ledger if str(record.get("event")) in {"step_blocked", "policy_blocked", "operator_blocked"}]
    decision = protocol.get("latest_decision") or {}
    label = "blocked" if hard_blocks or decision.get("decision") in {"blocked", "ask_user", "needs_referee"} else ("needs_review" if missing_required else "good")
    return {
        "label": label,
        "missing_required": missing_required,
        "blocked_count": len(hard_blocks),
        "latest_decision": decision.get("decision"),
    }


def summarize_authority(protocol: dict[str, Any], ledger: list[dict[str, Any]]) -> dict[str, Any]:
    intent = protocol.get("latest_intent") or {}
    decision = protocol.get("latest_decision") or {}
    proof = protocol.get("latest_proof") or {}
    votes = protocol.get("votes") or []
    if not intent:
        latest_gate = next((record for record in reversed(ledger) if record.get("event") == "step_blocked"), {})
        return {
            "state": latest_gate.get("status") or "none",
            "step_id": latest_gate.get("step_id"),
            "decision": None,
            "missing_voters": [],
            "bypass_mode": latest_gate.get("bypass_mode"),
            "proof": None,
        }
    return {
        "state": decision.get("decision") or ("voting" if votes else "proposed"),
        "step_id": intent.get("step_id"),
        "intent_id": intent.get("intent_id"),
        "authority_class": intent.get("authority_class"),
        "risk_level": intent.get("risk_level"),
        "decision": decision.get("decision"),
        "missing_voters": decision.get("missing_voters") or [],
        "votes": {vote.get("voter_role"): vote.get("vote") for vote in votes},
        "bypass_mode": intent.get("bypass_mode"),
        "proof": proof.get("status"),
    }


def summarize_agents(board: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    for agent in board.get("agents", [])[:8]:
        rows.append({"name": str(agent.get("name") or "agent"), "status": str(agent.get("status") or "pending")})
    return rows


def summarize_blocks(ledger: list[dict[str, Any]], protocol: dict[str, Any]) -> list[str]:
    blocks: list[str] = []
    for record in ledger:
        event = str(record.get("event") or "")
        status = str(record.get("status") or "")
        if event in {"step_blocked", "policy_blocked", "operator_blocked"} or status in {"protocol_gate", "reversibility_gate"}:
            step = record.get("step_id") or "run"
            message = record.get("message") or status or event
            blocks.append(f"{step}: {message}")
    decision = protocol.get("latest_decision") or {}
    if decision.get("missing_voters"):
        blocks.append(f"{decision.get('intent_id')}: waiting for {', '.join(decision.get('missing_voters') or [])}")
    return blocks[-5:]


def build_log_rows(
    activity: list[dict[str, Any]],
    ledger: list[dict[str, Any]],
    *,
    tail: int,
    show_paths: bool,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in activity:
        rows.append(
            {
                "ts": str(item.get("ts") or ""),
                "actor": str(item.get("actor") or "hive"),
                "kind": str(item.get("action") or "activity"),
                "summary": sanitize_summary(str(item.get("summary") or ""), show_paths=show_paths),
            }
        )
    for item in ledger:
        rows.append(
            {
                "ts": str(item.get("ts") or ""),
                "actor": str(item.get("actor") or "ledger"),
                "kind": str(item.get("event") or "event"),
                "summary": summarize_ledger_record(item, show_paths=show_paths),
            }
        )
    rows.sort(key=lambda row: row.get("ts", ""))
    return rows[-tail:]


def sanitize_summary(summary: str, *, show_paths: bool) -> str:
    if show_paths:
        return summary
    text = re.sub(r"\b(artifact|result|log|output|path)=\S+", r"\1=<hidden>", summary)
    text = re.sub(r"(?<!\w)\.runs/[^\s,;]+", "<hidden>", text)
    text = re.sub(r"/home/user/[^\s,;]+", "<hidden>", text)
    return text


def summarize_ledger_record(record: dict[str, Any], *, show_paths: bool) -> str:
    event = str(record.get("event") or "event")
    step = record.get("step_id") or "run"
    status = record.get("status") or "-"
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    if event == "intent_proposed":
        return f"intent proposed for {step}: {extra.get('authority_class')} risk={extra.get('risk_level')}"
    if event == "vote_cast":
        return f"vote {status} for {step}"
    if event == "quorum_decided":
        missing = extra.get("missing_voters") or []
        suffix = f"; waiting for {', '.join(missing)}" if missing else ""
        return f"decision {status} for {step}{suffix}"
    if event == "step_blocked":
        return f"blocked {step}: {record.get('message') or status}"
    if event in {"step_started", "step_completed", "step_failed", "step_skipped"}:
        files = record.get("files_touched") or []
        suffix = f"; files={len(files)}" if files and not show_paths else ""
        if show_paths and files:
            suffix = "; files=" + ", ".join(str(path) for path in files[:3])
        return f"{step} {status}{suffix}"
    if event.startswith("scheduler_round"):
        return f"scheduler {status}"
    return f"{step}: {status}"


def format_live_report(report: dict[str, Any], *, show_paths: bool = False) -> str:
    health = report.get("health") or {}
    next_action = report.get("next") or {}
    authority = report.get("authority") or {}
    lines = [
        "Hive Live",
        f"Run: {report.get('run_id')}  Health: {health.get('label')}  State: {report.get('phase')}/{report.get('status')}",
        f"Task: {report.get('task')}",
        "",
        f"Next: {next_action.get('command') or '-'}",
        f"Reason: {next_action.get('reason') or '-'}",
        "",
        "Authority:",
        format_authority(authority),
    ]
    blocks = report.get("blocked") or []
    if blocks:
        lines.extend(["", "Blocked / Waiting:"])
        lines.extend(f"- {item}" for item in blocks)
    agents = report.get("agents") or []
    if agents:
        lines.extend(["", "Agents:"])
        lines.extend(f"- {agent.get('name')}: {agent.get('status')}" for agent in agents)
    lines.extend(["", "Live Log:"])
    logs = report.get("log") or []
    if not logs:
        lines.append("- no live log yet")
    for row in logs:
        ts = short_timestamp(str(row.get("ts") or ""))
        lines.append(f"{ts}  {row.get('actor'):<22} {row.get('kind'):<24} {row.get('summary')}")
    if not show_paths:
        lines.extend(["", "Paths hidden. Use --paths for debug/export details."])
    return "\n".join(lines)


def format_authority(authority: dict[str, Any]) -> str:
    if not authority or authority.get("state") == "none":
        return "- no active protocol intent"
    missing = authority.get("missing_voters") or []
    votes = authority.get("votes") or {}
    chunks = [
        f"- step: {authority.get('step_id')}",
        f"  state: {authority.get('state')}",
        f"  class: {authority.get('authority_class') or '-'}",
        f"  risk: {authority.get('risk_level') or '-'}",
        f"  bypass: {authority.get('bypass_mode') or '-'}",
    ]
    if votes:
        chunks.append("  votes: " + ", ".join(f"{k}={v}" for k, v in sorted(votes.items())))
    if missing:
        chunks.append("  waiting: " + ", ".join(str(voter) for voter in missing))
    if authority.get("proof"):
        chunks.append(f"  proof: {authority.get('proof')}")
    return "\n".join(chunks)
