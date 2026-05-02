"""Command line entrypoint for the local MemoryOS MVP."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from .audit import format_summary, summarize
from .importers import import_path_with_warnings
from .local_workers import choose_model, list_workers, local_runtime_status, read_input, render_prompt, run_worker
from .schema import Node, make_edge, now_iso, stable_id
from .store import GraphStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="memoryos", description="Local MemoryOS graph tools")
    parser.add_argument("--root", default=".", help="workspace root")
    sub = parser.add_subparsers(dest="cmd", required=True)

    import_cmd = sub.add_parser("import", help="import markdown or AI conversation export")
    import_cmd.add_argument("paths", nargs="+", help="files to import")
    import_cmd.add_argument("--dry-run", action="store_true", help="preview import counts without appending")

    import_run_cmd = sub.add_parser("import-run", help="import memory drafts from a hive run folder")
    import_run_cmd.add_argument("run", help="run id, run folder, or 'current'")
    import_run_cmd.add_argument("--dry-run", action="store_true", help="preview import counts without appending")

    audit_cmd = sub.add_parser("audit", help="summarize the local memory graph")
    audit_cmd.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    audit_cmd.add_argument("--out", help="optional output report path")

    stats_cmd = sub.add_parser("stats", help="show platform, role, conversation, pair, and source counts")
    stats_cmd.add_argument("--json", action="store_true", help="emit JSON instead of text")

    local_cmd = sub.add_parser("local-workers", help="inspect or run local LLM worker prompts")
    local_sub = local_cmd.add_subparsers(dest="local_cmd", required=True)
    local_sub.add_parser("list", help="list local worker roles")
    local_sub.add_parser("status", help="show local runtime availability")
    prompt_cmd = local_sub.add_parser("prompt", help="render a local worker prompt without calling a model")
    prompt_cmd.add_argument("worker", help="worker name")
    prompt_cmd.add_argument("--input", required=True, help="input text file")
    prompt_cmd.add_argument("--max-chars", type=int, default=12000, help="maximum input characters")
    prompt_cmd.add_argument("--out", help="optional output path")
    run_cmd = local_sub.add_parser("run", help="run a local worker through Ollama")
    run_cmd.add_argument("worker", help="worker name")
    run_cmd.add_argument("--input", required=True, help="input text file")
    run_cmd.add_argument("--model", help="Ollama model name")
    run_cmd.add_argument("--complexity", choices=["fast", "default", "strong"], default="default")
    run_cmd.add_argument("--base-url", default="http://127.0.0.1:11434", help="Ollama base URL")
    run_cmd.add_argument("--max-chars", type=int, default=12000, help="maximum input characters")
    run_cmd.add_argument("--out", help="optional JSON output path")

    harness_cmd = sub.add_parser("local", help="role-based Local Model Harness commands")
    harness_sub = harness_cmd.add_subparsers(dest="harness_cmd", required=True)
    for command_name in LOCAL_HARNESS_ROUTES:
        command = harness_sub.add_parser(command_name, help=f"run local {command_name} worker")
        command.add_argument("--input", required=True, help="input text file")
        command.add_argument("--model", help="Ollama model name")
        command.add_argument("--complexity", choices=["fast", "default", "strong"], default="default")
        command.add_argument("--base-url", default="http://127.0.0.1:11434", help="Ollama base URL")
        command.add_argument("--max-chars", type=int, default=12000, help="maximum input characters")
        command.add_argument("--out", help="optional JSON output path")

    args = parser.parse_args()
    root = Path(args.root).resolve()

    if args.cmd == "import":
        store = GraphStore(root)
        total_nodes = 0
        total_edges = 0
        total_skipped_nodes = 0
        total_skipped_edges = 0
        for raw_path in args.paths:
            path = Path(raw_path)
            if not path.is_absolute():
                path = root / path
            result = import_path_with_warnings(path)
            nodes, edges = result.nodes, result.edges
            annotate_import(nodes, edges, path)
            if args.dry_run:
                node_count, edge_count, skipped_nodes, skipped_edges = store.preview_append(nodes, edges)
            else:
                node_count, edge_count, skipped_nodes, skipped_edges = store.append(nodes, edges)
            total_nodes += node_count
            total_edges += edge_count
            total_skipped_nodes += skipped_nodes
            total_skipped_edges += skipped_edges
            verb = "would import" if args.dry_run else "imported"
            print(
                f"{verb} {path}: {node_count} nodes, {edge_count} edges "
                f"({skipped_nodes} duplicate nodes, {skipped_edges} duplicate edges skipped)"
            )
            for warning in result.warnings:
                location = f" index={warning['index']}" if "index" in warning else ""
                print(f"warning {path}:{location} {warning['parser']}: {warning['message']}")
        prefix = "dry-run total" if args.dry_run else "total"
        print(
            f"{prefix}: {total_nodes} nodes, {total_edges} edges "
            f"({total_skipped_nodes} duplicate nodes, {total_skipped_edges} duplicate edges skipped)"
        )
        return

    if args.cmd == "import-run":
        store = GraphStore(root)
        nodes, edges = build_run_import(root, args.run)
        if args.dry_run:
            node_count, edge_count, skipped_nodes, skipped_edges = store.preview_append(nodes, edges)
            verb = "would import"
        else:
            node_count, edge_count, skipped_nodes, skipped_edges = store.append(nodes, edges)
            verb = "imported"
        print(
            f"{verb} run {args.run}: {node_count} nodes, {edge_count} edges "
            f"({skipped_nodes} duplicate nodes, {skipped_edges} duplicate edges skipped)"
        )
        return

    if args.cmd == "audit":
        summary = summarize(root)
        output = json.dumps(summary, ensure_ascii=False, indent=2) if args.json else format_summary(summary)
        if args.out:
            out_path = Path(args.out)
            if not out_path.is_absolute():
                out_path = root / out_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
            print(f"wrote {out_path}")
        else:
            print(output)
        return

    if args.cmd == "stats":
        stats = build_stats(GraphStore(root))
        if args.json:
            print(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_stats(stats))
        return

    if args.cmd == "local-workers":
        if args.local_cmd == "list":
            print(json.dumps(list_workers(), ensure_ascii=False, indent=2))
            return
        if args.local_cmd == "status":
            print(json.dumps(local_runtime_status(), ensure_ascii=False, indent=2))
            return
        if args.local_cmd == "prompt":
            input_path = Path(args.input)
            if not input_path.is_absolute():
                input_path = root / input_path
            input_text, source_ref = read_input(input_path, args.max_chars)
            output = render_prompt(args.worker, input_text, source_ref=source_ref)
            if args.out:
                out_path = Path(args.out)
                if not out_path.is_absolute():
                    out_path = root / out_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(output, encoding="utf-8")
                print(f"wrote {out_path}")
            else:
                print(output)
            return
        if args.local_cmd == "run":
            input_path = Path(args.input)
            if not input_path.is_absolute():
                input_path = root / input_path
            input_text, source_ref = read_input(input_path, args.max_chars)
            result = run_worker(
                args.worker,
                input_text,
                model=args.model or choose_model(args.worker, args.complexity),
                base_url=args.base_url,
                source_ref=source_ref,
            )
            output = json.dumps(result, ensure_ascii=False, indent=2)
            if args.out:
                out_path = Path(args.out)
                if not out_path.is_absolute():
                    out_path = root / out_path
                out_path.parent.mkdir(parents=True, exist_ok=True)
                out_path.write_text(output, encoding="utf-8")
                print(f"wrote {out_path}")
            else:
                print(output)
            return

    if args.cmd == "local":
        worker = LOCAL_HARNESS_ROUTES[args.harness_cmd]
        input_path = Path(args.input)
        if not input_path.is_absolute():
            input_path = root / input_path
        input_text, source_ref = read_input(input_path, args.max_chars)
        result = run_worker(
            worker,
            input_text,
            model=args.model or choose_model(worker, args.complexity),
            base_url=args.base_url,
            source_ref=source_ref,
        )
        output = json.dumps(result, ensure_ascii=False, indent=2)
        if args.out:
            out_path = Path(args.out)
            if not out_path.is_absolute():
                out_path = root / out_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
            print(f"wrote {out_path}")
        else:
            print(output)
        return


LOCAL_HARNESS_ROUTES = {
    "classify": "classifier",
    "extract-memory": "memory_extractor",
    "extract-capability": "capability_extractor",
    "compress-context": "context_compressor",
    "draft-handoff": "handoff_drafter",
    "summarize-log": "log_summarizer",
    "review-diff": "diff_reviewer",
}


def annotate_import(nodes, edges, path: Path) -> None:
    source_hash = sha256_file(path)
    imported_at = now_iso()
    import_run_id = stable_id("import", path.as_posix(), source_hash, imported_at)
    attrs = {
        "import_run_id": import_run_id,
        "imported_at": imported_at,
        "source_sha256": source_hash,
        "source_path": path.as_posix(),
    }
    for node in nodes:
        node.attrs.update(attrs)
    for edge in edges:
        edge.attrs.update(attrs)


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_run_import(root: Path, run_ref: str):
    run_dir = resolve_run_dir(root, run_ref)
    state_path = run_dir / "run_state.json"
    drafts_path = run_dir / "memory_drafts.json"
    if not state_path.exists():
        raise FileNotFoundError(f"run_state.json not found: {state_path}")
    if not drafts_path.exists():
        raise FileNotFoundError(f"memory_drafts.json not found: {drafts_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    drafts = json.loads(drafts_path.read_text(encoding="utf-8")).get("memory_drafts") or []
    source = f"run:{run_dir.name}"
    run_node = Node(
        id=stable_id("observation", source, "run"),
        type="observation",
        title=f"Run {run_dir.name}",
        text=state.get("user_request", run_dir.name),
        source=source,
        attrs={
            "kind": "agent_run",
            "run_id": run_dir.name,
            "phase": state.get("phase"),
            "status": state.get("status"),
            "run_dir": run_dir.relative_to(root).as_posix() if run_dir.is_relative_to(root) else run_dir.as_posix(),
        },
    )
    nodes = [run_node]
    edges = []
    task_node = Node(
        id=stable_id("task", source, state.get("user_request", "")),
        type="task",
        title=state.get("user_request", "Run task"),
        text=state.get("user_request", ""),
        source=source,
        attrs={"run_id": run_dir.name, "project": state.get("project"), "status": "draft"},
    )
    nodes.append(task_node)
    edges.append(make_edge("contains", run_node.id, task_node.id, source))
    for index, draft in enumerate(drafts):
        if not isinstance(draft, dict):
            continue
        node_type = draft_node_type(str(draft.get("type") or "observation"))
        content = str(draft.get("content") or "").strip()
        if not content:
            continue
        node = Node(
            id=stable_id(node_type, source, index, content[:240]),
            type=node_type,
            title=str(draft.get("type") or node_type),
            text=content,
            source=source,
            attrs={
                "run_id": run_dir.name,
                "draft_index": index,
                "draft_type": draft.get("type"),
                "origin": draft.get("origin", "unknown"),
                "confidence": draft.get("confidence"),
                "status": draft.get("status", "draft"),
                "raw_refs": draft.get("raw_refs") or [],
                "project": draft.get("project") or state.get("project"),
            },
        )
        nodes.append(node)
        edges.append(make_edge("contains", run_node.id, node.id, source))
    return nodes, edges


def resolve_run_dir(root: Path, run_ref: str) -> Path:
    if run_ref == "current":
        current_path = root / ".runs" / "current"
        if not current_path.exists():
            raise FileNotFoundError("No current run found at .runs/current")
        run_ref = current_path.read_text(encoding="utf-8").strip()
    path = Path(run_ref)
    if path.exists():
        return path.resolve()
    return root / ".runs" / run_ref


def draft_node_type(draft_type: str) -> str:
    return {
        "decision": "decision",
        "action": "task",
        "question": "question",
        "constraint": "assumption",
        "preference": "assumption",
        "idea": "claim",
    }.get(draft_type, "observation")


def build_stats(store: GraphStore) -> dict:
    nodes = store.load_nodes()
    edges = store.load_edges()

    node_types = Counter(node.get("type") for node in nodes)
    edge_types = Counter(edge.get("type") for edge in edges)
    platforms = Counter()
    roles = Counter()
    sources = Counter()

    for node in nodes:
        attrs = node.get("attrs") or {}
        platform = attrs.get("platform")
        role = attrs.get("role")
        if platform:
            platforms[str(platform)] += 1
        if role:
            roles[str(role)] += 1
        source = node.get("source")
        if source:
            sources[str(source)] += 1

    return {
        "nodes": len(nodes),
        "edges": len(edges),
        "node_types": dict(node_types),
        "edge_types": dict(edge_types),
        "platforms": dict(platforms),
        "roles": dict(roles),
        "conversations": node_types.get("conversation", 0),
        "pairs": node_types.get("pair", 0),
        "sources": dict(sources.most_common(30)),
    }


def format_stats(stats: dict) -> str:
    lines = [
        "# MemoryOS Stats",
        "",
        f"- Nodes: {stats['nodes']}",
        f"- Edges: {stats['edges']}",
        f"- Conversations: {stats['conversations']}",
        f"- Pairs: {stats['pairs']}",
        f"- Node types: {stats['node_types']}",
        f"- Edge types: {stats['edge_types']}",
        f"- Platforms: {stats['platforms']}",
        f"- Roles: {stats['roles']}",
        "",
        "## Top Sources",
    ]
    for source, count in stats["sources"].items():
        lines.append(f"- {source}: {count}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
