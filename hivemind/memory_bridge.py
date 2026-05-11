"""MemoryOS context bridge helpers for Hive runs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from .utils import now_iso


def build_memoryos_context_report(root: Path, paths: Any, state: dict[str, Any]) -> dict[str, Any]:
    """Call MemoryOS context build and return a run-local report.

    This module deliberately does not mutate run_state. The harness remains the
    authority for state updates and event emission.
    """
    memoryos_source_root = Path(os.environ.get("HIVE_MEMORYOS_SOURCE_ROOT") or (root.parent / "memoryOS")).resolve()
    memoryos_root = Path(os.environ.get("HIVE_MEMORYOS_ROOT") or memoryos_source_root).resolve()
    memoryos_cli = memoryos_source_root / "memoryos" / "cli.py"
    command = [
        sys.executable,
        "-m",
        "memoryos.cli",
        "--root",
        memoryos_root.as_posix(),
        "context",
        "build",
        "--for",
        "hive",
        "--task",
        str(state.get("user_request") or ""),
        "--json",
    ]
    artifact: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "phase": "context_retrieval",
        "status": "unavailable",
        "memoryos_root": memoryos_root.as_posix(),
        "memoryos_source_root": memoryos_source_root.as_posix(),
        "command": command,
        "trace_id": None,
        "accepted_memory_ids": [],
        "accepted_memories_used": [],
        "context_items": 0,
        "raw_refs": ["docs/HIVE_WORKING_METHOD.md", paths.context_pack.relative_to(root).as_posix()],
    }
    if not memoryos_cli.exists():
        artifact["reason"] = "MemoryOS CLI source not found next to Hive Mind workspace."
        return artifact
    if os.environ.get("HIVE_DISABLE_MEMORYOS") in {"1", "true", "yes"}:
        artifact["reason"] = "MemoryOS bridge disabled by HIVE_DISABLE_MEMORYOS."
        return artifact
    try:
        result = subprocess.run(command, cwd=memoryos_source_root, text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        artifact.update({"status": "failed", "reason": str(exc)})
        return artifact
    artifact.update(
        {
            "returncode": result.returncode,
            "stderr": result.stderr.strip()[-4000:],
        }
    )
    if result.returncode != 0:
        artifact.update({"status": "failed", "reason": "memoryos context build failed"})
        return artifact
    try:
        pack = json.loads(result.stdout)
    except json.JSONDecodeError:
        artifact.update(
            {
                "status": "failed",
                "reason": "memoryos context build did not emit JSON",
                "stdout_excerpt": result.stdout.strip()[-4000:],
            }
        )
        return artifact
    selected_ids = extract_memoryos_context_ids(pack)
    context_items = int(pack.get("context_items") or len(selected_ids))
    artifact.update(
        {
            "status": "available" if selected_ids or context_items else "empty",
            "trace_id": pack.get("trace_id"),
            "accepted_memory_ids": selected_ids,
            "accepted_memories_used": selected_ids,
            "context_items": context_items,
            "feedback_directives_count": len(pack.get("feedback_directives") or []),
            "total_accepted": pack.get("total_accepted", 0),
            "total_available": pack.get("total_available", 0),
            "excluded_count": len(pack.get("excluded_items") or []),
            "token_estimate": pack.get("token_estimate", 0),
            "pack": pack,
        }
    )
    write_memoryos_context_pack(paths, pack)
    return artifact


def extract_memoryos_context_ids(pack: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for section in ("decisions", "constraints", "open_questions", "recent_actions", "other"):
        for item in pack.get(section) or []:
            if not isinstance(item, dict):
                continue
            item_id = str(item.get("id") or "").strip()
            if item_id and item_id not in seen:
                seen.add(item_id)
                ids.append(item_id)
    explain = pack.get("explain") if isinstance(pack.get("explain"), dict) else {}
    for item_id in explain.get("selected_ids") or []:
        item_id = str(item_id).strip()
        if item_id and item_id not in seen:
            seen.add(item_id)
            ids.append(item_id)
    return ids


def write_memoryos_context_pack(paths: Any, pack: dict[str, Any]) -> None:
    lines = [
        "# Context Pack",
        "",
        "## User Request",
        str(pack.get("task") or ""),
        "",
        "## MemoryOS Accepted Context",
        f"- trace_id: `{pack.get('trace_id') or 'none'}`",
        f"- role: `{pack.get('role') or 'hive'}`",
        f"- audience: `{pack.get('audience') or 'local'}`",
        f"- accepted_memory_ids: {', '.join(extract_memoryos_context_ids(pack)) or 'none'}",
        "",
    ]
    for title, key in [
        ("Decisions", "decisions"),
        ("Constraints", "constraints"),
        ("Open Questions", "open_questions"),
        ("Recent Actions", "recent_actions"),
        ("Other", "other"),
    ]:
        items = pack.get(key) or []
        if not items:
            continue
        lines.append(f"## {title}")
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id") or ""
            item_type = item.get("type") or ""
            content = str(item.get("content") or "").replace("\n", " ")
            lines.append(f"- [{item_type}] {content} (`{item_id}`)")
            refs = item.get("raw_refs") or []
            if refs:
                lines.append(f"  refs: {', '.join(str(ref) for ref in refs[:5])}")
        lines.append("")
    feedback_directives = pack.get("feedback_directives") or []
    if feedback_directives:
        lines.append("## Feedback Directives")
        for item in feedback_directives:
            if not isinstance(item, dict):
                continue
            memory_id = item.get("memory_id") or item.get("id") or ""
            directive = str(item.get("directive") or "").replace("\n", " ")
            item_type = item.get("type") or "memory"
            lines.append(f"- [{item_type}] {directive} (`{memory_id}`)")
        lines.append("")
    lines.extend(
        [
            "## Retrieval Stats",
            f"- total_accepted: {pack.get('total_accepted', 0)}",
            f"- total_available: {pack.get('total_available', 0)}",
            f"- context_items: {pack.get('context_items', 0)}",
            f"- feedback_directives: {len(feedback_directives)}",
            f"- token_estimate: {pack.get('token_estimate', 0)}",
            "",
        ]
    )
    paths.context_pack.write_text("\n".join(lines), encoding="utf-8")
