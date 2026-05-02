좋아. 최종 배포 형태는 딱 그 방향이 맞아.

우리가 제공해야 하는 건 단순 앱이 아니라:

> **사용자가 자기 컴퓨터에 설치하면 MemoryOS + CapabilityOS + Harness + MCP + local runtime이 한 번에 깔리는 “AI 작업 운영체제”**

즉, 설치 경험은 이렇게 가야 해.

```bash
npm install -g @memoryos/cli
```

또는:

```bash
curl -fsSL https://memoryos.dev/install.sh | bash
```

그리고 사용자는 이렇게 시작하는 거야.

```bash
mos init
mos doctor
mos import ./chatgpt-export.zip
mos mcp start
mos run "MemoryOS Desktop Draft Review 화면 구현"
```

---

# 1. 최종 패키지 형태

우리가 제공할 것은 여러 개의 패키지로 나누는 게 좋아.

```text
@memoryos/cli
@memoryos/mcp
@memoryos/harness
@memoryos/desktop
@memoryos/local-runtime
@memoryos/skills
@memoryos/capability-radar
```

하지만 사용자는 복잡하게 설치하면 안 돼.

그래서 겉으로는 하나:

```bash
npm install -g @memoryos/cli
```

안에서 필요한 것들을 관리:

```bash
mos install mcp
mos install desktop
mos install local-runtime
mos install skills
mos install adapters
```

---

# 2. CLI 이름

긴 이름보다 짧은 게 좋아.

후보:

```text
mos
mem
memoryos
cog
```

나는 **`mos`** 추천.

```bash
mos init
mos run
mos status
mos mcp start
mos desktop
mos radar scan
mos society report
```

짧고, “Memory Operating System” 느낌도 있어.

---

# 3. 설치 후 첫 경험

사용자가 설치하면 이런 flow가 떠야 해.

```bash
mos init
```

그러면 wizard가 실행됨.

```text
Welcome to MemoryOS.

✓ Checking local environment
✓ Creating ~/.memoryos
✓ Initializing local database
✓ Installing default skills
✓ Setting up MemoryOS MCP
✓ Detecting available AI CLIs
  - Claude Code: found
  - Codex CLI: found
  - Gemini CLI: found
  - Ollama: found
✓ Creating agent registry
✓ Creating tool registry
✓ Creating default routing policy

MemoryOS is ready.
```

그 다음:

```bash
mos doctor
```

출력:

```text
MemoryOS Doctor

Core:
✓ Local DB running
✓ Memory API running
✓ MCP server available

Agents:
✓ Claude Code detected
✓ Codex CLI detected
✓ Gemini CLI detected
✓ Ollama detected

Local Models:
✓ qwen3:1.7b
✓ deepseek-coder:6.7b
✓ deepseek-coder-v2:16b

Skills:
✓ memory-first-workflow
✓ conversation-to-memory-graph
✓ implementation-handoff
✓ boot-orientation

Status: Ready
```

---

# 4. Provider CLI 자동 감지

우리는 Claude, Codex, Gemini, Ollama, LM Studio 등을 감지해야 해.

```bash
mos agents detect
```

예시:

```text
Detected AI runtimes:

Claude Code
- command: claude
- status: available
- role: planner/reviewer

Codex
- command: codex
- status: available
- role: executor

Gemini CLI
- command: gemini
- status: available
- role: multimodal/general

Ollama
- command: ollama
- status: available
- local models: 5
```

그리고 자동으로 adapter 생성.

```yaml
agents:
  claude:
    adapter: claude-cli
    command: claude
    role: architect_reviewer

  codex:
    adapter: codex-cli
    command: codex
    role: implementation_agent

  gemini:
    adapter: gemini-cli
    command: gemini
    role: multimodal_reasoner

  local_qwen:
    adapter: ollama
    model: qwen3:1.7b
    role: classifier
```

---

# 5. MCP 설정 자동화

사용자는 각 provider에 MemoryOS MCP를 연결해야 해.
이것도 자동으로 도와줘야 함.

```bash
mos mcp install --for claude
mos mcp install --for codex
mos mcp install --for cursor
mos mcp install --for all
```

출력:

```text
Installing MemoryOS MCP for Claude Code...
✓ MCP config updated

Installing MemoryOS MCP for Codex...
✓ .codex/config.toml updated

Installing MemoryOS MCP for Cursor...
✓ MCP config generated

Run:
mos mcp start
```

MCP server:

```bash
mos mcp start
```

제공 tools:

```text
memory.search
project.get_state
hypergraph.search
context.build_pack
memory.write_draft
handoff.create
run.log_event
capability.recommend
workflow.find
```

---

# 6. Local Runtime 설치

local LLM은 optional이지만, 비용 절감을 위해 강하게 추천해야 해.

```bash
mos local setup
```

동작:

```text
1. Ollama 설치 여부 확인
2. 없으면 설치 안내
3. 추천 모델 pull
4. 모델별 역할 등록
```

예:

```bash
mos local pull recommended
```

내부:

```bash
ollama pull qwen3:1.7b
ollama pull deepseek-coder:6.7b
ollama pull deepseek-coder-v2:16b
```

그 다음:

```bash
mos local benchmark
```

해서 사용자 컴퓨터에서 실제 속도를 측정.

```text
Local Model Benchmark

qwen3:1.7b
- classification: 96ms
- JSON validity: 91%
- recommended role: classifier

deepseek-coder:6.7b
- log summary: good
- parser draft: good
- recommended role: code_log_worker

deepseek-coder-v2:16b
- handoff draft: fair
- code review: good
- recommended role: local_reasoning_worker
```

---

# 7. 최종 명령어 체계

## Core

```bash
mos init
mos doctor
mos status
mos config
```

## MemoryOS

```bash
mos import ./chatgpt-export.zip
mos extract
mos index
mos ask "내가 MemoryOS에서 결정한 것 보여줘"
mos memory drafts
mos memory approve
mos memory search
```

## MCP

```bash
mos mcp start
mos mcp install --for claude
mos mcp install --for codex
mos mcp list-tools
```

## Harness

```bash
mos run "작업 지시"
mos status
mos invoke claude
mos invoke codex
mos invoke local
mos verify
mos summarize
```

## CapabilityOS

```bash
mos radar scan
mos capability search "figma design to code"
mos capability gap "Figma 디자인 React 구현"
mos workflow recommend "landing page 만들기"
```

## Agent Society

```bash
mos society report
mos society propose-updates
mos society approve prop_001
mos society rollback
```

## Desktop

```bash
mos desktop
mos desktop install
mos desktop dev
```

---

# 8. 사용자가 실제로 쓰는 최종 경험

## 처음 설치

```bash
npm install -g @memoryos/cli
mos init
mos doctor
```

## 기존 AI 대화 가져오기

```bash
mos import ~/Downloads/chatgpt-export.zip
mos extract
mos index
```

## Claude/Codex에 연결

```bash
mos mcp install --for all
mos mcp start
```

## 작업 실행

```bash
mos run "ChatGPT export parser 구현하고 테스트까지 돌려줘"
```

시스템 내부:

```text
1. Local LLM이 요청 분류
2. MemoryOS가 관련 기억 검색
3. Claude가 handoff 작성
4. Codex가 구현
5. Local LLM이 로그 요약
6. Verifier가 검증
7. MemoryOS가 새 memory draft 생성
```

## 결과 확인

```bash
mos status
mos open current
mos memory drafts
```

---

# 9. Install Script 구조

`curl | bash` 설치는 이렇게.

```bash
curl -fsSL https://memoryos.dev/install.sh | bash
```

설치 스크립트가 하는 일:

```text
1. OS 감지
2. Node.js 확인
3. pnpm/npm 확인
4. @memoryos/cli 설치
5. ~/.memoryos 생성
6. 기본 config 생성
7. mos doctor 실행
```

단, 보안상 `curl | bash`는 불신하는 사람도 많으니까, 반드시 대안 제공.

```bash
npm install -g @memoryos/cli
```

또는:

```bash
brew install memoryos
```

또는:

```bash
docker run memoryos/memoryos
```

최종 배포 채널:

```text
npm
Homebrew
Docker
GitHub Releases
Desktop installer
```

---

# 10. 패키지 이름 전략

처음에는 scoped package가 좋아.

```bash
npm install -g @memoryos/cli
```

나중에 유명해지면:

```bash
npm install -g memoryos
```

