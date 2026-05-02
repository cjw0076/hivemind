# Provider Harness Guide

Last checked: 2026-05-02 KST.

This guide is for `mos` provider adapters. It documents command availability, safe invocation patterns, output formats, risks, and the integration shape for Claude, Codex, Gemini, DeepSeek, Qwen, and local Ollama.

## Harness Contract

Every provider should write the same artifacts:

```text
.runs/<run_id>/agents/<provider>/
  <role>_prompt.md
  <role>_command.txt
  <role>_output.md
  <role>_result.yaml
```

Minimum `result.yaml` fields:

```yaml
provider: claude
role: planner
status: completed
mode: read_only
command: "claude -p ... --permission-mode plan --output-format json"
prompt: ".runs/.../agents/claude/planner_prompt.md"
output: ".runs/.../agents/claude/planner_output.md"
returncode: 0
started_at: "..."
finished_at: "..."
```

Default policy:

- Use read-only or plan mode unless the role explicitly needs edits.
- Capture stdout and stderr separately when possible.
- Prefer JSON or stream JSON when the CLI/API supports it.
- Never pass secrets through prompt artifacts, command files, or event logs.
- Store provider availability and version in a capability probe artifact.

## Availability Snapshot

| Provider | Local command | Status in this shell | Primary path |
| --- | --- | --- | --- |
| Claude | `claude` | available at `/home/user/.local/bin/claude` | CLI adapter |
| Codex | `codex` | available at `/home/user/bin/codex`; help was gated by local approval prompt | CLI adapter, prepare-only until verified |
| Gemini | `gemini` | available at Node path; `gemini --help` works | CLI adapter |
| DeepSeek | `deepseek` | not found | OpenAI-compatible HTTP adapter |
| Qwen | `qwen` | not found | install Qwen Code or use OpenAI-compatible HTTP adapter |
| Ollama | `ollama` | not on PATH; workspace wrapper works | local wrapper/API adapter |

## Claude

Observed local help:

- Non-interactive mode: `claude -p/--print`.
- Input formats: `text`, `stream-json`.
- Output formats: `text`, `json`, `stream-json`.
- Permission modes: `default`, `plan`, `acceptEdits`, `auto`, `dontAsk`, `bypassPermissions`.
- Useful controls: `--model`, `--effort`, `--max-budget-usd`, `--json-schema`, `--no-session-persistence`, `--add-dir`, `--tools`, `--allowed-tools`, `--disallowed-tools`, `--bare`.

Safe non-interactive pattern:

```bash
claude -p "$(cat .runs/<run>/agents/claude/planner_prompt.md)" \
  --permission-mode plan \
  --output-format json \
  --no-session-persistence
```

Edit-capable pattern, only for trusted executor roles:

```bash
claude -p "$(cat .runs/<run>/agents/claude/executor_prompt.md)" \
  --permission-mode acceptEdits \
  --output-format stream-json
```

Strengths:

- Strong planning, critique, architecture review, and claim discipline.
- Good fit for structured JSON output with `--json-schema`.
- Mature file/tool permission controls.

Risks:

- `--dangerously-skip-permissions` and `--allow-dangerously-skip-permissions` should stay forbidden in `mos`.
- Non-interactive mode skips workspace trust UI, so `mos` must enforce trusted root and allowed directories.
- Claude can edit when permission mode allows it; read-only roles must use `plan` and disabled write tools if possible.

`mos` integration:

- Make Claude the default `planner`, `critic`, and `claim-auditor`.
- Use `--output-format json` for parseable recommendations.
- Use `--json-schema` for roles that produce decisions, risks, and next actions.
- Add a `claude.execute=true` adapter path; current harness already supports read-only execution.

## Codex

Observed local state:

- `codex` exists at `/home/user/bin/codex`.
- `docs/cli_help.md` records the local CLI contract, including `codex exec` for non-interactive execution.
- Direct execution in this session is currently gated by a local access prompt and returns `접근 거부`; `mos` captures that as a failed provider artifact.

Safe read-only non-interactive pattern:

```bash
codex exec --cd . --sandbox read-only --ask-for-approval never \
  "$(cat .runs/<run>/agents/codex/reviewer_prompt.md)"
```

Edit-capable pattern, only after explicit approval:

```bash
codex exec --cd . --sandbox workspace-write --ask-for-approval on-request \
  "$(cat .runs/<run>/agents/codex/executor_prompt.md)"
```

Approval/sandbox modes to map:

- Suggest/read-only: exploration, review, and implementation planning.
- Auto Edit: file edits but shell commands still require approval.
- Full Auto: sandboxed edit and command execution; use only for scoped repo tasks.

Strengths:

- Best fit for implementation, test-running, and repository-aware execution.
- Good default executor for MyWorld code changes.
- Sandboxed full-auto mode is useful for contained repair loops once verified.

Risks:

- The local CLI contract is not yet verified in this shell.
- Full-auto can make broad changes if prompt scope is weak.
- `mos` must protect unrelated user edits and reject destructive commands unless explicitly authorized.

`mos` integration:

- Generate Codex prompt/command artifacts for executor/reviewer roles.
- Allow read-only `--execute` through `codex exec --sandbox read-only --ask-for-approval never`.
- Treat local access-gate failures as provider failures, not harness crashes.
- Use Codex primarily for `executor`, `test-fixer`, and `diff-reviewer` roles once local access is unblocked.
- Require changed-file summaries and command logs in `result.yaml`.

## Gemini

Observed local help:

- Non-interactive mode: `gemini -p/--prompt`.
- Output formats: `text`, `json`, `stream-json`.
- Approval modes: `default`, `auto_edit`, `yolo`, `plan`.
- Sandbox flag: `-s/--sandbox`.
- Trust bypass for a session: `--skip-trust`.
- Useful controls: `--model`, `--include-directories`, `--allowed-mcp-server-names`, `--policy`, `--admin-policy`.

Safe non-interactive pattern:

```bash
gemini -p "$(cat .runs/<run>/agents/gemini/reviewer_prompt.md)" \
  --approval-mode plan \
  --output-format json \
  --skip-trust
```

Edit-capable pattern, only for scoped work:

```bash
gemini -p "$(cat .runs/<run>/agents/gemini/executor_prompt.md)" \
  --approval-mode auto_edit \
  --output-format stream-json \
  --skip-trust
```

Strengths:

- Useful independent reviewer and alternative planner.
- JSON/stream JSON make it easy to parse.
- Policy files can encode MyWorld boundaries and read-only review defaults.

Risks:

- `--yolo` should be forbidden in `mos`.
- `--skip-trust` removes a prompt, so `mos` must enforce the trusted root.
- Model/version behavior may vary with user auth and configured provider.

`mos` integration:

- Keep Gemini as `reviewer`, `alternate-planner`, and `policy-checker`.
- Prefer `--approval-mode plan` for normal use.
- Add support for policy files generated from MyWorld boundaries.

## DeepSeek

Local command:

- `deepseek` is not installed.

Official API path:

- DeepSeek documents OpenAI-compatible access with `base_url=https://api.deepseek.com`.
- Current official docs list `deepseek-v4-flash` and `deepseek-v4-pro`; older aliases `deepseek-chat` and `deepseek-reasoner` are marked for deprecation on 2026-07-24.
- Docs also expose an Anthropic-compatible base path at `https://api.deepseek.com/anthropic`.

Non-interactive pattern:

```bash
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \
  -d @.runs/<run>/agents/deepseek/request.json
```

Preferred request shape:

```json
{
  "model": "deepseek-v4-flash",
  "messages": [
    {"role": "system", "content": "Return strict JSON for the MemoryOS harness."},
    {"role": "user", "content": "..."}
  ],
  "stream": false
}
```

Strengths:

- Cost-efficient critique, summarization, coding review, and batch synthesis.
- OpenAI-compatible request/response shape keeps adapter simple.

Risks:

- Hosted API requires `DEEPSEEK_API_KEY`.
- Model aliases and feature support change; probe model list or centralize model names in config.
- Do not rely on undocumented OpenAI-specific fields without adapter tests.

