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

MemoryObjectType = Literal["idea", "decision", "action", "question", "constraint", "preference", "artifact", "reflection"]
MemoryObjectStatus = Literal["draft", "reviewed", "accepted", "rejected", "speculative", "stale"]
HyperedgeType = Literal[
    "supports",
    "contradicts",
    "derives_from",
    "implements",
    "tests",
    "remembers",
    "compresses",
    "schedules",
    "depends_on",
    "generalizes",
    "specializes",
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


@dataclass(slots=True)
class MemoryObject:
    """Reviewable memory unit produced by imports, runs, or local workers."""

    id: str
    type: MemoryObjectType
    content: str
    origin: Literal["user", "assistant", "mixed", "unknown"]
    project: str
    confidence: float
    status: MemoryObjectStatus = "draft"
    raw_refs: list[str] = field(default_factory=list)
    source_run_id: str | None = None
    evidence_state: Literal["unreviewed", "supported", "unsupported", "conflicting"] = "unreviewed"
    attrs: dict[str, Any] = field(default_factory=dict)
    captured_at: str = field(default_factory=now_iso)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Hyperedge:
    """N-ary relation for memory/ontology events that cannot be represented by one edge."""

    id: str
    type: HyperedgeType
    members: list[str]
    source: str
    confidence: float = 1.0
    evidence_refs: list[str] = field(default_factory=list)
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


def make_memory_object(
    memory_type: MemoryObjectType,
    content: str,
    origin: Literal["user", "assistant", "mixed", "unknown"],
    project: str,
    raw_refs: list[str],
    confidence: float = 0.5,
    status: MemoryObjectStatus = "draft",
    source_run_id: str | None = None,
    **attrs: Any,
) -> MemoryObject:
    return MemoryObject(
        id=stable_id("mem", memory_type, content, origin, project, *raw_refs),
        type=memory_type,
        content=content,
        origin=origin,
        project=project,
        confidence=max(0.0, min(1.0, float(confidence))),
        status=status,
        raw_refs=raw_refs,
        source_run_id=source_run_id,
        attrs=attrs,
    )


def make_hyperedge(
    hyperedge_type: HyperedgeType,
    members: list[str],
    source: str,
    confidence: float = 1.0,
    evidence_refs: list[str] | None = None,
    **attrs: Any,
) -> Hyperedge:
    return Hyperedge(
        id=stable_id("hedge", hyperedge_type, source, *members),
        type=hyperedge_type,
        members=members,
        source=source,
        confidence=max(0.0, min(1.0, float(confidence))),
        evidence_refs=evidence_refs or [],
        attrs=attrs,
    )
