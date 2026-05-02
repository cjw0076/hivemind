좋아. 레퍼런스를 보면 `hive` CLI는 단순 coding CLI를 따라가면 안 되고, **“작업 진행판 + agent blackboard + provider wrapper + memory/capability context”가 결합된 terminal control surface**로 설계해야 해.

아래처럼 가면 된다.

---

# 1. 참고한 CLI 디자인 패턴

## Claude Code에서 가져올 것

Claude Code는 interactive session, initial prompt, `-p` one-shot query, pipe input, resume session, MCP 관리, slash command를 제공한다. 특히 slash command는 project/user scope markdown command와 MCP prompt command를 모두 지원한다. ([Claude][1])

가져올 패턴:

```text id="gocysy"
- hive "task" shorthand
- hive -p / hive ask one-shot
- slash-command shell
- project-local commands
- MCP prompt/tool discovery
- /doctor, /status, /memory, /permissions 류
```

## Codex CLI에서 가져올 것

Codex CLI는 terminal coding agent이고, approval mode가 핵심이다. 기본 Suggest는 읽기/제안, Auto Edit는 파일 쓰기, Full Auto는 sandbox 안에서 명령 실행까지 허용한다. ([OpenAI Help Center][2])

가져올 패턴:

```text id="jz2l6m"
- approval mode를 명확히 드러내기
- read-only / workspace-write / full-auto 구분
- git repo 아닌 경우 경고
- executor는 항상 sandbox/permission 상태 표시
```

## OpenCode에서 가져올 것

OpenCode는 terminal TUI를 기본으로 하고, 현재 디렉토리나 특정 작업 디렉토리에서 시작할 수 있으며, `@file` references와 `!bash` command 패턴을 제공한다. ([OpenCode][3])

가져올 패턴:

```text id="q84djw"
- TUI-first operational surface
- @file reference
- !shell command
- 현재 작업 디렉토리 중심
```

## Aider에서 가져올 것

Aider는 terminal pair programming 도구로, codebase map, local/cloud model, git integration, diff/commit/undo loop가 강점이다. ([GitHub][4])

가져올 패턴:

```text id="98tamy"
- git diff 중심
- commit summary
- undo/rollback 감각
- repo map / codebase map
- 작업이 끝나면 변경 파일과 테스트 결과를 명확히 보여주기
```

## Continue에서 가져올 것

Continue는 PR check를 markdown 파일로 정의한다. `.continue/checks/` 또는 `.agents/checks/`에 YAML frontmatter + markdown body로 check를 두고, agent가 diff를 보고 pass/fail 판정을 낸다. ([Continue Docs][5])

가져올 패턴:

```text id="57egjy"
- markdown-as-agent-check
- .hivemind/checks/*.md
- pass/fail criteria를 사람이 파일로 관리
- check 결과를 run artifact로 저장
```

## Goose에서 가져올 것

Goose는 Desktop, CLI, API를 모두 제공하고, 70개 이상 MCP extension을 연결하는 general-purpose local agent다. 또한 extension/configure UX와 MCP 기반 extension 구조가 잘 잡혀 있다. ([Goose Docs][6])

가져올 패턴:

```text id="6ecdvk"
- CLI + Desktop + API 삼중 구조
- extension/MCP management
- provider/extension status board
- 나중에 Desktop으로 확장 가능한 CLI 구조
```

---

# 2. `hive` CLI의 정체성

`hive`는 coding agent가 아니라 **작업 운영 CLI**여야 해.

```text id="67x3ab"
Claude Code = 한 agent와 대화/작업
Codex = repo executor
Aider = pair programming
OpenCode = terminal coding agent
Goose = general local agent

hive = 여러 agent와 memory/capability/runtime을 묶는 harness control plane
```

즉 `hive`의 한 줄 정의:

> **`hive` is a terminal control plane for Hive Mind runs, multi-agent handoffs, local workers, provider CLIs, checks, and MemoryOS draft artifacts.**

한국어로:

> **`hive`는 Claude/Codex/Gemini/local LLM을 직접 대체하는 CLI가 아니라, 이들을 하나의 작업 run으로 묶는 Hive Mind 하네스 터미널이다.**

---

# 3. 전체 CLI 정보 구조

