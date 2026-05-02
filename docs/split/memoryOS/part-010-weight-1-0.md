<!--
Source: docs/memoryOS.md
Source lines: 6301-7000
Source byte range: 173918-191840
Split title source: first-text
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 010: "weight": 1.0

Provenance: `docs/memoryOS.md` lines `6301-7000`, bytes `173918-191840`.

Local structure markers:

- Source line 6334: 9. Extraction Prompt
- Source line 6342: 1. Do not treat every sentence as memory.
- Source line 6343: 2. Extract only durable or useful information.
- Source line 6344: 3. Separate user-originated ideas from assistant-suggested ideas.
- Source line 6345: 4. Mark origin as:
- Source line 6350: 5. Distinguish:
- Source line 6360: 6. If something was discussed but not decided, mark it as idea or question, not decision.
- Source line 6361: 7. Every memory must include raw_refs.
- Source line 6362: 8. Every memory must include confidence.
- Source line 6363: 9. Use hyperedges for multi-way cognitive events.
- Source line 6364: 10. Do not invent facts not supported by the segment.
- Source line 6371: 10. Hypergraph 설계 원칙

---

          "weight": 1.0
        },
        {
          "node_label": "Skill",
          "role": "workflow_policy",
          "weight": 1.0
        },
        {
          "node_label": "Agent Harness",
          "role": "orchestrator",
          "weight": 1.0
        }
      ],
      "confidence": 0.9,
      "importance": 0.92
    }
  ],
  "project_state_updates": [
    {
      "project": "MemoryOS",
      "active_decisions": [
        "Memory access should be exposed through MCP.",
        "Memory usage workflows should be encoded as Skills.",
        "Memory writes should be draft-first."
      ],
      "open_questions": [],
      "next_actions": [
        "Implement ChatGPT export parser.",
        "Implement memory MCP server."
      ]
    }
  ]
}
9. Extraction Prompt
LLM에게 줄 기본 prompt는 다음과 같다.

You are a memory extraction agent for a local-first Agent Memory OS.

Given a conversation segment, extract structured memory objects.

Important rules:
1. Do not treat every sentence as memory.
2. Extract only durable or useful information.
3. Separate user-originated ideas from assistant-suggested ideas.
4. Mark origin as:
   - user
   - assistant
   - mixed
   - unknown
5. Distinguish:
   - idea
   - decision
   - question
   - action
   - preference
   - constraint
   - artifact
   - reflection
   - fact
6. If something was discussed but not decided, mark it as idea or question, not decision.
7. Every memory must include raw_refs.
8. Every memory must include confidence.
9. Use hyperedges for multi-way cognitive events.
10. Do not invent facts not supported by the segment.

Return strict JSON with:
- atomic_memories
- nodes
- hyperedges
- project_state_updates
10. Hypergraph 설계 원칙
일반 edge는 1:1 관계에 사용한다.
Hyperedge는 여러 개념/메시지/결정/행동이 하나의 의미 사건으로 묶일 때 사용한다.

예시
하나의 대화 segment에서 다음이 동시에 등장:
- MCP
- Skill
- Agent Harness
- Memory Graph
- Draft-first write
- Local-first architecture

이것은 각각 따로 연결하지 말고
DecisionEvent 또는 IdeaComposition hyperedge로 묶는다.
Hyperedge는 자체 summary와 embedding을 가져야 한다
node embedding:
개별 메시지/개념/결정의 의미

hyperedge embedding:
여러 node가 결합된 사고 사건의 의미
11. Retrieval 설계
MCP로 agent가 memory를 검색할 때 단순 vector search만 하면 안 된다.

검색 흐름:

1. query 분석
2. project 감지
3. memory vector search
4. hyperedge vector search
5. project_state 조회
6. hyperedge member expansion
7. reranking
8. context pack 생성
Reranking 기준
score =
  semantic_similarity * 0.35
