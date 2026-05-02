<!--
Source: docs/memoryOS.md
Source lines: 7701-8329
Source byte range: 219140-238844
Split title source: numbered-section
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 012: 8. Settings

Provenance: `docs/memoryOS.md` lines `7701-8329`, bytes `219140-238844`.

Local structure markers:

- Source line 7701: 8. Settings
- Source line 7723: 1. Import Center
- Source line 7724: 2. Draft Review
- Source line 7725: 3. Ask Memory
- Source line 7726: 4. Home
- Source line 7727: 5. Project Memory
- Source line 7731: 20. Desktop의 진짜 차별점
- Source line 7756: 21. 가장 중요한 Desktop UX 원칙
- Source line 7757: 1. 사용자가 통제감을 느껴야 함
- Source line 7760: 2. 근거가 보여야 함
- Source line 7762: 3. 복잡함은 접혀 있어야 함
- Source line 7768: 4. Graph는 장식이 아니라 탐색 도구여야 함

---

8. Settings

Initial Desktop MVP:
- Home dashboard
- Import Center
- Draft Review
- Ask Memory
- MCP status
- simple Project Memory page

Visual direction:
- dark calm cognitive cockpit
- warm charcoal background
- subtle grid
- translucent rounded cards
- soft violet/cyan/amber/green accents
- graph nodes with subtle glow
- left sidebar + central workspace + right inspector
- technical but not overwhelming

Do not overbuild graph visualization first.
Prioritize:
1. Import Center
2. Draft Review
3. Ask Memory
4. Home
5. Project Memory

The desktop should connect to the local MemoryOS API and MCP server.
Use mock data first if backend is not ready, but keep API boundaries clean.
20. Desktop의 진짜 차별점
대부분 memory app은 이런 식이야.

문서 저장
검색
태그
그래프 보기
MemoryOS Desktop은 달라야 해.

내 AI 대화가 어떻게 memory가 되는지 보인다.
memory가 agent에게 어떻게 전달되는지 보인다.
agent가 어떤 기억을 근거로 작업했는지 보인다.
새 memory가 들어오기 전에 내가 승인할 수 있다.
프로젝트의 현재 상태가 자동으로 유지된다.
즉, 핵심은 보이는 memory pipeline이야.

Raw Conversation
→ Pair
→ Segment
→ Draft Memory
→ Hyperedge
→ Project State
→ Agent Context
이 pipeline을 시각적으로 보여주는 것이 Desktop의 핵심이다.

21. 가장 중요한 Desktop UX 원칙
1. 사용자가 통제감을 느껴야 함
AI가 내 기억을 마음대로 쓰는 게 아니라,
내가 승인하고 조작한다.
2. 근거가 보여야 함
모든 답변은 raw_refs / memory / hyperedge 근거를 보여준다.
3. 복잡함은 접혀 있어야 함
처음엔 간단히:
“36 memories extracted”

펼치면 자세히:
type, origin, confidence, raw_refs, hyperedge members
4. Graph는 장식이 아니라 탐색 도구여야 함
예쁘기만 한 graph는 버려야 함.
Graph에서 클릭하면 반드시 이런 게 나와야 해.

이 concept가 나온 대화
관련 decision
관련 project
관련 action
충돌 memory
agent가 사용한 기록
5. Agent가 memory를 쓴 흔적이 남아야 함
Codex used:
- mem_123
- he_456
- project_state_memoryos

Result:
- implemented parser
- created 3 memory drafts
이게 신뢰를 만든다.

22. 최종 Desktop 그림
최종적으로 사용자는 이렇게 느껴야 해.

내 모든 AI 대화가 로컬에서 정리된다.
내 생각과 AI 제안이 분리된다.
내 프로젝트별 결정과 질문이 유지된다.
Claude/Codex/local agent가 이 기억을 꺼내 쓴다.
나는 어떤 기억이 저장되고 사용되는지 볼 수 있다.
한 문장으로:

MemoryOS Desktop은 내 AI memory graph를 보는 창이자, agent들이 내 기억을 안전하게 사용하는 관제실이다.

처음 Desktop MVP는 화려한 graph보다 이 3개에 집중해.

1. Import가 잘 된다.
2. Draft Review로 memory 품질을 통제한다.
3. Ask Memory에서 바로 가치가 보인다.
Hypergraph Explorer는 제품의 상징이지만, v0.1에서는 간단한 preview 정도로 시작하고, 진짜 visual graph는 v0.2~v0.3에서 밀어붙이는 게 좋아.


