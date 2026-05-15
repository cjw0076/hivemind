"""Native provider CLI passthrough wrapped by Hive receipts and ledger."""

from __future__ import annotations

import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from .protocol import cast_vote, check_intent, create_proof, decide_intent, save_intent
from .utils import now_iso, stable_id
from .workloop import append_execution_ledger, relative_artifact


PROVIDER_PASSTHROUGH_AGENTS = {"claude", "codex", "gemini"}


def provider_passthrough(
    root: Path,
    agent: str,
    native_args: list[str],
    *,
    run_id: str | None = None,
    execute: bool = False,
    timeout: int = 600,
    allow_workspace_write: bool = False,
    workspace_write_grant: str | None = None,
    allow_dangerous_full_access: bool = False,
    dangerous_grant: str | None = None,
) -> Path:
    """Record or execute a native provider CLI command without abstracting its flags."""
    from . import harness as h

    if agent not in PROVIDER_PASSTHROUGH_AGENTS:
        raise ValueError(f"provider must be one of: {', '.join(sorted(PROVIDER_PASSTHROUGH_AGENTS))}")
    if not native_args:
        raise ValueError("native provider passthrough requires args after --")

    paths, _ = h.load_run(root, run_id)
    provider_dir = paths.run_dir / "agents" / agent / "native"
    provider_dir.mkdir(parents=True, exist_ok=True)
    index = next_passthrough_index(provider_dir)
    prefix = f"passthrough_{index:02d}"
    command_path = provider_dir / f"{prefix}_command.txt"
    stdout_path = provider_dir / f"{prefix}_stdout.txt"
    stderr_path = provider_dir / f"{prefix}_stderr.txt"
    output_path = provider_dir / f"{prefix}_output.md"
    result_path = provider_dir / f"{prefix}_result.yaml"

    binary = h.resolve_provider_binary(root, agent) or agent
    command = [binary, *native_args]
    command_text = " ".join(shlex.quote(part) for part in command)
    command_path.write_text(command_text + "\n", encoding="utf-8")
    permission_mode = passthrough_permission_mode(agent, native_args)
    danger = passthrough_danger_reason(agent, native_args, allow_dangerous_full_access=allow_dangerous_full_access) or (
        passthrough_execute_allowlist_reason(
            agent,
            native_args,
            allow_workspace_write=allow_workspace_write,
            allow_dangerous_full_access=allow_dangerous_full_access,
        )
        if execute
        else None
    )
    if (
        execute
        and permission_mode == "danger_full_access_with_policy"
        and allow_dangerous_full_access
        and not explicit_dangerous_grant(dangerous_grant)
    ):
        danger = "blocked Codex dangerous full-access without explicit operator grant reason naming dangerous full-access"
    intent = build_provider_passthrough_intent(
        root,
        paths.run_id,
        agent,
        command_path,
        command,
        execute=execute,
        permission_mode=permission_mode,
        risk_level="high" if danger or permission_mode == "danger_full_access_with_policy" else ("low" if permission_mode == "read_only" else "medium"),
        timeout=timeout,
    )
    save_intent(root, intent)

    h.append_agent_log(paths, agent, "native", f"passthrough_command artifact={command_path.relative_to(root).as_posix()} execute={execute}")
    h.append_event(
        paths,
        "provider_passthrough_prepared",
        {"agent": agent, "artifact": command_path.relative_to(root).as_posix(), "execute": execute},
    )

    if danger:
        cast_vote(
            root,
            paths.run_id,
            intent.intent_id,
            voter_role="policy-gate",
            vote="block",
            confidence=0.98,
            risk_level="high",
            reasons=[danger],
            allow_executor=False,
        )
        decision = decide_intent(root, paths.run_id, intent.intent_id, decided_by="policy-gate")
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(danger + "\n", encoding="utf-8")
        output_path.write_text("", encoding="utf-8")
        result = h.provider_result_record(
            root,
            agent=agent,
            role="native",
            status="failed",
            provider_mode="policy_blocked",
            permission_mode=permission_mode,
            command_path=command_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_path=output_path,
            returncode=None,
            commands_run=[command_text],
            artifacts_created=[h.rel_or_empty(root, result_path), h.rel_or_empty(root, command_path), h.rel_or_empty(root, stderr_path)],
            risk_level="high",
            policy_violations=[danger],
            execute=execute,
            reason=danger,
        )
        result_path.write_text(h.format_simple_yaml(result), encoding="utf-8")
        create_proof(
            root,
            paths.run_id,
            intent.intent_id,
            status="blocked",
            returncode=None,
            stdout_path=h.rel_or_empty(root, stdout_path),
            stderr_path=h.rel_or_empty(root, stderr_path),
            output_path=h.rel_or_empty(root, output_path),
            commands_run=[command_text],
            artifacts_created=[h.rel_or_empty(root, result_path), h.rel_or_empty(root, command_path), h.rel_or_empty(root, stderr_path)],
            policy_violations=[danger],
            verifier_status="policy_blocked",
        )
        append_execution_ledger(
            root,
            paths.run_id,
            "policy_blocked",
            actor="policy-gate",
            step_id=intent.step_id,
            status=decision.decision,
            permission_mode=permission_mode,
            bypass_mode="execute" if execute else "prepare",
            artifact=h.rel_or_empty(root, result_path),
            extra={"intent_id": intent.intent_id, "reason": danger},
        )
        h.set_agent_status(paths, f"{agent}-native", "failed")
        h.update_state(paths, phase="provider", status="needs_attention")
        return result_path

    check_intent(root, paths.run_id, intent.intent_id)
    if execute and permission_mode in {"workspace_write_with_policy", "danger_full_access_with_policy"}:
        grant_reason = (
            dangerous_grant
            if permission_mode == "danger_full_access_with_policy"
            else workspace_write_grant
        ) or f"explicit {permission_mode} grant supplied by caller"
        required_conditions = ["capture execution proof", "review changed files before closeout"]
        if permission_mode == "danger_full_access_with_policy":
            required_conditions.extend(
                [
                    "do not store secrets or provider credentials",
                    "operator may stop or revert follow-up manually",
                ]
            )
        cast_vote(
            root,
            paths.run_id,
            intent.intent_id,
            voter_role="verifier",
            vote="approve_with_conditions",
            confidence=0.74 if permission_mode == "danger_full_access_with_policy" else 0.82,
            risk_level=intent.risk_level,
            reasons=[f"{permission_mode} requested through explicit AIOS provider policy", grant_reason],
            required_conditions=required_conditions,
        )
        cast_vote(
            root,
            paths.run_id,
            intent.intent_id,
            voter_role="user",
            vote="approve",
            confidence=0.9,
            risk_level=intent.risk_level,
            reasons=[grant_reason],
        )
    decision = decide_intent(root, paths.run_id, intent.intent_id, decided_by="policy-gate")

    if not execute:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        output_path.write_text("", encoding="utf-8")
        result = h.provider_result_record(
            root,
            agent=agent,
            role="native",
            status="prepared",
            provider_mode="native_passthrough",
            permission_mode=permission_mode,
            command_path=command_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_path=output_path,
            commands_run=[command_text],
            artifacts_created=[h.rel_or_empty(root, result_path), h.rel_or_empty(root, command_path)],
            risk_level=intent.risk_level,
            execute=False,
            reason=f"native passthrough prepared; decision={decision.decision}",
        )
        result_path.write_text(h.format_simple_yaml(result), encoding="utf-8")
        create_proof(
            root,
            paths.run_id,
            intent.intent_id,
            status="prepared",
            stdout_path=h.rel_or_empty(root, stdout_path),
            stderr_path=h.rel_or_empty(root, stderr_path),
            output_path=h.rel_or_empty(root, output_path),
            commands_run=[command_text],
            artifacts_created=[h.rel_or_empty(root, result_path), h.rel_or_empty(root, command_path)],
            verifier_status="not_run",
        )
        h.set_agent_status(paths, f"{agent}-native", "prepared")
        h.update_state(paths, phase="provider", status="ready")
        return result_path

    if decision.decision not in {"approved", "approved_with_conditions", "prepare_only"}:
        reason = f"provider passthrough execution blocked by decision={decision.decision}"
        stderr_path.write_text(reason + "\n", encoding="utf-8")
        stdout_path.write_text("", encoding="utf-8")
        output_path.write_text("", encoding="utf-8")
        result = h.provider_result_record(
            root,
            agent=agent,
            role="native",
            status="failed",
            provider_mode="policy_blocked",
            permission_mode=permission_mode,
            command_path=command_path,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            output_path=output_path,
            commands_run=[command_text],
            artifacts_created=[h.rel_or_empty(root, result_path), h.rel_or_empty(root, command_path), h.rel_or_empty(root, stderr_path)],
            risk_level=intent.risk_level,
            policy_violations=[reason],
            execute=True,
            reason=reason,
        )
        result_path.write_text(h.format_simple_yaml(result), encoding="utf-8")
        create_proof(
            root,
            paths.run_id,
            intent.intent_id,
            status="blocked",
            stdout_path=h.rel_or_empty(root, stdout_path),
            stderr_path=h.rel_or_empty(root, stderr_path),
            output_path=h.rel_or_empty(root, output_path),
            commands_run=[command_text],
            artifacts_created=[h.rel_or_empty(root, result_path), h.rel_or_empty(root, command_path), h.rel_or_empty(root, stderr_path)],
            policy_violations=[reason],
            verifier_status="policy_blocked",
        )
        h.set_agent_status(paths, f"{agent}-native", "failed")
        h.update_state(paths, phase="provider", status="needs_attention")
        return result_path

    started_at = now_iso()
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=timeout)
        returncode = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = 124
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr if isinstance(exc.stderr, str) else "") + f"\nprovider passthrough timed out after {timeout}s\n"
    finished_at = now_iso()
    duration_ms = int((time.monotonic() - started) * 1000)
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    output_path.write_text(stdout, encoding="utf-8")
    status = "timeout" if timed_out else ("completed" if returncode == 0 else "failed")
    reason = f"native passthrough timed out after {timeout}s; decision={decision.decision}" if timed_out else f"native passthrough executed; decision={decision.decision}"
    result = h.provider_result_record(
        root,
        agent=agent,
        role="native",
        status=status,
        provider_mode="native_passthrough",
        permission_mode=permission_mode,
        command_path=command_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        output_path=output_path,
        returncode=returncode,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        commands_run=[command_text],
        artifacts_created=[
            h.rel_or_empty(root, result_path),
            h.rel_or_empty(root, command_path),
            h.rel_or_empty(root, stdout_path),
            h.rel_or_empty(root, stderr_path),
            h.rel_or_empty(root, output_path),
        ],
        risk_level=intent.risk_level if status == "completed" else "medium",
        execute=True,
        reason=reason,
    )
    result_path.write_text(h.format_simple_yaml(result), encoding="utf-8")
    create_proof(
        root,
        paths.run_id,
        intent.intent_id,
        status=status,
        returncode=returncode,
        started_at=started_at,
        duration_ms=duration_ms,
        stdout_path=h.rel_or_empty(root, stdout_path),
        stderr_path=h.rel_or_empty(root, stderr_path),
        output_path=h.rel_or_empty(root, output_path),
        commands_run=[command_text],
        artifacts_created=[
            h.rel_or_empty(root, result_path),
            h.rel_or_empty(root, command_path),
            h.rel_or_empty(root, stdout_path),
            h.rel_or_empty(root, stderr_path),
            h.rel_or_empty(root, output_path),
        ],
        verifier_status="timeout" if timed_out else "not_run",
    )
    h.append_event(paths, f"provider_passthrough_{status}", {"agent": agent, "artifact": result_path.relative_to(root).as_posix()})
    h.append_transcript(paths, "Ran", f"{agent}/native passthrough -> `{result_path.relative_to(root).as_posix()}` status={status}")
    h.set_agent_status(paths, f"{agent}-native", status)
    h.update_state(paths, phase="provider", status="in_progress" if status == "completed" else "needs_attention")
    return result_path


