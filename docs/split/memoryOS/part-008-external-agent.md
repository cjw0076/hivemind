<!--
Source: docs/memoryOS.md
Source lines: 4901-5600
Source byte range: 140674-157651
Split title source: first-text
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 008: external_agent:

Provenance: `docs/memoryOS.md` lines `4901-5600`, bytes `140674-157651`.

Local structure markers:

- Source line 4904: 17. Memory write 정책
- Source line 4924: 18. Open source 라이선스
- Source line 4946: 19. README에서 바로 보여줘야 할 것
- Source line 4951: # MemoryOS
- Source line 4955: ## What it does
- Source line 4962: ## Quickstart
- Source line 4964: ## Connect to Codex
- Source line 4966: ## Connect to Claude Desktop / Claude Code
- Source line 4968: ## Architecture
- Source line 4970: ## Security model
- Source line 4972: ## Roadmap
- Source line 4974: ## License

---

  external_agent:
    memory.search: allow_filtered
    raw_access: deny
17. Memory write 정책
절대 agent가 바로 영구 memory에 쓰면 안 돼.

정책:

agent output
→ memory draft
→ validation
→ deduplication
→ conflict check
→ user/harness approval
→ commit
UI에는 “Pending Memory Drafts”가 있어야 해.

New decision detected:
“MemoryOS should expose memory as MCP and usage workflow as Skills.”

[Accept] [Edit] [Reject]
이게 있어야 memory system이 오염되지 않아.

18. Open source 라이선스
라이선스는 전략적으로 골라야 해.

완전 개방/확산
Apache-2.0
기업도 쓰기 좋고 특허 조항도 있음.

커뮤니티 보호/상업적 클라우드 견제
AGPL-3.0
서버로 돌려도 소스 공개 의무가 생김.

추천
나는 초기에는 Apache-2.0 추천.
이유는 agent/MCP ecosystem에서 빠르게 퍼지는 게 중요하기 때문.

하지만 SaaS 경쟁을 막고 싶으면 core는 AGPL, SDK는 MIT/Apache로 나누는 dual 구조도 가능해.

memory-os core: AGPL
sdk/mcp client: Apache-2.0
schemas: MIT
초기엔 복잡하게 가지 말고 Apache-2.0이 낫다.

19. README에서 바로 보여줘야 할 것
오픈소스는 첫 화면에서 바로 이해돼야 해.

README 구조:

# MemoryOS

Local-first memory layer for AI agents.

## What it does

- Import your ChatGPT/Claude/Gemini conversations
- Build a local memory graph
- Expose memory to Claude, Codex, Cursor, and local agents through MCP
- Keep user data on-device by default

## Quickstart

## Connect to Codex

## Connect to Claude Desktop / Claude Code

## Architecture

## Security model

## Roadmap

## License
핵심 이미지는 이거 하나.

AI Exports → Local Memory Graph → MCP Server → Claude/Codex/Local Agents
20. MVP Production Scope
처음 공개 버전은 너무 크게 내면 안 돼.

v0.1: Developer Preview
CLI
Postgres + pgvector
ChatGPT export importer
memory.search
project.get_state
hypergraph.search
Codex MCP config example
basic dashboard
v0.2: Local Desktop Alpha
Desktop UI
Claude export importer
Gemini Takeout importer
memory draft review
project state view
v0.3: Agent Harness Alpha
agent registry
tool registry
boot orientation
routing policy
Claude/Codex handoff
run logs
v0.4: Memory Reflection
daily/weekly summaries
decision extraction
open question tracking
superseded memory detection
v1.0: Stable Local Memory OS
stable schema
stable MCP tools
desktop app
backup/export/delete
security hardening
plugin system
docs
21. 실제 v0.1에 들어갈 기능만 자르면
진짜 첫 공개판은 이것만.

