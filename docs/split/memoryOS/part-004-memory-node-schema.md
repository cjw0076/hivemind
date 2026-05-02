<!--
Source: docs/memoryOS.md
Source lines: 2101-2800
Source byte range: 60040-78652
Split title source: first-text
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 004: - idea

Provenance: `docs/memoryOS.md` lines `2101-2800`, bytes `60040-78652`.

Local structure markers:

- Source line 2106: 6. project_state 테이블 생성
- Source line 2107: 7. ask_memory API 생성
- Source line 2108: 8. retrieval orchestrator 구현
- Source line 2136: 19. 한 문장으로 정리
- Source line 2177: 1. 일반 그래프 vs 하이퍼그래프
- Source line 2206: 2. 왜 하이퍼그래프가 필요한가
- Source line 2247: 3. 핵심 모델: Node와 Hyperedge를 분리
- Source line 2295: 4. AI 대화에서 하이퍼엣지 단위
- Source line 2298: 1. Turn Hyperedge
- Source line 2313: 2. Episode Hyperedge
- Source line 2329: 3. Decision Hyperedge
- Source line 2355: 4. Concept Cluster Hyperedge

---

   - idea
   - decision
   - question
   - action
   - preference
6. project_state 테이블 생성
7. ask_memory API 생성
8. retrieval orchestrator 구현
초기 ask_memory는 이렇게 동작하면 돼.

def ask_memory(user_query):
    task = classify_task(user_query)
    project = detect_project(user_query)

    state = get_project_state(project) if project else None

    vector_hits = vector_search(user_query)
    graph_hits = graph_expand(vector_hits)
    recent_hits = get_recent_context(project)

    candidates = merge(vector_hits, graph_hits, recent_hits, state)
    ranked = rerank(candidates, task)

    context_pack = build_context_pack(
        task=task,
        project_state=state,
        memories=ranked[:12]
    )

    answer = llm_generate(user_query, context_pack)

    new_memories = extract_new_memories(user_query, answer)
    save_new_memories(new_memories)

    return answer
19. 한 문장으로 정리
LLM/agent가 잘 쓰는 memory graph는 “전부 임베딩한 저장소”가 아니라, memory type·current state·evidence·graph relation·retrieval policy·reflection loop가 있는 cognition infrastructure다.

너는 이걸 이렇게 보면 돼.

대화 데이터
→ 기억
→ 상태
→ 판단
→ 행동
→ 다시 기억
이 루프가 닫히면 단순 검색 서비스가 아니라, 진짜 개인 agentic operating system이 된다.


1대1이 아니라 1대다 즉 하이퍼그래프는?

좋아, 여기서 하이퍼그래프가 딱 필요해져. 1:1 edge로 억지로 풀면 “한 번의 대화가 여러 개념·결정·프로젝트·행동을 동시에 묶었다”는 사건성이 사라지거든.

6s 동안 생각함
맞아. 1:1 graph보다 하이퍼그래프가 훨씬 잘 맞아.

왜냐하면 AI 대화/사고 데이터는 대부분 이런 구조이기 때문이야.

하나의 발화
→ 여러 개념을 동시에 포함
→ 여러 프로젝트에 걸침
→ 하나의 결정/행동/질문으로 이어짐
→ 과거 여러 대화의 합성 결과로 등장
일반 그래프는 이것을 억지로 쪼개서 표현해.

Message A ─ Concept 1
Message A ─ Concept 2
Message A ─ Project Uri
Message A ─ Decision X
그런데 실제 의미는 이게 아니야.

Message A 안에서
{Concept 1, Concept 2, Project Uri, Decision X, User Intent}가
하나의 의미 사건으로 동시에 결합했다.
이걸 표현하는 게 하이퍼엣지야.

1. 일반 그래프 vs 하이퍼그래프
일반 그래프:

A ─ B
B ─ C
C ─ D
관계가 항상 1:1이야.

하이퍼그래프:

E1 = {A, B, C, D}
하나의 관계가 여러 노드를 동시에 묶어.

AI memory에서는 이런 식이야.

Hyperedge_001 =
{
  UserMessage_123,
  AssistantMessage_124,
  Concept: ontology,
  Concept: hypergraph,
  Project: PersonalMemoryOS,
  Intent: system_design,
  Decision: use_hypergraph_model
}
즉, “이 대화 턴은 ontology, hypergraph, Personal Memory OS, system design 의도, 특정 결정이 동시에 결합된 사건이다”라고 저장하는 것.

이게 훨씬 정확해.

