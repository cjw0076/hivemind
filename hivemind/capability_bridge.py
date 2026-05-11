"""CapabilityOS recommendation bridge helpers for Hive runs."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal, TypeAlias

from .utils import now_iso


CapabilityRecommendation: TypeAlias = dict[str, Any]
BridgeStatus: TypeAlias = Literal["unavailable", "ok", "failed"]


def recommend_for(task: str) -> CapabilityRecommendation | None:
    """Return the top CapabilityOS recommendation for a task, if available."""
    report = build_capabilityos_recommendation_report(Path.cwd(), None, {"user_request": task})
    recommendation = report.get("recommendation")
    return recommendation if isinstance(recommendation, dict) else None


def bridge_status() -> BridgeStatus:
    """Return the bridge availability status without running a recommendation."""
    if os.environ.get("HIVE_DISABLE_CAPABILITYOS") in {"1", "true", "yes"}:
        return "unavailable"
    source_root = _capabilityos_source_root(Path.cwd())
    cli = source_root / "capabilityos" / "cli.py"
    return "ok" if cli.exists() else "unavailable"


def build_capabilityos_recommendation_report(root: Path, paths: Any, state: dict[str, Any]) -> dict[str, Any]:
    """Call CapabilityOS recommend and return a run-local report.

    This module deliberately does not mutate run_state. The harness remains the
    authority for state updates and event emission.
    """
    capabilityos_source_root = _capabilityos_source_root(root)
    capabilityos_cli = capabilityos_source_root / "capabilityos" / "cli.py"
    catalog = capabilityos_source_root / "tests" / "fixtures" / "capabilities.json"
    task = str(state.get("user_request") or state.get("task") or "")
    command = [
        sys.executable,
        "-m",
        "capabilityos.cli",
    ]
    if catalog.exists():
        command.extend(["--catalog", catalog.as_posix()])
    command.extend(["recommend", "--task", task, "--limit", "5", "--json"])
    artifact: dict[str, Any] = {
        "schema_version": 1,
        "generated_at": now_iso(),
        "run_id": getattr(paths, "run_id", None),
        "phase": "route",
        "status": "unavailable",
        "bridge_status": "unavailable",
        "capabilityos_source_root": capabilityos_source_root.as_posix(),
        "command": command,
        "task": task,
        "recommendation": None,
        "recommendations": [],
        "total_candidates": 0,
        "raw_refs": ["docs/contracts/ASC-0005-hive-capability-bridge.md"],
    }
    if not capabilityos_cli.exists():
        artifact["reason"] = "CapabilityOS CLI source not found next to Hive Mind workspace."
        return artifact
    if os.environ.get("HIVE_DISABLE_CAPABILITYOS") in {"1", "true", "yes"}:
        artifact["reason"] = "CapabilityOS bridge disabled by HIVE_DISABLE_CAPABILITYOS."
        return artifact
    try:
        result = subprocess.run(command, cwd=capabilityos_source_root, text=True, capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        artifact.update({"status": "failed", "bridge_status": "failed", "reason": str(exc)})
        return artifact
    artifact.update(
        {
            "returncode": result.returncode,
            "stderr": result.stderr.strip()[-4000:],
        }
    )
    if result.returncode != 0:
        artifact.update({"status": "failed", "bridge_status": "failed", "reason": "capabilityos recommend failed"})
        return artifact
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        artifact.update(
            {
                "status": "failed",
                "bridge_status": "failed",
                "reason": "capabilityos recommend did not emit JSON",
                "stdout_excerpt": result.stdout.strip()[-4000:],
            }
        )
        return artifact
    recommendations = [item for item in payload.get("recommendations") or [] if isinstance(item, dict)]
    recommendation = _summarize_recommendation(recommendations[0]) if recommendations else None
    if recommendation and recommendation.get("executes_tools") is True:
        artifact.update(
            {
                "status": "failed",
                "bridge_status": "failed",
                "reason": "CapabilityOS returned an execution-enabled recommendation; Hive refused it.",
                "payload": payload,
            }
        )
        return artifact
    status = "ok" if recommendation else "empty"
    artifact.update(
        {
            "status": status,
            "bridge_status": "ok",
            "contract": payload.get("contract"),
            "recommendation": recommendation,
            "recommendations": [_summarize_recommendation(item) for item in recommendations],
            "total_candidates": payload.get("total_candidates", 0),
            "payload": payload,
        }
    )
    return artifact


def _capabilityos_source_root(root: Path) -> Path:
    configured = os.environ.get("HIVE_CAPABILITYOS_SOURCE_ROOT")
    if configured:
        return Path(configured).resolve()
    return (root.parent / "CapabilityOS").resolve()


def _summarize_recommendation(item: dict[str, Any]) -> CapabilityRecommendation:
    return {
        "recommended_capability": str(item.get("id") or ""),
        "capability_name": item.get("name"),
        "kind": item.get("kind"),
        "score": item.get("score", 0),
        "reason_codes": item.get("reason_codes") or [],
        "fallback_ids": item.get("fallback_ids") or [],
        "risk_notes": item.get("risk_notes") or [],
        "evidence_refs": item.get("evidence_refs") or [],
        "requires_network": bool(item.get("requires_network")),
        "executes_tools": bool(item.get("executes_tools")),
        "privacy": item.get("privacy"),
    }
