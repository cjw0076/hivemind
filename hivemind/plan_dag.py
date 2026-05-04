"""Task DAG runtime for Hive Mind.

Step-level execution with sequential/parallel/barrier/verify/synthesize semantics.
The chair (harness) holds the state machine; agents run inside narrow write scopes.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .utils import now_iso

PLAN_DAG_FILE = "plan_dag.json"
SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

@dataclass
class PlanStep:
    step_id: str
    kind: str  # sequential | parallel | barrier | verify | synthesize
    depends_on: list[str]
    owner_role: str
    provider_candidates: list[str]
    permission_mode: str
    input_artifacts: list[str]
    expected_output_artifacts: list[str]
    acceptance_criteria: list[str]
    timeout: int          # seconds, 0 = use provider default
    retry_policy: str     # none | once | twice
    on_failure: str       # stop | skip | escalate
    status: str           # pending | running | completed | failed | skipped | blocked
    started_at: str | None = None
    finished_at: str | None = None
    artifact: str | None = None  # primary output artifact path (relative to root)

    # Evaluation policy (observe-only until mutation_policy.mode = "adaptive")
    evaluation_policy: dict[str, Any] = field(default_factory=dict)
    # {
    #   "evaluators": ["syntax", "execution", "claim", "risk", "disagreement"],
    #   "accept_if":   {schema_valid: true, risk_below: "high", disagreement_below: 2},
    #   "escalate_if": {confidence_below: 0.5, risk_level_above: "medium",
    #                   unsupported_claims_above: 1, disagreement_with: ["alt_planner"]},
    #   "mutation_policy": {mode: "observe_only", allowed_insertions: [...]}
    # }

    # Deprecated: use evaluation_policy instead. Kept for backward compat.
    quality_gates: list[dict[str, Any]] = field(default_factory=list)
    escalation_threshold: dict[str, Any] = field(default_factory=dict)
    referee_policy: dict[str, Any] = field(default_factory=dict)

    evaluation: dict[str, Any] | None = None

    # Append-only confidence trajectory across retries/providers.
    # Each point: {ts, value, source, attempt, provider, role, artifact}
    confidence_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PlanDAG:
    schema_version: int
    run_id: str
    task: str
    intent: str
    created_at: str
    steps: list[PlanStep]
    version: int = 0  # monotonically incremented on every atomic save (CAS key)

    def by_id(self, step_id: str) -> PlanStep | None:
        return next((s for s in self.steps if s.step_id == step_id), None)

    def status_of(self, step_id: str) -> str:
        step = self.by_id(step_id)
        return step.status if step else "unknown"

    def runnable(self) -> list[PlanStep]:
        """Steps whose dependencies are all satisfied (completed/prepared/skipped) and whose status is pending."""
        satisfied = {s.step_id for s in self.steps if s.status in {"completed", "prepared", "skipped"}}
        return [
            s for s in self.steps
            if s.status == "pending" and all(dep in satisfied for dep in s.depends_on)
        ]

    def next_sequential(self) -> PlanStep | None:
        """First runnable non-barrier step (priority: sequential > parallel > verify > synthesize)."""
        candidates = self.runnable()
        if not candidates:
            return None
        order = ["sequential", "parallel", "verify", "synthesize", "barrier"]
        candidates.sort(key=lambda s: (order.index(s.kind) if s.kind in order else 99, s.step_id))
        return candidates[0]

    def is_complete(self) -> bool:
        return all(s.status in {"completed", "skipped"} for s in self.steps)

    def is_blocked(self) -> bool:
        return any(s.status == "failed" for s in self.steps) and not self.runnable()


# ---------------------------------------------------------------------------
# DAG templates by intent
# ---------------------------------------------------------------------------

def _step(
    step_id: str,
    kind: str,
    depends_on: list[str],
    owner_role: str,
    provider_candidates: list[str],
    *,
    permission_mode: str = "read_only",
    input_artifacts: list[str] | None = None,
    expected_output_artifacts: list[str] | None = None,
    acceptance_criteria: list[str] | None = None,
    timeout: int = 120,
    retry_policy: str = "once",
    on_failure: str = "stop",
    status: str = "pending",
) -> PlanStep:
    return PlanStep(
        step_id=step_id,
        kind=kind,
        depends_on=depends_on,
        owner_role=owner_role,
        provider_candidates=provider_candidates,
        permission_mode=permission_mode,
        input_artifacts=input_artifacts or [],
        expected_output_artifacts=expected_output_artifacts or [],
        acceptance_criteria=acceptance_criteria or [],
        timeout=timeout,
        retry_policy=retry_policy,
        on_failure=on_failure,
        status=status,
    )


def _shared_tail(depends_on: list[str]) -> list[PlanStep]:
    return [
        _step("verify", "verify", depends_on, "verifier", [],
              permission_mode="none", expected_output_artifacts=["verification.yaml"],
              timeout=30, on_failure="escalate"),
        _step("memory", "sequential", ["verify"], "local-memory-curator", ["local"],
              input_artifacts=["events.jsonl"], expected_output_artifacts=["memory_drafts.json"],
              timeout=120, on_failure="skip"),
        _step("close", "synthesize", ["memory"], "harness", [],
              permission_mode="none", expected_output_artifacts=["final_report.md"],
              timeout=30, on_failure="skip"),
    ]


DAG_TEMPLATES: dict[str, list[PlanStep]] = {
    "implementation": [
        _step("intake", "sequential", [], "harness", [],
              permission_mode="none",
              expected_output_artifacts=["task.yaml"],
              timeout=0, on_failure="stop", status="completed"),
        _step("context", "parallel", ["intake"], "local-context-compressor", ["local"],
              input_artifacts=["context_pack.md"],
              expected_output_artifacts=["agents/local/context.json"],
              timeout=120, on_failure="skip"),
        _step("diff_review", "parallel", ["intake"], "local-diff-reviewer", ["local"],
              input_artifacts=["events.jsonl"],
              expected_output_artifacts=["agents/local/review.json"],
              timeout=120, on_failure="skip"),
        _step("barrier_context", "barrier", ["context", "diff_review"], "harness", [],
              permission_mode="none", timeout=0, on_failure="stop"),
        _step("planner", "sequential", ["barrier_context"], "claude-planner", ["claude"],
              permission_mode="plan",
              input_artifacts=["context_pack.md"],
              expected_output_artifacts=["agents/claude/planner_result.yaml"],
              acceptance_criteria=["status: prepared or completed"],
              timeout=600, on_failure="escalate"),
        _step("executor", "sequential", ["planner"], "codex-executor", ["codex"],
              permission_mode="workspace_write_with_policy",
              input_artifacts=["handoff.yaml"],
              expected_output_artifacts=["agents/codex/executor_result.yaml"],
              acceptance_criteria=["status: prepared or completed"],
              timeout=600, on_failure="escalate"),
        *_shared_tail(["executor"]),
    ],
    "review": [
        _step("intake", "sequential", [], "harness", [],
              permission_mode="none", expected_output_artifacts=["task.yaml"],
              timeout=0, on_failure="stop", status="completed"),
        _step("context", "parallel", ["intake"], "local-context-compressor", ["local"],
              input_artifacts=["context_pack.md"],
              expected_output_artifacts=["agents/local/context.json"],
              timeout=120, on_failure="skip"),
        _step("diff_review", "parallel", ["intake"], "local-diff-reviewer", ["local"],
              input_artifacts=["events.jsonl"],
              expected_output_artifacts=["agents/local/review.json"],
              timeout=120, on_failure="skip"),
        _step("barrier_context", "barrier", ["context", "diff_review"], "harness", [],
              permission_mode="none", timeout=0, on_failure="stop"),
        _step("reviewer", "sequential", ["barrier_context"], "claude-reviewer", ["claude"],
              permission_mode="plan",
              input_artifacts=["context_pack.md"],
              expected_output_artifacts=["agents/claude/reviewer_result.yaml"],
              timeout=600, on_failure="escalate"),
        *_shared_tail(["reviewer"]),
    ],
    "planning": [
        _step("intake", "sequential", [], "harness", [],
              permission_mode="none", expected_output_artifacts=["task.yaml"],
              timeout=0, on_failure="stop", status="completed"),
        _step("context", "sequential", ["intake"], "local-context-compressor", ["local"],
              input_artifacts=["context_pack.md"],
              expected_output_artifacts=["agents/local/context.json"],
              timeout=120, on_failure="skip"),
        _step("planner", "sequential", ["context"], "claude-planner", ["claude"],
              permission_mode="plan",
              input_artifacts=["context_pack.md"],
              expected_output_artifacts=["agents/claude/planner_result.yaml"],
              timeout=600, on_failure="escalate"),
        _step("alt_planner", "parallel", ["context"], "gemini-planner", ["gemini"],
              permission_mode="read_only",
              input_artifacts=["context_pack.md"],
              expected_output_artifacts=["agents/gemini/planner_result.yaml"],
              timeout=600, on_failure="skip"),
        _step("barrier_plans", "barrier", ["planner", "alt_planner"], "harness", [],
              permission_mode="none", timeout=0, on_failure="stop"),
        *_shared_tail(["barrier_plans"]),
    ],
    "debugging": [
        _step("intake", "sequential", [], "harness", [],
              permission_mode="none", expected_output_artifacts=["task.yaml"],
              timeout=0, on_failure="stop", status="completed"),
        _step("context", "parallel", ["intake"], "local-context-compressor", ["local"],
              input_artifacts=["context_pack.md"],
              expected_output_artifacts=["agents/local/context.json"],
              timeout=120, on_failure="skip"),
        _step("log_review", "parallel", ["intake"], "local-log-summarizer", ["local"],
              input_artifacts=["events.jsonl"],
              expected_output_artifacts=["agents/local/summarize.json"],
              timeout=120, on_failure="skip"),
        _step("barrier_debug", "barrier", ["context", "log_review"], "harness", [],
              permission_mode="none", timeout=0, on_failure="stop"),
        _step("planner", "sequential", ["barrier_debug"], "claude-planner", ["claude"],
              permission_mode="plan",
              input_artifacts=["context_pack.md"],
              expected_output_artifacts=["agents/claude/planner_result.yaml"],
              timeout=600, on_failure="escalate"),
        *_shared_tail(["planner"]),
    ],
}

# Fallback for unknown intents
DAG_TEMPLATES["unknown"] = DAG_TEMPLATES["planning"]
DAG_TEMPLATES["research"] = DAG_TEMPLATES["planning"]
DAG_TEMPLATES["documentation"] = DAG_TEMPLATES["review"]
DAG_TEMPLATES["memory_import"] = DAG_TEMPLATES["review"]


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def _steps_to_dicts(steps: list[PlanStep]) -> list[dict[str, Any]]:
    return [asdict(s) for s in steps]


def _steps_from_dicts(dicts: list[dict[str, Any]]) -> list[PlanStep]:
    import dataclasses
    known = {f.name for f in dataclasses.fields(PlanStep)}
    return [PlanStep(**{k: v for k, v in d.items() if k in known}) for d in dicts]


def save_dag(root: Path, dag: PlanDAG, expected_version: int | None = None) -> Path:
    """Atomically persist the DAG.

    expected_version: if set, performs a compare-and-swap check.
    Raises RuntimeError if the version on disk doesn't match.
    dag.version is incremented on every successful write.
    """
    from .dag_state import atomic_write
    from .harness import load_run  # lazy import to avoid circular
    paths, _ = load_run(root, dag.run_id)
    out = paths.run_dir / PLAN_DAG_FILE

    if expected_version is not None and out.exists():
        try:
            on_disk_version = json.loads(out.read_text(encoding="utf-8")).get("version", 0)
        except Exception:
            on_disk_version = 0
        if on_disk_version != expected_version:
            raise RuntimeError(
                f"DAG CAS conflict for '{dag.run_id}': "
                f"expected version {expected_version}, disk has {on_disk_version}. "
                "Reload the DAG and retry."
            )

    dag.version = (dag.version or 0) + 1
    data = {
        "schema_version": dag.schema_version,
        "version": dag.version,
        "run_id": dag.run_id,
        "task": dag.task,
        "intent": dag.intent,
        "created_at": dag.created_at,
        "steps": _steps_to_dicts(dag.steps),
    }
    atomic_write(out, json.dumps(data, ensure_ascii=False, indent=2))
    return out


def load_dag(root: Path, run_id: str | None = None) -> PlanDAG | None:
    from .harness import load_run  # lazy import
    try:
        paths, _ = load_run(root, run_id)
    except FileNotFoundError:
        return None
    dag_path = paths.run_dir / PLAN_DAG_FILE
    if not dag_path.exists():
        return None
    try:
        data = json.loads(dag_path.read_text(encoding="utf-8"))
        return PlanDAG(
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            version=data.get("version", 0),
            run_id=data["run_id"],
            task=data.get("task", ""),
            intent=data.get("intent", "unknown"),
            created_at=data.get("created_at", ""),
            steps=_steps_from_dicts(data.get("steps", [])),
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_dag(run_id: str, task: str, intent: str) -> PlanDAG:
    template = DAG_TEMPLATES.get(intent, DAG_TEMPLATES["planning"])
    import copy
    steps = copy.deepcopy(template)
    return PlanDAG(
        schema_version=SCHEMA_VERSION,
        version=0,
        run_id=run_id,
        task=task,
        intent=intent,
        created_at=now_iso(),
        steps=steps,
    )


# ---------------------------------------------------------------------------
# State transitions
# ---------------------------------------------------------------------------

def update_step(dag: PlanDAG, step_id: str, **kwargs: Any) -> None:
    """Mutate step fields in place."""
    step = dag.by_id(step_id)
    if step is None:
        raise ValueError(f"step '{step_id}' not found in DAG")
    for k, v in kwargs.items():
        object.__setattr__(step, k, v) if hasattr(step, k) else None
        setattr(step, k, v)


def auto_close_barriers(dag: PlanDAG) -> list[str]:
    """Close barriers when all deps are completed or skipped (at least one completed).

    A barrier with ALL deps skipped (e.g., all optional workers failed) stays open —
    there is no useful output to join on.
    """
    closed: list[str] = []
    satisfied = {s.step_id for s in dag.steps if s.status in {"completed", "prepared", "skipped"}}
    completed = {s.step_id for s in dag.steps if s.status in {"completed", "prepared"}}
    for step in dag.steps:
        if step.kind == "barrier" and step.status == "pending":
            deps = step.depends_on
            if deps and all(dep in satisfied for dep in deps) and any(dep in completed for dep in deps):
                step.status = "completed"
                step.finished_at = now_iso()
                closed.append(step.step_id)
    return closed


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

# Maps owner_role → (local_role, provider, provider_role) or special action
_ROLE_MAP: dict[str, tuple[str, str, str] | tuple[str, str, None]] = {
    "local-context-compressor": ("local", "context", None),
    "local-diff-reviewer":      ("local", "review",   None),
    "local-log-summarizer":     ("local", "summarize", None),
    "local-memory-curator":     ("local", "memory",    None),
    "local-classifier":         ("local", "classify",  None),
    "claude-planner":           ("external", "claude", "planner"),
    "claude-reviewer":          ("external", "claude", "reviewer"),
    "codex-executor":           ("external", "codex",  "executor"),
    "codex-reviewer":           ("external", "codex",  "reviewer"),
    "gemini-reviewer":          ("external", "gemini", "reviewer"),
    "gemini-planner":           ("external", "gemini", "planner"),
    "verifier":                 ("builtin", "verify",  None),
    "harness":                  ("builtin", "harness", None),
}


def _read_artifact_status(artifact_path: Path) -> str | None:
    """Read the 'status' field from a result yaml or json artifact."""
    if not artifact_path.exists():
        return None
    try:
        text = artifact_path.read_text(encoding="utf-8")
        if artifact_path.suffix == ".json":
            data = json.loads(text)
            return str(data.get("status", "")) or None
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("status:"):
                return stripped.split(":", 1)[1].strip().strip('"').strip("'") or None
    except Exception:
        pass
    return None


def _read_artifact_confidence(artifact_path: Path) -> float | None:
    if not artifact_path or not artifact_path.exists():
        return None
    try:
        text = artifact_path.read_text(encoding="utf-8")
        if artifact_path.suffix == ".json":
            data = json.loads(text)
            val = data.get("confidence")
            if val is None and isinstance(data.get("output"), dict):
                val = data["output"].get("parsed", {}).get("confidence")
        else:
            val = None
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("confidence:"):
                    try:
                        val = float(stripped.split(":", 1)[1].strip())
                    except ValueError:
                        pass
                    break
        return max(0.0, min(1.0, float(val))) if val is not None else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 5-evaluator helpers (syntax, execution, claim, risk, disagreement)
# ---------------------------------------------------------------------------

_RISK_ORDER: dict[str, int] = {"low": 0, "medium": 1, "high": 2}

_REQUIRED_KEYS_BY_KIND: dict[str, list[str]] = {
    "verify":     ["verdict", "status"],
    "sequential": ["status"],
    "parallel":   ["status"],
    "synthesize": [],
    "barrier":    [],
}


def _evaluate_syntax(step: "PlanStep", artifact_path: "Path | None") -> dict[str, Any]:
    """Syntax evaluator: artifact existence, parseability, required keys."""
    if artifact_path is None:
        no_artifact_required = not step.expected_output_artifacts
        return {
            "schema_valid": no_artifact_required,
            "artifact_exists": False,
            "artifact_parseable": False,
            "missing_keys": [],
        }
    if not artifact_path.exists():
        return {"schema_valid": False, "artifact_exists": False, "artifact_parseable": False, "missing_keys": []}
    parseable = False
    missing_keys: list[str] = []
    try:
        text = artifact_path.read_text(encoding="utf-8")
        if artifact_path.suffix == ".json":
            data = json.loads(text)
            parseable = isinstance(data, dict)
            required = _REQUIRED_KEYS_BY_KIND.get(step.kind, [])
            missing_keys = [k for k in required if k not in data]
        else:
            parseable = ":" in text and len(text.strip()) > 0
    except Exception:
        pass
    return {
        "schema_valid": parseable and not missing_keys,
        "artifact_exists": True,
        "artifact_parseable": parseable,
        "missing_keys": missing_keys,
    }


def _evaluate_execution(artifact_status: "str | None") -> dict[str, Any]:
    """Execution evaluator: subprocess success score 0–1."""
    score_map = {"completed": 1.0, "prepared": 1.0, "partial": 0.5, "failed": 0.0}
    score = score_map.get(artifact_status or "", 0.5 if artifact_status else 0.0)
    return {"execution_score": score, "artifact_status": artifact_status}


def _evaluate_claim(artifact_path: "Path | None") -> dict[str, Any]:
    """Claim evaluator: unsupported-claim count (heuristic from artifact fields)."""
    unsupported = 0
    evidence_score = 1.0
    if artifact_path and artifact_path.exists():
        try:
            text = artifact_path.read_text(encoding="utf-8")
            if artifact_path.suffix == ".json":
                data = json.loads(text)
                conf = data.get("confidence")
                if conf is not None:
                    conf_f = float(conf)
                    if conf_f < 0.5:
                        unsupported += 1
                        evidence_score = min(evidence_score, conf_f)
                unsupported += int(data.get("unsupported_claims", 0))
                if data.get("should_escalate") or data.get("needs_human_or_claude_review"):
                    unsupported += 1
        except Exception:
            pass
    return {"evidence_score": max(0.0, min(1.0, evidence_score)), "unsupported_claims": unsupported}


def _evaluate_risk(step: "PlanStep") -> dict[str, Any]:
    """Risk evaluator: irreversibility, write access, security concerns."""
    factors: list[str] = []
    if step.owner_role in {"codex-executor"}:
        factors.append("write_access")
    if step.permission_mode in {"workspace_write_with_policy"}:
        factors.append("filesystem_write")
    if step.owner_role in {"claude-planner", "claude-reviewer", "gemini-planner", "gemini-reviewer"}:
        factors.append("provider_cost")
    if step.kind == "verify" and step.on_failure == "escalate":
        factors.append("gate_step")
    if "write_access" in factors or "filesystem_write" in factors:
        level = "high"
    elif factors:
        level = "medium"
    else:
        level = "low"
    return {"risk_level": level, "risk_factors": factors}


def _evaluate_disagreement(dag: "PlanDAG", step: "PlanStep") -> dict[str, Any]:
    """Disagreement evaluator: conflicts among parallel siblings with overlapping deps."""
    siblings = [
        s for s in dag.steps
        if s.step_id != step.step_id
        and set(s.depends_on) & set(step.depends_on)
        and s.status in {"completed", "prepared", "failed"}
        and s.kind == "parallel"
    ]
    my_success = step.status in {"completed", "prepared"}
    conflicting = [s.step_id for s in siblings if (s.status == "failed") != (not my_success)]
    return {"disagreement_count": len(conflicting), "disagreement_targets": conflicting}


def _recommend_action(
    step: "PlanStep",
    syntax: dict[str, Any],
    execution: dict[str, Any],
    claim: dict[str, Any],
    risk: dict[str, Any],
    disagreement: dict[str, Any],
    confidence: "float | None",
    accept_if: dict[str, Any],
    escalate_if: dict[str, Any],
) -> tuple[str, bool, str]:
    """Return (recommended_action, escalation_triggered, escalation_reason)."""
    action = "accept"
    triggered = False
    parts: list[str] = []

    # Execution failure overrides everything
    if execution["execution_score"] == 0.0:
        action = "block" if step.on_failure == "stop" else "skip"
        triggered = True
        parts.append(f"execution_failed(status={execution['artifact_status']})")
        return action, triggered, "; ".join(parts)

    # accept_if checks (schema, risk ceiling, disagreement ceiling)
    if accept_if.get("schema_valid", True) and not syntax["schema_valid"]:
        action = "escalate" if step.on_failure == "stop" else "skip"
        triggered = True
        parts.append("schema_invalid")

    risk_below = accept_if.get("risk_below", "high")
    if _RISK_ORDER.get(risk["risk_level"], 0) >= _RISK_ORDER.get(risk_below, 2):
        action = "add_review"
        triggered = True
        parts.append(f"risk={risk['risk_level']} not_below {risk_below}")

    disagree_below = accept_if.get("disagreement_below", 2)
    if disagreement["disagreement_count"] >= disagree_below:
        action = "referee"
        triggered = True
        parts.append(f"disagreement_count={disagreement['disagreement_count']}>={disagree_below}")

    # escalate_if checks
    conf_threshold = escalate_if.get("confidence_below", 0.4)
    if confidence is not None and confidence < conf_threshold:
        action = "retry"
        triggered = True
        parts.append(f"confidence={confidence:.2f}<{conf_threshold}")

    risk_above = escalate_if.get("risk_level_above", "high")
    if _RISK_ORDER.get(risk["risk_level"], 0) > _RISK_ORDER.get(risk_above, 2):
        action = "add_review"
        triggered = True
        parts.append(f"risk={risk['risk_level']}>{risk_above}")

    claims_threshold = escalate_if.get("unsupported_claims_above", 1)
    if claim["unsupported_claims"] > claims_threshold:
        action = "escalate"
        triggered = True
        parts.append(f"unsupported_claims={claim['unsupported_claims']}>{claims_threshold}")

    disagree_with = escalate_if.get("disagreement_with", [])
    if disagree_with and any(t in disagreement["disagreement_targets"] for t in disagree_with):
        action = "referee"
        triggered = True
        parts.append(f"disagreement_with={disagree_with}")

    return action, triggered, "; ".join(parts)


# ---------------------------------------------------------------------------
# Evaluator vote helpers (P2)
# ---------------------------------------------------------------------------

def _provider_for_step(step: "PlanStep") -> str:
    _map = {
        "claude-planner": "claude", "claude-reviewer": "claude",
        "codex-executor": "codex",  "codex-reviewer": "codex",
        "gemini-planner": "gemini", "gemini-reviewer": "gemini",
    }
    return _map.get(step.owner_role, "local")


def _compute_evaluator_votes(
    step: "PlanStep",
    syntax: dict[str, Any],
    execution: dict[str, Any],
    claim: dict[str, Any],
    risk: dict[str, Any],
    disagreement: dict[str, Any],
    confidence: "float | None",
    accept_if: dict[str, Any],
    escalate_if: dict[str, Any],
) -> dict[str, str]:
    """Each evaluator independently casts a vote (accept/retry/escalate/add_review/referee/block/skip)."""
    votes: dict[str, str] = {}

    # syntax
    votes["syntax"] = "accept" if syntax["schema_valid"] else (
        "escalate" if step.on_failure == "stop" else "skip"
    )

    # execution
    score = execution["execution_score"]
    if score >= 0.8:
        votes["execution"] = "accept"
    elif score >= 0.4:
        votes["execution"] = "retry"
    else:
        votes["execution"] = "block" if step.on_failure == "stop" else "skip"

    # claim
    claims_threshold = escalate_if.get("unsupported_claims_above", 1)
    if claim["unsupported_claims"] > claims_threshold:
        votes["claim"] = "escalate"
    elif claim["evidence_score"] < 0.6:
        votes["claim"] = "retry"
    else:
        votes["claim"] = "accept"

    # risk
    level = risk["risk_level"]
    risk_below = accept_if.get("risk_below", "high")
    if _RISK_ORDER.get(level, 0) >= _RISK_ORDER.get(risk_below, 2):
        votes["risk"] = "add_review"
    else:
        votes["risk"] = "accept"

    # disagreement
    disagree_below = accept_if.get("disagreement_below", 2)
    if disagreement["disagreement_count"] >= disagree_below:
        votes["disagreement"] = "referee"
    elif confidence is not None and confidence < escalate_if.get("confidence_below", 0.4):
        votes["disagreement"] = "retry"
    else:
        votes["disagreement"] = "accept"

    return votes


def _compute_agreement(votes: dict[str, str], recommended_action: str) -> float:
    """Fraction of evaluators that agree with the final recommended_action."""
    if not votes:
        return 1.0
    matching = sum(1 for v in votes.values() if v == recommended_action)
    return round(matching / len(votes), 2)


# ---------------------------------------------------------------------------
# StepEvaluation artifact persistence (P1)
# ---------------------------------------------------------------------------

def save_step_evaluation(root: "Path", run_id: str, step_id: str, evaluation: dict[str, Any]) -> Path:
    """Write evaluation to .runs/<run_id>/step_evaluations/<step_id>.json."""
    from .harness import load_run  # lazy
    paths, _ = load_run(root, run_id)
    evals_dir = paths.run_dir / "step_evaluations"
    evals_dir.mkdir(exist_ok=True)
    out = evals_dir / f"{step_id}.json"
    out.write_text(json.dumps(evaluation, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def evaluate_step_output(root: "Path", dag: "PlanDAG", step: "PlanStep") -> dict[str, Any]:
    """Compute a 5-dimensional StepEvaluation for a completed/prepared/failed step.

    Evaluators: syntax (schema), execution (subprocess), claim (evidence),
    risk (irreversibility), disagreement (cross-step conflict).

    observe-only: recommended_action is logged to dag_mutations.jsonl but does NOT
    mutate the DAG. Pass mutation_policy.mode = "adaptive" (--adaptive) to enable
    real DAG mutation.
    """
    policy = step.evaluation_policy or {}
    accept_if = policy.get("accept_if", {})
    escalate_if = policy.get("escalate_if", {})
    mutation_mode = policy.get("mutation_policy", {}).get("mode", "observe_only")

    artifact_path = (root / step.artifact) if step.artifact else None
    artifact_status = _read_artifact_status(artifact_path) if artifact_path else step.status
    confidence = _read_artifact_confidence(artifact_path) if artifact_path else None

    syntax      = _evaluate_syntax(step, artifact_path)
    execution   = _evaluate_execution(artifact_status)
    claim       = _evaluate_claim(artifact_path)
    risk        = _evaluate_risk(step)
    disagreement = _evaluate_disagreement(dag, step)

    recommended_action, escalation_triggered, escalation_reason = _recommend_action(
        step, syntax, execution, claim, risk, disagreement,
        confidence, accept_if, escalate_if,
    )

    votes = _compute_evaluator_votes(
        step, syntax, execution, claim, risk, disagreement,
        confidence, accept_if, escalate_if,
    )
    agreement = _compute_agreement(votes, recommended_action)

    # Append to confidence trajectory (P0)
    attempt = len(step.confidence_history) + 1
    if confidence is not None:
        step.confidence_history.append({
            "ts": now_iso(),
            "value": confidence,
            "source": "step_evaluation",
            "attempt": attempt,
            "provider": _provider_for_step(step),
            "role": step.owner_role,
            "artifact": step.artifact,
        })

    # EVI-lite: only meaningful after first retry (P3 seed)
    evi: dict[str, Any] | None = None
    if len(step.confidence_history) >= 2:
        prev = step.confidence_history[-2]["value"]
        curr = step.confidence_history[-1]["value"]
        delta = round(curr - prev, 3)
        evi = {
            "confidence_delta": delta,
            "attempts": attempt,
            "estimated_value": "positive" if delta > 0.05 else ("negative" if delta < -0.05 else "flat"),
            "recommendation": "retry" if delta > 0.05 else ("stop_retry" if delta <= 0 else "accept"),
        }

    evaluation: dict[str, Any] = {
        "evaluated_at": now_iso(),
        # syntax
        "schema_valid": syntax["schema_valid"],
        "artifact_exists": syntax["artifact_exists"],
        "artifact_parseable": syntax["artifact_parseable"],
        # execution
        "execution_score": execution["execution_score"],
        "artifact_status": artifact_status,
        # claim
        "evidence_score": claim["evidence_score"],
        "unsupported_claims": claim["unsupported_claims"],
        # risk
        "risk_level": risk["risk_level"],
        "risk_factors": risk["risk_factors"],
        # disagreement
        "disagreement_count": disagreement["disagreement_count"],
        "disagreement_targets": disagreement["disagreement_targets"],
        # synthesis
        "confidence": confidence,
        "evaluator_votes": votes,
        "evaluator_agreement": agreement,
        "recommended_action": recommended_action,
        "escalation_triggered": escalation_triggered,
        "escalation_reason": escalation_reason,
        "mutation_mode": mutation_mode,
        "evi": evi,
    }
    step.evaluation = evaluation

    try:
        save_step_evaluation(root, dag.run_id, step.step_id, evaluation)
    except Exception:
        pass  # artifact write is best-effort; never block pipeline

    if escalation_triggered:
        _log_dag_mutation(root, dag.run_id, step.step_id, evaluation)

    return evaluation


def _log_dag_mutation(root: "Path", run_id: str, trigger_step: str, evaluation: dict[str, Any]) -> None:
    """Append a no-op mutation record to dag_mutations.jsonl (observe-only mode)."""
    from .harness import load_run  # lazy
    try:
        paths, _ = load_run(root, run_id)
    except Exception:
        return
    mutations_path = paths.run_dir / "dag_mutations.jsonl"

    recommended = evaluation.get("recommended_action", "accept")
    would_insert_map = {
        "add_review": "gemini-reviewer",
        "escalate": "claude-claim-auditor",
        "referee": "referee",
    }
    record = {
        "ts": now_iso(),
        "run_id": run_id,
        "trigger_step": trigger_step,
        "recommended_action": recommended,
        "would_insert": would_insert_map.get(recommended),
        "reason": evaluation.get("escalation_reason", ""),
        "confidence": evaluation.get("confidence"),
        "risk_level": evaluation.get("risk_level"),
        "active": False,    # --adaptive not enabled
        "decision": "observe_only",
    }
    with mutations_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def execute_step(
    root: Path,
    dag: PlanDAG,
    step_id: str,
    execute: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """Execute one step. Updates step status in dag. Caller must call save_dag after.

    force=True bypasses the transition guard and overwrites any live lease.
    Use only for --retry and operator recovery flows.
    """
    from .dag_state import StepLease, guard_transition
    from .harness import (
        build_memory_draft,
        build_summary,
        build_verification,
        invoke_external_agent,
        invoke_local,
        load_run,
    )

    step = dag.by_id(step_id)
    if step is None:
        return {"ok": False, "error": f"step '{step_id}' not found"}

    # Terminal-state idempotency check (before guard so it's always fast)
    if step.status == "completed":
        return {"ok": True, "step_id": step_id, "status": "already_completed"}

    if step.kind == "barrier":
        closed = auto_close_barriers(dag)
        if step_id in closed:
            return {"ok": True, "step_id": step_id, "status": "barrier_closed"}
        missing = [dep for dep in step.depends_on if dag.status_of(dep) != "completed"]
        return {"ok": False, "step_id": step_id, "status": "barrier_waiting", "waiting_on": missing}

    # Status transition guard
    try:
        guard_transition(step_id, step.status, "running", force=force)
    except ValueError as exc:
        return {"ok": False, "step_id": step_id, "status": "transition_blocked", "error": str(exc)}

    # Acquire step lease
    try:
        lease = StepLease.acquire(root, dag.run_id, step_id)
    except RuntimeError as exc:
        return {"ok": False, "step_id": step_id, "status": "lease_conflict", "error": str(exc)}

    paths, state = load_run(root, dag.run_id)
    step.status = "running"
    step.started_at = now_iso()

    try:
        mapping = _ROLE_MAP.get(step.owner_role)
        if mapping is None:
            raise ValueError(f"No executor mapping for owner_role='{step.owner_role}'")

        kind, a, b = mapping

        if kind == "local":
            artifact_path = invoke_local(root, a, run_id=dag.run_id)
        elif kind == "external":
            assert b is not None
            artifact_path = invoke_external_agent(root, a, b, run_id=dag.run_id, execute=execute)
        elif kind == "builtin":
            if a == "verify":
                artifact_path = build_verification(root, dag.run_id)
            elif step.kind == "synthesize":
                build_summary(root, dag.run_id)
                artifact_path = build_memory_draft(root, dag.run_id)
            else:
                # harness/intake — already completed at dag creation
                guard_transition(step_id, "running", "completed", force=force)
                step.status = "completed"
                step.finished_at = now_iso()
                lease.release()
                return {"ok": True, "step_id": step_id, "status": "completed",
                        "idempotency_key": lease.idempotency_key}
        else:
            raise ValueError(f"Unknown executor kind: {kind}")

        artifact_status = _read_artifact_status(artifact_path)
        if artifact_status == "failed":
            new_status = "failed" if step.on_failure == "stop" else "skipped"
            guard_transition(step_id, "running", new_status, force=force)
            step.status = new_status
            step.finished_at = now_iso()
            step.artifact = artifact_path.relative_to(root).as_posix()
            evaluation = evaluate_step_output(root, dag, step)
            lease.release()
            return {
                "ok": False, "step_id": step_id, "status": step.status,
                "artifact": step.artifact, "error": "artifact reported status=failed",
                "recommended_action": evaluation.get("recommended_action"),
                "idempotency_key": lease.idempotency_key,
            }
        # "prepared" = prompt ready, human must execute; "completed" = subprocess ran.
        new_status = "prepared" if (not execute and artifact_status == "prepared") else "completed"
        guard_transition(step_id, "running", new_status, force=force)
        step.status = new_status
        step.finished_at = now_iso()
        step.artifact = artifact_path.relative_to(root).as_posix()
        evaluation = evaluate_step_output(root, dag, step)
        auto_close_barriers(dag)
        lease.release()
        return {
            "ok": True, "step_id": step_id, "status": step.status,
            "artifact": step.artifact,
            "recommended_action": evaluation.get("recommended_action"),
            "confidence": evaluation.get("confidence"),
            "risk_level": evaluation.get("risk_level"),
            "idempotency_key": lease.idempotency_key,
        }

    except Exception as exc:
        new_status = "failed" if step.on_failure == "stop" else "skipped"
        step.status = new_status
        step.finished_at = now_iso()
        evaluation = evaluate_step_output(root, dag, step)
        lease.release()
        return {
            "ok": False, "step_id": step_id, "status": step.status, "error": str(exc),
            "recommended_action": evaluation.get("recommended_action"),
        }


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_STATUS_ICON = {
    "completed": "✓",
    "failed":    "✗",
    "running":   "▶",
    "pending":   "○",
    "skipped":   "–",
    "blocked":   "⊘",
    "barrier_closed": "✓",
    "unknown":   "?",
}

_KIND_LABEL = {
    "sequential": "seq ",
    "parallel":   "par ",
    "barrier":    "bar ",
    "verify":     "vrfy",
    "synthesize": "syn ",
}


def format_dag(dag: PlanDAG, root: Path | None = None) -> str:
    lines = [
        f"Plan DAG — run: {dag.run_id}",
        f"Task:   {dag.task}",
        f"Intent: {dag.intent}",
        "",
        f"{'ID':<20} {'KIND':<5} {'STATUS':<12} {'EVAL':<8} {'OWNER ROLE':<28} DEPS",
    ]
    lines.append("─" * 100)
    for step in dag.steps:
        icon = _STATUS_ICON.get(step.status, "?")
        kind = _KIND_LABEL.get(step.kind, step.kind[:5])
        deps = ", ".join(step.depends_on) if step.depends_on else "—"
        eval_hint = ""
        if step.evaluation:
            action = step.evaluation.get("recommended_action", "")
            conf = step.evaluation.get("confidence")
            risk = step.evaluation.get("risk_level", "")
            agreement = step.evaluation.get("evaluator_agreement")
            conf_str = f"{conf:.2f}" if conf is not None else "—"
            agr_str = f"/{agreement:.0%}" if agreement is not None else ""
            _action_icon = {
                "accept": "✓", "retry": "↺", "escalate": "↑",
                "add_review": "+R", "referee": "⚖", "block": "⊘",
                "skip": "–", "ask_user": "?",
            }.get(action, "?")
            risk_icon = {"high": "H", "medium": "M", "low": ""}.get(risk, "")
            eval_hint = f"{_action_icon}{conf_str}{risk_icon}{agr_str}"
        lines.append(f"{icon} {step.step_id:<18} {kind} {step.status:<12} {eval_hint:<8} {step.owner_role:<28} {deps}")
    lines.append("")
    next_step = dag.next_sequential()
    if dag.is_complete():
        lines.append("All steps complete.")
    elif dag.is_blocked():
        failed = [s.step_id for s in dag.steps if s.status == "failed"]
        lines.append(f"Blocked — failed steps: {', '.join(failed)}")
    elif next_step:
        provider_hint = "/".join(next_step.provider_candidates) or "harness"
        lines.append(f"Next:  hive step run {next_step.step_id}  [{next_step.owner_role} via {provider_hint}]")
    return "\n".join(lines)
