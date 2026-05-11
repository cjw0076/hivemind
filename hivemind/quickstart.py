"""Public-alpha quickstart demo for Hive Mind."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .harness import add_state_artifact, append_hive_activity, demo_live_run, load_run
from .harness import orchestrate_prompt
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


def memory_loop_demo(
    root: Path,
    task: str = "Remember this Hive Mind run and use it in the next run",
    *,
    delay: float = 0.0,
    memoryos_root: Path | None = None,
) -> dict[str, Any]:
    """Run an isolated Hive -> MemoryOS -> Hive feedback loop demo."""
    first = quickstart_demo(root, task=task, delay=delay)
    first_run_id = str(first["run_id"])
    first_paths, _state = load_run(root, first_run_id)
    memory_root = (memoryos_root or root / ".hivemind" / "demo_memoryos" / first_run_id).resolve()
    memory_root.mkdir(parents=True, exist_ok=True)

    import_result = _memoryos_json(root, memory_root, "import-run", first_paths.run_dir.as_posix(), "--json")
    imported_memory_ids = list(((import_result.get("imported_ids") or {}).get("memory_objects") or []))
    approved_memory_ids: list[str] = []
    approve_outputs: list[dict[str, Any]] = []
    for memory_id in imported_memory_ids:
        approve = _memoryos_text(
            root,
            memory_root,
            "drafts",
            "approve",
            str(memory_id),
            "--reviewer",
            "hive-demo",
            "--note",
            "public-alpha feedback loop demo",
        )
        approve_outputs.append(approve)
        if approve.get("returncode") == 0:
            approved_memory_ids.append(str(memory_id))

    context_pack = _memoryos_json(
        root,
        memory_root,
        "context",
        "build",
        "--for",
        "hive",
        "--task",
        "Use the accepted quickstart memory in the next Hive run",
        "--project",
        "Hive Mind",
        "--json",
    )
    memoryos_source_root = _memoryos_source_root()
    with temporary_env(
        {
            "HIVE_MEMORYOS_ROOT": memory_root.as_posix(),
            "HIVE_MEMORYOS_SOURCE_ROOT": memoryos_source_root.as_posix(),
        }
    ):
        second = orchestrate_prompt(
            root,
            "Use accepted MemoryOS context from the previous quickstart run",
            complexity="fast",
            execute=False,
            execute_local=False,
        )
    second_run_id = str(second.get("run_id") or "")
    second_paths, second_state = load_run(root, second_run_id)
    second_context = second_state.get("memoryos_context") if isinstance(second_state.get("memoryos_context"), dict) else {}

    report = {
        "schema_version": 1,
        "kind": "hive_memory_loop_demo",
        "generated_at": now_iso(),
        "status": "closed_loop" if approved_memory_ids and second_context.get("accepted_memory_ids") else "needs_review",
        "memoryos_root": memory_root.relative_to(root).as_posix() if memory_root.is_relative_to(root) else memory_root.as_posix(),
        "memoryos_source_root": memoryos_source_root.as_posix(),
        "first_run_id": first_run_id,
        "second_run_id": second_run_id,
        "imported_memory_ids": imported_memory_ids,
        "approved_memory_ids": approved_memory_ids,
        "context_trace_id": context_pack.get("trace_id"),
        "context_items": context_pack.get("context_items", 0),
        "second_run_context": {
            "status": second_context.get("status"),
            "trace_id": second_context.get("trace_id"),
            "accepted_memory_ids": second_context.get("accepted_memory_ids") or [],
            "context_items": second_context.get("context_items", 0),
        },
        "import_result": import_result,
        "approve_outputs": approve_outputs,
        "commands": [
            f"memoryos --root {memory_root} import-run {first_paths.run_dir}",
            f"memoryos --root {memory_root} drafts approve {approved_memory_ids[0] if approved_memory_ids else '<memory-id>'}",
            f"memoryos --root {memory_root} context build --for hive --project 'Hive Mind' --json",
            f"hive inspect {second_run_id}",
        ],
    }
    out_path = first_paths.artifacts / "memory_loop_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    add_state_artifact(first_paths, "memory_loop_report", out_path)
    append_hive_activity(
        first_paths,
        "memoryos",
        "feedback_loop_closed" if report["status"] == "closed_loop" else "feedback_loop_needs_review",
        f"MemoryOS feedback loop demo status={report['status']}",
        {"artifact": out_path.relative_to(root).as_posix(), "second_run_id": second_run_id},
    )
    report["artifact"] = out_path.relative_to(root).as_posix()
    return report


def format_memory_loop_demo(report: dict[str, Any]) -> str:
    second = report.get("second_run_context") or {}
    lines = [
        f"Hive ↔ MemoryOS feedback loop demo: {report.get('status')}",
        "",
        f"First run:  {report.get('first_run_id')}",
        f"Second run: {report.get('second_run_id')}",
        f"MemoryOS root: {report.get('memoryos_root')}",
        "",
        f"Imported memories: {', '.join(report.get('imported_memory_ids') or []) or 'none'}",
        f"Approved memories: {', '.join(report.get('approved_memory_ids') or []) or 'none'}",
        f"Context trace: {report.get('context_trace_id')} items={report.get('context_items')}",
        f"Second run context: status={second.get('status')} trace={second.get('trace_id')} "
        f"accepted={', '.join(second.get('accepted_memory_ids') or []) or 'none'}",
        "",
        f"Artifact: {report.get('artifact')}",
        "",
        "Try next:",
    ]
    lines.extend(f"  {command}" for command in report.get("commands") or [])
    return "\n".join(lines)


def _memoryos_json(root: Path, memoryos_root: Path, *args: str) -> dict[str, Any]:
    result = _run_memoryos(root, memoryos_root, *args)
    if result["returncode"] != 0:
        raise RuntimeError(result["stderr"] or result["stdout"] or f"memoryos {' '.join(args)} failed")
    try:
        return json.loads(str(result["stdout"] or "{}"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"memoryos {' '.join(args)} did not emit JSON: {exc}") from exc


def _memoryos_text(root: Path, memoryos_root: Path, *args: str) -> dict[str, Any]:
    return _run_memoryos(root, memoryos_root, *args)


def _run_memoryos(root: Path, memoryos_root: Path, *args: str) -> dict[str, Any]:
    started = time.perf_counter()
    command = [sys.executable, "-m", "memoryos.cli", "--root", memoryos_root.as_posix(), *args]
    result = subprocess.run(command, cwd=_memoryos_source_root(root), text=True, capture_output=True, timeout=60)
    return {
        "command": command,
        "returncode": result.returncode,
        "duration_ms": round((time.perf_counter() - started) * 1000),
        "stdout": result.stdout[-4000:],
        "stderr": result.stderr[-4000:],
    }


def _memoryos_source_root(_root: Path | None = None) -> Path:
    if os.environ.get("HIVE_MEMORYOS_SOURCE_ROOT"):
        return Path(str(os.environ["HIVE_MEMORYOS_SOURCE_ROOT"])).resolve()
    return (Path(__file__).resolve().parents[2] / "memoryOS").resolve()


@contextmanager
def temporary_env(values: dict[str, str]):
    previous = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
