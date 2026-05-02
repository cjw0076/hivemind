# Hive Local Backend Contract

Status: private alpha contract draft.

Hive Mind local workers target `hive-local-backend-v1`, not a specific runtime.
Ollama is the first working adapter. llama.cpp, vLLM, LM Studio, Transformers,
and OpenAI-compatible local servers are planned or stubbed until their adapters
pass the same benchmark and validation flow.

## Adapter Requirements

An adapter must provide:

- `id`: stable backend identifier such as `ollama`, `llama_cpp`, or `vllm`.
- `status`: `available`, `unavailable`, or `degraded`.
- `models`: list of locally reachable model names.
- `generate`: prompt plus model input, returning raw text.
- `latency_ms`: measured wall-clock latency for each call.
- `error`: structured failure string when generation fails.

Hive Mind owns:

- role prompt rendering;
- JSON extraction and parsing;
- role schema validation;
- escalation decisions;
- benchmark records;
- run artifacts and audit metadata.

## Runtime Boundary

Adapters may use CLI binaries, local HTTP servers, Docker containers, or Python
libraries. They must not require provider API keys for open-weight local models.
Hosted APIs stay in provider adapters such as `deepseek_api` or `qwen_api`.

## Current Adapter State

| Backend | State | Notes |
| --- | --- | --- |
| `ollama` | implemented | Used for current local benchmark runs through workspace helper scripts. |
| `llama_cpp` | planned/stubbed | Detected by `llama-cli`; generation adapter is not implemented yet. |
| `vllm` | planned/stubbed | OpenAI-compatible server detection exists; benchmark adapter is not implemented yet. |
| `lmstudio` | planned | Should use an OpenAI-compatible local endpoint. |
| `transformers` | planned | Useful for direct Python execution after model loading policy is defined. |

## Public Release Rule

Before public alpha, docs and CLI output must describe non-Ollama backends as
planned or stubbed unless they can run `hive local benchmark --backend <name>`
and produce validated role results.
