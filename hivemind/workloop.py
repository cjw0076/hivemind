"""Append-only workloop ledger for visible multi-agent execution.

The ledger is the bridge between the user's shared-folder collaboration style
and Hive Mind's TUI: every scheduler/step authority event becomes a durable,
tail-able JSONL record under the run directory.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .utils import now_iso


LEDGER_FILE = "execution_ledger.jsonl"
SCHEMA_VERSION = 1


def execution_ledger_path(root: Path, run_id: str) -> Path:
    return root / ".runs" / run_id / LEDGER_FILE


def _json_hash(record: dict[str, Any]) -> str:
    payload = {k: v for k, v in record.items() if k != "hash"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _read_last_record(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            return record
    return None


def append_execution_ledger(
    root: Path,
    run_id: str,
    event: str,
    *,
    actor: str = "harness",
    step_id: str | None = None,
    status: str | None = None,
    permission_mode: str | None = None,
    bypass_mode: str | None = None,
    files_touched: list[str] | None = None,
    command: str | None = None,
    artifact: str | None = None,
    message: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one hash-chained execution ledger record."""
    path = execution_ledger_path(root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    last = _read_last_record(path)
    seq = int(last.get("seq", 0)) + 1 if last else 1
    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seq": seq,
        "ts": now_iso(),
        "run_id": run_id,
        "event": event,
        "actor": actor,
        "step_id": step_id,
        "status": status,
        "permission_mode": permission_mode,
        "bypass_mode": bypass_mode,
        "files_touched": files_touched or [],
        "command": command,
        "artifact": artifact,
        "message": message,
        "extra": extra or {},
        "previous_hash": last.get("hash") if last else None,
        "hash": "",
    }
    record["hash"] = _json_hash(record)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record


def read_execution_ledger(root: Path, run_id: str | None = None, limit: int = 80) -> list[dict[str, Any]]:
    """Read recent ledger records for a run, newest last."""
    try:
        if run_id is None:
            from .harness import load_run

            paths, _ = load_run(root, None)
            run_id = paths.run_id
    except FileNotFoundError:
        return []
    if run_id is None:
        return []
    path = execution_ledger_path(root, run_id)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for line in lines[-max(1, limit) :]:
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def replay_execution_ledger(root: Path, run_id: str | None = None) -> dict[str, Any]:
    """Replay and validate a run's execution ledger from raw JSONL."""
    try:
        if run_id is None:
            from .harness import load_run

            paths, _ = load_run(root, None)
            run_id = paths.run_id
    except FileNotFoundError:
        return empty_replay_report(run_id, [{"type": "missing_run", "message": "No current run"}])
    if run_id is None:
        return empty_replay_report(None, [{"type": "missing_run_id", "message": "No run id supplied"}])

    path = execution_ledger_path(root, run_id)
    issues: list[dict[str, Any]] = []
    if not path.exists():
        return empty_replay_report(
            run_id,
            [{"type": "missing_ledger", "message": f"{LEDGER_FILE} is missing"}],
            ledger_path=path,
        )

    records: list[dict[str, Any]] = []
    previous_hash: str | None = None
    expected_seq = 1
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return empty_replay_report(run_id, [{"type": "read_error", "message": str(exc)}], ledger_path=path)

    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append({"type": "invalid_json", "line": line_no, "message": str(exc)})
            continue
        if not isinstance(record, dict):
            issues.append({"type": "invalid_record", "line": line_no, "message": "ledger record must be an object"})
            continue
        seq = record.get("seq")
        if seq != expected_seq:
            issues.append({"type": "seq_drift", "line": line_no, "seq": seq, "expected_seq": expected_seq})
        expected_seq = int(seq) + 1 if isinstance(seq, int) else expected_seq + 1
        if record.get("schema_version") != SCHEMA_VERSION:
            issues.append({"type": "schema_drift", "line": line_no, "schema_version": record.get("schema_version")})
        if record.get("previous_hash") != previous_hash:
            issues.append(
                {
                    "type": "previous_hash_drift",
                    "line": line_no,
                    "seq": seq,
                    "previous_hash": record.get("previous_hash"),
                    "expected_previous_hash": previous_hash,
                }
            )
        computed_hash = _json_hash(record)
        if record.get("hash") != computed_hash:
            issues.append(
                {
                    "type": "hash_mismatch",
                    "line": line_no,
                    "seq": seq,
                    "hash": record.get("hash"),
                    "expected_hash": computed_hash,
                }
            )
        previous_hash = record.get("hash")
        records.append(record)

    authority = replay_authority(root, run_id, records, issues)
    steps = replay_steps(records)
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": not issues,
        "run_id": run_id,
        "ledger_path": path.as_posix(),
        "record_count": len(records),
        "invalid_line_count": sum(1 for issue in issues if issue.get("type") == "invalid_json"),
        "hash_chain_ok": not any(issue.get("type") in {"hash_mismatch", "previous_hash_drift"} for issue in issues),
        "seq_ok": not any(issue.get("type") == "seq_drift" for issue in issues),
        "issues": issues,
        "steps": steps,
        "authority": authority,
    }


