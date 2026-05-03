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


@dataclass
class PlanDAG:
    schema_version: int
    run_id: str
    task: str
    intent: str
    created_at: str
    steps: list[PlanStep]

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
    return [PlanStep(**d) for d in dicts]


def save_dag(root: Path, dag: PlanDAG) -> Path:
    from .harness import load_run  # lazy import to avoid circular
    paths, _ = load_run(root, dag.run_id)
    out = paths.run_dir / PLAN_DAG_FILE
    data = {
        "schema_version": dag.schema_version,
        "run_id": dag.run_id,
        "task": dag.task,
        "intent": dag.intent,
        "created_at": dag.created_at,
        "steps": _steps_to_dicts(dag.steps),
    }
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
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


def execute_step(
    root: Path,
    dag: PlanDAG,
    step_id: str,
    execute: bool = False,
) -> dict[str, Any]:
    """Execute one step. Updates step status in dag. Caller must call save_dag after."""
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

    if step.status == "completed":
        return {"ok": True, "step_id": step_id, "status": "already_completed"}

    if step.kind == "barrier":
        closed = auto_close_barriers(dag)
        if step_id in closed:
            return {"ok": True, "step_id": step_id, "status": "barrier_closed"}
        missing = [dep for dep in step.depends_on if dag.status_of(dep) != "completed"]
        return {"ok": False, "step_id": step_id, "status": "barrier_waiting", "waiting_on": missing}

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
                step.status = "completed"
                step.finished_at = now_iso()
                return {"ok": True, "step_id": step_id, "status": "completed"}
        else:
            raise ValueError(f"Unknown executor kind: {kind}")

        artifact_status = _read_artifact_status(artifact_path)
        if artifact_status == "failed":
            step.status = "failed" if step.on_failure == "stop" else "skipped"
            step.finished_at = now_iso()
            step.artifact = artifact_path.relative_to(root).as_posix()
            return {
                "ok": False, "step_id": step_id, "status": step.status,
                "artifact": step.artifact, "error": f"artifact reported status=failed",
            }
        # "prepared" = prompt ready, human must execute; "completed" = subprocess ran.
        step.status = "prepared" if (not execute and artifact_status == "prepared") else "completed"
        step.finished_at = now_iso()
        step.artifact = artifact_path.relative_to(root).as_posix()
        auto_close_barriers(dag)
        return {"ok": True, "step_id": step_id, "status": step.status, "artifact": step.artifact}

    except Exception as exc:
        step.status = "failed" if step.on_failure == "stop" else "skipped"
        step.finished_at = now_iso()
        return {"ok": False, "step_id": step_id, "status": step.status, "error": str(exc)}


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
        f"{'ID':<20} {'KIND':<5} {'STATUS':<12} {'OWNER ROLE':<28} DEPS",
    ]
    lines.append("─" * 90)
    for step in dag.steps:
        icon = _STATUS_ICON.get(step.status, "?")
        kind = _KIND_LABEL.get(step.kind, step.kind[:5])
        deps = ", ".join(step.depends_on) if step.depends_on else "—"
        lines.append(f"{icon} {step.step_id:<18} {kind} {step.status:<12} {step.owner_role:<28} {deps}")
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
