"""Goal sprint read model for Hive Mind."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


OBJECTIVE = (
    "Complete Hive Mind production-v0 as a local provider-CLI operating harness "
    "without claiming full AIOS or autonomous long-horizon cognition."
)

STOPPING_CONDITION = (
    "`scripts/public-release-check.sh` passes with zero failures and includes a "
    "passing `scripts/user-value-benchmark.py` report after adversarial review."
)

VALIDATION_COMMANDS = [
    "python scripts/user-value-benchmark.py",
    "python -m unittest discover -s tests -p 'test_*.py'",
    "bash scripts/public-release-check.sh",
]

REQUIRED_READS = [
    "docs/GOAL.md",
    "docs/PUBLISHING_GATE.md",
    "docs/AGENT_WORKLOG.md",
    ".ai-runs/shared/comms_log.md",
    "scripts/user-value-benchmark.py",
    "scripts/public-release-check.sh",
]


def build_goal_report(root: Path) -> dict[str, Any]:
    """Return the current production-v0 goal sprint status."""
    goal_path = root / "docs" / "GOAL.md"
    benchmark = _latest_value_benchmark(root)
    release = _latest_release_gate(root)
    return {
        "schema_version": 1,
        "kind": "hive_goal_status",
        "status": "active",
        "objective": OBJECTIVE,
        "stopping_condition": STOPPING_CONDITION,
        "goal_path": _rel(root, goal_path),
        "required_reads": REQUIRED_READS,
        "validation_commands": VALIDATION_COMMANDS,
        "latest_value_benchmark": benchmark,
        "latest_release_gate": release,
        "attack_pack_command": "hive goal --write-attack-pack",
        "claude_attack_prompt": build_claude_attack_prompt(root, benchmark, release),
    }


def build_claude_attack_prompt(root: Path, benchmark: dict[str, Any] | None = None, release: dict[str, Any] | None = None) -> str:
    """Build a compact prompt for a Claude adversarial review."""
    benchmark = benchmark if benchmark is not None else _latest_value_benchmark(root)
    release = release if release is not None else _latest_release_gate(root)
    benchmark_path = benchmark.get("path", "none") if benchmark else "none"
    release_path = release.get("path", "none") if release else "none"
    return "\n".join(
        [
            "You are Claude acting as an adversarial Hive Mind production-v0 reviewer.",
            "Read docs/GOAL.md, docs/PUBLISHING_GATE.md, docs/AGENT_WORKLOG.md, and .ai-runs/shared/comms_log.md first.",
            f"Latest value benchmark: {benchmark_path}",
            f"Latest release gate: {release_path}",
            "Attack the claim that Hive Mind is useful beyond direct provider CLI usage.",
            "Find cases where Hive adds ceremony without enough audit, policy, recovery, or multi-agent value.",
            "Check provider passthrough safety, missing receipts, ledger replay, stop/inspect UX, Korean/Unicode prompts, and MemoryOS graceful degrade.",
            "Write findings with severity, reproduction command, expected behavior, and recommended fix.",
            "Log a short summary to .ai-runs/shared/comms_log.md.",
        ]
    )


def format_goal_report(report: dict[str, Any]) -> str:
    """Format the current goal sprint status for terminal use."""
    lines = [
        "Hive Mind Goal Sprint",
        "",
        f"Status: {report.get('status')}",
        f"Goal: {report.get('objective')}",
        f"Stop: {report.get('stopping_condition')}",
        "",
        "Required reads:",
    ]
    lines.extend(f"  - {item}" for item in report.get("required_reads", []))
    lines.append("")
    lines.append("Validation:")
    lines.extend(f"  - {item}" for item in report.get("validation_commands", []))
    lines.append("")
    lines.append(_format_artifact_summary("Latest value benchmark", report.get("latest_value_benchmark")))
    lines.append(_format_artifact_summary("Latest release gate", report.get("latest_release_gate")))
    lines.append("")
    lines.append("Claude attack prompt:")
    lines.append(report.get("claude_attack_prompt", ""))
    lines.append("")
    lines.append(f"Attack pack: {report.get('attack_pack_command')}")
    return "\n".join(lines)


def write_attack_pack(root: Path) -> dict[str, Any]:
    """Write a self-contained Markdown pack for adversarial review."""
    report = build_goal_report(root)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = root / ".hivemind" / "goal"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"attack-pack-{stamp}.md"
    text = _format_attack_pack(report)
    path.write_text(text, encoding="utf-8")
    return {
        "schema_version": 1,
        "kind": "hive_goal_attack_pack",
        "path": _rel(root, path),
        "goal_status": report.get("status"),
        "latest_value_benchmark": report.get("latest_value_benchmark"),
        "latest_release_gate": report.get("latest_release_gate"),
    }


def _latest_value_benchmark(root: Path) -> dict[str, Any]:
    candidates = sorted((root / ".hivemind" / "benchmarks").glob("user-value-*.json"), reverse=True)
    if not candidates:
        return {"status": "missing", "path": None}
    path = candidates[0]
    data = _read_json(path)
    summary = data.get("summary") if isinstance(data, dict) else {}
    return {
        "status": "present",
        "path": _rel(root, path),
        "verdict": summary.get("verdict"),
        "direct_cli_for_trivial": summary.get("direct_cli_for_trivial"),
        "hive_for_audited_multi_agent": summary.get("hive_for_audited_multi_agent"),
        "required_failures": summary.get("required_failures", []),
    }


def _format_attack_pack(report: dict[str, Any]) -> str:
    benchmark = report.get("latest_value_benchmark") or {}
    release = report.get("latest_release_gate") or {}
    lines = [
        "# Hive Mind Production-v0 Attack Pack",
        "",
        "## Objective",
        "",
        str(report.get("objective", "")),
        "",
        "## Stopping Condition",
        "",
        str(report.get("stopping_condition", "")),
        "",
        "## Latest Evidence",
        "",
        f"- Value benchmark: {benchmark.get('path')} verdict={benchmark.get('verdict')}",
        f"- Direct CLI wins trivial calls: {benchmark.get('direct_cli_for_trivial')}",
        f"- Hive wins audited multi-agent value: {benchmark.get('hive_for_audited_multi_agent')}",
        f"- Release gate: {release.get('path')} user_value_verdict={release.get('user_value_verdict')}",
        "",
        "## Required Reads",
        "",
    ]
    lines.extend(f"- `{item}`" for item in report.get("required_reads", []))
    lines.extend(
        [
            "",
            "## Validation Commands",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in report.get("validation_commands", []))
    lines.extend(
        [
            "",
            "## Attack Prompt",
            "",
            "```text",
            str(report.get("claude_attack_prompt", "")),
            "```",
            "",
            "## Attack Checklist",
            "",
            "- Find provider passthrough flags that bypass policy.",
            "- Find failed, skipped, timeout, blocked, or stopped paths without receipts.",
            "- Find ledger replay false positives or false negatives.",
            "- Corrupt run state and confirm the user gets a useful recovery path.",
            "- Compare direct CLI against Hive for trivial and audited multi-agent work.",
            "- Test Korean, Unicode, and long prompts.",
            "- Test MemoryOS absence or bridge degradation.",
            "- Report whether Hive adds ceremony without enough audit, policy, recovery, or coordination value.",
            "",
            "## Finding Format",
            "",
            "```text",
            "Severity: high|medium|low",
            "Surface:",
            "Reproduction:",
            "Expected:",
            "Actual:",
            "Recommended fix:",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def _latest_release_gate(root: Path) -> dict[str, Any]:
    release_root = root / ".hivemind" / "release"
    candidates = sorted(
        [
            path
            for path in release_root.glob("*")
            if path.is_dir() and (path / "test.log").exists() and (path / "user-value-benchmark.json").exists()
        ],
        reverse=True,
    )
    if not candidates:
        return {"status": "missing", "path": None}
    path = candidates[0]
    benchmark = _read_json(path / "user-value-benchmark.json")
    benchmark_summary = (benchmark.get("summary") if isinstance(benchmark, dict) else None) or {}
    return {
        "status": "present",
        "path": _rel(root, path),
        "has_user_value_benchmark": (path / "user-value-benchmark.json").exists(),
        "user_value_verdict": benchmark_summary.get("verdict"),
        "test_log": _rel(root, path / "test.log") if (path / "test.log").exists() else None,
    }


def _format_artifact_summary(label: str, artifact: Any) -> str:
    if not isinstance(artifact, dict) or artifact.get("status") == "missing":
        return f"{label}: missing"
    details = ", ".join(
        f"{key}={value}"
        for key, value in artifact.items()
        if key not in {"status", "path"} and value not in (None, [], {})
    )
    suffix = f" ({details})" if details else ""
    return f"{label}: {artifact.get('path')}{suffix}"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