`mos` integration:

- Implement as an HTTP provider, not a CLI provider.
- Use for `cheap-critic`, `batch-summarizer`, `code-review-draft`, and `memory-extractor-check`.
- Normalize responses into the same `output.md` and `result.yaml` artifacts.

## Qwen

Local command:

- `qwen` is not installed.

Official/primary paths:

- Qwen Code is an official terminal agent from QwenLM. It supports interactive `qwen` and headless `qwen -p "..."`.
- Qwen Code supports API-key authentication and multiple provider protocols.
- DashScope / Alibaba Model Studio supports OpenAI-compatible access through `https://dashscope.aliyuncs.com/compatible-mode/v1`.
- Qwen docs and tooling commonly use OpenAI-compatible environment names such as `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and Qwen model names, but `mos` should expose explicit provider config names to avoid ambiguity.

Headless CLI pattern after install:

```bash
qwen -p "$(cat .runs/<run>/agents/qwen/reviewer_prompt.md)"
```

HTTP pattern:

```bash
curl https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${QWEN_API_KEY}" \
  -d @.runs/<run>/agents/qwen/request.json
```

Strengths:

- Strong open-model/code-agent path, especially for Qwen Coder models.
- Good candidate for cheap alternative planning and local/open-model comparison.
- Qwen Code is based on Gemini CLI patterns, so `mos` can reuse much of the Gemini adapter shape after install.

Risks:

- CLI not installed yet in this workspace.
- Auth paths differ: Alibaba Cloud Coding Plan, DashScope API key, OpenRouter, Fireworks, and other compatible endpoints.
- Avoid overloading `OPENAI_API_KEY` in `mos`; use provider-specific env names and translate internally.

`mos` integration:

- Add `qwen` as optional CLI provider after install detection.
- Add `qwen_api` as OpenAI-compatible HTTP provider immediately.
- Use for `open-coder-reviewer`, `cheap-planner`, and local/open-weight comparison against Ollama Qwen models.

## Local Ollama

Observed local help:

- `ollama` is not on PATH, but `scripts/ollama-local.sh --help` works and wraps `.local/ollama/bin/ollama`.
- Commands include `serve`, `run`, `pull`, `list`, `ps`, `show`, `stop`.
- Local docs show pulled models: `qwen3:1.7b`, `qwen3:8b`, `deepseek-coder:6.7b`, `deepseek-coder-v2:16b`.

Non-interactive CLI pattern:

```bash
scripts/start-ollama-local.sh
scripts/ollama-local.sh run qwen3:8b "$(cat .runs/<run>/agents/ollama/memory_prompt.md)"
```

Preferred existing MyWorld worker path:

```bash
python -m memoryos.cli local-workers run memory_extractor \
  --input .runs/<run>/context_pack.md \
  --model qwen3:8b \
  --out .runs/<run>/agents/local/memory.json
```

Strengths:

- Local, cheap, private, and fast for compression, tagging, first-pass extraction, and log summaries.
- Already integrated through `memoryos.local_workers`.
- Good fit for repeated batch work and future fine-tuning data collection.

Risks:

- Model output may be weak for schema-critical JSON; validate and repair.
- Runtime availability depends on local server and model pulls.
- Local models are workers, not final judges for architecture or claim discipline.

`mos` integration:

- Keep Ollama behind role workers, not raw chat by default.
- Add health checks: wrapper exists, server responds, model exists, smoke prompt passes JSON validation.
- Store model, latency, token-ish size, and validation status in result artifacts.

## Source Notes

- Local CLI help: `claude --help`, `gemini --help`, `scripts/ollama-local.sh --help`.
- Local MyWorld docs: `docs/LOCAL_LLM_WORKERS.md`, `docs/TUI_HARNESS.md`, `docs/PROVIDER_MODELS.md`.
- Official docs consulted: OpenAI Codex CLI help center and non-interactive docs, DeepSeek API docs, Ollama CLI docs, QwenLM/qwen-code README, Alibaba DashScope OpenAI-compatible endpoint references.
