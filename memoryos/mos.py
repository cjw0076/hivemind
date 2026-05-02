"""`mos` command: MemoryOS harness CLI and TUI."""

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
    format_doctor,
    format_local_runtime,
    local_routes_report,
    get_current,
    init_harness,
    init_onboarding,
    invoke_external_agent,
    invoke_local,
    list_runs,
    local_runtime_report,
    load_run,
    open_run_folder,
    read_transcript,
    format_onboarding,
    format_settings,
    format_settings_shell,
    settings_report,
    ask_router,
    checks_report,
    format_routing_plan,
    format_checks_report,
    format_checks_run,
    format_git_diff_report,
    load_routing_plan,
    git_diff_report,
    review_diff,
    run_checks,
)
from .tui import print_status, run_tui


COMMANDS = {
    "init",
    "doctor",
    "agents",
    "settings",
    "local",
    "run",
    "ask",
    "status",
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
    "diff",
    "review-diff",
    "commit-summary",
    "log",
    "prompt",
}


def normalize_argv(argv: list[str]) -> list[str]:
    """Allow provider-style prompt entry: `mos "build this"` -> `mos ask "build this"`."""
    if not argv:
        return ["shell"] if sys.stdin.isatty() and sys.stdout.isatty() else ["--help"]
    if argv[0] in {"-h", "--help", "--version"}:
        return argv
    if argv[0] == "--root":
        if len(argv) >= 3 and argv[2] not in COMMANDS and not argv[2].startswith("-"):
            return [argv[0], argv[1], "ask", " ".join(argv[2:])]
        return argv
    if argv[0].startswith("--root="):
        if len(argv) >= 2 and argv[1] not in COMMANDS and not argv[1].startswith("-"):
            return [argv[0], "ask", " ".join(argv[1:])]
        return argv
    if argv[0] not in COMMANDS and not argv[0].startswith("-"):
        return ["ask", " ".join(argv)]
    return argv


