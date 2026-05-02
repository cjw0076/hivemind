<!--
Source: docs/memoryOS.md
Source lines: 1401-2100
Source byte range: 42384-60039
Split title source: numbered-section
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 003: 3. LLM/agent가 잘 쓰는 memory 단위

Provenance: `docs/memoryOS.md` lines `1401-2100`, bytes `42384-60039`.

Local structure markers:

- Source line 1401: 3. LLM/agent가 잘 쓰는 memory 단위
- Source line 1445: 4. Memory object schema
- Source line 1486: 5. Graph schema
- Source line 1535: 6. Agent가 memory를 “잘” 쓰는 조건
- Source line 1540: 1. Intent routing
- Source line 1541: 2. Candidate retrieval
- Source line 1542: 3. Evidence reranking
- Source line 1543: 4. Context packing
- Source line 1649: 1. Uri는 단순 데이팅 앱이 아니라 ESN으로 포지셔닝.
- Source line 1650: 2. mobile app과 web app의 주 기능은 달라야 함.
- Source line 1651: 3. offline activity와 online graph를 통합해야 함.
- Source line 1654: 1. 왜 대학생들이 매일 써야 하는가?

---

3. LLM/agent가 잘 쓰는 memory 단위
가장 중요한 설계 포인트는 memory unit이야.

그냥 메시지 단위로 넣으면 너무 작고, 대화 전체로 넣으면 너무 커.
그래서 여러 granularities를 동시에 가져가야 해.

Message
- 단일 user/assistant 발화

Pair
- user input + assistant output

Segment
- 하나의 주제 흐름

Episode
- 하나의 목적을 가진 대화 단위

Project Memory
- 프로젝트별 요약/결정/문제/행동

Concept Memory
- 특정 개념의 누적 정의와 변화

User Profile Memory
- 사용자의 선호, 목표, 반복 패턴
추천 hierarchy는 이거야.

Conversation
  └── Episode
        └── Segment
              └── Pair
                    ├── User Message
                    └── Assistant Message
각 계층마다 embedding을 따로 둬야 해.

message_embedding
pair_embedding
segment_embedding
episode_embedding
project_embedding
concept_embedding
LLM은 질문 종류에 따라 다른 단위를 써야 해.

4. Memory object schema
모든 memory는 이런 공통 schema를 가져야 해.

{
  "memory_id": "mem_123",
  "type": "decision | idea | question | fact | preference | action | artifact | reflection",
  "source": "chatgpt | claude | gemini | perplexity | manual | file | meeting",
  "content": "사용자가 Uri를 단순 데이팅 앱이 아니라 ESN으로 정의했다.",
  "raw_refs": ["message_001", "message_002"],
  "project": ["Uri"],
  "concepts": ["ESN", "digital campus", "emotional twin"],
  "actors": ["user", "assistant"],
  "timestamp": "2026-04-30T17:00:00+09:00",
  "confidence": 0.86,
  "importance": 0.92,
  "stability": "long_term",
  "status": "active | superseded | rejected | uncertain",
  "privacy_level": "private | sensitive | shareable",
  "embedding_id": "emb_123"
}
이 schema에서 중요한 필드는 이거야.

type
- 이 memory가 사실인지, 아이디어인지, 결정인지, 질문인지 구분

confidence
- 추출 확신도

importance
- 나중에 꺼내 쓸 가치

status
- 아직 유효한지, 폐기됐는지, 바뀌었는지

raw_refs
- 원문 근거

privacy_level
- agent가 외부로 말해도 되는지
LLM이 잘 쓰려면 memory에 근거, 신뢰도, 현재성이 있어야 해.

5. Graph schema
Graph DB에서는 단순히 message를 연결하지 말고, “생각의 구조”를 저장해야 해.

추천 node:

(:User)
(:Conversation)
(:Message)
(:Memory)
(:Project)
(:Concept)
(:Decision)
(:Question)
(:Action)
(:Artifact)
(:Agent)
(:Source)
(:TimePeriod)
추천 관계:

(:Conversation)-[:HAS_MESSAGE]->(:Message)
(:Message)-[:GENERATED_MEMORY]->(:Memory)

