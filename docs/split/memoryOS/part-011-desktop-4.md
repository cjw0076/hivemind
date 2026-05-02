<!--
Source: docs/memoryOS.md
Source lines: 7001-7700
Source byte range: 191841-219139
Split title source: first-text
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 011: 즉, Desktop은 다음 4가지를 해야 해.

Provenance: `docs/memoryOS.md` lines `7001-7700`, bytes `191841-219139`.

Local structure markers:

- Source line 7003: 1. Import
- Source line 7006: 2. Understand
- Source line 7009: 3. Visualize
- Source line 7012: 4. Operate
- Source line 7014: 2. Desktop의 핵심 감각
- Source line 7035: 3. Visual North Star
- Source line 7073: 4. 전체 정보 구조
- Source line 7076: 1. Home / Memory Cockpit
- Source line 7077: 2. Import Center
- Source line 7078: 3. Ask Memory
- Source line 7079: 4. Project Memory
- Source line 7080: 5. Hypergraph Explorer

---

즉, Desktop은 다음 4가지를 해야 해.

1. Import
   AI 대화 export를 가져온다.

2. Understand
   대화에서 memory, decision, action, concept를 추출한다.

3. Visualize
   내 사고 흐름과 프로젝트 상태를 시각화한다.

4. Operate
   Claude, Codex, local LLM, agents가 이 memory를 쓰도록 연결한다.
2. Desktop의 핵심 감각
이 앱은 Notion처럼 문서 앱이면 안 돼.
Obsidian처럼 그래프만 보여줘도 부족해.
Raycast처럼 도구형이어도 부족해.

MemoryOS Desktop의 감각은 이쪽이야.

개인 기억의 관제실
AI agent의 상황판
내 사고의 타임라인
프로젝트의 결정 지도
대화 데이터의 정제소
키워드:

local
private
calm
technical
alive
graphical
memory cockpit
3. Visual North Star
시각적으로는 이런 느낌이 좋아.

Dark / warm neutral background
얇은 grid
부드러운 노드
은은한 glow
graph line은 과하지 않게
카드 UI는 단정하게
terminal-like detail은 숨김
너의 Uri 쪽이 따뜻한 campus/social graph였다면,
MemoryOS는 더 차분한 cognitive graph / memory cockpit 느낌이어야 해.

Uri = warm social graph
MemoryOS = calm cognitive graph
색감:

Background:
- near black
- deep navy
- warm charcoal

Primary:
- soft violet
- electric blue
- mint cyan

Accent:
- amber for decisions
- green for actions
- purple for concepts
- blue for messages
- red/orange for conflicts

Surface:
- translucent dark cards
- subtle border
- glassy but not flashy
4. 전체 정보 구조
Desktop은 7개 메인 화면이면 충분해.

1. Home / Memory Cockpit
2. Import Center
3. Ask Memory
4. Project Memory
5. Hypergraph Explorer
6. Draft Review
7. Agent Harness
추가로 Settings가 필요해.

8. Settings
   - local DB
   - LLM provider
   - embedding provider
   - MCP config
   - privacy
   - backup/export/delete
5. 화면 1 — Home / Memory Cockpit
앱을 켜면 사용자가 바로 봐야 하는 화면.

목적
내 memory system이 지금 어떤 상태인지 한눈에 보여준다.
구성
상단:
- MemoryOS logo
- Local status: Running locally
- MCP status: Connected / Disconnected
- Index status

중앙:
- Memory graph preview
- Active projects
- Recent decisions
- Open questions
- Pending memory drafts

하단:
- Recent imports
- Recent agent runs
예시 UI
┌─────────────────────────────────────────────────────────────┐
│ MemoryOS                                      Local ● MCP ●  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Your Memory Graph                                          │
│                                                             │
│        Uri ●──────● ESN                                     │
│          ╲        ╲                                         │
│           ● Agent Avatar ───● Offline-Online Graph          │
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Conversations│ │ Memories     │ │ Hyperedges   │        │
│  │ 4,812        │ │ 18,240       │ │ 2,931        │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                             │
│  Active Projects                                            │
│  - Uri                    12 open questions                 │
│  - MemoryOS               8 active decisions                │
│  - Deepfake Detection     4 next actions                    │
│                                                             │
│  Pending Drafts: 36      Agent Runs Today: 5                │
└─────────────────────────────────────────────────────────────┘
Home에서 중요한 것
사용자가 이런 느낌을 받아야 해.