def next_passthrough_index(provider_dir: Path) -> int:
    indexes: list[int] = []
    for path in provider_dir.glob("passthrough_*_result.yaml"):
        try:
            indexes.append(int(path.name.split("_")[1]))
        except (IndexError, ValueError):
            continue
    return (max(indexes) + 1) if indexes else 1


def passthrough_permission_mode(agent: str, native_args: list[str]) -> str:
    lowered = [arg.lower() for arg in native_args]
    if agent == "codex":
        if "--dangerously-bypass-approvals-and-sandbox" in lowered:
            return "danger_full_access_with_policy"
        sandbox = option_value(lowered, "--sandbox")
        if sandbox == "read-only":
            return "read_only"
        if sandbox == "workspace-write":
            return "workspace_write_with_policy"
        if sandbox in {"danger-full-access", "full", "open"}:
            return "danger_full_access_with_policy"
    if agent == "claude" and option_value(lowered, "--permission-mode") in {"plan", "default"}:
        return "read_only"
    if agent == "gemini" and option_value(lowered, "--approval-mode") in {"plan", "default"}:
        return "read_only"
    return "provider_native"


def option_value(args: list[str], option: str) -> str | None:
    if option not in args:
        return None
    index = args.index(option)
    if index + 1 >= len(args):
        return ""
    return args[index + 1]


