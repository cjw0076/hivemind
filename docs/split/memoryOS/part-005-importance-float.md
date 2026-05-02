<!--
Source: docs/memoryOS.md
Source lines: 2801-3500
Source byte range: 78653-101258
Split title source: first-text
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 005: importance FLOAT,

Provenance: `docs/memoryOS.md` lines `2801-3500`, bytes `78653-101258`.

Local structure markers:

- Source line 2828: 17. Context Pack도 하이퍼그래프 중심으로 바꿔야 함
- Source line 2832: 1. ...
- Source line 2833: 2. ...
- Source line 2834: 3. ...
- Source line 2852: 18. 네 시스템의 최종 그림
- Source line 2893: 19. 한 문장으로 정리
- Source line 2921: 1. 전체 구조
- Source line 2959: 2. MCP와 Skill의 역할을 헷갈리면 안 됨
- Source line 2988: 3. 결론: 메모리는 MCP 서버 + Skill 둘 다 필요함
- Source line 3008: 4. 하네스는 어떻게 구현하나
- Source line 3011: 1. Task Router
- Source line 3012: 2. Agent Registry

---

  importance FLOAT,
  confidence FLOAT,
  created_at TIMESTAMP,
  metadata JSONB
);

CREATE TABLE hyperedge_members (
  hyperedge_id TEXT REFERENCES hyperedges(id),
  node_id TEXT REFERENCES nodes(id),
  role TEXT,
  weight FLOAT DEFAULT 1.0,
  order_index INT,
  PRIMARY KEY (hyperedge_id, node_id, role)
);
임베딩:

CREATE TABLE node_embeddings (
  node_id TEXT PRIMARY KEY REFERENCES nodes(id),
  embedding VECTOR(1536),
  model TEXT
);

CREATE TABLE hyperedge_embeddings (
  hyperedge_id TEXT PRIMARY KEY REFERENCES hyperedges(id),
  embedding VECTOR(1536),
  model TEXT
);
17. Context Pack도 하이퍼그래프 중심으로 바꿔야 함
일반 RAG context:

Relevant chunks:
1. ...
2. ...
3. ...
하이퍼그래프 context:

Relevant Hyperedges:

[DecisionEvent] Hypergraph selected as memory structure
- Decision: use hypergraph for 1-to-many AI memory relations
- Project: Personal AI Memory OS
- Concepts: graph DB, embedding, agent retrieval, MLP encoder
- Evidence: messages 123, 124
- Status: active
- Confidence: 0.93

[ConceptCluster] Agent-readable memory architecture
- Concepts: operational state, retrieval orchestrator, context pack, reflection loop
- Related decision: memory must be stateful, not just vector search
이렇게 넣어야 agent가 “덩어리”로 이해한다.

18. 네 시스템의 최종 그림
너의 Memory OS는 일반 graph가 아니라 이렇게 가야 해.

Message Layer
- 원문 발화

Pair Layer
- user-assistant pair

Atomic Memory Layer
- idea, fact, decision, question, action

Hyperedge Layer
- 여러 atomic memory가 결합한 사건

State Layer
- 현재 프로젝트 상태

Agent Layer
- retrieval, reasoning, update
구조:

Messages
   ↓
Atomic Memories
   ↓
Hyperedges
   ↓
Project / Concept / Decision State
   ↓
Agent Context
   ↓
New Hyperedges
이 루프가 닫히면:

대화가 쌓임
→ 개념이 묶임
→ 결정이 생김
→ 행동이 생김
→ 상태가 바뀜
→ 다음 대화에서 더 정확한 맥락으로 응답
19. 한 문장으로 정리
하이퍼그래프는 AI 대화 memory에서 “한 발화가 여러 개념·프로젝트·결정·행동을 동시에 묶는 사건”을 표현하기 위한 핵심 구조다.

그래서 너의 시스템은 이렇게 설계하는 게 맞아.