명령은 8개 그룹으로 나누자.

```text id="i5q89a"
1. Core
2. Run
3. TUI / Shell
4. Agent
5. Memory
6. Capability
7. Check / Verify
8. System / Settings
```

---

## 3.1 Core

```bash id="3der8v"
hive init
hive doctor
hive status
hive version
hive update
```

역할:

```text id="9999pt"
설치/환경/상태 확인
```

---

## 3.2 Run

```bash id="6flwm0"
hive run "task"
hive ask "task"
hive plan
hive continue
hive pause
hive resume <run_id>
hive open current
hive runs
```

역할:

```text id="3hqtm2"
작업 생성, 현재 run 관리, run folder 접근
```

`hive "task"`는 `hive ask "task"`의 shorthand로 유지.

---

## 3.3 TUI / Shell

```bash id="f3hz5g"
hive
hive tui
hive shell
```

역할:

```text id="e5foy9"
interactive control surface
```

bare `hive`는 Claude/OpenCode처럼 interactive entry로 들어가는 게 좋다.

---

## 3.4 Agent

```bash id="8gg81u"
hive agents detect
hive agents status
hive invoke local --role context
hive invoke claude --role planner
hive invoke codex --role executor
hive invoke gemini --role reviewer
hive handoff
```

역할:

```text id="5vqpef"
provider CLI/local LLM을 worker로 호출하고 artifact 저장
```

---

## 3.5 Memory

```bash id="k1vq6p"
hive memory draft
hive memory list
memoryos approve
memoryos reject
memoryos search "query"
hive context
```

역할:

```text id="tqjm9o"
run 결과를 MemoryOS memory draft로 만들고 승인
```

---

## 3.6 Capability

```bash id="lzxo4o"
capabilityos capability gap "task"
capabilityos capability recommend "task"
capabilityos radar scan
capabilityos workflow list
```

역할:

```text id="6vk0xw"
CapabilityOS가 생긴 뒤 tool/MCP/skill/workflow 추천
```

초기에는 stub만.

---

## 3.7 Check / Verify

```bash id="5l03ae"
hive check list
hive check run
hive verify
hive diff
hive review-diff
hive commit-summary
```

역할:

```text id="18ty5y"
Continue + Aider 패턴 결합
```

---

## 3.8 System / Settings

```bash id="pkctgq"
hive settings detect
hive settings shell
hive local status
hive local setup
hive mcp start
hive mcp install --for claude
hive mcp install --for codex
```

역할:

```text id="2ffjo0"
provider path, local runtime, MCP 연결 관리
```

---

# 4. Terminal UX 핵심: 3개 모드

## Mode A. One-shot

```bash id="qxfq48"
hive "Draft Review 화면 구현"
```

내부 동작:

```text id="d01vxg"
create run
→ local intent routing
→ context_pack 생성
→ Claude/Codex/Gemini/local artifacts 준비
→ status 출력
```

출력 예:

```text id="72gecg"
MemoryOS Run Created

Run      run_20260502_153012_a91c
Project  MemoryOS
Type     implementation
Phase    routed

Plan
  1. local/context-compressor  ready
  2. claude/planner            prepared
  3. codex/executor            prepared
  4. local/summarizer          pending

Next
  hive tui
  hive invoke claude --role planner --execute
  hive invoke codex --role executor --execute
```

---

## Mode B. Guided TUI

```bash id="usjh84"
hive tui
```

화면은 **run board** 중심.

```text id="g7r5re"
┌──────────────────────────────────────────────────────────────┐
│ hive / Hive Mind Harness                         Local ● MCP ○ │
├──────────────────────────────────────────────────────────────┤
│ Run     run_20260502_153012_a91c                             │
│ Task    Draft Review 화면 구현                                │
│ Phase   planning → implementation → verify → memory           │
│ Policy  workspace-write gated                                │
├───────────────────────┬──────────────────────────────────────┤
│ Agents                │ Current Artifacts                     │
│ ✓ local/context       │ task.yaml                 ok          │
│ ● claude/planner      │ context_pack.md           ok          │
│ ○ codex/executor      │ handoff.yaml              missing     │
│ ○ local/summarizer    │ verification.yaml         missing     │
│                       │ memory_drafts.json        missing     │
├───────────────────────┴──────────────────────────────────────┤
│ Latest Event                                                  │
│ 15:31 local router created routing_plan.json                   │
├───────────────────────────────────────────────────────────────┤
│ Keys: n new  a autoroute  l local  c claude  x codex          │
│       v verify  s summarize  m memory  d diff  q quit         │
└───────────────────────────────────────────────────────────────┘
```