네가 생각하는 데스크탑 앱 비주얼 이미지 보드 생성해봐. 

편집


Cli로 codex, claude, ...각자 쓰면 서로 독립된 환경이라 agent loop를 못만들지 않나? Api만 가져다 쓰면 provider가 제공하는 기능들을 못쓰고. 방법이있나?

맞아. 그냥 CLI를 각각 따로 띄우면 프로세스·세션·파일 권한·메모리가 분리돼서 “진짜 agent loop”가 깨지기 쉬워. 해결책은 둘 중 하나를 고르는 게 아니라, CLI를 하위 실행자(worker)로 감싸는 상위 harness를 두는 방식이야. 최신 CLI/MCP 연결 방식 기준으로 현실적인 패턴을 확인해서 정리할게.

13s 동안 생각함
맞아. CLI를 각각 따로 쓰면 기본적으로 독립된 세계라서 agent loop가 안 만들어진다.
그런데 방법은 있어.

핵심은 이거야.

Claude CLI, Codex CLI, local LLM CLI를 직접 “서로 대화시키는 것”이 아니라, 상위 Harness가 각 CLI를 headless worker로 호출하고, 공통 Memory/MCP/Event Bus를 통해 상태를 공유하게 만든다.

즉 구조는 이렇게 가야 해.

나쁜 구조:
Claude CLI session  ── 독립
Codex CLI session   ── 독립
Local LLM session   ── 독립

좋은 구조:
Harness
 ├─ Claude CLI Adapter
 ├─ Codex CLI Adapter
 ├─ Local LLM Adapter
 ├─ MemoryOS MCP
 ├─ Event Bus
 └─ Run State Store
1. 왜 그냥 CLI끼리는 agent loop가 안 되나
각 CLI는 보통 자기 세션, 자기 승인 흐름, 자기 context, 자기 tool 설정을 갖고 돌아가.

그래서 이런 문제가 생겨.

1. Claude가 알게 된 내용을 Codex가 모름
2. Codex가 수정한 근거를 Claude가 모름
3. local LLM이 추출한 memory draft를 다른 agent가 자동으로 못 봄
4. 각 CLI의 permission/sandbox/approval이 따로 놂
5. 대화 로그가 흩어짐
6. “다음 agent에게 넘길 상태”가 표준화되지 않음
그래서 CLI들을 그냥 병렬로 켜는 건 multi-agent system이 아니라 여러 도구를 수동으로 번갈아 쓰는 것에 가까워.

2. API만 쓰면 또 뭐가 문제냐
네 말대로 API만 쓰면 provider가 제공하는 고유 기능을 잃을 수 있어.

예를 들면:

Claude Code:
- repo-aware workflow
- hooks
- MCP integration
- permission flow
- coding-agent UX
- slash command / project instruction 생태계

Codex CLI:
- repo editing
- sandbox / approval
- non-interactive exec
- config.toml 기반 MCP
- cloud/task/IDE 연동 계열
Codex는 공식적으로 codex exec를 통해 TUI 없이 스크립트/CI에서 실행할 수 있고, CLI reference도 codex exec를 non-interactive 실행용으로 설명한다. 
 Codex는 ~/.codex/config.toml에 MCP 서버를 설정해 연결할 수 있다는 문서도 있다. 

Claude Code 쪽도 lifecycle의 특정 지점에서 shell command, HTTP endpoint, LLM prompt를 실행하는 hooks를 제공하고, hooks guide는 파일 포맷팅, 명령 차단, 알림, 세션 시작 context 주입 같은 자동화를 설명한다. 

즉 API만 쓰면 “모델”은 얻지만, CLI 제품이 가진 agent runtime을 버리게 된다.

3. 현실적인 정답: CLI-as-worker + shared substrate
정답은 이거야.

Provider CLI는 그대로 쓴다.
하지만 직접 사람이 조작하지 않고,
Harness가 CLI를 worker처럼 실행한다.

공통 상태는 CLI 내부가 아니라
MemoryOS / Event Bus / Run DB에 둔다.
구조:

┌──────────────────────────────────────────────┐
│                  Harness                      │
│ router / planner / state / permissions        │
└───────┬───────────────┬───────────────┬──────┘
        │               │               │
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌──────────────┐
│ Claude CLI  │ │ Codex CLI   │ │ Local LLM    │
│ Adapter     │ │ Adapter     │ │ Adapter      │
└──────┬──────┘ └──────┬──────┘ └──────┬───────┘
       │               │               │
       └───────────────┼───────────────┘
                       ▼
        ┌─────────────────────────────┐
        │      MemoryOS MCP/API        │
        │ memory / project / graph     │
        └─────────────────────────────┘
                       ▼
        ┌─────────────────────────────┐
        │ Run State + Event Log        │
        │ tasks / handoffs / outputs   │
        └─────────────────────────────┘
여기서 CLI들은 “독립된 뇌”가 아니라 실행 가능한 전문 worker가 된다.

4. Provider 기능을 유지하면서 loop를 만드는 방법
방법 A: Harness가 CLI를 headless로 호출
Codex는 codex exec로 비대화형 실행이 가능하니까 harness에서 이렇게 호출한다. 

codex exec --cd ./repo "Implement the ChatGPT export parser. Use MemoryOS MCP context."
Claude Code도 headless/prompt 기반 실행이나 hooks를 이용해 자동화할 수 있다. Claude Code hooks는 lifecycle 이벤트에 shell command/HTTP endpoint/LLM prompt를 붙일 수 있으므로, 세션 시작 시 MemoryOS context를 주입하거나 작업 종료 시 memory draft를 쓰는 흐름을 만들 수 있다. 

Harness 관점에서는 이렇게 감싼다.

interface AgentAdapter {
  id: string;
  run(task: AgentTask, context: ContextPack): Promise<AgentResult>;
}
class CodexCliAdapter implements AgentAdapter {
  async run(task, context) {
    const prompt = buildCodexPrompt(task, context);
    return execFile("codex", [
      "exec",
      "--cd",
      task.repoPath,
      prompt
    ]);
  }
}
이 방식의 장점:

- Codex/Claude CLI 고유 기능 유지
- repo-aware coding 기능 유지
- MCP 설정 유지
- approval/sandbox 일부 유지
- 자동 loop 가능
단점:

- CLI 출력 파싱이 필요함
- 세션 상태 복원이 까다로움
- provider별 adapter가 필요함
방법 B: 모든 CLI에 같은 MemoryOS MCP를 꽂는다
각 CLI가 독립 환경이어도 같은 MCP 서버를 보게 하면 상태 공유가 가능해진다.

Claude Code ─┐
Codex CLI ───┼── MemoryOS MCP
Cursor ──────┤
Local Agent ─┘
Codex는 config에서 MCP 서버를 설정할 수 있다. 
 Claude Code도 MCP 서버 추가/설정 흐름이 널리 문서화되어 있고, 공식 hooks/MCP 기반 workflow와 결합할 수 있다. 

이렇게 하면 각 agent는 자기 CLI 안에서 이런 tool을 호출한다.

memory.search
project.get_state
hypergraph.search
context.write_draft
run.get_state
handoff.create
중요한 건 MemoryOS MCP가 단순 검색이 아니라 run/session 상태도 제공해야 한다는 점이야.

memory://runs/current
memory://handoffs/pending
memory://projects/memoryos/state
방법 C: CLI Hooks로 Event Bus에 연결
Claude Code hooks는 lifecycle 이벤트에서 명령/HTTP endpoint/LLM prompt를 실행할 수 있으므로, 다음 같은 자동화를 걸 수 있다. 

SessionStart:
- MemoryOS에서 project_state/context_pack 가져와 주입

PreToolUse:
- 위험한 명령 차단
- 권한 체크

PostToolUse:
- 파일 변경/테스트 결과를 event log에 기록

Stop:
- 세션 요약
- memory draft 생성
즉 Claude Code 자체가 완전한 multi-agent loop를 관리하지 않아도, hook을 통해 harness/event bus와 연결할 수 있다.

Codex 쪽은 codex exec를 통해 harness가 작업 단위로 실행하고, 결과 stdout/stderr, diff, test 결과를 event log에 기록하면 된다.

5. 핵심 패턴: “대화”가 아니라 “handoff artifact”로 연결
agent끼리 자연어 채팅을 계속 시키면 흐려져.
대신 각 agent는 표준 handoff artifact를 남겨야 해.

handoff:
  run_id: run_2026_04_30_001
  from_agent: claude
  to_agent: codex
  task_type: implementation
  objective: "Implement ChatGPT export parser"
  context_refs:
    - project_state:memoryos
    - he_memoryos_architecture_split
    - mem_draft_first_policy
  constraints:
    - "Parser must be deterministic code"
    - "LLM only for semantic extraction"
    - "Do not commit memory directly"
  files_to_modify:
    - packages/parsers/src/chatgpt.ts
    - services/ingestion-worker/src/import.ts
  acceptance_criteria:
    - "Can import chatgpt-export.zip"
    - "Stores conversations/messages/pairs"
    - "Tests pass"