def main(argv: list[str] | None = None) -> None:
    argv = normalize_argv(list(sys.argv[1:] if argv is None else argv))
    parser = argparse.ArgumentParser(prog="mos", description="MemoryOS harness CLI/TUI")
    parser.add_argument("--root", default=".", help="workspace root")
    parser.add_argument("--version", action="version", version="mos 0.1.0")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_cmd = sub.add_parser("init", help="initialize MemoryOS onboarding state")
    init_cmd.add_argument("--json", action="store_true")
    init_cmd.add_argument("--no-tui", action="store_true", help="non-interactive init; accepted for installer compatibility")
    init_cmd.add_argument("--skills", choices=["yes", "no"], default="no", help="prepare skill config placeholders")
    init_cmd.add_argument("--mcp", choices=["yes", "no"], default="no", help="prepare MCP config placeholders")
    doctor_cmd = sub.add_parser("doctor", help="check MemoryOS runtime health")
    doctor_cmd.add_argument("--json", action="store_true")

    agents_cmd = sub.add_parser("agents", help="provider/agent registry helpers")
    agents_sub = agents_cmd.add_subparsers(dest="agents_cmd", required=True)
    detect_cmd = agents_sub.add_parser("detect", help="detect installed provider CLIs and runtime config")
    detect_cmd.add_argument("--json", action="store_true")

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
    local_setup_cmd.add_argument("--json", action="store_true")
    local_routes_cmd = local_sub.add_parser("routes", help="show local worker route table")
    local_routes_cmd.add_argument("--json", action="store_true")

    run_cmd = sub.add_parser("run", help="create a structured run folder")
    run_cmd.add_argument("task", help="user task/request")
    run_cmd.add_argument("--project", default="MemoryOS")
    run_cmd.add_argument("--type", default="implementation", dest="task_type")
    run_cmd.add_argument("-q", "--quiet", action="store_true", help="only print the run id/path")
    run_cmd.add_argument("--json", action="store_true")

    ask_cmd = sub.add_parser("ask", help="route one prompt through local intent decomposition")
    ask_cmd.add_argument("prompt", help="user prompt/task")
    ask_cmd.add_argument("--run-id")
    ask_cmd.add_argument("--complexity", choices=["fast", "default", "strong"], default="default")

    status_cmd = sub.add_parser("status", help="show current run status")
    status_cmd.add_argument("--run-id")
    status_cmd.add_argument("--json", action="store_true")

    tui_cmd = sub.add_parser("tui", help="open the run status TUI")
    tui_cmd.add_argument("--run-id")

    plan_cmd = sub.add_parser("plan", help="show current routing plan")
    plan_cmd.add_argument("--run-id")
    plan_cmd.add_argument("--json", action="store_true")

    sub.add_parser("runs", help="list recent runs")

    open_cmd = sub.add_parser("open", help="print/open current run folder")
    open_cmd.add_argument("target", nargs="?", default="current")

    context_cmd = sub.add_parser("context", help="print current context pack path")
    context_cmd.add_argument("--run-id")

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

    diff_cmd = sub.add_parser("diff", help="write/show git diff report for current run")
    diff_cmd.add_argument("--run-id")
    diff_cmd.add_argument("--json", action="store_true")
    review_diff_cmd = sub.add_parser("review-diff", help="capture git diff and run local review")
    review_diff_cmd.add_argument("--run-id")
    commit_summary_cmd = sub.add_parser("commit-summary", help="write proposed commit summary without committing")
    commit_summary_cmd.add_argument("--run-id")
    log_cmd = sub.add_parser("log", help="show current run transcript")
    log_cmd.add_argument("--run-id")
    log_cmd.add_argument("--tail", type=int, default=80)
    prompt_cmd = sub.add_parser("prompt", help="read a prompt from stdin or multiline input and route it")
    prompt_cmd.add_argument("--complexity", choices=["fast", "default", "strong"], default="default")

    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.cmd == "init":
        report = init_onboarding(root)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_onboarding(report))
        return
    if args.cmd == "doctor":
        report = doctor_report(root)
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_doctor(report))
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
        report = local_runtime_report(root, write=args.local_cmd == "setup")
        if args.json:
            import json

            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(format_local_runtime(report))
            if args.local_cmd == "setup":
                print("")
                print(f"Wrote {root / '.memoryos' / 'local_runtime.json'}")
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
    if args.cmd == "status":
        print_status(root, run_id=args.run_id, json_output=args.json)
        return
    if args.cmd == "tui":
        run_tui(root, run_id=args.run_id)
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
        paths, _ = load_run(root, args.run_id)
        print(paths.context_pack)
        return
    if args.cmd == "handoff":
        paths, _ = load_run(root, args.run_id)
        print(paths.handoff)
        return
    if args.cmd == "invoke":
        if args.execute and args.dry_run:
            parser.error("mos invoke: --execute and --dry-run are mutually exclusive")
        if args.agent == "local":
            if args.dry_run:
                parser.error("mos invoke local: --dry-run is only supported for external providers for now")
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
    if args.cmd == "diff":
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
        print(ask_router(root, prompt, complexity=args.complexity))
        return


def print_completion(shell: str) -> None:
    commands = " ".join(sorted(COMMANDS))
    if shell == "bash":
        print(
            f"""_mos_completion() {{
  local cur="${{COMP_WORDS[COMP_CWORD]}}"
  if [[ $COMP_CWORD -eq 1 ]]; then
    COMPREPLY=( $(compgen -W "{commands}" -- "$cur") )
  fi
}}
complete -F _mos_completion mos"""
        )
        return
    if shell == "zsh":
        print(
            f"""#compdef mos
_mos() {{
  local -a commands
  commands=({commands})
  if (( CURRENT == 2 )); then
    _describe 'command' commands
  fi
}}
compdef _mos mos"""
        )
        return
    if shell == "fish":
        for command in sorted(COMMANDS):
            print(f"complete -c mos -f -n '__fish_use_subcommand' -a {command}")


def run_shell(root: Path) -> None:
    print("MemoryOS shell. Type /help or /quit.")
    while True:
        try:
            line = input("mos> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("")
            return
        if not line:
            continue
        if line in {"/quit", "/exit", "quit", "exit"}:
            return
        if line == "/help":
            print("/new <task>  /prompt  /status  /route  /log  /verify  /summary  /memory  /check  /diff  /commit  /open  /quit")
            continue
        if line.startswith("/new "):
            main(["--root", root.as_posix(), "ask", line.split(" ", 1)[1]])
            continue
        if line == "/status":
            main(["--root", root.as_posix(), "status"])
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