일반 graph = 단순 연결
hypergraph = 사고 사건
embedding = 의미 유사도
MLP = 개인 사고공간 projection
agent = 현재 목적에 맞게 hyperedge를 꺼내 쓰는 실행자
최종적으로는:

Node는 기억의 원자이고,
Hyperedge는 생각의 사건이며,
State는 현재의 너이고,
Agent는 그것을 읽고 행동하는 실행 루프다.

만약 내가 claude, codex, local llm, llm agent, 등 하네스로 엮어서 쓴다고 하자. 이 하네스는 어떻게 구현할 수 있고 메모리시스템은 mcp와 skill의 형태로 만들어야하나 ?

이건 “여러 LLM을 한 UI에 붙이는 것”보다 한 단계 위야. 하네스는 모델들을 호출하는 라우터이고, 메모리 시스템은 모든 모델이 공유하는 외부 인지 계층으로 둬야 해. 최신 MCP/Claude/OpenAI Codex 쪽 개념도 확인해서, 실제 구현 가능한 형태로 나눠 설명할게.

18s 동안 생각함
응. 이 경우에는 하네스(harness), MCP, Skill, Memory System을 서로 다른 층으로 봐야 해.

한 문장으로 정리하면:

하네스는 여러 LLM/agent를 지휘하는 orchestration layer이고, MCP는 그들이 공유 도구/메모리에 접근하는 표준 인터페이스이며, Skill은 특정 작업을 잘 수행하게 만드는 workflow package다. 메모리 시스템은 MCP 서버로 노출하고, 메모리 사용법은 Skill로 패키징하는 게 가장 좋다.

1. 전체 구조
네가 말한 구성을 제대로 만들면 이렇게 돼.

                         ┌────────────────────┐
                         │  User / CLI / UI    │
                         └─────────┬──────────┘
                                   │
                         ┌─────────▼──────────┐
                         │   Agent Harness     │
                         │  planner/router     │
                         └──────┬─────┬───────┘
                                │     │
        ┌───────────────────────┘     └───────────────────────┐
        │                                                     │
┌───────▼────────┐   ┌───────────────┐   ┌────────────────────┐
│ Claude Code    │   │ Codex         │   │ Local LLM Agent     │
│ coding/reason  │   │ code/edit/test│   │ cheap/private tasks │
└───────┬────────┘   └───────┬───────┘   └─────────┬──────────┘
        │                    │                     │
        └────────────┬───────┴────────────┬────────┘
                     │                    │
              ┌──────▼────────────────────▼──────┐
              │              MCP Layer             │
              │ memory, repo, docs, browser, db    │
              └──────┬────────────────────┬──────┘
                     │                    │
        ┌────────────▼──────────┐   ┌─────▼──────────────┐
        │ Memory Hypergraph OS   │   │ External Tools      │
        │ vector/graph/state     │   │ git, fs, browser... │
        └───────────────────────┘   └────────────────────┘
중요한 구분은 이거야.

Harness = 누가 어떤 일을 할지 결정하는 지휘자
MCP = 외부 시스템에 접근하는 표준 포트
Skill = 특정 작업 절차/전문성을 압축한 레시피
Memory System = 모든 agent가 공유하는 장기 기억/상태 계층
MCP는 LLM 앱이 외부 데이터와 도구에 연결되도록 하는 표준 프로토콜이고, tools/resources/prompts 같은 서버 기능을 제공한다. 공식 스펙도 MCP를 LLM 애플리케이션이 외부 컨텍스트와 도구를 쓸 수 있게 하는 표준으로 정의한다. 

2. MCP와 Skill의 역할을 헷갈리면 안 됨
MCP는 “능력의 API”
MCP는 이런 데 써야 해.

search_memory()
write_memory()
get_project_state()
query_hypergraph()
read_repo()
run_tests()
search_docs()
create_issue()
즉, 실제로 외부 시스템을 읽고 쓰는 도구 인터페이스야.

OpenAI Apps SDK 문서도 MCP 서버가 모델이 호출할 수 있는 tool을 노출하고, tool은 JSON Schema 기반 입력/출력 계약을 갖는다고 설명한다. 

