좋아. `mos` CLI / Harness 만들 때 참고할 만한 레퍼런스는 크게 6종류로 보면 돼.

```text
1. Provider-native coding CLI
2. Open-source coding agent CLI
3. Agent harness / multi-provider runtime
4. Skills / rules / prompt packaging
5. GitHub/CI agent workflow
6. CLI → Desktop 확장 구조
```

## Current `mos` Implementation Notes

Implemented now:

```bash
mos
mos "task"
mos ask "task"
mos run -q --json "task"
mos plan
mos check list
mos check run
mos diff
mos review-diff
mos commit-summary
mos tui
mos completion zsh
```

`mos agents detect --json` now returns normalized provider records for:

```text
claude, codex, gemini, ollama, deepseek_api, qwen_api,
opencode, goose, openclaude
```

Reference-driven next CLI targets:

```text
- slash commands / REPL shell inspired by OpenClaude and Open Codex
- installer flags: mos init --no-tui --skills=yes --mcp=yes
- provider adapter execution paths beyond claude/codex/gemini/local
- markdown rules/checks under .memoryos/checks/
- git-first diff/check/commit summary loop inspired by Aider and Continue
- GitHub issue/PR runner later, after local run artifacts stabilize
```

Implemented checks:

```text
.memoryos/checks/memory-policy.md
.memoryos/checks/no-raw-export-leak.md
.memoryos/checks/implementation-handoff.md
```

아래 프로젝트들을 우선순위로 보면 좋아.

---

## 1. OpenClaude

**GitHub:** `Gitlawb/openclaude`

OpenClaude는 “cloud/local model provider를 모두 쓰는 open-source coding-agent CLI”를 표방하고, OpenAI-compatible APIs, Gemini, GitHub Models, Codex OAuth, Codex, Ollama, Atomic Chat 등을 하나의 terminal-first workflow로 묶는다고 설명한다. prompts, tools, agents, MCP, slash commands, streaming output을 한 workflow에 넣는 구조라서 `mos`의 CLI shell 구조에 참고하기 좋다. ([GitHub][1])

참고 포인트:

```text
- multi-provider adapter
- terminal-first UX
- MCP/tool integration
- slash command
- streaming output
- local + cloud provider abstraction
```

우리에게 중요한 건 “모델 하나”가 아니라 **provider/runtime abstraction**을 어떻게 잡는지야.

---

## 2. OpenCode

**GitHub:** `opencode-ai/opencode`
**Site:** `opencode.ai`

OpenCode는 open-source AI coding agent이고, terminal-based interface, desktop app, IDE extension 형태를 제공한다고 문서화되어 있다. 즉, 우리가 말한 “CLI 먼저 → TUI/Desktop으로 확장” 구조의 좋은 레퍼런스다. ([OpenCode][2])

또 GitHub workflow와도 붙어서, 이슈/PR에서 `/opencode` 또는 `/oc`를 멘션하면 GitHub Actions runner 안에서 작업을 실행하는 구조도 제공한다. ([OpenCode][3])

참고 포인트:

```text
- terminal AI coding agent UX
- desktop app beta 구조
- GitHub Actions integration
- issue/PR command trigger
- provider-agnostic 방향
```

`mos`도 나중에:

```text
mos CLI
→ MemoryOS Desktop
→ GitHub issue/PR runner
```

로 확장할 수 있음.

---

## 3. oh-my-opencode / oh-my-openagent

**GitHub:** `code-yeongyu/oh-my-openagent`
**관련:** `opensoft/oh-my-opencode`, `oh-my-opencode-slim`

oh-my-opencode 계열은 OpenCode 위에서 “battery included agent harness”처럼 설정/프리셋/스킬/루프를 패키징하는 흐름이라, 우리 `mos install`, `mos init`, `mos skills install` UX에 참고하기 좋아. 검색 결과에 따르면 oh-my-opencode는 OpenCode 위에서 동작하는 플러그인/하네스처럼 설명되고, 별도 설정 없이 설치 후 바로 쓸 수 있는 “Battery Included” 방향으로 성장했다. ([갓대희의 작은공간][4])

`oh-my-opencode-slim` 설치 문서는 `bunx oh-my-opencode-slim@latest install --no-tui --skills=yes`처럼 non-interactive install과 skills 설치 옵션을 제공한다. ([GitHub][5])

참고 포인트:

```text
- installer UX
- preset generation
- skills included
- non-interactive setup
- opinionated agent harness packaging
```

`mos`도 비슷하게:

```bash
mos init --no-tui --skills=yes --mcp=yes
```

