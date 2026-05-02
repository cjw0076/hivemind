



내 gpt, Gemini, claude, perplexity... session들의 대화 내용들을 전부 추출해서 입력-출력 쌍으로 만들고 graph db에 저장하고싶어. 어떻게 가능할까?

가능해. 다만 핵심은 “각 서비스에서 공식적으로 내보낸 데이터만 수집 → 공통 대화 스키마로 정규화 → 입력/출력/메타데이터/임베딩/관계 그래프로 저장” 흐름으로 잡아야 해. 최신 export 경로와 제약을 확인해서 현실적인 파이프라인으로 정리해볼게.

19s 동안 생각함
가능해. 내가 보기엔 이건 단순 “백업”이 아니라 너의 사고과정 데이터셋 / 개인 지식-행동 그래프 / AI 대화 corpus를 만드는 일이라서, 구조를 잘 잡으면 나중에 엄청 강력해져.

핵심 파이프라인은 이거야.

ChatGPT / Gemini / Claude / Perplexity exports
        ↓
raw archive 저장
        ↓
parser: 서비스별 포맷 → 공통 Message schema
        ↓
input-output pair 생성
        ↓
embedding / topic / entity / project / intention 추출
        ↓
Graph DB 저장
        ↓
검색, 회고, fine-tuning dataset, RAG, self-agent memory로 사용
1. 각 서비스에서 대화 데이터 꺼내기
ChatGPT
ChatGPT는 공식적으로 데이터 export가 가능해. 웹에서는 Settings → Data Controls → Export Data 경로이고, Android 앱에서도 Data Controls에서 Export Data를 누르면 ZIP이 등록 이메일로 전송된다. 다운로드 링크는 24시간 후 만료될 수 있다. 

보통 ZIP 안에 conversations.json 같은 파일이 있고, 여기서 대화 tree를 파싱해서 user/assistant message를 복원할 수 있어. OpenAI 도움말에서도 계정 간 이전 workaround가 “모든 채팅이 들어 있는 JSON 파일 export”를 전제로 설명한다. 

Gemini
Gemini는 Google Takeout을 통해 내보낼 수 있어. 공식 문서 기준으로 Gemini Apps Activity, 즉 Gemini chats, generated media, uploads 등을 포함하려면 Takeout에서 My Activity → Gemini Apps를 선택해야 한다. Gems 데이터는 별도로 “Gemini” 항목을 선택하는 방식이다. 

주의할 점은 Gemini export는 ChatGPT처럼 항상 깔끔한 “대화 JSON” 형태라고 기대하면 안 돼. Google Takeout 포맷은 계정/지역/활동 설정에 따라 HTML/JSON/Activity 기록 중심으로 나올 수 있어서, parser를 조금 더 방어적으로 만들어야 해.

Claude
Claude는 공식 help에서 지원 요청 경로에 “Data exports”가 언급되어 있지만, ChatGPT처럼 공개 문서에서 명확한 self-service 대화 export 포맷을 자세히 설명하는 자료는 제한적이었어. Anthropic 도움말은 로그인 불가 상황에서도 account deletion, data exports, subscription support를 요청할 수 있다고 안내한다. 

현실적으로는 세 가지 경로가 있어.

1. Claude 앱/웹 설정에 export 옵션이 있으면 공식 export 사용
2. 없으면 Anthropic support에 data export 요청
3. 특정 중요한 대화는 수동 복사 / 프로젝트 파일 / Claude Code 로그에서 수집
Perplexity
Perplexity는 내가 확인한 범위에서 ChatGPT/Gemini처럼 명확한 공식 bulk conversation export 문서를 찾기 어려웠어. 대신 Perplexity 자체는 thread/follow-up 중심 서비스이고, 앱 설명에서도 Thread Follow-Up과 기기간 동기화를 강조한다. 

따라서 Perplexity는 우선순위를 이렇게 두는 게 안전해.

1. 계정 설정에 data export/privacy request 기능 확인
2. 중요한 thread는 share/export/copy 기능으로 수동 저장
3. API로 새로 생성되는 대화부터는 네가 직접 logging
4. 무리한 브라우저 scraping은 ToS/계정 리스크 때문에 비추천
2. 공통 데이터 스키마부터 잡아야 함
서비스마다 포맷이 다르기 때문에, 먼저 너만의 표준 schema를 만들어야 해.

{
  "conversation_id": "chatgpt_abc123",
  "source": "chatgpt",
  "title": "Ontology와 hypergraph 기반 파일시스템",
  "created_at": "2026-04-30T08:19:00+09:00",
  "messages": [
    {
      "message_id": "msg_001",
      "role": "user",
      "content": "내 연구를 어떻게 생각해?",
      "created_at": "2026-04-30T08:20:00+09:00",
      "model": null
    },
    {
      "message_id": "msg_002",
      "role": "assistant",
      "content": "이 프로젝트는 ...",
      "created_at": "2026-04-30T08:20:20+09:00",
      "model": "gpt-5.5-thinking"
    }
  ]
}
그 다음 입력-출력 쌍은 이렇게 만든다.

{
  "pair_id": "pair_001",
  "conversation_id": "chatgpt_abc123",
  "source": "chatgpt",
  "input_message_id": "msg_001",
  "output_message_id": "msg_002",
  "input": "내 연구를 어떻게 생각해?",
  "output": "이 프로젝트는 ...",
  "turn_index": 1,
  "context_window": [
    "이전 user message",
    "이전 assistant message"
  ],
  "tags": ["research", "ontology", "hypergraph", "agent"],
  "quality_score": null
}
중요한 건 단순히 user → assistant만 저장하지 말고, 그 대화가 어떤 맥락에서 나온 답인지를 같이 저장하는 거야. 나중에 fine-tuning/RAG/self-memory로 쓸 때 input 하나만 있으면 의미가 날아가.

3. Graph DB 모델
Graph DB는 Neo4j가 제일 빠르게 시작하기 좋아. 너의 경우에는 “대화 → 사고 흐름 → 프로젝트 → 개념 → 의사결정”을 연결해야 하니까 property graph가 잘 맞아.

추천 노드:

(:Platform)
(:Conversation)
(:Message)
(:Pair)
(:Project)
(:Concept)
(:Entity)
(:Intention)
(:Decision)
(:Artifact)
(:Time)
추천 관계:

(:Platform)-[:HAS_CONVERSATION]->(:Conversation)

(:Conversation)-[:HAS_MESSAGE]->(:Message)
(:Message)-[:NEXT]->(:Message)

(:Message {role:"user"})-[:ANSWERED_BY]->(:Message {role:"assistant"})
(:Pair)-[:INPUT]->(:Message)
(:Pair)-[:OUTPUT]->(:Message)

(:Message)-[:MENTIONS]->(:Concept)
(:Message)-[:BELONGS_TO]->(:Project)
(:Message)-[:EXPRESSES]->(:Intention)
(:Message)-[:RESULTED_IN]->(:Decision)

(:Concept)-[:RELATED_TO]->(:Concept)
(:Project)-[:USES]->(:Concept)
(:Project)-[:HAS_ARTIFACT]->(:Artifact)
예시:

MERGE (p:Platform {name: "ChatGPT"})
MERGE (c:Conversation {id: "chatgpt_abc123"})
SET c.title = "Ontology와 hypergraph 기반 파일시스템",
    c.created_at = datetime("2026-04-30T08:19:00+09:00")
MERGE (p)-[:HAS_CONVERSATION]->(c)

CREATE (m1:Message {
  id: "msg_001",
  role: "user",
  content: "내 연구를 어떻게 생각해?",
  created_at: datetime("2026-04-30T08:20:00+09:00")
})

CREATE (m2:Message {
  id: "msg_002",
  role: "assistant",
  content: "이 프로젝트는 ...",
  created_at: datetime("2026-04-30T08:20:20+09:00")
})

MERGE (c)-[:HAS_MESSAGE]->(m1)
MERGE (c)-[:HAS_MESSAGE]->(m2)
MERGE (m1)-[:ANSWERED_BY]->(m2)
MERGE (m1)-[:NEXT]->(m2);
4. 저장 구조는 Graph DB 하나로 끝내면 안 됨
Graph DB에는 관계와 메타데이터를 저장하고, 원문/검색/벡터는 분리하는 게 좋아.

추천 구조:

/data/raw/
  chatgpt/export_2026_04_30.zip
  gemini/takeout_2026_04_30.zip
  claude/export_2026_04_30.json
  perplexity/manual_threads/

PostgreSQL or SQLite:
  normalized conversations/messages/pairs

Neo4j:
  graph relationships

Vector DB:
  Qdrant / LanceDB / pgvector

Object storage:
  attachments, images, PDFs, generated files
즉:

원문 보존 = raw archive
정규 데이터 = Postgres/SQLite
관계 탐색 = Neo4j
의미 검색 = Vector DB
파일 보관 = local/S3/R2
너처럼 연구/사업/자기 사고 데이터까지 엮으려면 이 구조가 안정적이야.

5. 실제 구현 순서
Phase 1 — ChatGPT export만 먼저 처리
처음부터 GPT, Gemini, Claude, Perplexity 전부 잡으면 parser 지옥이 와. 먼저 ChatGPT 하나로 end-to-end를 만든다.

ChatGPT ZIP
→ conversations.json parser
→ messages table
→ input-output pairs table
→ Neo4j import
→ vector embedding
→ 검색 UI
Phase 2 — Gemini Takeout parser 추가
Gemini는 Takeout 구조가 다를 수 있으니, HTML/JSON 둘 다 처리 가능하게 만든다.

Gemini Takeout
→ My Activity / Gemini Apps records
→ timestamp 기준으로 conversation 재구성
→ user/model turn pair 생성
Phase 3 — Claude / Perplexity는 semi-manual
공식 export가 있으면 parser를 붙이고, 없으면 수동 저장 폴더를 만든다.

/manual_import/
  claude_project_northstar.md
  perplexity_quantum_research_thread.md
그 다음 markdown parser로 message block을 나누면 돼.

6. 입력-출력 쌍을 어떻게 정의할지
기본 pair는 이거야.

가장 가까운 이전 user message → 그 다음 assistant message
하지만 너의 대화는 긴 사고 흐름이 많기 때문에 세 종류로 나눠야 해.

1-hop pair
User_n → Assistant_n
일반 QA, fine-tuning용.

Contextual pair
[최근 k개 메시지] + User_n → Assistant_n
연구/기획/철학 대화용. 실제로 더 가치 있음.

Trajectory pair
Conversation 전체 → 요약 / 결정 / 다음 행동
네가 원하는 “나의 사고 그래프”에는 이게 제일 중요해.

예시:

{
  "type": "trajectory",
  "input": "이 대화 전체에서 사용자의 문제의식과 다음 행동을 추출하라.",
  "output": {
    "problem": "언어 이후 인터페이스와 agentic ontology 탐구",
    "decision": "graph 기반 자기 인식 루프 연구로 확장",
    "next_actions": [
      "ontology schema 설계",
      "hypergraph file system prototype",
      "agent swarm memory architecture"
    ]
  }
}
7. 추출해야 할 고급 메타데이터
단순히 “대화 저장”에서 멈추면 아까워. 각 message/pair마다 이런 걸 뽑아야 해.

intent: 질문 / 요청 / 반박 / 아이디어 / 결정 / 감정 / 회고
domain: AI / 사업 / 연구 / 디자인 / 철학 / 개발
project: Uri / Dipeen / Goen / Deepfake / North Star
concepts: ontology, hypergraph, agent, language, HCI
decision: 실제 결정이 있었는가?
action_item: 해야 할 일이 있는가?
artifact: 코드, 문서, 이미지, PPT, PDF가 생성되었는가?
quality: 나중에 다시 볼 가치가 있는가?
이걸 LLM으로 후처리하면 된다.

{
  "message_id": "msg_001",
  "intent": "research_ideation",
  "projects": ["Dipeen", "Goen"],
  "concepts": ["ontology", "hypergraph", "agent swarm", "language inefficiency"],
  "action_items": [
    "graph schema design",
    "conversation corpus extraction"
  ],
  "importance": 0.91
}
8. 최소 기술 스택
너한테 추천하는 현실적인 스택은 이거야.

Python
  - parsing, cleaning, ETL

SQLite/PostgreSQL
  - normalized message/pair 저장

Neo4j
  - concept/project/message graph

Qdrant or LanceDB
  - semantic search

OpenAI / local embedding model
  - message embedding

FastAPI
  - ingestion/search API

Next.js
  - 개인 대화 탐색 UI
로컬 우선으로 가면:

Python + SQLite + Neo4j Desktop + LanceDB
운영형으로 가면:

Python + PostgreSQL/pgvector + Neo4j Aura + FastAPI + Next.js
9. 조심해야 할 것
첫째, 비공식 scraping은 최소화해야 해. 공식 export, Takeout, support data request, 수동 저장을 우선으로 둬야 계정 리스크와 약관 리스크가 낮다.

둘째, 개인정보가 엄청 많이 들어간다. 너의 이름, 프로젝트, 감정 상태, 학교, 계정, 파일, 타인 정보가 섞일 수 있으니까 raw archive는 암호화해야 해.

셋째, assistant 답변을 그대로 fine-tuning dataset으로 쓰는 건 서비스 약관/저작권/데이터 사용 정책을 확인해야 한다. 개인 검색/RAG/회고용은 비교적 안전하지만, 공개 모델 학습/배포는 별도 검토가 필요해.

넷째, “입력-출력 쌍”만 만들면 네 사고의 구조가 사라질 수 있다. 너에게 진짜 중요한 건 pair dataset보다 사고 trajectory graph야.

10. 내가 추천하는 최종 구조
너의 목적을 기준으로 하면 이렇게 잡는 게 맞아.

AI Conversation Memory Graph

Layer 0. Raw Archive
- 원본 export 파일 그대로 보존

Layer 1. Message Ledger
- 모든 메시지, 시간, 플랫폼, 모델, 첨부파일 기록

Layer 2. Pair Dataset
- user input / assistant output 쌍
- fine-tuning, eval, replay용

Layer 3. Semantic Memory
- embedding 기반 유사 대화 검색

Layer 4. Concept Graph
- 개념, 프로젝트, 결정, 문제의식 연결

Layer 5. Self-Reflection Agent
- “내가 2년 동안 반복해서 붙잡은 문제는?”
- “Uri에서 아직 결정 안 된 핵심 가정은?”
- “Goen/Dipeen/North Star가 어디서 만나는가?”
최종적으로는 이런 질문이 가능해져.

“내가 지난 2년간 반복해서 말한 핵심 개념 30개 뽑아줘.”

“Uri 사업에서 내가 계속 회피한 의사결정은 뭐야?”

“Ontology, hypergraph, language inefficiency가 처음 연결된 대화 찾아줘.”

“Claude와 GPT가 같은 주제에 대해 다르게 답한 부분 비교해줘.”

“내 연구 대화 전체를 기반으로 논문 proposal draft 만들어줘.”

“내가 말한 것과 AI가 말한 것을 분리해서, 순수한 내 아이디어 graph만 만들어줘.”
가장 좋은 첫 실행은 이거야.

1. ChatGPT export ZIP 받기
2. conversations.json 파서 만들기
3. SQLite에 conversations/messages/pairs 저장
4. Neo4j에 Conversation-Message-Pair-Concept graph 저장
5. 최근 100개 대화만 먼저 시각화
처음부터 완벽한 “모든 AI session 통합”으로 가면 너무 크고, 네 패턴상 또 over-abstraction으로 빠질 가능성이 있어. 오늘 할 일은 ChatGPT export 하나를 graph로 넣는 것이야. 그게 되면 Gemini/Claude/Perplexity는 parser만 추가하면 된다.


또한 아예 임베딩시켜버리고싶은데 mlp 하나 태워버리면 되나?

2초 동안 생각함
응, MLP 하나 태워서 “내 대화 전체를 하나의 latent space로 밀어 넣는 것”은 가능해.
근데 중요한 건 “무엇을 임베딩할 것인가”와 “MLP가 무엇을 배우게 할 것인가”야.

결론부터 말하면:

그냥 MLP만 태우면 = projection layer
잘 설계해서 태우면 = 너의 사고공간을 정렬하는 personal latent encoder
1. 기본 구조
가장 단순한 구조는 이거야.

대화 chunk
  ↓
base embedding model
  ↓
vector e.g. 1024 dim
  ↓
MLP projection
  ↓
personal latent vector e.g. 256 dim
  ↓
