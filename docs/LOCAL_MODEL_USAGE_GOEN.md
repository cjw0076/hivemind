# Local Model Usage For GoEN Reviews

Date: 2026-05-04

This note records how local models were used from Hive Mind to review the GoEN phase plan. It is meant as an operational recipe for future agents, not as a claim that local models make final research decisions.

## Runtime

Run from the Hive Mind repo:

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
scripts/start-ollama-local.sh
```

In another shell:

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
python -m hivemind.hive local status
scripts/ollama-local.sh list
```

The workspace-local Ollama wrapper sets:

```text
OLLAMA_HOST=127.0.0.1:11434
OLLAMA_MODELS=/home/user/workspaces/jaewon/myworld/hivemind/.local/ollama/models
```

Use the wrappers instead of a global `ollama` binary, because this machine may not have `ollama` on `PATH`.

## Current GoEN Review Roles

| Model | Role | Good for | Do not use for |
|---|---|---|---|
| `qwen3:1.7b` | fast checklist worker | missing fields, route sanity, simple schema gaps | deep architecture judgment, final decisions |
| `qwen3:8b` | handoff clarity reviewer | phase legibility, artifact naming, future-agent confusion | code-level correctness as final authority |
| `deepseek-coder:6.7b` | code/logging risk reviewer | script ambiguity, logging/accounting gaps, runnable TODO issues | broad paper strategy or final design calls |
| `deepseek-coder-v2:16b` | intended deeper code review worker | larger diff review, architecture/code review draft | use only after runtime health check; it failed during the 2026-05-04 GoEN review |

Local model output is advisory. Codex/Claude/user make final calls.

## Generic Direct CLI Pattern

From the GoEN repo:

```bash
cd /home/user/workspaces/jaewon/_from_desktop/GoEN

prompt=$(
  printf '%s\n' \
    'Review TODO.md for GoEN.' \
    'Return final bullets only.' \
    'No hidden reasoning, no chain-of-thought.' \
    'Focus on concrete missing TODO items, risky ordering, logging/schema gaps, and implementation ambiguity.'
  printf '\n--- TODO.md ---\n'
  sed -n '1,360p' TODO.md
)

/home/user/workspaces/jaewon/myworld/hivemind/scripts/ollama-local.sh run qwen3:8b "$prompt"
```

CLI output can include terminal control sequences. For durable notes, summarize the useful bullets manually into a review artifact rather than storing raw output.

## Generic JSON API Pattern

The Ollama API is cleaner when the model is stable:

```bash
cd /home/user/workspaces/jaewon/_from_desktop/GoEN

{
  printf '%s\n' \
    'Review TODO.md for GoEN.' \
    'Return final bullets only.' \
    'No hidden reasoning, no chain-of-thought.'
  printf '\n--- TODO.md ---\n'
  sed -n '1,360p' TODO.md
} | jq -Rs --arg model 'qwen3:8b' \
  '{model:$model,prompt:.,stream:false,options:{temperature:0.2,num_predict:900}}' \
  | curl -s http://127.0.0.1:11434/api/generate -d @- \
  | jq -r '.response'
```

If `.response` is `null`, inspect the raw JSON for an `error` field.

## Model-Specific Prompts

### `qwen3:1.7b`

Use as a quick missing-field scan.

```bash
cd /home/user/workspaces/jaewon/_from_desktop/GoEN

prompt=$(
  printf '%s\n' \
    'You are a fast checklist worker.' \
    'Review TODO.md and return 5 bullets max.' \
    'Find missing fields, ambiguous artifact names, and phase handoff confusion.' \
    'No chain-of-thought. Final bullets only.'
  printf '\n--- TODO.md ---\n'
  sed -n '1,260p' TODO.md
)

/home/user/workspaces/jaewon/myworld/hivemind/scripts/ollama-local.sh run qwen3:1.7b "$prompt"
```

Expected useful output:

