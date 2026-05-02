좋아. 최종 배포 형태는 딱 그 방향이 맞아.

우리가 제공해야 하는 건 단순 앱이 아니라:

> **사용자가 자기 컴퓨터에 설치하면 Hive Mind가 MemoryOS + CapabilityOS + MCP + local runtime을 연결하는 “AI 작업 운영체제”**

즉, 설치 경험은 이렇게 가야 해.

```bash
npm install -g @hive-mind/hive
```

또는:

```bash
curl -fsSL https://hive-mind.dev/install.sh | bash
```

그리고 사용자는 이렇게 시작하는 거야.

```bash
hive init
hive doctor
memoryos import ./chatgpt-export.zip
hive mcp start
hive run "MemoryOS Desktop Draft Review 화면 구현"
```

---

# 1. 최종 패키지 형태

우리가 제공할 것은 여러 개의 패키지로 나누는 게 좋아.

```text
@hive-mind/hive
@memoryos/mcp
@memoryos/desktop
@hive-mind/local-runtime
@hive-mind/skills
@capabilityos/radar
```

하지만 사용자는 복잡하게 설치하면 안 돼.

그래서 겉으로는 하나:

```bash
npm install -g @hive-mind/hive
```

안에서 필요한 것들을 관리:

```bash
hive install mcp
hive install desktop
hive install local-runtime
hive install skills
hive install adapters
```

---

# 2. CLI 이름

긴 이름보다 짧은 게 좋아.

후보:

```text
hive
mem
memoryos
cog
```

나는 **`hive`** 추천.

```bash
hive init
hive run
hive status
hive mcp start
hive cockpit
capabilityos radar scan
hive society report
```

짧고, swarm runtime 정체성이 분명하다. `memoryos`는 기억 substrate CLI 이름으로 남긴다.

---

# 3. 설치 후 첫 경험

사용자가 설치하면 이런 flow가 떠야 해.

```bash
hive init
```

그러면 wizard가 실행됨.

```text
Welcome to Hive Mind.

✓ Checking local environment
✓ Creating ~/.hivemind
✓ Initializing Hive Mind run blackboard
✓ Installing default skills
✓ Checking MemoryOS MCP connection
✓ Detecting available AI CLIs
  - Claude Code: found
  - Codex CLI: found
  - Gemini CLI: found
  - Ollama: found
✓ Creating agent registry
✓ Creating provider/tool registry
✓ Creating default routing policy

Hive Mind is ready.
```

그 다음:

```bash
hive doctor
```

출력:

```text
Hive Mind Doctor

Core:
✓ Run blackboard available
✓ Provider registry available
✓ MemoryOS MCP reachable

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
hive agents detect
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
hive mcp install --for claude
hive mcp install --for codex
hive mcp install --for cursor
hive mcp install --for all
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
hive mcp start
```

MCP server:

```bash
hive mcp start
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
hive local setup
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
hive local pull recommended
```

내부:

```bash
ollama pull qwen3:1.7b
ollama pull deepseek-coder:6.7b
ollama pull deepseek-coder-v2:16b
```

그 다음:

```bash
hive local benchmark
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
hive init
hive doctor
hive status
hive config
```

## MemoryOS

```bash
memoryos import ./chatgpt-export.zip
memoryos extract
memoryos index
hive ask "내가 MemoryOS에서 결정한 것 보여줘"
hive memory drafts
memoryos approve
memoryos search
```

## MCP

```bash
hive mcp start
hive mcp install --for claude
hive mcp install --for codex
hive mcp list-tools
```

## Harness

```bash
hive run "작업 지시"
hive status
hive invoke claude
hive invoke codex
hive invoke local
hive verify
hive summarize
```

## CapabilityOS

```bash
capabilityos radar scan
capabilityos capability search "figma design to code"
capabilityos capability gap "Figma 디자인 React 구현"
capabilityos workflow recommend "landing page 만들기"
```

## Agent Society

```bash
hive society report
hive society propose-updates
hive society approve prop_001
hive society rollback
```

## Desktop

```bash
hive cockpit
hive cockpit install
hive cockpit dev
```

---

# 8. 사용자가 실제로 쓰는 최종 경험

## 처음 설치

```bash
npm install -g @hive-mind/hive
hive init
hive doctor
```

## 기존 AI 대화 가져오기

```bash
memoryos import ~/Downloads/chatgpt-export.zip
memoryos extract
memoryos index
```

## Claude/Codex에 연결

