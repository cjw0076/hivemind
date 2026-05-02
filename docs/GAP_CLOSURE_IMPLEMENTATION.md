# Hive Mind Gap Closure Implementation

Status: public alpha implementation note.

Source gap report: `docs/HIVE_MIND_GAPS.md`, mirrored from
`../memoryOS/docs/shared/HIVE_MIND_GAPS.md`.

## Chair Model

Hive Mind is the chair of the provider society. It does not try to be the
smartest participant. It controls turn order, waits for barriers, records
conflict, writes convergence, and proposes the next action.

## Implemented Loop

`hive gaps` now builds the minimum artifact layer needed to resolve the
MemoryOS-side gaps:

- `artifacts/memory_context.json`: pre-run MemoryOS context hook and provenance.
- `artifacts/semantic_verification.json`: objective, acceptance, scope, and provider-result checks.
- `artifacts/handoff_quality.json`: handoff completeness gate.
- `artifacts/routing_evidence.json`: provider assignment evidence.
- `artifacts/conflict_set.json`: cross-agent conflict and reviewer assignment surface.
- `artifacts/operator_decisions.json`: prioritized next actions for the operator.
- `artifacts/gap_closure.json`: index over the above artifacts.

`hive next` now refreshes the gap artifacts before choosing the top operator
decision, so the next action is grounded in current run state instead of only
the pipeline checklist.

## Remaining Limits

The MemoryOS pre-run context command is currently a planned integration point.
Hive Mind records the intended command and root, but it does not import accepted
MemoryOS memories until the sibling MemoryOS repo exposes a stable context
builder.

Semantic verification is deterministic and artifact-based for now. High-risk
runs should still assign Claude or another reviewer for judgment until an LLM
semantic verifier is wired into policy.

Conflict detection currently starts with provider result status/risk and output
previews. The next step is real disagreement extraction from executed provider
outputs.

## Work Log

- Added `hive debate` for chaired provider first-opinion, review, and convergence artifacts.
- Added `docs/OPERATOR_METHOD_PROFILE.md` so intent routing and task decomposition inherit the user/Claude/Codex/local-LLM working method without committing raw sessions.
- Identified raw local session stores: `~/.codex/sessions`, `~/.codex/history.jsonl`, `~/.claude/projects`, `~/.claude/sessions`, and `~/.claude/history.jsonl`.
- Added public-release security fixes from Claude review: license, safe folder opening, env/data/model ignores, private data README, workbench eval contract note, and Ollama Docker port validation.
- Added `hive gaps` and updated `hive next` to build the learning-operator-loop artifacts.