1. ChatGPT export.zip import
2. conversations/messages/pairs 저장
3. node/hyperedge 생성
4. embedding 생성
5. ask memory
6. MCP server 제공
7. Codex/Claude 연결 예시
8. local-only privacy guarantee
기능 욕심내면 망해.
처음 가치는 이것만 증명하면 돼.

“내 ChatGPT 대화가 로컬 memory graph가 되고, Codex/Claude가 MCP로 읽을 수 있다.”

이게 되면 충분히 강하다.

22. 최종 사용자 경험
사용자는 이런 흐름을 겪어야 해.

앱 설치
→ “Import your AI history”
→ ChatGPT export 업로드
→ “We found 4,812 conversations”
→ “We extracted 28,440 message pairs”
→ “Your main projects: Uri, MemoryOS, Deepfake, Capstone”
→ “Connect to Codex / Claude”
→ 자동 config 생성
→ Codex에서 질문:
   “Use my MemoryOS context and implement the MCP server”
→ Codex가 memory.search 호출
→ 과거 결정 기반으로 코드 작성
여기서 사용자가 느끼는 가치는:

“AI가 이제 나를 처음 보는 것처럼 행동하지 않는다.”
23. 최종 System Production 이름
이름 후보:

MemoryOS
TraceOS
Mnemo
RecallGraph
AgentMemory
ContextLayer
Second Context
MindGraph
오픈소스 프로젝트명은 너무 감성적이면 안 되고 명확해야 해.

추천:

MemoryOS
또는 더 개발자 친화적으로:

agent-memory-os
GitHub repo:

github.com/your-org/memory-os
github.com/your-org/agent-memory-os
24. Production-ready 판단 기준
이 기준을 통과해야 v1.0이야.

설치:
- 비개발자도 desktop app 실행 가능
- 개발자는 docker compose로 실행 가능

데이터:
- raw import 보존/삭제 선택 가능
- 전체 export/delete 가능
- schema migration 안정적

검색:
- semantic search 가능
- project state 검색 가능
- hypergraph expansion 가능

Agent:
- MCP로 Claude/Codex 연결 가능
- read-only tools 안정적
- write draft review 가능

보안:
- localhost only 기본값
- 권한 분리
- audit log
- raw data 암호화 옵션
- destructive action approval

오픈소스:
- README 명확
- example data
- MCP config examples
- CONTRIBUTING.md
- SECURITY.md
25. 최종 그림
최종 Production은 이 형태가 맞아.

MemoryOS
= Local-first open-source memory layer for AI agents

Core:
- 개인 AI 대화/문서/작업을 memory graph로 변환

Storage:
- Postgres/SQLite + vector + hypergraph schema

Interface:
- Desktop UI
- CLI
- MCP server
- REST API

Agent Layer:
- Claude / Codex / local LLM / custom agents
- Skills
- AGENTS.md
- Harness router

Security:
- local-first
- encrypted
- permissioned
- draft-first memory commit

Future:
- optional cloud sync
- team workspace
- personal encoder
- marketplace of skills/connectors
한 문장으로 끝내면:

최종 제품은 “개인 디바이스 위에서 실행되는 오픈소스 AI memory kernel”이어야 한다. Desktop app은 껍데기이고, 진짜 핵심은 MCP로 노출되는 local hypergraph memory system과 agent harness다.

너는 이걸 SaaS 앱처럼 시작하면 안 되고, 개발자들이 자기 Claude/Codex/local agent에 꽂아 쓰는 local-first infrastructure로 시작해야 해. 그게 신뢰도, 확산성, 오픈소스 생태계 측면에서 제일 강하다.


대화 내용도 자동으로 agent나 llm api가 정리해 로컬에 파싱하고 메모리 그래프 생성하게 해주려면? Skill형태여야 하나?

몇 초 동안 생각함
응. **“대화 내용을 자동으로 정리 → 로컬 파싱 → 메모리 그래프 생성”**은 Skill 하나로 끝나는 게 아니라, 구조적으로는 이렇게 나눠야 해.