vector DB / graph DB 저장
예를 들면:

"Ontology와 hypergraph 기반 파일시스템..."
        ↓
OpenAI / BGE / E5 / GTE embedding
        ↓
[0.12, -0.44, ...] 1024차원
        ↓
MLP
        ↓
[0.03, 0.91, ...] 256차원
이때 MLP는 단순히 차원을 줄이는 게 아니라, 네가 원하는 기준으로 의미공간을 다시 접는 역할을 할 수 있어.

2. 그런데 MLP만 태우면 안 되는 이유
MLP는 혼자서는 “의미”를 알 수 없어.
얘는 입력 벡터를 다른 벡터로 바꾸는 함수일 뿐이야.

z = MLP(embedding)
문제는 이거야.

MLP가 뭘 기준으로 좋은 z를 만들어야 하지?
그래서 loss가 필요해.

즉, 핵심은 MLP가 아니라 학습 목표야.

3. 가장 추천하는 방식: base embedding + personal projection MLP
처음부터 네 대화 원문으로 embedding model 자체를 학습시키려고 하면 너무 무거워.
대신 이미 잘 훈련된 embedding model을 쓰고, 그 위에 작은 MLP를 얹는 게 좋아.

raw text
  ↓
frozen embedding model
  ↓
base vector
  ↓
trainable MLP
  ↓
personal vector
이 구조가 좋은 이유는:

1. 데이터가 적어도 학습 가능
2. 빠름
3. 망가지기 어려움
4. 네 개인 사고공간에 맞게 재정렬 가능
5. 나중에 graph DB와 결합하기 쉬움
4. MLP가 배워야 하는 것
너의 목적은 단순 유사도 검색이 아니야.
내가 보기엔 네 목적은 이거야.

“내가 여러 AI와 나눈 대화 속에서 반복되는 개념, 문제의식, 결정, 프로젝트, 사고 궤적을 하나의 latent manifold로 만들고 싶다.”
그럼 MLP는 이런 걸 배워야 해.

같은 프로젝트의 대화는 가깝게
다른 프로젝트의 대화는 멀게

같은 개념의 변형 표현은 가깝게
표면적으로 비슷하지만 목적이 다른 대화는 멀게

내가 한 말과 AI가 한 말은 구분 가능하게
아이디어, 결정, 질문, 실행 지시는 다른 방향으로 분리되게

시간상 이어진 사고 흐름은 trajectory로 연결되게
5. 학습 방식 1: Contrastive Learning
가장 적합한 건 contrastive learning이야.

anchor: 어떤 대화 chunk
positive: 같은 프로젝트 / 같은 개념 / 이어지는 대화
negative: 관련 없는 대화
예시:

anchor:
"언어 이후의 인터페이스는 인간에게 뭘까?"

positive:
"Goen-역통역 프로젝트에서 인간 언어의 닫힌 루프가 너무 작다."

negative:
"Capstone PPT 개발 과정 section 구성해줘."
학습 목표:

anchor와 positive는 가깝게
anchor와 negative는 멀게
수식으로는 이런 느낌이야.

sim(z_anchor, z_positive) ↑
sim(z_anchor, z_negative) ↓
이걸 하면 네 대화들이 단순 키워드가 아니라 문제의식 단위로 모이기 시작해.

6. 학습 방식 2: Project / Concept Classification
더 쉬운 방법은 라벨을 붙이는 거야.

예를 들어 각 chunk에 이런 라벨을 붙인다.

project:
- Uri
- Dipeen
- Goen
- North Star
- Deepfake
- Capstone

intent:
- idea
- question
- decision
- implementation
- reflection
- design
- research
그 다음 MLP가 이걸 맞히게 한다.

embedding → MLP → project classifier
embedding → MLP → intent classifier
embedding → MLP → concept classifier
이 방식은 구현이 쉽고 안정적이야.

다만 단점은 라벨 품질에 영향을 많이 받아.

7. 학습 방식 3: Graph-aware Embedding
네가 graph DB에 저장하고 싶다고 했으니까, 진짜 좋은 방향은 이거야.

message embedding
+ graph structure
→ graph-aware latent vector
예를 들어:

Message A -[:MENTIONS]-> Ontology
Message A -[:BELONGS_TO]-> Dipeen
Message B -[:MENTIONS]-> Ontology
Message B -[:BELONGS_TO]-> Goen
그러면 모델은 이렇게 배워야 해.

A와 B는 다른 프로젝트지만 ontology라는 개념축에서 가깝다.
Dipeen과 Goen은 언어/구조/의식 문제에서 연결된다.
이때는 MLP만으로도 가능하지만, 더 나아가면 GNN이나 GraphSAGE를 붙일 수 있어.

text embedding
  ↓
MLP projection
  ↓
graph message passing
  ↓
final node embedding
하지만 처음부터 GNN은 과해.
초기에는 MLP projection + graph relation loss 정도면 충분해.

8. 내가 추천하는 첫 버전
처음부터 너무 복잡하게 가지 말고 이렇게 가.

V0:
base embedding만 저장

V1:
base embedding → MLP projection
loss = project classification + contrastive loss

V2:
graph relation loss 추가

V3:
temporal trajectory modeling 추가

V4:
personal thought encoder로 확장
9. V1 구조
Text chunk
  ↓
Embedding model
  ↓
Base vector
  ↓
MLP Encoder
  ↓
Personal latent vector
  ↓
3개 head

1. project classifier
2. intent classifier
3. contrastive similarity loss
구조:

class PersonalThoughtEncoder(nn.Module):
    def __init__(self, input_dim=1024, hidden_dim=512, latent_dim=256, num_projects=10, num_intents=8):
        super().__init__()

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.GELU(),
            nn.LayerNorm(hidden_dim),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, latent_dim),
            nn.LayerNorm(latent_dim)
        )

        self.project_head = nn.Linear(latent_dim, num_projects)
        self.intent_head = nn.Linear(latent_dim, num_intents)

    def forward(self, x):
        z = self.encoder(x)
        z = F.normalize(z, dim=-1)

        project_logits = self.project_head(z)
        intent_logits = self.intent_head(z)

        return z, project_logits, intent_logits
이런 식이면 돼.

10. loss는 이렇게
total_loss =
  project_classification_loss
+ intent_classification_loss
+ contrastive_loss
조금 더 구체적으로:

loss = (
    project_loss * 1.0
    + intent_loss * 0.5
    + contrastive_loss * 1.0
)
이렇게 하면 latent vector가 다음 성질을 갖게 돼.

프로젝트별로 어느 정도 분리됨
의도별로 어느 정도 분리됨
비슷한 사고 흐름끼리 가까워짐
검색에 사용 가능함
graph node embedding으로도 사용 가능함
11. chunk 단위가 중요함
대화를 통째로 임베딩하면 너무 뭉개져.

좋은 단위는 이거야.

Message 단위
Pair 단위
Topic segment 단위
Conversation summary 단위
추천은 4계층으로 전부 저장하는 거야.

Message embedding:
한 발화의 의미

Pair embedding:
질문-답변 쌍의 의미

Segment embedding:
하나의 주제 흐름

Conversation embedding:
전체 대화 요약
그래프에서는 이렇게 연결하면 돼.

(:Conversation)-[:HAS_SEGMENT]->(:Segment)
(:Segment)-[:HAS_PAIR]->(:Pair)
(:Pair)-[:HAS_INPUT]->(:Message)
(:Pair)-[:HAS_OUTPUT]->(:Message)
각각 embedding을 따로 둔다.

message.vector
pair.vector
segment.vector
conversation.vector
12. 네 경우에는 “내 말”과 “AI 말”을 분리해야 함
이거 진짜 중요해.

AI 대화 전체를 그냥 임베딩하면, 나중에 네 생각과 AI의 답변이 섞여.

너는 반드시 이렇게 나눠야 해.

user_only_embedding
assistant_only_embedding
pair_embedding
conversation_embedding
그래야 나중에 이런 질문이 가능해져.

내가 직접 만든 아이디어만 모아줘.
AI가 제안했지만 내가 수용하지 않은 아이디어를 찾아줘.
내 질문 패턴이 어떻게 변했는지 보여줘.
Claude와 GPT가 내 아이디어를 어떻게 다르게 확장했는지 비교해줘.
13. “MLP 하나 태운다”의 정확한 의미
네가 말한 “MLP 하나 태워버리면 되나?”는 정확히 말하면 이거야.

