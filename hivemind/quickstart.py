"""Public-alpha quickstart demo for Hive Mind."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .harness import add_state_artifact, append_hive_activity, demo_live_run, load_run
from .inspect_run import build_inspect_report
from .live import build_memoryos_observability_report
from .utils import now_iso
from .workloop import append_execution_ledger


DEFAULT_QUICKSTART_TASK = "Show why Hive Mind is useful beyond direct provider CLI"


def quickstart_demo(root: Path, task: str = DEFAULT_QUICKSTART_TASK, *, delay: float = 0.0) -> dict[str, Any]:
    """Create a provider-free demo that shows Hive's public-alpha value loop."""
    demo = demo_live_run(root, task=task, delay=delay)
    run_id = str(demo["run_id"])
    paths, _state = load_run(root, run_id)
    append_execution_ledger(
        root,
        run_id,
        "quickstart_demo",
        actor="hive-mind",
        status="completed",
        artifact=(paths.run_dir / "memory_drafts.json").relative_to(root).as_posix(),
        extra={"demo": "quickstart", "public_alpha_value": True},
    )
    inspect = build_inspect_report(root, run_id, show_paths=False)
    memoryos = build_memoryos_observability_report(root, run_id, tail=30, show_paths=False)
    graph = memoryos.get("graph") if isinstance(memoryos.get("graph"), dict) else {}
    report = {
        "schema_version": 1,
        "kind": "hive_quickstart_demo",
        "generated_at": now_iso(),
        "run_id": run_id,
        "task": task,
        "status": "ready",
        "value_claim": (
            "Hive Mind is not faster than direct CLI for trivial commands; it is useful "
            "when a run needs auditable multi-agent coordination, receipts, inspection, "
            "memory drafts, and a MemoryOS-compatible read model."
        ),
        "wow_path": [
            "prompt intake",
            "role routing",
            "agent artifacts",
            "verification",
            "memory draft",
            "inspect report",
            "MemoryOS observability read model",
        ],
        "demo": demo,
        "inspect_summary": {
            "verdict": inspect.get("verdict"),
            "ledger_records": (inspect.get("ledger") or {}).get("record_count", 0),
            "provider_result_count": len(inspect.get("provider_results") or []),
            "local_worker_result_count": len(inspect.get("local_worker_results") or []),
            "next": inspect.get("next"),
        },
        "memoryos_summary": {
            "kind": memoryos.get("kind"),
            "contract": memoryos.get("memoryos_contract"),
            "nodes": len(graph.get("nodes") or []),
            "edges": len(graph.get("edges") or []),
            "events": len(memoryos.get("events") or []),
            "paths_hidden": memoryos.get("paths_hidden"),
        },
        "commands": [
            f"hive inspect {run_id}",
            f"hive live --run-id {run_id}",
            f"hive live --run-id {run_id} --memoryos --json",
            f"hive tui --run-id {run_id}",
        ],
    }
    out_path = paths.artifacts / "quickstart_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    add_state_artifact(paths, "quickstart_report", out_path)
    append_hive_activity(
        paths,
        "hive-mind",
        "quickstart_ready",
        "Quickstart demo ready: inspect, memory draft, and MemoryOS read model are available",
        {"artifact": out_path.relative_to(root).as_posix()},
    )
    report["artifact"] = out_path.relative_to(root).as_posix()
    return report


def format_quickstart_demo(report: dict[str, Any]) -> str:
    """Render a concise public-alpha quickstart result."""
    inspect = report.get("inspect_summary") or {}
    memoryos = report.get("memoryos_summary") or {}
    lines = [
        f"Hive Mind quickstart demo: {report.get('run_id')}",
        "",
        str(report.get("value_claim") or ""),
        "",
        "What happened:",
    ]
    lines.extend(f"- {item}" for item in report.get("wow_path") or [])
    lines.extend(
        [
            "",
            f"Inspect: verdict={inspect.get('verdict')} ledger_records={inspect.get('ledger_records')} "
            f"providers={inspect.get('provider_result_count')} local_workers={inspect.get('local_worker_result_count')}",
            f"MemoryOS read model: nodes={memoryos.get('nodes')} edges={memoryos.get('edges')} "
            f"events={memoryos.get('events')} paths_hidden={memoryos.get('paths_hidden')}",
            "",
            f"Artifact: {report.get('artifact')}",
            "",
            "Try next:",
        ]
    )
    lines.extend(f"  {command}" for command in report.get("commands") or [])
    return "\n".join(lines)