(:Memory)-[:ABOUT_PROJECT]->(:Project)
(:Memory)-[:MENTIONS_CONCEPT]->(:Concept)
(:Memory)-[:SUPPORTS]->(:Decision)
(:Memory)-[:CONTRADICTS]->(:Memory)
(:Memory)-[:SUPERSEDES]->(:Memory)

(:Project)-[:HAS_OPEN_QUESTION]->(:Question)
(:Project)-[:HAS_DECISION]->(:Decision)
(:Project)-[:HAS_ACTION]->(:Action)
(:Project)-[:HAS_ARTIFACT]->(:Artifact)

(:Concept)-[:RELATED_TO]->(:Concept)
(:Concept)-[:USED_IN]->(:Project)

(:Decision)-[:BASED_ON]->(:Memory)
(:Action)-[:DERIVED_FROM]->(:Decision)
이렇게 하면 agent가 단순히 “비슷한 문장”이 아니라, 이런 식으로 탐색할 수 있어.

Uri 프로젝트
→ 아직 active 상태인 open question
→ 관련된 과거 decision
→ 그 decision의 근거 memory
→ 최근에 contradict된 memory
→ 다음 action
이게 진짜 memory graph야.

6. Agent가 memory를 “잘” 쓰는 조건
LLM이 잘 쓰려면 retrieval을 그냥 similarity search로 하면 안 돼.

좋은 retrieval은 최소 4단계야.

1. Intent routing
2. Candidate retrieval
3. Evidence reranking
4. Context packing
6.1 Intent routing
먼저 사용자의 현재 요청을 분류해야 해.

사용자 요청:
“이 사업 방향 어떻게 잡아야 하지?”
agent는 먼저 이걸 판단해야 해.

{
  "intent": "strategic_planning",
  "project": "Uri",
  "needs": [
    "past_decisions",
    "open_questions",
    "business_model",
    "user_preferences",
    "recent_context"
  ]
}
요청 유형에 따라 조회하는 memory가 달라져야 해.

질문 답변
→ semantic chunks

프로젝트 의사결정
→ decisions + open questions + constraints

글쓰기
→ tone preferences + prior drafts + target project

실행 계획
→ current state + action items + blockers

자기 회고
→ temporal memory + repeated patterns
6.2 Candidate retrieval
그 다음 여러 저장소에서 후보를 가져와.

Vector search:
- 의미적으로 비슷한 memory

Graph traversal:
- 같은 프로젝트/개념/결정과 연결된 memory

Keyword/BM25:
- 정확한 이름, 파일명, 고유명사

Recency search:
- 최근 대화

State search:
- 현재 active decision/open action
즉, retrieval은 이렇게 합쳐야 해.

retrieval_candidates =
  vector_results
+ graph_neighbors
+ keyword_matches
+ recent_context
+ active_project_state
6.3 Reranking
후보가 100개 나와도 LLM에게 전부 넣으면 안 돼.
점수를 다시 매겨야 해.

추천 scoring:

score =
  semantic_similarity * 0.35
+ graph_relevance * 0.25
+ importance * 0.15
+ recency * 0.10
+ confidence * 0.10
+ user_confirmed * 0.05
하지만 요청에 따라 가중치를 바꿔야 해.

예:

“최근에 내가 뭐라고 했지?”
→ recency ↑

“내 오래된 north star 찾아줘”
→ importance ↑, semantic ↑

“현재 결정된 것만 보여줘”
→ status=active, type=decision 필터

“내가 직접 말한 것만”
→ actor=user 필터
6.4 Context packing
마지막으로 agent에게 넣을 context를 구성한다.

여기서 중요한 건 원문 chunk를 그냥 붙이지 않는 것.
agent가 쓰기 좋게 압축해야 해.

예:

[User Profile]
- 사용자는 over-abstraction에 빠지는 경향을 경계한다.
- 실행 중심의 답변을 선호한다.

[Current Project: Uri]
- 정의: 대학 기반 ESN, digital campus + agent avatar.
- 핵심 목표: 사람들의 offline/online 관계 데이터를 자연스럽게 자산화.
- 최근 고민: 사용자가 귀찮음을 느끼지 않게 하는 경험 설계.