2. 왜 하이퍼그래프가 필요한가
너의 경우 memory가 단순 문서 검색이 아니야.

너는 이런 걸 하고 싶어 해.

내 생각이 어떻게 여러 프로젝트에 걸쳐 반복되는가?
어떤 개념들이 항상 같이 등장하는가?
내 질문 하나가 어떤 결정과 행동으로 이어졌는가?
GPT, Claude, Gemini가 각각 같은 문제의식에 어떻게 다르게 반응했는가?
내가 만든 아이디어와 AI가 제안한 아이디어가 어디서 합쳐졌는가?
이건 1:1 edge로는 약해.

예를 들어 너의 최근 흐름을 보면:

AI 대화 export
→ input-output pair
→ graph DB
→ embedding
→ MLP
→ service
→ agent-readable memory
→ hypergraph
이건 각각 따로따로 연결된 게 아니라, 하나의 큰 문제의식이 여러 개념을 동시에 끌고 가는 흐름이야.

하이퍼그래프로는 이렇게 표현할 수 있어.

Hyperedge: "AI memory system design episode"

nodes:
- Conversation: AI session extraction
- Concept: input-output pair
- Concept: embedding
- Concept: personal MLP encoder
- Concept: graph DB
- Concept: agent memory
- Concept: hypergraph
- Project: Personal AI Memory Graph
- Intention: systematize cognition
- Decision: use hypergraph rather than simple graph
이렇게 저장하면 나중에 agent가 “아, 이건 단순히 graph DB 얘기가 아니라 개인 cognition infrastructure 설계 흐름이구나”라고 이해할 수 있어.

3. 핵심 모델: Node와 Hyperedge를 분리
하이퍼그래프에서는 노드보다 하이퍼엣지 자체가 의미 단위가 된다.

Node
Message
Pair
Conversation
Project
Concept
Decision
Question
Action
Artifact
Person
Agent
Source
Time
Hyperedge
Episode
Claim
DecisionEvent
IdeaComposition
ConceptCluster
ProjectStateUpdate
ActionDerivation
ContradictionSet
ComparisonSet
예를 들어:

{
  "hyperedge_id": "he_001",
  "type": "IdeaComposition",
  "label": "Personal AI Memory Graph as cognition infrastructure",
  "nodes": [
    {"id": "msg_101", "role": "evidence"},
    {"id": "concept_embedding", "role": "method"},
    {"id": "concept_graphdb", "role": "storage"},
    {"id": "concept_agent", "role": "consumer"},
    {"id": "project_memory_os", "role": "project"},
    {"id": "decision_hypergraph", "role": "structural_choice"}
  ],
  "confidence": 0.91,
  "importance": 0.95,
  "timestamp": "2026-04-30T15:00:00+09:00"
}
여기서 중요한 건 단순히 노드 목록만 저장하는 게 아니라, 각 노드가 이 하이퍼엣지 안에서 어떤 역할을 했는지 저장하는 거야.

role = evidence | concept | project | decision | cause | result | constraint | artifact | actor
4. AI 대화에서 하이퍼엣지 단위
AI memory system에서 좋은 하이퍼엣지 타입은 이거야.

1. Turn Hyperedge
하나의 user-assistant pair를 묶음.

HE_Turn =
{
  user_message,
  assistant_message,
  detected_intent,
  concepts,
  project,
  source_model,
  timestamp
}
이건 가장 기본.

2. Episode Hyperedge
여러 turn이 하나의 주제 흐름을 만들 때.

HE_Episode =
{
  turn_1,
  turn_2,
  turn_3,
  topic,
  project,
  open_question,
  temporary_conclusion
}
예:

“AI 대화들을 graph DB에 저장하고 agent가 쓰는 memory system으로 만들기”
3. Decision Hyperedge
어떤 결정이 여러 근거에서 나왔을 때.

HE_Decision =
{
  decision,
  supporting_messages,
  rejected_alternatives,
  project,
  constraints,
  timestamp
}
예:

Decision:
"초기 MVP는 full auto-sync가 아니라 export upload 기반으로 시작한다."

nodes:
- privacy risk
- ToS risk
- ChatGPT export
- Gemini Takeout
- local-first MVP
- service feasibility
이건 1:1 graph보다 하이퍼그래프가 훨씬 자연스러워.

4. Concept Cluster Hyperedge
여러 개념이 하나의 문제의식으로 묶일 때.