def passthrough_danger_reason(agent: str, native_args: list[str], *, allow_dangerous_full_access: bool = False) -> str | None:
    lowered = [arg.lower() for arg in native_args]
    if agent == "claude" and "--dangerously-skip-permissions" in lowered:
        return "blocked dangerous Claude bypass flag: --dangerously-skip-permissions"
    if agent == "gemini" and any(flag in lowered for flag in {"--yolo", "--skip-trust", "--trust-all", "--trusted"}):
        return "blocked Gemini trust/approval bypass flag"
    if agent == "codex":
        if "--dangerously-bypass-approvals-and-sandbox" in lowered and not allow_dangerous_full_access:
            return "blocked Codex dangerous full-access flag without explicit AIOS dangerous grant: --dangerously-bypass-approvals-and-sandbox"
        sandbox = option_value(lowered, "--sandbox")
        approval = option_value(lowered, "--ask-for-approval") or option_value(lowered, "--approval")
        if sandbox in {"danger-full-access", "full", "open"} and not allow_dangerous_full_access:
            return f"blocked Codex full-access sandbox without explicit AIOS dangerous grant: sandbox={sandbox}"
        if sandbox in {"workspace-write", "danger-full-access", "full", "open"} and approval == "never":
            return f"blocked Codex unsafe sandbox/approval combination: sandbox={sandbox} approval={approval}"
    if native_args and Path(native_args[0]).name in {"sh", "bash", "zsh", "fish"}:
        command_text = " ".join(lowered)
        destructive = ["rm -rf", "git reset --hard", "mkfs", "dd if=", ":(){", ">/dev/sd", "> /dev/sd"]
        if any(pattern in command_text for pattern in destructive):
            return "blocked destructive shell wrapper in provider passthrough"
    return None


