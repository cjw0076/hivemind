<!--
Source: docs/memoryOS.md
Source lines: 4201-4900
Source byte range: 119694-140673
Split title source: first-text
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 007: 해결:

Provenance: `docs/memoryOS.md` lines `4201-4900`, bytes `119694-140673`.

Local structure markers:

- Source line 4223: 14. Boot protocol 예시
- Source line 4237: 15. Boot coordinator prompt 예시
- Source line 4245: 1. Discover all available agents and tools.
- Source line 4246: 2. Ask each agent to produce a structured self-profile.
- Source line 4247: 3. Run small capability probes for reasoning, coding, memory retrieval, extraction, and tool discipline.
- Source line 4248: 4. Analyze the user's memory system to identify dominant projects, task types, preferences, and recurring patterns.
- Source line 4249: 5. Let agents review each other's probe outputs.
- Source line 4250: 6. Produce:
- Source line 4256: 7. Mark all initial conclusions as provisional.
- Source line 4257: 8. Store the result as a SystemBootstrappingEvent hyperedge.
- Source line 4258: 16. Agent self-profile schema
- Source line 4274: 17. Capability score schema

---


해결:

근거 없는 peer agreement는 낮은 신뢰도
tool evidence와 test result 우선
위험 3: memory 오염
초기 자기소개와 추측이 장기 memory에 들어가면 나중에 시스템이 잘못된 역할을 믿을 수 있음.

해결:

status = provisional
confidence 낮게 시작
실제 task 성능으로 강화/폐기
위험 4: 비용 폭발
agent끼리 계속 토론하면 token이 많이 든다.

해결:

structured dialogue
max turns
output schema 강제
harness가 중간 요약
14. Boot protocol 예시
실제 시스템에 넣을 수 있는 흐름은 이거야.

BOOT_STEP_1: Discover agents
BOOT_STEP_2: Discover MCP/tools/connectors
BOOT_STEP_3: Read user memory summary
BOOT_STEP_4: Generate user work profile
BOOT_STEP_5: Ask each agent for self profile
BOOT_STEP_6: Run capability probes
BOOT_STEP_7: Peer review probe outputs
BOOT_STEP_8: Generate role assignments
BOOT_STEP_9: Generate routing policy
BOOT_STEP_10: Store boot hyperedge
BOOT_STEP_11: Enter observation mode
15. Boot coordinator prompt 예시
하네스의 boot coordinator에게 이런 지시를 줄 수 있어.

You are the boot coordinator for a multi-agent memory system.

Your job is to initialize the agent society.

Steps:
1. Discover all available agents and tools.
2. Ask each agent to produce a structured self-profile.
3. Run small capability probes for reasoning, coding, memory retrieval, extraction, and tool discipline.
4. Analyze the user's memory system to identify dominant projects, task types, preferences, and recurring patterns.
5. Let agents review each other's probe outputs.
6. Produce:
   - agent_registry
   - tool_registry
   - user_work_profile
   - routing_policy
   - memory_policy
7. Mark all initial conclusions as provisional.
8. Store the result as a SystemBootstrappingEvent hyperedge.
16. Agent self-profile schema
{
  "agent_id": "string",
  "model_or_runtime": "string",
  "available_tools": ["string"],
  "self_declared_strengths": ["string"],
  "self_declared_weaknesses": ["string"],
  "preferred_tasks": ["string"],
  "avoid_tasks": ["string"],
  "permission_requests": ["string"],
  "required_context": ["string"],
  "handoff_preferences": {
    "receives_from": ["string"],
    "hands_off_to": ["string"]
  }
}
17. Capability score schema
{
  "agent_id": "string",
  "evaluated_at": "datetime",
  "scores": {
    "architecture_reasoning": 0.0,
    "code_implementation": 0.0,
    "test_debugging": 0.0,
    "memory_retrieval": 0.0,
    "memory_extraction": 0.0,
    "tool_discipline": 0.0,
    "source_grounding": 0.0,
    "cost_efficiency": 0.0,
    "latency_efficiency": 0.0
  },
  "evidence": [
    {
      "probe_id": "string",
      "result": "pass|fail|partial",
      "notes": "string"
    }
  ],
  "confidence": 0.0
}
18. User work profile 생성 방식
memory system에서 다음을 추출하면 돼.

프로젝트 빈도
최근성
대화 길이
반복 개념
반복 요청 유형
생성 산출물 유형
실행으로 이어진 대화
미완료 action
사용자 교정 패턴
예를 들어 너의 경우는 이런 식으로 나올 수 있어.