Skill은 “일하는 법”
Skill은 이런 데 써야 해.

memory-first-research
bugfix-with-memory
paper-reading-workflow
feature-implementation-workflow
agent-handoff-protocol
decision-extraction-workflow
즉, 도구들을 어떤 순서와 원칙으로 쓸지를 패키징한 것.

Codex의 Agent Skills는 instructions, resources, optional scripts를 묶어 반복 workflow를 안정적으로 수행하게 하는 단위이고, SKILL.md 중심의 폴더 구조를 가진다. 

3. 결론: 메모리는 MCP 서버 + Skill 둘 다 필요함
정답은 둘 중 하나가 아니라 둘 다야.

Memory MCP Server
= 메모리에 접근하는 기능 제공

Memory Skills
= agent가 메모리를 올바르게 사용하는 절차 제공
예를 들면:

MCP tool:
search_memory(query, filters)

Skill:
“작업 시작 전 관련 project_state를 먼저 읽고,
과거 decision과 open question을 조회한 뒤,
답변 후 새 decision/action을 write_memory 하라.”
MCP만 있으면 agent가 도구를 “쓸 수는” 있지만, 잘 쓰지는 못해.
Skill만 있으면 절차는 있지만 실제 메모리 DB에 접근할 수 없어.

4. 하네스는 어떻게 구현하나
하네스는 크게 5개 모듈로 잡으면 돼.

1. Task Router
2. Agent Registry
3. Context Builder
4. Tool/MCP Gateway
5. Memory Committer
4.1 Task Router
사용자 요청을 보고 어떤 agent에게 보낼지 결정.

def route_task(task):
    if task.type in ["large_refactor", "codebase_edit", "test_fix"]:
        return "codex"

    if task.type in ["architecture", "deep_reasoning", "research_synthesis"]:
        return "claude"

    if task.type in ["private_summary", "cheap_batch_tagging", "embedding_labeling"]:
        return "local_llm"

    if task.type in ["web_research", "source_comparison"]:
        return "research_agent"

    return "general_agent"
예:

“이 repo에서 memory MCP server 만들어줘”
→ Codex

“이 memory system architecture 검토해줘”
→ Claude

“대화 1만 개에서 concept 추출해줘”
→ local LLM batch worker

“최신 MCP 보안 이슈 조사해줘”
→ web research agent
4.2 Agent Registry
각 agent의 능력, 비용, 속도, 권한을 registry로 관리.

agents:
  claude_code:
    role: "architect/coding agent"
    strengths: ["repo-wide reasoning", "multi-file edits", "planning"]
    allowed_tools: ["memory_mcp", "repo_mcp", "shell_limited"]
    risk_level: "medium"

  codex:
    role: "implementation agent"
    strengths: ["code edits", "tests", "PRs", "worktrees"]
    allowed_tools: ["memory_mcp", "repo_mcp", "test_runner"]
    risk_level: "medium"

  local_llm:
    role: "private batch worker"
    strengths: ["cheap extraction", "classification", "summarization"]
    allowed_tools: ["memory_read", "local_files"]
    risk_level: "low"

  research_agent:
    role: "external research"
    strengths: ["web/source synthesis"]
    allowed_tools: ["browser", "memory_write_draft"]
    risk_level: "high"
여기서 중요한 건 모든 agent에게 같은 권한을 주면 안 된다는 것.

4.3 Context Builder
각 agent에게 넘길 context를 자동으로 구성.

User task
→ detect project
→ read project_state
→ retrieve relevant hyperedges
→ retrieve active decisions
→ include repo instructions
→ build agent-specific prompt
Claude에게는 넓은 설계 context를, Codex에게는 repo 구조와 구현 지시를, local LLM에게는 원문 chunk와 schema만 준다.

4.4 MCP Gateway
각 agent가 직접 DB에 붙는 게 아니라, MCP 서버를 통해서만 접근.

