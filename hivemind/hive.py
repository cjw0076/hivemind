"""`hive` command: Hive Mind CLI and TUI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .harness import (
    build_memory_draft,
    build_summary,
    build_verification,
    create_run,
    commit_summary,
    detect_agents,
    doctor_report,
    doctor_scope_report,
    agent_roles_report,
    build_context_pack_for_role,
    explain_agent_role,
    explain_policy,
    format_agents_status,
    format_agent_explain,
    format_agent_roles,
    format_doctor,
    format_doctor_scope,
    format_memory_drafts,
    format_local_runtime,
    format_local_model_profile,
    format_local_benchmark,
    format_llm_checker_report,
    format_policy_explain,
    format_policy_report,
    format_run_audit,
    format_workspace_layout,
    local_routes_report,
    local_benchmark_report,
    local_model_profile,
    llm_checker_report,
    get_current,
    init_harness,
    init_onboarding,
    invoke_external_agent,
    invoke_local,
    list_runs,
    local_runtime_report,
    load_run,
    memory_drafts_report,
    open_run_folder,
    read_transcript,
    read_events,
    read_hive_activity,
    format_onboarding,
    format_run_board,
    format_settings,
    format_settings_shell,
    format_orchestration_report,
    settings_report,
    ask_router,
    orchestrate_prompt,
    checks_report,
    agent_icon,
    format_routing_plan,
    format_checks_report,
    format_checks_run,
    format_git_diff_report,
    format_hive_activity,
    load_routing_plan,
    git_diff_report,
    review_diff,
    run_checks,
    run_board,
    run_audit_report,
    policy_report,
    workspace_layout_report,
)
from .tui import TUI_VIEWS, print_status, run_tui


COMMANDS = {
    "init",
    "doctor",
    "agents",
    "settings",
    "policy",
    "local",
    "run",
    "ask",
    "orchestrate",
    "status",
    "board",
    "events",
    "transcript",
    "artifacts",
    "society",
    "tui",
    "plan",
    "runs",
    "open",
    "context",
    "handoff",
    "invoke",
    "verify",
    "summarize",
    "memory",
    "completion",
    "check",
    "shell",
    "chat",
    "diff",
    "review-diff",
    "commit-summary",
    "audit",
    "workspace",
    "log",
    "prompt",
    "next",
    "hive",
}


def normalize_argv(argv: list[str]) -> list[str]:
    """Allow provider-style prompt entry: `hive "build this"` -> `hive orchestrate "build this"`."""
    if not argv:
        return ["chat"] if sys.stdin.isatty() and sys.stdout.isatty() else ["--help"]
    if argv[0] in {"-h", "--help", "--version"}:
        return argv
    if argv[0] == "--root":
        if len(argv) >= 3 and argv[2] not in COMMANDS and not argv[2].startswith("-"):
            return [argv[0], argv[1], "orchestrate", " ".join(argv[2:])]
        return argv
    if argv[0].startswith("--root="):
        if len(argv) >= 2 and argv[1] not in COMMANDS and not argv[1].startswith("-"):
            return [argv[0], "orchestrate", " ".join(argv[1:])]
        return argv
    if argv[0] not in COMMANDS and not argv[0].startswith("-"):
        return ["orchestrate", " ".join(argv)]
    return argv


def resolve_root(root_arg: str) -> Path:
    """Resolve Hive Mind root, including the umbrella `myworld/` workspace layout."""
    root = Path(root_arg).resolve()
    if (root / "pyproject.toml").exists() and (root / "hivemind").is_dir():
        return root
    child = root / "hivemind"
    if (child / "pyproject.toml").exists() and (child / "hivemind").is_dir():
        return child.resolve()
    return root


def main(argv: list[str] | None = None) -> None:
    argv = normalize_argv(list(sys.argv[1:] if argv is None else argv))
    parser = argparse.ArgumentParser(prog="hive", description="Hive Mind control plane for provider CLI harnessing")
    parser.add_argument("--root", default=".", help="workspace root")
    parser.add_argument("--version", action="version", version="hive 0.1.0")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_cmd = sub.add_parser("init", help="initialize Hive Mind onboarding state")
    init_cmd.add_argument("--json", action="store_true")
    init_cmd.add_argument("--no-tui", action="store_true", help="non-interactive init; accepted for installer compatibility")
    init_cmd.add_argument("--skills", choices=["yes", "no"], default="no", help="prepare skill config placeholders")
    init_cmd.add_argument("--mcp", choices=["yes", "no"], default="no", help="prepare MCP config placeholders")
    doctor_cmd = sub.add_parser("doctor", help="check Hive Mind runtime health")
    doctor_cmd.add_argument("scope", nargs="?", choices=["hardware", "providers", "models", "permissions", "all"], help="doctor scope")
    doctor_cmd.add_argument("--json", action="store_true")

    agents_cmd = sub.add_parser("agents", help="provider/agent registry helpers")
    agents_sub = agents_cmd.add_subparsers(dest="agents_cmd", required=True)
    detect_cmd = agents_sub.add_parser("detect", help="detect installed provider CLIs and runtime config")
    detect_cmd.add_argument("--json", action="store_true")
    agents_status_cmd = agents_sub.add_parser("status", help="show provider registry as an agent status board")
    agents_status_cmd.add_argument("--json", action="store_true")
    agents_view_cmd = agents_sub.add_parser("view", help="open the agents TUI view")
    agents_view_cmd.add_argument("--run-id")
    agents_roles_cmd = agents_sub.add_parser("roles", help="show role registry")
    agents_roles_cmd.add_argument("--json", action="store_true")
    agents_policy_cmd = agents_sub.add_parser("policy", help="show role policy status")
    agents_policy_cmd.add_argument("--json", action="store_true")
    agents_explain_cmd = agents_sub.add_parser("explain", help="explain an agent role")
    agents_explain_cmd.add_argument("role")
    agents_explain_cmd.add_argument("--json", action="store_true")

    policy_cmd = sub.add_parser("policy", help="policy gate helpers")
    policy_sub = policy_cmd.add_subparsers(dest="policy_cmd", required=True)
    policy_check_cmd = policy_sub.add_parser("check", help="validate or create project policy")
    policy_check_cmd.add_argument("--write", action="store_true", help="write default policy if missing")
    policy_check_cmd.add_argument("--json", action="store_true")
    policy_explain_cmd = policy_sub.add_parser("explain", help="explain policy for a role")
    policy_explain_cmd.add_argument("role")
    policy_explain_cmd.add_argument("--json", action="store_true")

    settings_cmd = sub.add_parser("settings", help="detect and persist production CLI settings")
    settings_sub = settings_cmd.add_subparsers(dest="settings_cmd", required=True)
    settings_detect_cmd = settings_sub.add_parser("detect", help="write provider/runtime settings profile")
    settings_detect_cmd.add_argument("--json", action="store_true")
    settings_shell_cmd = settings_sub.add_parser("shell", help="print shell exports for detected providers")
    settings_shell_cmd.add_argument("--json", action="store_true")

    local_cmd = sub.add_parser("local", help="local runtime helpers")
    local_sub = local_cmd.add_subparsers(dest="local_cmd", required=True)
    local_status_cmd = local_sub.add_parser("status", help="show local runtime/model status")
    local_status_cmd.add_argument("--json", action="store_true")
    local_setup_cmd = local_sub.add_parser("setup", help="write local runtime config and show recommended setup")
    local_setup_cmd.add_argument("--auto", action="store_true", help="write local model profile and role assignments")
    local_setup_cmd.add_argument("--json", action="store_true")
    local_routes_cmd = local_sub.add_parser("routes", help="show local worker route table")
    local_routes_cmd.add_argument("--json", action="store_true")
    local_benchmark_cmd = local_sub.add_parser("benchmark", help="run local model JSON-validity and latency smoke benchmarks")
    local_benchmark_cmd.add_argument("--model", action="append", dest="models", help="model to benchmark; repeatable")
    local_benchmark_cmd.add_argument("--limit", type=int, default=4)
    local_benchmark_cmd.add_argument("--timeout", type=int, default=90)
    local_benchmark_cmd.add_argument("--json", action="store_true")
    local_checker_cmd = local_sub.add_parser("checker", help="optional llm-checker adapter report")
    local_checker_cmd.add_argument("--category", default="coding")
    local_checker_cmd.add_argument("--use-npx", action="store_true", help="allow npx --yes llm-checker when not installed")
    local_checker_cmd.add_argument("--execute", action="store_true", help="run llm-checker commands instead of only writing the adapter plan")
    local_checker_cmd.add_argument("--json", action="store_true")

    run_cmd = sub.add_parser("run", help="create a structured run folder")
    run_cmd.add_argument("task", help="user task/request")
    run_cmd.add_argument("--project", default="Hive Mind")
    run_cmd.add_argument("--type", default="implementation", dest="task_type")
    run_cmd.add_argument("-q", "--quiet", action="store_true", help="only print the run id/path")
    run_cmd.add_argument("--json", action="store_true")

    ask_cmd = sub.add_parser("ask", help="route one prompt through local intent decomposition")
    ask_cmd.add_argument("prompt", help="user prompt/task")
    ask_cmd.add_argument("--run-id")
    ask_cmd.add_argument("--complexity", choices=["fast", "default", "strong"], default="default")
    orchestrate_cmd = sub.add_parser("orchestrate", help="route a prompt into a multi-agent society plan")
    orchestrate_cmd.add_argument("prompt", help="user prompt/task")
    orchestrate_cmd.add_argument("--run-id")
    orchestrate_cmd.add_argument("--complexity", choices=["fast", "default", "strong"], default="default")
    orchestrate_cmd.add_argument("--execute", action="store_true", help="execute supported non-Codex providers instead of only preparing artifacts")
    orchestrate_cmd.add_argument("--json", action="store_true")

    status_cmd = sub.add_parser("status", help="show current run status")
    status_cmd.add_argument("--run-id")
    status_cmd.add_argument("--json", action="store_true")

    board_cmd = sub.add_parser("board", help="open the board TUI view")
    board_cmd.add_argument("--run-id")
    board_cmd.add_argument("--observer", action="store_true", help="open read-only observer mode")

    events_cmd = sub.add_parser("events", help="show run events or open the events TUI view")
    events_cmd.add_argument("--run-id")
    events_cmd.add_argument("--tail", type=int, default=60)
    events_cmd.add_argument("--follow", action="store_true", help="open the live events TUI view")
    events_cmd.add_argument("--json", action="store_true")

    transcript_cmd = sub.add_parser("transcript", help="show transcript or open transcript TUI view")
    transcript_cmd.add_argument("--run-id")
    transcript_cmd.add_argument("--tail", type=int, default=120)
    transcript_cmd.add_argument("--tui", action="store_true")

    artifacts_cmd = sub.add_parser("artifacts", help="open the artifacts TUI view")
    artifacts_cmd.add_argument("--run-id")

    next_cmd = sub.add_parser("next", help="show next recommended command")
    next_cmd.add_argument("--run-id")
    next_cmd.add_argument("--json", action="store_true")

    tui_cmd = sub.add_parser("tui", help="open the run status TUI")
    tui_cmd.add_argument("--run-id")
    tui_cmd.add_argument("--view", choices=sorted(TUI_VIEWS), default="board")
    tui_cmd.add_argument("--observer", action="store_true", help="read-only TUI session")

    plan_cmd = sub.add_parser("plan", help="show current routing plan")
    plan_cmd.add_argument("--run-id")
    plan_cmd.add_argument("--json", action="store_true")

    sub.add_parser("runs", help="list recent runs")

    open_cmd = sub.add_parser("open", help="print/open current run folder")
    open_cmd.add_argument("target", nargs="?", default="current")

    context_cmd = sub.add_parser("context", help="print current context pack path or build agent-specific context")
    context_cmd.add_argument("context_cmd", nargs="?", choices=["build"])
    context_cmd.add_argument("--run-id")
    context_cmd.add_argument("--for", dest="for_role", help="agent role, for example claude.planner or codex.executor")

    handoff_cmd = sub.add_parser("handoff", help="print current handoff path")
    handoff_cmd.add_argument("--run-id")

    invoke_cmd = sub.add_parser("invoke", help="invoke or prepare an agent artifact")
    invoke_cmd.add_argument("agent", choices=["local", "claude", "codex", "gemini"])
    invoke_cmd.add_argument("--role", required=True)
    invoke_cmd.add_argument("--run-id")
    invoke_cmd.add_argument("--complexity", choices=["fast", "default", "strong"], default="default")
    invoke_cmd.add_argument("--dry-run", action="store_true", help="prepare prompt/command/result artifacts without executing")
    invoke_cmd.add_argument("--execute", action="store_true", help="execute the external agent when supported")

    verify_cmd = sub.add_parser("verify", help="create a verification report")
    verify_cmd.add_argument("--run-id")

    summarize_cmd = sub.add_parser("summarize", help="update final_report.md")
    summarize_cmd.add_argument("--run-id")

    memory_cmd = sub.add_parser("memory", help="memory draft helpers")
    memory_sub = memory_cmd.add_subparsers(dest="memory_cmd", required=True)
    draft_cmd = memory_sub.add_parser("draft", help="create memory_drafts.json")
    draft_cmd.add_argument("--run-id")
    memory_list_cmd = memory_sub.add_parser("list", help="list memory drafts for the current run")
    memory_list_cmd.add_argument("--run-id")
    memory_list_cmd.add_argument("--json", action="store_true")
    memory_view_cmd = memory_sub.add_parser("view", help="open the memory draft TUI view")
    memory_view_cmd.add_argument("--run-id")

    completion_cmd = sub.add_parser("completion", help="print shell completion script")
    completion_cmd.add_argument("shell", choices=["bash", "zsh", "fish"])

    check_cmd = sub.add_parser("check", help="list or run markdown agent checks")
    check_sub = check_cmd.add_subparsers(dest="check_cmd", required=True)
    check_list_cmd = check_sub.add_parser("list", help="list configured checks")
    check_list_cmd.add_argument("--json", action="store_true")
    check_run_cmd = check_sub.add_parser("run", help="run checks against current run")
    check_run_cmd.add_argument("--run-id")
    check_run_cmd.add_argument("--json", action="store_true")

    sub.add_parser("shell", help="open a thin slash-command shell")
    sub.add_parser("chat", help="open a conversational Hive Mind operator shell")

    diff_cmd = sub.add_parser("diff", help="write/show git diff report for current run")
    diff_cmd.add_argument("--run-id")
    diff_cmd.add_argument("--json", action="store_true")
    diff_cmd.add_argument("--tui", action="store_true")
    review_diff_cmd = sub.add_parser("review-diff", help="capture git diff and run local review")
    review_diff_cmd.add_argument("--run-id")
    commit_summary_cmd = sub.add_parser("commit-summary", help="write proposed commit summary without committing")
    commit_summary_cmd.add_argument("--run-id")
    log_cmd = sub.add_parser("log", help="show current run transcript")
    log_cmd.add_argument("--run-id")
    log_cmd.add_argument("--tail", type=int, default=80)
    prompt_cmd = sub.add_parser("prompt", help="read a prompt from stdin or multiline input and route it")
    prompt_cmd.add_argument("--complexity", choices=["fast", "default", "strong"], default="default")
    hive_cmd = sub.add_parser("hive", help="Hive Mind activity and orchestration helpers")
    hive_sub = hive_cmd.add_subparsers(dest="hive_cmd", required=True)
    hive_activity_cmd = hive_sub.add_parser("activity", help="show human-readable hive activity feed")
    hive_activity_cmd.add_argument("--run-id")
    hive_activity_cmd.add_argument("--tail", type=int, default=30)
    society_cmd = sub.add_parser("society", help="open the society TUI view")
    society_cmd.add_argument("--run-id")

    audit_cmd = sub.add_parser("audit", help="audit current run artifacts, provider results, and policy")
    audit_cmd.add_argument("--run-id")
    audit_cmd.add_argument("--json", action="store_true")

    workspace_cmd = sub.add_parser("workspace", help="print multi-session Hive Console layout")
    workspace_cmd.add_argument("--layout", choices=["dev", "dual"], default="dev")
    workspace_cmd.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    root = resolve_root(args.root)

    if args.cmd == "init":
        report = init_onboarding(root)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_onboarding(report))
        return
    if args.cmd == "doctor":
        if args.scope:
            report = doctor_scope_report(root, args.scope)
            formatter = format_doctor_scope
        else:
            report = doctor_report(root)
            formatter = format_doctor
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(formatter(report))
        return
    if args.cmd == "agents" and args.agents_cmd == "detect":
        result = detect_agents(root, write=True)
        if args.json:
            import json

            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            for name, item in result["providers"].items():
                detail = item.get("version") or item.get("path") or item.get("reason", "")
                print(f"{name}: {item.get('status')} {detail}")
            print(root / ".runs" / "provider_capabilities.json")
        return
    if args.cmd == "agents" and args.agents_cmd == "status":
        result = detect_agents(root, write=True)
        if args.json:
            import json

            print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_agents_status(result))
        return
    if args.cmd == "agents" and args.agents_cmd == "view":
        run_tui(root, run_id=args.run_id, view="agents", control=False)
        return
    if args.cmd == "agents" and args.agents_cmd == "roles":
        report = agent_roles_report()
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_agent_roles(report))
        return
    if args.cmd == "agents" and args.agents_cmd == "policy":
        report = policy_report(root, write=False)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_policy_report(report))
        return
    if args.cmd == "agents" and args.agents_cmd == "explain":
        report = explain_agent_role(root, args.role)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_agent_explain(report))
        return
    if args.cmd == "policy" and args.policy_cmd == "check":
        report = policy_report(root, write=args.write)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_policy_report(report))
        return
    if args.cmd == "policy" and args.policy_cmd == "explain":
        report = explain_policy(root, args.role)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_policy_explain(report))
        return
    if args.cmd == "settings":
        report = settings_report(root, write=True)
        if args.settings_cmd == "shell":
            if args.json:
                import json

                print(json.dumps(report.get("shell_exports", {}), ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(format_settings_shell(report))
            return
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_settings(report))
        return
    if args.cmd == "local":
        if args.local_cmd == "routes":
            report = local_routes_report()
            if args.json:
                import json

                print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                for name, route in report["routes"].items():
                    models = route["models"]
                print(f"{name}: fast={models['fast']} default={models['default']} strong={models['strong']}")
            return
        if args.local_cmd == "checker":
            report = llm_checker_report(root, category=args.category, use_npx=args.use_npx, execute=args.execute, write=True)
            if args.json:
                import json

                print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(format_llm_checker_report(report))
                print("")
                print(f"Wrote {root / '.hivemind' / 'llm_checker_report.json'}")
            return
        if args.local_cmd == "benchmark":
            report = local_benchmark_report(root, models=args.models, limit=args.limit, timeout=args.timeout, write=True)
            if args.json:
                import json

                print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(format_local_benchmark(report))
                print("")
                print(f"Wrote {root / '.hivemind' / 'local_benchmark.json'}")
            return
        if args.local_cmd == "setup" and args.auto:
            report = local_model_profile(root, write=True)
            if args.json:
                import json

                print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(format_local_model_profile(report))
                print("")
                print(f"Wrote {root / '.hivemind' / 'local_model_profile.json'}")
            return
        report = local_runtime_report(root, write=args.local_cmd == "setup")
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_local_runtime(report))
            if args.local_cmd == "setup":
                print("")
                print(f"Wrote {root / '.hivemind' / 'local_runtime.json'}")
                print("To start the local server:")
                print("  scripts/start-ollama-local.sh")
        return
    if args.cmd == "run":
        paths = create_run(root, args.task, project=args.project, task_type=args.task_type)
        if args.json:
            import json

            indent = None if args.quiet else 2
            print(json.dumps({"run_id": paths.run_id, "run_dir": paths.run_dir.as_posix()}, ensure_ascii=False, indent=indent))
        elif args.quiet:
            print(paths.run_id)
        else:
            print(paths.run_dir)
        return
    if args.cmd == "ask":
        print(ask_router(root, args.prompt, run_id=args.run_id, complexity=args.complexity))
        return
    if args.cmd == "orchestrate":
        report = orchestrate_prompt(root, args.prompt, run_id=args.run_id, complexity=args.complexity, execute=args.execute)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_orchestration_report(report))
        return
    if args.cmd == "status":
        if args.json:
            print_status(root, run_id=args.run_id, json_output=True)
        else:
            print(format_run_board(run_board(root, args.run_id)))
        return
    if args.cmd == "board":
        run_tui(root, run_id=args.run_id, view="board", control=not args.observer)
        return
    if args.cmd == "events":
        if args.follow:
            run_tui(root, run_id=args.run_id, view="events", control=False)
            return
        paths, _ = load_run(root, args.run_id)
        events = read_hive_activity(paths, limit=args.tail) or read_events(paths, limit=args.tail)
        if args.json:
            import json

            print(json.dumps(events, ensure_ascii=False, indent=2))
        else:
            for event in events:
                if "summary" in event:
                    print(f"{event.get('ts')} {event.get('actor')} {event.get('action')} {event.get('summary')}")
                else:
                    artifact = f" {event.get('artifact')}" if event.get("artifact") else ""
                    print(f"{event.get('ts')} {event.get('type')}{artifact}")
        return
    if args.cmd == "transcript":
        if args.tui:
            run_tui(root, run_id=args.run_id, view="transcript", control=False)
        else:
            print(read_transcript(root, args.run_id, tail=args.tail), end="")
        return
    if args.cmd == "artifacts":
        run_tui(root, run_id=args.run_id, view="artifacts", control=False)
        return
    if args.cmd == "next":
        board = run_board(root, args.run_id)
        if args.json:
            import json

            print(json.dumps(board.get("next", {}), ensure_ascii=False, indent=2, sort_keys=True))
        else:
            next_action = board.get("next", {})
            print("Next recommended action:")
            print(f"  {next_action.get('command')}")
            print("")
            print("Reason:")
            print(f"  {next_action.get('reason')}")
        return
    if args.cmd == "tui":
        run_tui(root, run_id=args.run_id, view=args.view, control=not args.observer)
        return
    if args.cmd == "plan":
        plan = load_routing_plan(root, args.run_id)
        if args.json:
            import json

            print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_routing_plan(plan))
        return
    if args.cmd == "runs":
        for run in list_runs(root)[:20]:
            marker = "*" if run.get("run_id") == get_current(root) else " "
            print(f"{marker} {run.get('run_id')} [{run.get('status')}] {run.get('user_request')}")
        return
    if args.cmd == "open":
        paths, _ = load_run(root, None if args.target == "current" else args.target)
        open_run_folder(paths)
        return
    if args.cmd == "context":
        if args.context_cmd == "build":
            if not args.for_role:
                raise SystemExit("hive context build requires --for <agent-role>")
            report = build_context_pack_for_role(root, args.for_role, args.run_id)
            print(report["path"])
            return
        paths, _ = load_run(root, args.run_id)
        print(paths.context_pack)
        return
    if args.cmd == "handoff":
        paths, _ = load_run(root, args.run_id)
        print(paths.handoff)
        return
    if args.cmd == "invoke":
        if args.execute and args.dry_run:
            parser.error("hive invoke: --execute and --dry-run are mutually exclusive")
        if args.agent == "local":
            if args.dry_run:
                parser.error("hive invoke local: --dry-run is only supported for external providers for now")
            print(invoke_local(root, args.role, run_id=args.run_id, complexity=args.complexity))
            return
        print(invoke_external_agent(root, args.agent, args.role, run_id=args.run_id, execute=args.execute))
        return
    if args.cmd == "verify":
        print(build_verification(root, args.run_id))
        return
    if args.cmd == "summarize":
        print(build_summary(root, args.run_id))
        return
    if args.cmd == "memory" and args.memory_cmd == "draft":
        print(build_memory_draft(root, args.run_id))
        return
    if args.cmd == "memory" and args.memory_cmd == "list":
        report = memory_drafts_report(root, args.run_id)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_memory_drafts(report))
        return
    if args.cmd == "memory" and args.memory_cmd == "view":
        run_tui(root, run_id=args.run_id, view="memory", control=False)
        return
    if args.cmd == "completion":
        print_completion(args.shell)
        return
    if args.cmd == "check":
        if args.check_cmd == "list":
            report = checks_report(root)
            if args.json:
                import json

                print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
            else:
                print(format_checks_report(report))
            return
        report = run_checks(root, args.run_id)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_checks_run(report))
        return
    if args.cmd == "shell":
        run_shell(root)
        return
    if args.cmd == "chat":
        run_chat(root)
        return
    if args.cmd == "diff":
        if args.tui:
            run_tui(root, run_id=args.run_id, view="diff", control=False)
            return
        report = git_diff_report(root, args.run_id)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_git_diff_report(report))
        return
    if args.cmd == "review-diff":
        print(review_diff(root, args.run_id))
        return
    if args.cmd == "commit-summary":
        print(commit_summary(root, args.run_id))
        return
    if args.cmd == "log":
        print(read_transcript(root, args.run_id, tail=args.tail), end="")
        return
    if args.cmd == "prompt":
        prompt = read_prompt_from_stdin()
        if not prompt.strip():
            parser.error("prompt is empty")
        print(format_orchestration_report(orchestrate_prompt(root, prompt, complexity=args.complexity)))
        return
    if args.cmd == "hive" and args.hive_cmd == "activity":
        print(format_hive_activity(root, args.run_id, limit=args.tail))
        return
    if args.cmd == "society":
        run_tui(root, run_id=args.run_id, view="society", control=False)
        return
    if args.cmd == "audit":
        report = run_audit_report(root, args.run_id)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_run_audit(report))
        return
    if args.cmd == "workspace":
        report = workspace_layout_report(args.layout)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_workspace_layout(report))
        return


def print_completion(shell: str) -> None:
    commands = " ".join(sorted(COMMANDS))
    if shell == "bash":
        print(
            f"""_hive_completion() {{
  local cur="${{COMP_WORDS[COMP_CWORD]}}"
  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=( $(compgen -W "{commands}" -- "$cur") )
  fi
}}
complete -F _hive_completion hive"""
        )
        return
    if shell == "zsh":
        print(
            f"""#compdef hive
