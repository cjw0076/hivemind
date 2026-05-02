# Provider / Well-Made Model Access - 2026-05-01

This file tracks whether MyWorld can use major hosted and open-weight model families.

## Current Local Key State

Checked environment variable names only; no values were printed.

Currently not set in this shell:

- `OPENROUTER_API_KEY`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `XAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `HF_TOKEN`

So provider calls are structurally possible but not ready until keys/credits are added.

## Recommended Adapter Strategy

Use one internal interface:

```text
provider
model
messages / input
tools
structured output schema
stream
budget policy
```

Then implement adapters:

- OpenAI-compatible chat/responses providers
- OpenRouter gateway
- Hugging Face Inference Providers
- direct open-model providers: Together, Fireworks, Groq, Cerebras, Nebius
- local Ollama/vLLM server
- future specialized providers

See also:

- `docs/OPEN_MODEL_PROVIDER_SURVEY.md`

## OpenRouter

Status: recommended as the first provider gateway.

Why:

- One API key can route to many providers and model families.
- OpenRouter request/response schemas are very similar to OpenAI Chat API.
- Model listing is available through `GET https://openrouter.ai/api/v1/models`.
- Useful for comparing GPT, Claude, Gemini, Grok, DeepSeek, Llama-hosted variants, and smaller niche models through a single abstraction.

Config:

```text
base_url = https://openrouter.ai/api/v1
api_key_env = OPENROUTER_API_KEY
```

Use:

- broad model exploration
- fallback routing
- comparative agent evaluation
- quick access before self-hosting local models

## DeepSeek

Status: usable through direct API once `DEEPSEEK_API_KEY` is set.

Official docs state OpenAI-compatible access:

```text
base_url = https://api.deepseek.com
```

Current model names from docs:

```text
deepseek-v4-flash
deepseek-v4-pro
```

Older aliases noted as deprecating in 2026:

```text
deepseek-chat
deepseek-reasoner
```

Use:

- cost-efficient reasoning / coding
- critique agent
- batch synthesis

## xAI / Grok

Status: usable through direct API once `XAI_API_KEY` is set.

Official docs support OpenAI-compatible clients:

```text
base_url = https://api.x.ai/v1
```

Current model examples from docs:

```text
grok-4.20-reasoning
grok-4.20-non-reasoning
grok-4-1-fast-reasoning
grok-4-1-fast-non-reasoning
```

Use:

- alternate reasoning voice
- long-context exploration where cost allows
- model disagreement checks

## OpenAI Hosted Models

Status: usable once `OPENAI_API_KEY` is set.

Use:

- high-reliability synthesis
- code/refactor tasks
- structured outputs
- tool-calling heavy agents

Note:

- `gpt-oss` is not served through the OpenAI API.
- OpenAI hosted API models and OpenAI open-weight `gpt-oss` should be treated as separate provider families.

## gpt-oss

Status: open-weight, not hosted by the OpenAI API.

Official OpenAI Help Center states:

- `gpt-oss-120b` and `gpt-oss-20b` are open-weight reasoning models.
- They run on infrastructure you control or through hosting providers.
- They are not available through the OpenAI API or ChatGPT.
- Common runtimes include vLLM, Ollama, llama.cpp, and Transformers.

Local feasibility on this machine:

- `gpt-oss-20b`: realistic after installing runtime and downloading weights.
- `gpt-oss-120b`: likely too large for comfortable local full-precision serving on 64 GiB total VRAM; may be possible only with quantization/sharding and careful runtime support.

Use:

- local/private reasoning experiments
- ontology agent experiments where data locality matters
- comparing open-weight behavior against hosted APIs

## Llama / Other Open Weights

Status: usable either through hosted gateways or self-hosting.

Access paths:

- OpenRouter / hosted inference providers
- Hugging Face downloads
- Ollama
- vLLM
- llama.cpp / GGUF

Local feasibility:

- 8B/13B/14B/20B/32B class models should be straightforward after runtime setup.
- 70B class quantized models are plausible.
- Full large models need careful VRAM planning.

## llm-checker Role

`llm-checker` is useful, but its role is specific:

- detects hardware;
- recommends local/Ollama models;
- can sync/search Ollama model catalog;
- can generate Ollama pull/run commands;
- can integrate with Claude MCP.

It is not the full answer for hosted model providers.

For MyWorld, use:

- `llm-checker` for local model selection;
- provider adapters for OpenRouter / DeepSeek / xAI / OpenAI / Anthropic / Google;
- a policy layer to decide which model handles which task.

## Initial Routing Policy

Suggested first routing:

```text
high_stakes_code_or_research:
  hosted frontier model, if key available

cheap_parallel_critique:
  DeepSeek direct or OpenRouter route

independent_reasoning_voice:
  Grok via xAI or OpenRouter

private/local_memory_experiments:
  local gpt-oss / Qwen / Llama via Ollama or vLLM

hardware/model_fit:
  llm-checker
```
