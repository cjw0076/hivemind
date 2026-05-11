"""Ledger protocol artifacts for execution authority.

This module is intentionally file-first. It creates the structured artifacts
that make provider/local execution auditable before any supervisor daemon exists.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .dag_state import atomic_write
from .utils import now_iso
from .workloop import append_execution_ledger, artifact_sha256, relative_artifact

SCHEMA_VERSION = 1

VOTES = {"approve", "approve_with_conditions", "block", "ask_user", "needs_referee"}
APPROVING_VOTES = {"approve", "approve_with_conditions"}
APPROVED_DECISIONS = {"approved", "approved_with_conditions"}


@dataclass
class ExecutionIntent:
    schema_version: int
    intent_id: str
    run_id: str
    step_id: str
    attempt: int
    requested_by: str
    owner_role: str
    provider: str
    provider_family: str
    action_type: str
    authority_class: str
    command_path: str | None
    command_hash: str | None
    prompt_path: str | None
    prompt_hash: str | None
    cwd: str
    permission_mode: str
    bypass_mode: str
    reversibility: float
    reversibility_source: str
    reversibility_factors: list[str]
    expected_artifacts: list[str]
    expected_file_scopes: list[str]
    timeout_seconds: int
    network_access: str
    env_allowlist: list[str]
    risk_level: str
    created_at: str


@dataclass
class ExecutionVote:
    schema_version: int
    intent_id: str
    run_id: str
    voter_role: str
    voter_provider: str
    vote: str
    confidence: float
    risk_level: str
    reasons: list[str]
    required_conditions: list[str]
    created_at: str


@dataclass
class ExecutionDecision:
    schema_version: int
    intent_id: str
    run_id: str
    decision: str
    quorum_policy: str
    votes: dict[str, str]
    required_voters: list[str]
    missing_voters: list[str]
    conditions: list[str]
    decided_by: str
    created_at: str


@dataclass
class ExecutionProof:
    schema_version: int
    intent_id: str
    run_id: str
    status: str
    returncode: int | None
    started_at: str | None
    finished_at: str
    duration_ms: int | None
    stdout_path: str | None
    stderr_path: str | None
    output_path: str | None
    files_touched: list[str] = field(default_factory=list)
    commands_run: list[str] = field(default_factory=list)
    tests_run: list[str] = field(default_factory=list)
    artifacts_created: list[str] = field(default_factory=list)
    artifact_hashes: dict[str, str] = field(default_factory=dict)
    policy_violations: list[str] = field(default_factory=list)
    verifier_status: str = "not_run"


def _run_dir(root: Path, run_id: str) -> Path:
    return root / ".runs" / run_id


def _dir(root: Path, run_id: str, name: str) -> Path:
    path = _run_dir(root, run_id) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def intent_path(root: Path, run_id: str, intent_id: str) -> Path:
    return _dir(root, run_id, "execution_intents") / f"{intent_id}.json"


def vote_path(root: Path, run_id: str, intent_id: str, voter_role: str) -> Path:
    safe_voter = voter_role.replace("/", "_").replace(" ", "_")
    return _dir(root, run_id, "execution_votes") / intent_id / f"{safe_voter}.json"


def decision_path(root: Path, run_id: str, intent_id: str) -> Path:
    return _dir(root, run_id, "execution_decisions") / f"{intent_id}.json"


def proof_path(root: Path, run_id: str, intent_id: str) -> Path:
    return _dir(root, run_id, "execution_proofs") / f"{intent_id}.json"


def _write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True))
    return path


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_path(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def _provider_and_role(owner_role: str, provider_candidates: list[str]) -> tuple[str, str, str]:
    if provider_candidates:
        provider = provider_candidates[0]
    else:
        provider = owner_role.split("-", 1)[0] if "-" in owner_role else "harness"
    role = owner_role.split("-", 1)[1] if "-" in owner_role else owner_role
    family = {
        "claude": "anthropic",
        "codex": "openai",
        "gemini": "google",
        "local": "local",
        "harness": "harness",
        "verifier": "harness",
    }.get(provider, provider)
    return provider, role, family


def _action_type(provider: str, owner_role: str) -> str:
    if provider in {"claude", "codex", "gemini"}:
        return "provider_cli"
    if provider == "local" or owner_role.startswith("local-"):
        return "local_worker"
    return "builtin"


def _risk_level(permission_mode: str, reversibility: float, action_type: str, execute: bool) -> str:
    if reversibility < 0.3:
        return "high"
    if execute and action_type == "provider_cli":
        return "high" if "write" in permission_mode else "medium"
    if "write" in permission_mode:
        return "medium"
    return "low"


def _authority_class(action_type: str, permission_mode: str, reversibility: float, execute: bool) -> str:
    if not execute:
        return "prepare_only"
    if action_type == "provider_cli":
        return "provider_bypass_irreversible" if reversibility < 0.3 else "provider_bypass_reversible"
    if action_type == "local_worker":
        return "local_write_reversible" if "write" in permission_mode else "local_read"
    if "write" in permission_mode:
        return "local_write_reversible"
    return "read_only"


def _prompt_path_for_step(root: Path, run_id: str, provider: str, role: str) -> Path | None:
    candidate = _run_dir(root, run_id) / "agents" / provider / f"{role.replace('-', '_')}_prompt.md"
    return candidate if candidate.exists() else candidate


def _next_attempt(root: Path, run_id: str, step_id: str) -> int:
    intents_dir = _run_dir(root, run_id) / "execution_intents"
    if not intents_dir.exists():
        return 1
    prefix = f"intent_{run_id}_{step_id}_"
    attempts: list[int] = []
    for path in intents_dir.glob(f"{prefix}*.json"):
        try:
            attempts.append(int(path.stem.rsplit("_", 1)[1]))
        except (IndexError, ValueError):
            continue
    return (max(attempts) + 1) if attempts else 1


def build_execution_intent(
    root: Path,
    dag: Any,
    step_id: str,
    *,
    execute: bool = False,
    requested_by: str = "harness",
) -> ExecutionIntent:
    step = dag.by_id(step_id)
    if step is None:
        raise ValueError(f"step '{step_id}' not found in DAG")
    attempt = _next_attempt(root, dag.run_id, step_id)
    intent_id = f"intent_{dag.run_id}_{step_id}_{attempt:02d}"
    provider, role, family = _provider_and_role(step.owner_role, list(step.provider_candidates or []))
    action_type = _action_type(provider, step.owner_role)
    command = shutil.which(provider) if action_type == "provider_cli" else None
    command_path = str(Path(command).resolve()) if command else None
    prompt_path = _prompt_path_for_step(root, dag.run_id, provider, role) if action_type == "provider_cli" else None
    authority_class = _authority_class(action_type, step.permission_mode, float(step.reversibility), execute)
    risk = _risk_level(step.permission_mode, float(step.reversibility), action_type, execute)
    return ExecutionIntent(
        schema_version=SCHEMA_VERSION,
        intent_id=intent_id,
        run_id=dag.run_id,
        step_id=step_id,
        attempt=attempt,
        requested_by=requested_by,
        owner_role=step.owner_role,
        provider=provider,
        provider_family=family,
        action_type=action_type,
        authority_class=authority_class,
        command_path=command_path,
        command_hash=_sha256_path(Path(command_path)) if command_path else None,
        prompt_path=relative_artifact(root, prompt_path) if prompt_path else None,
        prompt_hash=_sha256_path(prompt_path) if prompt_path else None,
        cwd=root.as_posix(),
        permission_mode=step.permission_mode,
        bypass_mode="execute" if execute else "prepare",
        reversibility=float(step.reversibility),
        reversibility_source=step.reversibility_source,
        reversibility_factors=list(step.reversibility_factors or []),
        expected_artifacts=list(step.expected_output_artifacts or []),
        expected_file_scopes=[],
        timeout_seconds=int(step.timeout or 0),
        network_access="none",
        env_allowlist=["PATH", "HOME", "HIVE_*"],
        risk_level=risk,
        created_at=now_iso(),
    )


def save_intent(root: Path, intent: ExecutionIntent) -> Path:
    path = intent_path(root, intent.run_id, intent.intent_id)
    _write_json(path, asdict(intent))
    append_execution_ledger(
        root,
        intent.run_id,
        "intent_proposed",
        actor=intent.requested_by,
        step_id=intent.step_id,
        status="proposed",
        permission_mode=intent.permission_mode,
        bypass_mode=intent.bypass_mode,
        artifact=relative_artifact(root, path),
        extra={
            "intent_id": intent.intent_id,
            "authority_class": intent.authority_class,
            "risk_level": intent.risk_level,
        },
    )
    return path


def load_intent(root: Path, run_id: str, intent_id: str) -> ExecutionIntent:
    data = _read_json(intent_path(root, run_id, intent_id))
    return ExecutionIntent(**data)


def _quorum_policy(intent: ExecutionIntent) -> str:
    if intent.authority_class == "prepare_only":
        return "prepare_only"
    if intent.authority_class in {"read_only", "local_read"}:
        return "read_only"
    if intent.authority_class == "local_write_reversible":
        return "reversible_write"
    if intent.authority_class == "provider_bypass_irreversible" or intent.reversibility < 0.3:
        return "irreversible"
    if intent.authority_class == "provider_bypass_reversible":
        return "provider_bypass"
    return "read_only"


def _required_voters(policy: str) -> list[str]:
    return {
        "prepare_only": ["policy-gate"],
        "read_only": ["policy-gate"],
        "reversible_write": ["policy-gate", "verifier"],
        "provider_bypass": ["policy-gate", "verifier", "independent-reviewer"],
        "irreversible": ["policy-gate", "user"],
        "conflicted": ["policy-gate", "referee"],
    }.get(policy, ["policy-gate"])


def check_intent(root: Path, run_id: str, intent_id: str) -> ExecutionVote:
    intent = load_intent(root, run_id, intent_id)
    policy = _quorum_policy(intent)
    vote = "approve"
    confidence = 0.95
    reasons = [f"quorum_policy={policy}", f"authority_class={intent.authority_class}"]
    conditions: list[str] = []
    event = "policy_allowed"
    if policy == "provider_bypass":
        vote = "approve_with_conditions"
        confidence = 0.75
        conditions = ["requires verifier and independent reviewer/user approval", "capture execution proof"]
        event = "policy_needs_vote"
    elif policy == "irreversible":
        vote = "ask_user"
        confidence = 0.9
        conditions = ["requires user approval or explicit repo policy"]
        event = "policy_needs_vote"
    elif policy == "reversible_write":
        vote = "approve_with_conditions"
        confidence = 0.8
        conditions = ["requires verifier approval", "capture touched files"]
        event = "policy_needs_vote"
    result = cast_vote(
        root,
        run_id,
        intent_id,
        voter_role="policy-gate",
        vote=vote,
        confidence=confidence,
        risk_level=intent.risk_level,
        reasons=reasons,
        required_conditions=conditions,
        allow_executor=False,
    )
    append_execution_ledger(
        root,
        run_id,
        event,
        actor="policy-gate",
        step_id=intent.step_id,
        status=vote,
        permission_mode=intent.permission_mode,
        bypass_mode=intent.bypass_mode,
        artifact=relative_artifact(root, vote_path(root, run_id, intent_id, "policy-gate")),
        extra={"intent_id": intent_id, "quorum_policy": policy, "conditions": conditions},
    )
    return result


def cast_vote(
    root: Path,
    run_id: str,
    intent_id: str,
    *,
    voter_role: str,
    vote: str,
    confidence: float = 0.8,
    risk_level: str | None = None,
    reasons: list[str] | None = None,
    required_conditions: list[str] | None = None,
    voter_provider: str | None = None,
    allow_executor: bool = False,
) -> ExecutionVote:
    if vote not in VOTES:
        raise ValueError(f"invalid vote '{vote}'. Allowed: {sorted(VOTES)}")
    intent = load_intent(root, run_id, intent_id)
    if not allow_executor and voter_role == intent.owner_role:
        raise ValueError("executor cannot approve its own execution intent")
    record = ExecutionVote(
        schema_version=SCHEMA_VERSION,
        intent_id=intent_id,
        run_id=run_id,
        voter_role=voter_role,
        voter_provider=voter_provider or voter_role.split("-", 1)[0],
        vote=vote,
        confidence=max(0.0, min(1.0, float(confidence))),
        risk_level=risk_level or intent.risk_level,
        reasons=reasons or [],
        required_conditions=required_conditions or [],
        created_at=now_iso(),
    )
    path = vote_path(root, run_id, intent_id, voter_role)
    _write_json(path, asdict(record))
    append_execution_ledger(
        root,
        run_id,
        "vote_cast",
        actor=voter_role,
        step_id=intent.step_id,
        status=vote,
        permission_mode=intent.permission_mode,
        bypass_mode=intent.bypass_mode,
        artifact=relative_artifact(root, path),
        extra={"intent_id": intent_id, "confidence": record.confidence},
    )
    return record


def load_votes(root: Path, run_id: str, intent_id: str) -> list[ExecutionVote]:
    directory = _run_dir(root, run_id) / "execution_votes" / intent_id
    if not directory.exists():
        return []
    votes: list[ExecutionVote] = []
    for path in sorted(directory.glob("*.json")):
        votes.append(ExecutionVote(**_read_json(path)))
    return votes


def decide_intent(root: Path, run_id: str, intent_id: str, *, decided_by: str = "harness") -> ExecutionDecision:
    intent = load_intent(root, run_id, intent_id)
    policy = _quorum_policy(intent)
    votes = load_votes(root, run_id, intent_id)
    vote_map = {v.voter_role: v.vote for v in votes}
    conditions: list[str] = []
    for vote in votes:
        conditions.extend(vote.required_conditions)

    required = _required_voters(policy)
    if policy == "provider_bypass" and "user" in vote_map and vote_map["user"] in APPROVING_VOTES:
        required = ["policy-gate", "verifier", "user"]
    missing = [voter for voter in required if voter not in vote_map]

    if any(v.vote == "block" for v in votes):
        decision = "blocked"
    elif any(v.vote == "ask_user" for v in votes) and "user" not in vote_map:
        decision = "ask_user"
    elif any(v.vote == "needs_referee" for v in votes):
        decision = "needs_referee"
    elif missing:
        decision = "needs_vote"
    elif all(vote_map.get(voter) in APPROVING_VOTES for voter in required):
        if policy == "prepare_only":
            decision = "prepare_only"
        elif any(vote_map.get(voter) == "approve_with_conditions" for voter in required) or conditions:
            decision = "approved_with_conditions"
        else:
            decision = "approved"
    else:
        decision = "blocked"

    record = ExecutionDecision(
        schema_version=SCHEMA_VERSION,
        intent_id=intent_id,
        run_id=run_id,
        decision=decision,
        quorum_policy=policy,
        votes=vote_map,
        required_voters=required,
        missing_voters=missing,
        conditions=sorted(set(conditions)),
        decided_by=decided_by,
        created_at=now_iso(),
    )
    path = decision_path(root, run_id, intent_id)
    _write_json(path, asdict(record))
    append_execution_ledger(
        root,
        run_id,
        "quorum_decided",
        actor=decided_by,
        step_id=intent.step_id,
        status=decision,
        permission_mode=intent.permission_mode,
        bypass_mode=intent.bypass_mode,
        artifact=relative_artifact(root, path),
        extra={
            "intent_id": intent_id,
            "quorum_policy": policy,
            "missing_voters": missing,
            "conditions": record.conditions,
        },
    )
    return record


def load_decision(root: Path, run_id: str, intent_id: str) -> ExecutionDecision:
    return ExecutionDecision(**_read_json(decision_path(root, run_id, intent_id)))


def approved_decision_for_step(root: Path, run_id: str, step_id: str) -> ExecutionDecision | None:
    directory = _run_dir(root, run_id) / "execution_decisions"
    if not directory.exists():
        return None
    decisions: list[tuple[ExecutionDecision, ExecutionIntent]] = []
    for path in sorted(directory.glob("*.json")):
        try:
            decision = ExecutionDecision(**_read_json(path))
            intent = load_intent(root, run_id, decision.intent_id)
        except Exception:
            continue
        if (
            intent.step_id == step_id
            and intent.bypass_mode == "execute"
            and decision.decision in APPROVED_DECISIONS
        ):
            decisions.append((decision, intent))
    if not decisions:
        return None
    decisions.sort(key=lambda pair: (pair[1].attempt, pair[0].created_at))
    return decisions[-1][0]


def step_requires_protocol_decision(step: Any, execute: bool) -> bool:
    if not execute:
        return False
    providers = set(step.provider_candidates or [])
    if providers & {"claude", "codex", "gemini"}:
        return True
    return step.owner_role.startswith(("claude-", "codex-", "gemini-"))


def create_proof(
    root: Path,
    run_id: str,
    intent_id: str,
    *,
    status: str = "completed",
    returncode: int | None = None,
    started_at: str | None = None,
    duration_ms: int | None = None,
    stdout_path: str | None = None,
    stderr_path: str | None = None,
    output_path: str | None = None,
    files_touched: list[str] | None = None,
    commands_run: list[str] | None = None,
    tests_run: list[str] | None = None,
    artifacts_created: list[str] | None = None,
    policy_violations: list[str] | None = None,
    verifier_status: str = "not_run",
) -> ExecutionProof:
    intent = load_intent(root, run_id, intent_id)
    artifact_hashes = proof_artifact_hashes(
        root,
        [stdout_path, stderr_path, output_path, *(artifacts_created or [])],
    )
    proof = ExecutionProof(
        schema_version=SCHEMA_VERSION,
        intent_id=intent_id,
        run_id=run_id,
        status=status,
        returncode=returncode,
        started_at=started_at,
        finished_at=now_iso(),
        duration_ms=duration_ms,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        output_path=output_path,
        files_touched=files_touched or [],
        commands_run=commands_run or [],
        tests_run=tests_run or [],
        artifacts_created=artifacts_created or [],
        artifact_hashes=artifact_hashes,
        policy_violations=policy_violations or [],
        verifier_status=verifier_status,
    )
    path = proof_path(root, run_id, intent_id)
    _write_json(path, asdict(proof))
    append_execution_ledger(
        root,
        run_id,
        "execution_proof_created",
        actor="verifier" if verifier_status != "not_run" else "harness",
        step_id=intent.step_id,
        status=status,
        permission_mode=intent.permission_mode,
        bypass_mode=intent.bypass_mode,
        files_touched=proof.files_touched,
        artifact=relative_artifact(root, path),
        extra={
            "intent_id": intent_id,
            "returncode": returncode,
            "verifier_status": verifier_status,
            "artifact_hash_count": len(artifact_hashes),
        },
    )
    return proof


def proof_artifact_hashes(root: Path, artifacts: list[str | None]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for artifact in artifacts:
        if not artifact:
            continue
        digest = artifact_sha256(root, artifact)
        if digest:
            hashes[str(artifact)] = digest
    return hashes


def format_protocol_record(record: Any) -> str:
    data = asdict(record) if hasattr(record, "__dataclass_fields__") else dict(record)
    lines = []
    for key in sorted(data):
        value = data[key]
        if isinstance(value, (list, dict)):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True)
        lines.append(f"{key}: {value}")
    return "\n".join(lines)
