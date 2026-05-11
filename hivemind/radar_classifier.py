"""Deterministic ASC-0007 task-radar quality gate.

The classifier is deliberately local and data-minimal: it reads radar rows and
uses only path, domain, score, and signal labels. It does not read candidate
document bodies or call provider/local LLM runtimes.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERDICTS = {"executable", "needs_context", "needs_capability", "ambiguous", "out_of_scope"}
EXTERNAL_DOMAINS = {"_from_desktop", "deepfake", "fire", "universe"}
ACTION_SIGNALS = {"next", "todo", "verify", "p0"}
QUALITY_SIGNALS = {"blocker", "gap", "contract", "stop_condition"}
RATIONALE_LIMIT = 300


@dataclass(frozen=True)
class RadarCandidate:
    rank: int
    score: int
    domain: str
    path: str
    signal_labels: dict[str, int]
    candidate_task: str = ""
    path_exists: bool = False


@dataclass(frozen=True)
class RadarReview:
    rank: int
    score: int
    domain: str
    path: str
    signal_labels: dict[str, int]
    path_exists: bool
    verdict: str
    rationale: str


def review_radar(radar_path: Path, top: int = 10, workspace_root: Path | None = None) -> dict[str, Any]:
    """Parse a radar artifact and classify its top candidates."""
    radar_path = radar_path.resolve()
    text = radar_path.read_text(encoding="utf-8")
    detected_root = workspace_root or detect_radar_root(text) or radar_path.parents[2]
    candidates = parse_radar(text, workspace_root=detected_root)
    selected = candidates[:top]
    reviews = [classify_candidate(candidate) for candidate in selected]
    return {
        "schema": "hivemind.radar_review.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "radar_path": radar_path.as_posix(),
        "workspace_root": detected_root.resolve().as_posix(),
        "top": top,
        "verdicts": sorted(VERDICTS),
        "entries": [asdict(review) for review in reviews],
    }


def parse_radar(text: str, workspace_root: Path) -> list[RadarCandidate]:
    stripped = text.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        return parse_json_radar(text, workspace_root=workspace_root)
    return parse_markdown_radar(text, workspace_root=workspace_root)


def parse_json_radar(text: str, workspace_root: Path) -> list[RadarCandidate]:
    payload = json.loads(text)
    rows = payload.get("top_task_signals") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        raise ValueError("radar JSON must be a list or contain top_task_signals")
    candidates: list[RadarCandidate] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        path = clean_cell(str(row.get("path", "")))
        signals = parse_signals(row.get("signals") or row.get("signal_labels") or {})
        candidates.append(
            RadarCandidate(
                rank=index,
                score=int(row.get("score", 0)),
                domain=str(row.get("domain", "")),
                path=path,
                signal_labels=signals,
                candidate_task=str(row.get("candidate_task", "")),
                path_exists=resolve_candidate_path(path, workspace_root).exists(),
            )
        )
    return candidates


def parse_markdown_radar(text: str, workspace_root: Path) -> list[RadarCandidate]:
    candidates: list[RadarCandidate] = []
    in_table = False
    for line in text.splitlines():
        if line.startswith("| Score | Domain | Path | Signals | Candidate Task |"):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            if candidates:
                break
            continue
        if re.fullmatch(r"\|\s*-+:?\s*\|.*", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 5:
            continue
        score_text, domain, path_text, signals_text, task = cells[:5]
        try:
            score = int(score_text)
        except ValueError:
            continue
        path = clean_cell(path_text)
        candidates.append(
            RadarCandidate(
                rank=len(candidates) + 1,
                score=score,
                domain=clean_cell(domain),
                path=path,
                signal_labels=parse_signals(signals_text),
                candidate_task=clean_cell(task),
                path_exists=resolve_candidate_path(path, workspace_root).exists(),
            )
        )
    if not candidates:
        raise ValueError("No radar candidate rows found")
    return candidates


def classify_candidate(candidate: RadarCandidate) -> RadarReview:
    verdict, reason = choose_verdict(candidate)
    rationale = clip_rationale(reason)
    return RadarReview(
        rank=candidate.rank,
        score=candidate.score,
        domain=candidate.domain,
        path=candidate.path,
        signal_labels=candidate.signal_labels,
        path_exists=candidate.path_exists,
        verdict=verdict,
        rationale=rationale,
    )


def choose_verdict(candidate: RadarCandidate) -> tuple[str, str]:
    labels = candidate.signal_labels
    path = candidate.path
    domain = candidate.domain

    if domain in EXTERNAL_DOMAINS or path.startswith("_from_desktop/"):
        return "out_of_scope", f"{path}: external domain {domain}; keep as path-only context before AIOS dispatch."

    if not candidate.path_exists:
        return "needs_context", f"{path}: radar path is missing; refresh context or source location before execution."

    if domain == "memoryOS" or "/memoryOS/" in path:
        return "needs_context", f"{path}: memoryOS signal; needs MemoryOS context/provenance owner before Hive execution."

    if domain == "CapabilityOS" or "/CapabilityOS/" in path:
        return "needs_capability", f"{path}: CapabilityOS signal; needs capability route/recommendation before dispatch."

    if domain == "myworld":
        return "ambiguous", f"{path}: control-plane signal; operator must decide contract/release before Hive execution."

    if domain == "hivemind" or "/hivemind/" in path:
        action_score = sum(labels.get(label, 0) for label in ACTION_SIGNALS)
        quality_score = sum(labels.get(label, 0) for label in QUALITY_SIGNALS)
        if action_score > 0 and quality_score > 0:
            return "executable", f"{path}: Hive-owned path exists with action and quality signals; ready for bounded packet review."
        return "ambiguous", f"{path}: Hive path exists, but signal mix lacks clear action/quality evidence."

    if labels.get("capabilityos", 0) >= 8:
        return "needs_capability", f"{path}: capability signal is high; request CapabilityOS recommendation first."

    return "ambiguous", f"{path}: signal domain does not map to a single executable Hive packet."


def write_review_artifacts(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "radar_review.json"
    md_path = out_dir / "RADAR_REVIEW.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(format_review_markdown(report), encoding="utf-8")
    return json_path, md_path


def format_review_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Radar Review",
        "",
        "Generated by `hive radar-review` from ASC-0007 radar signals.",
        "",
        f"- radar_path: `{report['radar_path']}`",
        f"- workspace_root: `{report['workspace_root']}`",
        f"- top: `{report['top']}`",
        "",
        "| Rank | Score | Domain | Path | Verdict | Rationale |",
        "| ---: | ---: | --- | --- | --- | --- |",
    ]
    for entry in report["entries"]:
        lines.append(
            "| {rank} | {score} | {domain} | `{path}` | {verdict} | {rationale} |".format(
                rank=entry["rank"],
                score=entry["score"],
                domain=escape_table(entry["domain"]),
                path=escape_table(entry["path"]),
                verdict=entry["verdict"],
                rationale=escape_table(entry["rationale"]),
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Advisory only; operator chooses which candidates become contracts.",
            "- Classifier uses path, domain, score, and signal labels only.",
            "- No external LLM provider or source document body is used.",
            "",
        ]
    )
    return "\n".join(lines)


def detect_radar_root(text: str) -> Path | None:
    match = re.search(r"- root:\s*`([^`]+)`", text)
    if not match:
        return None
    return Path(match.group(1)).expanduser().resolve()


def parse_signals(value: Any) -> dict[str, int]:
    if isinstance(value, dict):
        return {str(key): int(score) for key, score in value.items()}
    text = clean_cell(str(value))
    signals: dict[str, int] = {}
    for item in text.split(","):
        if ":" not in item:
            continue
        label, score = item.split(":", 1)
        try:
            signals[label.strip()] = int(score.strip())
        except ValueError:
            continue
    return signals


def resolve_candidate_path(path: str, workspace_root: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return workspace_root / candidate


def clean_cell(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == "`" and value[-1] == "`":
        return value[1:-1].strip()
    return value


def clip_rationale(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= RATIONALE_LIMIT:
        return text
    return text[: RATIONALE_LIMIT - 1].rstrip() + "."


def escape_table(value: str) -> str:
    return value.replace("|", "\\|")
