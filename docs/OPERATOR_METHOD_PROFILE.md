# Operator Method Profile

Status: private alpha system context.

This is the redacted method profile Hive Mind should give to intent classifiers,
task decomposers, debate prompts, and context builders. It captures the working
style, not raw Claude/Codex session contents.

## Working Loop

1. Classify the user's intent before choosing tools.
2. Split broad requests into ordered tasks with explicit blockers.
3. Keep project boundaries visible, especially Hive Mind vs MemoryOS vs CapabilityOS.
4. Use Claude-style critique for conceptual risk, claim discipline, and security review.
5. Use Codex-style execution for filesystem edits, commands, tests, and reproducible logs.
6. Use local LLMs for cheap first-pass classification, JSON normalization, extraction, and summaries.
7. Preserve disagreement instead of forcing early consensus.
8. Convert decisions into artifacts, TODOs, tests, and memory-ready summaries.
9. Verify with commands before calling work complete.
10. Only escalate to public/release state after privacy, security, docs, and reproducibility gates pass.

## Debate Loop

For topics requiring judgment:

```text
topic
  -> every selected provider gives an independent first position
  -> stop until all selected providers reached prepared/completed/failed
  -> every selected provider reviews the combined first-round snapshot
  -> stop again until all selected providers reached a terminal state
  -> Hive Mind writes convergence, disagreement, risks, and next action
```

Hive Mind acts as the chair. Providers are participants: they make arguments,
review each other, and expose disagreement. The chair controls turn order,
barriers, artifact discipline, convergence, and the next action.

## Routing Bias

- Security, privacy, production claims, and public release decisions require Claude review.
- Implementation tasks require Codex or Claude Code execution artifacts.
- Local model outputs are drafts unless schema-valid, evidence-linked, and low-risk.
- If provider opinions conflict, produce a disagreement log and choose the smallest reversible next action.

## Session Sources

Local raw session stores are private inputs, not publishable artifacts:

- Codex: `~/.codex/sessions/` and `~/.codex/history.jsonl`
- Claude: `~/.claude/projects/`, `~/.claude/sessions/`, and `~/.claude/history.jsonl`

Do not commit raw sessions, credentials, or provider transcripts. Extract only
redacted method patterns into this profile or MemoryOS review drafts.
