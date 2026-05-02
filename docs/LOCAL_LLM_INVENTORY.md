# Local LLM Inventory - 2026-05-01

## Hardware

Detected by `nvidia-smi` and `llm-checker hw-detect`:

- Host: `user-MS73-HB1-000`
- CPU: 2x Intel Xeon Gold 6526Y, 64 logical CPUs
- RAM: 251 GiB
- GPU: 2x NVIDIA GeForce RTX 5090, 32 GiB each
- CUDA driver stack: driver 570.211.01, CUDA 12.8
- Total dedicated VRAM: 64 GiB
- Current GPU state during check:
  - GPU0: P18-A process running, about 873 MiB used
  - GPU1: effectively idle, about 18 MiB used

## Installed Runtime Check

Found:

- Node.js: `/home/user/.nvm/versions/node/v22.22.2/bin/node`
- npm: `/home/user/.nvm/versions/node/v22.22.2/bin/npm`
- npx: `/home/user/.nvm/versions/node/v22.22.2/bin/npx`
- conda envs: `base`, `prodet`, `dain_fake`, `dain_fake2`, `fft`

Not found:

- `ollama`
- `llama-server`
- `llama-cli`
- Python `transformers` in base or `prodet`
- Python `vllm` in base or `prodet`
- local `.gguf` / `.safetensors` LLM files under `/home/user` at shallow search depth

## llm-checker Result

Command:

```bash
npx llm-checker hw-detect
```

Result summary:

```text
Tier: VERY HIGH
Max model size: 62GB
Best backend: NVIDIA CUDA
Fingerprint: cuda-rtx-5090-64gb-x2
```

Command:

```bash
npx llm-checker recommend --category coding
```

Result summary:

```text
BEST OVERALL: qwen3:8b
Coding: deepseek-coder:6.7b
Reasoning: deepseek-coder-v2:16b
Multimodal: qwen3-vl:8b
Creative/Chat/General: qwen3:8b
Reading: qwen3:1.7b
```

Interpretation:

- `llm-checker` works on this machine.
- It is useful for hardware-aware local/Ollama model selection.
- It is not a complete provider-router for OpenRouter/DeepSeek/xAI/OpenAI APIs.
- Since Ollama is not installed, `ollama pull ...` commands are not executable yet.

## Practical Local Model Direction

With 2x RTX 5090 / 64 GiB total VRAM:

- Small/medium local models should be easy once a runtime is installed.
- 7B, 8B, 14B, 16B, 20B, 32B class quantized models are realistic.
- 70B class quantized models may be realistic depending on quantization and runtime.
- 120B class models are risky on 64 GiB unless heavily quantized and well-sharded; check runtime support before committing.

Recommended runtime path:

1. Install Ollama for quick model experiments and llm-checker integration.
2. Use `llm-checker check` / `recommend` / `ollama-plan`.
3. For serious serving, add vLLM or llama.cpp later.
4. Keep provider API routing separate from local runtime routing.

