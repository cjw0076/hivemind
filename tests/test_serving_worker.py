"""Tests for the serving worker queue/resume primitive (ASC-0263).

Proves:
- Two interrupted jobs resume from recorded receipts without duplicate sensitive actions.
- user_id=A cannot resume/read user_id=B worker state.
- Provider credential values are rejected or redacted from receipts.
- No live provider or network call is required.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from hivemind.serving_worker import (
    JobScope,
    ServingWorkerQueue,
    ServingWorkerReceipt,
    validate_credential_refs,
    write_receipt,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scope(user_id: str = "user-A", job_id: str = "job-1") -> JobScope:
    return JobScope(
        user_id=user_id,
        session_id="sess-1",
        job_id=job_id,
        workspace_ref="/workspace/user-A",
    )


def _default_stages() -> list[dict]:
    return [
        {"name": "fetch_data", "sensitive": False},
        {"name": "send_email", "sensitive": True},
        {"name": "log_result", "sensitive": False},
    ]


def _enqueue_and_start(q: ServingWorkerQueue, scope: JobScope | None = None) -> None:
    scope = scope or _make_scope()
    q.enqueue(scope, _default_stages(), credential_refs=["vault://email-creds"])
    q.start(scope.job_id, scope.user_id)


# ---------------------------------------------------------------------------
# Enqueue / Start / Close lifecycle
# ---------------------------------------------------------------------------

class TestLifecycle:
    def test_enqueue_creates_queued_job(self):
        q = ServingWorkerQueue()
        r = q.enqueue(_make_scope(), _default_stages())
        assert r.status == "queued"
        assert r.operation == "enqueue"
        assert r.user_id == "user-A"
        assert r.job_id == "job-1"
        assert r.workspace_ref == "/workspace/user-A"

    def test_start_transitions_to_running(self):
        q = ServingWorkerQueue()
        q.enqueue(_make_scope(), _default_stages())
        r = q.start("job-1", "user-A")
        assert r.status == "running"
        assert "fetch_data" not in r.stages_completed

    def test_close_marks_completed(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        r = q.close("job-1", "user-A")
        assert r.status == "completed"
        assert r.operation == "close"

    def test_stage_completion_advances_pipeline(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        r = q.record_stage_completion("job-1", "user-A", "fetch_data")
        assert "fetch_data" in r.stages_completed
        job = q.get_job("job-1", "user-A")
        assert job is not None
        running = [s for s in job.stages if s.status == "running"]
        assert len(running) == 1
        assert running[0].name == "send_email"


# ---------------------------------------------------------------------------
# Resume without duplicate sensitive action (core contract requirement)
# ---------------------------------------------------------------------------

class TestResumeNoDuplicateSensitive:
    def test_pause_and_resume_skips_completed_sensitive(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        q.record_stage_completion("job-1", "user-A", "fetch_data")
        q.record_stage_completion("job-1", "user-A", "send_email", evidence_ref="email-sent-abc")
        q.pause("job-1", "user-A")

        r = q.resume("job-1", "user-A")
        assert r.status == "running"
        assert r.schema_version == "aios.serving_worker_resume.v1"
        assert "send_email" in r.stages_completed
        assert "send_email" not in r.stages_pending

    def test_retry_preserves_completed_sensitive_as_skipped(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        q.record_stage_completion("job-1", "user-A", "fetch_data")
        q.record_stage_completion("job-1", "user-A", "send_email", evidence_ref="email-sent-abc")

        job = q.get_job("job-1", "user-A")
        assert job is not None
        job.status = "failed"

        r = q.retry("job-1", "user-A")
        assert r.status == "running"
        assert "send_email" in r.stages_skipped
        assert "send_email" not in r.stages_pending
        assert "sensitive_stages_preserved" in r.reason

    def test_two_interrupted_jobs_resume_independently(self):
        """Two jobs pause mid-pipeline. Each resumes from its own checkpoint."""
        q = ServingWorkerQueue()

        scope_a = _make_scope(user_id="user-A", job_id="job-A")
        scope_b = _make_scope(user_id="user-B", job_id="job-B")
        scope_b.workspace_ref = "/workspace/user-B"

        q.enqueue(scope_a, _default_stages(), credential_refs=["vault://a-creds"])
        q.enqueue(scope_b, _default_stages(), credential_refs=["vault://b-creds"])
        q.start("job-A", "user-A")
        q.start("job-B", "user-B")

        q.record_stage_completion("job-A", "user-A", "fetch_data")
        q.record_stage_completion("job-A", "user-A", "send_email", evidence_ref="email-A")
        q.record_stage_completion("job-B", "user-B", "fetch_data")

        q.pause("job-A", "user-A")
        q.pause("job-B", "user-B")

        r_a = q.resume("job-A", "user-A")
        r_b = q.resume("job-B", "user-B")

        assert "send_email" in r_a.stages_completed
        assert "send_email" not in r_a.stages_pending

        assert "send_email" not in r_b.stages_completed
        assert "send_email" in r_b.stages_pending or "send_email" in [
            s.name for s in q.get_job("job-B", "user-B").stages if s.status == "running"
        ]


# ---------------------------------------------------------------------------
# Cross-user denial (core contract requirement)
# ---------------------------------------------------------------------------

class TestCrossUserDenial:
    def test_user_b_cannot_start_user_a_job(self):
        q = ServingWorkerQueue()
        q.enqueue(_make_scope(user_id="user-A", job_id="job-1"), _default_stages())
        r = q.start("job-1", "user-B")
        assert r.status == "refused"
        assert "cross_user" in r.reason

    def test_user_b_cannot_resume_user_a_job(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        q.pause("job-1", "user-A")
        r = q.resume("job-1", "user-B")
        assert r.status == "refused"
        assert "cross_user" in r.reason

    def test_user_b_cannot_read_user_a_job(self):
        q = ServingWorkerQueue()
        q.enqueue(_make_scope(user_id="user-A"), _default_stages())
        assert q.get_job("job-1", "user-B") is None

    def test_user_b_cannot_close_user_a_job(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        r = q.close("job-1", "user-B")
        assert r.status == "refused"

    def test_user_b_cannot_record_stage_on_user_a_job(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        r = q.record_stage_completion("job-1", "user-B", "fetch_data")
        assert r.status == "refused"

    def test_list_jobs_only_returns_own(self):
        q = ServingWorkerQueue()
        q.enqueue(_make_scope(user_id="user-A", job_id="job-A"), _default_stages())
        q.enqueue(
            JobScope(user_id="user-B", session_id="s2", job_id="job-B", workspace_ref="/w/B"),
            _default_stages(),
        )
        assert len(q.list_jobs("user-A")) == 1
        assert q.list_jobs("user-A")[0].scope.job_id == "job-A"


# ---------------------------------------------------------------------------
# Credential redaction (core contract requirement)
# ---------------------------------------------------------------------------

class TestCredentialRedaction:
    def test_raw_api_key_rejected_at_enqueue(self):
        q = ServingWorkerQueue()
        r = q.enqueue(
            _make_scope(),
            _default_stages(),
            credential_refs=["sk-1234567890abcdef1234"],
        )
        assert r.status == "refused"
        assert "credential_refs_rejected" in r.reason

    def test_raw_password_rejected(self):
        q = ServingWorkerQueue()
        r = q.enqueue(
            _make_scope(),
            _default_stages(),
            credential_refs=["api_key=supersecretvalue12345"],
        )
        assert r.status == "refused"

    def test_vault_ref_accepted(self):
        q = ServingWorkerQueue()
        r = q.enqueue(
            _make_scope(),
            _default_stages(),
            credential_refs=["vault://my-secret", "env://API_KEY"],
        )
        assert r.status == "queued"

    def test_validate_credential_refs_detects_secrets(self):
        assert len(validate_credential_refs(["sk-abcdefghijklmnop"])) > 0
        assert len(validate_credential_refs(["vault://ok"])) == 0
        assert len(validate_credential_refs([""])) > 0

    def test_private_key_rejected(self):
        q = ServingWorkerQueue()
        r = q.enqueue(
            _make_scope(),
            _default_stages(),
            credential_refs=["-----BEGIN RSA PRIVATE KEY-----\nMIIE..."],
        )
        assert r.status == "refused"


# ---------------------------------------------------------------------------
# Missing scope produces refusal receipt
# ---------------------------------------------------------------------------

class TestMissingScopeRefusal:
    def test_missing_user_id_refused(self):
        q = ServingWorkerQueue()
        r = q.enqueue(
            JobScope(user_id="", session_id="s1", job_id="j1", workspace_ref="/w"),
            _default_stages(),
        )
        assert r.status == "refused"
        assert "missing" in r.reason

    def test_missing_session_id_refused(self):
        q = ServingWorkerQueue()
        r = q.enqueue(
            JobScope(user_id="u1", session_id="", job_id="j1", workspace_ref="/w"),
            _default_stages(),
        )
        assert r.status == "refused"

    def test_missing_job_id_refused(self):
        q = ServingWorkerQueue()
        r = q.enqueue(
            JobScope(user_id="u1", session_id="s1", job_id="", workspace_ref="/w"),
            _default_stages(),
        )
        assert r.status == "refused"

    def test_nonexistent_job_refused(self):
        q = ServingWorkerQueue()
        r = q.start("nonexistent", "user-A")
        assert r.status == "refused"


# ---------------------------------------------------------------------------
# State transition guards
# ---------------------------------------------------------------------------

class TestTransitionGuards:
    def test_cannot_start_already_running(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        r = q.start("job-1", "user-A")
        assert r.status == "refused"

    def test_cannot_pause_queued(self):
        q = ServingWorkerQueue()
        q.enqueue(_make_scope(), _default_stages())
        r = q.pause("job-1", "user-A")
        assert r.status == "refused"

    def test_cannot_resume_running(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        r = q.resume("job-1", "user-A")
        assert r.status == "refused"

    def test_cannot_retry_running(self):
        q = ServingWorkerQueue()
        _enqueue_and_start(q)
        r = q.retry("job-1", "user-A")
        assert r.status == "refused"


# ---------------------------------------------------------------------------
# Receipt persistence
# ---------------------------------------------------------------------------

class TestReceiptPersistence:
    def test_write_receipt_creates_file(self):
        q = ServingWorkerQueue()
        r = q.enqueue(_make_scope(), _default_stages())
        with tempfile.TemporaryDirectory() as td:
            path = write_receipt(Path(td), r)
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["schema_version"] == "aios.serving_worker_run.v1"
            assert data["user_id"] == "user-A"
            assert data["job_id"] == "job-1"

    def test_receipt_carries_all_scope_fields(self):
        q = ServingWorkerQueue()
        r = q.enqueue(_make_scope(), _default_stages())
        assert r.user_id == "user-A"
        assert r.session_id == "sess-1"
        assert r.job_id == "job-1"
        assert r.workspace_ref == "/workspace/user-A"
