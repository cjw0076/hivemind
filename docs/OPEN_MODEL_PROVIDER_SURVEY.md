# Open-Model Provider Survey - 2026-05-01

Goal: identify hosted providers that expose strong open-weight / open-source model families for MyWorld agents.

## Summary

Yes, there are many options beyond OpenRouter, DeepSeek, xAI, OpenAI, and local Ollama.

Recommended provider categories:

1. Gateway / router:
   - OpenRouter
   - Hugging Face Inference Providers

2. Open-weight model specialists:
   - Together AI
   - Fireworks AI
   - GroqCloud
   - Cerebras Inference
   - Nebius AI Studio / Token Factory

3. Secondary / specialized providers:
   - SambaNova
   - Hyperbolic
   - Novita
   - Nscale
   - Scaleway
   - Replicate
   - Cohere for selected open/command models and enterprise APIs

## Provider Matrix

| Provider | Main role | Open model families seen in docs | Interface style | MyWorld priority |
|---|---|---|---|---|
| OpenRouter | Unified gateway | GPT OSS, Llama, Qwen, DeepSeek, Kimi, GLM, Grok via providers | OpenAI-like | High |
| Hugging Face Inference Providers | Unified open-model gateway | Depends on model/provider; many Hub models | HF SDK / provider routes | High |
| Together AI | Open model serverless + fine-tune | GPT OSS, DeepSeek, Qwen, Llama, Kimi, GLM, Mistral, Gemma | OpenAI-compatible | High |
| Fireworks AI | Open model serving + custom model deploy | DeepSeek, Qwen, Kimi, GLM, Llama, Mistral, Gemma, Phi, StarCoder | OpenAI-compatible | High |
| GroqCloud | Ultra-fast inference | GPT OSS 120B, Llama 3.1 8B, and other openly available models | OpenAI-compatible | Medium-high |
| Cerebras | Very fast open model inference | GPT OSS 120B, Llama 3.1 8B, Qwen 235B, GLM 4.7 | OpenAI-compatible | Medium-high |
| Nebius AI Studio | Open model inference / enterprise endpoints | GPT OSS, Llama, Qwen, DeepSeek, Kimi, Hermes, GLM | OpenAI-compatible | Medium-high |
| Replicate | Broad hosted model demos | Many open-source models, stronger for image/video and demos | Provider-specific | Medium |
| SambaNova | Fast open LLM/embedding APIs | varies | Provider-specific / OpenAI-like in some paths | Medium |
| Hyperbolic | GPU/open model inference | varies | OpenAI-like in many examples | Medium |
| Novita | LLM/VLM/image/video | varies | OpenAI-like in many examples | Medium |

## Notable Model Families

Open-weight / open-source families worth tracking:

- OpenAI `gpt-oss-120b`, `gpt-oss-20b`
- Meta Llama 3.1 / 3.3 / 4 Scout / 4 Maverick
- Alibaba Qwen 2.5 / Qwen3 / Qwen3-Coder / Qwen3-VL
- DeepSeek R1 / V3 / V3.1
- Moonshot Kimi K2 / Kimi K2 Thinking
- Z.ai GLM 4.5 / 4.6 / 4.7
- Mistral / Mixtral / Magistral
- Google Gemma
- NousResearch Hermes
- Deep Cogito
- StarCoder / StarCoder2 for code-specialized work
- Llama Guard / safety classifiers

## Provider Notes

### Together AI

Docs show 100+ open-source models on serverless and dedicated endpoints.

Useful listed examples:

- `openai/gpt-oss-120b`
- `openai/gpt-oss-20b`
- `deepseek-ai/DeepSeek-R1`
- `deepseek-ai/DeepSeek-V3.1`
- `Qwen/Qwen3-Coder-480B-A35B-Instruct-FP8`
- `meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8`
- `meta-llama/Llama-3.3-70B-Instruct-Turbo`
- `moonshotai/Kimi-K2-*`
- `zai-org/GLM-*`

Use for:

- high-quality open-weight reasoning/coding;
- fine-tuning experiments;
- comparing multiple open families under one API.

### Fireworks AI

Docs state support for custom models from Hugging Face and broad architecture support:

- DeepSeek V1/V2/V3
- Qwen/Qwen2/Qwen2.5/Qwen2.5-VL/Qwen3
- Kimi K2
- GLM 4.X
- Llama 1/2/3/3.1/4
- Mistral/Mixtral
- Gemma
- Phi / StarCoder / LLaVA / etc.

Fireworks recommended open models for code/reasoning include:

- Kimi K2
- DeepSeek V3.1
- Qwen3 Coder 480B
- DeepSeek R1
- Qwen2.5-32B-Coder

Use for:

- open coding/reasoning models;
- custom or fine-tuned model deployment later.

### GroqCloud

Docs list very fast hosted inference for open models.

Seen examples:

- `openai/gpt-oss-120b`
- `llama-3.1-8b-instant`

Use for:

- fast agent loops;
- cheap/low-latency critique passes;
- latency-sensitive internal tools.

### Cerebras

Docs list:

- `gpt-oss-120b`
- `llama3.1-8b`
- `qwen-3-235b-a22b-instruct-2507`
- `zai-glm-4.7`

Use for:

- extremely fast reasoning/coding calls;
- rapid multi-agent debate where throughput matters.

### Nebius

Docs describe OpenAI-compatible access:

```text
base_url = https://api.studio.nebius.com/v1/
```

Public pages mention:

- GPT OSS
- Llama
- Qwen
- DeepSeek
- Kimi
- Hermes
- GLM

Use for:

- enterprise-style open-model endpoint;
- zero-retention / dedicated endpoint option if needed.

### Hugging Face Inference Providers

HF integrates multiple providers through a consistent interface.

Docs list partners supporting chat LLM/VLM:

- Cerebras
- Cohere
- Featherless AI
- Fireworks
- Groq
- HF Inference
- Hyperbolic
- Novita
- Nscale
- OVHcloud AI Endpoints
- Public AI
- SambaNova
- Scaleway
- Together
- Z.ai

Use for:

- discovery and quick tests across many open models;
- leveraging existing Hugging Face model pages and filters;
- provider comparison without setting up each provider separately.

## Recommended MyWorld Provider Stack

Start with three layers:

```text
Layer 1: Gateway
  OpenRouter
  Hugging Face Inference Providers

Layer 2: Direct open-model providers
  Together
  Fireworks
  Groq
  Cerebras
  Nebius

Layer 3: Local self-hosting
  Ollama
  vLLM
  llama.cpp
```

Initial routing:

```text
frontier/fallback comparison:
  OpenRouter

open coding/reasoning:
  Together or Fireworks

fast cheap loops:
  Groq or Cerebras

local/private:
  Ollama/vLLM with gpt-oss, Qwen, Llama, DeepSeek distills

model discovery:
  Hugging Face Inference Providers + llm-checker
```

## Open Questions

- Which accounts/API keys are available to User?
- Should MyWorld optimize for cost, latency, quality, privacy, or disagreement diversity first?
- Do we want provider-level evals before implementing a full router?
- Should provider calls be logged into MyWorld memory as observations with cost/latency/model metadata?

