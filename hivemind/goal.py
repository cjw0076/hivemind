"""Goal sprint read model for Hive Mind."""

from __future__ import annotations

import json
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
    return "\n".join(lines)


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


def _latest_release_gate(root: Path) -> dict[str, Any]:
    release_root = root / ".hivemind" / "release"
    candidates = sorted([path for path in release_root.glob("*") if path.is_dir()], reverse=True)
    if not candidates:
        return {"status": "missing", "path": None}
    path = candidates[0]
    benchmark = _read_json(path / "user-value-benchmark.json")
    benchmark_summary = benchmark.get("summary") if isinstance(benchmark, dict) else {}
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