자동 정리/파싱/그래프 생성은 Worker Pipeline이고,
그 파이프라인을 agent가 올바르게 실행하도록 만드는 운영 절차가 Skill이다.

즉 결론은:

핵심 기능 = local ingestion / parsing / extraction pipeline
Agent 사용법 = Skill
외부 접근 인터페이스 = MCP
실행 통제 = Harness
1. Skill 하나로 만들면 안 됨
Skill은 “절차 설명서”에 가까워.

예를 들어 Skill은 agent에게 이렇게 말해줄 수 있어.

새로운 대화 export가 들어오면:
1. source를 식별하라.
2. parser를 선택하라.
3. message/pair/segment를 생성하라.
4. decision/action/concept를 추출하라.
5. hyperedge를 생성하라.
6. draft memory를 만들고 검증하라.
7. commit 전 conflict를 확인하라.
하지만 Skill 자체가 DB, parser, embedding, graph builder를 대신하지는 않아.

그래서 실제 구현은 이렇게 해야 해.

Skill
= agent에게 “어떻게 처리할지” 알려줌

Worker
= 실제로 대화 파일을 파싱하고 정리함

MCP Tool
= agent가 Worker와 Memory DB를 호출하게 해줌

Harness
= 전체 실행 순서와 권한을 통제함
2. 최종 구조
ChatGPT / Claude / Gemini / Perplexity export
        ↓
Local File Watcher or Manual Upload
        ↓
Ingestion Worker
        ↓
Source Detector
        ↓
Parser
        ↓
Normalizer
        ↓
Chunker / Pair Builder
        ↓
LLM Extraction Worker
        ↓
Memory Drafts
        ↓
Validation / Dedup / Conflict Check
        ↓
Hypergraph Builder
        ↓
Embedding Worker
        ↓
Local Memory DB
        ↓
MCP Server
        ↓
Claude / Codex / Local Agent
여기서 agent나 LLM API는 주로 이 부분에 들어간다.

1. conversation segmentation
2. summary 생성
3. concept 추출
4. decision/action/question 추출
5. hyperedge 후보 생성
6. conflict/supersede 판단
7. project_state 업데이트 초안 생성
반면 deterministic하게 처리해야 하는 부분은 코드로 처리한다.

1. zip 압축 해제
2. JSON/HTML 파싱
3. message 순서 복원
4. role 분리
5. timestamp 정규화
6. DB insert
7. id 생성
8. duplicate check
3. 역할 분리
A. Parser는 코드로
대화 export 파싱은 LLM에게 맡기면 안 돼.
이건 deterministic해야 해.

ChatGPT parser
Claude parser
Gemini Takeout parser
Perplexity manual parser
Markdown parser
JSON parser
결과는 공통 schema로 맞춘다.

{
  "conversation_id": "chatgpt_123",
  "source": "chatgpt",
  "title": "Memory OS 설계",
  "messages": [
    {
      "id": "msg_001",
      "role": "user",
      "content": "...",
      "created_at": "2026-04-30T15:00:00+09:00"
    },
    {
      "id": "msg_002",
      "role": "assistant",
      "content": "...",
      "created_at": "2026-04-30T15:00:20+09:00"
    }
  ]
}
B. LLM은 의미 추출에 사용
LLM은 파싱이 아니라 해석에 써야 해.

이 대화에서 핵심 아이디어는?
사용자가 실제로 결정한 것은?
미해결 질문은?
실행해야 할 action은?
어떤 프로젝트와 연결되는가?
어떤 개념들이 같이 등장하는가?
이전 memory와 충돌하는가?
예시 출력:

{
  "atomic_memories": [
    {
      "type": "decision",
      "content": "메모리 시스템은 MCP 서버로 노출하고, 사용 절차는 Skill로 정의한다.",
      "project": "MemoryOS",
      "origin": "user+assistant",
      "confidence": 0.93,
      "status": "active"
    },
    {
      "type": "concept",
      "content": "Skill은 기능 구현체가 아니라 agent가 작업을 수행하는 절차 패키지다.",
      "project": "MemoryOS",
      "confidence": 0.9
    }
  ],
  "hyperedges": [
    {
      "type": "DecisionEvent",
      "label": "MemoryOS architecture split",
      "members": [
        {
          "node": "MCP",
          "role": "tool_interface"
        },
        {
          "node": "Skill",
          "role": "workflow_policy"
        },
        {
          "node": "Harness",
          "role": "orchestrator"
        },
        {
          "node": "Memory Graph",
          "role": "storage_substrate"
        }
      ]
    }
  ]
}
C. Embedding은 worker로
LLM extraction 이후에는 embedding worker가 돈다.

message embedding
pair embedding
segment embedding
memory embedding
hyperedge embedding
project_state embedding
이건 API embedding을 써도 되고, 로컬 embedding 모델을 써도 돼.

초기 추천:

민감한 원문 → local embedding
고성능 검색 → optional API embedding
4. Skill은 어디에 들어가나
Skill은 자동 정리 시스템 전체에서 agent가 이 pipeline을 다루는 방법을 정의한다.

예를 들면 이런 Skill이 필요해.

conversation-ingestion-skill
memory-extraction-skill
hypergraph-construction-skill
memory-dedup-conflict-skill
project-state-update-skill
하지만 처음에는 하나로 시작해도 돼.

conversation-to-memory-graph
5. Skill 예시
skills/conversation-to-memory-graph/SKILL.md

---
name: conversation-to-memory-graph
description: Use this skill when importing, parsing, summarizing, and converting AI conversations into local memory graph entries.
---

# Conversation to Memory Graph Workflow

## Goal

Convert AI conversation exports into structured local memory:
- conversations
- messages
- input-output pairs
- segments
- atomic memories
- hyperedges
- embeddings
- project state updates

## Procedure

1. Detect source type:
   - ChatGPT export
   - Claude export
   - Gemini Takeout
   - Perplexity thread
   - Markdown/manual import

2. Use deterministic parser first.
   Do not use an LLM to parse raw JSON or HTML unless parser fails.

3. Normalize into the common schema:
   - conversation
   - message
   - pair
   - segment

4. Run memory extraction:
   Extract:
   - ideas
   - decisions
   - questions
   - actions
   - constraints
   - preferences
   - artifacts
   - concepts

5. Separate origin:
   - user-originated
   - assistant-suggested
   - mixed
   - uncertain

6. Build hyperedges:
   Use hyperedges for multi-way cognitive events:
   - DecisionEvent
   - IdeaComposition
   - ConceptCluster
   - ActionDerivation
   - ContradictionSet
   - SystemBootstrappingEvent

7. Validate:
   - deduplicate similar memories
   - check stale/superseded memories
   - attach raw_refs
   - assign confidence and importance

8. Do not commit directly.
   Create memory drafts first.

9. Commit only after validation or harness approval.

## Required MCP tools

- ingestion.detect_source
- ingestion.parse
- memory.write_draft
- memory.search
- hypergraph.create_draft
- embedding.enqueue
- context.commit_session
이 Skill은 “LLM이 알아서 정리하게 해줘”가 아니라, 정리할 때 지켜야 할 절차를 강제하는 역할이야.

6. MCP tools는 이렇게 필요함
자동화하려면 MCP 쪽에는 이런 tool이 있어야 해.

ingestion.detect_source(file_path)
ingestion.parse(file_path, source_type)
ingestion.normalize(parsed_data)
ingestion.build_pairs(conversation_id)
ingestion.segment(conversation_id)

memory.extract(segment_id)
memory.write_draft(memory_objects)
memory.validate_drafts(draft_ids)
memory.commit_drafts(draft_ids)

