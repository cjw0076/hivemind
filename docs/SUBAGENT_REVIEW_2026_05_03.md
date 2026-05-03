# Subagent Review: Product Hardening

Date: 2026-05-03 KST

Context: Codex launched three read-only subagents to pressure-test Hive Mind:
`hive.verifier`, `hive.product_evaluator`, and `persona.actual_user`.

## Verifier

Verdict: provider CLI auto-execution remains blocked by default, but the first
auto-loop implementation had validation and trust gaps.

Findings:

- High: `hive loop` wrote `auto_loop_step_executed` and `auto_loop_ready` event
  types that were missing from the run validation taxonomy.
- Medium: product eval used `pip wheel .` from the repo root, leaving generated
  `build/` output.
- Medium: product eval route checks primarily exercised heuristic routing, not
  semantic route quality.
- Low: persona/evaluator/verifier roles existed, but their review outputs were
  not captured as durable artifacts.

Follow-up applied:

- Added auto-loop event types to validation.
- Added failed-agent state validation.
- Made auto-loop stop after failed local actions instead of retrying and calling
  them created artifacts.
- Added `--out -` and temp source copy wheel builds to product eval.
- Added this subagent review artifact.

## Product Evaluator

Verdict: Hive Mind is better than the user's manual shared-folder workflow as a
structured artifact ledger and coordination shell. It is not yet better as the
semantic chair that replaces the user's dispatch/referee work. Direct
Codex/Claude remains faster for small tasks.

Key points:

- Strength: fixed run artifacts, provider prompts/results, validation, memory
  drafts, transcripts, and next actions beat loose folders for traceability.
- Weakness: routing is still too heuristic/test-shaped.
- Weakness: debate/convergence records are mostly scaffolding until
  `disagreements.json` and convergence scoring exist.
- Weakness: MemoryOS accepted-memory integration is still placeholder-level.

P0 recommendations:

1. Add real `disagreements.json`.
2. Add schema-validated route quality and provider fallback.
3. Make `hive next` a crisp operator decision surface.
4. Implement read-only chair artifacts first.
5. Add baseline eval against direct agents and manual shared-folder runs.

## Actual User Persona

Verdict: for a simple coding task, the persona would still use direct
Codex/Claude. For a long multi-agent run, the persona would consider Hive Mind
as an audit/control ledger.

Pain points:

- `hive ask` returns a file path instead of a readable answer.
- `--root` ordering and command differences hurt discoverability.
- `verify` was less trustworthy than `audit` when local worker state failed.
- `hive loop` was safe but not smart enough before the failed-action fix.
- Korean prompts route, but operator summaries are mostly English.
- TUI observer/read-only behavior and quit semantics need clearer affordances.

Keep-using threshold:

- `hive "task"` should return a concise plan, artifact links, and next safe
  command.
- Failed workers must affect `next`, `verify`, and `loop`.
- Korean-first summaries should appear when the prompt is Korean.
- Auto-loop must stop on repeated or failed action and escalate.
