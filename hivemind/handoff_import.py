"""Compatibility importer for old shared-folder HANDOFF.json loops."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .harness import append_event, create_run, update_state, write_json


SCHEMA_VERSION = "hive.handoff_import.v1"


def import_handoff(root: Path, source: Path, *, show_paths: bool = False) -> dict[str, Any]:
    """Import a HANDOFF.json file or directory into a standard Hive run."""
    source_path = resolve_handoff_source(source)
    payload = load_handoff_payload(source_path)
    objective = handoff_objective(payload)
    paths = create_run(root, objective, project="Hive Mind", task_type="handoff_import")
    imported = build_import_artifact(payload, source_path, paths.run_id, show_paths=show_paths)

    artifact_path = paths.artifacts / "handoff_import.json"
    write_json(artifact_path, imported)
    paths.context_pack.write_text(format_context_pack(imported), encoding="utf-8")
    paths.handoff.write_text(format_handoff_yaml(imported), encoding="utf-8")
    paths.final_report.write_text(format_final_report(imported), encoding="utf-8")
    state = update_state(
        paths,
        phase="imported",
        status="imported",
        latest_event="handoff_imported",
    )
    artifacts = dict(state.get("artifacts") or {})
    artifacts["handoff_import"] = artifact_path.relative_to(root).as_posix()
    update_state(paths, artifacts=artifacts)
    append_event(
        paths,
        "handoff_imported",
        {
            "artifact": artifact_path.relative_to(root).as_posix(),
            "source_kind": imported["source"]["kind"],
            "task_id": imported["task"].get("id"),
        },
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "hive_handoff_import",
        "run_id": paths.run_id,
        "status": "imported",
        "source": imported["source"],
        "artifact": artifact_path.relative_to(root).as_posix(),
        "inspect_command": f"hive inspect {paths.run_id}",
    }


def resolve_handoff_source(source: Path) -> Path:
    candidate = source.resolve()
    if candidate.is_dir():
        candidate = candidate / "HANDOFF.json"
    if not candidate.exists():
        raise FileNotFoundError(f"HANDOFF.json not found: {candidate}")
    if candidate.name != "HANDOFF.json":
        raise ValueError("handoff import expects a HANDOFF.json file or a directory containing HANDOFF.json")
    return candidate


def load_handoff_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed HANDOFF.json: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("HANDOFF.json must contain a JSON object")
    return payload


def handoff_objective(payload: dict[str, Any]) -> str:
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
    for value in (
        task.get("description"),
        task.get("title"),
        task.get("id"),
        payload.get("north_star"),
        payload.get("phase"),
    ):
        if isinstance(value, str) and value.strip():
            return truncate(value.strip(), 180)
    return "Imported HANDOFF.json shared-folder loop"


def build_import_artifact(payload: dict[str, Any], source_path: Path, run_id: str, *, show_paths: bool) -> dict[str, Any]:
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
    queue = payload.get("task_queue") if isinstance(payload.get("task_queue"), list) else []
    task_summary = {
        "id": clean_string(task.get("id")),
        "title": clean_string(task.get("title")),
        "description": truncate(clean_string(task.get("description")), 500),
        "owner": clean_string(task.get("owner")),
        "turn_type": clean_string(task.get("turn_type")),
        "status": clean_string(task.get("status")),
        "acceptance_criteria": clean_string_list(task.get("acceptance_criteria"), limit=12),
        "files_to_touch": clean_string_list(task.get("files_to_touch"), limit=30),
    }
    imported_queue = [summarize_queue_item(item) for item in queue if isinstance(item, dict)]
    imported_queue = imported_queue[:50]
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "hive_handoff_import_artifact",
        "run_id": run_id,
        "source": {
            "kind": "handoff_json",
            "file_name": source_path.name,
            "protocol_version": payload.get("protocol_version"),
            "phase": clean_string(payload.get("phase")),
            "turn": clean_string(payload.get("turn")),
            "locked": bool(payload.get("locked")) if "locked" in payload else None,
            "updated_at": clean_string(payload.get("updated_at")),
            "path": source_path.as_posix() if show_paths else None,
        },
        "task": task_summary,
        "queue_summary": {
            "total_items": len(queue),
            "imported_items": len(imported_queue),
            "items": imported_queue,
        },
        "privacy": {
            "raw_source_body_stored": False,
            "paths_hidden": not show_paths,
            "omitted_fields": ["notes", "tests", "raw logs", "provider stdout/stderr", "private export bodies"],
        },
    }


def summarize_queue_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": clean_string(item.get("id")),
        "title": clean_string(item.get("title")),
        "owner": clean_string(item.get("owner")),
        "status": clean_string(item.get("status")),
    }


def format_context_pack(imported: dict[str, Any]) -> str:
    task = imported["task"]
    queue = imported["queue_summary"]
    lines = [
        f"# Imported HANDOFF Context: {imported['run_id']}",
        "",
        "Source: HANDOFF.json compatibility import",
        f"Phase: {imported['source'].get('phase') or 'unknown'}",
        f"Turn: {imported['source'].get('turn') or 'unknown'}",
        "",
        "## Active Task",
        f"- id: {task.get('id') or 'unknown'}",
        f"- title: {task.get('title') or 'unknown'}",
        f"- owner: {task.get('owner') or 'unknown'}",
        f"- status: {task.get('status') or 'unknown'}",
        "",
        "## Queue",
        f"- total_items: {queue.get('total_items')}",
        f"- imported_items: {queue.get('imported_items')}",
        "",
        "Privacy: raw HANDOFF body and provider outputs were not copied.",
    ]
    return "\n".join(lines) + "\n"


def format_handoff_yaml(imported: dict[str, Any]) -> str:
    task = imported["task"]
    criteria = task.get("acceptance_criteria") or ["Imported run is inspectable."]
    files = task.get("files_to_touch") or []
    lines = [
        "from_agent: handoff-import",
        "to_agent: codex",
        f"objective: {json.dumps(task.get('description') or task.get('title') or 'Imported HANDOFF.json', ensure_ascii=False)}",
        "constraints:",
        "  - Imported from HANDOFF.json compatibility surface.",
        "  - Do not infer accepted memory from imported handoff state.",
        "  - Keep raw provider output and private exports out of imported artifacts.",
        "acceptance_criteria:",
    ]
    lines.extend(f"  - {json.dumps(item, ensure_ascii=False)}" for item in criteria)
    if files:
        lines.append("files_or_domains:")
        lines.extend(f"  - {json.dumps(item, ensure_ascii=False)}" for item in files[:30])
    return "\n".join(lines) + "\n"


def format_final_report(imported: dict[str, Any]) -> str:
    task = imported["task"]
    return "\n".join(
        [
            f"# Final Report: {imported['run_id']}",
            "",
            f"- Task: {task.get('title') or task.get('description') or 'Imported HANDOFF.json'}",
            "- Status: imported",
            f"- Source phase: {imported['source'].get('phase') or 'unknown'}",
            f"- Queue items summarized: {imported['queue_summary'].get('imported_items')}",
            "",
            "## Privacy",
            "",
            "Raw HANDOFF body, provider logs, prompts, stdout/stderr bodies, and private export bodies were not copied.",
            "",
            "## Recent Events",
            "",
            "- HANDOFF.json imported into Hive run artifacts.",
            "",
        ]
    )


def clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    return truncate(text, 240) if text else None


def clean_string_list(value: Any, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = clean_string(item)
        if text:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def truncate(value: str | None, max_length: int) -> str | None:
    if value is None or len(value) <= max_length:
        return value
    return value[: max_length - 3].rstrip() + "..."
