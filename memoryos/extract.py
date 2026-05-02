"""Deterministic extraction pass for early MemoryOS ingestion."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .schema import Edge, Node, make_edge, stable_id

KOREAN_TASK_HINTS = ("해야", "하자", "만들", "구현", "추가", "다음", "필요", "추천")
KOREAN_DECISION_HINTS = ("결론", "정의", "맞다", "잡아야", "가야", "추천", "핵심")
KOREAN_ASSUMPTION_HINTS = ("아마", "가능성", "가설", "보면", "해석", "전제")
QUESTION_MARKERS = ("?", "까", "어떻게", "왜", "무엇", "뭐")

CONCEPT_SEEDS = {
    "MemoryOS",
    "Dipeen",
    "GoEN",
    "Asimov",
    "ontology",
    "hypergraph",
    "agent",
    "memory",
    "graph",
    "plasticity",
    "LLM",
    "Claude",
    "GPT",
    "Gemini",
    "Perplexity",
    "ChatGPT",
    "Neo4j",
    "SQLite",
    "embedding",
    "Personal Thought Encoder",
}


def extract_from_text(parent: Node, text: str, source: str) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []

    chunks = split_chunks(text)
    for idx, chunk in enumerate(chunks):
        node_type = classify_chunk(chunk)
        if node_type is None:
            continue
        node = Node(
            id=stable_id(node_type, parent.id, idx, chunk[:240]),
            type=node_type,
            text=chunk,
            source=source,
            attrs={"parent": parent.id, "heuristic": True},
        )
        nodes.append(node)
        edges.append(make_edge("extracts", parent.id, node.id, source, confidence=0.62))

    for concept in extract_concepts(text):
        concept_node = Node(
            id=stable_id("concept", concept.lower()),
            type="concept",
            title=concept,
            text=concept,
            source=source,
            attrs={"kind": "seed_or_surface_form"},
        )
        nodes.append(concept_node)
        edges.append(make_edge("mentions", parent.id, concept_node.id, source, confidence=0.74))

    return nodes, edges


def split_chunks(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    chunks: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line:
            if current:
                chunks.append(" ".join(current).strip())
                current = []
            continue
        if line.startswith(("#", "-", "*")) and current:
            chunks.append(" ".join(current).strip())
            current = []
        current.append(re.sub(r"^\s*[-*#]+\s*", "", line))
    if current:
        chunks.append(" ".join(current).strip())
    return [chunk for chunk in chunks if len(chunk) >= 24]


def classify_chunk(chunk: str) -> str | None:
    lower = chunk.lower()
    if any(marker in chunk for marker in QUESTION_MARKERS):
        return "question"
    if any(hint in chunk for hint in KOREAN_TASK_HINTS) or lower.startswith(("todo", "next")):
        return "task"
    if any(hint in chunk for hint in KOREAN_ASSUMPTION_HINTS):
        return "assumption"
    if any(hint in chunk for hint in KOREAN_DECISION_HINTS):
        return "decision"
    if 36 <= len(chunk) <= 320:
        return "claim"
    return None


def extract_concepts(text: str) -> list[str]:
    found: Counter[str] = Counter()
    lower = text.lower()
    for seed in CONCEPT_SEEDS:
        if seed.lower() in lower:
            found[seed] += 3

    for match in re.finditer(r"\b[A-Z][A-Za-z0-9-]{2,}(?:\s+[A-Z][A-Za-z0-9-]{2,}){0,3}\b", text):
        value = match.group(0).strip()
        if len(value) <= 48:
            found[value] += 1

    for match in re.finditer(r"\b[a-zA-Z]+(?:-[a-zA-Z]+)*(?:\s+[a-zA-Z]+(?:-[a-zA-Z]+)*){1,3}\b", text):
        value = match.group(0).strip()
        if any(token in value.lower() for token in ("graph", "agent", "memory", "ontology", "embedding")):
            found[value] += 1

    return [name for name, _ in found.most_common(32)]


def source_name(path: Path) -> str:
    return path.as_posix()