HE_ConceptCluster =
{
  ontology,
  hypergraph,
  agent memory,
  MLP projection,
  personal latent space,
  cognition infrastructure
}
이걸 만들어두면 나중에 “내가 말한 진리 모델/Memory OS/agentic loop가 어떻게 연결되냐?” 같은 질문에 강해져.

5. Contradiction Hyperedge
서로 충돌하는 기억들을 묶음.

HE_Contradiction =
{
  old_memory: "Uri는 데이팅 앱에 가깝다",
  new_memory: "Uri는 ESN이다",
  reason,
  current_winner,
  timestamp
}
이것도 일반 그래프보다 하이퍼그래프가 좋다.
왜냐하면 충돌은 보통 두 문장만의 문제가 아니라, 맥락/시점/프로젝트 방향/사용자의 수용 여부가 같이 얽히기 때문.

6. Action Derivation Hyperedge
어떤 행동이 어떤 결정과 근거에서 나왔는지.

HE_Action =
{
  action: "ChatGPT export parser 구현",
  derived_from: "MVP는 export upload부터 시작",
  project: "Personal AI Memory Graph",
  constraints: ["local-first", "privacy", "fast MVP"],
  deadline,
  status
}
5. LLM/Agent가 하이퍼그래프를 잘 쓰는 방식
Agent가 memory를 쓸 때 일반 graph는 이렇게 탐색해.

현재 질문
→ 관련 message
→ 연결된 concept
→ 연결된 project
하이퍼그래프에서는 이렇게 탐색해야 해.

현재 질문
→ 관련 node 검색
→ 이 node가 포함된 hyperedge 찾기
→ hyperedge의 type/role/importance로 rerank
→ 같은 hyperedge 안의 다른 node들을 context로 가져오기
예를 들어 사용자가 묻는다.

“MLP는 여기서 어디에 들어가?”
일반 vector search면 MLP 들어간 문장을 찾는다.

하이퍼그래프 retrieval이면:

Node: MLP
→ 포함된 Hyperedge:
   - Personal Thought Encoder 설계
   - Memory OS service architecture
   - Agent-readable memory 구조
→ 관련 nodes:
   - base embedding
   - personal latent space
   - project classification
   - contrastive loss
   - vector DB
   - graph DB
→ 답변:
   MLP는 저장소가 아니라 personal projection layer다.
이게 훨씬 좋다.

6. 하이퍼그래프 retrieval 알고리즘
간단히 말하면:

def hyper_retrieve(query):
    query_embedding = embed(query)

    # 1. 노드 후보 검색
    node_hits = vector_search_nodes(query_embedding)

    # 2. 해당 노드들이 포함된 하이퍼엣지 검색
    hyperedges = find_hyperedges_containing(node_hits)

    # 3. 하이퍼엣지 점수 계산
    scored_hyperedges = score_hyperedges(
        hyperedges,
        query=query,
        node_hits=node_hits
    )

    # 4. 상위 하이퍼엣지의 이웃 노드 확장
    context_nodes = expand_nodes_from_hyperedges(scored_hyperedges[:k])

    # 5. context pack 구성
    return build_context_pack(scored_hyperedges, context_nodes)
점수는 이렇게 줄 수 있어.

hyperedge_score =
  max_node_similarity * 0.30
+ avg_node_similarity * 0.20
+ hyperedge_importance * 0.20
+ role_match_score * 0.15
+ recency_score * 0.05
+ confidence * 0.10
그리고 task에 따라 다르게.

의사결정 질문 → Decision Hyperedge 우선
개념 질문 → ConceptCluster Hyperedge 우선
실행 질문 → ActionDerivation Hyperedge 우선
회고 질문 → Episode/Trajectory Hyperedge 우선
7. 저장은 실제 DB에서 어떻게 하나?
현실적으로 대부분 DB는 native hypergraph를 직접 지원하지 않아도, 아래처럼 구현하면 돼.

Relational schema
nodes
- id
- type
- label
- content
- embedding_id
- created_at

hyperedges
- id
- type
- label
- summary
- importance
- confidence
- created_at
- status

hyperedge_members
- hyperedge_id
- node_id
- role
- weight
- order_index
핵심은 hyperedge_members야.

하이퍼엣지 하나가 여러 node를 가진다.
각 node는 role과 weight를 가진다.
예:

hyperedge_members

he_001 | msg_101 | evidence | 0.8
he_001 | concept_embedding | method | 0.9
he_001 | concept_hypergraph | structural_choice | 1.0
he_001 | project_memory_os | project | 1.0
he_001 | decision_use_hypergraph | decision | 0.95
이렇게 하면 Postgres만으로도 하이퍼그래프 가능해.

