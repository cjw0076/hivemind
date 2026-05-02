맞아. 이제부터는 **wrapper CLI/UI가 필요해.**
다만 처음부터 거대한 Desktop을 만들 필요는 없고, 지금 쓰는 “공유 폴더 + 작업 로그” 방식을 정식화해서 **Harness CLI**로 만들면 돼.

핵심 구조는 이거야.

```text
지금:
Claude CLI 따로
Codex CLI 따로
공유 폴더에 logs/tasks.md 남김

다음:
memory-os run
→ wrapper CLI가 task/run/handoff/log/context를 관리
→ Claude/Codex/local LLM은 worker처럼 호출
→ 모든 결과는 Run State와 Event Log에 저장
```

---

# 1. 결론: Wrapper CLI가 있어야 함

필요한 이름은 이런 식이면 돼.

```bash
hive
memory-os
agent-harness
cog
```

예를 들어:

```bash
hive run "MemoryOS Desktop에 Draft Review 화면 구현"
```

그러면 내부에서:

```text
1. task 생성
2. MemoryOS context 검색
3. local LLM이 요청 정리
4. Chatbot Harness가 필요하면 deliberation
5. Claude에게 handoff 작성 요청
6. Codex에게 구현 요청
7. local LLM이 로그 요약
8. memory draft 생성
9. 결과를 run 폴더와 DB에 저장
```

이렇게 흘러가야 해.

---

# 2. 기존 공유 폴더 방식은 좋은 출발점임

네가 지금 하는 방식:

```text
/shared
  task.md
  claude_thought.md
  codex_result.md
  logs.md
  decisions.md
```

이건 사실상 아주 원시적인 **agent blackboard**야.

이걸 정식화하면:

> **Blackboard Workspace**

가 된다.

```text
각 agent는 직접 서로 대화하지 않고,
공통 작업판에 자기 결과를 남긴다.
Harness가 다음 agent에게 넘긴다.
```

즉, 기존 방식을 버리지 말고 이렇게 구조화해.

```text
.runs/
  run_2026_05_02_001/
    task.yaml
    context_pack.md
    handoff/
      claude_to_codex.yaml
    agents/
      claude/
        output.md
        events.jsonl
      codex/
        output.md
        diff.patch
        test.log
      local/
        summary.json
        memory_drafts.json
    artifacts/
    final_report.md
    run_state.json
```

---

# 3. 최종 소통 단위는 “채팅”이 아니라 Artifact여야 함

agent끼리 자유롭게 대화시키면 흐려져.
소통 단위는 반드시 구조화된 artifact여야 해.

필수 artifact는 6개.

```text
1. Task Spec
2. Context Pack
3. Agent Handoff
4. Agent Result
5. Verification Report
6. Memory Draft
```

---

## 3.1 Task Spec

사용자 요청을 정리한 최초 작업 명세.

```yaml
run_id: run_001
user_request: "Draft Review 화면 구현"
project: MemoryOS
task_type: implementation
goal: "Memory draft를 승인/수정/거절할 수 있는 Desktop 화면 구현"
priority: high
status: planned
```

---

## 3.2 Context Pack

MemoryOS에서 꺼낸 관련 맥락.

```md
# Context Pack

## Project State
MemoryOS v0.1 is focused on:
- ChatGPT import
- memory draft review
- ask memory
- MCP search

## Active Decisions
- Memory write is draft-first.
- User-origin and assistant-origin must be separated.
- Every memory must show raw_refs.

## Relevant Concepts
- Draft Review
- Memory Hygiene
- Origin Separation
```

---

## 3.3 Agent Handoff

Claude가 Codex에게 넘기는 작업 계약서.

```yaml
from_agent: claude
to_agent: codex
objective: "Implement Draft Review screen"
files_to_create:
  - apps/desktop/src/routes/DraftReview.tsx
  - apps/desktop/src/components/drafts/DraftCard.tsx
constraints:
  - "Show type, origin, confidence, raw_refs"
  - "Do not auto-commit drafts"
  - "Use mock API if backend not ready"
acceptance_criteria:
  - "Draft list visible"
  - "Accept/Edit/Reject controls exist"
  - "Raw refs inspector visible"
```

---

## 3.4 Agent Result

Codex가 남기는 결과.

```yaml
agent: codex
status: completed
changed_files:
  - apps/desktop/src/routes/DraftReview.tsx
  - apps/desktop/src/components/drafts/DraftCard.tsx
commands_run:
  - pnpm typecheck
  - pnpm lint
test_result: passed
unresolved:
  - "Needs real API integration later"
```

---

## 3.5 Verification Report

검증 agent나 local LLM이 정리.

```yaml
verdict: pass_with_notes
checks:
  typecheck: pass
  lint: pass
  acceptance_criteria: partial
issues:
  - "Edit modal is stubbed"
  - "Raw ref preview uses mock data"
risk_level: low
```