TUI는 final product UI가 아니라 **작업 진행판**이어야 함.

---

## Mode C. Slash Shell

```bash id="3yi2oh"
hive
```

입력:

```text id="923mt7"
hive> /new Draft Review 화면 구현
hive> /route
hive> /invoke claude planner
hive> /invoke codex executor
hive> /diff
hive> /memory
```

Claude slash command처럼 익숙한 구조를 가져가되, 우리 명령은 run artifact 중심.

---

# 5. 작업 진행 순서 UI

`hive`의 핵심은 “작업이 어느 단계인지”가 보여야 하는 것.

기본 pipeline:

```text id="n2o5g2"
Intake
→ Route
→ Context
→ Deliberate
→ Handoff
→ Execute
→ Verify
→ Memory
→ Close
```

터미널에서는 이렇게 보여줘.

```text id="63tpw7"
Pipeline

[✓] Intake       task.yaml
[✓] Route        routing_plan.json
[✓] Context      context_pack.md
[●] Deliberate   claude/planner_output.md
[ ] Handoff      handoff.yaml
[ ] Execute      codex/executor_result.yaml
[ ] Verify       verification.yaml
[ ] Memory       memory_drafts.json
[ ] Close        final_report.md
```

이게 기존 coding CLI와 차별점이야.
우리는 여러 agent가 있으므로 **pipeline state**가 최우선 UI다.

---

# 6. Agent 상태 UI

각 agent는 단순 이름이 아니라 role/mode/permission을 보여줘야 해.

```text id="orpop5"
Agents

local/context-compressor
  model: qwen3:8b
  mode: local
  status: completed
  confidence: 0.82
  escalate: false

claude/planner
  mode: plan
  permission: read-only
  status: ready

codex/executor
  mode: workspace-write
  permission: approval-required
  status: waiting

gemini/reviewer
  mode: plan
  status: optional
```

Codex/Cli류에서 approval mode가 중요하듯, `hive`는 **agent별 permission/mode**를 항상 보여줘야 함. Codex의 approval mode UX를 참고하면 된다. ([OpenAI Help Center][2])

---

# 7. Artifact-first 디자인

모든 화면/명령은 artifact를 중심으로 해야 해.

```text id="wh74hm"
task.yaml
routing_plan.json
context_pack.md
handoff.yaml
provider_result.yaml
verification.yaml
memory_drafts.json
events.jsonl
final_report.md
```

`hive status`는 이 artifact completeness를 보여줘야 함.

```bash id="efd08l"
hive status
```

출력:

```text id="hq33sg"
Run: run_20260502_153012_a91c

Artifacts
  ✓ task.yaml
  ✓ routing_plan.json
  ✓ context_pack.md
  ✗ handoff.yaml
  ✗ verification.yaml
  ✗ memory_drafts.json

Missing next artifact:
  handoff.yaml

Recommended next command:
  hive invoke claude --role planner --execute
```

---

# 8. 명령어 디자인 원칙

## 8.1 짧은 happy path

사용자 기본 경험:

```bash id="ghskax"
hive "작업"
hive tui
```

## 8.2 모든 단계는 직접 실행 가능

```bash id="f6v4f0"
hive invoke local --role context
hive invoke claude --role planner
hive invoke codex --role executor
hive verify
hive memory draft
```

## 8.3 항상 dry-run 가능

```bash id="4jbn0a"
hive invoke codex --role executor --dry-run
```

Provider CLI가 불안정해도 artifact는 생성되어야 한다.

## 8.4 JSON output 필수

```bash id="l9wej5"
hive run -q --json "task"
hive status --json
hive agents detect --json
hive check run --json
```

다른 agent가 `hive`를 호출할 수 있어야 하니까.

## 8.5 위험한 모드는 명시적이어야 함