“내 기억 시스템이 살아 있고,
지금 어떤 프로젝트가 활성화되어 있고,
AI agent들이 무엇을 참조할 수 있는지 보인다.”
6. 화면 2 — Import Center
목적
AI 대화를 가져오는 정제소.

주요 기능
- ChatGPT export.zip upload
- Claude export upload
- Gemini Takeout upload
- Markdown/manual import
- watched folder 설정
- import progress
- parsing 결과 확인
Import flow
1. Drop export file
2. Detect source
3. Parse locally
4. Show preview
5. Build pairs
6. Create segments
7. Run extraction
8. Generate memory drafts
9. Review or auto-save
Visual
┌─────────────────────────────────────────────┐
│ Import Center                               │
├─────────────────────────────────────────────┤
│                                             │
│  Drop your AI export here                   │
│  ┌───────────────────────────────────────┐  │
│  │    ChatGPT export.zip                 │  │
│  │    Claude export.json                 │  │
│  │    Gemini Takeout.zip                 │  │
│  └───────────────────────────────────────┘  │
│                                             │
│  Recent Imports                             │
│  ChatGPT export       4,812 conversations   │
│  Claude export        931 conversations     │
│                                             │
│  Processing Pipeline                        │
│  Parse  →  Normalize  →  Pair  →  Extract   │
│    ✓         ✓           ✓        running   │
└─────────────────────────────────────────────┘
7. 화면 3 — Ask Memory
이게 killer feature야.

목적
사용자가 자기 memory에 질문한다.

예:

“내가 MemoryOS에 대해 결정한 것만 보여줘.”

“Uri에서 아직 미해결인 질문은?”

“내가 반복해서 말한 agent memory 구조는?”

“내가 직접 말한 아이디어와 AI가 제안한 아이디어를 분리해줘.”
UI 구조
왼쪽:
- query input
- filters
  - project
  - source
  - origin
  - memory type
  - status
  - date

중앙:
- answer

오른쪽:
- retrieved memories
- hyperedges
- raw references
예시
┌─────────────────────────────────────────────────────────────┐
│ Ask Memory                                                  │
├─────────────────────────────────────────────────────────────┤
│ Query                                                       │
│ [ MemoryOS에서 MCP와 Skill은 어떻게 나누기로 했지?       ] │
│                                                             │
│ Filters                                                     │
│ Project: MemoryOS                                           │
│ Origin: user + mixed                                        │
│ Type: decision, idea                                        │
│ Status: active                                              │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Answer                                                      │
│                                                             │
│ 과거 대화 기준으로 MemoryOS에서는 MCP와 Skill을 이렇게     │
│ 분리하기로 했다.                                            │
│                                                             │
│ MCP는 실제 memory system에 접근하는 도구 인터페이스이고,   │
│ Skill은 agent가 그 도구를 어떤 절차로 사용할지 정의하는    │
│ workflow package다.                                         │
│                                                             │
│ Active Decisions                                            │
│ 1. Memory access는 MCP server로 노출한다.                   │
│ 2. Memory usage protocol은 Skill로 정의한다.                │
│ 3. Memory write는 draft-first로 한다.                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Evidence                                                    │
│ [DecisionEvent] MemoryOS architecture split                 │
│ [Memory] MCP is tool interface                              │
│ [Memory] Skill is workflow policy                           │
└─────────────────────────────────────────────────────────────┘
중요한 건 답변만 보여주면 안 되고, 왜 그렇게 답했는지 근거 hyperedge를 같이 보여줘야 함.

8. 화면 4 — Project Memory
목적
프로젝트별 현재 상태를 보여준다.

예:

Uri
MemoryOS
Deepfake Detection
Capstone
North Star Research
Project page 구성
Project Header
- 이름
- 현재 단계
- north star
- 최근 업데이트

