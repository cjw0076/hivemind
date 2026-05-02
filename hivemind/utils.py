"""Small runtime utilities for Hive Mind orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha1


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: object) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return f"{prefix}_{sha1(raw.encode('utf-8')).hexdigest()[:16]}"