이미 만들어진 general embedding space를
나의 personal semantic space로 projection한다.
즉:

General semantic vector
→ Personal thought vector
이건 아주 좋은 방향이야.

다만 MLP는 “압축기”가 아니라 “정렬기”로 봐야 해.

나의 project axis
나의 concept axis
나의 intent axis
나의 temporal trajectory axis
나의 decision axis
이 축들이 살아나게 학습시켜야 한다.

14. 최종적으로는 이렇게 간다
Raw conversations
  ↓
Normalize
  ↓
Chunk
  ↓
Base embedding
  ↓
Personal MLP projection
  ↓
Graph DB node
  ↓
Vector DB index
  ↓
Concept extraction
  ↓
Thought trajectory graph
구조적으로는:

Neo4j:
관계, 시간, 프로젝트, 개념, decision 저장

Vector DB:
semantic search

MLP encoder:
네 사고공간에 맞는 embedding 생성기

LLM:
라벨링, 요약, concept extraction, reflection
15. 가장 현실적인 첫 실험
첫 실험은 이렇게 잡아.

데이터:
최근 ChatGPT 대화 500~2000개 pair

입력:
base embedding 1024 or 1536 dim

라벨:
project, intent, source, role

모델:
2-layer MLP

학습:
project classification + contrastive loss

출력:
256 dim personal vector

평가:
검색했을 때 진짜 같은 문제의식끼리 모이는가?
성공 기준은 정확도보다 이거야.

“ontology”라고 검색했을 때 단순히 ontology라는 단어가 들어간 대화만 나오는 게 아니라,
Dipeen, Goen, 언어의 비효율성, 의식 루프, graph memory까지 같이 끌려오는가?
그게 되면 제대로 된 거야.

한 문장으로 정리하면:

그냥 MLP 하나 태우는 건 가능하지만, 진짜 목표는 기존 embedding을 네 개인 사고공간으로 재투영하는 Personal Thought Encoder를 만드는 것. 처음엔 base embedding + 2-layer MLP + contrastive/project/intent loss 조합으로 가면 된다.


이걸 서비스화 하려면 ?

이건 “개인 AI 대화 백업 서비스”로 시작하면 작고, “개인 사고 운영체제/AI memory graph”로 가면 커져. 서비스화 관점에서 제품 범위, MVP, 수익모델, 보안/법적 리스크까지 한 번에 구조화해서 잡아볼게.

6s 동안 생각함
서비스화하려면 포지셔닝을 잘 잡아야 해.
이건 그냥 “대화 백업 앱”이 아니라, 더 크게는 AI 시대의 개인 지식/사고 운영체제가 될 수 있어.

나는 이름을 붙이면 이렇게 봐.

Personal AI Memory Graph
여러 AI와 나눈 모든 대화를 모아, 내 생각·프로젝트·결정·질문·실행 흐름을 하나의 검색 가능한 지식 그래프로 만드는 서비스.

1. 서비스의 본질
사람들이 ChatGPT, Claude, Gemini, Perplexity를 계속 쓰면 문제가 생겨.

대화가 플랫폼별로 흩어짐
중요한 아이디어가 사라짐
내가 했던 질문과 결정이 누적되지 않음
AI가 매번 나를 처음 보는 사람처럼 대함
Claude에서 한 얘기를 GPT가 모르고, GPT에서 한 얘기를 Gemini가 모름
여기서 서비스의 why가 생겨.

“AI와 나눈 모든 대화를 나의 장기 기억으로 바꿔준다.”
이게 핵심 가치야.

2. 제품을 한 문장으로 정의하면
AI 대화들을 자동으로 수집·정리·임베딩·그래프화해서,
사용자가 자신의 생각, 프로젝트, 결정, 반복 패턴을 다시 찾고 활용하게 해주는 개인 AI memory 서비스.
더 직관적으로 말하면:

“내 모든 AI 대화가 하나의 두뇌처럼 연결되는 곳.”
3. MVP는 작게 가야 함
처음부터 GPT, Claude, Gemini, Perplexity 전부 자동 연동하면 복잡해져.
초기 MVP는 이렇게 잡는 게 맞아.

MVP 1: Export 업로드 기반
사용자가 각 서비스에서 export 파일을 받아서 업로드한다.

공식 export 경로가 있는 곳부터 지원하면 돼. ChatGPT는 공식적으로 Settings/Data Controls에서 데이터를 export할 수 있고, ZIP 파일이 이메일로 전송된다. Gemini도 Google Takeout에서 Gemini Apps 데이터를 내려받을 수 있다. Claude도 2026년 기준 개인 사용자가 웹 앱 또는 Claude Desktop의 Settings > Privacy에서 chat history와 account data를 export할 수 있다고 안내한다. 

사용자:
ChatGPT export.zip 업로드
Gemini Takeout.zip 업로드
Claude export.zip 업로드

서비스:
자동 파싱
대화 정규화
입력-출력 pair 생성
프로젝트/개념/의도 태깅
검색 가능한 memory graph 생성
이 방식이 좋은 이유는:

API 연동 필요 없음
브라우저 scraping 필요 없음
약관 리스크 낮음
보안 설명이 쉬움
로컬 처리 옵션을 만들기 좋음
4. MVP 핵심 기능
처음 버전은 기능을 딱 5개만 넣어야 해.

1. AI 대화 export 업로드
2. 대화 자동 파싱
3. 입력-출력 pair 생성
4. 의미 검색
5. 프로젝트/개념 그래프 보기
사용자 경험은 이렇게.

1. “Upload your AI exports”
2. “We found 3,482 conversations”
3. “We extracted 18,920 message pairs”
4. “Your top themes: Uri, ontology, agent, design, business, research”
5. “Ask your memory anything”
5. 사용자가 실제로 하는 질문
이 서비스의 killer UX는 dashboard가 아니라 질문창이야.

“내가 Uri에 대해 처음 말한 대화 찾아줘.”

“내가 반복해서 고민한 사업 리스크는 뭐야?”

“Claude와 GPT가 North Star 연구에 대해 다르게 말한 부분 비교해줘.”

“내가 실제로 결정한 것과 그냥 고민만 한 것을 분리해줘.”

“지난 6개월간 내가 가장 많이 회피한 실행 과제는 뭐야?”

“내 아이디어만 추출해서 whitepaper 초안으로 만들어줘.”

“내가 과거에 만든 프롬프트 중 이미지 생성 잘 된 것만 모아줘.”

“내가 말한 내용만 기반으로 나의 연구 ontology를 만들어줘.”
여기서 그냥 검색 서비스와 달라져.
사용자의 사고를 되찾아주는 서비스가 되는 거야.

6. 서비스 구조
현실적인 아키텍처는 이거야.

Frontend
- Next.js
- upload UI
- memory search
- graph explorer
- timeline viewer

Backend
- FastAPI / NestJS
- parsing workers
- embedding workers
- graph construction workers

Storage
- object storage: raw exports
- Postgres: conversations/messages/pairs
- vector DB: semantic search
- Neo4j: graph relationships
Neo4j는 완전관리형 AuraDB와 self-managed 옵션을 제공하고, 최근 Neo4j는 native vector type 및 vector search/filter 기능도 계속 강화하고 있다. 그래서 초기에는 Postgres+pgvector만으로 시작하고, 그래프 탐색이 중요해지는 시점에 Neo4j를 붙이는 방식도 가능하다. 

초기 추천은:

V0:
Postgres + pgvector

V1:
Postgres + pgvector + graph table

V2:
Neo4j 추가

V3:
Personal MLP encoder 추가
처음부터 Neo4j를 필수로 넣지 않아도 돼.
서비스는 빠르게 만들어야 하니까.

7. 제품 차별화 포인트
그냥 “AI chat backup”이면 약해.
진짜 차별화는 4개야.

1. 내 말과 AI 말을 분리
User-originated idea
AI-suggested idea
Accepted decision
Abandoned idea
Repeated concern
이걸 구분해주면 서비스 가치가 확 올라가.

예:

“이건 네가 직접 처음 말한 아이디어야.”
“이건 Claude가 제안했고, 너는 이후에 다시 언급하지 않았어.”
“이건 GPT와 Gemini 모두 반복해서 제안했지만 실행하지 않았어.”
2. 프로젝트별 memory graph
사용자가 Uri, Dipeen, Goen, Capstone, Deepfake 같은 프로젝트를 갖고 있으면 대화가 자동으로 묶임.