Tabs:
1. Overview
2. Decisions
3. Open Questions
4. Actions
5. Concepts
6. Conversations
7. Artifacts
예시
┌─────────────────────────────────────────────────────────────┐
│ Project: MemoryOS                                           │
├─────────────────────────────────────────────────────────────┤
│ North Star                                                  │
│ Local-first memory layer for AI agents                      │
│                                                             │
│ Current Stage                                               │
│ v0.1 MVP: ChatGPT export → memory graph → MCP search        │
│                                                             │
│ Active Decisions                                            │
│ ✓ Use deterministic parser for raw exports                  │
│ ✓ Use LLM only for semantic extraction                      │
│ ✓ Expose memory through MCP                                 │
│ ✓ Use Skills for memory workflows                           │
│ ✓ Draft-first memory write                                  │
│                                                             │
│ Open Questions                                              │
│ ? SQLite-first or Postgres-first?                           │
│ ? Desktop shell: Tauri or Electron?                         │
│ ? How much auto-commit is safe?                             │
│                                                             │
│ Next Actions                                                │
│ → Implement ChatGPT parser                                  │
│ → Create MCP server scaffold                                │
│ → Add memory.search                                         │
└─────────────────────────────────────────────────────────────┘
이 화면은 agent도 써야 해.
즉, Project Memory는 UI인 동시에 MCP resource가 돼야 해.

memory://projects/memoryos/state
9. 화면 5 — Hypergraph Explorer
이게 Visual의 핵심.

목적
단순 graph가 아니라 사고 사건을 보여준다.

일반 노드 그래프:

MCP ─ Skill ─ Harness
이걸 넘어서:

[DecisionEvent: MemoryOS architecture split]
members:
- MCP as tool interface
- Skill as workflow policy
- Harness as orchestrator
- Hypergraph as memory substrate
시각화 방식
Hyperedge를 그냥 선으로 표현하면 복잡해져.
추천 방식은 Hyperedge Card + Graph Canvas 조합.

왼쪽: graph canvas
오른쪽: selected hyperedge detail
아래: timeline
Visual representation
Concept nodes = 작은 원
Project nodes = 둥근 사각형
Decision nodes = 다이아몬드
Action nodes = 체크 아이콘
Question nodes = 물음표
Hyperedge = 반투명 blob / group boundary / event card
예시
┌─────────────────────────────────────────────────────────────┐
│ Hypergraph Explorer                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│      MCP ●─────╮                                            │
│                │                                            │
│   Skill ●──────┼── [DecisionEvent] Architecture Split       │
│                │                                            │
│ Harness ●──────╯                                            │
│        ╲                                                    │
│         ╲                                                   │
│      Memory Graph ●──── [IdeaComposition] Agent Memory OS   │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ Selected Hyperedge                                          │
│ Type: DecisionEvent                                         │
│ Label: MemoryOS architecture split                          │
│ Summary: MCP는 tool interface, Skill은 workflow policy...   │
│ Confidence: 0.93                                            │
│ Status: active                                              │
│ Members: MCP, Skill, Harness, Memory Graph                  │
└─────────────────────────────────────────────────────────────┘
필터
- Project
- Type
  - DecisionEvent
  - IdeaComposition
  - ConceptCluster
  - ActionDerivation
  - ContradictionSet
- Origin
- Status
- Time range
10. 화면 6 — Draft Review
이 화면이 진짜 중요해.
Memory 품질을 결정하는 곳이야.

목적
LLM/agent가 추출한 memory draft를 사용자가 승인/수정/거절한다.

UI
┌─────────────────────────────────────────────────────────────┐
│ Draft Review                                                │
├─────────────────────────────────────────────────────────────┤
│ 36 pending memory drafts                                    │
│                                                             │
│ [Decision]                                                  │
│ MemoryOS should expose memory through MCP.                  │
│                                                             │
│ origin: mixed                                               │
│ project: MemoryOS                                           │
│ confidence: 0.94                                            │
│ raw refs: 3 messages                                        │
│                                                             │
│ [Accept] [Edit] [Reject] [Mark as Idea]                     │
│                                                             │
│ ─────────────────────────────────────────────────────────── │
│                                                             │
│ [Action]                                                    │
│ Implement ChatGPT export parser first.                      │
│                                                             │
│ [Accept] [Edit] [Reject]                                   │
└─────────────────────────────────────────────────────────────┘
필수 기능
- Accept
- Edit
- Reject
- Change type
- Change origin
- Change project
- Link to existing memory
- Mark as duplicate
- Mark as supersedes old memory
이게 없으면 memory graph는 금방 오염돼.

