# Local LLM Workers

MemoryOS uses local LLMs as a cheap cognitive worker layer, not as the final judge.

```text
Local LLM = worker / filter / compressor
Claude or GPT = judge / architect / synthesis
Codex or Claude Code = executor / integration
MemoryOS = durable memory and context provider
```

## Current Runtime State

As of 2026-05-02 KST:

- `ollama`: installed locally at `.local/ollama/bin/ollama`.
- `llama-server`: not installed.
- `llama-cli`: not installed.
- `llm-checker`: available through `npx`.
- Hardware: 2x RTX 5090, 64 GiB total VRAM.
- Pulled models: `qwen3:1.7b`, `qwen3:8b`, `deepseek-coder:6.7b`, `deepseek-coder-v2:16b`.

Use the workspace-local wrappers so model paths stay inside this repo:

```bash
scripts/start-ollama-local.sh
scripts/ollama-local.sh list
```

## Worker Roles

Use:

```bash
python -m memoryos.cli local-workers list
python -m memoryos.cli local-workers status
```

Current workers:

- `classifier`: short snippet -> routing, memory type candidates, escalation hints.
- `memory_extractor`: conversation segment -> reviewable memory draft JSON.
- `context_compressor`: retrieved context -> compact Claude/Codex handoff pack.
- `handoff_drafter`: request + context -> implementation handoff draft.
- `log_summarizer`: run logs/test output -> change summary and memory candidates.
- `capability_extractor`: README/docs -> CapabilityOS TechnologyCard draft.
- `diff_reviewer`: git diff/test output -> first-pass risk review.

## Model Routing

Use several local models by task difficulty:

| Complexity | Model | Use |
| --- | --- | --- |
| tiny | `qwen3:1.7b` | simple tags and duplicate candidates only; avoid for schema-critical JSON |
| `fast` / `default` | `qwen3:8b` | memory extraction, context compression, summaries, handoff drafts |
| coding default | `deepseek-coder:6.7b` | code/test log summarization and error triage |
| `strong` | `deepseek-coder-v2:16b` | harder local reasoning, design comparison, local review drafts |

CLI workers accept `--complexity fast|default|strong`, or an explicit `--model`.

The preferred interface is role-based:

```bash
python -m memoryos.cli local classify --input docs/local_llm_use.md
python -m memoryos.cli local extract-memory --input docs/local_llm_use.md
python -m memoryos.cli local extract-capability --input docs/local_llm_use.md
python -m memoryos.cli local compress-context --input runs/work_items/INTEGRATED_EXECUTION_PLAN.md
python -m memoryos.cli local draft-handoff --input runs/work_items/INTEGRATED_EXECUTION_PLAN.md --complexity strong
python -m memoryos.cli local summarize-log --input runs/work_items/INTEGRATED_EXECUTION_PLAN.md
python -m memoryos.cli local review-diff --input runs/local_workers/diff.txt --complexity strong
```

## Prompt Rendering

Render a schema-first prompt without calling a model:

```bash
python -m memoryos.cli local-workers prompt memory_extractor \
  --input docs/localllm.md \
  --max-chars 8000 \
  --out runs/local_workers/localllm_memory_extractor.prompt.txt
```

This is useful even before Ollama is installed. Claude/Codex can inspect or reuse the prompt.

## Ollama Runtime Path

Once Ollama is installed and a model is pulled:

```bash
scripts/start-ollama-local.sh
scripts/ollama-local.sh pull qwen3:8b
python -m memoryos.cli local-workers run memory_extractor \
  --input docs/localllm.md \
  --model qwen3:8b \
  --out runs/local_workers/localllm_memory_draft.json
```

Or route by complexity:

```bash
python -m memoryos.cli local compress-context \
  --input docs/localllm.md \
  --complexity fast
```

Recommended initial models from `llm-checker`:

- General / cheap worker: `qwen3:8b`.
- Coding-oriented worker: `deepseek-coder:6.7b`.
- Larger local reasoning worker: `deepseek-coder-v2:16b`.
- Reading / lightweight classification: `qwen3:1.7b`.

Smoke-test outputs are written under `runs/local_workers/`.

## Escalation Rules

Escalate local worker output to Claude/GPT when:

- confidence is below `0.75`;
- output changes project state;
- the item is a decision, security/privacy issue, schema migration, or architecture tradeoff;
- local workers disagree;
- source evidence is missing;
- user-facing final prose is needed.

Escalate to Codex/Claude Code when:

- repo edits are required;
- tests must be run;
- parser/worker implementation is needed;
- multi-file refactor or integration is required.

## Logging For Future Fine-Tuning

Keep these pairs for future local model tuning:

```text
input segment
local worker draft
Claude/Codex corrected version
user accepted/rejected state
final committed memory
```

Targets:

- `conversation segment -> memory draft JSON`
- `README/docs -> TechnologyCard JSON`
- `request + context -> handoff draft JSON`
- `run log -> execution summary JSON`