```bash id="ngljb2"
hive invoke codex --role executor --execute --mode workspace-write
hive invoke codex --role executor --execute --mode danger --confirm-danger
```

기본은 safe.

---

# 9. `hive`의 slash commands

Claude의 slash command 패턴을 참고해서, 우리는 이렇게 간다.

```text id="0s1wrl"
/new <task>          새 run 생성
/status              현재 run 상태
/route               routing plan 보기
/context             context pack 열기
/handoff             handoff 보기
/local <role>        local worker 호출
/claude <role>       Claude artifact 생성/실행
/codex <role>        Codex artifact 생성/실행
/gemini <role>       Gemini artifact 생성/실행
/verify              verification 생성
/diff                git diff report
/review-diff         local/code model diff review
/memory              memory draft 생성
/check               markdown checks 실행
/summary             final report 갱신
/open                run folder 열기
```

나중에는 project-local command도 가능.

```text id="rmsucu"
.hivemind/commands/
  draft-review.md
  parser-work.md
  capability-card.md
```

이건 Claude custom slash command에서 가져올 패턴이다. ([Claude API Docs][7])

---

# 10. `@file`, `!shell` 지원

OpenCode처럼 `@file`과 `!shell`은 강력하다. ([OpenCode][3])

`hive` shell에서:

```text id="qjkljz"
hive> @docs/TODO.md 다음 작업 3개 뽑아줘
hive> !git status
hive> 이 diff를 review-diff로 보내줘
```

다만 `!shell`은 event log에 반드시 기록.

```json id="64e9bt"
{"type":"shell_command","command":"git status","actor":"user","run_id":"..."}
```

---

# 11. Check 디자인

Continue 패턴을 그대로 가져오자. ([Continue Docs][5])

```text id="l5h1hk"
.hivemind/checks/
  no-raw-export-leak.md
  memory-draft-policy.md
  schema-change-safety.md
  quantum-boundary.md
```

예:

```md id="9yzv72"
---
name: Memory Draft Policy
description: Ensure memory writes are draft-first and include raw_refs
---

Fail if a code change:
- commits memory directly without draft review
- creates memory records without raw_refs
- mixes user-origin and assistant-origin ideas
```

명령:

```bash id="wwrjgm"
hive check list
hive check run
```

출력:

```text id="4gxf14"
Checks

✓ Quantum Boundary
✗ Memory Draft Policy
  Reason: memory_drafts.json lacks raw_refs for 2 entries.
  Suggested fix: add raw_refs from .runs/<run_id>/...
```

---

# 12. Git-first Loop

Aider에서 가져올 패턴. ([GitHub][4])

```bash id="pvbegz"
hive diff
hive review-diff
hive commit-summary
```

출력:

```text id="c6jfb7"
Changed Files
  M hivemind/hive.py
  A tests/fixtures/exports/chatgpt_redacted.json

Risk
  medium: parser path changed
  low: docs only

Suggested Commit
  feat(parser): add redacted ChatGPT fixture and parser metadata
```

`hive`가 직접 commit하는 것은 나중. 초기에는 commit message 제안까지만.

---

# 13. Provider Extension 디자인

Goose처럼 extension/provider를 설정 가능하게 한다. ([Goose Docs][6])

```bash id="ui39mb"
hive agents detect
hive agents configure
hive mcp install --for claude
hive mcp install --for codex
hive extension list
```

출력:

```text id="4o294w"
Providers

Claude
  command: /home/user/.local/bin/claude
  mode: execute_supported
  roles: planner, critic

Codex
  command: /home/user/bin/codex
  mode: prepare_only
  roles: executor, reviewer

Gemini
  command: /home/user/.nvm/.../gemini
  mode: execute_supported
  roles: reviewer, alternate-planner

Ollama
  wrapper: scripts/ollama-local.sh
  models: qwen3:1.7b, qwen3:8b, deepseek-coder:6.7b
```

---

# 14. Terminal 색상/시각 디자인

과하게 꾸미지 말고, 상태 중심.

```text id="9n2jcq"
✓ completed     green
● running       cyan
○ pending       gray
! warning       yellow
✗ failed        red
◆ decision      violet
◇ optional      dim
```

Run board:

```text id="1qpw0m"
Hive Mind Harness
────────────────────────────────────────────
Run      run_20260502_153012_a91c
Task     Add provider validation
Project  MemoryOS
Mode     safe / read-only default

Pipeline
✓ intake      ✓ route       ✓ context
● handoff     ○ execute     ○ verify     ○ memory

Agents
✓ local/context       qwen3:8b       conf 0.82
● claude/planner      plan           running
○ codex/executor      prepare_only   waiting

Next
hive invoke claude --role planner --execute
```

---

# 15. MVP CLI 설계

지금 바로 구현/정리할 v0.1 design은 이거야.

## Default Happy Path

```bash id="dc893z"
hive "작업 내용"
hive tui
```

## Manual Step Path

```bash id="7mw5w0"
hive ask "작업 내용"
hive plan
hive invoke local --role context
hive invoke claude --role planner --execute
hive invoke codex --role executor --dry-run
hive verify
hive memory draft
hive summarize
```

## Review Path

```bash id="ele2jl"
hive diff
hive review-diff
hive check run
hive commit-summary
```

## Environment Path

```bash id="8vk5vt"
hive init
hive doctor
hive agents detect
hive local status
hive settings shell
```

---

# 16. 우리가 추가해야 할 차별점

기존 reference와 다른 우리만의 핵심은 이거야.

```text id="o7uk7y"
1. Multi-agent pipeline state가 보인다.
2. Provider CLI를 worker로 감싼다.
3. MemoryOS context pack을 항상 사용한다.
4. CapabilityOS 추천이 나중에 붙는다.
5. 모든 것이 .runs artifact로 남는다.
6. local LLM이 중간 정리자 역할을 한다.
7. TODO/route/source provenance와 연결된다.
```

그래서 `hive`는 일반 CLI보다 **작업 추적성과 agent handoff 품질**이 중요해.

---

# 17. 다음 개선 제안

현재 Hive Mind repo 기준으로는 이미 `hive` 명령이 많이 있으니, 다음은 디자인을 더 굳히는 작업이 좋다.

```text id="q77kwl"
1. `hive status`를 pipeline board 형태로 개선
2. `hive tui`에서 pipeline phase를 상단 고정
3. `hive invoke` 결과를 provider cards로 정리
4. `hive check run` 결과를 pass/fail table로 정리
5. `hive next` 명령 추가
```

특히 `hive next`가 있으면 좋아.

```bash id="pccwir"
hive next
```

출력:

```text id="6ftysu"
Next recommended action:
  hive invoke claude --role planner --execute

Reason:
  handoff.yaml is missing and task_type=implementation.
```

이게 multi-agent harness에서는 매우 중요하다.

---

# 18. 최종 CLI 철학

> **`hive` should always answer: What is the current task? Where are we in the pipeline? Which agent should act next? What artifacts exist? What is safe to do now?**

한국어로:

> **`hive`는 항상 “현재 작업이 무엇이고, 어느 단계이며, 다음에 어떤 agent가 무엇을 해야 하고, 어떤 산출물이 남았는지”를 보여줘야 한다.**

그래서 터미널 디자인의 중심은 채팅창이 아니라:

```text id="ljtk6z"
Run
Pipeline
Agents
Artifacts
Checks
Next Action
```

이 6개다.

[1]: https://code.claude.com/docs/en/cli-reference?utm_source=chatgpt.com "CLI reference - Claude Code Docs"
[2]: https://help.openai.com/en/articles/11096431-openai-codex-cli-getting-started?utm_source=chatgpt.com "OpenAI Codex CLI – Getting Started | OpenAI Help Center"
[3]: https://opencode.ai/docs/tui/?utm_source=chatgpt.com "TUI | OpenCode"
[4]: https://github.com/aider-ai/aider?utm_source=chatgpt.com "GitHub - Aider-AI/aider: aider is AI pair programming in your terminal · GitHub"
[5]: https://docs.continue.dev/checks/reference?utm_source=chatgpt.com "Check File Reference | Continue Docs"
[6]: https://goose-docs.ai/?utm_source=chatgpt.com "goose | Your open source AI agent"
[7]: https://docs.claude.com/en/docs/claude-code/slash-commands?utm_source=chatgpt.com "Slash commands - Claude Docs"