Frequent projects:
- Uri
- AI Memory OS
- Deepfake detection
- Capstone
- North Star / cognition research

Frequent task modes:
- product strategy
- system architecture
- research framing
- prompt generation
- implementation planning
- pitch/storyline writing

Important behavioral constraints:
- avoid over-abstraction
- push toward concrete execution
- preserve long-term continuity
- distinguish user-origin ideas from AI-origin suggestions
이걸 기반으로 harness가 답변 스타일과 agent 배정을 조정한다.

19. Agent 탐색과 User 탐색을 합치면 더 좋음
단순히 agent만 정의하는 게 아니라, 사용자-작업-에이전트 매칭 행렬을 만들어야 해.

Task Type                  Best Agent       Support Agent      Memory Needed
--------------------------------------------------------------------------------
architecture design         Claude           Memory Agent       high
repo implementation         Codex            Claude            medium
bulk memory extraction      Local LLM         Claude verifier   high
business strategy           Claude           Research Agent    high
image prompt generation     General/Claude    Memory Agent       medium
paper/research synthesis    Claude           Research Agent    high
test/debugging              Codex            Local tools       low
이게 있으면 하네스가 훨씬 똑똑해진다.

20. 결론
너의 아이디어는 맞다.
처음 시스템을 켰을 때는 바로 일을 시키는 게 아니라, agent society를 부팅하고, 서로의 역할과 사용자의 작업 세계를 파악하는 orientation phase가 있어야 한다.

다만 핵심은 이거야.

agent 자기소개만 믿지 말 것
실제 probe와 task log로 검증할 것
초기 정의는 provisional로 둘 것
memory에 boot event로 저장할 것
주기적으로 role/routing을 업데이트할 것
최종 구조는 이렇게 보면 돼.

Agent Orientation Phase
= agent들이 서로를 이해하는 시간

User Exploration Phase
= 시스템이 사용자의 작업 세계를 이해하는 시간

Capability Registry
= 누가 무엇을 잘하는지에 대한 운영 지도

Routing Policy
= 어떤 작업을 누구에게 맡길지에 대한 규칙

Memory Hypergraph
= 이 모든 정의와 변화 이력을 저장하는 장기 기억
이걸 넣으면 네 하네스는 단순 multi-agent wrapper가 아니라, 스스로 자기 조직을 정렬하는 agentic operating system에 가까워져.


최종 System Production 어떤 형태로 나와야하지? Opensource로 풀고 개인 디바이스에서 구동시키려면? 

이제는 “아이디어”가 아니라 배포 가능한 제품 형태로 내려야 해. 개인 디바이스에서 돌아가는 오픈소스라면, 핵심은 local-first, plugin/MCP 기반, optional cloud-sync, 그리고 사용자 데이터 주권을 제품 원칙으로 박는 거야.

9s 동안 생각함
최종 Production 형태는 이렇게 나와야 해.

Local-first Open Source Agent Memory OS
개인 디바이스에서 실행되는 “AI 대화/문서/코드/작업 기억 시스템”이고, Claude, Codex, local LLM, MCP 도구들이 공통 메모리를 읽고 쓰는 개인용 agent harness.

즉, 최종 제품은 앱 하나가 아니라 아래 4개가 묶인 형태야.

1. Desktop App
   사용자가 직접 보는 UI

2. Local Memory Server
   대화/문서/작업/하이퍼그래프/임베딩 저장

3. MCP Server
   Claude, Codex, Cursor, local agent 등이 메모리에 접근하는 표준 포트

4. Agent Harness
   여러 agent를 라우팅하고, 작업을 분배하고, memory commit을 통제
1. 최종 제품 형태
가장 좋은 Production 패키지는 이거야.

MemoryOS Desktop
├── 로컬 앱
├── 로컬 DB
├── 로컬 MCP 서버
├── 로컬 LLM/embedding 옵션
├── Claude/Codex 연결 설정
├── export/import 파서
├── agent harness
└── optional cloud sync
사용자 입장에서는 이렇게 보이면 돼.

1. 앱 설치
2. ChatGPT / Claude / Gemini export 업로드
3. 로컬에서 파싱
4. 내 대화 memory graph 생성
5. Claude Code / Codex / Cursor에 MCP로 연결
6. 이후 모든 agent가 내 memory를 읽고 작업
제품 카피는 이렇게 잡을 수 있어.