[Relevant Decisions]
1. Uri는 단순 데이팅 앱이 아니라 ESN으로 포지셔닝.
2. mobile app과 web app의 주 기능은 달라야 함.
3. offline activity와 online graph를 통합해야 함.

[Open Questions]
1. 왜 대학생들이 매일 써야 하는가?
2. 어떤 보상이 충분히 자연스러운가?
3. human resource assetization을 어떻게 정당화할 것인가?

[Evidence]
- message_123
- conversation_45
이런 식의 context pack이 있어야 LLM이 잘 써.

7. “Operational State”가 제일 중요함
대부분 memory 시스템은 과거를 저장하는 데서 끝나.
하지만 agent가 잘 쓰려면 현재 상태를 따로 유지해야 해.

예를 들어 Uri 프로젝트 state:

{
  "project": "Uri",
  "current_stage": "MVP built, experience design refinement",
  "north_star": "campus emotional/social graph as ESN",
  "active_goals": [
    "pilot test 모집",
    "mobile app page 구성",
    "offline-online integration 설계"
  ],
  "active_constraints": [
    "사용자가 귀찮음을 느끼면 안 됨",
    "보상은 자연스러워야 함",
    "초기에는 대학생 경험에 집중"
  ],
  "open_questions": [
    "왜 매일 써야 하는가?",
    "어떤 데이터 제공을 사용자가 납득하는가?"
  ],
  "recent_decisions": [
    "web과 mobile의 성격은 다르게 가져간다",
    "Uri는 포트폴리오가 될 수 있다"
  ]
}
Agent는 매번 전체 memory를 뒤지기보다, 우선 이 state를 읽어야 해.

현재 상태
→ 관련 memory retrieval
→ 답변/계획
→ 새 decision/action 추출
→ state 업데이트
이게 진짜 agentic loop야.

8. Memory lifecycle
Memory는 한 번 저장하면 끝이 아니야.
상태가 변해야 해.

created
→ extracted
→ validated
→ active
→ used
→ reinforced
→ updated
→ superseded
→ archived
예를 들어 예전에는:

“Uri는 데이팅 앱에 가깝다”
나중에는:

“Uri는 단순 데이팅 앱이 아니라 ESN이다”
그러면 이전 memory를 삭제하지 말고:

(old memory)-[:SUPERSEDED_BY]->(new memory)
로 연결해야 해.

그래야 agent가 낡은 결정을 현재 결정처럼 말하지 않아.

9. Agent memory tools 설계
LLM/agent가 memory를 잘 쓰려면 내부 tool이 필요해.

예:

search_memory(query, filters)
get_project_state(project_id)
get_decisions(project_id, status="active")
get_open_questions(project_id)
get_concept_history(concept)
get_user_preferences()
write_memory(memory)
update_project_state(project_id, patch)
mark_superseded(old_id, new_id)
중요한 건 agent에게 vector_search()만 주면 안 된다는 거야.
그럼 agent가 모든 걸 유사도 검색으로 해결하려고 해.

더 좋은 tool interface는 의도 기반이어야 해.

get_relevant_context(task, project, constraints)
내부에서 알아서 vector + graph + state를 조회하게 만드는 게 좋다.

10. Agent가 답변할 때의 기본 프로토콜
Agent의 system prompt에 memory 사용 규칙을 넣어야 해.

1. 사용자의 현재 요청을 task type으로 분류한다.
2. 현재 프로젝트가 명확하면 project state를 먼저 조회한다.
3. 필요한 경우에만 long-term memory를 검색한다.
4. memory의 status, confidence, timestamp를 확인한다.
5. 오래된 memory와 최근 memory가 충돌하면 최근 active decision을 우선한다.
6. 불확실하면 “과거 기록상으로는”이라고 표시한다.
7. 답변 후 새로운 decision/action/preference가 생기면 memory update를 제안한다.
이 규칙이 없으면 agent는 기억을 무분별하게 끌어오거나, 낡은 정보를 현재 사실처럼 말하게 돼.

11. “잘 사용하는” agent loop
최종적으로 agent는 이렇게 움직여야 해.

