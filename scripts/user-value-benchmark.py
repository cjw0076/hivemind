#!/usr/bin/env python3
"""Benchmark whether Hive Mind adds user-visible value over direct provider CLIs.

This is not a speed benchmark. Direct provider CLIs should win trivial one-shot
latency. Hive wins only if it preserves native access while adding receipts,
policy gates, ledger/proof, inspectability, and supervisor recovery.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Hive Mind user-value benchmark")
    parser.add_argument("--repo", default=".", help="Hive Mind repository root")
    parser.add_argument(
        "--out-dir",
        default=".hivemind/benchmarks",
        help="directory for the JSON benchmark report",
    )
    parser.add_argument("--json", action="store_true", help="print the full report JSON")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    report: dict[str, Any] = {
        "schema_version": 1,
        "kind": "hive_user_value_benchmark",
        "generated_at": stamp,
        "repo": repo.as_posix(),
        "checks": [],
        "summary": {},
    }

    with tempfile.TemporaryDirectory(prefix="hive_user_value_") as tmp:
        workspace = Path(tmp) / "workspace"
        workspace.mkdir(parents=True, exist_ok=True)
        hive = [sys.executable, "-m", "hivemind.hive", "--root", workspace.as_posix()]

        for provider in ("claude", "codex", "gemini"):
            direct = provider_help(provider)
            add_check(report, f"direct_{provider}_help", direct, optional=True)

        run_result = run(hive + ["run", "한글 prompt receipt benchmark", "--json"], repo, parse_json=True)
        add_check(report, "hive_run_korean_prompt", run_result)
        run_id = ""
        if isinstance(run_result.get("json"), dict):
            run_id = str(run_result["json"].get("run_id") or "")

        add_check(report, "hive_status", run(hive + ["status", "--json"], repo, parse_json=True))
        add_check(report, "hive_next", run(hive + ["next", "--json"], repo, parse_json=True))
        add_check(report, "hive_inspect", run(hive + ["inspect", run_id, "--json"], repo, parse_json=True) if run_id else missing("run_id"))
        add_check(report, "hive_ledger_replay", run(hive + ["ledger", "replay", "--run-id", run_id, "--json"], repo, parse_json=True) if run_id else missing("run_id"))
        add_check(report, "hive_diff", run(hive + ["diff", "--json"], repo, parse_json=True))

        provider_dry = run(
            hive + ["provider", "claude", "--dry-run", "--run-id", run_id, "--", "--help"],
            repo,
            parse_json=False,
        ) if run_id else missing("run_id")
        add_check(report, "hive_provider_claude_dry_run", provider_dry)

        danger_block = run(
            hive + [
                "provider",
                "claude",
                "--execute",
                "--run-id",
                run_id,
                "--",
                "--dangerously-skip-permissions",
                "-p",
                "blocked benchmark",
            ],
            repo,
            parse_json=False,
            expect_nonzero=True,
        ) if run_id else missing("run_id")
        danger_block["expected_block"] = danger_block.get("returncode") not in (None, 0)
        if danger_block.get("returncode") == 0:
            danger_block["ok"] = False
            danger_block["error"] = "dangerous provider bypass was not blocked"
        add_check(report, "hive_provider_danger_block", danger_block)

        if run_id:
            add_check(report, "hive_stop_receipt", run(hive + ["run", "stop", "--run-id", run_id, "--json"], repo, parse_json=True))

        long_prompt = "긴 Unicode 입력 " + ("가나다라마바사 " * 120)
        add_check(report, "hive_long_unicode_prompt", run(hive + ["run", long_prompt, "--json"], repo, parse_json=True))
        add_check(report, "memoryos_disabled_degrade", run_memoryos_disabled_degrade(hive, repo, workspace))

        supervised_id = create_supervised_run(hive, repo, report)
        if supervised_id:
            add_check(report, "supervised_inspect", run(hive + ["inspect", supervised_id, "--json"], repo, parse_json=True))
            add_check(report, "supervised_stop_receipt", run(hive + ["run", "stop", "--run-id", supervised_id, "--json"], repo, parse_json=True))

        add_value_summary(report)

    out_dir = repo / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"user-value-{stamp}.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        summary = report["summary"]
        print(f"report: {out_path}")
        print(f"verdict: {summary.get('verdict')}")
        print(f"direct_cli_for_trivial: {summary.get('direct_cli_for_trivial')}")
        print(f"hive_for_audited_multi_agent: {summary.get('hive_for_audited_multi_agent')}")
        print(f"required_failures: {summary.get('required_failures')}")
    return 0 if report["summary"].get("verdict") == "pass" else 1


def provider_help(provider: str) -> dict[str, Any]:
    binary = shutil.which(provider)
    if not binary:
        return {"ok": True, "optional": True, "available": False, "reason": "provider CLI not installed"}
    if provider == "codex":
        cmd = [binary, "--help"]
    else:
        cmd = [binary, "--help"]
    result = run(cmd, Path.cwd(), timeout=20)
    result["available"] = True
    return result


def create_supervised_run(hive: list[str], repo: Path, report: dict[str, Any]) -> str:
    run_plan = run(hive + ["run", "supervised pingpong benchmark", "--json"], repo, parse_json=True)
    add_check(report, "supervised_run_create", run_plan)
    run_id = ""
    if isinstance(run_plan.get("json"), dict):
        run_id = str(run_plan["json"].get("run_id") or "")
    if not run_id:
        return ""
    add_check(report, "supervised_plan_dag", run(hive + ["plan", "dag", "--intent", "planning", "--run-id", run_id, "--json"], repo, parse_json=True))
    add_check(report, "supervised_start_pingpong", run(hive + ["run", "start", "--run-id", run_id, "--scheduler", "pingpong", "--json"], repo, parse_json=True))
    return run_id


def run_memoryos_disabled_degrade(hive: list[str], repo: Path, workspace: Path) -> dict[str, Any]:
    result = run(
        hive + ["orchestrate", "MemoryOS disabled benchmark", "--json"],
        repo,
        parse_json=True,
        extra_env={"HIVE_DISABLE_MEMORYOS": "1"},
    )
    run_id = ""
    if isinstance(result.get("json"), dict):
        run_id = str(result["json"].get("run_id") or "")
    artifact_path = workspace / ".runs" / run_id / "artifacts" / "memory_context.json"
    result["memory_context_path"] = artifact_path.as_posix()
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["ok"] = False
        result["error"] = f"memory_context artifact missing or invalid: {exc}"
        return result
    result["memory_context_status"] = artifact.get("status")
    result["memory_context_reason"] = artifact.get("reason")
    reason = str(artifact.get("reason", "")).lower()
    if artifact.get("status") != "unavailable" or ("disabled" not in reason and "not found" not in reason):
        result["ok"] = False
        result["error"] = "MemoryOS disabled path did not degrade to unavailable"
    return result


def run(
    cmd: list[str],
    cwd: Path,
    timeout: int = 60,
    parse_json: bool = False,
    expect_nonzero: bool = False,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    env = os.environ.copy()
    env.setdefault("HIVE_ROUTER_MODE", "heuristic")
    if extra_env:
        env.update(extra_env)
    try:
        completed = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "cmd": cmd,
            "duration_ms": round((time.perf_counter() - start) * 1000),
            "timeout": timeout,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "error": "timeout",
        }
    ok = completed.returncode != 0 if expect_nonzero else completed.returncode == 0
    result: dict[str, Any] = {
        "ok": ok,
        "cmd": cmd,
        "returncode": completed.returncode,
        "duration_ms": round((time.perf_counter() - start) * 1000),
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }
    if parse_json and completed.stdout.strip():
        try:
            result["json"] = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            result["ok"] = False
            result["error"] = f"invalid JSON: {exc}"
    return result


def missing(reason: str) -> dict[str, Any]:
    return {"ok": False, "error": f"missing {reason}"}


def add_check(report: dict[str, Any], name: str, result: dict[str, Any], optional: bool = False) -> None:
    check = {"name": name, **result}
    if optional:
        check["optional"] = True
    report["checks"].append(check)


def add_value_summary(report: dict[str, Any]) -> None:
    checks = report["checks"]
    required_failures = [
        check["name"]
        for check in checks
        if not check.get("optional") and not check.get("ok")
    ]
    by_name = {check["name"]: check for check in checks}

    direct_times = [
        check.get("duration_ms")
        for check in checks
        if check["name"].startswith("direct_") and check.get("available") and check.get("ok")
    ]
    hive_dry_time = by_name.get("hive_provider_claude_dry_run", {}).get("duration_ms")
    direct_cli_for_trivial = bool(direct_times and hive_dry_time and min(direct_times) < hive_dry_time)

    audit_signals = {
        "run_created": by_name.get("hive_run_korean_prompt", {}).get("ok") is True,
        "inspectable": by_name.get("hive_inspect", {}).get("ok") is True,
        "ledger_replay": by_name.get("hive_ledger_replay", {}).get("ok") is True,
        "next_action": by_name.get("hive_next", {}).get("ok") is True,
        "danger_blocked": by_name.get("hive_provider_danger_block", {}).get("expected_block") is True,
        "stop_receipt": by_name.get("hive_stop_receipt", {}).get("ok") is True,
        "supervised_run": by_name.get("supervised_start_pingpong", {}).get("ok") is True,
        "memoryos_degrade": by_name.get("memoryos_disabled_degrade", {}).get("ok") is True,
    }
    hive_for_audited_multi_agent = all(audit_signals.values())

    report["summary"] = {
        "verdict": "pass" if not required_failures and hive_for_audited_multi_agent else "fail",
        "required_failures": required_failures,
        "direct_cli_for_trivial": direct_cli_for_trivial,
        "hive_for_audited_multi_agent": hive_for_audited_multi_agent,
        "audit_signals": audit_signals,
        "interpretation": (
            "Use direct provider CLI for trivial one-shot calls. Use Hive Mind when the work "
            "needs auditability, policy, receipts, ledger/proof, supervisor control, and "
            "multi-agent review."
        ),
    }


if __name__ == "__main__":
    raise SystemExit(main())
