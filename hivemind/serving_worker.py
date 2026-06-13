"""Serving worker queue/resume primitive for user-scoped AIOS execution.

Enqueue, start, pause, resume, retry, and close user-scoped serving jobs.
Every receipt carries user_id, session_id, job_id, and workspace_ref.
Completed sensitive stages are never re-executed on resume or retry.
Cross-user access is rejected at every entry point.

Contract: ASC-0263
Receipt schemas: aios.serving_worker_run.v1, aios.serving_worker_resume.v1
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .dag_state import atomic_write
from .utils import now_iso

RUN_SCHEMA = "aios.serving_worker_run.v1"
RESUME_SCHEMA = "aios.serving_worker_resume.v1"

ALLOWED_JOB_STATUSES = frozenset({
    "queued", "running", "paused", "completed", "failed", "refused",
})
ALLOWED_STAGE_STATUSES = frozenset({"pending", "running", "completed", "failed", "skipped"})

SECRET_LIKE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|AKIA[0-9A-Z]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+=-]{12,})",
    re.IGNORECASE,
)
SAFE_REF_PREFIXES = ("vault://", "env://", "secretref://", "credential://")


def _is_credential_value(value: str) -> bool:
    if value.startswith(SAFE_REF_PREFIXES):
        return False
    return bool(SECRET_LIKE.search(value))


def validate_credential_refs(refs: list[str]) -> list[str]:
    issues: list[str] = []
    for ref in refs:
        if not isinstance(ref, str) or not ref:
            issues.append("credential ref must be a non-empty string")
        elif _is_credential_value(ref):
            issues.append(f"credential ref looks like a raw secret, not a reference: {ref[:20]}...")
    return issues


@dataclass
class JobScope:
    user_id: str
    session_id: str
    job_id: str
    workspace_ref: str


@dataclass
class StageRecord:
    name: str
    sensitive: bool
    status: str = "pending"
    completed_at: str = ""
    evidence_ref: str = ""


@dataclass
class ServingJob:
    scope: JobScope
    stages: list[StageRecord]
    status: str = "queued"
    credential_refs: list[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class ServingWorkerReceipt:
    schema_version: str
    user_id: str
    session_id: str
    job_id: str
    workspace_ref: str
    operation: str
    status: str
    stages_completed: list[str]
    stages_skipped: list[str]
    stages_pending: list[str]
    credential_refs: list[str]
    created_at: str
    reason: str = ""


def _build_receipt(
    job: ServingJob,
    *,
    operation: str,
    schema: str = RUN_SCHEMA,
    reason: str = "",
) -> ServingWorkerReceipt:
    completed = [s.name for s in job.stages if s.status == "completed"]
    skipped = [s.name for s in job.stages if s.status == "skipped"]
    pending = [s.name for s in job.stages if s.status in ("pending", "running")]
    return ServingWorkerReceipt(
        schema_version=schema,
        user_id=job.scope.user_id,
        session_id=job.scope.session_id,
        job_id=job.scope.job_id,
        workspace_ref=job.scope.workspace_ref,
        operation=operation,
        status=job.status,
        stages_completed=completed,
        stages_skipped=skipped,
        stages_pending=pending,
        credential_refs=job.credential_refs,
        created_at=now_iso(),
        reason=reason,
    )


def _refuse_receipt(
    *,
    operation: str,
    reason: str,
    user_id: str = "",
    session_id: str = "",
    job_id: str = "",
    workspace_ref: str = "",
) -> ServingWorkerReceipt:
    return ServingWorkerReceipt(
        schema_version=RUN_SCHEMA,
        user_id=user_id,
        session_id=session_id,
        job_id=job_id,
        workspace_ref=workspace_ref,
        operation=operation,
        status="refused",
        stages_completed=[],
        stages_skipped=[],
        stages_pending=[],
        credential_refs=[],
        created_at=now_iso(),
        reason=reason,
    )


def write_receipt(receipt_dir: Path, receipt: ServingWorkerReceipt) -> Path:
    safe_id = receipt.job_id.replace("/", "_").replace(" ", "_") if receipt.job_id else "unknown"
    path = receipt_dir / f"{safe_id}_{receipt.operation}.json"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(asdict(receipt), ensure_ascii=False, indent=2, sort_keys=True))
    return path


class ServingWorkerQueue:
    """In-memory serving job queue with per-user isolation.

    All mutating operations validate user_id ownership before proceeding.
    Completed sensitive stages are never re-executed on resume or retry.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, ServingJob] = {}

    def _get_job_for_user(self, job_id: str, user_id: str) -> ServingJob | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if job.scope.user_id != user_id:
            return None
        return job

    def enqueue(
        self,
        scope: JobScope,
        stages: list[dict[str, Any]],
        credential_refs: list[str] | None = None,
    ) -> ServingWorkerReceipt:
        if not scope.user_id or not scope.session_id:
            return _refuse_receipt(
                operation="enqueue",
                reason="missing user_id or session_id",
                job_id=scope.job_id,
            )
        if not scope.job_id:
            return _refuse_receipt(
                operation="enqueue",
                reason="missing job_id",
                user_id=scope.user_id,
                session_id=scope.session_id,
            )

        cred_refs = credential_refs or []
        cred_issues = validate_credential_refs(cred_refs)
        if cred_issues:
            return _refuse_receipt(
                operation="enqueue",
                reason=f"credential_refs_rejected: {cred_issues[0]}",
                user_id=scope.user_id,
                session_id=scope.session_id,
                job_id=scope.job_id,
            )

        stage_records = [
            StageRecord(name=s["name"], sensitive=s.get("sensitive", False))
            for s in stages
        ]
        ts = now_iso()
        job = ServingJob(
            scope=scope,
            stages=stage_records,
            status="queued",
            credential_refs=cred_refs,
            created_at=ts,
            updated_at=ts,
        )
        self._jobs[scope.job_id] = job
        return _build_receipt(job, operation="enqueue")

    def start(self, job_id: str, user_id: str) -> ServingWorkerReceipt:
        job = self._get_job_for_user(job_id, user_id)
        if job is None:
            return _refuse_receipt(
                operation="start",
                reason="job_not_found_or_cross_user_denied",
                user_id=user_id,
                job_id=job_id,
            )
        if job.status != "queued":
            return _refuse_receipt(
                operation="start",
                reason=f"cannot start job in status={job.status}",
                user_id=user_id,
                job_id=job_id,
            )
        job.status = "running"
        job.updated_at = now_iso()
        for stage in job.stages:
            if stage.status == "pending":
                stage.status = "running"
                break
        return _build_receipt(job, operation="start")

    def record_stage_completion(
        self, job_id: str, user_id: str, stage_name: str, *, evidence_ref: str = "",
    ) -> ServingWorkerReceipt:
        job = self._get_job_for_user(job_id, user_id)
        if job is None:
            return _refuse_receipt(
                operation="record_stage",
                reason="job_not_found_or_cross_user_denied",
                user_id=user_id,
                job_id=job_id,
            )
        found = False
        for stage in job.stages:
            if stage.name == stage_name:
                stage.status = "completed"
                stage.completed_at = now_iso()
                stage.evidence_ref = evidence_ref
                found = True
                break
        if not found:
            return _refuse_receipt(
                operation="record_stage",
                reason=f"stage_not_found: {stage_name}",
                user_id=user_id,
                job_id=job_id,
            )
        # advance to next pending stage
        for stage in job.stages:
            if stage.status == "pending":
                stage.status = "running"
                break
        job.updated_at = now_iso()
        return _build_receipt(job, operation="record_stage")

    def pause(self, job_id: str, user_id: str) -> ServingWorkerReceipt:
        job = self._get_job_for_user(job_id, user_id)
        if job is None:
            return _refuse_receipt(
                operation="pause",
                reason="job_not_found_or_cross_user_denied",
                user_id=user_id,
                job_id=job_id,
            )
        if job.status != "running":
            return _refuse_receipt(
                operation="pause",
                reason=f"cannot pause job in status={job.status}",
                user_id=user_id,
                job_id=job_id,
            )
        job.status = "paused"
        job.updated_at = now_iso()
        for stage in job.stages:
            if stage.status == "running":
                stage.status = "pending"
        return _build_receipt(job, operation="pause")

    def resume(self, job_id: str, user_id: str) -> ServingWorkerReceipt:
        job = self._get_job_for_user(job_id, user_id)
        if job is None:
            return _refuse_receipt(
                operation="resume",
                reason="job_not_found_or_cross_user_denied",
                user_id=user_id,
                job_id=job_id,
            )
        if job.status != "paused":
            return _refuse_receipt(
                operation="resume",
                reason=f"cannot resume job in status={job.status}",
                user_id=user_id,
                job_id=job_id,
            )
        job.status = "running"
        job.updated_at = now_iso()
        for stage in job.stages:
            if stage.status == "completed" and stage.sensitive:
                continue
            if stage.status == "pending":
                stage.status = "running"
                break
        return _build_receipt(job, operation="resume", schema=RESUME_SCHEMA)

    def retry(self, job_id: str, user_id: str) -> ServingWorkerReceipt:
        job = self._get_job_for_user(job_id, user_id)
        if job is None:
            return _refuse_receipt(
                operation="retry",
                reason="job_not_found_or_cross_user_denied",
                user_id=user_id,
                job_id=job_id,
            )
        if job.status not in ("failed", "paused"):
            return _refuse_receipt(
                operation="retry",
                reason=f"cannot retry job in status={job.status}",
                user_id=user_id,
                job_id=job_id,
            )
        skipped: list[str] = []
        for stage in job.stages:
            if stage.status == "completed" and stage.sensitive:
                stage.status = "skipped"
                skipped.append(stage.name)
            elif stage.status in ("failed", "pending", "running"):
                stage.status = "pending"
        job.status = "running"
        job.updated_at = now_iso()
        for stage in job.stages:
            if stage.status == "pending":
                stage.status = "running"
                break
        return _build_receipt(
            job,
            operation="retry",
            schema=RESUME_SCHEMA,
            reason=f"sensitive_stages_preserved: {skipped}" if skipped else "",
        )

    def close(self, job_id: str, user_id: str) -> ServingWorkerReceipt:
        job = self._get_job_for_user(job_id, user_id)
        if job is None:
            return _refuse_receipt(
                operation="close",
                reason="job_not_found_or_cross_user_denied",
                user_id=user_id,
                job_id=job_id,
            )
        job.status = "completed"
        job.updated_at = now_iso()
        return _build_receipt(job, operation="close")

    def get_job(self, job_id: str, user_id: str) -> ServingJob | None:
        return self._get_job_for_user(job_id, user_id)

    def list_jobs(self, user_id: str) -> list[ServingJob]:
        return [j for j in self._jobs.values() if j.scope.user_id == user_id]
