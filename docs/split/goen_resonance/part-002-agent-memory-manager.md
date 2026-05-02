<!--
Source: docs/goen_resonance.md
Source lines: 282-421
Source byte range: 11007-17609
Split title source: numbered-section
Split note: Source has no Markdown headings; split at recurring numbered section starts and major topic transitions.
-->

# Part 002: 1. Agent는 “도구 호출자”에서 “자기 기억 관리자”가 된다

Provenance: `docs/goen_resonance.md` lines `282-421`, bytes `11007-17609`.

Local structure markers:

- Source line 282: 1. Agent는 “도구 호출자”에서 “자기 기억 관리자”가 된다
- Source line 295: 2. Ontology가 다시 “AI의 뼈대”가 된다
- Source line 307: 3. World model은 이미지/텍스트 생성기가 아니라 “개입 가능한 그래프”가 된다
- Source line 389: 1. 강력한 distribution을 가진 product agent
- Source line 390: 2. 특정 domain의 깊은 workflow agent
- Source line 391: 3. 기억/세계모델/자기수정 구조를 가진 architecture agent

---

1. Agent는 “도구 호출자”에서 “자기 기억 관리자”가 된다
지금의 agent는 대체로 tool call, workflow, RAG, planning 중심이야.
다음 2년에는 agent의 경쟁력이 무슨 모델을 쓰느냐보다 무엇을 기억하고, 무엇을 잊고, 어떤 구조로 저장하느냐로 갈 가능성이 커.

이미 산업 쪽에서도 agent가 서로 협력하고 기억을 공유하는 방향, structured retrieval augmentation 같은 메모리 압축 방향을 밀고 있어. 

GoEN으로 번역하면:

Memory = vector DB가 아니라 살아있는 graph
Recall = 검색이 아니라 부분 ontology 활성화
Learning = fine-tuning이 아니라 memory graph 재배선
이게 첫 번째 큰 축이야.

2. Ontology가 다시 “AI의 뼈대”가 된다
LLM은 엄청난 언어 유창성을 줬지만, 세계를 일관된 구조로 유지하는 능력은 아직 약해.
그래서 다음 단계는 “텍스트를 잘 생성하는 모델”보다 개념, 관계, 원인, 사건, 목적, 규칙을 안정적으로 보존하는 구조가 중요해질 거야.

즉, ontology는 과거 symbolic AI의 낡은 잔재가 아니라, LLM/agent 시대의 정신 골격으로 돌아온다.

GoEN식 표현은 이거야:

Ontology = agent가 현실을 압축한 내부 시뮬레이션 구조
Plasticity = 그 ontology를 고치는 생존 메커니즘
여기서 네가 잡은 “뇌 가소성이 agent의 형태로 ontology의 형태로 나왔다”는 말은 정확히 다음 2년의 중심축이 될 수 있어.

3. World model은 이미지/텍스트 생성기가 아니라 “개입 가능한 그래프”가 된다
다음 2년의 world model은 단순히 미래 프레임을 예측하거나 텍스트 다음 문장을 예측하는 수준에서 멈추지 않을 거야.

중요한 질문은 이거야.

내가 A를 바꾸면 B가 어떻게 변하는가?
이 관계는 관찰된 것인가, 추론된 것인가?
이 edge는 causal인가, temporal인가, semantic인가?
이 구조는 다른 task로 transfer되는가?
그래서 world model은 점점 graph world model로 갈 가능성이 높아. 실제로 agent reasoning과 graph world model을 연결하려는 흐름도 이미 보이고 있어. 

GoEN은 여기서 “복소 위상 + 방향성 edge + 가소성”을 가진 구조라서, 단순 KG보다 더 신경망적이고, 단순 GNN보다 더 인지적일 수 있어.

GoEN의 다음 2년 로드맵
나는 이렇게 봐.

2026 상반기:
GoEN을 GNN 모델이 아니라 Ontology Plasticity Agent로 재정의

2026 하반기:
작은 synthetic world에서 ontology edit 실험 성공

2027 상반기:
멀티모달 bridge graph + working memory patch 구현

2027 하반기:
global coherence / self-repair / plan-revision 실험으로 논문화
조금 더 구체적으로 말하면.