```bash
hive mcp install --for all
hive mcp start
```

## 작업 실행

```bash
hive run "ChatGPT export parser 구현하고 테스트까지 돌려줘"
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
hive status
hive open current
hive memory drafts
```

---

# 9. Install Script 구조

`curl | bash` 설치는 이렇게.

```bash
curl -fsSL https://hive-mind.dev/install.sh | bash
```

설치 스크립트가 하는 일:

```text
1. OS 감지
2. Node.js 확인
3. pnpm/npm 확인
4. @hive-mind/hive 설치
5. ~/.hivemind 생성
6. 기본 config 생성
7. hive doctor 실행
```

단, 보안상 `curl | bash`는 불신하는 사람도 많으니까, 반드시 대안 제공.

```bash
npm install -g @hive-mind/hive
```

또는:

```bash
brew install hive-mind
```

또는:

```bash
docker run hive-mind/hive
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
npm install -g @hive-mind/hive
```

나중에 유명해지면 Hive Mind 단축 패키지를 별도로 둘 수 있다:

```bash
npm install -g hive
```

패키지 구성:

```text
@hive-mind/hive
- 사용자가 설치하는 메인 CLI

@memoryos/core
- memory engine

@memoryos/mcp
- MCP server

@hive-mind/runtime
- agent orchestration internals

@hive-mind/skills
- default skills

@hive-mind/adapters
- claude/codex/gemini/ollama adapters

@capabilityos/core
- CapabilityOS ontology/radar

@memoryos/desktop
- desktop app
```

---

# 11. 내부 설치 구조

사용자 홈:

```text
~/.hivemind/
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
├── .hivemind/
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
현재 MemoryOS project 관련 기억
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
Hive Mind = harness provider; MemoryOS = memory provider; CapabilityOS = capability provider
```

---

# 13. README 첫 문장

이렇게 가면 좋아.

```md
# Hive Mind

Coordinate your local AI agent swarm with MemoryOS and CapabilityOS context.

Hive Mind wraps Claude Code, Codex, Gemini CLI, local LLMs, MCP servers, skills, and MemoryOS/CapabilityOS context into one local-first swarm runtime.
```

한국어로:

```md
# Hive Mind

AI agent를 위한 로컬 군체지성 실행 런타임.

Hive Mind는 Claude Code, Codex, Gemini CLI, local LLM, MCP, Skill을 MemoryOS 기억과 CapabilityOS 능력 지도 위에서 하나의 local-first agent harness로 묶어줍니다.
```

---

# 14. 가장 중요한 UX

설치 후 사용자는 이걸 느껴야 해.

```text
“이제 Claude, Codex, Gemini, local LLM을 따로따로 켜는 게 아니라,
hive가 내 작업을 이해하고 적절한 agent에게 넘겨준다.”
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
hive run "..."
```

으로 감싸는 것.

---

# 15. 최종 형태

최종 설치 명령:

```bash
npm install -g @hive-mind/hive
```

또는:

```bash
curl -fsSL https://hive-mind.dev/install.sh | bash
```

초기화:

```bash
hive init
```

AI runtime 연결:

```bash
hive agents detect
hive mcp install --for all
hive local setup
```

작업:

```bash
hive run "MemoryOS Desktop에 Hypergraph Explorer 구현"
```

탐색:

```bash
hive ask "내가 이 프로젝트에서 결정한 것 정리해줘"
capabilityos capability gap "Figma 디자인을 React로 구현"
capabilityos radar scan
```

관리:

```bash
hive society report
hive memory drafts
hive cockpit
```

---

# 16. 한 문장으로 정리

> **우리는 Claude Code CLI, Codex CLI, Gemini CLI처럼 provider들이 모델 사용법을 감싼 방식을 모방하되, 모델 하나가 아니라 memory, capability, MCP, skill, local LLM, agent harness 전체를 감싸는 `hive` CLI를 제공해야 한다.**

최종적으로 사용자는 이렇게만 기억하면 돼.

```bash
npm install -g @hive-mind/hive
hive init
hive run "내가 만들고 싶은 것"
```

그 뒤는 Hive Mind가 orchestration을 맡고, MemoryOS/CapabilityOS가 각각 기억과 능력 지도를 제공한다:

```text
의도 정제
MemoryOS 맥락 검색
CapabilityOS 능력 추천
agent 배정
작업 실행
결과 검증
memory draft artifact 생성
기억 업데이트
```

까지 이어가게 만드는 것.
