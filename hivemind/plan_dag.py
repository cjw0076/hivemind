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
from .workloop import (
    append_execution_ledger,
    capture_worktree_snapshot,
    relative_artifact,
    touched_files_between,
)
from .protocol import (
    approved_decision_for_step,
    cast_vote,
    create_proof,
    step_requires_protocol_decision,
)

PLAN_DAG_FILE = "plan_dag.json"
SCHEMA_VERSION = 1

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

@dataclass
class StepCriterion:
    """Typed acceptance criterion for a probe step.

    criterion_type:
      "artifact_field_check"  — navigate field.path OP value in an artifact
      "command_exit"          — run shell command; pass if exit code == 0
      "local_worker_eval"     — call a local Ollama worker; pass if not failed
      "human_review"          — block until operator writes an _override.json
    """
    criterion_type: str
    criterion_value: str   # "field OP val" | command | worker_name | review prompt
    evaluator: str | None = None
    timeout: int = 60
    on_failure: str = "block"  # "block" | "escalate" | "warn"


@dataclass
class PlanStep:
    step_id: str
    kind: str  # sequential | parallel | barrier | verify | synthesize | probe
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

    # Reversibility gradient: 0.0=irreversible, 1.0=fully reversible.
    # "default" → not yet estimated; "declared" → set by operator; "estimated" → auto-computed.
    reversibility: float = 1.0
    reversibility_source: str = "default"  # "default" | "declared" | "estimated"
    reversibility_factors: list[str] = field(default_factory=list)

    # Typed acceptance criteria for probe steps (kind="probe").
    # Empty list = trivially passes.
    typed_criteria: list[StepCriterion] = field(default_factory=list)


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
    steps = []
    for d in dicts:
        raw = {k: v for k, v in d.items() if k in known}
        if "typed_criteria" in raw and isinstance(raw["typed_criteria"], list):
            raw["typed_criteria"] = [
                StepCriterion(**c) if isinstance(c, dict) else c
                for c in raw["typed_criteria"]
            ]
        steps.append(PlanStep(**raw))
    return steps


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


ACTION_OWNER_ROLES: dict[tuple[str, str], str] = {
    ("local", "context"): "local-context-compressor",
    ("local", "context-compressor"): "local-context-compressor",
    ("local", "review"): "local-diff-reviewer",
    ("local", "diff-reviewer"): "local-diff-reviewer",
    ("local", "summarize"): "local-log-summarizer",
    ("local", "log-summarizer"): "local-log-summarizer",
    ("local", "memory"): "local-memory-curator",
    ("local", "memory-curator"): "local-memory-curator",
    ("local", "classify"): "local-classifier",
    ("local", "handoff"): "local-handoff-drafter",
    ("local", "handoff-drafter"): "local-handoff-drafter",
    ("claude", "planner"): "claude-planner",
    ("claude", "reviewer"): "claude-reviewer",
    ("codex", "executor"): "codex-executor",
    ("codex", "reviewer"): "codex-reviewer",
    ("gemini", "planner"): "gemini-planner",
    ("gemini", "reviewer"): "gemini-reviewer",
}


def build_dag_from_actions(
    run_id: str,
    task: str,
    intent: str,
    actions: list[dict[str, Any]],
) -> PlanDAG:
    """Build a lifecycle DAG from the router's provider/role actions.

    This is the prompt-entry bridge: the intent router owns role selection, and
    the DAG owns lifecycle state, ledger/probe/evaluation, and supervisor steps.
    """
    if not actions:
        return build_dag(run_id, task, intent)
    steps: list[PlanStep] = [
        _step(
            "intake",
            "sequential",
            [],
            "harness",
            [],
            permission_mode="none",
            expected_output_artifacts=["task.yaml"],
            timeout=0,
            on_failure="stop",
            status="completed",
        )
    ]
    previous = "intake"
    used_ids = {"intake"}
    for action in actions:
        provider = str(action.get("provider") or "").strip().lower()
        role = str(action.get("role") or "").strip().lower()
        owner_role = ACTION_OWNER_ROLES.get((provider, role))
        if not owner_role:
            continue
        step_id = unique_step_id(f"{provider}_{role}", used_ids)
        used_ids.add(step_id)
        permission = "read_only" if provider == "local" else ("plan" if provider == "claude" else "read_only")
        if provider == "codex" and role == "executor":
            permission = "workspace_write_with_policy"
        steps.append(
            _step(
                step_id,
                "sequential",
                [previous],
                owner_role,
                [provider] if provider else [],
                permission_mode=permission,
                input_artifacts=action_input_artifacts(provider, role),
                expected_output_artifacts=action_output_artifacts(provider, role),
                acceptance_criteria=[str(action.get("reason") or "role action completes")],
                timeout=600 if provider in {"claude", "codex", "gemini"} else 120,
                on_failure="escalate" if provider in {"claude", "codex", "gemini"} else "skip",
            )
        )
        previous = step_id
    if len(steps) == 1:
        return build_dag(run_id, task, intent)
    steps.extend(_shared_tail([previous]))
    return PlanDAG(
        schema_version=SCHEMA_VERSION,
        version=0,
        run_id=run_id,
        task=task,
        intent=intent,
        created_at=now_iso(),
        steps=steps,
    )


def unique_step_id(base: str, used: set[str]) -> str:
    clean = "".join(ch if ch.isalnum() else "_" for ch in base).strip("_") or "step"
    candidate = clean
    index = 2
    while candidate in used:
        candidate = f"{clean}_{index}"
        index += 1
    return candidate


def action_input_artifacts(provider: str, role: str) -> list[str]:
    if provider == "local" and role in {"summarize", "log-summarizer", "review", "diff-reviewer"}:
        return ["events.jsonl"]
    if provider == "local" and role in {"handoff", "handoff-drafter"}:
        return ["task.yaml"]
    if provider == "codex":
        return ["handoff.yaml"]
    return ["context_pack.md"]