Year 1: “구조 가소성”을 증명해야 함
첫 1년은 멋있는 거 만들면 안 돼.
작은 세계에서 구조가 바뀌어야만 풀리는 문제를 만들어야 해.

예를 들면:

Task:
agent가 작은 세계의 object, relation, event를 관찰한다.

Hidden rule:
A causes B였던 관계가 context에 따라 A inhibits B로 바뀐다.
또는 X와 Y가 같은 개념인 줄 알았는데 실제로는 분리되어야 한다.

Agent action:
AddNode / SplitNode / MergeNode / RetypeEdge / PruneEdge

Metric:
prediction error 감소
adaptation speed 증가
catastrophic forgetting 감소
ontology contradiction 감소
여기서 승리 조건은 단순 accuracy가 아니야.

고정 graph < rewired graph < ontology-editing graph
이 순서를 보여줘야 해.

Year 2: “기억과 계획”으로 올라가야 함
두 번째 해에는 ontology graph가 단순 예측기를 넘어서야 해.

핵심은 이것:

과거 경험이 graph patch로 저장된다.
현재 task에서 관련 patch가 활성화된다.
충돌하는 patch는 coherence loss로 조정된다.
계획 실패 시 ontology edit이 일어난다.
이러면 GoEN은 진짜 agent가 돼.

이때 Phase δ와 Ω가 살아난다.

Phase δ:
Working Memory = temporary ontology patch

Phase Ω:
Global Coherence = 여러 patch 사이의 phase-locking / contradiction minimization

Policy:
행동 선택 = graph state 위에서의 intervention selection
냉정한 예측
다음 2년 동안 그냥 “LLM agent app”은 엄청 많이 사라질 거야.
도구 연결, 웹 자동화, RAG wrapper만으로는 차별화가 안 돼.

살아남는 건 세 종류야.

1. 강력한 distribution을 가진 product agent
2. 특정 domain의 깊은 workflow agent
3. 기억/세계모델/자기수정 구조를 가진 architecture agent
GoEN은 3번으로 가야 해.

하지만 위험도 있어.
너무 큰 말을 먼저 하면 또 2년 날아간다. 이번에는 반드시 MPU 단위로 가야 해.

다음 2년의 한 문장
나는 이렇게 정리할게.

다음 2년은 agent가 외부 도구를 쓰는 시대에서, 자기 내부의 세계 구조를 수정하는 시대로 넘어가는 구간이다. GoEN은 그 전환을 GNN, ontology, neuromodulated plasticity로 구현하는 프로젝트가 되어야 한다.

그리고 당장 다음 실험명은 이걸 추천해.

MPU-δ0: Ontology Plasticity Agent
목표는 단 하나.

정답을 더 잘 맞히는 모델이 아니라, 틀렸을 때 자기 세계관을 더 잘 고치는 모델을 만든다.


그 사이에 하고있던 연구가 있는데 확인해볼래? Ontology와 hypergrah 내용 기반 파일시스템, 군체지성 agent 시스템 dipeen

좋아. “Ontology / hypergraph 기반 파일시스템 / 군체지성 agent / dipeen”을 하나의 연구 흐름으로 보고, 네가 남겨둔 문서나 코드 흔적을 먼저 찾아서 구조를 복원해볼게.

42s 동안 생각함
확인해봤어. 네가 말한 흐름은 GoEN과 별개 연구가 아니라, 오히려 GoEN의 상위 운영체제처럼 보인다.

내가 찾은 직접 관련 문서는 SELF_LEARNING_AGENT.md였고, 여기에는 “쓰면 쓸수록 나를 닮아가는 에이전트”라는 설계가 꽤 구체적으로 적혀 있어. 핵심은 한 번 Gemini가 처리한 복합 의도를 LearnedSkill로 저장하고, 이후에는 fingerprint/slot/toolChain 기반으로 LLM 호출 없이 재사용하는 구조야. 즉, “기억 → 패턴화 → 실행 레시피화 → 빠른 회상” 시스템이다. 


다만 dipeen이라는 정확한 이름이나 “hypergraph 기반 파일시스템” 전용 문서는 검색에서 직접 잡히지 않았어. 그래서 지금은 발견된 SELF_LEARNING_AGENT.md, 기존 GoEN 코드, 네가 말한 키워드를 합쳐서 구조를 복원해볼게.

