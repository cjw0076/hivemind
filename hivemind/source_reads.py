"""Per-run source-read registry for Hive agents."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .harness import load_run, now_iso


SCHEMA_VERSION = "hive.source_reads.v1"


def registry_path(root: Path, run_id: str | None = None) -> Path:
    paths, _ = load_run(root, run_id)
    return paths.artifacts / "source_reads.json"


def normalize_source_ref(source: str) -> str:
    return " ".join(source.strip().split())


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def source_id(source: str) -> str:
    return f"src_{stable_hash(normalize_source_ref(source))[:16]}"


def interpretation_hash(interpretation: str | None) -> str | None:
    if not interpretation:
        return None
    return f"interp_{stable_hash(interpretation.strip())[:16]}"


def empty_registry(run_id: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "hive_source_read_registry",
        "run_id": run_id,
        "records": [],
    }


def load_registry(root: Path, run_id: str | None = None) -> dict[str, Any]:
    paths, _ = load_run(root, run_id)
    path = paths.artifacts / "source_reads.json"
    if not path.exists():
        return empty_registry(paths.run_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return empty_registry(paths.run_id)
    if not isinstance(data, dict):
        return empty_registry(paths.run_id)
    records = data.get("records")
    if not isinstance(records, list):
        records = []
    return {
        "schema_version": data.get("schema_version") or SCHEMA_VERSION,
        "kind": data.get("kind") or "hive_source_read_registry",
        "run_id": data.get("run_id") or paths.run_id,
        "records": [item for item in records if isinstance(item, dict)],
    }


def save_registry(root: Path, registry: dict[str, Any], run_id: str | None = None) -> Path:
    path = registry_path(root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def record_source_read(
    root: Path,
    *,
    run_id: str | None = None,
    agent: str,
    source: str,
    role: str = "",
    source_kind: str = "file",
    interpretation: str | None = None,
    verification_state: str = "observed",
) -> dict[str, Any]:
    """Append a path/ref-only source-read record to the current run."""
    paths, _ = load_run(root, run_id)
    normalized = normalize_source_ref(source)
    record = {
        "record_id": f"sr_{stable_hash(f'{paths.run_id}:{agent}:{role}:{normalized}:{interpretation or ''}')[:16]}",
        "run_id": paths.run_id,
        "source_id": source_id(normalized),
        "source_ref": normalized,
        "source_kind": source_kind,
        "agent": agent,
        "role": role or agent,
        "interpretation": interpretation or "",
        "interpretation_hash": interpretation_hash(interpretation),
        "verification_state": verification_state,
        "read_at": now_iso(),
        "privacy": {
            "raw_source_body_included": False,
            "path_or_ref_only": True,
        },
    }
    registry = load_registry(root, paths.run_id)
    records = registry.setdefault("records", [])
    existing_ids = {item.get("record_id") for item in records if isinstance(item, dict)}
    if record["record_id"] not in existing_ids:
        records.append(record)
    save_registry(root, registry, paths.run_id)
    return record


def summarize_source_reads(root: Path, run_id: str | None = None, *, show_paths: bool = False) -> dict[str, Any]:
    """Summarize shared-source reads and divergent interpretations."""
    registry = load_registry(root, run_id)
    records = registry.get("records") or []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(str(record.get("source_id")), []).append(record)

    sources: list[dict[str, Any]] = []
    divergent: list[dict[str, Any]] = []
    shared: list[dict[str, Any]] = []
    for sid, items in sorted(grouped.items()):
        agents = sorted({str(item.get("agent") or "") for item in items if item.get("agent")})
        interp_hashes = sorted({str(item.get("interpretation_hash")) for item in items if item.get("interpretation_hash")})
        source_ref = str(items[0].get("source_ref") or "")
        source_item: dict[str, Any] = {
            "source_id": sid,
            "source_ref": source_ref if show_paths else mask_source_ref(source_ref),
            "read_count": len(items),
            "agents": agents,
            "interpretation_count": len(interp_hashes),
            "shared": len(agents) > 1,
            "divergent": len(agents) > 1 and len(interp_hashes) > 1,
        }
        sources.append(source_item)
        if source_item["shared"]:
            shared.append(source_item)
        if source_item["divergent"]:
            divergent.append(
                {
                    "source_id": sid,
                    "source_ref": source_item["source_ref"],
                    "agents": agents,
                    "interpretation_count": len(interp_hashes),
                    "recommended_action": "reconcile_interpretations",
                }
            )
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "hive_source_read_summary",
        "run_id": registry.get("run_id"),
        "paths_hidden": not show_paths,
        "record_count": len(records),
        "source_count": len(sources),
        "shared_source_count": len(shared),
        "divergent_source_count": len(divergent),
        "sources": sources,
        "divergent_sources": divergent,
    }


def mask_source_ref(source_ref: str) -> str:
    """Keep enough signal for operators without exposing full local paths."""
    if not source_ref:
        return ""
    path = Path(source_ref)
    if path.is_absolute():
        return f".../{path.name}"
    parts = path.parts
    if len(parts) > 3:
        return "/".join(("...",) + parts[-3:])
    return source_ref


def format_source_read_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"Hive Source Reads  Run {summary.get('run_id')}",
        f"records={summary.get('record_count')} sources={summary.get('source_count')} shared={summary.get('shared_source_count')} divergent={summary.get('divergent_source_count')}",
        "",
        "Sources",
    ]
    for item in summary.get("sources") or []:
        lines.append(
            f"  - {item.get('source_ref')} agents={','.join(item.get('agents') or [])} interpretations={item.get('interpretation_count')} divergent={item.get('divergent')}"
        )
    if not (summary.get("sources") or []):
        lines.append("  none")
    if summary.get("divergent_sources"):
        lines.extend(["", "Reconcile"])
        for item in summary.get("divergent_sources") or []:
            lines.append(f"  - {item.get('source_ref')} agents={','.join(item.get('agents') or [])}")
    return "\n".join(lines)