Your local memory layer for AI agents.
흩어진 AI 대화와 작업 기록을 개인 디바이스 위의 agent memory graph로 바꿔주는 오픈소스 시스템.

2. 왜 local-first여야 하나
이 제품은 무조건 local-first로 가야 해.

이유는 명확해.

사용자의 AI 대화에는
- 사업 아이디어
- 연구 방향
- 코드
- 개인정보
- 회사/학교 자료
- 감정 상태
- 미완성 생각
- 타인 정보
가 전부 섞여 있음.
그래서 초기 신뢰 전략은 SaaS가 아니라:

“당신의 데이터는 기본적으로 당신의 기기 안에만 있습니다.”
이게 되어야 해.

나중에 cloud sync를 붙이더라도 기본은:

local-first
user-owned
encrypted
exportable
deleteable
open source
로 가야 한다.

3. 오픈소스 배포 형태
추천 repo 구조는 이렇게.

memory-os/
├── apps/
│   ├── desktop/                 # Tauri or Electron desktop app
│   ├── web/                     # local web dashboard
│   └── cli/                     # memory-os CLI
│
├── services/
│   ├── memory-api/              # local REST/GraphQL API
│   ├── memory-mcp/              # MCP server
│   ├── harness/                 # multi-agent orchestrator
│   ├── ingestion-worker/        # export parsers
│   ├── embedding-worker/        # embedding pipeline
│   └── reflection-worker/       # daily/weekly memory summarizer
│
├── packages/
│   ├── schemas/                 # Zod/JSON schema
│   ├── hypergraph/              # node/hyperedge logic
│   ├── retrieval/               # hybrid retrieval
│   ├── connectors/              # ChatGPT/Gemini/Claude parsers
│   ├── skills/                  # agent skills
│   └── security/                # permission/sandbox/audit
│
├── mcp/
│   ├── memory-os-mcp/
│   └── examples/
│
├── skills/
│   ├── memory-first-workflow/
│   ├── implementation-handoff/
│   ├── research-synthesis/
│   └── boot-orientation/
│
├── docker/
│   ├── docker-compose.yml
│   └── postgres-init.sql
│
├── AGENTS.md
├── README.md
├── SECURITY.md
├── PRIVACY.md
└── LICENSE
4. 사용자 설치 방식
오픈소스라도 설치 경험은 쉬워야 해.

일반 사용자
MemoryOS Desktop 다운로드
→ 앱 실행
→ 로컬 DB 자동 생성
→ export 파일 업로드
→ MCP 연결 가이드 자동 생성
개발자
git clone https://github.com/your-org/memory-os
cd memory-os
pnpm install
pnpm dev
Docker 사용자
docker compose up
CLI 사용자
memory-os init
memory-os import ./chatgpt-export.zip
memory-os index
memory-os mcp start
memory-os ask "내가 Uri에 대해 결정한 것들 보여줘"
즉, 배포 채널은 4개가 필요해.

1. Desktop app
2. CLI
3. Docker compose
4. MCP server package
5. 기술 스택 추천
Desktop
나는 Tauri 추천해.
Electron도 가능하지만, 개인 디바이스 local-first 앱이면 Tauri가 더 가볍고 보안 모델도 잡기 좋다.

Frontend: React / Next.js 또는 Vite
Desktop shell: Tauri
Local API: Rust or Node
Backend
Node.js/TypeScript
or
Python/FastAPI
너의 경우 Codex/Claude/JS ecosystem/MCP SDK 연결을 생각하면 초기에는 TypeScript가 좋아.

TypeScript
Fastify or Hono
Zod
Drizzle ORM
Postgres/SQLite
pgvector
DB
초기 local-first는 2가지 선택지가 있어.

가벼운 개인용
SQLite + sqlite-vec
장점: 설치 쉬움.
단점: 확장성/동시성/고급 검색 약함.

강한 개인용/개발자용
Postgres + pgvector
pgvector는 Postgres 안에 벡터를 저장하고 similarity search를 할 수 있는 오픈소스 확장이고, cosine/L2/inner product 등 다양한 거리와 approximate nearest neighbor search를 지원한다. 

나는 MVP는 SQLite로 빠르게, Production 개발자 버전은 Postgres+pgvector를 추천해.

Starter mode: SQLite
Power mode: Postgres + pgvector
Graph / Hypergraph
처음부터 Neo4j 필수로 두지 마.
하이퍼그래프는 Postgres 테이블로 충분히 표현 가능해.