같은 형태가 좋다.

---

## 4. Open Codex 계열

### `ymichael/open-codex`

`open-codex`는 interactive REPL, initial prompt, quiet/non-interactive mode, shell completion, `--model`, `--approval-mode`, `--quiet` 같은 CLI reference를 제공한다. ([GitHub][6])

### `codingmoh/open-codex`

`codingmoh/open-codex`는 OpenAI Codex에서 영감을 받은 fully open-source command-line AI assistant이고, local language model을 지원한다고 설명된다. ([GitHub][7])

참고 포인트:

```text
- REPL mode
- quiet/non-interactive mode
- model flag
- approval mode
- shell completion
- local model support
```

우리도 최소한:

```bash
mos
mos "task"
mos run "task"
mos run -q --json "task"
mos completion zsh
```

이런 CLI ergonomics가 필요해.

---

## 5. OpenAI Codex CLI

**GitHub:** `openai/codex`
**Docs:** OpenAI Codex CLI docs

Codex CLI는 `npm i -g @openai/codex` 또는 Homebrew로 설치하고, local computer에서 repo를 inspect/edit/run commands 하는 coding agent다. ([GitHub][8]) 공식 CLI 문서도 설치/실행 흐름을 `npm i -g @openai/codex` → `codex`로 설명한다. ([OpenAI 개발자][9])

참고 포인트:

```text
- installation UX
- repo-aware local agent
- sandbox/approval modes
- non-interactive exec
- MCP config
- AGENTS.md convention
```

`mos`는 Codex를 대체하기보다 감싸야 하니까:

```text
codex = executor
mos = context/harness/memory provider
```

로 봐야 함.

---

## 6. Aider

**GitHub:** `aider-ai/aider`

Aider는 “AI pair programming in your terminal”이고, local git repo에서 LLM과 pair programming하며 새 프로젝트를 만들거나 기존 codebase를 수정하는 도구다. ([GitHub][10])

참고 포인트:

```text
- git-first workflow
- local repo edit loop
- chat ↔ editor 왕복
- commit/patch 중심 UX
- terminal pair-programming ergonomics
```

`mos`의 Agent Harness에서 `git diff`, `patch`, `commit summary`, `run event`를 어떻게 다룰지 참고하기 좋다.

---

## 7. Goose

**GitHub:** `aaif-goose/goose`

Goose는 macOS/Linux/Windows desktop app, terminal workflow용 CLI, embed 가능한 API를 제공하고, Anthropic/OpenAI/Google/Ollama/OpenRouter/Azure/Bedrock 등 15개 이상 provider와 70개 이상 MCP extension을 연결한다고 설명한다. ([GitHub][11])

참고 포인트:

```text
- CLI + Desktop + API 삼중 구조
- multi-provider support
- MCP extension ecosystem
- agent runtime architecture
- recipes/workflows 가능성
```

우리의 최종 형태와 매우 유사한 방향:

```text
mos CLI
MemoryOS Desktop
MemoryOS API/MCP
```

---

## 8. Continue.dev

**GitHub:** `continuedev/continue`
**Site:** `continue.dev`

Continue는 PR마다 agent check를 돌리는 구조가 인상적이다. `.continue/checks/` 아래 markdown 파일로 agent checks를 정의하고, GitHub status check처럼 green/red와 suggested diff를 제공한다고 설명한다. ([GitHub][12])

참고 포인트:

```text
- markdown-as-agent-check
- repo-local rules/checks
- CI integration
- suggested diff
- source-controlled agent policy
```

우리에게는 `skills/`, `rules/`, `checks/` 구조 설계에 중요함.

예:

```text
.memoryos/checks/security-review.md
.memoryos/checks/memory-policy.md
.memoryos/checks/no-raw-export-leak.md
```

---

## 9. Continue rules / awesome-rules

`continuedev/awesome-rules`는 Cursor, Continue.dev 등 여러 AI coding assistant와 호환되는 YAML frontmatter + markdown rule 형식을 모아둔 repo다. ([GitHub][13])

참고 포인트:

```text
- rules as markdown
- YAML frontmatter
- assistant-agnostic instruction packaging
- repository-local conventions
```

우리의 `Skill`, `Capability Module`, `Agent Constitution` 파일 포맷 설계에 참고.

---

## 10. CLI-Anything

**GitHub:** `HKUDS/CLI-Anything`

CLI-Anything은 기존 software를 agent-native CLI로 변환하려는 방향이라, “모든 앱을 capability wrapper로 감싼다”는 우리의 CapabilityOS 비전과 잘 맞다. 검색 결과 기준으로 소프트웨어 경로/repo를 주면 GIMP 같은 앱의 CLI를 생성하는 워크플로우를 예시로 든다. ([GitHub][14])