User input
  ↓
Task understanding
  ↓
Memory plan
  ↓
Retrieve state
  ↓
Retrieve evidence
  ↓
Resolve conflicts
  ↓
Build context pack
  ↓
Generate answer/action
  ↓
Extract new memories
  ↓
Update graph/state
예:

사용자:
“Uri의 다음 기능 뭐 만들까?”

Agent:
1. project=Uri 인식
2. Uri state 조회
3. 최근 decision 조회
4. open question 조회
5. 과거 기능 아이디어 조회
6. 현재 MVP 상태와 충돌 없는 기능 후보 생성
7. “오늘 만들 1개”로 압축
8. 새 action item 저장
이렇게 해야 너에게 필요한 “실행형 비서”가 돼.

12. 시스템적으로 중요한 7가지
1. Memory type 분리
모든 memory를 같은 벡터로 보지 마.

Fact
Decision
Preference
Idea
Question
Action
Artifact
Reflection
이건 반드시 구분해야 해.

2. User-origin vs AI-origin 분리
너한테 특히 중요해.

사용자가 직접 말한 아이디어
AI가 제안한 아이디어
사용자가 수용한 아이디어
사용자가 거부한 아이디어
아직 검증 안 된 아이디어
이걸 안 나누면 나중에 “내 생각”과 “AI가 준 말”이 섞여.

3. Currentness 관리
memory에는 현재성이 있어야 해.

active
stale
superseded
rejected
uncertain
Agent는 active memory를 우선해야 해.

4. Evidence link
모든 요약 memory는 원문으로 돌아갈 수 있어야 해.

memory.summary
→ raw_refs
→ original message
그래야 hallucination을 줄일 수 있어.

5. Importance score
모든 대화를 동일하게 저장하면 noise가 너무 많아.

중요한 결정
반복되는 문제의식
사용자의 장기 목표
프로젝트 방향성
명시적 선호
이런 건 high importance.

반면:

일회성 번역
단순 문구 수정
짧은 잡담
이런 건 low importance.

6. Compression
memory는 계속 압축되어야 해.

100 messages
→ 10 segment summaries
→ 3 project memories
→ 1 current state update
무한히 원문만 쌓으면 agent가 못 써.

7. Reflection job
주기적으로 background reflection이 필요해.

예:

매일:
- 오늘 생긴 decision/action 추출

매주:
- 프로젝트별 변화 요약
- 반복 질문/회피 패턴 탐지

매월:
- north star 변화
- 장기 goal 업데이트
이건 agent가 기억을 정리하는 수면 같은 역할이야.

13. Personal Thought Encoder는 어디에 들어가나
네가 말한 MLP는 여기 들어간다.

raw text
→ base embedding
→ personal projection MLP
→ personal latent vector
→ vector DB / graph node
하지만 이건 memory system의 일부일 뿐이야.

Memory System
  ├── raw storage
  ├── normalized DB
  ├── vector DB
  ├── graph DB
  ├── state store
  ├── retrieval orchestrator
  └── personal encoder
MLP의 역할은:

일반 의미공간
→ 너의 사고공간
예:

“언어의 종말”
“역통역”
“ontology”
“hypergraph”
“agent 자기인식 루프”
이걸 일반 embedding은 따로 볼 수 있지만, personal encoder는 같은 문제의식 축으로 모아야 해.

다만 MVP에서는 이렇게 가야 해.

V0: base embedding
V1: LLM tagging + graph
V2: user feedback 기반 reranking
V3: personal MLP projection
V4: graph-aware encoder
처음부터 MLP로 해결하려고 하면 product가 아니라 research가 돼.

14. MVP 시스템 설계
처음 시스템은 이렇게 충분해.

Frontend:
- Upload
- Search
- Project Memory
- Graph View
- Ask My Memory

Backend:
- Parser worker
- Embedding worker
- Memory extractor
- Retrieval orchestrator
- Context builder

DB:
- Postgres + pgvector
- optional Neo4j later
초기에는 Neo4j 없이도 가능해.

Postgres 테이블:

conversations
messages
pairs
chunks
memories
concepts
projects
decisions
actions
memory_links
embeddings
project_states
memory_links로 graph를 흉내낼 수 있어.

