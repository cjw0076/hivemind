# Local Model Benchmark

Date: 2026-05-02 KST

Hive Mind now treats local inference as `hive-local-backend-v1`. Ollama was used
as the measurement adapter for this run, but it is not a required dependency.

## Inventory

Pulled and retained locally:

| Model | Size | Keep |
| --- | ---: | --- |
| `qwen3:1.7b` | 1.4 GB | yes, non-critical fast pass only |
| `phi4-mini:latest` | 2.5 GB | yes, default classify/JSON/memory candidate |
| `qwen3:4b` | 2.5 GB | yes, but failed this JSON adapter benchmark |
| `qwen3:8b` | 5.2 GB | yes, general fallback |
| `qwen2.5-coder:7b` | 4.7 GB | yes, coder fallback candidate |
| `deepseek-coder:6.7b` | 3.8 GB | yes, code-log candidate |
| `qwen2.5-coder:14b` | 9.0 GB | yes, diff-review fallback |
| `deepseek-coder-v2:16b` | 8.9 GB | yes, diff/architecture primary |
| `qwen3-coder:30b` | 18 GB | yes, architecture fallback |

`qwen3-coder-next` was pulled accidentally during the batch and removed because
it was outside the agreed scope.

Disk after cleanup:

| Path | Usage |
| --- | ---: |
| `/` | 898 GB used / 842 GB free |
| local model store | 53 GB |

## General Role Results

| Model | Roles | Result |
| --- | --- | --- |
| `qwen3:1.7b` | classify, JSON normalizer, memory extraction, capability extraction | failed strict schemas, 3.1-6.1s |
| `phi4-mini` | same four roles | passed all, 13.4-20.1s |
| `qwen3:4b` | same four roles | failed JSON parsing, 10.1-34.7s |
| `qwen3:8b` | same four roles | passed all, 19.8-35.6s |

Routing impact:

- Promote `phi4-mini` to default classifier and JSON normalizer.
- Keep `qwen3:1.7b` only as a cheap fast path where schema failure is tolerable.
- Prefer `phi4-mini` or `qwen3:8b` for schema-critical general work.
- Do not rely on `qwen3:4b` until adapter/prompt settings are retested.

Adapter note:

- The original `qwen3:*` JSON failures were partly an Ollama adapter issue:
  `format: "json"` plus qwen3 thinking mode can return an empty `{}`. Hive Mind
  now sends top-level `think: false` and prefixes `/no_think` for qwen3-family
  models. Putting `think` inside `options` is not sufficient.

## Coder Role Results

| Model | Role | Result |
| --- | --- | --- |
| `deepseek-coder:6.7b` | log summary | failed role schema, 26.3s |
| `qwen2.5-coder:7b` | log summary | failed role schema, 32.3s |
| `qwen2.5-coder:14b` | diff review | passed, 46.6s |
| `deepseek-coder-v2:16b` | diff review | passed, 9.1s |
| `deepseek-coder-v2:16b` | handoff | JSON truncated, failed schema, 12.7s |
| `deepseek-coder-v2:16b` | architecture | passed, 7.9s |
| `qwen3-coder:30b` | handoff | JSON truncated, failed schema, 19.6s |
| `qwen3-coder:30b` | architecture | passed, 18.0s |

Routing impact:

- Use `deepseek-coder-v2:16b` for diff review and local architecture drafts.
- Keep `qwen2.5-coder:14b` as a slower diff review fallback.
- Do not make coder models responsible for final handoff JSON until output
  truncation is fixed with larger `num_predict`, better schemas, or a
  normalizer pass.
- Code-log summarization needs prompt/schema tuning before it can be trusted.

## Current Stance

The local model layer is useful, but only as a measured worker tier. Production
routing should use benchmark results, schema validation, and escalation rules
rather than model reputation.
