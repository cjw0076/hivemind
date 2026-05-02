"""Shared schema helpers for the MemoryOS file-backed graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from hashlib import sha1
from typing import Any, Literal

NodeType = Literal[
    "observation",
    "conversation",
    "message",
    "pair",
    "claim",
    "decision",
    "assumption",
    "task",
    "question",
    "concept",
]

EdgeType = Literal[
    "contains",
    "next",
    "answered_by",
    "mentions",
    "extracts",
    "supports",
    "contradicts",
    "motivates",
    "depends_on",
    "about",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def stable_id(prefix: str, *parts: object) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return f"{prefix}_{sha1(raw.encode('utf-8')).hexdigest()[:16]}"


@dataclass(slots=True)
class Node:
    id: str
    type: NodeType
    text: str
    source: str
    created_at: str | None = None
    title: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=now_iso)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Edge:
    id: str
    type: EdgeType
    src: str
    dst: str
    source: str
    confidence: float = 1.0
    attrs: dict[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=now_iso)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


def make_edge(edge_type: EdgeType, src: str, dst: str, source: str, **attrs: Any) -> Edge:
    confidence = float(attrs.pop("confidence", 1.0))
    return Edge(
        id=stable_id("edge", edge_type, src, dst, source),
        type=edge_type,
        src=src,
        dst=dst,
        source=source,
        confidence=confidence,
        attrs=attrs,
    )
