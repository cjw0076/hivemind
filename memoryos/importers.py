"""Importers for markdown notes and AI conversation exports."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .extract import extract_from_text, source_name
from .schema import Edge, Node, make_edge, stable_id


PARSER_VERSION = "0.2.0"


@dataclass(slots=True)
class ImportResult:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)


def import_path(path: Path) -> tuple[list[Node], list[Edge]]:
    result = import_path_with_warnings(path)
    return result.nodes, result.edges


def import_path_with_warnings(path: Path) -> ImportResult:
    warnings: list[dict[str, Any]] = []
    if path.suffix.lower() in {".md", ".txt"}:
        nodes, edges = import_markdown(path)
        return ImportResult(nodes, edges, warnings)
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            warn(warnings, path, "json", f"JSON parse failed: {exc}")
            return ImportResult(warnings=warnings)
        nodes, edges = import_chatgpt_json(path, data, warnings=warnings)
        return ImportResult(nodes, edges, warnings)
    if path.suffix.lower() == ".zip":
        nodes, edges = import_zip(path, warnings=warnings)
        return ImportResult(nodes, edges, warnings)
    raise ValueError(f"Unsupported import file: {path}")


def import_markdown(path: Path) -> tuple[list[Node], list[Edge]]:
    text = path.read_text(encoding="utf-8")
    source = source_name(path)
    title = first_heading(text) or path.name
    obs = Node(
        id=stable_id("obs", source, path.stat().st_mtime_ns),
        type="observation",
        title=title,
        text=text,
        source=source,
        attrs={"format": "markdown", "bytes": path.stat().st_size},
    )
    nodes = [obs]
    edges: list[Edge] = []
    extracted_nodes, extracted_edges = extract_from_text(obs, text, source)
    nodes.extend(extracted_nodes)
    edges.extend(extracted_edges)
    stamp_parser_metadata(nodes, "markdown")
    return nodes, edges


def import_zip(path: Path, warnings: list[dict[str, Any]] | None = None) -> tuple[list[Node], list[Edge]]:
    warnings = warnings if warnings is not None else []
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        conversation_name = next((name for name in names if name.endswith("conversations.json")), None)
        if conversation_name:
            try:
                data = json.loads(archive.read(conversation_name).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                warn(warnings, path, "zip", f"Skipped malformed {conversation_name}: {exc}")
                data = None
            if data is None:
                return [], []
            if looks_like_chatgpt(data):
                return import_chatgpt_json(path, data, warnings=warnings)
            return import_deepseek_json(path, data, warnings=warnings)

        grok_name = next((name for name in names if name.endswith("prod-grok-backend.json")), None)
        if grok_name:
            try:
                data = json.loads(archive.read(grok_name).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                warn(warnings, path, "zip", f"Skipped malformed {grok_name}: {exc}")
                return [], []
            return import_grok_json(path, data, warnings=warnings)

        markdown_names = [name for name in names if name.lower().endswith((".md", ".txt"))]
        if markdown_names:
            return import_markdown_zip(path, archive, markdown_names)

    raise ValueError(f"No supported conversation export found in {path}")


def import_chatgpt_json(path: Path, data: Any, warnings: list[dict[str, Any]] | None = None) -> tuple[list[Node], list[Edge]]:
    warnings = warnings if warnings is not None else []
    if not isinstance(data, list):
        warn(warnings, path, "chatgpt", "ChatGPT conversations export must be a JSON list")
        return [], []

    source = source_name(path)
    nodes: list[Node] = []
    edges: list[Edge] = []
    platform = Node(
        id=stable_id("concept", "ChatGPT"),
        type="concept",
        title="ChatGPT",
        text="ChatGPT",
        source=source,
        attrs={"kind": "platform"},
    )
    nodes.append(platform)

    for conv_index, conv in enumerate(data):
        if not isinstance(conv, dict):
            warn(warnings, path, "chatgpt", "Skipped non-object conversation", index=conv_index)
            continue
        conv_id = str(conv.get("id") or stable_id("conversation", source, conv_index))
        title = str(conv.get("title") or f"ChatGPT conversation {conv_index + 1}")
        conv_node = Node(
            id=stable_id("conversation", "chatgpt", conv_id),
            type="conversation",
            title=title,
            text=title,
            source=source,
            created_at=timestamp_or_none(conv.get("create_time")),
            attrs={"platform": "chatgpt", "raw_id": conv_id},
        )
        nodes.append(conv_node)
        edges.append(make_edge("contains", platform.id, conv_node.id, source))

        messages = flatten_chatgpt_messages(conv)
        previous_id: str | None = None
        previous_user_id: str | None = None
        for turn_index, msg in enumerate(messages):
            msg_node = Node(
                id=stable_id("message", "chatgpt", conv_id, msg["id"]),
                type="message",
                text=msg["content"],
                title=msg.get("role"),
                source=source,
                created_at=timestamp_or_none(msg.get("created_at")),
                attrs={
                    "platform": "chatgpt",
                    "conversation_id": conv_node.id,
                    "role": msg.get("role"),
                    "turn_index": turn_index,
                    "model": msg.get("model"),
                },
            )
            nodes.append(msg_node)
            edges.append(make_edge("contains", conv_node.id, msg_node.id, source))
            if previous_id:
                edges.append(make_edge("next", previous_id, msg_node.id, source))
            if msg.get("role") == "assistant" and previous_user_id:
                pair_node = Node(
                    id=stable_id("pair", previous_user_id, msg_node.id),
                    type="pair",
                    text=f"INPUT:\n{previous_user_id}\n\nOUTPUT:\n{msg_node.id}",
                    title=title,
                    source=source,
                    attrs={
                        "platform": "chatgpt",
                        "conversation_id": conv_node.id,
                        "input_message_id": previous_user_id,
                        "output_message_id": msg_node.id,
                    },
                )
                nodes.append(pair_node)
                edges.append(make_edge("answered_by", previous_user_id, msg_node.id, source))
                edges.append(make_edge("contains", conv_node.id, pair_node.id, source))
            if msg.get("role") == "user":
                previous_user_id = msg_node.id
            previous_id = msg_node.id

            extracted_nodes, extracted_edges = extract_from_text(msg_node, msg["content"], source)
            nodes.extend(extracted_nodes)
            edges.extend(extracted_edges)

    stamp_parser_metadata(nodes, "chatgpt")
    return nodes, edges


def import_deepseek_json(path: Path, data: Any, warnings: list[dict[str, Any]] | None = None) -> tuple[list[Node], list[Edge]]:
    warnings = warnings if warnings is not None else []
    if not isinstance(data, list):
        warn(warnings, path, "deepseek", "DeepSeek conversations export must be a JSON list")
        return [], []
    return import_linear_mapping_export(path, data, platform="deepseek", warnings=warnings)


def import_grok_json(path: Path, data: Any, warnings: list[dict[str, Any]] | None = None) -> tuple[list[Node], list[Edge]]:
    warnings = warnings if warnings is not None else []
    if not isinstance(data, dict):
        warn(warnings, path, "grok", "Grok export must be a JSON object")
        return [], []

    source = source_name(path)
    nodes: list[Node] = []
    edges: list[Edge] = []
    platform = Node(
        id=stable_id("concept", "Grok"),
        type="concept",
        title="Grok",
        text="Grok",
        source=source,
        attrs={"kind": "platform"},
    )
    nodes.append(platform)

    for conv_index, item in enumerate(data.get("conversations") or []):
        if not isinstance(item, dict):
            warn(warnings, path, "grok", "Skipped non-object conversation item", index=conv_index)
            continue
        conv = item.get("conversation") or {}
        responses = item.get("responses") or []
        conv_id = str(conv.get("id") or stable_id("conversation", source, conv_index))
        title = str(conv.get("title") or f"Grok conversation {conv_index + 1}")
        conv_node = Node(
            id=stable_id("conversation", "grok", conv_id),
            type="conversation",
            title=title,
            text=title,
            source=source,
            created_at=parse_time_value(conv.get("create_time")),
            attrs={"platform": "grok", "raw_id": conv_id},
        )
        nodes.append(conv_node)
        edges.append(make_edge("contains", platform.id, conv_node.id, source))

        messages = []
        for response_item in responses:
            response = (response_item or {}).get("response") or {}
            text = response.get("message")
            if not isinstance(text, str) or not text.strip():
                continue
            sender = str(response.get("sender") or "")
            role = "user" if sender in {"human", "user"} else "assistant"
            messages.append(
                {
                    "id": response.get("_id") or stable_id("rawmsg", conv_id, text[:120]),
                    "role": role,
                    "content": text.strip(),
                    "created_at": parse_time_value(response.get("create_time")),
                    "model": response.get("model"),
                }
            )
        messages.sort(key=lambda item: (item.get("created_at") or "", item["id"]))
        add_messages(nodes, edges, conv_node, messages, source, "grok")

    stamp_parser_metadata(nodes, "grok")
    return nodes, edges


def import_markdown_zip(path: Path, archive: zipfile.ZipFile, names: list[str]) -> tuple[list[Node], list[Edge]]:
    source = source_name(path)
    nodes: list[Node] = []
    edges: list[Edge] = []
    bundle = Node(
        id=stable_id("observation", source, "markdown_zip"),
        type="observation",
        title=path.name,
        text=path.name,
        source=source,
        attrs={"format": "markdown_zip", "file_count": len(names)},
    )
    nodes.append(bundle)

    for name in sorted(names):
        raw = archive.read(name)
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("utf-8", errors="replace")
        title = first_heading(text) or Path(name).name
        obs = Node(
            id=stable_id("observation", source, name),
            type="observation",
            title=title,
            text=text,
            source=f"{source}!{name}",
            attrs={"format": "markdown", "archive": source, "archive_name": name, "bytes": len(raw)},
        )
        nodes.append(obs)
        edges.append(make_edge("contains", bundle.id, obs.id, source))
        extracted_nodes, extracted_edges = extract_from_text(obs, text, obs.source)
        nodes.extend(extracted_nodes)
        edges.extend(extracted_edges)

    stamp_parser_metadata(nodes, "markdown_zip")
    return nodes, edges


def import_linear_mapping_export(
    path: Path,
    data: list[Any],
    platform: str,
    warnings: list[dict[str, Any]] | None = None,
) -> tuple[list[Node], list[Edge]]:
    warnings = warnings if warnings is not None else []
    source = source_name(path)
    nodes: list[Node] = []
    edges: list[Edge] = []
    platform_title = platform.title()
    platform_node = Node(
        id=stable_id("concept", platform_title),
        type="concept",
        title=platform_title,
        text=platform_title,
        source=source,
        attrs={"kind": "platform"},
    )
    nodes.append(platform_node)

    for conv_index, conv in enumerate(data):
        if not isinstance(conv, dict):
            warn(warnings, path, platform, "Skipped non-object conversation", index=conv_index)
            continue
        conv_id = str(conv.get("id") or stable_id("conversation", source, conv_index))
        title = str(conv.get("title") or f"{platform_title} conversation {conv_index + 1}")
        conv_node = Node(
            id=stable_id("conversation", platform, conv_id),
            type="conversation",
            title=title,
            text=title,
            source=source,
            created_at=conv.get("inserted_at") or conv.get("created_at"),
            attrs={"platform": platform, "raw_id": conv_id},
        )
        nodes.append(conv_node)
        edges.append(make_edge("contains", platform_node.id, conv_node.id, source))
        messages = flatten_mapping_messages(conv, platform)
        add_messages(nodes, edges, conv_node, messages, source, platform)

    stamp_parser_metadata(nodes, platform)
    return nodes, edges


def add_messages(
    nodes: list[Node],
    edges: list[Edge],
    conv_node: Node,
    messages: list[dict[str, Any]],
    source: str,
    platform: str,
) -> None:
    previous_id: str | None = None
    previous_user_id: str | None = None
    for turn_index, msg in enumerate(messages):
        msg_node = Node(
            id=stable_id("message", platform, conv_node.id, msg["id"]),
            type="message",
            text=msg["content"],
            title=msg.get("role"),
            source=source,
            created_at=msg.get("created_at"),
            attrs={
                "platform": platform,
                "conversation_id": conv_node.id,
                "role": msg.get("role"),
                "turn_index": turn_index,
                "model": msg.get("model"),
            },
        )
        nodes.append(msg_node)
        edges.append(make_edge("contains", conv_node.id, msg_node.id, source))
        if previous_id:
            edges.append(make_edge("next", previous_id, msg_node.id, source))
        if msg.get("role") == "assistant" and previous_user_id:
            pair_node = Node(
                id=stable_id("pair", previous_user_id, msg_node.id),
                type="pair",
                text=f"INPUT_MESSAGE_ID: {previous_user_id}\nOUTPUT_MESSAGE_ID: {msg_node.id}",
                title=conv_node.title,
                source=source,
                attrs={
                    "platform": platform,
                    "conversation_id": conv_node.id,
                    "input_message_id": previous_user_id,
                    "output_message_id": msg_node.id,
                },
            )
            nodes.append(pair_node)
            edges.append(make_edge("answered_by", previous_user_id, msg_node.id, source))
            edges.append(make_edge("contains", conv_node.id, pair_node.id, source))
        if msg.get("role") == "user":
            previous_user_id = msg_node.id
        previous_id = msg_node.id

        extracted_nodes, extracted_edges = extract_from_text(msg_node, msg["content"], source)
        nodes.extend(extracted_nodes)
        edges.extend(extracted_edges)


def first_heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return None


def timestamp_or_none(value: Any) -> str | None:
    if value is None:
        return None
    try:
        from datetime import datetime, timezone

        return datetime.fromtimestamp(float(value), tz=timezone.utc).astimezone().isoformat(timespec="seconds")
    except (TypeError, ValueError, OSError):
        return None


def flatten_chatgpt_messages(conv: dict[str, Any]) -> list[dict[str, Any]]:
    mapping = conv.get("mapping")
    if not isinstance(mapping, dict):
        return []

    messages: list[dict[str, Any]] = []
    for node in mapping.values():
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        author = message.get("author") or {}
        role = author.get("role")
        if role not in {"user", "assistant", "system", "tool"}:
            continue
        content = extract_chatgpt_content(message.get("content"))
        if not content:
            continue
        messages.append(
            {
                "id": message.get("id") or stable_id("rawmsg", content[:120]),
                "role": role,
                "content": content,
                "created_at": message.get("create_time"),
                "model": (message.get("metadata") or {}).get("model_slug"),
            }
        )

    messages.sort(key=lambda item: (item.get("created_at") is None, item.get("created_at") or 0, item["id"]))
    return messages


def flatten_mapping_messages(conv: dict[str, Any], platform: str) -> list[dict[str, Any]]:
    mapping = conv.get("mapping")
    if not isinstance(mapping, dict):
        return []

    messages: list[dict[str, Any]] = []
    for raw_id, item in mapping.items():
        if not isinstance(item, dict):
            continue
        message = item.get("message")
        if not isinstance(message, dict):
            continue
        fragments = message.get("fragments")
        if not isinstance(fragments, list):
            continue
        for frag_index, fragment in enumerate(fragments):
            if not isinstance(fragment, dict):
                continue
            content = fragment.get("content")
            if not isinstance(content, str) or not content.strip():
                continue
            frag_type = str(fragment.get("type") or "").upper()
            role = "user" if frag_type in {"REQUEST", "USER"} else "assistant"
            messages.append(
                {
                    "id": f"{raw_id}:{frag_index}",
                    "role": role,
                    "content": content.strip(),
                    "created_at": message.get("inserted_at"),
                    "model": message.get("model") or platform,
                }
            )

    messages.sort(key=lambda item: (item.get("created_at") or "", item["id"]))
    return messages


def extract_chatgpt_content(content: Any) -> str:
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if isinstance(parts, list):
        values = []
        for part in parts:
            if isinstance(part, str):
                values.append(part)
            elif isinstance(part, dict):
                values.append(json.dumps(part, ensure_ascii=False, sort_keys=True))
        return "\n".join(value.strip() for value in values if value and value.strip()).strip()
    text = content.get("text")
    if isinstance(text, str):
        return text.strip()
    return ""


def looks_like_chatgpt(data: Any) -> bool:
    if not isinstance(data, list) or not data:
        return False
    first = data[0]
    if not isinstance(first, dict):
        return False
    mapping = first.get("mapping")
    if not isinstance(mapping, dict):
        return False
    for item in mapping.values():
        if not isinstance(item, dict):
            continue
        message = item.get("message")
        if isinstance(message, dict) and "author" in message:
            return True
    return False


def parse_time_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        date_value = value.get("$date")
        if isinstance(date_value, str):
            return date_value
        if isinstance(date_value, dict):
            number = date_value.get("$numberLong")
            if number is not None:
                try:
                    from datetime import datetime, timezone

                    return datetime.fromtimestamp(int(number) / 1000, tz=timezone.utc).isoformat(timespec="seconds")
                except (TypeError, ValueError, OSError):
                    return None
    return None


def warn(
    warnings: list[dict[str, Any]],
    path: Path,
    parser: str,
    message: str,
    index: int | None = None,
) -> None:
    item: dict[str, Any] = {
        "source": path.as_posix(),
        "parser": parser,
        "message": message,
    }
    if index is not None:
        item["index"] = index
    warnings.append(item)


def stamp_parser_metadata(nodes: list[Node], parser_name: str) -> None:
    for node in nodes:
        node.attrs.setdefault("parser_name", parser_name)
        node.attrs.setdefault("parser_version", PARSER_VERSION)