- missing schema fields
- missing artifact names
- unclear phase dependencies
- future-agent confusion points

### `qwen3:8b`

Use for handoff clarity and phase-plan readability.

```bash
cd /home/user/workspaces/jaewon/_from_desktop/GoEN

prompt=$(
  printf '%s\n' \
    'You are reviewing a shared execution plan for Codex, Claude, and local LLM workers.' \
    'Return final bullets only.' \
    'Find unclear phase order, missing artifacts, and acceptance criteria that are not executable.' \
    'No chain-of-thought.'
  printf '\n--- TODO.md ---\n'
  sed -n '1,420p' TODO.md
)

/home/user/workspaces/jaewon/myworld/hivemind/scripts/ollama-local.sh run qwen3:8b "$prompt"
```

Expected useful output:

- phase lock issues
- artifact naming gaps
- acceptance criteria ambiguity
- missing policy files or ledger hooks

### `deepseek-coder:6.7b`

Use for code/logging/script risk review.

```bash
cd /home/user/workspaces/jaewon/_from_desktop/GoEN

prompt=$(
  printf '%s\n' \
    'You are a code and experiment-harness reviewer.' \
    'Review TODO.md for implementation ambiguity.' \
    'Return final bullets only.' \
    'Focus on logging schema, crash handling, run reproducibility, and impossible tasks.' \
    'No chain-of-thought.'
  printf '\n--- TODO.md ---\n'
  sed -n '1,420p' TODO.md
)

/home/user/workspaces/jaewon/myworld/hivemind/scripts/ollama-local.sh run deepseek-coder:6.7b "$prompt"
```

Expected useful output:

- missing `summary.csv` / `failure.csv` fields
- pre/post rewire logging gaps
- controller comparison pitfalls
- ambiguous metrics such as `unitary_penalty`

### `deepseek-coder-v2:16b`

Use only after checking runtime health:

```bash
cd /home/user/workspaces/jaewon/myworld/hivemind
scripts/ollama-local.sh list
python -m hivemind.hive local benchmark --model deepseek-coder-v2:16b --role diff_review --timeout 180
```

If healthy, use it for larger code-review drafts:

```bash
cd /home/user/workspaces/jaewon/_from_desktop/GoEN

prompt=$(
  printf '%s\n' \
    'You are a senior local code-review draft worker.' \
    'Review TODO.md as if you will later inspect stability_sweep.py.' \
    'Return final bullets only.' \
    'Focus on architecture/code review risks, schema gaps, and risky phase ordering.' \
    'No chain-of-thought.'
  printf '\n--- TODO.md ---\n'
  sed -n '1,420p' TODO.md
)

/home/user/workspaces/jaewon/myworld/hivemind/scripts/ollama-local.sh run deepseek-coder-v2:16b "$prompt"
```

Known issue from 2026-05-04:

```text
Error: 500 Internal Server Error: llama runner process has terminated: %!w(<nil>)
```

If this repeats, do not block GoEN work on this model. Record the failure and continue with `qwen3:8b` plus `deepseek-coder:6.7b`.

## Capturing Results Back Into GoEN

For GoEN reviews, write the consolidated notes to:

```text
/home/user/workspaces/jaewon/_from_desktop/GoEN/ai_shared/LOCAL_LLM_TODO_REVIEW.md
```

Recommended structure:

```text
Models Called
Consolidated Feedback
Per-Model Notes
Codex Decision
```

Only incorporate concrete, testable feedback into `TODO.md`. Do not copy local model speculation into the execution plan unless Codex/Claude/user accepts it.

## Escalation

Escalate to Claude when:

- the feedback changes the research claim
- the model criticizes phase ordering
- topology transfer, memory, STDP, sleep, or neuromodulation claims are involved

Escalate to Codex when:

- code edits are needed
- run artifact schema must be implemented
- tests/smoke runs are required
- local model output contradicts actual repository behavior