8. Neo4j에서 하이퍼그래프 흉내내기
Neo4j는 기본적으로 property graph라서 edge가 1:1이야.
하지만 하이퍼엣지를 노드로 승격하면 된다.

(:Message)-[:PARTICIPATES_IN {role:"evidence"}]->(:Hyperedge)
(:Concept)-[:PARTICIPATES_IN {role:"method"}]->(:Hyperedge)
(:Project)-[:PARTICIPATES_IN {role:"project"}]->(:Hyperedge)
(:Decision)-[:PARTICIPATES_IN {role:"result"}]->(:Hyperedge)
즉:

Message ─┐
Concept ─┼── Hyperedge: IdeaComposition
Project ─┤
Decision ┘
Cypher 예시:

CREATE (he:Hyperedge {
  id: "he_001",
  type: "IdeaComposition",
  label: "Personal AI Memory Graph architecture",
  importance: 0.95,
  confidence: 0.91
})

MATCH (m:Message {id:"msg_101"})
MATCH (c1:Concept {name:"embedding"})
MATCH (c2:Concept {name:"hypergraph"})
MATCH (p:Project {name:"Personal AI Memory Graph"})
MATCH (d:Decision {id:"decision_use_hypergraph"})

CREATE (m)-[:PARTICIPATES_IN {role:"evidence", weight:0.8}]->(he)
CREATE (c1)-[:PARTICIPATES_IN {role:"method", weight:0.9}]->(he)
CREATE (c2)-[:PARTICIPATES_IN {role:"structure", weight:1.0}]->(he)
CREATE (p)-[:PARTICIPATES_IN {role:"project", weight:1.0}]->(he)
CREATE (d)-[:PARTICIPATES_IN {role:"decision", weight:0.95}]->(he)
이게 실무적으로 제일 좋다.

9. Hyperedge 자체도 embedding해야 함
이게 중요해.

노드만 embedding하면 부족해.
하이퍼엣지 자체도 embedding해야 해.

왜냐하면 하이퍼엣지는 “관계 사건”이기 때문이야.

{
  "hyperedge_id": "he_001",
  "summary": "사용자는 AI 대화 데이터를 단순 저장하는 것이 아니라, embedding, graph DB, MLP projection, agent retrieval을 결합한 개인 Memory OS로 설계하고 있다.",
  "embedding": [...]
}
즉, embedding은 세 종류가 있어야 해.

node embedding
- 개별 메시지/개념/결정의 의미

hyperedge embedding
- 여러 노드가 결합된 사건의 의미

project/state embedding
- 누적된 현재 상태의 의미
Agent retrieval에서는 먼저 hyperedge embedding을 검색하는 것도 좋다.

query
→ hyperedge vector search
→ 해당 hyperedge 구성 node 가져오기
→ context pack 생성
이러면 “한 문장”이 아니라 “사고 묶음” 단위로 검색돼.

10. 하이퍼그래프 + MLP
네가 말한 personal MLP encoder는 하이퍼그래프와 더 잘 맞아.

기존:

message embedding → MLP → personal vector
더 좋은 구조:

node embedding
+ hyperedge context
+ role embedding
→ MLP/GNN/Hypergraph Neural Network
→ personal cognitive embedding
초기에는 복잡하게 가지 말고 이렇게.

hyperedge vector =
weighted_mean(member_node_vectors + role_embeddings)
예:

hyperedge_vector = mean([
    node_vector_i * member_weight_i + role_embedding_i
])
그다음 MLP:

personal_hyperedge_vector = MLP(hyperedge_vector)
나중에 고도화하면 Hypergraph Neural Network로 갈 수 있어.

Node → Hyperedge → Node message passing
흐름:

노드들이 하이퍼엣지로 정보 전달
하이퍼엣지가 다시 노드들에 정보 전달
이걸 하면 “ontology”라는 개념 노드가 단순 정의가 아니라, 어떤 프로젝트/결정/대화에서 쓰였는지까지 반영한 embedding을 갖게 돼.

11. 하이퍼그래프가 특히 강한 질문들
이 구조가 있으면 다음 질문들이 강해져.

“내 생각에서 항상 같이 등장하는 개념 묶음은?”
→ ConceptCluster Hyperedge 검색.

“Uri라는 프로젝트는 어떤 결정들의 조합으로 현재 상태가 됐어?”
→ Decision Hyperedge + ProjectState Hyperedge.