hypergraph.build_from_memories(memory_ids)
hypergraph.create_draft(hyperedge)
hypergraph.commit(hyperedge_id)

embedding.enqueue(target_type, target_id)
embedding.status(job_id)

project.suggest_state_update(project_id, memory_ids)
project.update_state(project_id, patch)
처음 MVP는 이 정도만 있으면 돼.

ingestion.import_file
memory.extract_drafts
hypergraph.build_drafts
embedding.index
context.commit_session
7. 자동 실행 방식
자동화를 하려면 3가지 방식이 있어.

1. Manual Import
사용자가 export 파일을 직접 넣음.

Upload ZIP
→ parse
→ extract
→ review
→ commit
초기 MVP에 가장 적합.

2. Watched Folder
특정 폴더에 파일을 넣으면 자동 처리.

~/MemoryOS/imports/
  chatgpt-export.zip
  claude-export.json
파일이 들어오면 local watcher가 감지한다.

new file detected
→ ingestion pipeline start
→ memory drafts created
→ user review notification
이게 개인 디바이스용으로 좋다.

3. Live Capture
브라우저 extension이나 desktop capture로 대화를 실시간 저장.

ChatGPT/Claude에서 대화
→ 사용자가 Save to MemoryOS 클릭
→ local API로 전송
→ parsing/extraction/indexing
단, 이건 나중에.
처음부터 live capture를 하면 약관/보안/유지보수 리스크가 커져.

8. 로컬 자동 정리 pipeline
구체적으로는 이렇게 구현하면 돼.

def import_conversation_file(file_path):
    source = detect_source(file_path)

    raw = load_raw(file_path)

    parsed = parse_by_source(raw, source)

    normalized = normalize_conversations(parsed)

    save_conversations(normalized)

    pairs = build_input_output_pairs(normalized)

    segments = segment_conversations(normalized)

    extraction_jobs = enqueue_memory_extraction(segments)

    embedding_jobs = enqueue_embeddings([
        normalized.messages,
        pairs,
        segments
    ])

    return {
        "source": source,
        "conversations": len(normalized.conversations),
        "messages": len(normalized.messages),
        "pairs": len(pairs),
        "segments": len(segments),
        "extraction_jobs": extraction_jobs,
        "embedding_jobs": embedding_jobs
    }
LLM extraction worker:

def extract_memory_from_segment(segment):
    prompt = build_extraction_prompt(segment)

    result = llm.generate_json(prompt, schema=MemoryExtractionSchema)

    drafts = validate_extraction(result)

    drafts = attach_raw_refs(drafts, segment)

    drafts = deduplicate_against_existing(drafts)

    save_memory_drafts(drafts)

    hyperedge_drafts = build_hyperedge_drafts(drafts)

    save_hyperedge_drafts(hyperedge_drafts)

    return drafts
9. 반드시 Draft-first여야 함
자동으로 정리된 내용을 바로 메모리에 넣으면 안 돼.

왜냐하면 LLM이 이런 실수를 할 수 있어.

사용자가 한 말과 AI가 한 말을 섞음
아이디어를 결정으로 오분류
옛날 맥락을 현재 상태로 오해
중요하지 않은 내용을 중요 memory로 저장
중복 memory를 계속 생성
그래서 flow는 반드시 이렇게.

Extracted Memory
→ Draft
→ Validation
→ Conflict Check
→ Review
→ Commit
자동 commit은 나중에 제한적으로만.

low-risk summary: auto commit 가능
decision/preference/user profile: review 필요
project state 변경: approval 필요
10. Memory Draft UI
앱에는 이런 화면이 있어야 해.

New memories extracted from conversation:

[Decision]
메모리 시스템은 MCP 서버와 Skill workflow를 함께 사용해야 한다.
source: current conversation
origin: mixed
confidence: 0.94
project: MemoryOS
