"""Filesystem transaction protocol for DAG state.

Provides the minimal substrate required before parallel fan-out:
  - atomic_write: tmp → fsync → rename (POSIX atomic on same filesystem)
  - guard_transition: step status machine — illegal transitions raise ValueError
  - StepLease: per-step execution lock with TTL and crash recovery
  - recover_expired_leases: reset 'running' steps whose leases have expired

No external dependencies beyond the stdlib. No imports from plan_dag
to avoid circular dependencies — callers wire these together.
"""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, TYPE_CHECKING

from .utils import now_iso

if TYPE_CHECKING:
    from .plan_dag import PlanDAG

# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------

def atomic_write(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write content to path via tmp → fsync → rename.

    On POSIX, rename(2) is atomic when src and dst share a filesystem.
    This guarantees readers see either the old file or the new file — never
    a partial write.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding=encoding)
        with open(tmp, "rb") as fh:
            os.fsync(fh.fileno())
        tmp.rename(path)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Step status transition guard
# ---------------------------------------------------------------------------

# Terminal states have empty allowed-next sets.
_VALID_TRANSITIONS: dict[str, frozenset[str]] = {
    "pending":   frozenset({"running", "skipped"}),
    "running":   frozenset({"completed", "prepared", "failed", "skipped"}),
    "prepared":  frozenset({"running", "completed"}),  # retry or manual promote
    "failed":    frozenset({"running"}),               # retry only
    "completed": frozenset(),                          # terminal
    "skipped":   frozenset(),                          # terminal
    "blocked":   frozenset({"pending"}),               # externally unblocked
}


def guard_transition(
    step_id: str,
    current_status: str,
    new_status: str,
    force: bool = False,
) -> None:
    """Raise ValueError if the transition is not in the allowed set.

    force=True is reserved for --retry and operator recovery flows.
    It bypasses the guard entirely — use only when the caller has verified
    that forcing is safe (e.g., lease has expired and step is being recovered).
    """
    if force:
        return
    allowed = _VALID_TRANSITIONS.get(current_status, frozenset())
    if new_status not in allowed:
        terminal_note = " (terminal state)" if not allowed else ""
        raise ValueError(
            f"Illegal step transition: {step_id!r}  {current_status!r} → {new_status!r}"
            f"{terminal_note}. Allowed: {sorted(allowed) or 'none'}"
        )


# ---------------------------------------------------------------------------
# StepLease
# ---------------------------------------------------------------------------

LEASE_DEFAULT_TTL: int = 300  # seconds
STEP_LEASES_DIR: str = "step_leases"


@dataclass
class StepLease:
    """Exclusive execution lock for one step, stored as a JSON file.

    Layout: .runs/<run_id>/step_leases/<step_id>.json

    A lease is considered live while expires_at is in the future.
    An expired lease can be re-acquired by any caller (crash recovery path).
    The idempotency_key is a UUID that uniquely identifies this execution
    attempt — if the same key is observed twice, the second call is a no-op.
    """

    run_id: str
    step_id: str
    idempotency_key: str
    acquired_at: str
    expires_at: str
    owner: str          # "{pid}@{hostname}"
    _path: Path = field(default=None, repr=False, compare=False)  # type: ignore[assignment]

    # ------------------------------------------------------------------
    @classmethod
    def acquire(
        cls,
        root: Path,
        run_id: str,
        step_id: str,
        ttl: int = LEASE_DEFAULT_TTL,
    ) -> "StepLease":
        """Acquire a lease. Raises RuntimeError if a live lease already exists."""
        from .harness import load_run  # lazy — avoids circular at module level
        paths, _ = load_run(root, run_id)
        leases_dir = paths.run_dir / STEP_LEASES_DIR
        leases_dir.mkdir(exist_ok=True)
        lease_path = leases_dir / f"{step_id}.json"

        if lease_path.exists():
            existing = _read_lease_file(lease_path)
            if existing and not _is_expired(existing):
                raise RuntimeError(
                    f"Step '{step_id}' is leased by {existing.get('owner')} "
                    f"until {existing.get('expires_at')}. "
                    "Wait for expiry or run recover_expired_leases()."
                )

        import socket
        key = str(uuid.uuid4())
        now = now_iso()
        expires = _iso_from_now(ttl)
        owner = f"{os.getpid()}@{socket.gethostname()}"
        lease = cls(
            run_id=run_id,
            step_id=step_id,
            idempotency_key=key,
            acquired_at=now,
            expires_at=expires,
            owner=owner,
            _path=lease_path,
        )
        atomic_write(lease_path, json.dumps(lease._as_dict(), ensure_ascii=False, indent=2))
        return lease

    # ------------------------------------------------------------------
    def release(self) -> None:
        """Remove the lease file. Idempotent."""
        if self._path and self._path.exists():
            try:
                self._path.unlink()
            except FileNotFoundError:
                pass

    def heartbeat(self, ttl: int = LEASE_DEFAULT_TTL) -> None:
        """Extend expiry. Call periodically from long-running steps."""
        self.expires_at = _iso_from_now(ttl)
        data = self._as_dict()
        data["expires_at"] = self.expires_at
        atomic_write(self._path, json.dumps(data, ensure_ascii=False, indent=2))

    def _as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "step_id": self.step_id,
            "idempotency_key": self.idempotency_key,
            "acquired_at": self.acquired_at,
            "expires_at": self.expires_at,
            "owner": self.owner,
        }


# ---------------------------------------------------------------------------
# Lease helpers
# ---------------------------------------------------------------------------

def _read_lease_file(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_expired(data: dict[str, Any]) -> bool:
    try:
        expires = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        return datetime.now(timezone.utc) > expires
    except Exception:
        return True  # malformed → treat as expired


def _iso_from_now(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# ---------------------------------------------------------------------------
# Crash recovery
# ---------------------------------------------------------------------------

def recover_expired_leases(root: Path, run_id: str, dag: "PlanDAG") -> list[str]:
    """Reset 'running' steps whose leases have expired back to 'pending'.

    Call at scheduler startup or before fan-out to recover from crashed workers.
    Returns the list of recovered step_ids.
    """
    from .harness import load_run  # lazy
    try:
        paths, _ = load_run(root, run_id)
    except Exception:
        return []
    leases_dir = paths.run_dir / STEP_LEASES_DIR
    if not leases_dir.exists():
        return []
    recovered: list[str] = []
    for lease_file in leases_dir.glob("*.json"):
        data = _read_lease_file(lease_file)
        if data and _is_expired(data):
            step_id = data.get("step_id", lease_file.stem)
            step = dag.by_id(step_id)
            if step and step.status == "running":
                step.status = "pending"
                step.started_at = None
                recovered.append(step_id)
            lease_file.unlink(missing_ok=True)
    return recovered