nodes
hyperedges
hyperedge_members
memory_links
나중에 시각화/고급 탐색이 필요하면 Neo4j adapter를 붙이면 된다. Neo4j도 HNSW 기반 vector index와 graph 기반 검색을 지원하므로, 고급 graph-RAG 모드에는 적합하다. 

6. Production 아키텍처
최종 구조는 이렇게.

┌─────────────────────────────────────────────┐
│               MemoryOS Desktop               │
│  Search UI / Graph UI / Import UI / Settings │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│              Local Memory API                │
│  auth / permissions / retrieval / commit      │
└───────┬──────────────┬──────────────┬────────┘
        │              │              │
┌───────▼──────┐ ┌─────▼─────┐ ┌─────▼────────┐
│ Relational DB│ │ Vector DB │ │ Hypergraph DB│
│ messages     │ │ embeddings│ │ nodes/edges  │
│ pairs        │ │ chunks    │ │ memberships  │
└──────────────┘ └───────────┘ └──────────────┘
        │
┌───────▼──────────────────────────────────────┐
│              Memory MCP Server               │
│ project.get_state / memory.search / etc.     │
└───────┬──────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────┐
│ Claude / Codex / Cursor / Local LLM / Agents │
└──────────────────────────────────────────────┘
7. MCP 서버는 핵심 제품이다
이 제품의 핵심은 앱 UI보다 MCP 서버야.

MCP는 LLM 앱이 외부 데이터와 도구를 표준 방식으로 연결할 수 있게 하는 프로토콜이다. 공식 스펙도 MCP를 LLM applications와 external data sources/tools를 연결하는 open protocol로 정의한다. 

즉, 네 MemoryOS가 MCP 서버를 제공하면 Claude, Codex, Cursor, local agent들이 이런 식으로 접근할 수 있어.

memory.search
project.get_state
hypergraph.search
context.build_pack
context.commit_session
Codex도 MCP 서버를 CLI와 IDE extension에서 지원한다고 공식 문서가 설명한다. 

8. MCP tool 설계
최소 MCP tools는 8개면 충분해.

project.get_state
project.update_state

memory.search
memory.get
memory.write_draft

hypergraph.search
hypergraph.expand

context.commit_session
처음에는 read-only로 시작해야 해.

V0:
- project.get_state
- memory.search
- hypergraph.search

V1:
- memory.write_draft

V2:
- context.commit_session

V3:
- project.update_state
왜냐하면 agent가 처음부터 write 권한을 가지면 memory가 오염돼.

9. Skill은 repo 안에 포함
오픈소스 production에는 skills도 같이 들어가야 해.

OpenAI Codex의 Agent Skills는 task-specific workflow를 안정적으로 수행하게 하는 instructions, resources, optional scripts 묶음이다. 

너의 repo에는 기본 skill 4개가 필요해.

skills/
├── memory-first-workflow/
│   └── SKILL.md
├── implementation-handoff/
│   └── SKILL.md
├── research-synthesis/
│   └── SKILL.md
└── boot-orientation/
    └── SKILL.md
memory-first-workflow
모든 비 trivial 작업 전에 메모리 조회.

1. project.get_state
2. memory.search
3. hypergraph.search
4. active decision 우선
5. 답변 후 memory draft 생성
implementation-handoff
Claude → Codex 인수인계.

objective
files_to_modify
constraints
acceptance_criteria
relevant_memories
boot-orientation
처음 시스템 구동 시 agent/tool/user profile 탐색.

agent registry
tool registry
user work profile
routing policy
research-synthesis
웹/문서/메모리 근거를 결합해 synthesis.

10. AGENTS.md는 반드시 제공
Codex는 작업 전에 AGENTS.md를 읽어 repo-level guidance로 사용한다. 공식 문서도 AGENTS.md를 build/test commands, repo conventions, project-specific expectations를 제공하는 durable guidance로 설명한다. 

MemoryOS repo의 AGENTS.md에는 이런 규칙을 박아야 해.

# AGENTS.md

## Core rules

- Memory access must go through MCP tools.
- Do not directly modify memory DB.
- All memory writes must be draft-first.
- Every memory must include source, status, confidence, and raw_refs.
- Hyperedges represent multi-way cognitive events.
- User-originated ideas and agent-suggested ideas must be separated.
- Prefer active decisions over stale/superseded memories.

