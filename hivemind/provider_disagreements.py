from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import harness as h
from .run_receipts import load_receipt_yaml, provider_result_paths
from .utils import now_iso


SCHEMA_VERSION = "hive.provider_output_disagreements.v1"
REPORT_NAME = "provider_output_disagreements.json"
EXECUTED_OUTPUT_STATUSES = {"completed", "partial"}


def build_provider_output_disagreements(root: Path, run_id: str | None = None, *, show_paths: bool = False) -> dict[str, Any]:
    paths, state = h.load_run(root, run_id)
    participants = [
        participant
        for participant in (
            project_executed_provider_output(root, result_path, show_paths=show_paths)
            for result_path in provider_result_paths(paths.run_dir)
        )
        if participant is not None
    ]
    records = extract_disagreements_from_participants(paths.run_id, str(state.get("user_request") or ""), participants)
    dis_path = paths.run_dir / "disagreements.json"
    merged = merge_disagreements(load_existing_disagreements(dis_path), records)
    h.write_json(dis_path, merged)
    report_path = paths.artifacts / REPORT_NAME
    report_ref = report_path.relative_to(root).as_posix()
    report = {
        "schema_version": SCHEMA_VERSION,
        "kind": "hive_provider_output_disagreements",
        "generated_at": now_iso(),
        "run_id": paths.run_id,
        "task": state.get("user_request"),
        "provider_output_count": len(participants),
        "disagreement_count": len(records),
        "disagreements": records,
        "artifact": report_ref,
        "disagreements_artifact": dis_path.relative_to(root).as_posix(),
        "paths_hidden": not show_paths,
        "privacy": {
            "raw_provider_output_read": True,
            "raw_provider_output_included": False,
            "output_preview_included": False,
            "path_refs_hidden": not show_paths,
        },
    }
    h.write_json(report_path, report)
    artifacts = dict(state.get("artifacts") or {})
    artifacts["provider_output_disagreements"] = report_ref
    artifacts["disagreements"] = dis_path.relative_to(root).as_posix()
    h.update_state(paths, artifacts=artifacts, latest_event="provider_disagreements_extracted")
    h.append_event(
        paths,
        "provider_disagreements_extracted",
        {
            "artifact": dis_path.relative_to(root).as_posix(),
            "report": report_ref if show_paths else f"artifacts/{REPORT_NAME}",
            "count": len(records),
        },
    )
    return report


def project_executed_provider_output(root: Path, result_path: Path, *, show_paths: bool) -> dict[str, Any] | None:
    data = load_receipt_yaml(result_path)
    if data.get("status") not in EXECUTED_OUTPUT_STATUSES:
        return None
    output_ref = str(data.get("output_path") or data.get("stdout_path") or "").strip()
    if not output_ref:
        return None
    output_path = root / output_ref
    if not output_path.exists() or not output_path.is_file():
        return None
    try:
        output_text = output_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not output_text.strip():
        return None
    return {
        "provider": str(data.get("provider") or data.get("agent") or "unknown"),
        "role": str(data.get("role") or "unknown"),
        "status": str(data.get("status") or "unknown"),
        "provider_mode": str(data.get("provider_mode") or "unknown"),
        "receipt_ref": ref(root, result_path, show_paths=show_paths),
        "output_text": output_text,
    }


def extract_disagreements_from_participants(run_id: str, topic: str, participants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for left_index, left in enumerate(participants):
        for right in participants[left_index + 1:]:
            axes = h.disagreement_axes_for_outputs(str(left.get("output_text") or ""), str(right.get("output_text") or ""))
            if not axes:
                continue
            severity = h.provider_disagreement_severity(axes)
            records.append(
                {
                    "ts": now_iso(),
                    "run_id": run_id,
                    "source": "executed_provider_output",
                    "topic": topic,
                    "step_id": "provider_outputs",
                    "participants": [participant_label(left), participant_label(right)],
                    "topology_type": "split" if len(axes) == 1 else "distributed",
                    "severity": severity,
                    "axes": axes,
                    "dominant_axis": axes[0],
                    "disagreement_count": 1,
                    "disagreement_targets": [participant_label(right)],
                    "topology_recommended_action": "referee" if severity in {"high", "medium"} else "add_review",
                    "evidence_refs": [str(left.get("receipt_ref")), str(right.get("receipt_ref"))],
                }
            )
    return records


def participant_label(row: dict[str, Any]) -> str:
    return f"{row.get('provider')}/{row.get('role')}"


def load_existing_disagreements(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [item for item in loaded if isinstance(item, dict)]


def merge_disagreements(existing: list[dict[str, Any]], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = list(existing)
    seen = {dedupe_key(item) for item in merged}
    for record in records:
        key = dedupe_key(record)
        if key in seen:
            continue
        merged.append(record)
        seen.add(key)
    return merged


def dedupe_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(record.get("source")),
        str(record.get("step_id")),
        ",".join(str(participant) for participant in record.get("participants", [])),
        ",".join(str(axis) for axis in record.get("axes", [])),
    )


def ref(root: Path, path: Path, *, show_paths: bool) -> str:
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        rel = path.as_posix()
    if show_paths:
        return rel
    try:
        return path.relative_to(root / h.RUNS_DIR).as_posix()
    except ValueError:
        return path.name


def format_provider_output_disagreements(report: dict[str, Any]) -> str:
    lines = [
        "Hive Provider Output Disagreements",
        f"Run: {report.get('run_id')}",
        f"Provider outputs: {report.get('provider_output_count')}",
        f"Disagreements: {report.get('disagreement_count')}",
        f"Artifact: {report.get('artifact')}",
        "",
        "Privacy:",
        f"- raw_provider_output_included: {report.get('privacy', {}).get('raw_provider_output_included')}",
        "",
        "Records:",
    ]
    for record in report.get("disagreements") or []:
        lines.append(
            f"- {record.get('severity')} {','.join(record.get('axes') or [])} "
            f"{' vs '.join(record.get('participants') or [])}"
        )
    if not report.get("disagreements"):
        lines.append("- none")
    return "\n".join(lines)