def action_output_artifacts(provider: str, role: str) -> list[str]:
    if provider == "local":
        return [f"agents/local/{role.replace('-', '_')}.json"]
    return [f"agents/{provider}/{role}_result.yaml"]


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
    "local-handoff-drafter":    ("local", "handoff",   None),
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
# Reversibility gradient
# ---------------------------------------------------------------------------

# Pre-execution gates
REVERSIBILITY_BLOCK_THRESHOLD   = 0.1   # < 0.1 → block; irreversible without force
REVERSIBILITY_REVIEW_THRESHOLD  = 0.3   # < 0.3 → add_review in risk evaluator

# Roles that perform writes get a lower baseline
_ROLE_REVERSIBILITY_BASELINE: dict[str, float] = {
    "codex-executor":         0.5,
    "harness":                1.0,
    "verifier":               1.0,
}

_PERMISSION_REVERSIBILITY_PENALTY: dict[str, float] = {
    "workspace_write_with_policy": -0.3,
    "plan":                        -0.1,
    "read_only":                    0.0,
    "none":                         0.0,
}

# (regex_pattern, score_impact) — scanned against input artifact text
_DESTRUCTIVE_PATTERNS: list[tuple[str, str, float]] = [
    ("drop_table",        r"(?i)\bDROP\s+TABLE\b",    -0.3),
    ("delete_from",       r"(?i)\bDELETE\s+FROM\b",   -0.15),
    ("drop_database",     r"(?i)\bDROP\s+DATABASE\b", -0.5),
    ("rm_recursive_force", r"\brm\s+-[^\s]*[rf][^\s]*", -0.4),
    ("shutil_rmtree",     r"shutil\.rmtree\s*\(",     -0.3),
    ("path_unlink",       r"\.unlink\s*\(",           -0.1),
    ("os_remove",         r"os\.remove\s*\(",         -0.15),
    ("truncate",          r"(?i)\btruncate\b",        -0.1),
]


def _estimate_reversibility(step: "PlanStep", root: "Path", run_id: str | None = None) -> tuple[float, list[str]]:
    """Return (score, factors) where score ∈ [0.0, 1.0].

    Score is driven down by write permissions, risky owner roles, and
    destructive operation patterns found in input artifacts.
    """
    import re

    score: float = _ROLE_REVERSIBILITY_BASELINE.get(step.owner_role, 1.0)
    factors: list[str] = []

    penalty = _PERMISSION_REVERSIBILITY_PENALTY.get(step.permission_mode, 0.0)
    if penalty < 0:
        score += penalty
        factors.append(f"permission={step.permission_mode}")

    for artifact_rel in step.input_artifacts:
        artifact_path = root / artifact_rel
        if not artifact_path.exists() and run_id:
            run_artifact_path = root / ".runs" / run_id / artifact_rel
            if run_artifact_path.exists():
                artifact_path = run_artifact_path
        if not artifact_path.exists():
            continue
        try:
            text = artifact_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for label, pattern, impact in _DESTRUCTIVE_PATTERNS:
            if re.search(pattern, text):
                score += impact
                factors.append(f"destructive_pattern:{label}")

    return max(0.0, min(1.0, round(score, 2))), factors


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

    # Reversibility gradient factors (only meaningful once estimated)
    if step.reversibility_source != "default":
        if step.reversibility < REVERSIBILITY_BLOCK_THRESHOLD:
            factors.append("low_reversibility")
        elif step.reversibility < REVERSIBILITY_REVIEW_THRESHOLD:
            factors.append("medium_reversibility")

    if "write_access" in factors or "filesystem_write" in factors or "low_reversibility" in factors:
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


# ---------------------------------------------------------------------------
# Disagreement topology
# ---------------------------------------------------------------------------

_EVIDENCE_AXIS_THRESHOLD = 0.3   # min evidence score gap to flag divergence

# Priority order for escalation override (never de-escalate)
_RECOMMEND_ORDER: dict[str, int] = {
    "accept": 0, "retry": 1, "add_review": 2,
    "escalate": 3, "referee": 4, "block": 5, "skip": 5,
}


def _load_sibling_evaluation(root: "Path", run_id: str, sibling_id: str) -> dict[str, Any] | None:
    """Load persisted step_evaluations/<sibling_id>.json, best-effort."""
    try:
        from .harness import load_run
        paths, _ = load_run(root, run_id)
        path = paths.run_dir / "step_evaluations" / f"{sibling_id}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None


def _detect_axes(
    step: "PlanStep",
    sibling: "PlanStep",
    step_eval: dict[str, Any] | None,
    sibling_eval: dict[str, Any] | None,
) -> list[str]:
    """Return which disagreement axes are active between step and sibling."""
    axes: list[str] = []

    step_ok = step.status in {"completed", "prepared"}
    sib_ok  = sibling.status in {"completed", "prepared"}
    if step_ok != sib_ok:
        axes.append("conclusion")

    step_ev = (step_eval or {}).get("evidence_score")
    sib_ev  = (sibling_eval or {}).get("evidence_score")
    if step_ev is not None and sib_ev is not None:
        if abs(step_ev - sib_ev) > _EVIDENCE_AXIS_THRESHOLD:
            axes.append("evidence")

    step_risk = (step_eval or {}).get("risk_level")
    sib_risk  = (sibling_eval or {}).get("risk_level")
    if step_risk and sib_risk and step_risk != sib_risk:
        axes.append("risk_assessment")

    step_action = (step_eval or {}).get("recommended_action")
    sib_action  = (sibling_eval or {}).get("recommended_action")
    if step_action and sib_action and step_action != sib_action:
        axes.append("approach")

    return axes


def _topology_recommended_action(topology_type: str, severity: str, axes: list[str]) -> str:
    if severity == "none" or topology_type == "clean":
        return "accept"
    if severity == "high" or topology_type == "distributed":
        return "referee"
    if "conclusion" in axes or "risk_assessment" in axes:
        return "referee" if severity == "medium" else "add_review"
    if severity == "medium":
        return "add_review"
    return "retry"


