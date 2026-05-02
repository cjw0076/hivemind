"""Append-only JSONL store for MemoryOS graph objects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Iterator

from .schema import Edge, Node


class GraphStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.nodes_path = root / "memory" / "processed" / "nodes.jsonl"
        self.edges_path = root / "ontology" / "edges.jsonl"

    def ensure(self) -> None:
        self.nodes_path.parent.mkdir(parents=True, exist_ok=True)
        self.edges_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, nodes: Iterable[Node], edges: Iterable[Edge]) -> tuple[int, int, int, int]:
        self.ensure()
        existing_node_ids = self.existing_ids(self.nodes_path)
        existing_edge_ids = self.existing_ids(self.edges_path)

        new_nodes = []
        skipped_nodes = 0
        for node in nodes:
            if node.id in existing_node_ids:
                skipped_nodes += 1
                continue
            existing_node_ids.add(node.id)
            new_nodes.append(node.to_json())

        new_edges = []
        skipped_edges = 0
        for edge in edges:
            if edge.id in existing_edge_ids:
                skipped_edges += 1
                continue
            existing_edge_ids.add(edge.id)
            new_edges.append(edge.to_json())

        node_count = self._append_jsonl(self.nodes_path, new_nodes)
        edge_count = self._append_jsonl(self.edges_path, new_edges)
        return node_count, edge_count, skipped_nodes, skipped_edges

    def preview_append(self, nodes: Iterable[Node], edges: Iterable[Edge]) -> tuple[int, int, int, int]:
        existing_node_ids = self.existing_ids(self.nodes_path)
        existing_edge_ids = self.existing_ids(self.edges_path)
        new_node_ids = set()
        new_edge_ids = set()
        skipped_nodes = 0
        skipped_edges = 0

        for node in nodes:
            if node.id in existing_node_ids or node.id in new_node_ids:
                skipped_nodes += 1
            else:
                new_node_ids.add(node.id)
        for edge in edges:
            if edge.id in existing_edge_ids or edge.id in new_edge_ids:
                skipped_edges += 1
            else:
                new_edge_ids.add(edge.id)

        return len(new_node_ids), len(new_edge_ids), skipped_nodes, skipped_edges

    def load_nodes(self) -> list[dict]:
        return list(self._read_jsonl(self.nodes_path))

    def load_edges(self) -> list[dict]:
        return list(self._read_jsonl(self.edges_path))

    @staticmethod
    def existing_ids(path: Path) -> set[str]:
        ids: set[str] = set()
        for row in GraphStore._read_jsonl(path):
            row_id = row.get("id")
            if isinstance(row_id, str):
                ids.add(row_id)
        return ids

    @staticmethod
    def _append_jsonl(path: Path, rows: list[dict]) -> int:
        if not rows:
            return 0
        with path.open("a", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return len(rows)

    @staticmethod
    def _read_jsonl(path: Path) -> Iterator[dict]:
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)