## Commands

- pnpm test
- pnpm lint
- pnpm typecheck
- pnpm db:migrate

## Done means

- Tests pass.
- Schema changes include migration.
- MCP tool contracts are updated.
- Memory updates are submitted as drafts, not committed directly.
11. 최종 모듈 구성
Production은 이 8개 모듈로 보면 돼.

1. Importer
ChatGPT export parser
Claude export parser
Gemini Takeout parser
Perplexity manual thread parser
Markdown/JSON importer
2. Normalizer
conversation
message
pair
segment
episode
artifact
3. Memory Extractor
idea
decision
question
action
preference
artifact
reflection
constraint
4. Hypergraph Builder
node 생성
hyperedge 생성
member role 부여
confidence/importance 계산
5. Embedding Worker
node embedding
hyperedge embedding
project state embedding
local embedding과 API embedding 둘 다 지원.

6. Retrieval Orchestrator
keyword search
vector search
hypergraph expansion
project state retrieval
reranking
context pack 생성
7. MCP Server
agent-facing memory tools
8. Harness
agent routing
capability registry
permission control
session logging
memory commit
12. UI는 어떻게 보여야 하나
Desktop UI는 6개 화면이면 충분해.

1. Home
Memory health
Indexed conversations
Active projects
Open questions
Recent decisions
2. Import
Upload ChatGPT export
Upload Claude export
Upload Gemini Takeout
Manual import
Folder watch
3. Ask Memory
내 memory에 질문하기
source filter
project filter
user-only / assistant-only filter
4. Project State
Uri
- Current stage
- Active decisions
- Open questions
- Next actions
- Related memories
5. Hypergraph Explorer
Concept clusters
Decision events
Action derivations
Contradiction sets
Agent boot events
6. Agent Harness
Registered agents
Available MCP servers
Capability scores
Routing policy
Recent runs
Pending memory drafts
13. 개인 디바이스 구동 방식
로컬에서는 이렇게 떠야 해.

memory-os-desktop
  ├── starts local API on localhost
  ├── starts MCP server
  ├── starts embedding worker
  ├── connects to local DB
  ├── optionally connects to Ollama/LM Studio
  └── exposes config for Claude/Codex/Cursor
예:

Local ports:
- 3434: MemoryOS API
- 3435: MemoryOS MCP
- 3436: local dashboard
CLI:

memory-os start
memory-os mcp start
memory-os import ./chatgpt-export.zip
memory-os index
memory-os status
14. Local LLM 연동
개인 디바이스에서 돌릴 거면 local LLM은 optional worker로 붙여.

Ollama
LM Studio
llama.cpp
vLLM
역할은:

대량 분류
concept extraction 초안
PII detection
summary draft
memory draft 생성
고난도 reasoning은 외부 Claude/GPT를 써도 되고, 민감한 대량 처리만 local LLM이 맡게 하면 된다.

15. 데이터 저장 정책
기본 디렉토리는 이렇게.

~/.memory-os/
├── config.yaml
├── data/
│   ├── memory.db
│   ├── postgres/
│   ├── raw-imports/
│   ├── artifacts/
│   └── indexes/
├── logs/
├── mcp/
└── backups/
중요한 옵션:

raw exports 저장 여부
raw exports 암호화 여부
embedding만 남기고 원문 삭제
특정 project 제외
특정 source 제외
전체 export
전체 delete
16. 보안 구조
여기서 대충 만들면 안 돼.
특히 MCP는 외부 tool access와 연결되기 때문에 보안 경계가 핵심이다. MCP 공식 스펙도 보안과 신뢰 고려가 중요하다고 다루고 있고, 최근에는 MCP 구현/운영 방식과 관련한 원격 코드 실행 및 prompt injection 위험이 보도되기도 했다. 

필수 보안 원칙:

1. MCP server는 기본 localhost only
2. 외부 네트워크 bind 금지
3. tool allowlist
4. read/write 권한 분리
5. raw export 접근 제한
6. memory write는 draft-first
7. destructive action은 user approval
8. audit log 저장
9. secrets는 model context에 노출 금지
10. prompt injection 방어
MCP tool 권한은 이렇게 나눠.

permissions:
  default_agent:
    memory.search: allow
    project.get_state: allow
    hypergraph.search: allow
    memory.write_draft: allow
    context.commit_session: deny

  trusted_harness:
    context.commit_session: allow
    project.update_state: allow

