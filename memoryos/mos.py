"""`mos` command: MemoryOS harness CLI and TUI."""

from __future__ import annotations

import argparse
from pathlib import Path

from .harness import (
    build_memory_draft,
    build_summary,
    build_verification,
    create_run,
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
    format_onboarding,
)
from .tui import print_status, run_tui


def main() -> None:
    parser = argparse.ArgumentParser(prog="mos", description="MemoryOS harness CLI/TUI")
    parser.add_argument("--root", default=".", help="workspace root")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_cmd = sub.add_parser("init", help="initialize MemoryOS onboarding state")
    init_cmd.add_argument("--json", action="store_true")
    doctor_cmd = sub.add_parser("doctor", help="check MemoryOS runtime health")
    doctor_cmd.add_argument("--json", action="store_true")

    agents_cmd = sub.add_parser("agents", help="provider/agent registry helpers")
    agents_sub = agents_cmd.add_subparsers(dest="agents_cmd", required=True)
    detect_cmd = agents_sub.add_parser("detect", help="detect installed provider CLIs and runtime config")
    detect_cmd.add_argument("--json", action="store_true")

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

    status_cmd = sub.add_parser("status", help="show current run status")
    status_cmd.add_argument("--run-id")
    status_cmd.add_argument("--json", action="store_true")

    tui_cmd = sub.add_parser("tui", help="open the run status TUI")
    tui_cmd.add_argument("--run-id")

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

    args = parser.parse_args()
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
        print(paths.run_dir)
        return
    if args.cmd == "status":
        print_status(root, run_id=args.run_id, json_output=args.json)
        return
    if args.cmd == "tui":
        run_tui(root, run_id=args.run_id)
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


if __name__ == "__main__":
    main()