참고 포인트:

```text
- 기존 software를 CLI wrapper로 감싸기
- agent-native interface 생성
- GUI tool을 자동화 가능한 tool로 전환
```

CapabilityOS의 “MCP가 없는 앱도 wrapper 생성” 아이디어에 직접 관련 있음.

---

# 참고 우선순위

지금 `mos` CLI를 만든다면 우선순위는 이렇게.

```text
1. OpenClaude
   multi-provider + MCP + slash command + terminal workflow

2. OpenCode
   CLI/Desktop/IDE 확장 구조

3. oh-my-opencode / oh-my-openagent
   battery-included harness packaging

4. Codex CLI
   approval/sandbox/exec/config UX

5. Goose
   CLI + Desktop + API + MCP extension 구조

6. Aider
   git-first pair-programming loop

7. Continue
   markdown rules/checks + CI agent policy

8. CLI-Anything
   arbitrary software를 agent-native CLI로 감싸는 방향
```

---

# `mos`에 바로 반영할 설계

이 레퍼런스들을 종합하면 `mos` CLI는 이렇게 가면 좋다.

```bash
mos init
mos doctor
mos agents detect
mos mcp install --for all
mos local setup
mos run "작업"
mos invoke claude
mos invoke codex
mos invoke local
mos status
mos open current
mos memory drafts
mos capability gap "작업"
mos radar scan
mos society report
```

내부 구조:

```text
mos
├── provider adapters
│   ├── claude-cli
│   ├── codex-cli
│   ├── gemini-cli
│   ├── opencode
│   ├── goose
│   └── ollama/local
│
├── run workspace
│   ├── task.yaml
│   ├── context_pack.md
│   ├── handoff.yaml
│   ├── events.jsonl
│   └── memory_drafts.json
│
├── skills/rules
│   ├── memory-first-workflow
│   ├── implementation-handoff
│   ├── boot-orientation
│   └── conversation-to-memory-graph
│
└── MCP
    ├── memory.search
    ├── project.get_state
    ├── hypergraph.search
    ├── handoff.create
    └── run.log_event
```

---

# 한 줄 결론

`mos`는 **OpenClaude의 multi-provider terminal UX + OpenCode/Goose의 CLI/Desktop/API 구조 + oh-my-opencode의 battery-included setup + Codex의 executor ergonomics + Continue의 markdown rules/checks + Aider의 git-first loop**를 섞어서 만들면 된다.

[1]: https://github.com/Gitlawb/openclaude?utm_source=chatgpt.com "Gitlawb/openclaude: runs anywhere. uses anything"
[2]: https://opencode.ai/docs/?utm_source=chatgpt.com "Intro | AI coding agent built for the terminal"
[3]: https://opencode.ai/docs/github/?utm_source=chatgpt.com "GitHub"
[4]: https://goddaehee.tistory.com/485?utm_source=chatgpt.com "Open Code 리뷰(2) : oh-my-opencode 설치 및 설정 방법(기본 ..."
[5]: https://github.com/alvinunreal/oh-my-opencode-slim/blob/master/docs/installation.md?utm_source=chatgpt.com "Installation Guide - alvinunreal/oh-my-opencode-slim"
[6]: https://github.com/ymichael/open-codex?utm_source=chatgpt.com "ymichael/open-codex: Lightweight coding agent ..."
[7]: https://github.com/codingmoh/open-codex?utm_source=chatgpt.com "codingmoh/open-codex: Fully open-source command-line ..."
[8]: https://github.com/openai/codex?utm_source=chatgpt.com "openai/codex: Lightweight coding agent that runs in your ..."
[9]: https://developers.openai.com/codex/cli?utm_source=chatgpt.com "Codex CLI"
[10]: https://github.com/aider-ai/aider?utm_source=chatgpt.com "aider is AI pair programming in your terminal"
[11]: https://github.com/aaif-goose/goose?utm_source=chatgpt.com "aaif-goose/goose: an open source, extensible AI agent that ..."
[12]: https://github.com/continuedev/continue?utm_source=chatgpt.com "continuedev/continue: ⏩ Source-controlled AI checks ..."
[13]: https://github.com/continuedev/awesome-rules?utm_source=chatgpt.com "continuedev/awesome-rules: A collection of useful ..."
[14]: https://github.com/HKUDS/CLI-Anything?utm_source=chatgpt.com "CLI-Anything: Making ALL Software Agent-Native"
