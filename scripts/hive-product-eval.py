#!/usr/bin/env python3
"""Run a product-level Hive Mind smoke evaluation.

This script is intentionally broader than unit tests. It checks whether the
installed CLI can run in a clean workspace, whether common tasks route to useful
provider artifacts, and where Hive Mind still falls short of production.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


TASK_MATRIX = [
    {
        "name": "implementation_en",
        "prompt": "Fix the TUI cursor bug and add a regression test",
        "expected_intent": "implementation",
        "required_actions": [("claude", "planner"), ("codex", "executor")],
    },
    {
        "name": "implementation_ko",
        "prompt": "한글 입력 버그 고쳐주고 테스트 추가",
        "expected_intent": "implementation",
        "required_actions": [("claude", "planner"), ("codex", "executor")],
    },
    {
        "name": "debugging_ko",
        "prompt": "왜 hive tui가 멈추는지 로그 보고 원인 찾아",
        "expected_intent": "debugging",
        "required_actions": [("claude", "planner"), ("local", "review")],
    },
    {
        "name": "review_ko",
        "prompt": "public alpha 전에 보안 리스크 검토",
        "expected_intent": "review",
        "required_actions": [("claude", "reviewer"), ("gemini", "reviewer")],
    },
    {
        "name": "memory_import",
        "prompt": "memoryOS export parser로 메모리 가져오기 계획",
        "expected_intent": "memory_import",
        "required_actions": [("local", "memory"), ("codex", "executor")],
    },
    {
        "name": "architecture",
        "prompt": "chair layer 구조 설계하고 provider 역할 분리",
        "expected_intent": "planning",
        "required_actions": [("claude", "planner"), ("gemini", "reviewer")],
    },
    {
        "name": "ambiguous",
        "prompt": "list",
        "expected_intent": "planning",
        "required_actions": [("claude", "planner")],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Hive Mind product evaluation")
    parser.add_argument("--repo", default=".", help="repository root")
    parser.add_argument("--out", default="runs/reports/hive-product-eval.json", help="JSON report path, or '-' for stdout only")
    parser.add_argument("--deep", action="store_true", help="also run slower local-LLM router smoke")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    report: dict[str, Any] = {
        "schema_version": 1,
        "generated_at_epoch": time.time(),
        "repo": repo.as_posix(),
        "checks": [],
        "summary": {},
    }

    with tempfile.TemporaryDirectory(prefix="hive_product_eval_") as tmp:
        tmp_path = Path(tmp)
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        wheelhouse = tmp_path / "wheelhouse"
        wheelhouse.mkdir()
        venv = tmp_path / "venv"
        wheel_source = tmp_path / "source"
        copy_eval_source(repo, wheel_source)

        add_check(report, "unit_tests", run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], repo, timeout=120))
        add_check(report, "wheel_build", run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", wheelhouse.as_posix()], wheel_source, timeout=120))
        wheels = sorted(wheelhouse.glob("*.whl"))
        if wheels:
            add_check(report, "venv_create", run([sys.executable, "-m", "venv", venv.as_posix()], repo, timeout=120))
            pip = venv / "bin" / "pip"
            hive = venv / "bin" / "hive"
            add_check(report, "wheel_install", run([pip.as_posix(), "install", wheels[-1].as_posix()], repo, timeout=120))
            add_check(report, "installed_hive_version", run([hive.as_posix(), "--version"], repo, timeout=20))
            add_check(report, "installed_hive_init", run([hive.as_posix(), "--root", workspace.as_posix(), "init", "--json"], repo, timeout=60, parse_json=True))
            add_check(report, "installed_hive_doctor", run([hive.as_posix(), "--root", workspace.as_posix(), "doctor", "all", "--json"], repo, timeout=60, parse_json=True))
            run_routing_matrix(report, hive.as_posix(), workspace)
            add_check(report, "provider_prepare_claude", run([hive.as_posix(), "--root", workspace.as_posix(), "invoke", "claude", "--role", "planner"], repo, timeout=60))
            add_check(report, "validate_current_run", run([hive.as_posix(), "--root", workspace.as_posix(), "check", "run"], repo, timeout=60))
            add_check(report, "next_action", run([hive.as_posix(), "--root", workspace.as_posix(), "next", "--json"], repo, timeout=60, parse_json=True))
            add_check(report, "auto_loop_dry_run", run([hive.as_posix(), "--root", workspace.as_posix(), "loop", "--json"], repo, timeout=60, parse_json=True))
            add_check(report, "auto_loop_execute_blocked_without_allow", run([hive.as_posix(), "--root", workspace.as_posix(), "loop", "--execute", "--json"], repo, timeout=60, parse_json=True))
            add_check(report, "flow_prepare", run([hive.as_posix(), "--root", workspace.as_posix(), "flow", "한글 입력 버그 고치고 테스트 추가", "--json"], repo, timeout=60, parse_json=True))
            if args.deep:
                add_check(report, "local_llm_router_smoke", run([hive.as_posix(), "--root", workspace.as_posix(), "ask", "간단히 상태를 보고 다음 액션 분해"], repo, timeout=90))
        else:
            add_check(report, "wheel_present", {"ok": False, "error": "no wheel was built"})

    summarize(report)
    output = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out == "-":
        print(output, end="")
    else:
        out_path = repo / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(out_path)
    return 0 if report["summary"].get("failed", 0) == 0 else 1


def copy_eval_source(repo: Path, destination: Path) -> None:
    ignored = {
        ".git",
        ".hivemind",
        ".mypy_cache",
        ".pytest_cache",
        ".runs",
        "__pycache__",
        "build",
        "dist",
        "runs",
        "hive_mind.egg-info",
    }

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in ignored or name.endswith(".egg-info")}

    shutil.copytree(repo, destination, ignore=ignore)


def run_routing_matrix(report: dict[str, Any], hive: str, workspace: Path) -> None:
    for item in TASK_MATRIX:
        result = run(
            [hive, "--root", workspace.as_posix(), "ask", item["prompt"], "--complexity", "fast", "--json"],
            workspace,
            timeout=60,
            parse_json=True,
            force_heuristic=True,
        )
        if result.get("ok"):
            plan = result.get("json")
            if isinstance(plan, dict):
                result["plan"] = {
                    "intent": plan.get("intent"),
                    "route_source": plan.get("route_source"),
                    "actions": plan.get("actions", []),
                }
                result["ok"] = route_matches(plan, item)
                if not result["ok"]:
                    result["error"] = "route did not match expected intent/actions"
            else:
                result["ok"] = False
                result["error"] = "routing plan JSON was not an object"
        add_check(report, f"route_{item['name']}", result)


def route_matches(plan: dict[str, Any], item: dict[str, Any]) -> bool:
    if plan.get("intent") != item["expected_intent"]:
        return False
    actions = {(str(action.get("provider")), str(action.get("role"))) for action in plan.get("actions", [])}
    return all(pair in actions for pair in item["required_actions"])


def run(cmd: list[str], cwd: Path, timeout: int, parse_json: bool = False, force_heuristic: bool = False) -> dict[str, Any]:
    started = time.time()
    env = os.environ.copy()
    if force_heuristic:
        env["HIVE_ROUTER_MODE"] = "heuristic"
    try:
        completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "cmd": cmd,
            "timeout": timeout,
            "duration_ms": round((time.time() - started) * 1000),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "error": "timeout",
        }
    result: dict[str, Any] = {
        "ok": completed.returncode == 0,
        "cmd": cmd,
        "returncode": completed.returncode,
        "duration_ms": round((time.time() - started) * 1000),
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }
    if parse_json and completed.stdout.strip():
        try:
            result["json"] = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            result["ok"] = False
            result["error"] = f"invalid json: {exc}"
    return result


def add_check(report: dict[str, Any], name: str, result: dict[str, Any]) -> None:
    report["checks"].append({"name": name, **result})


def summarize(report: dict[str, Any]) -> None:
    total = len(report["checks"])
    failed = [check for check in report["checks"] if not check.get("ok")]
    durations = [int(check.get("duration_ms", 0)) for check in report["checks"]]
    report["summary"] = {
        "total": total,
        "passed": total - len(failed),
        "failed": len(failed),
        "failed_checks": [check["name"] for check in failed],
        "duration_ms": sum(durations),
        "verdict": "pass" if not failed else "fail",
    }


if __name__ == "__main__":
    raise SystemExit(main())