+ hyperedge_relevance * 0.25
+ importance * 0.15
+ confidence * 0.10
+ recency * 0.10
+ status_bonus * 0.05
status는 active를 우선한다.
superseded, rejected, stale은 기본 검색에서 낮춘다.

12. MCP Server v0.1
12.1 필수 tools
project.get_state
입력:

{
  "project": "MemoryOS"
}
출력:

{
  "project": "MemoryOS",
  "current_stage": "...",
  "north_star": "...",
  "active_goals": [],
  "active_constraints": [],
  "active_decisions": [],
  "open_questions": [],
  "next_actions": []
}
memory.search
입력:

{
  "query": "MCP와 Skill은 어떻게 나눠야 하지?",
  "project": "MemoryOS",
  "types": ["decision", "idea", "question"],
  "status": ["active"],
  "origin": "user",
  "limit": 10
}
출력:

{
  "results": [
    {
      "id": "mem_123",
      "type": "decision",
      "content": "...",
      "origin": "mixed",
      "project": "MemoryOS",
      "status": "active",
      "confidence": 0.93,
      "importance": 0.91,
      "raw_refs": ["msg_001", "msg_002"],
      "why_relevant": "..."
    }
  ]
}
hypergraph.search
입력:

{
  "query": "agent harness memory system MCP skill",
  "project": "MemoryOS",
  "types": ["DecisionEvent", "IdeaComposition"],
  "limit": 5
}
출력:

{
  "results": [
    {
      "id": "he_123",
      "type": "DecisionEvent",
      "label": "MemoryOS architecture split",
      "summary": "...",
      "members": [
        {
          "node_id": "node_mcp",
          "label": "MCP",
          "role": "tool_interface"
        }
      ],
      "confidence": 0.9,
      "importance": 0.92
    }
  ]
}
ingestion.import_file
입력:

{
  "file_path": "/path/to/chatgpt-export.zip",
  "source_hint": "chatgpt"
}
출력:

{
  "source": "chatgpt",
  "conversations": 100,
  "messages": 2000,
  "pairs": 900,
  "segments": 120,
  "status": "imported"
}
memory.extract_drafts
입력:

{
  "segment_ids": ["seg_123"],
  "model": "local_or_api"
}
출력:

{
  "drafts_created": 12,
  "hyperedge_drafts_created": 4,
  "project_state_updates_created": 1
}
memory.commit_drafts
입력:

{
  "draft_ids": ["draft_123", "draft_124"]
}
출력:

{
  "committed": 2,
  "memories": ["mem_123", "mem_124"]
}
13. Agent Harness v0.1
Harness는 다음 역할을 가진다.

1. task 분석
2. project 감지
3. context pack 구성
4. 어떤 agent/model을 쓸지 결정
5. MCP 호출 통제
6. memory draft commit 통제
7. run log 저장
v0.1에서는 단순하게 구현한다.

- CLI command로 harness 실행
- agent registry yaml 읽기
- tool permission 확인
- memory search 후 prompt 생성
agent_registry.yaml 예시
agents:
  claude:
    role: architect_reviewer
    strengths:
      - architecture_reasoning
      - long_context_synthesis
      - critique
    permissions:
      memory_read: true
      memory_write_draft: true
      memory_commit: false
      repo_write: false

  codex:
    role: implementation_agent
    strengths:
      - code_editing
      - test_fixing
      - repo_modification
    permissions:
      memory_read: true
      memory_write_draft: true
      memory_commit: false
      repo_write: true

  local_llm:
    role: batch_extraction_agent
    strengths:
      - cheap_classification
      - private_processing
      - memory_draft_generation
    permissions:
      memory_read_batch: true
      memory_write_draft: true
      memory_commit: false
      repo_write: false
14. Boot Orientation
처음 시스템을 실행하면 agent와 tool과 user memory를 탐색하는 boot phase가 있어야 한다.

