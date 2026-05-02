<!--
Source: docs/memoryOS.md
Source lines: 701-1400
Source byte range: 22557-42383
Split title source: first-text
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 002: 구조적으로는:

Provenance: `docs/memoryOS.md` lines `701-1400`, bytes `22557-42383`.

Local structure markers:

- Source line 714: 15. 가장 현실적인 첫 실험
- Source line 761: 1. 서비스의 본질
- Source line 774: 2. 제품을 한 문장으로 정의하면
- Source line 780: 3. MVP는 작게 가야 함
- Source line 807: 4. MVP 핵심 기능
- Source line 810: 1. AI 대화 export 업로드
- Source line 811: 2. 대화 자동 파싱
- Source line 812: 3. 입력-출력 pair 생성
- Source line 813: 4. 의미 검색
- Source line 814: 5. 프로젝트/개념 그래프 보기
- Source line 817: 1. “Upload your AI exports”
- Source line 818: 2. “We found 3,482 conversations”

---

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