---

## 3.6 Memory Draft

이번 작업에서 새로 생긴 기억.

```json
{
  "type": "decision",
  "content": "Draft Review screen should always expose raw_refs before commit.",
  "origin": "mixed",
  "project": "MemoryOS",
  "confidence": 0.91,
  "status": "draft",
  "raw_refs": ["run_001/final_report.md"]
}
```

---

# 4. Wrapper CLI의 핵심 명령어

처음엔 이 정도면 충분해.

```bash
hive init
hive run "<task>"
hive status
hive context
hive handoff
hive invoke claude
hive invoke codex
hive invoke local
hive verify
hive summarize
hive memory draft
hive memory commit
hive open
```

실제 흐름:

```bash
hive run "ChatGPT export parser 구현"
```

자동 생성:

```text
.runs/run_001/task.yaml
.runs/run_001/context_pack.md
.runs/run_001/run_state.json
```

Claude에게 계획 요청:

```bash
hive invoke claude --role planner
```

Codex에게 구현 요청:

```bash
hive invoke codex --role executor
```

local LLM으로 결과 요약:

```bash
hive invoke local --role log-summarizer
```

검증:

```bash
hive verify
```

memory draft 생성:

```bash
hive memory draft
```

최종 리포트:

```bash
hive summarize
```

---

# 5. Wrapper CLI UI는 어떻게 생겨야 하나

초기에는 TUI가 좋다. Desktop보다 빠르고, CLI workflow와 잘 맞아.

```text
┌─────────────────────────────────────────────────────┐
│ Hive Mind Harness                                    │
├─────────────────────────────────────────────────────┤
│ Run: run_001                                        │
│ Task: Draft Review 화면 구현                         │
│ Project: MemoryOS                                   │
│ Phase: implementation                               │
├─────────────────────────────────────────────────────┤
│ Agents                                              │
│ ✓ local-context-compressor                          │
│ ✓ claude-planner                                    │
│ ● codex-executor running                            │
│ ○ local-log-summarizer                              │
│ ○ verifier                                          │
├─────────────────────────────────────────────────────┤
│ Context                                             │
│ 12 memories used                                    │
│ 3 active decisions                                  │
│ 2 open questions                                    │
├─────────────────────────────────────────────────────┤
│ Latest Event                                        │
│ Codex modified 3 files and is running typecheck.    │
└─────────────────────────────────────────────────────┘
```

기술적으로는:

```text
Node.js:
- commander
- inquirer
- blessed / ink

Python:
- typer
- rich
- textual
```

추천은 **Node/TypeScript + Ink** 또는 **Python + Textual**.
MemoryOS가 TypeScript 쪽이면 `Ink`가 자연스럽고, Python worker가 많으면 `Textual`도 좋아.

---

# 6. 내부 구조

```text
services/harness/
  src/
    cli/
      index.ts
      commands/
        run.ts
        invoke.ts
        status.ts
        verify.ts
        summarize.ts
    core/
      run-manager.ts
      context-builder.ts
      router.ts
      event-log.ts
      handoff-manager.ts
    adapters/
      claude-cli.ts
      codex-cli.ts
      local-llm.ts
    schemas/
      task-spec.ts
      handoff.ts
      agent-result.ts
      run-event.ts
```

---

# 7. Local LLM이 들어오면 무엇이 바뀌나

지금은 사람이 공유 폴더를 읽고 정리하고 있지?

local LLM이 들어오면 이걸 대신해.

```text
사람이 하던 일:
- claude 결과 읽기
- codex 결과 읽기
- 뭐가 바뀌었는지 정리
- 다음 지시 만들기
- memory에 남길 것 찾기

local LLM worker:
- 로그 요약
- diff 요약
- memory draft 생성
- handoff 초안 생성
- context 압축
- 실패 원인 분류
```

즉 local LLM은 **agent들 사이의 서기/비서/정리자**야.

역할 이름으로는:

```text
Local Clerk
Run Summarizer
Context Compressor
Handoff Drafter
Memory Curator
```

---

# 8. 최종 소통 방식

agent 간 소통은 이렇게 가야 해.

```text
Agent가 직접 다른 Agent에게 말하지 않는다.

Agent
→ 자기 결과를 artifact로 남긴다.
→ Harness가 읽는다.
→ 필요하면 local LLM이 요약한다.
→ 다음 Agent에게 handoff로 전달한다.
```

즉:

```text
Claude ↔ Codex 직접 대화 ❌

Claude → Handoff Artifact → Harness → Codex ⭕
Codex → Result Artifact → Harness → Claude Reviewer ⭕
```

이 방식이 좋은 이유:

```text
1. 로그가 남음
2. 재실행 가능
3. 디버깅 가능
4. memory update 가능
5. 비용 통제 가능
6. agent hallucination이 덜 전염됨
```

---

# 9. Run Folder는 계속 유지해라