Boot phase 목표
1. 사용 가능한 agent 확인
2. 사용 가능한 MCP/tool/connector 확인
3. 사용자의 기존 memory 분석
4. 주요 project와 작업 패턴 파악
5. agent별 역할 정의
6. routing policy 생성
7. SystemBootstrappingEvent hyperedge 저장
생성 파일
agent_registry.yaml
tool_registry.yaml
routing_policy.yaml
user_work_profile.json
memory_policy.yaml
v0.1에서는 파일 템플릿만 만들어도 된다.

15. Skills
15.1 conversation-to-memory-graph
skills/conversation-to-memory-graph/SKILL.md

---
name: conversation-to-memory-graph
description: Use this skill when importing, parsing, summarizing, and converting AI conversations into local memory graph entries.
---

# Conversation to Memory Graph Workflow

Goal:
Convert AI conversation exports into structured local memory:
- conversations
- messages
- input-output pairs
- segments
- atomic memories
- hyperedges
- embeddings
- project state updates

Procedure:
1. Detect source type.
2. Use deterministic parser first.
3. Normalize into common schema.
4. Build input-output pairs.
5. Segment conversations.
6. Extract memory drafts:
   - ideas
   - decisions
   - questions
   - actions
   - constraints
   - preferences
   - artifacts
   - concepts
7. Separate origin:
   - user
   - assistant
   - mixed
   - unknown
8. Build hyperedge drafts for multi-way cognitive events.
9. Attach raw_refs to every memory.
10. Validate and deduplicate.
11. Do not commit directly.
12. Commit only after validation or harness approval.
15.2 memory-first-workflow
---
name: memory-first-workflow
description: Use this skill before any non-trivial planning, coding, research, or project task that may depend on prior user context.
---

# Memory-first Workflow

1. Identify project and task type.
2. Call project.get_state if project is detected.
3. Call memory.search for relevant decisions, constraints, and open questions.
4. Call hypergraph.search for multi-concept or cross-project tasks.
5. Prefer active decisions over stale/superseded memories.
6. Separate user-originated ideas from assistant-suggested ideas.
7. Build a compact context pack.
8. Complete the task.
9. Write memory drafts for new decisions, actions, and open questions.
10. Do not directly commit memory unless explicitly authorized.
15.3 implementation-handoff
---
name: implementation-handoff
description: Use when turning architecture or planning output into implementation tasks for a coding agent.
---

# Implementation Handoff

Output must include:
- objective
- files_to_modify
- constraints
- acceptance_criteria
- relevant_memories
- commands_to_run
- expected_outputs
- unresolved_questions

Rules:
1. Keep implementation scope small.
2. Provide concrete file paths.
3. Define tests or verification.
4. Include memory references when relevant.
5. Do not let coding agent infer product philosophy from scratch.
15.4 boot-orientation
---
name: boot-orientation
description: Use when initializing the multi-agent memory system for the first time.
---

# Boot Orientation Workflow

1. Discover available agents.
2. Discover available MCP servers, tools, and connectors.
3. Generate initial agent self-profiles.
4. Run small capability probes when possible.
5. Analyze existing user memory.
6. Generate user_work_profile.
7. Generate agent_registry.
8. Generate tool_registry.
9. Generate routing_policy.
10. Store SystemBootstrappingEvent as hyperedge.
11. Mark initial conclusions as provisional.
16. AGENTS.md
repo root에 반드시 작성한다.

# AGENTS.md

## Project

This repository implements MemoryOS, a local-first open-source memory layer for AI agents.

## Core Architecture

MemoryOS imports AI conversation exports, parses them locally, extracts structured memories, builds a hypergraph memory system, and exposes memory to agents through MCP.

## Core Rules

- Memory access must go through MCP tools.
- Do not directly modify memory DB outside repository/service layer.
- Do not parse raw conversation exports with LLMs unless deterministic parsers fail.
- Use LLMs for semantic extraction, not raw parsing.
- All memory writes must be draft-first.
- Every memory must include:
  - type
  - content
  - origin
  - source
  - confidence
  - status
  - raw_refs
- User-originated ideas and assistant-suggested ideas must be separated.
- Hyperedges represent multi-way cognitive events.
- Prefer active decisions over stale or superseded memories.
- Do not expose secrets or raw private data to external models by default.