def explicit_dangerous_grant(grant: str | None) -> bool:
    lowered = str(grant or "").lower()
    return "dangerous" in lowered and ("full-access" in lowered or "full access" in lowered)


def passthrough_execute_allowlist_reason(
    agent: str,
    native_args: list[str],
    *,
    allow_workspace_write: bool = False,
    allow_dangerous_full_access: bool = False,
) -> str | None:
    """Return a block reason unless native args match a safe execute profile."""
    lowered = [arg.lower() for arg in native_args]
    command_name = Path(lowered[0]).name if lowered else ""
    if agent == "codex":
        sandbox = option_value(lowered, "--sandbox")
        if command_name == "exec" and sandbox == "read-only":
            return None
        if allow_workspace_write and command_name == "exec" and sandbox == "workspace-write":
            return None
        if allow_dangerous_full_access and command_name == "exec" and "--dangerously-bypass-approvals-and-sandbox" in lowered:
            return None
        if allow_dangerous_full_access and command_name == "exec" and sandbox == "danger-full-access":
            return None
        return "blocked provider passthrough execute outside Codex allowlist: require `exec --sandbox read-only`, explicit workspace-write grant, or explicit dangerous full-access grant"
    if agent == "claude":
        permission_mode = option_value(lowered, "--permission-mode")
        if ("-p" in lowered or "--print" in lowered) and permission_mode in {"plan", "default"}:
            return None
        return "blocked provider passthrough execute outside Claude allowlist: require print mode with --permission-mode plan/default"
    if agent == "gemini":
        approval_mode = option_value(lowered, "--approval-mode")
        if ("-p" in lowered or "--prompt" in lowered) and approval_mode in {"plan", "default"}:
            return None
        return "blocked provider passthrough execute outside Gemini allowlist: require prompt mode with --approval-mode plan/default"
    return "blocked provider passthrough execute for unknown provider profile"


