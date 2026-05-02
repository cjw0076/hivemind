<!--
Source: docs/memoryOS.md
Source lines: 5601-6300
Source byte range: 157652-173917
Split title source: first-text
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 009: [Accept] [Edit] [Reject]

Provenance: `docs/memoryOS.md` lines `5601-6300`, bytes `157652-173917`.

Local structure markers:

- Source line 5611: 11. Agent/LLM API가 자동으로 정리하는 흐름
- Source line 5614: 1. Ingestion worker가 deterministic parse 완료
- Source line 5615: 2. Harness가 extraction task 생성
- Source line 5616: 3. Local LLM 또는 API LLM에게 segment 단위로 extraction 요청
- Source line 5617: 4. 결과를 JSON schema로 강제
- Source line 5618: 5. Validator가 schema/중복/충돌 검사
- Source line 5619: 6. Hypergraph builder가 하이퍼엣지 후보 생성
- Source line 5620: 7. Embedding worker가 index
- Source line 5621: 8. Memory MCP가 새 draft를 노출
- Source line 5622: 9. 사용자가 승인하거나 harness가 low-risk 자동 commit
- Source line 5625: 12. 어떤 LLM을 어디에 쓸지
- Source line 5648: 13. 자동 정리 결과는 하이퍼그래프로 들어가야 함

---


[Accept] [Edit] [Reject]

[Action]
conversation-to-memory-graph Skill을 작성한다.
confidence: 0.88

[Accept] [Edit] [Reject]
이게 있어야 사용자가 memory quality를 통제할 수 있어.

11. Agent/LLM API가 자동으로 정리하는 흐름
agent가 개입하는 경우에는 이렇게.

1. Ingestion worker가 deterministic parse 완료
2. Harness가 extraction task 생성
3. Local LLM 또는 API LLM에게 segment 단위로 extraction 요청
4. 결과를 JSON schema로 강제
5. Validator가 schema/중복/충돌 검사
6. Hypergraph builder가 하이퍼엣지 후보 생성
7. Embedding worker가 index
8. Memory MCP가 새 draft를 노출
9. 사용자가 승인하거나 harness가 low-risk 자동 commit
즉 agent는 “파일을 읽고 DB에 막 쓰는 존재”가 아니라, structured extraction worker로 써야 해.

12. 어떤 LLM을 어디에 쓸지
Local LLM
대량 처리
저비용 tagging
민감한 원문 요약
초기 memory draft 생성
concept extraction
Claude / GPT API
복잡한 decision extraction
충돌 판단
프로젝트 상태 요약
고품질 long-context synthesis
Codex
parser 구현
schema migration
MCP tool 추가
테스트 작성
즉:

Local LLM = 많이 처리
API LLM = 어렵게 판단
Codex = 시스템을 고침
Harness = 전체를 통제
13. 자동 정리 결과는 하이퍼그래프로 들어가야 함
대화 하나에서 바로 여러 노드와 하이퍼엣지를 만든다.

Conversation
  ↓
Messages
  ↓
Pairs
  ↓
Segments
  ↓
Atomic Memories
  ↓
Hyperedges
  ↓
Project State
예:

Segment:
“메모리 시스템은 MCP와 Skill 둘 다 필요하다.”

Nodes:
- Concept: MCP
- Concept: Skill
- Concept: Agent Harness
- Decision: Memory should be exposed via MCP
- Decision: Memory workflow should be encoded as Skill
- Project: MemoryOS

Hyperedge:
DecisionEvent {
  MCP,
  Skill,
  Agent Harness,
  MemoryOS,
  two decisions,
  source segment
}
14. 자동화 수준을 단계별로 올려야 함
처음부터 완전 자동은 위험해.

Level 0 — Manual
사용자가 파일 업로드
수동 import
Level 1 — Assisted
자동 파싱
자동 draft 생성
사용자 승인 후 commit
Level 2 — Semi-auto
low-risk memory는 자동 commit
decision/preference는 review
Level 3 — Autonomous
일정 confidence 이상이면 자동 graph update
충돌만 사용자에게 알림
Level 4 — Agentic
agent가 새 대화/파일을 감지
관련 project state 업데이트
다음 action까지 제안
초기 제품은 Level 1이 맞다.

15. Production 관점에서 필요한 컴포넌트
services/
  ingestion-worker/
    detect_source.ts
    parse_chatgpt.ts
    parse_claude.ts
    parse_gemini.ts
    parse_markdown.ts

  extraction-worker/
    extract_memories.ts
    extract_concepts.ts
    extract_decisions.ts
    extract_actions.ts

  hypergraph-worker/
    build_hyperedges.ts
    dedupe_hyperedges.ts
    detect_contradictions.ts

  embedding-worker/
    embed_nodes.ts
    embed_hyperedges.ts
    index_vectors.ts

  memory-api/
    drafts.ts
    commit.ts
    search.ts
    project_state.ts

  memory-mcp/
    tools.ts
    resources.ts

  harness/
    route_task.ts
    run_extraction.ts
    approve_commit.ts