def empty_replay_report(
    run_id: str | None,
    issues: list[dict[str, Any]],
    *,
    ledger_path: Path | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "run_id": run_id,
        "ledger_path": ledger_path.as_posix() if ledger_path else None,
        "record_count": 0,
        "invalid_line_count": 0,
        "hash_chain_ok": False,
        "seq_ok": False,
        "issues": issues,
        "steps": {},
        "authority": {"intents": {}, "votes": {}, "decisions": {}, "proofs": {}, "by_step": {}},
    }


def replay_steps(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    steps: dict[str, dict[str, Any]] = {}
    for record in records:
        step_id = record.get("step_id")
        if not step_id:
            continue
        step = steps.setdefault(
            str(step_id),
            {
                "step_id": str(step_id),
                "status": "observed",
                "last_event": None,
                "last_seq": None,
                "started": False,
                "completed": False,
                "blocked": False,
                "failed": False,
                "artifacts": [],
                "files_touched": [],
            },
        )
        event = str(record.get("event") or "")
        status = record.get("status")
        step["last_event"] = event
        step["last_seq"] = record.get("seq")
        if status:
            step["status"] = status
        if event == "step_started":
            step["started"] = True
        if event in {"step_completed", "barrier_closed"}:
            step["completed"] = True
            step["status"] = "completed"
        if event == "step_failed":
            step["failed"] = True
        if event in {"step_blocked", "policy_blocked", "operator_blocked"}:
            step["blocked"] = True
        artifact = record.get("artifact")
        if artifact and artifact not in step["artifacts"]:
            step["artifacts"].append(artifact)
        for touched in record.get("files_touched") or []:
            if touched not in step["files_touched"]:
                step["files_touched"].append(touched)
        extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
        if "probe_action" in extra:
            step["probe"] = {
                "step_id": str(step_id),
                "action": extra.get("probe_action"),
                "confidence": extra.get("probe_confidence"),
                "criteria_count": extra.get("criteria_count"),
                "status": status or step.get("status"),
                "event": event,
                "seq": record.get("seq"),
            }
    return steps


def replay_authority(
    root: Path,
    run_id: str,
    records: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    authority: dict[str, Any] = {"intents": {}, "votes": {}, "decisions": {}, "proofs": {}, "by_step": {}}
    for record in records:
        extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
        intent_id = extra.get("intent_id")
        event = str(record.get("event") or "")
        step_id = record.get("step_id")
        artifact = record.get("artifact")
        artifact_data = validate_record_artifact(root, record, issues)
        if not intent_id and isinstance(artifact_data, dict):
            intent_id = artifact_data.get("intent_id")
        if not intent_id:
            continue
        intent_id = str(intent_id)
        if event == "intent_proposed":
            authority["intents"][intent_id] = {
                "intent_id": intent_id,
                "step_id": step_id,
                "status": record.get("status"),
                "authority_class": extra.get("authority_class"),
                "risk_level": extra.get("risk_level"),
                "artifact": artifact,
            }
            if step_id:
                authority["by_step"].setdefault(str(step_id), {})["latest_intent"] = intent_id
        elif event == "vote_cast":
            authority["votes"].setdefault(intent_id, {})[str(record.get("actor") or "voter")] = record.get("status")
        elif event in {"policy_allowed", "policy_needs_vote", "policy_blocked"}:
            authority["votes"].setdefault(intent_id, {})["policy-gate"] = record.get("status")
        elif event == "quorum_decided":
            authority["decisions"][intent_id] = {
                "intent_id": intent_id,
                "decision": record.get("status"),
                "missing_voters": extra.get("missing_voters") or [],
                "conditions": extra.get("conditions") or [],
                "artifact": artifact,
            }
            if step_id:
                authority["by_step"].setdefault(str(step_id), {})["latest_decision"] = intent_id
        elif event == "protocol_decision_used":
            if step_id:
                authority["by_step"].setdefault(str(step_id), {})["used_decision"] = intent_id
        elif event == "execution_proof_created":
            authority["proofs"][intent_id] = {
                "intent_id": intent_id,
                "status": record.get("status"),
                "returncode": extra.get("returncode"),
                "verifier_status": extra.get("verifier_status"),
                "artifact": artifact,
            }
            if step_id:
                authority["by_step"].setdefault(str(step_id), {})["latest_proof"] = intent_id
    return authority


def validate_record_artifact(root: Path, record: dict[str, Any], issues: list[dict[str, Any]]) -> Any:
    artifact = record.get("artifact")
    if not artifact:
        return None
    path = Path(str(artifact))
    if not path.is_absolute():
        path = root / path
    if not path.exists():
        issues.append(
            {
                "type": "missing_artifact",
                "seq": record.get("seq"),
                "event": record.get("event"),
                "artifact": artifact,
            }
        )
        return None
    if path.suffix != ".json":
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        issues.append(
            {
                "type": "artifact_json_invalid",
                "seq": record.get("seq"),
                "event": record.get("event"),
                "artifact": artifact,
                "message": str(exc),
            }
        )
        return None
    if isinstance(data, dict):
        extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
        expected_intent = extra.get("intent_id")
        if expected_intent and data.get("intent_id") and data.get("intent_id") != expected_intent:
            issues.append(
                {
                    "type": "artifact_intent_drift",
                    "seq": record.get("seq"),
                    "artifact": artifact,
                    "intent_id": data.get("intent_id"),
                    "expected_intent_id": expected_intent,
                }
            )
    return data


def capture_worktree_snapshot(root: Path) -> dict[str, str]:
    """Return path -> git status for visible worktree changes.

    If the root is not a git repository, return an empty snapshot. Runtime
    artifacts are still recorded explicitly by the caller.
    """
    try:
        completed = subprocess.run(
            ["git", "-C", root.as_posix(), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            text=False,
            capture_output=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {}
    if completed.returncode != 0 or not completed.stdout:
        return {}
    items = [item.decode("utf-8", errors="replace") for item in completed.stdout.split(b"\0") if item]
    snapshot: dict[str, str] = {}
    index = 0
    while index < len(items):
        item = items[index]
        status = item[:2].strip() or "?"
        path = item[3:] if len(item) > 3 else item
        if path:
            snapshot[path] = status
        if status[:1] in {"R", "C"} and index + 1 < len(items):
            index += 1
            snapshot[items[index]] = status
        index += 1
    return snapshot


def relative_artifact(root: Path, artifact_path: Path | None) -> str | None:
    if artifact_path is None:
        return None
    try:
        return artifact_path.relative_to(root).as_posix()
    except ValueError:
        return artifact_path.as_posix()


def touched_files_between(
    before: dict[str, str],
    after: dict[str, str],
    *,
    root: Path,
    artifact_path: Path | None = None,
) -> list[str]:
    """Summarize files whose git-visible status changed plus the output artifact."""
    touched = {path for path, status in after.items() if before.get(path) != status}
    touched.update(path for path in before if path not in after)
    artifact = relative_artifact(root, artifact_path)
    if artifact:
        touched.add(artifact)
    return sorted(touched)


def format_ledger_entry(record: dict[str, Any]) -> str:
    seq = str(record.get("seq", "?")).rjust(3)
    ts = str(record.get("ts", ""))[11:19] or "--:--:--"
    actor = str(record.get("actor") or "-")
    event = str(record.get("event") or "-")
    step = str(record.get("step_id") or "-")
    status = str(record.get("status") or "-")
    files = record.get("files_touched") or []
    file_hint = ", ".join(str(path) for path in files[:3])
    if len(files) > 3:
        file_hint += f" +{len(files) - 3}"
    extra = record.get("extra") if isinstance(record.get("extra"), dict) else {}
    extra_hints: list[str] = []
    if "probe_action" in extra:
        action = extra.get("probe_action")
        confidence = format_probe_confidence(extra.get("probe_confidence"))
        criteria = extra.get("criteria_count")
        extra_hints.append(f"probe={action} conf={confidence} criteria={criteria}")
    if extra_hints:
        suffix = " | ".join(extra_hints)
        file_hint = f"{file_hint} | {suffix}" if file_hint else suffix
    return f"{seq} {ts} {actor:<24} {event:<26} {step:<18} {status:<12} {file_hint}"


def format_probe_confidence(value: Any) -> str:
    if value is None:
        return "-"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return str(value)


def format_execution_ledger(records: list[dict[str, Any]]) -> str:
    lines = ["Execution Ledger", "SEQ TIME     ACTOR                    EVENT                      STEP               STATUS       FILES"]
    lines.append("-" * 112)
    if not records:
        lines.append("No ledger records yet.")
        return "\n".join(lines)
    lines.extend(format_ledger_entry(record) for record in records)
    return "\n".join(lines)


def format_ledger_replay(report: dict[str, Any]) -> str:
    lines = [
        "Ledger Replay",
        f"Run: {report.get('run_id')}  OK: {report.get('ok')}  Records: {report.get('record_count')}",
        f"Hash chain: {'ok' if report.get('hash_chain_ok') else 'drift'}  Seq: {'ok' if report.get('seq_ok') else 'drift'}",
        "",
        "Authority:",
    ]
    authority = report.get("authority") or {}
    decisions = authority.get("decisions") or {}
    proofs = authority.get("proofs") or {}
    intents = authority.get("intents") or {}
    if not intents:
        lines.append("- no protocol intents")
    else:
        for intent_id, intent in sorted(intents.items()):
            decision = decisions.get(intent_id, {}).get("decision") or "-"
            proof = proofs.get(intent_id, {}).get("status") or "-"
            lines.append(
                f"- {intent.get('step_id')}: {intent_id} "
                f"class={intent.get('authority_class') or '-'} risk={intent.get('risk_level') or '-'} "
                f"decision={decision} proof={proof}"
            )
    lines.extend(["", "Steps:"])
    steps = report.get("steps") or {}
    if not steps:
        lines.append("- no step records")
    else:
        for step_id, step in sorted(steps.items()):
            flags = [key for key in ("started", "completed", "blocked", "failed") if step.get(key)]
            suffix = f" ({', '.join(flags)})" if flags else ""
            lines.append(f"- {step_id}: {step.get('status')} last={step.get('last_event')}{suffix}")
    lines.extend(["", "Issues:"])
    issues = report.get("issues") or []
    if not issues:
        lines.append("- none")
    else:
        for issue in issues[:20]:
            seq = f" seq={issue.get('seq')}" if issue.get("seq") is not None else ""
            line = f" line={issue.get('line')}" if issue.get("line") is not None else ""
            detail = issue.get("message") or issue.get("artifact") or ""
            lines.append(f"- {issue.get('type')}{seq}{line}: {detail}")
        if len(issues) > 20:
            lines.append(f"- ... {len(issues) - 20} more")
    return "\n".join(lines)