def build_provider_passthrough_intent(
    root: Path,
    run_id: str,
    agent: str,
    command_path: Path,
    command: list[str],
    *,
    execute: bool,
    permission_mode: str,
    risk_level: str,
    timeout: int,
) -> Any:
    from .protocol import ExecutionIntent

    intents_dir = root / ".runs" / run_id / "execution_intents"
    attempt = len(list(intents_dir.glob(f"intent_{run_id}_provider_{agent}_native_*.json"))) + 1 if intents_dir.exists() else 1
    command_hash = stable_id("command", *command)
    if not execute:
        authority_class = "prepare_only"
    elif permission_mode == "read_only":
        authority_class = "read_only"
    elif permission_mode == "danger_full_access_with_policy":
        authority_class = "provider_bypass_irreversible"
    else:
        authority_class = "provider_bypass_reversible"
    reversibility = 1.0 if permission_mode == "read_only" else (0.2 if permission_mode == "danger_full_access_with_policy" else 0.6)
    return ExecutionIntent(
        schema_version=1,
        intent_id=f"intent_{run_id}_provider_{agent}_native_{attempt:02d}",
        run_id=run_id,
        step_id=f"provider_{agent}_native",
        attempt=attempt,
        requested_by="operator",
        owner_role=f"{agent}-native",
        provider=agent,
        provider_family={"claude": "anthropic", "codex": "openai", "gemini": "google"}.get(agent, agent),
        action_type="provider_cli",
        authority_class=authority_class,
        command_path=relative_artifact(root, command_path),
        command_hash=command_hash,
        prompt_path=None,
        prompt_hash=None,
        cwd=root.as_posix(),
        permission_mode=permission_mode,
        bypass_mode="execute" if execute else "prepare",
        reversibility=reversibility,
        reversibility_source="estimated",
        reversibility_factors=["native_provider_passthrough", f"permission_mode={permission_mode}"],
        expected_artifacts=[relative_artifact(root, command_path)],
        expected_file_scopes=[],
        timeout_seconds=timeout,
        network_access="provider_default",
        env_allowlist=["PATH", "HOME", "HIVE_*"],
        risk_level=risk_level,
        created_at=now_iso(),
    )
