"""Small runtime utilities for Hive Mind orchestration."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from hashlib import sha1

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: object) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return f"{prefix}_{sha1(raw.encode('utf-8')).hexdigest()[:16]}"


def is_valid_run_id(run_id: object) -> bool:
    return isinstance(run_id, str) and bool(RUN_ID_PATTERN.fullmatch(run_id))


def ensure_valid_run_id(run_id: str) -> str:
    if not is_valid_run_id(run_id):
        raise ValueError(f"invalid run_id: {run_id!r}")
    return run_id