16. Skill vs MCP vs Worker 정리
이 질문에 대한 정확한 답은 이거야.

대화 자동 정리 기능 자체
= Worker Pipeline

agent가 그 기능을 호출하는 인터페이스
= MCP Tools

agent가 그 기능을 올바른 순서로 쓰는 절차
= Skill

누가 언제 어떤 모델로 실행할지 결정
= Harness

결과가 저장되는 곳
= Local Memory Hypergraph
그러니까:

Skill 형태여야 하냐?
Skill만으로는 부족하고, Skill + MCP + Worker Pipeline 형태여야 한다.

17. 제일 작은 MVP
바로 만들면 이거부터.

1. import_file(file_path)
2. parse_chatgpt_export()
3. normalize_messages()
4. build_pairs()
5. segment_conversation()
6. extract_memory_drafts_with_llm()
7. build_hyperedge_drafts()
8. embed_and_index()
9. review_drafts_ui
10. commit_to_memory_graph()
MCP tool은 3개만.

ingestion.import_file
memory.extract_drafts
memory.commit_drafts
Skill은 1개만.

conversation-to-memory-graph
18. 최종 결론
대화 내용을 자동으로 정리해서 로컬에 파싱하고 메모리 그래프를 만들려면 이렇게 가야 해.

Parser는 코드로 만든다.
LLM은 의미 추출에 쓴다.
Graph 생성은 worker가 한다.
Agent가 접근하는 문은 MCP로 만든다.
Agent가 잘 쓰는 절차는 Skill로 만든다.
전체 순서와 권한은 Harness가 통제한다.
한 문장으로 정리하면:

자동 메모리 생성은 Skill이 아니라 local ingestion pipeline이 핵심이고, Skill은 그 pipeline을 agent가 안전하고 일관되게 사용하도록 만드는 운영 레이어다.


바로 제작해볼게. Agent한테 먹이게 전체 정리 한 번 해줘.

2초 동안 생각함
아래 그대로 Claude / Codex / Cursor / local agent한테 먹이면 돼.
목표는 Local-first Open Source Agent Memory OS v0.1 제작이야.

Agent 작업 지시서: Local-first Agent Memory OS v0.1
0. 프로젝트 한 줄 정의
우리는 개인 디바이스에서 실행되는 Local-first Agent Memory OS를 만든다.

이 시스템은 사용자의 ChatGPT / Claude / Gemini / Perplexity 등 AI 대화 export를 로컬에서 파싱하고, 입력-출력 쌍과 의미 단위 memory를 추출하고, 하이퍼그래프 기반 memory graph를 생성한 뒤, Claude / Codex / local LLM / agent들이 MCP를 통해 이 memory를 읽고 쓸 수 있게 한다.

핵심 철학:

대화 데이터
→ 정규화된 메시지
→ 입력-출력 pair
→ atomic memory
→ hyperedge
→ project state
→ agent context
→ 새 작업 결과
→ 다시 memory
1. 최종 시스템 목표
최종 제품은 다음 형태다.

MemoryOS
= Local-first open-source memory layer for AI agents

구성:
1. Desktop / Web UI
2. Local Memory API
3. Local DB
4. Ingestion Worker
5. Extraction Worker
6. Hypergraph Builder
7. Embedding Worker
8. MCP Server
9. Agent Harness
10. Skills
v0.1에서는 Desktop까지 완성하지 않아도 된다.
우선 CLI + Local API + MCP Server + ChatGPT export import + memory graph 생성이 되면 된다.

2. v0.1 MVP 범위
반드시 구현
1. ChatGPT export.zip import
2. conversations.json 파싱
3. conversation / message / pair 저장
4. segment 생성
5. LLM 또는 rule 기반 memory draft 추출
6. node / hyperedge / hyperedge_member 저장
7. embedding 저장 구조 준비
8. memory.search
9. hypergraph.search
10. project.get_state
11. MCP server 제공
12. AGENTS.md 작성
13. 기본 Skill 작성
v0.1에서는 미뤄도 됨
1. Gemini / Claude / Perplexity importer
2. Desktop app
3. full graph visualization
4. personal MLP encoder
5. cloud sync
6. browser extension
7. 완전 자동 memory commit
8. hypergraph neural network
3. 핵심 원칙
3.1 Local-first
사용자 데이터는 기본적으로 로컬에 저장한다.

- raw export는 로컬 보관
- 외부 API 사용은 optional
- local embedding / local LLM 옵션 고려
- 사용자가 raw export 삭제 가능해야 함
3.2 Parser는 deterministic code로
대화 export 파싱은 LLM에게 맡기지 않는다.

