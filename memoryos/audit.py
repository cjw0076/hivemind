"""Local audit and dashboard summary for MemoryOS."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from .store import GraphStore


def summarize(root: Path) -> dict:
    store = GraphStore(root)
    nodes = store.load_nodes()
    edges = store.load_edges()

    node_types = Counter(node.get("type") for node in nodes)
    edge_types = Counter(edge.get("type") for edge in edges)
    sources = Counter(node.get("source") for node in nodes if node.get("source"))

    concepts = [
        node
        for node in nodes
        if node.get("type") == "concept" and (node.get("title") or node.get("text"))
    ]
    concept_counts = Counter((node.get("title") or node.get("text")) for node in concepts)

    by_source = defaultdict(Counter)
    for node in nodes:
        by_source[node.get("source")][node.get("type")] += 1

    unresolved_questions = [
        node
        for node in nodes
        if node.get("type") == "question"
    ][:20]
    tasks = [node for node in nodes if node.get("type") == "task"][:20]
    decisions = [node for node in nodes if node.get("type") == "decision"][:20]

    return {
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "node_types": dict(node_types),
            "edge_types": dict(edge_types),
            "sources": dict(sources),
        },
        "top_concepts": dict(concept_counts.most_common(20)),
        "by_source": {source: dict(counts) for source, counts in by_source.items()},
        "sample_decisions": compact_nodes(decisions),
        "sample_tasks": compact_nodes(tasks),
        "sample_unresolved_questions": compact_nodes(unresolved_questions),
    }


def compact_nodes(nodes: list[dict]) -> list[dict]:
    result = []
    for node in nodes:
        text = " ".join(str(node.get("text", "")).split())
        result.append(
            {
                "id": node.get("id"),
                "source": node.get("source"),
                "text": text[:220],
            }
        )
    return result


def format_summary(summary: dict) -> str:
    lines = ["# MemoryOS Audit", ""]
    counts = summary["counts"]
    lines.append(f"- Nodes: {counts['nodes']}")
    lines.append(f"- Edges: {counts['edges']}")
    lines.append(f"- Node types: {counts['node_types']}")
    lines.append(f"- Edge types: {counts['edge_types']}")
    lines.append("")
    lines.append("## Top Concepts")
    for name, count in summary["top_concepts"].items():
        lines.append(f"- {name}: {count}")
    lines.append("")
    lines.append("## Sample Decisions")
    for node in summary["sample_decisions"]:
        lines.append(f"- {node['text']}")
    lines.append("")
    lines.append("## Sample Tasks")
    for node in summary["sample_tasks"]:
        lines.append(f"- {node['text']}")
    lines.append("")
    lines.append("## Sample Unresolved Questions")
    for node in summary["sample_unresolved_questions"]:
        lines.append(f"- {node['text']}")
    return "\n".join(lines) + "\n"