“내가 ‘언어의 비효율성’이라고 말할 때 실제로는 어떤 문제들을 같이 말하고 있었어?”
→ Concept hyperedge expansion.

“GPT와 Claude가 같은 아이디어를 어떻게 다르게 확장했어?”
→ Comparison Hyperedge.

“내가 한 결정 중 근거가 약한 건 뭐야?”
→ Decision Hyperedge 중 evidence weight 낮은 것.

“지금 실행할 수 있는 행동은 어떤 미해결 질문에서 파생됐어?”
→ Question → Decision → Action Hyperedge traversal.

12. 일반 그래프와 하이퍼그래프를 같이 써야 함
하이퍼그래프만 쓰면 또 무거워져.
정답은 hybrid야.

Property Graph:
- 빠른 1:1 관계
- message next
- belongs_to
- mentions
- created_by

Hypergraph:
- episode
- decision
- idea composition
- concept bundle
- contradiction
- action derivation
즉, 단순 관계는 일반 edge.

Message -[:NEXT]-> Message
Message -[:MENTIONS]-> Concept
Message -[:BELONGS_TO]-> Conversation
복합 사건은 Hyperedge.

Hyperedge: "Uri ESN positioning decision"
members:
- messages
- concepts
- project
- decision
- constraints
- rejected alternatives
13. 시스템 구조를 다시 쓰면
기존 Memory OS가 이거였다면:

Raw data
→ messages
→ embeddings
→ graph
→ retrieval
→ agent
하이퍼그래프 버전은 이렇게 돼.

Raw data
→ messages/pairs
→ atomic memory extraction
→ hyperedge construction
→ node embedding + hyperedge embedding
→ hybrid retrieval
→ context pack
→ agent reasoning
→ new hyperedge update
좀 더 구체적으로:

1. 대화 수집
2. message/pair 생성
3. LLM으로 atomic memory 추출
4. atomic memory들을 project/concept/decision/action으로 node화
5. 한 사건에 같이 등장한 것들을 hyperedge로 묶음
6. hyperedge summary 생성
7. hyperedge embedding 생성
8. node-hyperedge membership 저장
9. agent query 시 node + hyperedge 동시 retrieval
10. 답변 후 새 decision/action hyperedge 생성
14. 자동 하이퍼엣지 생성 방법
LLM extractor에게 이렇게 시키면 돼.

Given this conversation segment, extract:
1. atomic memories
2. concepts
3. projects
4. decisions
5. open questions
6. actions
7. construct hyperedges that represent multi-way relations
출력 예:

{
  "nodes": [
    {
      "id": "concept_hypergraph",
      "type": "Concept",
      "label": "Hypergraph"
    },
    {
      "id": "project_memory_os",
      "type": "Project",
      "label": "Personal AI Memory OS"
    },
    {
      "id": "decision_use_hypergraph",
      "type": "Decision",
      "label": "Use hypergraph to model multi-way AI memory relations"
    }
  ],
  "hyperedges": [
    {
      "type": "DecisionEvent",
      "label": "Hypergraph selected as memory structure",
      "summary": "The user concluded that 1-to-many hypergraph relations are more appropriate than pairwise graph edges for modeling AI conversation memory.",
      "members": [
        {
          "node_id": "concept_hypergraph",
          "role": "chosen_structure",
          "weight": 1.0
        },
        {
          "node_id": "project_memory_os",
          "role": "target_system",
          "weight": 1.0
        },
        {
          "node_id": "decision_use_hypergraph",
          "role": "decision",
          "weight": 1.0
        }
      ],
      "confidence": 0.93,
      "importance": 0.91
    }
  ]
}
15. 가장 좋은 MVP 구현
처음부터 hypergraph neural network는 하지 마.
서비스 MVP에서는 이렇게 가.

Postgres:
- nodes
- hyperedges
- hyperedge_members
- embeddings

pgvector:
- node embeddings
- hyperedge embeddings

LLM:
- hyperedge extractor
- context pack builder

Agent:
- node search
- hyperedge search
- membership expansion
Neo4j는 나중에 시각화/탐색용으로 붙여도 돼.

16. 최소 DB schema
CREATE TABLE nodes (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  label TEXT,
  content TEXT,
  source TEXT,
  created_at TIMESTAMP,
  metadata JSONB
);

CREATE TABLE hyperedges (
  id TEXT PRIMARY KEY,
  type TEXT NOT NULL,
  label TEXT,
  summary TEXT,
  status TEXT DEFAULT 'active',