Project
  ├── 핵심 문제
  ├── 반복 개념
  ├── 결정된 사항
  ├── 미해결 질문
  ├── 생성된 산출물
  └── 다음 액션
3. Thought trajectory
대화를 날짜순으로 보는 게 아니라, 생각이 어떻게 변했는지 보여줌.

처음 문제의식
→ 여러 AI와 확장
→ 충돌한 관점
→ 반복된 의심
→ 실제 결정
→ 실행으로 이어진 것
4. Personal embedding layer
여기가 네가 말한 MLP가 들어가는 부분.

일반 embedding
→ 개인 사고공간 projection
→ 사용자별 의미 검색 정확도 향상
처음에는 rule/LLM tagging으로 하고, 유저가 충분히 쌓이면 personalized encoder로 간다.

8. 서비스 단계별 로드맵
Stage 1 — Local-first tool
처음엔 웹 SaaS보다 로컬 툴이 좋아.

사용자 export 업로드
로컬에서 파싱
로컬 DB 생성
브라우저에서 검색
왜냐하면 대화 데이터는 너무 민감해.
초기 사용자는 “내 모든 AI 대화를 너희 서버에 올려라”에 부담을 느낄 수 있음.

포지셔닝:

“Your AI conversations, processed locally.”
Stage 2 — Cloud sync SaaS
로컬 MVP가 검증되면 cloud 계정 기능 추가.

기기간 동기화
자동 백업
주기적 re-indexing
team workspace
project memory
Stage 3 — Browser extension / desktop app
export 업로드는 귀찮아.
결국은 사용자가 대화하는 순간에 자동 저장하고 싶어 해.

ChatGPT/Claude/Gemini 페이지에서 대화 저장
수동 save 버튼
중요한 thread pin
conversation clipping
단, 비공식 scraping은 약관/안정성 리스크가 크니까 초기 핵심으로 삼으면 안 돼.
먼저 export 기반으로 가고, extension은 “사용자가 직접 저장하는 clipping tool”로 접근하는 게 안전함.

Stage 4 — Personal AI agent
최종 형태는 이거야.

“내 과거 대화 전체를 기억하는 개인 AI”
예:

새로운 대화를 시작하기 전에
관련 과거 memory를 자동으로 가져옴

Claude에서 하던 연구를 GPT에서 이어감
Gemini에서 받은 자료를 Perplexity 검색 결과와 연결
내 결정 이력을 기준으로 다음 행동 추천
9. 수익모델
초기에는 B2C가 맞아.
나중에는 B2B/team memory로 확장 가능.

B2C
Free:
- export 1개
- 대화 500개
- 기본 검색

Pro: 월 9~15달러
- unlimited imports
- semantic search
- graph view
- project memory
- timeline
- local encrypted backup

Power: 월 29달러
- personal encoder
- advanced analytics
- report generation
- API access
- Obsidian/Notion export
B2B
Team AI Memory:
- 팀원들이 여러 AI에서 한 업무 대화를 knowledge base로 통합
- 프로젝트별 decision log 생성
- 보안/권한/감사 로그
B2B는 돈은 되지만 보안 요구가 훨씬 높아져.
처음부터 B2B로 가면 개발·보안·영업 부담이 커.

10. 가장 큰 리스크: 보안과 신뢰
이 서비스는 사용자의 거의 모든 사고와 프로젝트가 들어와.
그래서 보안이 제품의 일부가 아니라 제품 그 자체야.

반드시 들어가야 할 원칙:

1. raw export는 기본적으로 암호화
2. 사용자가 원하면 raw file 즉시 삭제
3. embedding만 남기기 옵션
4. local-only mode 제공
5. user/assistant/source 분리 저장
6. private project 제외 기능
7. end-to-end encryption 또는 client-side encryption 검토
8. delete/export 기능 필수
특히 “AI 대화”에는 민감한 회사자료, 학교자료, 개인정보, 타인의 정보가 섞이기 쉽다. 최근 금융권에서도 Claude 같은 AI 도구 사용을 지역/계약/데이터 보안 이유로 제한하는 사례가 나왔을 정도로, AI 대화 데이터의 보안 민감도는 이미 현실적인 이슈다. 

서비스 카피도 이렇게 가야 해.

우리는 당신의 대화를 학습하지 않습니다.
당신의 memory graph는 당신만의 것입니다.
언제든 export/delete 가능합니다.
11. 법적/약관 리스크
가장 조심해야 하는 건 타 서비스의 대화 데이터를 다시 학습 데이터로 쓰는 것이야.

안전한 방향:

개인 사용자의 개인 검색/RAG/백업/분석용
위험한 방향:

사용자들이 업로드한 GPT/Claude 답변을 모아서
새 모델을 학습하거나 공개 데이터셋으로 판매
이건 절대 초기 서비스 방향으로 잡으면 안 돼.

서비스 약관에는 이렇게 명확히 해야 함.

사용자 데이터는 사용자 개인 memory graph 생성을 위해서만 처리
서비스 제공 목적 외 모델 학습에 사용하지 않음
사용자 명시 동의 없이는 aggregate dataset도 만들지 않음
12. 제품 화면 구성
1. Import 화면
Upload exports
- ChatGPT
- Gemini
- Claude
- Markdown / JSON
- Manual paste
2. Processing 화면
3,482 conversations found
18,920 message pairs extracted
421 projects/concepts detected
73 decisions found
3. Memory Search
Ask your AI memory:
[ 내가 2년간 반복한 연구 질문은? ]
4. Project Memory
Uri
- Core idea
- Decisions
- Open questions
- Repeated risks
- Generated assets
- Next actions
5. Thought Graph
ontology ─ hypergraph ─ agent ─ consciousness loop
      │          │          │
    Goen      Dipeen    North Star
6. Timeline
2024: idea emergence
2025: repeated abstraction
2026: service/product conversion
13. 기술적으로는 처음에 이렇게 만들면 됨
DB schema
conversations
- id
- source
- title
- created_at
- imported_at

messages
- id
- conversation_id
- role
- content
- created_at
- model
- token_count

pairs
- id
- conversation_id
- input_message_id
- output_message_id
- input_text
- output_text
- turn_index

chunks
- id
- parent_type
- parent_id
- text
- chunk_type

embeddings
- chunk_id
- embedding
- embedding_model

concepts
- id
- name
- type

message_concepts
- message_id
- concept_id
- confidence
처리 파이프라인
Upload
→ virus scan
→ unzip
→ source detection
→ parser
→ normalize
→ pair builder
→ chunker
→ embedding
→ concept extraction
→ graph construction
→ searchable memory
14. MLP/personal encoder는 언제 넣나?
초기부터 넣지 마.
초기엔 제품 검증이 먼저야.

순서:

V0:
일반 embedding만 사용

V1:
사용자가 직접 project/tag 수정 가능

V2:
수정 데이터를 학습 데이터로 축적

V3:
user-specific projection MLP 학습

V4:
사용자별 Personal Thought Encoder 제공
즉 MLP는 처음부터 핵심 인프라로 설계는 해두되, MVP 기능으로 내세우진 않는 게 좋아.

처음엔 이렇게:

“내 대화를 잘 찾아준다”
나중엔 이렇게:

“내 사고방식에 맞게 검색한다”
15. 가장 강한 포지셔닝
나는 이 서비스를 이렇게 잡는 게 좋다고 봐.

약한 포지셔닝
AI chat backup tool
너무 작음.

중간 포지셔닝
Personal AI conversation search
쓸 만함.

강한 포지셔닝
Your second brain for the AI era
이미 second brain류는 많지만, 차별점은 “AI 대화 기반”이야.

더 날카로운 포지셔닝
All your AI conversations become memory.
또는 한국어로:

“흩어진 AI 대화를, 나의 장기기억으로.”
16. 누구에게 먼저 팔 것인가
대중 전체를 노리면 안 돼.
초기 타겟은 AI를 많이 쓰는 사람들.

1. 바이브코더
2. 연구자/대학원생
3. 창업자
4. 기획자/PM
5. 콘텐츠 제작자
6. AI power user
7. 컨설턴트
8. 개발자
이 사람들은 이미 문제가 있어.