Claude는 이걸 만들고, Codex는 이걸 받아 구현한다.
Codex 결과는 다시 이런 artifact로 나온다.

agent_result:
  run_id: run_2026_04_30_001
  agent: codex
  changed_files:
    - packages/parsers/src/chatgpt.ts
  commands_run:
    - pnpm test
  tests:
    status: passed
  memory_drafts:
    - "Implemented deterministic ChatGPT parser"
  unresolved:
    - "Need sample export fixture"
Harness가 이걸 읽어서 다음 agent에게 넘긴다.

6. “세션 독립성”을 해결하는 4가지 공유 계층
CLI가 독립이어도 아래 4개를 공유하면 loop가 만들어져.

1) Shared Memory
MemoryOS DB/MCP
- project_state
- decisions
- constraints
- prior context
2) Shared Run State
runs
- current objective
- phase
- assigned agent
- status
- artifacts
- pending handoffs
3) Shared Workspace
repo/worktree
- agent들이 실제 파일 변경을 공유
- branch/worktree 단위로 격리 가능
4) Shared Event Log
events
- agent_started
- tool_called
- file_changed
- test_ran
- handoff_created
- memory_draft_created
이 4개가 있으면 각 CLI는 독립이어도 “하나의 시스템”처럼 움직인다.

7. 구현 형태: Adapter 기반
각 provider는 adapter로 감싼다.

type AgentKind = "claude_cli" | "codex_cli" | "local_llm" | "api_llm";

interface AgentAdapter {
  id: string;
  kind: AgentKind;
  capabilities: string[];
  run(input: AgentRunInput): Promise<AgentRunOutput>;
}
Codex adapter:

class CodexCliAdapter implements AgentAdapter {
  id = "codex";
  kind = "codex_cli";
  capabilities = ["code_edit", "test_fix", "repo_reasoning"];

  async run(input) {
    const prompt = renderPrompt(input);
    const result = await spawnCapture("codex", [
      "exec",
      "--cd",
      input.workspacePath,
      prompt
    ]);

    return parseCodexOutput(result);
  }
}
Claude adapter:

class ClaudeCliAdapter implements AgentAdapter {
  id = "claude";
  kind = "claude_cli";
  capabilities = ["architecture", "review", "handoff"];

  async run(input) {
    const prompt = renderPrompt(input);
    const result = await spawnCapture("claude", [
      "-p",
      prompt
    ], {
      cwd: input.workspacePath
    });

    return parseClaudeOutput(result);
  }
}
Local LLM adapter:

class LocalLlmAdapter implements AgentAdapter {
  id = "local-llm";
  kind = "local_llm";
  capabilities = ["classification", "extraction", "summarization"];

  async run(input) {
    return callOllamaOrLmStudio(input);
  }
}
8. Provider 기능을 최대한 살리는 운영 방식
각 CLI를 그냥 API처럼 쓰면 기능을 잃는다.
그래서 provider별 “native runtime”은 유지하되, 공통 입출력만 표준화한다.

Claude Code:
- hooks 사용
- MCP 사용
- CLAUDE.md / project instructions 사용
- architecture/review/handoff에 강하게 배정

Codex:
- codex exec 사용
- ~/.codex/config.toml MCP 유지
- repo edit/test/refactor에 배정
- sandbox/approval 정책 유지

Local LLM:
- batch extraction
- privacy-sensitive local processing
- cheap tagging

Harness:
- routing
- state
- event log
- memory commit
즉 “모두를 API 호출로 평평하게 만들기”가 아니라:

각 provider의 native strength는 유지
공통 substrate만 MemoryOS로 통일
이게 정답이야.

9. loop 예시
사용자:

MemoryOS의 ChatGPT importer 구현해.
Harness:

1. task classify: implementation
2. project_state MemoryOS 조회
3. memory.search: parser/draft-first/MCP 관련 결정 조회
4. Claude에게 설계/handoff 요청
5. Codex에게 handoff 전달
6. Codex가 구현
7. tests 실행
8. Claude가 review
9. local LLM이 memory draft 추출
10. Harness가 draft 저장
흐름:

User
 ↓
Harness
 ↓