memory_links
- source_memory_id
- relation_type
- target_memory_id
- confidence
나중에 graph가 커지면 Neo4j로 이전.

15. Agent-readable Context Pack 예시
LLM에게 최종적으로 넣는 건 이런 구조여야 해.

{
  "task": {
    "type": "strategic_planning",
    "user_request": "Uri의 다음 기능 뭐 만들까?"
  },
  "user_profile": {
    "long_term_goal": "세상을 바꾸는 영향력 있는 사람 되기",
    "working_pattern": [
      "over-abstraction tendency",
      "needs execution bias"
    ]
  },
  "project_state": {
    "project": "Uri",
    "stage": "MVP built, experience design refinement",
    "north_star": "campus ESN / digital emotional twin",
    "constraints": [
      "사용자가 귀찮음을 느끼면 안 됨",
      "offline-online integration 필요",
      "대학생만의 경험이어야 함"
    ]
  },
  "relevant_memories": [
    {
      "type": "decision",
      "content": "Uri는 단순 데이팅 앱이 아니라 ESN으로 포지셔닝한다.",
      "confidence": 0.94,
      "status": "active"
    },
    {
      "type": "open_question",
      "content": "대학생들이 왜 매일 써야 하는가에 답해야 한다.",
      "confidence": 0.91,
      "status": "active"
    }
  ],
  "output_policy": {
    "prefer": "concrete next action",
    "avoid": "overly abstract roadmap"
  }
}
이렇게 넣으면 LLM이 훨씬 안정적으로 답해.

16. 좋은 memory system의 기준
네가 만든 시스템이 좋은지 확인하는 기준은 이거야.

1. 관련 있는 과거 대화를 잘 찾는가?
2. 낡은 결정을 현재 결정으로 착각하지 않는가?
3. 사용자의 말과 AI의 말을 구분하는가?
4. 프로젝트별 현재 상태를 유지하는가?
5. 답변 후 새 decision/action을 갱신하는가?
6. 근거 원문으로 돌아갈 수 있는가?
7. 사용자의 반복 패턴을 장기적으로 인식하는가?
8. 검색 결과가 단순 키워드가 아니라 문제의식 단위로 모이는가?
특히 너한테 제일 중요한 테스트는 이거야.

“내가 언어의 비효율성에 대해 말한 모든 흐름을 찾아줘.”
좋은 시스템이면 단순히 “언어”라는 단어가 들어간 대화만 찾는 게 아니라:

Goen 역통역
ontology
hypergraph
LLM tokenization
softmax
closed loop
의식 루프
HCI
언어 이후 인터페이스
이걸 한 덩어리로 끌어와야 해.

17. 최종 구조: Memory OS
결국 이건 이렇게 가야 해.

Memory OS
├── Ingestion
│   ├── ChatGPT export
│   ├── Gemini Takeout
│   ├── Claude export
│   ├── Perplexity threads
│   ├── Notes
│   └── Files
│
├── Normalization
│   ├── Message ledger
│   ├── Pair builder
│   ├── Chunker
│   └── Metadata extractor
│
├── Understanding
│   ├── Concept extraction
│   ├── Project linking
│   ├── Decision detection
│   ├── Action extraction
│   └── Importance scoring
│
├── Storage
│   ├── Raw archive
│   ├── Relational DB
│   ├── Vector DB
│   ├── Graph DB
│   └── State store
│
├── Retrieval
│   ├── Intent router
│   ├── Hybrid search
│   ├── Graph traversal
│   ├── Reranker
│   └── Context packer
│
├── Agent Interface
│   ├── ask_memory
│   ├── get_project_state
│   ├── get_decisions
│   ├── update_memory
│   └── reflect
│
└── Reflection Loop
    ├── daily summary
    ├── weekly pattern extraction
    ├── project state update
    └── personal encoder training
18. 지금 바로 만들 최소 버전
너의 실행 편향을 위해, 지금은 이렇게만 잡아.

1. ChatGPT export parser
2. conversations/messages/pairs 저장
3. chunks 생성
4. embedding 저장
5. memory extractor 실행