agent
→ MCP tool call
→ policy check
→ memory system
→ structured result
Codex도 MCP 서버를 CLI/IDE extension에서 지원하고, STDIO 서버와 Streamable HTTP 서버를 설정할 수 있다. Codex 설정은 ~/.codex/config.toml 또는 project-scoped .codex/config.toml에서 관리할 수 있다. 

4.5 Memory Committer
작업이 끝나면 agent가 만든 결과를 그대로 저장하지 말고, commit protocol을 거친다.

agent output
→ extract decisions/actions/artifacts
→ user-origin vs agent-origin 구분
→ confidence/status 부여
→ hyperedge 생성
→ project_state patch
→ append to memory log
즉, memory write는 반드시 구조화해야 해.

5. 메모리 MCP 서버 설계
너의 핵심 MCP 서버는 memory-os-mcp가 될 거야.

Tools
memory.search
memory.get
memory.write
memory.update
memory.link
memory.supersede

project.get_state
project.update_state
project.get_decisions
project.get_open_questions

hypergraph.search
hypergraph.expand
hypergraph.create_edge
hypergraph.get_related

context.build_pack
context.commit_session

artifact.register
artifact.link_to_memory
이 중 agent가 제일 자주 쓰는 건 5개면 충분해.

get_project_state(project)
search_memory(query, filters)
search_hyperedges(query, filters)
build_context_pack(task, project)
commit_session_summary(summary, decisions, actions)
6. MCP resource도 같이 제공해야 함
MCP는 tool만 있는 게 아니라 resource 개념도 중요해.

메모리 시스템에서 resource는 이런 것들이야.

memory://projects/uri/state
memory://projects/memory-os/state
memory://concepts/hypergraph/history
memory://decisions/active
memory://user/preferences
memory://schemas/memory-object
memory://schemas/hyperedge
Agent가 매번 tool을 호출하지 않아도, 특정 resource를 읽어 컨텍스트로 삼을 수 있게 하는 구조야.

7. Skill은 어떻게 만들까
Skill은 agent가 메모리 시스템을 제대로 쓰게 하는 “운영 규칙”이다.

예를 들면 .agents/skills/memory-first-workflow/SKILL.md.

---
name: memory-first-workflow
description: Use this skill when starting any non-trivial planning, coding, research, or project task that may depend on prior user context or project decisions.
---

# Memory-first workflow

Before answering or coding:

1. Identify the project, task type, and expected artifact.
2. Call `project.get_state` if a project is detected.
3. Call `memory.search` for relevant prior decisions, constraints, and open questions.
4. Call `hypergraph.search` when the task combines multiple concepts or projects.
5. Prefer active decisions over stale or superseded memories.
6. Separate user-originated ideas from agent-suggested ideas.
7. After completing the task, call `context.commit_session` with:
   - new decisions
   - new actions
   - changed constraints
   - generated artifacts
   - unresolved questions
이 Skill은 Claude, Codex, local agent 모두에게 같은 철학을 제공한다.

Codex Skill은 이름/description/path가 먼저 context에 들어가고, 필요할 때 전체 SKILL.md가 로드되는 progressive disclosure 방식을 사용한다. 이 구조는 context를 아끼면서도 workflow를 재사용하기 좋다. 

8. AGENTS.md는 어디에 쓰나
AGENTS.md는 repo-level 헌법이다.

Codex 기준으로 AGENTS.md는 작업 전에 읽히는 durable project guidance이고, build/test 명령, review 기대치, repo convention, directory-specific instruction 같은 것을 넣는 데 적합하다. 

예:

# AGENTS.md

## Project
This repository implements a Personal AI Memory OS.

## Architecture rules
- Memory access must go through MCP tools.
- Do not read raw exports directly from agent code except ingestion workers.
- Do not write unstructured memory records.
- Every memory write must include source, confidence, status, and raw_refs.
- Hyperedges represent multi-way cognitive events.

## Commands
- pnpm test
- pnpm lint
- pnpm typecheck

## Done means
- Tests pass.
- Memory schema migration included if needed.
- MCP tool contract documented.
정리하면:

AGENTS.md = 이 repo에서 항상 지켜야 하는 규칙
Skill = 특정 작업을 수행하는 workflow
MCP = 실제 외부 시스템 접근 도구
Harness = 어떤 agent에게 어떤 Skill/MCP/context를 줄지 결정
9. 구현 방식: Local-first harness
처음 버전은 SaaS 말고 로컬에서 이렇게 가는 게 좋아.

memory-harness/
  apps/
    harness-cli/
    dashboard/
  services/
    memory-api/
    memory-mcp/
    ingestion-worker/
    embedding-worker/
    local-llm-worker/
  packages/
    schemas/
    agent-router/
    context-builder/
    evals/
  .agents/
    skills/
      memory-first-workflow/
      implementation-handoff/
      research-synthesis/
  AGENTS.md
10. 핵심 실행 흐름
사용자가 말한다:

“Claude랑 Codex 써서 memory MCP server 구현해줘.”
하네스는 이렇게 동작:

1. task_router:
   type = implementation
   project = memory-os

2. context_builder:
   project_state 조회
   active decisions 조회
   memory MCP 설계 관련 hyperedge 조회

3. planner agent:
   Claude에게 architecture plan 생성 요청

4. implementation agent:
   Codex에게 file-level 구현 요청

5. local agent:
   생성된 code/doc에서 memory update 후보 추출

6. verifier:
   tests/lint/schema check 실행

7. memory_committer:
   decision/action/artifact hyperedge 저장
이게 “하네스”야.

11. Harness 내부 API 예시
class AgentHarness:
    def run(self, user_task: str):
        task = self.task_analyzer.analyze(user_task)

        project_state = self.memory.get_project_state(task.project)
        context_pack = self.context_builder.build(
            task=task,
            project_state=project_state,
        )

        plan = self.invoke_agent(
            agent="claude",
            skill="memory-first-workflow",
            context=context_pack,
            prompt=f"Create an implementation plan for: {user_task}",
        )

        result = self.invoke_agent(
            agent="codex",
            skill="implementation-handoff",
            context=context_pack,
            prompt=plan.to_codex_prompt(),
        )

        verification = self.verify(result)

        memory_update = self.extract_memory_update(
            task=user_task,
            plan=plan,
            result=result,
            verification=verification,
        )

        self.memory.commit(memory_update)

        return result
12. Agent 간 handoff protocol
여러 agent를 쓰면 “인수인계 문서”가 중요해.

Claude가 Codex에게 넘길 때는 반드시 이런 포맷으로.

handoff:
  objective: "Implement memory MCP server"
  files_to_modify:
    - services/memory-mcp/src/server.ts
    - packages/schemas/src/memory.ts
  constraints:
    - "All writes require raw_refs"
    - "No direct DB access outside repository layer"
    - "MCP tools must return structured JSON"
  acceptance_criteria:
    - "memory.search works"
    - "project.get_state works"
    - "hypergraph.expand works"
    - "tests pass"
  relevant_memories:
    - id: "he_001"
      summary: "Memory system should use hypergraph for multi-way cognitive events"
이걸 Skill로 만들어두면 좋아.

13. Local LLM은 어디에 쓰나
local LLM은 “최종 판단”보다 batch worker로 쓰는 게 좋아.

좋은 용도:
- 대화 chunk 분류
- intent tagging
- concept extraction 초안
- PII detection
- low-cost summary
- duplicate detection
- local private preprocessing

주의할 용도:
- 최종 architecture decision
- 복잡한 코드 변경
- 보안 민감한 자동 실행
즉:

Claude / GPT / Codex = 고난도 reasoning + implementation
Local LLM = 대량 전처리 + privacy-sensitive cheap worker
14. 보안 구조는 필수
MCP는 강력한 만큼 위험하다. 공식 MCP 스펙도 MCP가 arbitrary data access와 code execution path를 열 수 있으므로 보안/신뢰 고려가 중요하다고 명시한다. 

반드시 이렇게 해야 해.

