# Hive Mind Product Evaluation

Date: 2026-05-03 KST

Status: product smoke passed; production claim still blocked.

## Evidence

- `npm test`: 80 tests passed.
- `git diff --check`: passed.
- `python scripts/hive-product-eval.py --out -`: 20/20 checks passed in 103,617 ms without
  writing a repo report file or leaving `build/`.
- `python scripts/hive-product-eval.py --deep --out -`: 21/21 checks passed in
  110,778 ms.
- Local evidence artifacts:
  - `runs/reports/hive-product-eval.json`
  - `runs/reports/hive-product-eval-deep.json`
- Subagent review artifact: `docs/SUBAGENT_REVIEW_2026_05_03.md`

The product eval builds a wheel, installs it into a clean venv, runs the
installed `hive` CLI against a clean workspace, then verifies onboarding,
doctor, Korean/English routing, provider prompt preparation, run validation,
next-action output, and auto-loop safety behavior.

## Packaging Verdict

Hive Mind is packageable as a private/public alpha CLI. The clean installed CLI
can initialize a workspace, detect runtime state, route common task shapes,
prepare provider artifacts, and validate a run.

It is not production-grade yet. The remaining blocker is not packaging. The
blocker is product quality: semantic routing, disagreement extraction,
convergence quality, high-risk verification, and smoother operator ergonomics.

## Versus Manual Shared-Folder Coordination

Hive Mind is already better where the manual shared-folder method is weak:

- run state is structured instead of implied by recent files;
- next action is computed from artifacts;
- provider prompts, commands, and result schemas are durable;
- verification and memory drafts have fixed locations;
- packaging and smoke evaluation are reproducible;
- dry-run/prepare-only defaults reduce accidental provider execution.

The manual method is still better in one important way: human judgment is fast
and semantically rich. Hive Mind does not yet reliably replace the user's role
as dispatcher, referee, drift detector, and convergence enforcer.

## Versus Direct Single-Agent Use

For a small coding task, direct Codex or Claude is still faster and less
ceremonial.

Hive Mind earns its overhead only when the work is multi-agent, long-running, or
risk-sensitive: provider debate, handoff, traceability, MemoryOS integration,
auditability, and repeatable run closure.

Current verdict: Hive Mind is not yet "월등" in raw task performance. It is
better as a coordination substrate and evidence ledger.

## UX Verdict

The operator UX is usable for alpha:

- `hive "task"` and `hive ask` create useful artifacts;
- `hive live` has prompt/log status without a terminal dashboard;
- `hive next`, `hive status`, `hive agents status`, and `hive memory list` give
  a workable command-line loop;
- `hive loop` now gives an option-only chair loop for repetitive run hygiene.

It is not yet the final Hive Mind north-star UX. The system still needs stronger
route-quality scoring, structured disagreement surfaces, turn arbitration,
front state, and semantic verification before it clearly beats the user's
manual multi-agent workflow end to end.

## Subagent Verdicts

Verifier:

- Provider CLI auto-execution remains blocked by default.
- `hive loop` needed event taxonomy coverage and failed-action handling; both
  were patched after review.
- Product eval needed a stdout-only path and temp source wheel build to avoid
  dirtying the repo during read-only evaluation; patched.

Product evaluator:

- Hive Mind is valuable as a coordination ledger.
- It is not yet a semantic chair that replaces user dispatch/referee work.
- Direct agents still win for small tasks.

Actual user persona:

- Best entrypoint is bare `hive "task"`.
- `hive ask` returning only a path is too opaque.
- Failed workers must affect `next`, `verify`, and `loop`.
- Korean prompts work at input/routing level, but Korean operator summaries are
  still missing.

## Auto-Loop Safety

`hive loop` is deliberately narrow:

- default: dry-run only;
- execution: requires `--execute` plus repeated `--allow <action>`;
- allowlisted internal actions: `audit`, `verify`, `memory-draft`, `summarize`,
  `diff`, `check-run`, `local-context`, `local-review`;
- blocked: Claude/Codex/Gemini provider CLI execution, arbitrary shell commands,
  memory commit, and new prompt/routing boundaries.

This is enough for self-judgment over run hygiene without turning the chair into
an unsafe autopilot.

## DAG Runtime Assessment

The new `plan_dag.py` runtime is directionally correct for the user's actual
work pattern: it records sequential dependencies, parallel fan-out candidates,
barrier joins, owner roles, permission modes, expected artifacts, and durable
step status.

Verified CLI surface:

- `hive plan dag --intent implementation`
- `hive step list`
- `hive step next`
- `hive step run <step-id>`
- DAG-aware `hive next`

Current limitation: the executor still advances one step at a time. Parallel
steps are marked in the schema, but `hive step run` chooses one runnable step,
then the next. A true Hive Mind loop needs a bounded fan-out runner that starts
all safe runnable parallel steps, waits at the barrier, and only then advances.

Blocking safety concern: the current Claude execute path uses
`--dangerously-skip-permissions` to avoid non-TTY empty output. That may be a
useful diagnostic workaround, but it conflicts with the public-alpha safety
gate unless it is moved behind an explicit danger policy, isolated runner, or
replaced with a safer non-interactive Claude contract.

Execution correctness concern: `execute_step()` should inspect local/provider
result artifacts before marking a step `completed`. A failed local worker should
be `failed` or `skipped` according to `on_failure`, and barriers should apply
clear completed/skipped rules instead of assuming every produced artifact means
success.

## Next Product P0

1. Policy-gate or replace the unsafe Claude execute workaround before adding
   broader automation.
2. Harden DAG step result handling: local/provider failures must not become
   completed steps.
3. Reconcile `hive flow` and `plan_dag.json` into one scheduler surface.
4. Add bounded parallel fan-out plus barrier join for safe internal/local
   steps first, provider execution later.
5. Add schema-validated route-quality scoring and provider fallback.
6. Extract structured disagreements from executed provider outputs.
7. Make `hive "task"` and `hive ask` return a readable plan plus next command,
   not only artifact paths.
8. Add convergence scoring and front/turn arbitration.
9. Add semantic verifier review for high-risk runs.
10. Keep testing Hive Mind against the real baseline: direct agents and the
   user's shared-folder collaboration method.