DB만 쓰면 사람이 보기 어렵고, git으로 추적하기도 애매해.

그래서 둘 다 써.

```text
DB:
- 검색
- 상태 관리
- memory graph
- event log query

Run Folder:
- 사람이 보기
- agent에게 파일로 주기
- 재현 가능성
- artifact 보존
```

추천:

```text
.runs/
  current -> run_2026_05_02_001
  run_2026_05_02_001/
```

그리고 CLI에서:

```bash
hive open current
```

하면 폴더를 열어준다.

---

# 10. Desktop은 언제 필요한가

처음부터 Desktop까지 가지 마.

순서는:

```text
1. 공유 폴더 규격화
2. Wrapper CLI
3. TUI status
4. MemoryOS DB/MCP 연결
5. Desktop Cockpit
```

Desktop은 나중에:

```text
- run graph 보기
- agent 상태 보기
- memory draft 승인
- handoff 편집
- capability 추천
```

에 필요해.

지금 당장은 **Wrapper CLI + Run Folder + TUI**가 맞다.

---

# 11. 바로 만들 MVP

첫 버전은 딱 이 정도.

```bash
hive run "작업 내용"
```

생성:

```text
.runs/run_xxx/
  task.yaml
  context_pack.md
  handoff.yaml
  events.jsonl
  final_report.md
```

명령:

```bash
hive invoke local --role context
hive invoke claude --role planner
hive invoke codex --role executor
hive invoke local --role summarize
hive status
```

---

# 12. `events.jsonl` 예시

```jsonl
{"ts":"2026-05-02T10:00:00+09:00","type":"run_created","run_id":"run_001","task":"Draft Review 화면 구현"}
{"ts":"2026-05-02T10:01:00+09:00","type":"context_built","memories_used":12}
{"ts":"2026-05-02T10:04:00+09:00","type":"agent_started","agent":"claude","role":"planner"}
{"ts":"2026-05-02T10:08:00+09:00","type":"handoff_created","from":"claude","to":"codex"}
{"ts":"2026-05-02T10:09:00+09:00","type":"agent_started","agent":"codex","role":"executor"}
{"ts":"2026-05-02T10:20:00+09:00","type":"files_changed","agent":"codex","files":["DraftReview.tsx"]}
{"ts":"2026-05-02T10:22:00+09:00","type":"tests_run","status":"passed"}
{"ts":"2026-05-02T10:25:00+09:00","type":"memory_drafts_created","count":3}
```

이게 나중에 MemoryOS로 들어가서 `AgentRunEvent` hyperedge가 된다.

---

# 13. 제일 중요한 설계 원칙

## 1. 사람은 `hive`만 보면 된다

Claude CLI, Codex CLI를 매번 직접 켜지 않는 방향으로 가야 해.

```bash
hive run
hive status
hive approve
hive continue
```

---

## 2. Agent들은 파일 artifact로 소통한다

자연어 채팅이 아니라 artifact.

```text
task.yaml
handoff.yaml
result.yaml
verification.yaml
memory_drafts.json
```

---

## 3. Local LLM은 사이사이 정리자다

비싼 모델에게 넘기기 전에 압축하고, 실행 후 정리한다.

---

## 4. 모든 작업은 run_id를 가진다

run_id가 없으면 memory와 trace가 끊긴다.

---

## 5. Agent가 한 말보다 검증 결과가 우선이다

```text
Codex says success ❌
tests passed + files changed + acceptance met ⭕
```

---

# 14. 네 현재 방식에서 다음으로 바꿀 것

지금:

```text
공유 폴더에 사람이 임의로 로그 작성
```

다음:

```text
공유 폴더 구조 고정
CLI가 자동 생성
local LLM이 자동 요약
Claude/Codex 호출 결과가 자동 저장
```

즉, 진화는 이거야.

```text
Manual shared folder
→ Structured blackboard
→ Harness CLI
→ TUI
→ Desktop cockpit
```

---

# 15. 최종 답

응, **wrapper CLI UI가 필요하다.**

하지만 그 목적은 Claude/Codex/local LLM을 “한 채팅창에 합치는 것”이 아니야.

목적은:

> **여러 독립 CLI와 local runtime을 하나의 Run State, Event Log, Handoff Artifact, MemoryOS Context로 묶는 것.**

최종적으로 사람은 이렇게 작업해야 해.

```bash
hive run "MemoryOS에 Capability Radar 화면 추가"
```

그러면 시스템이 알아서:

```text
local LLM이 context 압축
Claude가 계획/명세 작성
Codex가 구현
local LLM이 로그 요약
Verifier가 확인
MemoryOS가 기억
CapabilityOS가 workflow 업데이트
```

하게 만드는 것.

한 문장으로:

> **지금의 공유 폴더는 agent blackboard의 원형이고, 다음 단계는 그것을 Harness CLI가 관리하는 구조화된 작업판으로 승격시키는 것이다.**
