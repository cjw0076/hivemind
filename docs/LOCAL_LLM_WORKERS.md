# Local LLM Workers

Hive Mind uses local LLMs as a cheap worker layer, not as the final judge.

```text
Local LLM = worker / filter / compressor / first-pass reviewer
Claude or GPT = judge / architect / synthesis
Codex or Claude Code = executor / integration
Hive Mind = orchestration, routing, benchmark, policy, and run artifacts
MemoryOS = accepted durable memory after review
CapabilityOS = accepted technology/capability records after review
```

## Current Runtime State

Hive Mind depends on a backend protocol, not on one runtime. The adapter
contract lives in `LOCAL_BACKEND_CONTRACT.md`:

```text
hive-local-backend-v1
  -> render schema-first prompt
  -> send to selected local backend adapter
  -> parse JSON
  -> validate role schema
  -> record model, backend, latency, validity, and failure reason
```

Ollama is only the first convenient adapter. A production install may use
Ollama, llama.cpp, vLLM, Transformers, LM Studio, or another OpenAI-compatible
local server behind the same Hive Mind local worker interface.

As of 2026-05-02 KST on this machine:

- Active adapter for experiments: workspace-local Ollama.
- `llama-server`: not installed.
- `llama-cli`: not installed.
- `llm-checker`: available through `npx`.
- Hardware: 2x RTX 5090, 64 GiB total VRAM.
- Pulled models are detected by `hive local status`; do not assume docs are current.

Optional Ollama adapter helpers:

```bash
scripts/start-ollama-local.sh
scripts/ollama-local.sh list
scripts/ollama-local.sh pull qwen3:1.7b
scripts/hive-local-benchmark.sh qwen3:1.7b
HIVE_LOCAL_BACKEND=ollama HIVE_OLLAMA_MODE=docker scripts/hive-local-benchmark.sh qwen3:1.7b
```

For the concrete GoEN TODO review workflow and model-by-model prompt recipes,
see `LOCAL_MODEL_USAGE_GOEN.md`.

## Worker Roles

Use Hive Mind commands:

```bash
python -m hivemind.hive local routes
python -m hivemind.hive local setup --auto
python -m hivemind.hive local benchmark --role json_normalizer --model qwen3:1.7b
```

Current workers:

- `classifier`: short snippet -> routing, memory type candidates, escalation hints.
- `json_normalizer`: rough local output -> strict JSON for downstream schemas.
- `memory_extractor`: conversation segment -> reviewable MemoryOS draft JSON.
- `context_compressor`: retrieved context -> compact Claude/Codex handoff pack.
- `handoff_drafter`: request + context -> implementation handoff draft.
- `log_summarizer`: run logs/test output -> change summary and memory candidates.
- `capability_extractor`: README/docs -> CapabilityOS TechnologyCard draft.
- `diff_reviewer`: git diff/test output -> first-pass risk review.

## Role Model Matrix

This is the intended routing policy before benchmark calibration:

| Role | Primary local model | Fallback | Escalation |
| --- | --- | --- | --- |
| fast classification | `phi4-mini` | `qwen3:1.7b` only for non-critical fast pass | rare |
| JSON normalizer | `phi4-mini` | `qwen3:8b` | schema failure |
| memory extraction | `phi4-mini` / `qwen3:8b` | `qwen3:1.7b` for simple snippets | Claude for decisions/conflicts |
| capability extraction | `phi4-mini` / `qwen3:8b` | `qwen2.5-coder:7b` for docs | Claude for top items |
| code log summary | `deepseek-coder:6.7b` | `qwen2.5-coder:7b` | Codex when fixes are needed |
| diff review draft | `deepseek-coder-v2:16b` | `qwen2.5-coder:14b` | Claude for high-risk diffs |
| handoff draft | `deepseek-coder-v2:16b` | `qwen3-coder` if available | Claude final review |
| local architecture draft | `deepseek-coder-v2:16b` | `qwen3-coder:30b` | Claude final review |
| implementation | none | none | Codex / Claude Code |
| final product judgment | none | none | Claude / user |

Calibration notes from the first local benchmark run:

- `qwen3:1.7b` was fast but failed strict schemas across tested roles.
- `qwen3:4b` failed JSON parsing in this adapter setup.
- `phi4-mini` passed classify, JSON normalization, memory extraction, and capability extraction.
- `qwen3:8b` passed the same general roles but was slower.
- `deepseek-coder-v2:16b` passed diff review and architecture; handoff JSON was truncated in the smoke test.
- `qwen3-coder:30b` passed architecture; handoff JSON was truncated in the smoke test.

## Benchmark Path

`hive local benchmark` now runs role-specific suites, not only one generic JSON smoke prompt:

```bash
python -m hivemind.hive local benchmark \
  --model qwen3:1.7b \
  --model phi4-mini \
  --backend auto \
  --role classify \
  --role json_normalizer \
  --role memory_extraction \
  --timeout 120
```

Supported benchmark roles:

- `classify`
- `json_normalizer`
- `memory_extraction`
- `capability_extraction`
- `log_summary`
- `diff_review`
- `handoff`
- `architecture`

Results are written to:

```text
.hivemind/local_benchmark.json
.hivemind/local_model_profile.json
```

The profile stores per-model, per-role latency and schema validity so routing can later move from a static matrix to measured policy.

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