패키지 구성:

```text
@memoryos/cli
- 사용자가 설치하는 메인 CLI

@memoryos/core
- memory engine

@memoryos/mcp
- MCP server

@memoryos/harness
- agent orchestration

@memoryos/skills
- default skills

@memoryos/adapters
- claude/codex/gemini/ollama adapters

@memoryos/capability
- CapabilityOS ontology/radar

@memoryos/desktop
- desktop app
```

---

# 11. 내부 설치 구조

사용자 홈:

```text
~/.memoryos/
├── config.yaml
├── agents.yaml
├── routing.yaml
├── skills/
├── runs/
├── imports/
├── db/
├── logs/
├── mcp/
└── cache/
```

프로젝트별:

```text
project/
├── AGENTS.md
├── .memoryos/
│   ├── project.yaml
│   ├── runs/
│   ├── context/
│   └── skills/
└── .codex/
    └── config.toml
```

즉 global memory와 project-local memory를 나눠야 해.

```text
Global MemoryOS:
개인 전체 기억

Project MemoryOS:
현재 repo/project 관련 기억
```

---

# 12. 우리가 provider처럼 제공하는 것

최종적으로 우리는 이런 provider가 된다.

기존 provider:

```text
Google Gemini CLI
Anthropic Claude Code
OpenAI Codex CLI
```

우리:

```text
MemoryOS CLI
```

제공하는 것:

```text
1. memory provider
2. context provider
3. capability provider
4. agent harness provider
5. local runtime provider
6. MCP provider
7. skill provider
```

즉 사용자는 이렇게 생각하면 됨.

```text
Claude = reasoning provider
Codex = coding agent provider
Gemini = multimodal provider
MemoryOS = context/capability/harness provider
```

---

# 13. README 첫 문장

이렇게 가면 좋아.

```md
# MemoryOS

Install your local memory and capability layer for AI agents.

MemoryOS wraps Claude Code, Codex, Gemini CLI, local LLMs, MCP servers, Skills, and your personal memory graph into one local-first agent operating system.
```

한국어로:

```md
# MemoryOS

AI agent를 위한 로컬 기억·능력·실행 운영체제.

MemoryOS는 Claude Code, Codex, Gemini CLI, local LLM, MCP, Skill, 개인 memory graph를 하나의 local-first agent harness로 묶어줍니다.
```

---

# 14. 가장 중요한 UX

설치 후 사용자는 이걸 느껴야 해.

```text
“이제 Claude, Codex, Gemini, local LLM을 따로따로 켜는 게 아니라,
mos가 내 작업을 이해하고 적절한 agent에게 넘겨준다.”
```

즉:

```bash
claude ...
codex ...
gemini ...
ollama ...
```

를 직접 쓰는 대신:

```bash
mos run "..."
```

으로 감싸는 것.

---

# 15. 최종 형태

최종 설치 명령:

```bash
npm install -g @memoryos/cli
```

또는:

```bash
curl -fsSL https://memoryos.dev/install.sh | bash
```

초기화:

```bash
mos init
```

AI runtime 연결:

```bash
mos agents detect
mos mcp install --for all
mos local setup
```

작업:

```bash
mos run "MemoryOS Desktop에 Hypergraph Explorer 구현"
```

탐색:

```bash
mos ask "내가 이 프로젝트에서 결정한 것 정리해줘"
mos capability gap "Figma 디자인을 React로 구현"
mos radar scan
```

관리:

```bash
mos society report
mos memory drafts
mos desktop
```

---

# 16. 한 문장으로 정리

> **우리는 Claude Code CLI, Codex CLI, Gemini CLI처럼 provider들이 모델 사용법을 감싼 방식을 모방하되, 모델 하나가 아니라 memory, capability, MCP, skill, local LLM, agent harness 전체를 감싸는 `mos` CLI를 제공해야 한다.**

최종적으로 사용자는 이렇게만 기억하면 돼.

```bash
npm install -g @memoryos/cli
mos init
mos run "내가 만들고 싶은 것"
```

그 뒤는 MemoryOS가 알아서:

```text
생각 정제
맥락 검색
능력 추천
agent 배정
작업 실행
결과 검증
기억 업데이트
```

까지 이어가게 만드는 것.