_hive() {{
  local -a commands
  commands=({commands})
  if (( CURRENT == 2 )); then
    _describe 'command' commands
  fi
}}
compdef _hive hive"""
        )
        return
    if shell == "fish":
        for command in sorted(COMMANDS):
            print(f"complete -c hive -f -n '__fish_use_subcommand' -a {command}")


def run_shell(root: Path) -> None:
    print("Hive Mind shell. Type /help or /quit.")
    while True:
        try:
            line = input("hive> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            return
        if not line:
            continue
        if line in {"/quit", "/exit", "quit", "exit"}:
            return
        if line == "/help":
            print("/new <task>  /prompt  /status  /next  /route  /log  /verify  /summary  /memory  /check  /diff  /commit  /open  /quit")
            continue
        if line.startswith("/new "):
            main(["--root", root.as_posix(), "ask", line.split(" ", 1)[1]])
            continue
        if line == "/status":
            main(["--root", root.as_posix(), "status"])
            continue
        if line == "/next":
            main(["--root", root.as_posix(), "next"])
            continue
        if line == "/prompt":
            prompt = read_multiline_prompt()
            if prompt.strip():
                main(["--root", root.as_posix(), "ask", prompt])
            continue
        if line == "/route":
            main(["--root", root.as_posix(), "plan"])
            continue
        if line == "/log":
            main(["--root", root.as_posix(), "log"])
            continue
        if line == "/verify":
            main(["--root", root.as_posix(), "verify"])
            continue
        if line == "/summary":
            main(["--root", root.as_posix(), "summarize"])
            continue
        if line == "/memory":
            main(["--root", root.as_posix(), "memory", "draft"])
            continue
        if line == "/check":
            main(["--root", root.as_posix(), "check", "run"])
            continue
        if line == "/diff":
            main(["--root", root.as_posix(), "diff"])
            continue
        if line == "/commit":
            main(["--root", root.as_posix(), "commit-summary"])
            continue
        if line == "/open":
            main(["--root", root.as_posix(), "open"])
            continue
        if line.startswith("/invoke "):
            parts = line.split()
            if len(parts) >= 3:
                main(["--root", root.as_posix(), "invoke", parts[1], "--role", parts[2]])
            else:
                print("usage: /invoke claude|codex|gemini|local role")
            continue
        if line.startswith("/"):
            print("unknown slash command")
            continue
        main(["--root", root.as_posix(), "ask", line])


def run_chat(root: Path) -> None:
    print("Hive Mind operator shell. Type a task, or /help.")
    while True:
        try:
            line = input("hive> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            return
        if not line:
            continue
        if line in {"/quit", "/exit", "quit", "exit"}:
            return
        if line == "/help":
            print_chat_help()
            continue
        if line == "/status":
            main(["--root", root.as_posix(), "status"])
            continue
        if line == "/next":
            main(["--root", root.as_posix(), "next"])
            continue
        if line == "/agents":
            main(["--root", root.as_posix(), "agents", "status"])
            continue
        if line == "/plan":
            main(["--root", root.as_posix(), "plan"])
            continue
        if line == "/log":
            main(["--root", root.as_posix(), "log", "--tail", "30"])
            continue
        if line == "/hive":
            main(["--root", root.as_posix(), "hive", "activity"])
            continue
        if line == "/memory":
            main(["--root", root.as_posix(), "memory", "list"])
            continue
        if line == "/draft-memory":
            main(["--root", root.as_posix(), "memory", "draft"])
            print_chat_run_update(root)
            continue
        if line == "/verify":
            main(["--root", root.as_posix(), "verify"])
            print_chat_run_update(root)
            continue
        if line == "/summary":
            main(["--root", root.as_posix(), "summarize"])
            print_chat_run_update(root)
            continue
        if line == "/check":
            main(["--root", root.as_posix(), "check", "run"])
            print_chat_run_update(root)
            continue
        if line == "/diff":
            main(["--root", root.as_posix(), "diff"])
            print_chat_run_update(root)
            continue
        if line == "/tui":
            main(["--root", root.as_posix(), "tui"])
            continue
        if line.startswith("/invoke "):
            parts = line.split()
            if len(parts) >= 3:
                main(["--root", root.as_posix(), "invoke", parts[1], "--role", parts[2]])
                print_chat_run_update(root)
            else:
                print("usage: /invoke claude|codex|gemini|local role")
            continue
        if line.startswith("/"):
            print("Unknown command. Type /help.")
            continue
        handle_chat_task(root, line)


def print_chat_help() -> None:
    print(
        "\n".join(
            [
                "Type a normal task to create a Hive Mind society run.",
                "",
                "Commands:",
                "  /status        show run board",
                "  /next          show next recommended command",
                "  /agents        show provider/agent status",
                "  /plan          show routing plan",
                "  /log           show recent transcript",
                "  /hive          show hive activity",
                "  /memory        list memory drafts",
                "  /draft-memory  create memory draft",
                "  /verify        validate run artifacts",
                "  /summary       update final report",
                "  /check         run policy checks",
                "  /diff          capture git diff",
                "  /tui           open status TUI",
                "  /quit          exit",
            ]
        )
    )


def handle_chat_task(root: Path, prompt: str) -> None:
    print("Hive Mind: 새 작업을 받았습니다.")
    print("Hive Mind: local router가 의도를 분해하고, Claude/Codex/Gemini/local 역할을 배정합니다.")
    report = orchestrate_prompt(root, prompt, complexity="default")
    print("Hive Mind: society plan 준비 완료.")
    for member in report.get("members") or []:
        print(f"  - {member.get('provider')}/{member.get('role')}: {member.get('status') or 'planned'}")
    print_chat_run_update(root)


def print_chat_run_update(root: Path) -> None:
    try:
        board = run_board(root)
    except Exception as exc:
        print(f"Hive Mind: 상태를 읽지 못했습니다: {exc}")
        return
    print("")
    print(format_chat_board(board))
    print("")


def format_chat_board(board: dict[str, object]) -> str:
    pipeline = board.get("pipeline") if isinstance(board.get("pipeline"), list) else []
    agents = board.get("agents") if isinstance(board.get("agents"), list) else []
    artifacts = board.get("artifacts") if isinstance(board.get("artifacts"), list) else []
    next_action = board.get("next") if isinstance(board.get("next"), dict) else {}
    done = sum(1 for item in pipeline if isinstance(item, dict) and item.get("status") == "done")
    missing = [item for item in artifacts if isinstance(item, dict) and item.get("status") != "ok"]
    active_agents = [
        item
        for item in agents
        if isinstance(item, dict) and item.get("status") in {"running", "in_progress", "prepared", "ready", "failed"}
    ]
    lines = [
        f"Run: {board.get('run_id')}  [{board.get('phase')} / {board.get('status')}]",
        f"Task: {board.get('task')}",
        f"Pipeline: {done}/{len(pipeline)} complete",
    ]
    if active_agents:
        lines.append("Agents:")
        for agent in active_agents[:8]:
            lines.append(f"  {agent_icon(str(agent.get('status')))} {agent.get('name')} [{agent.get('status')}]")
    if missing:
        names = ", ".join(str(item.get("name")) for item in missing[:6] if isinstance(item, dict))
        suffix = f" (+{len(missing) - 6} more)" if len(missing) > 6 else ""
        lines.append(f"Missing artifacts: {names}{suffix}")
    lines.extend(
        [
            "Next:",
            f"  {next_action.get('command')}",
            f"  Reason: {next_action.get('reason')}",
        ]
    )
    return "\n".join(lines)


def read_prompt_from_stdin() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return read_multiline_prompt()


def read_multiline_prompt() -> str:
    print("Enter prompt. Finish with a single '.' line.")
    lines: list[str] = []
    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("")
            break
        if line == ".":
            break
        lines.append(line)
    return "\n".join(lines)


if __name__ == "__main__":
    main()