## Commands

- pnpm install
- pnpm dev
- pnpm test
- pnpm lint
- pnpm typecheck
- pnpm db:migrate

## Done Means

- Code compiles.
- Tests pass or failure is clearly explained.
- Schema changes include migration.
- MCP tool contracts are updated.
- Memory updates are written as drafts, not committed directly.
17. CLI 명령
v0.1에서 제공할 CLI.

memory-os init
memory-os import ./chatgpt-export.zip
memory-os extract --all
memory-os index
memory-os ask "내가 MemoryOS에 대해 결정한 것 보여줘"
memory-os mcp start
memory-os status
명령별 동작
memory-os init
- config 생성
- DB 연결 확인
- migration 실행
- 기본 project_state 생성
memory-os import
- source detect
- parse
- normalize
- save conversations/messages/pairs/segments
memory-os extract
- segment 기반 memory draft 생성
- hyperedge draft 생성
- project state update draft 생성
memory-os index
- embedding 생성
- node/hyperedge indexing
memory-os ask
- memory.search
- hypergraph.search
- project_state 조회
- context pack 생성
- 답변
memory-os mcp start
- MCP server 시작
- Claude/Codex/Cursor 연결 가능
18. README 핵심 문구
README 첫 부분은 이렇게 작성한다.

# MemoryOS

Local-first memory layer for AI agents.

MemoryOS turns your AI conversations into a local memory graph that Claude, Codex, Cursor, local LLMs, and custom agents can use through MCP.

## What it does

- Imports ChatGPT conversation exports
- Parses conversations locally
- Builds input-output pairs
- Extracts decisions, ideas, actions, questions, and concepts
- Builds a hypergraph memory system
- Exposes memory through MCP
- Keeps user data on-device by default

## Why

AI agents should not start from zero every session.
Your previous conversations, decisions, projects, and unfinished questions should become reusable memory.
19. 보안 원칙
SECURITY.md에 넣을 내용.

1. MCP server는 기본 localhost only.
2. 외부 네트워크 bind 금지.
3. raw export 접근은 제한.
4. memory write는 draft-first.
5. destructive action은 user approval 필요.
6. secrets는 model context에 노출하지 않음.
7. agent별 permission 분리.
8. audit log 저장.
9. external API 사용 시 사용자 명시 설정 필요.
10. raw data 삭제/export 기능 제공.
20. Privacy 원칙
PRIVACY.md에 넣을 내용.

- MemoryOS is local-first.
- Imported conversations stay on the user's device by default.
- MemoryOS does not train models on user data.
- Users can delete raw imports.
- Users can export all stored memory.
- Users can choose local or external embedding/LLM providers.
- External API usage is opt-in.
21. Implementation Priority
작업 순서는 반드시 이렇게 간다.

Phase 1 — Core DB + ChatGPT Import
1. DB schema 작성
2. migration
3. ChatGPT export parser
4. conversation/message 저장
5. pair 생성
6. segment 생성
Phase 2 — Memory Extraction
1. extraction schema 작성
2. extraction prompt 작성
3. LLM provider interface 작성
4. memory_drafts 저장
5. hyperedge_drafts 저장
Phase 3 — Search
1. keyword search
2. vector embedding 저장 구조
3. memory.search 구현
4. hypergraph.search 구현
5. project.get_state 구현
Phase 4 — MCP
1. MCP server scaffold
2. project.get_state tool
3. memory.search tool
4. hypergraph.search tool
5. ingestion.import_file tool
Phase 5 — CLI
1. memory-os init
2. memory-os import
3. memory-os extract
4. memory-os ask
5. memory-os mcp start
Phase 6 — Skills + Docs
1. AGENTS.md
2. SKILL.md files
3. README
4. SECURITY
5. PRIVACY
22. Acceptance Criteria
v0.1 완료 기준:

1. ChatGPT export.zip을 import할 수 있다.
2. conversations/messages/pairs/segments가 DB에 저장된다.
3. segment에서 memory_drafts가 생성된다.
4. memory_drafts에는 type/origin/confidence/raw_refs가 있다.
5. nodes/hyperedges/hyperedge_members가 생성된다.
6. memory.search가 동작한다.
7. hypergraph.search가 동작한다.
8. project.get_state가 동작한다.
9. MCP server가 위 tool들을 노출한다.
10. Codex/Claude/Cursor에서 MCP 연결 가능하도록 config 예시가 있다.
11. AGENTS.md와 최소 4개 Skill이 존재한다.
12. README만 보고 개발자가 실행할 수 있다.
23. 가장 중요한 구현 판단
절대 처음부터 완벽한 agent OS를 만들려고 하지 말 것.

v0.1의 핵심 증명은 하나다.

내 ChatGPT 대화 export가
로컬에서 파싱되고
memory graph가 되고
MCP를 통해 agent가 검색할 수 있다.
이게 되면 나머지는 확장이다.

24. Codex/Claude에게 줄 짧은 작업 프롬프트
아래를 그대로 붙여넣어도 된다.

We are building MemoryOS v0.1.

Goal:
Create a local-first open-source memory layer for AI agents.

MVP:
- Import ChatGPT export.zip
- Parse conversations.json
- Store conversations/messages/pairs/segments
- Extract memory drafts from segments
- Build nodes/hyperedges/hyperedge_members
- Provide memory.search, hypergraph.search, project.get_state
- Expose these through an MCP server
- Provide CLI commands:
  - memory-os init
  - memory-os import
  - memory-os extract
  - memory-os ask
  - memory-os mcp start
- Add AGENTS.md and Skills:
  - conversation-to-memory-graph
  - memory-first-workflow
  - implementation-handoff
  - boot-orientation

Core rules:
- Local-first.
- Parser must be deterministic code.
- LLM is used for semantic extraction, not raw parsing.
- Memory writes are draft-first.
- Every memory needs type, content, origin, source, confidence, status, raw_refs.
- User-originated ideas and assistant-suggested ideas must be separated.
- Hyperedges represent multi-way cognitive events.
- Expose memory to agents through MCP.

Implement in small phases:
1. DB schema and migrations
2. ChatGPT importer
3. Pair/segment builder
4. Extraction schema and draft writer
5. Hypergraph builder
6. Search functions
7. MCP server
8. CLI
9. Docs and Skills

Do not overbuild.
First prove:
ChatGPT export → local memory graph → MCP search.
25. 너한테 지금 당장 할 일
오늘은 이것만 하면 돼.

1. repo 생성
2. AGENTS.md 작성
3. 위 Skill 4개 생성
4. DB schema 작성
5. ChatGPT export parser부터 구현
첫 목표는 딱 하나:

chatgpt-export.zip 넣었을 때
conversations / messages / pairs가 DB에 들어가게 만들기
그 다음에 extraction, hypergraph, MCP 붙이면 된다.


Desktop까지 가면? Visual도 생각

Desktop까지 가면 제품의 성격이 확 바뀌어. CLI/MCP는 개발자용 코어이고, Desktop은 사용자가 “내 기억이 살아 있다”고 느끼는 시각적 운영실이 되어야 해.

몇 초 동안 생각함
Desktop까지 가면 **MemoryOS는 단순 개발자 도구가 아니라 “개인 기억을 조작하는 시각적 운영체제”**가 돼야 해.

CLI/MCP의 핵심이 이것이었다면:

ChatGPT export → local memory graph → MCP search
Desktop의 핵심은 이거야.

내가 쌓아온 대화, 생각, 결정, 프로젝트가
눈에 보이는 구조로 살아 움직이는 느낌
1. Desktop 제품 정의
제품 한 줄
MemoryOS Desktop은 사용자의 AI 대화와 작업 기록을 로컬 memory graph로 변환하고, 이를 시각적으로 탐색·정리·승인·agent에 연결하는 개인용 AI memory cockpit이다.