좋음:
- JSON parser
- HTML parser
- timestamp normalizer
- role mapper
- pair builder

나쁨:
- LLM에게 raw JSON 전체를 주고 알아서 파싱하게 하기
3.3 LLM은 의미 추출에만 사용
LLM은 다음 작업에 사용한다.

- idea 추출
- decision 추출
- question 추출
- action 추출
- concept 추출
- project 연결
- hyperedge 후보 생성
- conflict/supersede 판단
3.4 Memory write는 draft-first
agent나 LLM이 추출한 memory를 바로 영구 저장하지 않는다.

extraction result
→ memory draft
→ validation
→ deduplication
→ conflict check
→ user/harness approval
→ commit
v0.1에서는 draft와 committed 상태를 반드시 구분한다.

3.5 User-origin과 AI-origin 분리
모든 memory는 origin을 가져야 한다.

origin:
- user
- assistant
- mixed
- unknown
사용자가 직접 말한 아이디어와 AI가 제안한 아이디어를 절대 섞지 않는다.

4. 추천 repo 구조
memory-os/
├── apps/
│   ├── cli/
│   └── web/
│
├── services/
│   ├── memory-api/
│   ├── memory-mcp/
│   ├── ingestion-worker/
│   ├── extraction-worker/
│   ├── hypergraph-worker/
│   ├── embedding-worker/
│   └── harness/
│
├── packages/
│   ├── schemas/
│   ├── db/
│   ├── parsers/
│   ├── retrieval/
│   ├── hypergraph/
│   ├── llm/
│   └── config/
│
├── skills/
│   ├── conversation-to-memory-graph/
│   │   └── SKILL.md
│   ├── memory-first-workflow/
│   │   └── SKILL.md
│   ├── implementation-handoff/
│   │   └── SKILL.md
│   └── boot-orientation/
│       └── SKILL.md
│
├── AGENTS.md
├── README.md
├── SECURITY.md
├── PRIVACY.md
├── docker-compose.yml
└── package.json
단순화를 원하면 v0.1은 이렇게 시작해도 된다.

memory-os/
├── src/
│   ├── cli/
│   ├── api/
│   ├── mcp/
│   ├── db/
│   ├── parsers/
│   ├── ingestion/
│   ├── extraction/
│   ├── hypergraph/
│   ├── retrieval/
│   └── schemas/
├── skills/
├── AGENTS.md
└── README.md
5. DB 설계
v0.1은 Postgres + pgvector를 권장한다.
더 가볍게 가려면 SQLite로 시작해도 되지만, agent memory system 확장을 생각하면 Postgres가 낫다.

5.1 conversations
CREATE TABLE conversations (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  source_conversation_id TEXT,
  title TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  imported_at TIMESTAMP DEFAULT NOW(),
  raw_ref TEXT,
  metadata JSONB DEFAULT '{}'
);
5.2 messages
CREATE TABLE messages (
  id TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id),
  source_message_id TEXT,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMP,
  model TEXT,
  parent_message_id TEXT,
  order_index INT,
  metadata JSONB DEFAULT '{}'
);
5.3 pairs
CREATE TABLE pairs (
  id TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id),
  input_message_id TEXT REFERENCES messages(id),
  output_message_id TEXT REFERENCES messages(id),
  input_text TEXT NOT NULL,
  output_text TEXT NOT NULL,
  turn_index INT,
  created_at TIMESTAMP,
  metadata JSONB DEFAULT '{}'
);
5.4 segments
CREATE TABLE segments (
  id TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id),
  title TEXT,
  summary TEXT,
  start_message_id TEXT REFERENCES messages(id),
  end_message_id TEXT REFERENCES messages(id),
  order_index INT,
  metadata JSONB DEFAULT '{}'
);
5.5 memory_drafts
CREATE TABLE memory_drafts (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  content TEXT NOT NULL,
  origin TEXT NOT NULL,
  project TEXT,
  confidence FLOAT,
  importance FLOAT,
  status TEXT DEFAULT 'draft',
  source TEXT,
  raw_refs JSONB DEFAULT '[]',
  concepts JSONB DEFAULT '[]',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);
type 후보:

idea
decision
question
action
preference
constraint
artifact
reflection
fact
origin 후보:

user
assistant
mixed
unknown
status 후보:

draft
active
stale
superseded
rejected
uncertain
5.6 memories
CREATE TABLE memories (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  content TEXT NOT NULL,
  origin TEXT NOT NULL,
  project TEXT,
  confidence FLOAT,
  importance FLOAT,
  status TEXT DEFAULT 'active',
  source TEXT,
  raw_refs JSONB DEFAULT '[]',
  concepts JSONB DEFAULT '[]',
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
5.7 nodes
CREATE TABLE nodes (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  label TEXT,
  content TEXT,
  source TEXT,
  source_ref TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'
);
node type 후보:

Message
Pair
Segment
Memory
Project
Concept
Decision
Question
Action
Artifact
Agent
Tool
Source
TimePeriod
5.8 hyperedges
CREATE TABLE hyperedges (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  label TEXT,
  summary TEXT,
  status TEXT DEFAULT 'active',
  importance FLOAT,
  confidence FLOAT,
  created_at TIMESTAMP DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'
);
hyperedge type 후보:

TurnEvent
EpisodeEvent
DecisionEvent
IdeaComposition
ConceptCluster
ActionDerivation
ContradictionSet
ProjectStateUpdate
SystemBootstrappingEvent
AgentHandoffEvent
5.9 hyperedge_members
CREATE TABLE hyperedge_members (
  hyperedge_id TEXT REFERENCES hyperedges(id),
  node_id TEXT REFERENCES nodes(id),
  role TEXT,
  weight FLOAT DEFAULT 1.0,
  order_index INT,
  metadata JSONB DEFAULT '{}',
  PRIMARY KEY (hyperedge_id, node_id, role)
);
role 후보:

evidence
input
output
concept
project
decision
question
action
constraint
artifact
actor
tool
result
cause
alternative
chosen_structure
5.10 project_states
CREATE TABLE project_states (
  id TEXT PRIMARY KEY,
  project TEXT UNIQUE NOT NULL,
  current_stage TEXT,
  north_star TEXT,
  active_goals JSONB DEFAULT '[]',
  active_constraints JSONB DEFAULT '[]',
  active_decisions JSONB DEFAULT '[]',
  open_questions JSONB DEFAULT '[]',
  next_actions JSONB DEFAULT '[]',
  updated_at TIMESTAMP DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'
);
5.11 embeddings
Postgres + pgvector 기준.

CREATE TABLE embeddings (
  id TEXT PRIMARY KEY,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  model TEXT NOT NULL,
  dimensions INT NOT NULL,
  embedding vector(1536),
  created_at TIMESTAMP DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'
);
target_type:

message
pair
segment
memory
node
hyperedge
project_state
6. ChatGPT Export Importer
6.1 입력
chatgpt-export.zip
내부에서 conversations.json을 찾는다.

6.2 처리
1. zip 압축 해제
2. conversations.json 로드
3. conversation별 id 생성
4. message tree flatten
5. role=user/assistant/system/tool 분리
6. timestamp 정규화
7. order_index 부여
8. messages 저장
9. user → assistant pair 생성
10. segment 생성
6.3 pair 생성 규칙
기본은 다음과 같다.

가장 가까운 user message 다음에 오는 assistant message를 pair로 묶는다.
단, system/tool/internal message는 pair에서 제외하거나 metadata로 보존한다.

7. Segment 생성
v0.1에서는 간단하게 해도 된다.

옵션 A: fixed window
N개 pair마다 segment 하나 생성
예:

10 pairs = 1 segment
옵션 B: title/conversation 단위
대화가 짧으면 conversation 전체를 segment 하나로 본다.

옵션 C: LLM topic segmentation
나중에 추가한다.

v0.1 추천:

conversation당 segment 1개
단, pair가 20개 이상이면 10 pair 단위로 segment 분할
8. LLM Extraction Worker
8.1 목적
segment에서 atomic memory와 hyperedge 후보를 추출한다.

8.2 입력
{
  "segment_id": "seg_123",
  "conversation_title": "...",
  "messages": [
    {
      "role": "user",
      "content": "..."
    },
    {
      "role": "assistant",
      "content": "..."
    }
  ]
}
8.3 출력 schema
{
  "atomic_memories": [
    {
      "type": "decision",
      "content": "메모리 시스템은 MCP 서버로 노출하고, 메모리 사용 절차는 Skill로 정의한다.",
      "origin": "mixed",
      "project": "MemoryOS",
      "concepts": ["MCP", "Skill", "Agent Harness", "Memory Graph"],
      "confidence": 0.93,
      "importance": 0.91,
      "status": "draft",
      "raw_refs": ["msg_001", "msg_002"]
    }
  ],
  "nodes": [
    {
      "type": "Concept",
      "label": "MCP",
      "content": "LLM/agent가 외부 도구와 메모리에 접근하는 표준 인터페이스"
    },
    {
      "type": "Concept",
      "label": "Skill",
      "content": "agent가 작업을 일관되게 수행하기 위한 workflow package"
    }
  ],
  "hyperedges": [
    {
      "type": "DecisionEvent",
      "label": "MemoryOS architecture split",
      "summary": "사용자는 메모리 시스템을 MCP 서버, Skill workflow, Harness, Hypergraph Memory로 분리해 설계하기로 했다.",
      "members": [
        {
          "node_label": "MCP",
          "role": "tool_interface",