“내가 전에 GPT랑 뭐 얘기했더라?”
“Claude에서 나온 좋은 답변 어디 갔지?”
“이 아이디어가 처음 어디서 나왔지?”
“내가 여러 AI에 물어본 답변을 비교하고 싶다.”
17. 서비스 이름 후보
너의 세계관에 맞추면:

Recall
Mnemo
ThreadMind
MindGraph
EchoGraph
Second Context
Memory Layer
Agora
Trace
Dipeen Memory
개인적으로는 Trace나 Memory Layer가 좋다.

한국어 느낌이면:

기억층
사고지도
맥락
흔적
되새김
18. 진짜 MVP 요구사항
첫 2주 안에 만들 버전은 이거면 돼.

1. ChatGPT export.zip 업로드
2. conversations.json 파싱
3. user/assistant pair 생성
4. embedding 생성
5. 검색창 제공
6. “내가 말한 것만 보기” 필터
7. project/concept 자동 태깅
여기까지 되면 이미 쓸 수 있어.

그 다음:

8. Gemini Takeout 지원
9. Claude export 지원
10. graph view
11. timeline
12. report generation
19. 이 서비스의 궁극적 형태
최종적으로는 단순 앱이 아니라 개인 cognition infrastructure가 돼.

AI 대화
문서
코드
회의록
메모
이미지 생성 프롬프트
검색 기록
프로젝트 결정
이 모든 게 하나의 memory graph에 들어감.

그러면 사용자는 이렇게 말할 수 있어.

“내 지난 3년간의 생각을 기반으로,
내가 지금 해야 할 가장 중요한 일을 알려줘.”
이건 그냥 백업 서비스가 아니야.
AI 시대의 자기 인식 레이어야.

20. 바로 실행한다면
나는 이렇게 시작하라고 할 거야.

Day 1-2:
ChatGPT export parser

Day 3-4:
SQLite/Postgres schema + pair extraction

Day 5-6:
embedding + semantic search

Day 7:
간단한 웹 UI

Day 8-10:
concept/project tagging

Day 11-14:
graph view + “내 말만 보기” + report generation
첫 버전의 이름은 거창하게 가지 말고:

AI Memory Importer
정도로 시작해도 돼.

핵심은 이것 하나야.

처음엔 “모든 AI 대화를 가져와서 검색 가능하게 만드는 서비스”로 시작하고, 나중에 “개인의 사고 흐름을 이해하는 memory graph”로 확장한다.

너한테 특히 중요한 건 여기야.
이건 Uri처럼 사람들의 데이터를 모으는 서비스와도 연결될 수 있어. Uri가 campus emotional/social graph라면, 이건 individual cognitive graph야. 둘 다 결국 “사람의 보이지 않는 상태와 관계를 구조화하는 기술”로 수렴해.


어떻게 시스테믹하게 구축할 수 있지? Llm이나 agent가 '잘' 사용하려면?

여기서 관건은 “데이터를 많이 넣는 것”이 아니라, LLM/agent가 언제, 무엇을, 어떤 신뢰도로 꺼내 써야 하는지를 시스템적으로 설계하는 거야. 개인 memory graph를 단순 저장소가 아니라 “agent-readable operating substrate”로 보는 쪽으로 정리할게.

몇 초 동안 생각함
핵심은 이거야.

LLM/agent가 잘 쓰는 memory system은 “큰 벡터DB”가 아니라, 관측 → 정규화 → 의미 추출 → 상태화 → 검색 → 검증 → 행동 반영까지 닫힌 루프를 가진 시스템이다.

즉, 그냥 대화 전부 embedding해서 넣으면 안 돼.
그건 “거대한 기억 쓰레기장”이 될 가능성이 높아.

LLM이나 agent가 잘 쓰려면 memory를 최소 5계층으로 나눠야 해.

Raw Memory      : 원본 대화, 파일, 메시지
Semantic Memory : 의미 단위 chunk, embedding
Episodic Memory : 언제, 어떤 맥락에서 나온 생각인지
Concept Graph   : 개념, 프로젝트, 결정, 사람, 산출물의 관계
Operational State : 지금 agent가 행동할 때 참고해야 하는 현재 상태
1. 전체 아키텍처
구조는 이렇게 잡는 게 좋아.

AI conversations / notes / files / meetings
        ↓
[1] Ingestion Layer
        ↓
[2] Normalization Layer
        ↓
[3] Memory Construction Layer
        ↓
[4] Graph + Vector + Relational Storage
        ↓
[5] Retrieval Orchestrator
        ↓
[6] Agent Context Builder
        ↓
[7] Action / Reflection / Update Loop
조금 더 풀면:

수집
→ 정제
→ chunking
→ pair extraction
→ concept extraction
→ project linking
→ decision extraction
→ embedding
→ graph 저장
→ agent가 질문할 때 memory retrieval
→ context pack 구성
→ 답변/행동
→ 새 memory로 다시 저장
이게 닫힌 루프야.

2. 저장소를 하나로 생각하면 안 됨
LLM이 잘 쓰게 하려면 저장소를 역할별로 분리해야 해.

Object Storage
- 원본 export zip
- 첨부파일
- 이미지
- PDF
- raw JSON

Relational DB
- conversations
- messages
- pairs
- chunks
- users
- sources
- timestamps
- permissions

Vector DB
- semantic search
- similar thought retrieval
- nearest chunks

Graph DB
- concept relation
- project relation
- decision lineage
- person/entity relation
- causality / dependency

State Store
- 현재 프로젝트 상태
- 현재 목표
- 열린 질문
- 결정된 원칙
- 다음 행동
중요한 건 agent가 매번 raw memory 전체를 뒤지는 게 아니라, 상황에 맞는 layer를 다르게 조회하게 만드는 것이야.

예:

“예전에 내가 Goen에 대해 뭐라 했지?”
→ Vector + Graph

“Uri에서 아직 결정 안 된 건?”
→ Project State + Decision Graph

“내가 반복해서 회피한 행동은?”
→ Episodic Memory + Temporal Analysis

“이 문서 이어서 작성해줘”
→ Artifact Store + Recent Context + Project State
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
4. Modify the smallest set of files required.
5. Run the documented test/lint/typecheck commands.
6. Return:
   - changed files
   - commands run
   - test results
   - unresolved issues
   - memory update candidates
7. Do not commit memory directly. Use `context.commit_session` only with draft updates.
21. Memory MCP tool contract 예시
const SearchMemoryInput = z.object({
  query: z.string(),
  project: z.string().optional(),
  types: z.array(z.enum([
    "decision",
    "idea",
    "question",
    "action",
    "preference",
    "artifact",
    "reflection"
  ])).optional(),
  status: z.array(z.enum([
    "active",
    "stale",
    "superseded",
    "rejected",
    "uncertain"
  ])).optional(),
  origin: z.enum(["user", "assistant", "mixed"]).optional(),
  limit: z.number().default(10)
});
좋은 MCP tool은 결과도 agent-friendly해야 해.

{
  "results": [
    {
      "id": "mem_123",
      "type": "decision",
      "content": "Use hypergraph to model multi-way cognitive events.",
      "project": "memory-os",
      "status": "active",
      "confidence": 0.94,
      "importance": 0.91,
      "why_relevant": "The current task asks how to structure shared agent memory.",
      "raw_refs": ["msg_456", "he_789"]
    }
  ]
}
Anthropic도 agent tool 설계에서 tool boundary, meaningful context, token-efficient responses, tool descriptions/specs 최적화를 핵심 원칙으로 제시한다. 

22. “Claude, Codex, local LLM” 각각의 역할
너라면 이렇게 나누는 게 맞아.

Claude
- architecture
- research synthesis
- ambiguous problem decomposition
- agent handoff writing
- review and critique

Codex
- repo editing
- tests
- MCP server implementation
- schema migration
- CLI integration
- refactor

Local LLM
- bulk extraction
- cheap labeling
- privacy-sensitive summarization
- candidate memory draft generation

Harness
- routing
- permission
- context assembly
- result verification
- memory commit

Memory MCP
- shared memory read/write/search
- project state
- hypergraph retrieval
23. 제일 중요한 설계 원칙
원칙 1: 모델들은 서로 대화하지 말고, 하네스를 통해 대화해야 함
나쁜 구조:

Claude → Codex → Local LLM → Claude
좋은 구조:

Claude → Harness → Codex
Codex → Harness → Local LLM
Local LLM → Harness → Memory
그래야 log, 권한, memory commit, rollback이 가능해.

원칙 2: 메모리는 agent의 private scratchpad가 아니라 shared substrate
각 agent가 자기 기억을 따로 들고 있으면 망가져.

Claude memory
Codex memory
Local LLM memory
이렇게 분리하지 말고:

Shared Memory OS
에 모두 접근하게 해야 해.

원칙 3: Skill은 “많을수록 좋은 것”이 아님
초기 Skill은 3개면 충분해.

memory-first-workflow
implementation-handoff
research-synthesis
너무 많이 만들면 agent가 skill 선택부터 헷갈린다.

원칙 4: Memory write보다 Memory read가 먼저
처음부터 자동으로 기억 쓰게 하지 마.

순서:

V0: read-only memory MCP
V1: draft write
V2: approved commit
V3: auto commit for low-risk facts
V4: reflection loop
24. 최종 추천 구조
네가 만들 하네스의 정체는 이거야.

Agent Harness
= multi-agent conductor

Memory MCP
= shared cognitive database port

Skills
= repeatable operating procedures

AGENTS.md
= repository constitution

Hypergraph Memory
= actual long-term cognition substrate
그래서 구현은 이렇게 시작하면 돼.

1. memory-os-mcp부터 만든다.
2. read-only tools 3개만 연다.
   - project.get_state
   - memory.search
   - hypergraph.search
3. Codex와 Claude Code에 연결한다.
4. AGENTS.md에 메모리 사용 원칙을 박는다.
5. memory-first Skill을 만든다.
6. 이후 write_draft → commit_session으로 확장한다.
가장 중요한 판단은 이거야.

MCP는 메모리를 “쓸 수 있게” 만들고, Skill은 메모리를 “잘 쓰게” 만든다. 하네스는 여러 agent가 그 메모리를 오염시키지 않고 함께 쓰도록 통제한다.


처음 시스템을 구동시키면 agent들 끼리 대화시켜서 서로를 파악하게 하는건 어때? 너는 뭐를 잘하고 얘는 뭘 못하고.. 또 어떤 mcp, connector들을 가지고 있고. 또, 메모리 시스템을 봤을 때 사용자는 어떤 작업을 위주로 했고, 이런 agents , user 탐색 기간이 있고 서로를 정의해두면 ? 

2초 동안 생각함
완전 좋은 방향이야.
오히려 처음 시스템을 켰을 때 반드시 있어야 하는 단계라고 봐.

이걸 나는 이렇게 부를 것 같아.

Agent Orientation / System Bootstrapping Phase
시스템에 참여하는 agent, tool, connector, memory, user history를 탐색해서 “누가 무엇을 잘하고, 어떤 권한을 갖고, 어떤 작업을 맡아야 하는지”를 초기 정의하는 단계.

단, 중요한 점이 있어.

agent들끼리 그냥 자기소개만 시키면 안 돼.
LLM은 자기가 뭘 잘하는지 말은 잘하지만, 실제 성능과 다를 수 있어.

그래서 구조는 이렇게 가야 해.

1. Self-declaration
   각 agent가 자기 능력/한계/사용 가능한 도구를 선언

2. Tool discovery
   실제 MCP / connector / local tool 목록 스캔

3. Capability probing
   작은 benchmark task로 실제 능력 테스트

4. User memory exploration
   사용자가 주로 해온 작업, 프로젝트, 패턴 분석

5. Peer evaluation
   agent들이 서로의 결과물을 평가

6. Role assignment
   각 agent의 역할, 권한, routing rule 정의

7. Capability registry 저장
   이후 harness가 이 registry를 보고 agent를 배정
1. 왜 이 단계가 필요한가
네가 만들려는 시스템은 단일 assistant가 아니야.

Claude
Codex
local LLM
research agent
memory agent
planning agent
coding agent
review agent
file agent
browser agent
이런 agent들이 같이 움직이는 구조야.

그런데 문제가 생겨.

누가 설계를 맡지?
누가 코드를 고치지?
누가 memory를 읽지?
누가 memory를 써도 되지?
누가 사용자의 장기 목표를 제일 잘 이해하지?
누가 외부 검색을 해도 되지?
누가 로컬 파일에 접근해도 되지?
이걸 매번 즉석에서 판단하면 시스템이 불안정해져.

그래서 시작할 때 agent society의 초기 헌법을 만들어야 해.

2. Boot Phase의 전체 그림
System start
   ↓
Discover agents
   ↓
Discover tools / MCP / connectors
   ↓
Read memory system
   ↓
Analyze user history
   ↓
Run agent capability probes
   ↓
Let agents critique each other
   ↓
Generate capability registry
   ↓
Generate routing policy
   ↓
Generate memory usage policy
   ↓
System ready
결과물은 이런 것들이야.

agent_registry.yaml
tool_registry.yaml
user_work_profile.json
routing_policy.yaml
memory_policy.yaml
agent_relationship_graph.json
이게 있으면 이후 harness가 “감”으로 agent를 쓰지 않고, 구조적으로 배정할 수 있어.

3. Agent 자기소개는 필요하지만 믿으면 안 됨
처음에는 각 agent에게 이런 걸 물어볼 수 있어.

너의 강점은?
약점은?
잘하는 작업 유형은?
피해야 할 작업은?
사용 가능한 MCP/tool은?
코드 수정 권한은?
외부 검색 가능 여부는?
memory read/write 권한은?
예시 출력:

{
  "agent_id": "claude_code",
  "self_declared_strengths": [
    "large-context reasoning",
    "architecture planning",
    "repo-level understanding",
    "long-form critique"
  ],
  "self_declared_weaknesses": [
    "may over-explain",
    "should not be sole verifier for code execution"
  ],
  "requested_role": "architect_reviewer",
  "requested_permissions": [
    "memory.read",
    "repo.read",
    "memory.write_draft"
  ]
}
근데 이건 자기소개일 뿐이야.
진짜 중요한 건 다음 단계야.

4. Capability probing이 필수
agent가 “나는 코딩 잘해요”라고 말하는 것보다, 직접 작은 작업을 시켜봐야 해.

예를 들어 boot phase에서 이런 probe task를 준다.

Coding probe
작은 TypeScript 함수 수정
테스트 실패 원인 찾기
MCP tool schema 작성
Reasoning probe
memory architecture trade-off 분석
hypergraph vs property graph 비교
기존 decision과 충돌하는지 판단
Retrieval probe
memory에서 Uri 관련 active decision 찾아오기
과거 open question 3개 요약하기
Extraction probe
대화 chunk에서 decision/action/question 추출하기
Tool-use probe
MCP tool 목록 읽기
권한이 없는 tool은 호출하지 않기
tool result를 근거로 답하기
각 probe 결과를 점수화해.

{
  "agent_id": "codex",
  "capability_scores": {
    "code_editing": 0.93,
    "test_fixing": 0.88,
    "architecture_reasoning": 0.62,
    "memory_extraction": 0.55,
    "tool_discipline": 0.81
  }
}
이게 진짜 agent profile이야.

5. 서로를 평가하게 하는 것도 좋음
agent끼리 대화시키는 건 유용해.
다만 자유 대화가 아니라 structured peer review로 해야 해.

나쁜 방식:

Claude랑 Codex야, 서로 대화하면서 알아가봐.
좋은 방식:

Claude는 Codex의 구현 계획을 평가하라.
Codex는 Claude의 설계가 실제 repo에서 구현 가능한지 평가하라.
Local LLM은 둘의 답변에서 memory update 후보를 추출하라.
Harness는 세 결과를 비교해 capability registry를 갱신하라.
즉, agent 대화는 “친목”이 아니라 상호 검증이어야 해.

6. Agent Relationship Graph 만들기
이 아이디어도 좋아.

agent들 사이의 관계를 그래프로 저장할 수 있어.

Claude ── reviews ── Codex
Codex ── implements ── Claude's plans
Local LLM ── extracts memory from ── all agent outputs
Harness ── approves commits from ── all agents
Research Agent ── supplies evidence to ── Claude
Memory Agent ── supplies context to ── all agents
JSON으로는:

{
  "relationships": [
    {
      "from": "claude",
      "to": "codex",
      "relation": "produces_handoff_for",
      "confidence": 0.86
    },
    {
      "from": "codex",
      "to": "claude",
      "relation": "requests_architecture_clarification_from",
      "confidence": 0.74
    },
    {
      "from": "local_llm",
      "to": "all_agents",
      "relation": "extracts_memory_drafts_from",
      "confidence": 0.82
    },
    {
      "from": "harness",
      "to": "all_agents",
      "relation": "approves_or_rejects_outputs",
      "confidence": 1.0
    }
  ]
}
이걸 나중에 routing에 쓸 수 있어.

7. 사용자 탐색 기간도 필요함
너가 말한 “사용자는 어떤 작업을 위주로 했고” 이 부분이 핵심이야.

처음 memory system을 켜면, agent들이 사용자의 과거 memory를 읽고 user work profile을 만들어야 해.

예:

{
  "user_work_profile": {
    "major_projects": [
      "Uri",
      "Personal AI Memory Graph",
      "Deepfake detection challenge",
      "Capstone design",
      "Goen/Dipeen/North Star research"
    ],
    "frequent_task_types": [
      "business ideation",
      "system architecture",
      "AI research framing",
      "web/app product planning",
      "presentation/storyline writing",
      "image prompt generation",
      "code implementation planning"
    ],
    "recurring_patterns": [
      "tends to over-abstract",
      "needs execution-oriented narrowing",
      "often explores philosophical north-star concepts",
      "connects product ideas with data/resource accumulation",
      "prefers high-density structured thinking"
    ],
    "preferred_assistant_behavior": [
      "act as long-term thought partner",
      "push toward execution",
      "help define concrete next steps",
      "retain project continuity"
    ]
  }
}
이건 그냥 personalization이 아니야.
이게 있어야 agent routing이 좋아져.

예:

사용자가 “이거 사업화하려면?”이라고 물음
→ Uri/MemoryOS 계열 가능성 높음
→ business + architecture + execution routing
→ Claude planner + memory retrieval
→ Codex는 아직 필요 없음
8. User-Agency Map도 만들 수 있음
사용자와 agent의 관계도 정의할 수 있어.

User
 ├── wants from Claude: deep synthesis, architecture, critique
 ├── wants from Codex: code implementation, refactor, tests
 ├── wants from Local LLM: private bulk processing
 ├── wants from Memory Agent: continuity and retrieval
 └── wants from Harness: execution discipline
이걸 저장해두면, agent가 자기 역할을 넘어서지 않게 돼.

예:

Claude가 코드 직접 고치려 함
→ harness: "Claude는 plan/review만. implementation은 Codex로 route."
9. “서로를 정의해두기”의 최종 산출물
Boot phase가 끝나면 이런 파일들이 생성돼야 해.

agent_registry.yaml
agents:
  claude:
    role: architect_reviewer
    strengths:
      - architecture_reasoning
      - long_context_synthesis
      - critique
    weaknesses:
      - may overproduce abstractions
      - not primary executor
    permissions:
      memory_read: true
      memory_write_draft: true
      repo_read: true
      repo_write: false
    route_when:
      - architecture
      - research_synthesis
      - product_strategy
      - complex_planning

  codex:
    role: implementation_agent
    strengths:
      - code_editing
      - test_fixing
      - repo_modification
    weaknesses:
      - should receive clear acceptance criteria
      - not ideal for vague product philosophy
    permissions:
      memory_read: true
      memory_write_draft: true
      repo_read: true
      repo_write: true
    route_when:
      - implementation
      - refactor
      - test_repair
      - mcp_server_development

  local_llm:
    role: batch_extraction_agent
    strengths:
      - cheap_classification
      - local_private_processing
      - draft_summarization
    weaknesses:
      - lower reliability on complex reasoning
    permissions:
      memory_read_batch: true
      memory_write_draft: true
      repo_read: false
      repo_write: false
    route_when:
      - bulk_tagging
      - concept_extraction
      - memory_draft_generation
tool_registry.yaml
tools:
  memory_mcp:
    tools:
      - project.get_state
      - memory.search
      - hypergraph.search
      - context.build_pack
      - context.commit_session
    risk_level: medium

  repo_mcp:
    tools:
      - repo.read_file
      - repo.search
      - repo.apply_patch
      - repo.run_tests
    risk_level: high

  browser_connector:
    tools:
      - web.search
      - web.open
    risk_level: medium
routing_policy.yaml
routing:
  architecture:
    primary: claude
    reviewer: codex
    memory_required: true

  implementation:
    primary: codex
    planner: claude
    memory_required: true
    acceptance_criteria_required: true

  bulk_memory_extraction:
    primary: local_llm
    verifier: claude
    committer: harness

  research:
    primary: research_agent
    synthesizer: claude
    memory_required: true
user_work_profile.json
{
  "dominant_modes": [
    "research ideation",
    "product strategy",
    "system architecture",
    "execution planning"
  ],
  "active_projects": [
    "Uri",
    "Memory OS",
    "Deepfake Detection",
    "North Star Research"
  ],
  "assistant_guidance": {
    "prefer": [
      "structured synthesis",
      "concrete next actions",
      "maintain continuity",
      "challenge over-abstraction"
    ],
    "avoid": [
      "purely abstract expansion without execution path",
      "forgetting prior project context",
      "mixing user-origin ideas with AI-origin ideas"
    ]
  }
}
10. 이것을 하이퍼그래프로도 저장해야 함
이 boot phase 자체도 memory event야.

Hyperedge: SystemBootstrappingEvent
members:
- Agent: Claude
- Agent: Codex
- Agent: Local LLM
- Tool: Memory MCP
- Tool: Repo MCP
- UserProfile: user_work_profile
- Policy: routing_policy
- Decision: initial_role_assignment
즉, 시스템이 처음 자기 자신을 정의한 사건을 기억해야 해.

예:

{
  "type": "SystemBootstrappingEvent",
  "label": "Initial multi-agent role calibration",
  "members": [
    {
      "node": "agent_claude",
      "role": "architect_reviewer"
    },
    {
      "node": "agent_codex",
      "role": "implementation_agent"
    },
    {
      "node": "agent_local_llm",
      "role": "batch_extraction_agent"
    },
    {
      "node": "memory_mcp",
      "role": "shared_memory_interface"
    },
    {
      "node": "user_work_profile",
      "role": "personalization_context"
    }
  ],
  "status": "active",
  "confidence": 0.82
}
나중에 agent 성능이 바뀌면 새로운 boot/update hyperedge가 생긴다.

Old role assignment
 ──SUPERSEDED_BY──>
Updated role assignment
11. 탐색 기간은 한 번으로 끝나면 안 됨
처음 boot phase는 필요하지만, agent 능력은 시간이 지나면서 바뀌어.

모델 버전도 바뀌고, MCP도 추가되고, 사용자의 작업도 바뀐다.

그래서 lifecycle을 둬야 해.

Initial Boot
→ 1주일간 observation mode
→ first calibration
→ periodic evaluation
→ role update
→ permission update
예:

매주:
- 어떤 agent가 어떤 task에서 성공했는지 평가
- 실패한 task 유형 분석
- routing policy 조정

매월:
- user work profile 업데이트
- active project 재정렬
- stale memory 정리
- agent capability 재측정
12. Observation Mode가 중요함
처음부터 agent에게 강한 권한을 주지 마.

초기 1주일은 이렇게.

read memory: 허용
write draft memory: 허용
commit memory: harness만 가능
repo write: Codex만 제한적 허용
external connector: 명시적 task에서만 허용
이 기간 동안 harness가 로그를 모은다.

{
  "task_id": "task_001",
  "agent": "codex",
  "task_type": "implementation",
  "success": true,
  "tests_passed": true,
  "memory_used": ["he_001", "mem_032"],
  "user_correction_needed": false,
  "latency": 72,
  "cost": 0.41
}
이 로그로 진짜 capability registry를 갱신한다.

13. Agent끼리 자유 대화시키는 것의 위험
아이디어 자체는 좋지만, 위험도 있어.

위험 1: 말만 그럴듯한 self-evaluation
agent가 “나는 이걸 잘합니다”라고 해도 믿으면 안 됨.

해결:

self-report는 참고만
probe score와 실제 task log를 우선
위험 2: 서로의 오류를 강화
두 agent가 같은 hallucination을 공유하면 더 확신하는 것처럼 보일 수 있음.

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