11. 화면 7 — Agent Harness
목적
Claude, Codex, local LLM, custom agents가 어떻게 연결되어 있고, 무엇을 할 수 있는지 보여준다.

구성
Agents
- Claude
- Codex
- Local LLM
- Research Agent
- Extraction Worker

Tools / MCP
- memory.search
- hypergraph.search
- project.get_state
- ingestion.import_file
- memory.extract_drafts

Capabilities
- architecture
- implementation
- extraction
- search
- review

Recent Runs
- 어떤 agent가 어떤 작업을 했는가
- 어떤 memory를 참조했는가
- 어떤 draft를 만들었는가
예시
┌─────────────────────────────────────────────────────────────┐
│ Agent Harness                                               │
├─────────────────────────────────────────────────────────────┤
│ Agents                                                      │
│                                                             │
│ Claude        Architect / Reviewer        Connected ●       │
│ Codex         Implementation Agent        Connected ●       │
│ Local LLM     Extraction Worker           Running ●         │
│                                                             │
│ MCP Tools                                                   │
│ ✓ project.get_state                                         │
│ ✓ memory.search                                             │
│ ✓ hypergraph.search                                         │
│ ✓ ingestion.import_file                                     │
│ ✓ memory.extract_drafts                                     │
│                                                             │
│ Recent Agent Runs                                           │
│ Codex  → implemented parser scaffold     12 memories used   │
│ Claude → reviewed architecture           8 memories used    │
│ Local  → extracted 41 memory drafts       3 rejected         │
└─────────────────────────────────────────────────────────────┘
12. Visual System 상세
Layout
Desktop은 좌측 sidebar + 중앙 workspace + 우측 inspector 구조가 좋아.

┌────────────┬─────────────────────────────┬──────────────┐
│ Sidebar    │ Main Workspace              │ Inspector    │
│            │                             │              │
│ Home       │ Graph / Ask / Project       │ Details      │
│ Import     │                             │ Evidence     │
│ Ask        │                             │ Raw refs     │
│ Projects   │                             │ Actions      │
│ Graph      │                             │              │
│ Drafts     │                             │              │
│ Agents     │                             │              │
└────────────┴─────────────────────────────┴──────────────┘
Typography
Title: clean sans, medium weight
Body: readable, not too small
Code/IDs: mono font
Labels: compact uppercase optional
Component tone
Cards:
- rounded-xl or 2xl
- low contrast border
- subtle shadow
- transparent dark surface

Graph:
- no heavy 3D
- smooth transitions
- zoom/pan
- hover detail
- selected node glow

Buttons:
- primary actions clear
- destructive actions muted red
- approve/edit/reject distinct
Color semantics
Message = blue
Memory = violet
Decision = amber
Action = green
Question = cyan
Conflict = red/orange
Project = white/neutral
Agent = purple
Tool/MCP = teal
중요한 건 과도한 색보다 의미가 반복적으로 유지되는 것.

13. Animation / Interaction
좋은 Desktop은 정적 대시보드가 아니라 “기억이 처리되는 느낌”이 있어야 해.

Import animation
File drop
→ source detected
→ conversations expanding
→ messages forming
→ pairs linking
→ memories extracted
→ hyperedges forming
Graph animation
새 memory가 commit되면
관련 project node 근처에 작은 pulse
hyperedge boundary가 부드럽게 생김
Agent run animation
User task
→ memory retrieval
→ context pack
→ agent handoff
→ result
→ memory draft
이걸 너무 화려하게 하지 말고, calm technical motion으로.

14. Desktop 기술 선택
추천
Tauri + React + TypeScript
이유:

- local-first desktop에 적합
- 앱이 가벼움
- Rust backend와 연결 가능
- 파일 시스템 접근/로컬 서버 구동에 좋음
하지만 빠르게 만들려면:

Electron + Next.js
도 괜찮아.

현실적인 선택
너가 빠르게 agent에게 시킬 거면:

V0 Desktop:
Electron + Vite React + local API

V1:
Tauri로 경량화 고려
혹은 처음부터 Tauri 가도 됨.

15. Desktop 내부 구조
apps/desktop/
├── src/
│   ├── app/
│   ├── routes/
│   │   ├── Home.tsx
│   │   ├── ImportCenter.tsx
│   │   ├── AskMemory.tsx
│   │   ├── ProjectMemory.tsx
│   │   ├── HypergraphExplorer.tsx
│   │   ├── DraftReview.tsx
│   │   ├── AgentHarness.tsx
│   │   └── Settings.tsx
│   ├── components/
│   │   ├── graph/
│   │   ├── cards/
│   │   ├── timeline/
│   │   ├── command-palette/
│   │   └── inspector/
│   ├── lib/
│   │   ├── api.ts
│   │   ├── graph-layout.ts
│   │   └── theme.ts
│   └── styles/
Graph library 후보
React Flow
Cytoscape.js
Sigma.js
D3 force graph
추천:

초기: React Flow
고급 graph: Sigma.js or Cytoscape.js
React Flow는 node/edge UI를 빠르게 만들기 좋고, hyperedge를 custom node/card로 표현하기 쉽다.

16. Desktop v0.1 Scope
Desktop까지 한 번에 가더라도 v0.1은 이렇게 자르자.

Desktop v0.1에 넣을 것
1. Home
2. Import Center
3. Ask Memory
4. Draft Review
5. Simple Project Memory
6. MCP Status
Desktop v0.1에서 미룰 것
1. 고급 hypergraph visualization
2. agent capability probing UI
3. timeline animation
4. full desktop notification
5. live browser capture
6. multi-device sync
즉 첫 Desktop은 이렇게만 증명하면 돼.

export 업로드
→ processing 상태 확인
→ memory draft 승인
→ memory에 질문
→ MCP 연결 상태 확인
17. 화면별 우선순위
개발 순서:

1. Import Center
2. Draft Review
3. Ask Memory
4. Home
5. Project Memory
6. Agent Harness
7. Hypergraph Explorer
왜냐하면:

Import Center 없으면 데이터가 없음
Draft Review 없으면 memory 품질이 망가짐
Ask Memory 없으면 가치가 안 보임
Home은 그 다음
Graph Explorer는 가장 멋있지만 가장 나중
18. Visual Prototype Prompt
Agent나 image generator에게 줄 수 있는 visual prompt.

Design a desktop app called MemoryOS.

It is a local-first memory cockpit for AI agents. The app imports ChatGPT/Claude/Gemini conversation exports, extracts memories, builds a hypergraph memory system, and exposes it to agents through MCP.

Visual style:
- calm dark interface
- warm charcoal background
- subtle grid
- translucent rounded panels
- soft violet, cyan, amber, and green accents
- graph nodes with gentle glow
- technical but elegant
- not cyberpunk, not flashy
- more like a private cognitive cockpit

Main layout:
- left sidebar navigation
- central workspace
- right inspector panel

Screens:
1. Home dashboard with memory graph preview, active projects, recent decisions, pending drafts
2. Import Center with drag-and-drop AI export upload and processing pipeline
3. Ask Memory with answer, evidence memories, and hyperedge references
4. Project Memory page showing north star, active decisions, open questions, next actions
5. Draft Review page with extracted memory cards and Accept/Edit/Reject controls
6. Agent Harness page showing Claude, Codex, local LLM, MCP tools, and recent runs
7. Hypergraph Explorer showing concept nodes grouped by hyperedge events

The UI should feel like a local AI memory operating system, not a generic note app.
19. Desktop Agent 작업 지시서
Claude/Codex한테 줄 프롬프트는 이거.

We are extending MemoryOS into a desktop app.

Goal:
Build a local-first desktop UI for MemoryOS, a personal memory layer for AI agents.

The desktop app should visualize and operate:
- AI conversation imports
- memory extraction pipeline
- memory drafts
- project states
- hypergraph memories
- MCP/agent connections

Use this information architecture:
1. Home / Memory Cockpit
2. Import Center
3. Ask Memory
4. Project Memory
5. Draft Review
6. Agent Harness
7. Hypergraph Explorer