1. Tool allowlist
2. Read/write 권한 분리
3. Human approval for destructive actions
4. Per-agent permission scope
5. Raw export 접근 제한
6. Prompt injection 방어
7. Tool output sanitization
8. Audit log
9. Sandbox execution
10. Secrets never exposed to model context
MCP reference servers repository도 reference 구현은 교육용 예시이며 production-ready가 아니므로 threat model에 맞는 safeguard가 필요하다고 경고한다. 

15. 권한 모델
각 agent에게 tool permission을 다르게 줘.

permissions:
  claude:
    memory:
      read: true
      write_draft: true
      commit: false
    repo:
      read: true
      write: false

  codex:
    memory:
      read: true
      write_draft: true
      commit: false
    repo:
      read: true
      write: true
      shell: limited

  local_llm:
    memory:
      read_batch: true
      write_draft: true
      commit: false
    repo:
      read: false

  harness:
    memory:
      commit: true
    repo:
      approve_changes: true
핵심은 agent는 draft를 만들고, harness가 commit한다는 것.

16. 메모리 write는 2단계로
Agent가 바로 영구 기억에 쓰면 오염된다.

write_draft_memory()
→ validation
→ deduplication
→ conflict check
→ user/harness approval
→ commit_memory()
예:

{
  "draft_memory": {
    "type": "decision",
    "content": "Memory system should expose core capabilities as an MCP server and operational workflows as Skills.",
    "source": "current_session",
    "origin": "user+assistant",
    "confidence": 0.92,
    "status": "active",
    "raw_refs": ["current_turn_001"]
  }
}
17. 하네스가 들고 있어야 하는 “상태”
하네스는 단순 router가 아니라 작업 상태를 들고 있어야 해.

{
  "run_id": "run_2026_04_30_001",
  "user_goal": "Build memory MCP server",
  "project": "memory-os",
  "active_agents": ["claude", "codex", "local_llm"],
  "current_phase": "implementation",
  "context_pack_id": "ctx_123",
  "memory_refs": ["he_001", "decision_004"],
  "artifacts": ["plan.md", "server.ts"],
  "pending_approvals": [],
  "new_memory_drafts": []
}
이걸 저장해야 session이 끊겨도 이어갈 수 있어.

18. 최소 MVP
처음 만들 것은 딱 이거야.

MVP 0:
- memory DB
- memory MCP server
- Codex 연결
- Claude Code 연결
- AGENTS.md
- memory-first Skill
구현 순서:

1. Postgres + pgvector schema
2. nodes / hyperedges / memories / project_states 테이블
3. memory-api REST 구현
4. memory-mcp가 REST를 감싸서 MCP tools 제공
5. Codex config.toml에 memory-mcp 등록
6. Claude Code에도 memory-mcp 등록
7. .agents/skills/memory-first-workflow 작성
8. AGENTS.md에 “메모리 접근은 MCP만 사용” 규칙 추가
19. Codex 연결 예시
Codex는 MCP 서버를 CLI로 추가하거나 config 파일에 추가할 수 있다. 공식 문서 기준으로 codex mcp add <server-name> -- <stdio server-command> 형태로 STDIO 서버를 등록할 수 있고, HTTP 서버도 설정할 수 있다. 

예:

codex mcp add memory-os -- node ./services/memory-mcp/dist/server.js
또는 .codex/config.toml:

[mcp_servers.memory-os]
command = "node"
args = ["./services/memory-mcp/dist/server.js"]
cwd = "."
startup_timeout_sec = 10
tool_timeout_sec = 60
enabled_tools = [
  "project.get_state",
  "memory.search",
  "hypergraph.search",
  "context.commit_session"
]
20. Skill 예시: implementation-handoff
---
name: implementation-handoff
description: Use when receiving an architecture plan and implementing it in code with tests.
---

# Implementation Handoff

1. Read the handoff objective and acceptance criteria.
2. Call `project.get_state` for the current project.
3. Call `memory.search` for active implementation constraints.