def _evaluate_disagreement_topology(
    dag: "PlanDAG",
    step: "PlanStep",
    root: "Path",
    run_id: str,
    step_eval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return axis-level disagreement topology.

    step_eval is the current evaluation dict (pass the freshly computed dict so
    axis detection uses up-to-date evidence/risk/approach values).
    """
    siblings = [
        s for s in dag.steps
        if s.step_id != step.step_id
        and set(s.depends_on) & set(step.depends_on)
        and s.status in {"completed", "prepared", "failed"}
        and s.kind == "parallel"
    ]
    step_ok = step.status in {"completed", "prepared"}
    conflicting = [s for s in siblings if (s.status == "failed") != (not step_ok)]

    if not conflicting:
        return {
            "disagreement_count": 0,
            "disagreement_targets": [],
            "observations": [],
            "axes": [],
            "dominant_axis": None,
            "topology_type": "clean",
            "severity": "none",
            "topology_recommended_action": "accept",
        }

    observations: list[dict[str, Any]] = []
    axis_counter: dict[str, int] = {}

    for sibling in conflicting:
        sib_eval = sibling.evaluation or _load_sibling_evaluation(root, run_id, sibling.step_id)
        axes = _detect_axes(step, sibling, step_eval, sib_eval)
        for ax in axes:
            axis_counter[ax] = axis_counter.get(ax, 0) + 1
        observations.append({
            "sibling_id": sibling.step_id,
            "axes": axes,
            "step_status": step.status,
            "sibling_status": sibling.status,
            "step_recommended": (step_eval or {}).get("recommended_action"),
            "sibling_recommended": (sib_eval or {}).get("recommended_action"),
            "step_risk": (step_eval or {}).get("risk_level"),
            "sibling_risk": (sib_eval or {}).get("risk_level"),
            "step_evidence_score": (step_eval or {}).get("evidence_score"),
            "sibling_evidence_score": (sib_eval or {}).get("evidence_score"),
        })

    all_axes = sorted({ax for obs in observations for ax in obs["axes"]})
    dominant = max(axis_counter, key=lambda k: axis_counter[k]) if axis_counter else None

    n = len(conflicting)
    if n == 1:
        ttype = "isolated"
    elif len(all_axes) > 1:
        ttype = "distributed"
    else:
        ttype = "split"

    if ttype == "distributed" or len(all_axes) >= 3:
        severity = "high"
    elif "conclusion" in all_axes or "risk_assessment" in all_axes:
        severity = "medium"
    else:
        severity = "low"

    return {
        "disagreement_count": n,
        "disagreement_targets": [s.step_id for s in conflicting],
        "observations": observations,
        "axes": all_axes,
        "dominant_axis": dominant,
        "topology_type": ttype,
        "severity": severity,
        "topology_recommended_action": _topology_recommended_action(ttype, severity, all_axes),
    }


def _write_disagreement_record(
    root: "Path",
    run_id: str,
    step_id: str,
    topology: dict[str, Any],
) -> None:
    """Append a disagreement record to .runs/<run_id>/disagreements.json."""
    from .dag_state import atomic_write
    from .harness import load_run
    try:
        paths, _ = load_run(root, run_id)
        dis_path = paths.run_dir / "disagreements.json"
        record: dict[str, Any] = {
            "ts": now_iso(),
            "run_id": run_id,
            "step_id": step_id,
            "topology_type": topology["topology_type"],
            "severity": topology["severity"],
            "axes": topology["axes"],
            "dominant_axis": topology["dominant_axis"],
            "disagreement_count": topology["disagreement_count"],
            "disagreement_targets": topology["disagreement_targets"],
            "topology_recommended_action": topology["topology_recommended_action"],
        }
        existing: list[Any] = []
        if dis_path.exists():
            try:
                existing = json.loads(dis_path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []
        existing.append(record)
        atomic_write(dis_path, json.dumps(existing, ensure_ascii=False, indent=2))
    except Exception:
        pass


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

    # Disagreement topology (uses current evaluation for richer axis detection)
    topology = _evaluate_disagreement_topology(dag, step, root, dag.run_id, step_eval=evaluation)
    topo_action = topology["topology_recommended_action"]
    if _RECOMMEND_ORDER.get(topo_action, 0) > _RECOMMEND_ORDER.get(evaluation["recommended_action"], 0):
        evaluation["recommended_action"] = topo_action
        evaluation["escalation_triggered"] = True
        note = f"topology={topology['topology_type']}({topology['severity']})"
        evaluation["escalation_reason"] = (
            f"{evaluation['escalation_reason']}; {note}".lstrip("; ")
        )
    evaluation["disagreement_topology"] = topology
    if topology["disagreement_count"] > 0:
        _write_disagreement_record(root, dag.run_id, step.step_id, topology)

    try:
        save_step_evaluation(root, dag.run_id, step.step_id, evaluation)
    except Exception:
        pass  # artifact write is best-effort; never block pipeline

    if evaluation["escalation_triggered"]:
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


# ---------------------------------------------------------------------------
# Evaluation-to-protocol bridge
# ---------------------------------------------------------------------------

_EVALUATION_TO_VERIFIER_STATUS: dict[str, str] = {
    "accept":     "passed",
    "retry":      "low_confidence",
    "add_review": "review_required",
    "escalate":   "flagged",
    "referee":    "conflict",
    "block":      "blocked",
    "skip":       "skipped",
}

# evaluator_agreement below this threshold triggers a needs_referee post-vote
_REFEREE_AGREEMENT_THRESHOLD = 0.5


def _evaluation_to_verifier_status(recommended_action: str) -> str:
    return _EVALUATION_TO_VERIFIER_STATUS.get(recommended_action, "not_run")


def _post_execution_bridge(
    root: "Path",
    dag: "PlanDAG",
    step: "PlanStep",
    evaluation: dict[str, Any],
    files_touched: list[str],
) -> None:
    """Best-effort: close protocol loop after evaluation.

    If an approved ExecutionDecision exists for this step, write an
    ExecutionProof with verifier_status derived from the evaluation result.
    If evaluator agreement is below the referee threshold, cast a
    needs_referee post-execution vote so downstream audit can track it.

    Never raises — pipeline must not be blocked by protocol bookkeeping.
    """
    try:
        decision = approved_decision_for_step(root, dag.run_id, step.step_id)
        if decision is None:
            return
        recommended = evaluation.get("recommended_action", "accept")
        verifier_status = _evaluation_to_verifier_status(recommended)
        create_proof(
            root,
            dag.run_id,
            decision.intent_id,
            status=step.status,
            output_path=step.artifact,
            files_touched=files_touched,
            verifier_status=verifier_status,
        )
    except Exception:
        return

    try:
        raw_agreement = evaluation.get("evaluator_agreement", 1.0)
        try:
            agreement = 1.0 if raw_agreement is None else float(raw_agreement)
        except (TypeError, ValueError):
            agreement = 1.0
        recommended = evaluation.get("recommended_action", "accept")
        if recommended == "referee" or agreement < _REFEREE_AGREEMENT_THRESHOLD:
            reasons = [f"evaluator_agreement={agreement:.2f}"]
            if recommended == "referee":
                reasons.append(f"escalation_reason={evaluation.get('escalation_reason', '')}")
            cast_vote(
                root,
                dag.run_id,
                decision.intent_id,
                voter_role="evaluator",
                vote="needs_referee",
                confidence=agreement,
                risk_level=evaluation.get("risk_level"),
                reasons=reasons,
                allow_executor=True,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Probe step execution
# ---------------------------------------------------------------------------

@dataclass
class ProbeResult:
    """Outcome artifact for a probe step evaluation."""
    schema_version: int
    step_id: str
    run_id: str
    criterion_type: str
    criterion_value: str
    status: str           # "completed" | "failed" — _read_artifact_status key
    passed: bool | None   # None = pending human review
    observed: str
    expected: str
    evidence: str
    confidence: float
    failure_disposition: str  # "block" | "escalate" | "warn"
    next_action: str           # "accept" | "block" | "escalate" | "override_pending"
    evaluated_at: str


def save_probe_result(root: Path, run_id: str, step_id: str, result: ProbeResult) -> Path:
    """Write ProbeResult to .runs/<run_id>/step_probes/<step_id>.json."""
    from .harness import load_run
    paths, _ = load_run(root, run_id)
    probes_dir = paths.run_dir / "step_probes"
    probes_dir.mkdir(exist_ok=True)
    out = probes_dir / f"{step_id}.json"
    out.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def _probe_override_path(root: Path, run_id: str, step_id: str) -> Path:
    from .harness import load_run
    paths, _ = load_run(root, run_id)
    return paths.run_dir / "step_probes" / f"{step_id}_override.json"


_FIELD_OPS = [("!=", "!="), (">=", ">="), ("<=", "<="), (">", ">"), ("<", "<"), ("==", "==")]


def _parse_field_criterion(criterion_value: str) -> tuple[str, str, str]:
    """Return (field_path, operator, expected) from criterion_value like 'status == completed'."""
    for op, _ in _FIELD_OPS:
        if op in criterion_value:
            lhs, _, rhs = criterion_value.partition(op)
            return lhs.strip(), op, rhs.strip()
    return criterion_value.strip(), "exists", ""


def _navigate_field(data: Any, field_path: str) -> Any:
    """Navigate dot-separated path in a dict/list structure."""
    current = data
    for part in field_path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            current = current[int(part)]
        else:
            return None
        if current is None:
            return None
    return current


def _compare_field(observed: Any, operator: str, expected: str) -> bool:
    if operator == "exists":
        return observed is not None
    observed_str = str(observed).strip() if observed is not None else ""
    try:
        obs_n, exp_n = float(observed_str), float(expected)
        if operator == "==":  return obs_n == exp_n
        if operator == "!=":  return obs_n != exp_n
        if operator == ">=":  return obs_n >= exp_n
        if operator == "<=":  return obs_n <= exp_n
        if operator == ">":   return obs_n > exp_n
        if operator == "<":   return obs_n < exp_n
    except (ValueError, TypeError):
        pass
    if operator == "==":  return observed_str == expected
    if operator == "!=":  return observed_str != expected
    return False


def _load_probe_artifact(root: Path, run_id: str, step: "PlanStep") -> dict | None:
    """Try to load the step's primary artifact or first input_artifact as a dict."""
    candidates: list[Path] = []
    if step.artifact:
        candidates.append(root / step.artifact)
    for ia in step.input_artifacts:
        candidates.append(root / ".runs" / run_id / ia)
        candidates.append(root / ia)
    for path in candidates:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if path.suffix == ".json":
                return json.loads(text)
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                result: dict[str, Any] = {}
                for line in text.splitlines():
                    if ":" in line and not line.startswith("#") and not line.startswith(" "):
                        k, _, v = line.partition(":")
                        result[k.strip()] = v.strip().strip('"').strip("'")
                if result:
                    return result
        except Exception:
            continue
    return None


def _eval_artifact_field_check(
    root: Path, run_id: str, step: "PlanStep", criterion: StepCriterion,
) -> ProbeResult:
    field_path, operator, expected = _parse_field_criterion(criterion.criterion_value)
    data = _load_probe_artifact(root, run_id, step)
    if data is None:
        return ProbeResult(
            schema_version=1, step_id=step.step_id, run_id=run_id,
            criterion_type="artifact_field_check", criterion_value=criterion.criterion_value,
            status="failed", passed=False,
            observed="no_artifact", expected=expected or field_path,
            evidence=f"no readable artifact found for field check '{criterion.criterion_value}'",
            confidence=0.0, failure_disposition=criterion.on_failure,
            next_action=criterion.on_failure, evaluated_at=now_iso(),
        )
    observed = _navigate_field(data, field_path)
    passed = _compare_field(observed, operator, expected)
    return ProbeResult(
        schema_version=1, step_id=step.step_id, run_id=run_id,
        criterion_type="artifact_field_check", criterion_value=criterion.criterion_value,
        status="completed" if passed else "failed",
        passed=passed,
        observed=str(observed) if observed is not None else "null",
        expected=expected if expected else f"'{field_path}' exists",
        evidence=f"field='{field_path}' observed='{observed}' op='{operator}' expected='{expected}'",
        confidence=1.0 if passed else 0.0,
        failure_disposition=criterion.on_failure,
        next_action="accept" if passed else criterion.on_failure,
        evaluated_at=now_iso(),
    )


def _eval_command_exit(
    root: Path, run_id: str, step: "PlanStep", criterion: StepCriterion,
) -> ProbeResult:
    import subprocess
    try:
        proc = subprocess.run(
            criterion.criterion_value,
            shell=True,
            capture_output=True,
            timeout=criterion.timeout,
            cwd=str(root),
        )
        passed = proc.returncode == 0
        observed = str(proc.returncode)
        stdout = proc.stdout.decode(errors="replace")
        stderr = proc.stderr.decode(errors="replace")
        evidence = (stdout + stderr)[:400].strip() or f"exit_code={proc.returncode}"
    except subprocess.TimeoutExpired:
        passed = False
        observed = "timeout"
        evidence = f"command timed out after {criterion.timeout}s"
    except Exception as exc:
        passed = False
        observed = "error"
        evidence = str(exc)[:200]
    return ProbeResult(
        schema_version=1, step_id=step.step_id, run_id=run_id,
        criterion_type="command_exit", criterion_value=criterion.criterion_value,
        status="completed" if passed else "failed",
        passed=passed, observed=observed, expected="0",
        evidence=evidence,
        confidence=1.0 if passed else 0.0,
        failure_disposition=criterion.on_failure,
        next_action="accept" if passed else criterion.on_failure,
        evaluated_at=now_iso(),
    )


def _eval_local_worker(
    root: Path, run_id: str, step: "PlanStep", criterion: StepCriterion,
) -> ProbeResult:
    try:
        from .harness import invoke_local
        artifact_path = invoke_local(root, criterion.criterion_value, run_id=run_id)
        status = _read_artifact_status(artifact_path)
        passed = status not in {None, "failed"}
        observed = status or "no_status"
        evidence = f"worker={criterion.criterion_value} status={observed}"
    except Exception as exc:
        passed = False
        observed = "error"
        evidence = str(exc)[:200]
    return ProbeResult(
        schema_version=1, step_id=step.step_id, run_id=run_id,
        criterion_type="local_worker_eval", criterion_value=criterion.criterion_value,
        status="completed" if passed else "failed",
        passed=passed, observed=observed, expected="not_failed",
        evidence=evidence,
        confidence=0.8 if passed else 0.2,
        failure_disposition=criterion.on_failure,
        next_action="accept" if passed else criterion.on_failure,
        evaluated_at=now_iso(),
    )


def _eval_human_review(
    root: Path, run_id: str, step: "PlanStep", criterion: StepCriterion,
) -> ProbeResult:
    try:
        override_path = _probe_override_path(root, run_id, step.step_id)
        if override_path.exists():
            override = json.loads(override_path.read_text(encoding="utf-8"))
            if override.get("approved"):
                return ProbeResult(
                    schema_version=1, step_id=step.step_id, run_id=run_id,
                    criterion_type="human_review", criterion_value=criterion.criterion_value,
                    status="completed", passed=True,
                    observed="operator_approved", expected="operator_approved",
                    evidence=f"override: {override.get('notes', '')[:200]}",
                    confidence=1.0, failure_disposition=criterion.on_failure,
                    next_action="accept", evaluated_at=now_iso(),
                )
    except Exception:
        pass
    # No valid override: pending review — step fails to block downstream.
    # Operator writes step_probes/<step_id>_override.json with {"approved": true} then retries.
    return ProbeResult(
        schema_version=1, step_id=step.step_id, run_id=run_id,
        criterion_type="human_review", criterion_value=criterion.criterion_value,
        status="failed", passed=None,
        observed="pending_review", expected="operator_approved",
        evidence=f"review required: {criterion.criterion_value[:200]}",
        confidence=0.0, failure_disposition=criterion.on_failure,
        next_action="override_pending", evaluated_at=now_iso(),
    )


def _run_probe_step(
    root: Path,
    dag: "PlanDAG",
    step: "PlanStep",
    before_snapshot: list[str],
    lease: Any,
    execute: bool,
    force: bool,
) -> dict[str, Any]:
    """Evaluate typed_criteria for a probe step. Called from execute_step."""
    from .dag_state import guard_transition

    step_id = step.step_id
    run_id = dag.run_id

    # Evaluate each criterion
    results: list[ProbeResult] = []
    for criterion in step.typed_criteria:
        if criterion.criterion_type == "artifact_field_check":
            r = _eval_artifact_field_check(root, run_id, step, criterion)
        elif criterion.criterion_type == "command_exit":
            r = _eval_command_exit(root, run_id, step, criterion)
        elif criterion.criterion_type == "local_worker_eval":
            r = _eval_local_worker(root, run_id, step, criterion)
        elif criterion.criterion_type == "human_review":
            r = _eval_human_review(root, run_id, step, criterion)
        else:
            r = ProbeResult(
                schema_version=1, step_id=step_id, run_id=run_id,
                criterion_type=criterion.criterion_type, criterion_value=criterion.criterion_value,
                status="completed", passed=True,
                observed="unknown_type", expected="known_type",
                evidence=f"unknown criterion_type '{criterion.criterion_type}' — treated as warn",
                confidence=0.5, failure_disposition="warn",
                next_action="accept", evaluated_at=now_iso(),
            )
        results.append(r)

    # No criteria → trivial pass
    if not results:
        probe_result = ProbeResult(
            schema_version=1, step_id=step_id, run_id=run_id,
            criterion_type="none", criterion_value="",
            status="completed", passed=True,
            observed="no_criteria", expected="no_criteria",
            evidence="no typed_criteria defined; probe trivially passes",
            confidence=1.0, failure_disposition="block",
            next_action="accept", evaluated_at=now_iso(),
        )
    else:
        blocking = [r for r in results if r.passed is False and r.failure_disposition in {"block", "escalate"}]
        pending  = [r for r in results if r.passed is None]

        if pending:
            agg_passed, agg_status, agg_action = None, "failed", "override_pending"
            agg_evidence = "; ".join(r.evidence for r in pending[:3])
            agg_confidence = 0.0
            agg_disp = pending[0].failure_disposition
        elif blocking:
            agg_passed, agg_status = False, "failed"
            agg_action = blocking[0].next_action
            agg_evidence = "; ".join(r.evidence for r in blocking[:3])
            agg_confidence = min(r.confidence for r in blocking)
            agg_disp = blocking[0].failure_disposition
        else:
            warns = [r for r in results if r.passed is False and r.failure_disposition == "warn"]
            agg_passed, agg_status, agg_action = True, "completed", "accept"
            agg_evidence = ("; ".join(r.evidence for r in warns[:2]) + " [warn only]"
                            if warns else "all criteria passed")
            agg_confidence = min((r.confidence for r in results), default=1.0)
            agg_disp = "warn" if warns else "block"

        probe_result = ProbeResult(
            schema_version=1, step_id=step_id, run_id=run_id,
            criterion_type="aggregate",
            criterion_value=f"{len(results)}_criteria",
            status=agg_status,
            passed=agg_passed,
            observed=str(sum(1 for r in results if r.passed is True)),
            expected=str(len(results)),
            evidence=agg_evidence,
            confidence=agg_confidence,
            failure_disposition=agg_disp,
            next_action=agg_action,
            evaluated_at=now_iso(),
        )

    # Write probe artifact (becomes step.artifact for evaluate_step_output)
    artifact_path = save_probe_result(root, run_id, step_id, probe_result)
    step.artifact = artifact_path.relative_to(root).as_posix()

    # Transition step status
    if probe_result.status == "completed":
        new_status = "completed"
        auto_close_barriers(dag)
    else:
        new_status = "failed" if step.on_failure == "stop" else "skipped"

    guard_transition(step_id, "running", new_status, force=force)
    step.status = new_status
    step.finished_at = now_iso()

    # Standard evaluation + bridge
    evaluation = evaluate_step_output(root, dag, step)
    files_touched = touched_files_between(
        before_snapshot,
        capture_worktree_snapshot(root),
        root=root,
        artifact_path=artifact_path,
    )

    ledger_event = ("step_completed" if new_status == "completed"
                    else "step_failed" if new_status == "failed" else "step_skipped")
    append_execution_ledger(
        root, run_id, ledger_event,
        actor=step.owner_role,
        step_id=step_id,
        status=step.status,
        permission_mode=step.permission_mode,
        bypass_mode="execute" if execute else "prepare",
        files_touched=files_touched,
        artifact=relative_artifact(root, artifact_path),
        extra={
            "probe_action": probe_result.next_action,
            "probe_confidence": probe_result.confidence,
            "criteria_count": len(step.typed_criteria),
        },
    )
    append_execution_ledger(
        root, run_id, "evaluation_complete",
        actor="evaluator",
        step_id=step_id,
        status=evaluation.get("recommended_action", "accept"),
        permission_mode=step.permission_mode,
        bypass_mode="execute" if execute else "prepare",
        extra={
            "confidence": evaluation.get("confidence"),
            "risk_level": evaluation.get("risk_level"),
            "evaluator_agreement": evaluation.get("evaluator_agreement"),
        },
    )
    _post_execution_bridge(root, dag, step, evaluation, files_touched)
    lease.release()

    return {
        "ok": new_status == "completed",
        "step_id": step_id,
        "status": new_status,
        "probe_passed": probe_result.passed,
        "probe_action": probe_result.next_action,
        "probe_confidence": probe_result.confidence,
        "probe_evidence": probe_result.evidence,
        "artifact": step.artifact,
        "files_touched": files_touched,
        "recommended_action": evaluation.get("recommended_action"),
        "idempotency_key": lease.idempotency_key,
    }


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
        append_execution_ledger(
            root,
            dag.run_id,
            "step_idempotent",
            actor=step.owner_role,
            step_id=step_id,
            status="already_completed",
            permission_mode=step.permission_mode,
        )
        return {"ok": True, "step_id": step_id, "status": "already_completed"}

    if step.kind == "barrier":
        closed = auto_close_barriers(dag)
        if step_id in closed:
            append_execution_ledger(
                root,
                dag.run_id,
                "barrier_closed",
                actor=step.owner_role,
                step_id=step_id,
                status="completed",
                permission_mode=step.permission_mode,
                extra={"depends_on": step.depends_on},
            )
            return {"ok": True, "step_id": step_id, "status": "barrier_closed"}
        missing = [dep for dep in step.depends_on if dag.status_of(dep) != "completed"]
        append_execution_ledger(
            root,
            dag.run_id,
            "barrier_waiting",
            actor=step.owner_role,
            step_id=step_id,
            status="waiting",
            permission_mode=step.permission_mode,
            extra={"waiting_on": missing},
        )
        return {"ok": False, "step_id": step_id, "status": "barrier_waiting", "waiting_on": missing}

    # Status transition guard
    try:
        guard_transition(step_id, step.status, "running", force=force)
    except ValueError as exc:
        append_execution_ledger(
            root,
            dag.run_id,
            "step_blocked",
            actor=step.owner_role,
            step_id=step_id,
            status="transition_blocked",
            permission_mode=step.permission_mode,
            message=str(exc),
        )
        return {"ok": False, "step_id": step_id, "status": "transition_blocked", "error": str(exc)}

    if step_requires_protocol_decision(step, execute):
        decision = approved_decision_for_step(root, dag.run_id, step_id)
        if decision is None:
            append_execution_ledger(
                root,
                dag.run_id,
                "step_blocked",
                actor=step.owner_role,
                step_id=step_id,
                status="protocol_gate",
                permission_mode=step.permission_mode,
                bypass_mode="execute",
                message="execute requires approved ExecutionDecision",
            )
            return {
                "ok": False,
                "step_id": step_id,
                "status": "protocol_gate",
                "error": (
                    "execute requires approved ExecutionDecision. "
                    f"Run: hive protocol intent {step_id} --execute"
                ),
            }
        append_execution_ledger(
            root,
            dag.run_id,
            "protocol_decision_used",
            actor="harness",
            step_id=step_id,
            status=decision.decision,
            permission_mode=step.permission_mode,
            bypass_mode="execute",
            extra={"intent_id": decision.intent_id, "conditions": decision.conditions},
        )

    # Acquire step lease
    try:
        lease = StepLease.acquire(root, dag.run_id, step_id)
    except RuntimeError as exc:
        append_execution_ledger(
            root,
            dag.run_id,
            "step_blocked",
            actor=step.owner_role,
            step_id=step_id,
            status="lease_conflict",
            permission_mode=step.permission_mode,
            message=str(exc),
        )
        return {"ok": False, "step_id": step_id, "status": "lease_conflict", "error": str(exc)}

    # Reversibility gate (pre-execution): declared values are operator-owned;
    # auto-estimated values are refreshed every run because input artifacts can
    # change after retries or prior steps.
    if step.reversibility_source in {"default", "estimated"}:
        est, factors = _estimate_reversibility(step, root, dag.run_id)
        step.reversibility = est
        step.reversibility_source = "estimated"
        step.reversibility_factors = factors
    if step.reversibility < REVERSIBILITY_BLOCK_THRESHOLD and not force:
        append_execution_ledger(
            root,
            dag.run_id,
            "step_blocked",
            actor=step.owner_role,
            step_id=step_id,
            status="reversibility_gate",
            permission_mode=step.permission_mode,
            message=f"reversibility={step.reversibility:.2f}",
            extra={
                "reversibility": step.reversibility,
                "reversibility_source": step.reversibility_source,
                "reversibility_factors": step.reversibility_factors,
            },
        )
        lease.release()
        return {
            "ok": False,
            "step_id": step_id,
            "status": "reversibility_gate",
            "reversibility": step.reversibility,
            "reversibility_source": step.reversibility_source,
            "reversibility_factors": step.reversibility_factors,
            "error": (
                f"reversibility={step.reversibility:.2f} below block threshold "
                f"{REVERSIBILITY_BLOCK_THRESHOLD}. Use force=True to override."
            ),
        }

    paths, state = load_run(root, dag.run_id)
    step.status = "running"
    step.started_at = now_iso()
    before_snapshot = capture_worktree_snapshot(root)
    append_execution_ledger(
        root,
        dag.run_id,
        "step_started",
        actor=step.owner_role,
        step_id=step_id,
        status="running",
        permission_mode=step.permission_mode,
        bypass_mode="execute" if execute else "prepare",
        extra={
            "kind": step.kind,
            "execute": execute,
            "force": force,
            "provider_candidates": step.provider_candidates,
            "reversibility": step.reversibility,
            "reversibility_source": step.reversibility_source,
            "reversibility_factors": step.reversibility_factors,
        },
    )

    try:
        # Probe steps: evaluate typed_criteria before normal executor dispatch
        if step.kind == "probe":
            return _run_probe_step(root, dag, step, before_snapshot, lease, execute, force)

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
                files_touched = touched_files_between(
                    before_snapshot,
                    capture_worktree_snapshot(root),
                    root=root,
                )
                append_execution_ledger(
                    root,
                    dag.run_id,
                    "step_completed",
                    actor=step.owner_role,
                    step_id=step_id,
                    status=step.status,
                    permission_mode=step.permission_mode,
                    bypass_mode="execute" if execute else "prepare",
                    files_touched=files_touched,
                )
                lease.release()
                return {"ok": True, "step_id": step_id, "status": "completed",
                        "files_touched": files_touched,
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
            files_touched = touched_files_between(
                before_snapshot,
                capture_worktree_snapshot(root),
                root=root,
                artifact_path=artifact_path,
            )
            append_execution_ledger(
                root,
                dag.run_id,
                "step_failed" if new_status == "failed" else "step_skipped",
                actor=step.owner_role,
                step_id=step_id,
                status=step.status,
                permission_mode=step.permission_mode,
                bypass_mode="execute" if execute else "prepare",
                files_touched=files_touched,
                artifact=relative_artifact(root, artifact_path),
                message="artifact reported status=failed",
                extra={"recommended_action": evaluation.get("recommended_action")},
            )
            append_execution_ledger(
                root,
                dag.run_id,
                "evaluation_complete",
                actor="evaluator",
                step_id=step_id,
                status=evaluation.get("recommended_action", "accept"),
                permission_mode=step.permission_mode,
                bypass_mode="execute" if execute else "prepare",
                extra={
                    "confidence": evaluation.get("confidence"),
                    "risk_level": evaluation.get("risk_level"),
                    "evaluator_agreement": evaluation.get("evaluator_agreement"),
                },
            )
            _post_execution_bridge(root, dag, step, evaluation, files_touched)
            lease.release()
            return {
                "ok": False, "step_id": step_id, "status": step.status,
                "artifact": step.artifact, "error": "artifact reported status=failed",
                "files_touched": files_touched,
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
        files_touched = touched_files_between(
            before_snapshot,
            capture_worktree_snapshot(root),
            root=root,
            artifact_path=artifact_path,
        )
        append_execution_ledger(
            root,
            dag.run_id,
            "step_completed",
            actor=step.owner_role,
            step_id=step_id,
            status=step.status,
            permission_mode=step.permission_mode,
            bypass_mode="execute" if execute else "prepare",
            files_touched=files_touched,
            artifact=relative_artifact(root, artifact_path),
            extra={
                "recommended_action": evaluation.get("recommended_action"),
                "confidence": evaluation.get("confidence"),
                "risk_level": evaluation.get("risk_level"),
            },
        )
        append_execution_ledger(
            root,
            dag.run_id,
            "evaluation_complete",
            actor="evaluator",
            step_id=step_id,
            status=evaluation.get("recommended_action", "accept"),
            permission_mode=step.permission_mode,
            bypass_mode="execute" if execute else "prepare",
            extra={
                "confidence": evaluation.get("confidence"),
                "risk_level": evaluation.get("risk_level"),
                "evaluator_agreement": evaluation.get("evaluator_agreement"),
            },
        )
        _post_execution_bridge(root, dag, step, evaluation, files_touched)
        lease.release()
        return {
            "ok": True, "step_id": step_id, "status": step.status,
            "artifact": step.artifact,
            "files_touched": files_touched,
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
        files_touched = touched_files_between(
            before_snapshot,
            capture_worktree_snapshot(root),
            root=root,
        )
        append_execution_ledger(
            root,
            dag.run_id,
            "step_failed" if new_status == "failed" else "step_skipped",
            actor=step.owner_role,
            step_id=step_id,
            status=step.status,
            permission_mode=step.permission_mode,
            bypass_mode="execute" if execute else "prepare",
            files_touched=files_touched,
            message=str(exc),
            extra={"recommended_action": evaluation.get("recommended_action")},
        )
        append_execution_ledger(
            root,
            dag.run_id,
            "evaluation_complete",
            actor="evaluator",
            step_id=step_id,
            status=evaluation.get("recommended_action", "accept"),
            permission_mode=step.permission_mode,
            bypass_mode="execute" if execute else "prepare",
            extra={
                "confidence": evaluation.get("confidence"),
                "risk_level": evaluation.get("risk_level"),
                "evaluator_agreement": evaluation.get("evaluator_agreement"),
            },
        )
        _post_execution_bridge(root, dag, step, evaluation, files_touched)
        lease.release()
        return {
            "ok": False, "step_id": step_id, "status": step.status, "error": str(exc),
            "files_touched": files_touched,
            "recommended_action": evaluation.get("recommended_action"),
        }


# ---------------------------------------------------------------------------
# Fan-out scheduler
# ---------------------------------------------------------------------------

def execute_fan_out(
    root: Path,
    dag: PlanDAG,
    execute: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    """One round of DAG progression.

    Priority:
      1. If runnable parallel steps exist → dispatch all of them (sequentially
         in this implementation; concurrent dispatch is a later upgrade behind
         the same interface).
      2. After parallel steps complete → auto_close_barriers.
      3. If no parallel steps were runnable → dispatch the next sequential/
         verify/synthesize step (barriers are handled transparently).

    Returns:
      {ok, mode, dispatched, results, barriers_closed, next, dag_complete}

    The caller must call save_dag() after this returns.
    """
    from .dag_state import recover_expired_leases

    append_execution_ledger(
        root,
        dag.run_id,
        "scheduler_round_started",
        actor="harness",
        status="running",
        bypass_mode="execute" if execute else "prepare",
        extra={"force": force},
    )

    # Recover any crashed workers before scheduling
    recovered = recover_expired_leases(root, dag.run_id, dag)

    runnable = dag.runnable()
    parallel_steps = [s for s in runnable if s.kind == "parallel"]

    dispatched: list[str] = []
    results: dict[str, Any] = {}
    mode = "idle"

    if parallel_steps:
        mode = "parallel"
        for step in parallel_steps:
            result = execute_step(root, dag, step.step_id, execute=execute, force=force)
            dispatched.append(step.step_id)
            results[step.step_id] = result

    # Auto-close any barriers whose deps are now satisfied
    closed = auto_close_barriers(dag)

    # If no parallel steps ran, fall through to the next sequential step
    if not parallel_steps:
        next_step = dag.next_sequential()
        if next_step and next_step.kind != "parallel":
            mode = "sequential"
            result = execute_step(root, dag, next_step.step_id, execute=execute, force=force)
            dispatched.append(next_step.step_id)
            results[next_step.step_id] = result
            # Close any barriers that opened after the sequential step
            closed.extend(auto_close_barriers(dag))

    if not dispatched and not closed:
        mode = "idle"

    # ok=False only when a hard stop-failure step actually failed
    any_hard_fail = False
    for r in results.values():
        if r.get("status") == "failed":
            s = dag.by_id(r.get("step_id", ""))
            if s and s.on_failure == "stop":
                any_hard_fail = True
                break
    reversibility_gates = [
        {
            "step_id": r.get("step_id"),
            "reversibility": r.get("reversibility"),
            "source": r.get("reversibility_source"),
            "factors": r.get("reversibility_factors", []),
            "error": r.get("error", ""),
        }
        for r in results.values()
        if r.get("status") == "reversibility_gate"
    ]

    next_step = dag.next_sequential()
    report = {
        "ok": not any_hard_fail,
        "mode": mode,
        "dispatched": dispatched,
        "results": results,
        "barriers_closed": closed,
        "recovered_leases": recovered,
        "reversibility_gates": reversibility_gates,
        "next": next_step.step_id if next_step else None,
        "dag_complete": dag.is_complete(),
        "dag_blocked": dag.is_blocked(),
    }
    append_execution_ledger(
        root,
        dag.run_id,
        "scheduler_round_completed",
        actor="harness",
        status=mode,
        bypass_mode="execute" if execute else "prepare",
        extra={
            "dispatched": dispatched,
            "barriers_closed": closed,
            "recovered_leases": recovered,
            "next": report["next"],
            "dag_complete": report["dag_complete"],
            "dag_blocked": report["dag_blocked"],
        },
    )
    return report


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