Claude CLI Adapter
  - produce implementation handoff
 ↓
Harness event log
 ↓
Codex CLI Adapter
  - edit files, run tests
 ↓
Harness event log
 ↓
Claude CLI Adapter
  - review diff
 ↓
Local LLM Adapter
  - extract memory drafts
 ↓
MemoryOS
여기서 agent끼리 직접 대화하지 않아도 loop가 성립한다.

10. “Claude가 Codex를 호출”하게 만들 수도 있나?
가능은 해. 예를 들어 Claude에 Codex CLI를 감싼 MCP tool을 제공하면 Claude가 Codex를 도구처럼 호출할 수 있다. 실제로 Codex CLI를 다른 agent에서 호출하게 해주는 MCP 서버류도 존재한다. 

하지만 나는 초기에는 비추천.

왜냐하면:

Claude → Codex → 또 tool 호출
이렇게 중첩되면 권한, 비용, 로그, 실패 복구가 복잡해진다.

초기 권장 구조는:

Claude
  ↓ result
Harness
  ↓ task
Codex
즉 agent-to-agent가 아니라 agent-to-harness-to-agent.

11. 최소 구현안
당장 만들려면 이 정도면 돼.

services/harness/
  adapters/
    codex-cli.ts
    claude-cli.ts
    local-llm.ts
  run-state.ts
  event-log.ts
  router.ts
  handoff.ts
  context-builder.ts
DB 테이블:

CREATE TABLE runs (
  id TEXT PRIMARY KEY,
  objective TEXT NOT NULL,
  project TEXT,
  status TEXT,
  current_phase TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'
);

CREATE TABLE run_events (
  id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(id),
  event_type TEXT NOT NULL,
  agent_id TEXT,
  payload JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE handoffs (
  id TEXT PRIMARY KEY,
  run_id TEXT REFERENCES runs(id),
  from_agent TEXT,
  to_agent TEXT,
  objective TEXT,
  context_refs JSONB DEFAULT '[]',
  constraints JSONB DEFAULT '[]',
  acceptance_criteria JSONB DEFAULT '[]',
  status TEXT DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT NOW()
);
MCP 추가 tools:

run.get_current
run.log_event
handoff.create
handoff.get_pending
handoff.complete
context.build_pack
12. 보안상 중요한 점
CLI들을 harness가 호출하면 사실상 로컬 자동화 시스템이 된다.
따라서 MCP와 CLI 조합은 권한 경계를 명확히 해야 한다. MCP 조합에서 path validation, git/file tools 조합, prompt injection 등으로 문제가 생길 수 있다는 사례도 이미 있었다. 

그래서 원칙은 이거야.

1. agent는 memory draft까지만 작성
2. commit은 harness/user만 가능
3. repo write는 Codex만
4. shell command는 allowlist
5. raw export 접근은 ingestion worker만
6. 외부 네트워크 tool은 별도 승인
7. 모든 run/event/handoff를 audit log에 저장
8. CLI는 가능하면 isolated worktree에서 실행
특히 --dangerously-bypass-approvals-and-sandbox 같은 옵션은 Codex CLI 문서에도 위험하다고 명시되어 있으므로, 격리 runner 안에서만 써야 한다. 

13. 최종 답
네 문제의식이 정확해.

CLI를 각자 쓰면 loop가 안 생김.
API만 쓰면 provider-native 기능을 잃음.
그래서 정답은:

Provider CLI를 버리지 않는다.
각 CLI를 Adapter로 감싼다.
Harness가 headless로 실행한다.
MemoryOS MCP를 공통 기억으로 쓴다.
Run State / Event Log / Handoff Artifact로 agent loop를 만든다.
최종 구조:

Desktop / CLI
   ↓
Harness
   ├─ Claude CLI Adapter
   ├─ Codex CLI Adapter
   ├─ Local LLM Adapter
   └─ API LLM Adapter
   ↓
MemoryOS MCP
   ├─ memory.search
   ├─ project.get_state
   ├─ hypergraph.search
   ├─ run.log_event
   └─ handoff.create
   ↓
Local DB
   ├─ memory graph
   ├─ run state
   ├─ event log
   └─ draft commits
한 문장으로:

CLI들은 독립 실행 환경으로 두되, 독립된 기억을 갖게 하지 말고, Harness가 그들을 “상태 없는 전문 실행자”처럼 호출하며 MemoryOS가 공통 기억과 run state를 제공하게 만들면 된다.


