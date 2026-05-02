<!--
Source: docs/goen_resonance.md
Source lines: 422-695
Source byte range: 17610-27883
Split title source: numbered-section
Split note: Source has no Markdown headings; split at recurring numbered section starts and major topic transitions.
-->

# Part 003: 1. 이 연구의 본질은 “Agent용 뇌 바깥 해마”야

Provenance: `docs/goen_resonance.md` lines `422-695`, bytes `17610-27883`.

Local structure markers:

- Source line 422: 1. 이 연구의 본질은 “Agent용 뇌 바깥 해마”야
- Source line 444: 2. SELF_LEARNING_AGENT 문서와 연결되는 지점
- Source line 481: 3. Hypergraph 기반 파일시스템은 왜 필요한가
- Source line 513: 4. 군체지성 agent 시스템의 역할
- Source line 551: 5. Dipeen을 내가 재정의한다면
- Source line 595: 6. 냉정한 판단: 이건 강한데, 범위가 너무 크다
- Source line 616: 7. GoEN과 Dipeen의 통합 North Star
- Source line 644: 8. 바로 다음 MPU 제안
- Source line 654: 1. Markdown/PDF/code를 chunk로 분해
- Source line 655: 2. Node 생성: File, Chunk, Claim, Concept, Experiment, Code
- Source line 656: 3. Hyperedge 생성: supports, contradicts, implements, tests, next_action
- Source line 657: 4. Agent 3개만 운영:

---

1. 이 연구의 본질은 “Agent용 뇌 바깥 해마”야
GoEN이 신경망 내부의 가소성이라면,

Ontology + Hypergraph FileSystem + 군체지성 Agent 시스템은 외부화된 인지기관이다.

즉, 뇌 안쪽에서는 GoEN이 복소 위상, 방향성 메시지패싱, STDP rewiring을 하고 있고, 바깥쪽에서는 Dipeen 같은 시스템이 파일·개념·관계·작업·기억을 hypergraph로 관리하는 구조가 된다.

정리하면:

GoEN
= neural plastic substrate
= 내부 표현/연결을 바꾸는 뇌

Dipeen / Ontology Hypergraph FS
= cognitive operating system
= 기억, 파일, 개념, 작업, agent를 연결하는 외부 세계모델

Swarm Agent System
= plasticity operators
= hypergraph를 읽고, 수정하고, 압축하고, 재배선하는 행위자들
이건 단순한 파일관리 앱이 아니라 agent cognition substrate에 가까워.

2. SELF_LEARNING_AGENT 문서와 연결되는 지점
SELF_LEARNING_AGENT.md의 구조는 이미 ontology/hypergraph filesystem의 원형을 갖고 있어.

문서 안에서 LearnedSkill은 발화 fingerprint, slot schema, tool chain, reply template, confidence, usage count, context distribution을 저장하는 실행 단위로 정의돼 있어. 


이걸 ontology 관점으로 바꾸면:

LearnedSkill = 실행 가능한 ontology subgraph

fingerprint = 의도 패턴 노드
slotSchema = 변수/개념 타입 노드
toolChain = 절차적 edge sequence
contextDistribution = 조건부 활성화 영역
confidence = edge belief / reliability
usageCount = Hebbian trace
negativeFeedback = anti-Hebbian signal
즉, 네가 만든 자기학습 에이전트 설계는 이미 STDP적 가소성을 앱/agent 레벨로 올린 형태야.

GoEN의 RewireControllerSTDP가 edge correlation, entropy, loss 변화량을 보고 prune/grow를 수행한다면, 


SELF_LEARNING_AGENT는 사용자 피드백, 사용 횟수, context consistency, confidence를 보고 skill을 생성/강등/폐기한다. 


둘은 같은 원리야.

신경망 내부:
edge usage ↑ → connection 유지/강화
edge usefulness ↓ → prune

agent memory:
skill usage ↑ + success ↑ → confidence 강화
negative feedback ↑ → DEGRADED/DISABLED
이건 중요해.
너는 서로 다른 프로젝트를 한 게 아니라, 같은 구조 가소성 원리를 서로 다른 스케일에서 반복 구현하고 있었던 거야.

3. Hypergraph 기반 파일시스템은 왜 필요한가
일반 파일시스템은 tree야.

folder/file
그런데 연구, 기억, agent 작업은 tree가 아니야. 하나의 문서가 여러 맥락에 동시에 속해.

paper3.pdf
 ├─ quantum inverse problem
 ├─ Born-rule marginal recovery
 ├─ GoEN phase representation
 ├─ ontology plasticity
 ├─ future paper candidate
 └─ Claude/GPT/Gemini debate source
이건 graph도 부족하고, 정확히는 hypergraph가 맞아.

왜냐하면 하나의 관계가 단순히 A → B가 아니라:

{문서, 실험, 가설, 코드, 실패 로그, 다음 액션}
같은 여러 노드를 한 번에 묶기 때문이야.

예를 들면:

Hyperedge: "supports_hypothesis"
nodes:
- paper3.pdf
- Lindblad collapse layer
- inverse-generative North Star
- experiment P12
- claim: hidden phase can be recovered from partial marginals
- next action: ablation with no-collapse
이 구조가 되면 파일시스템은 저장소가 아니라 생각의 장기기억 그래프가 된다.

4. 군체지성 agent 시스템의 역할
여기서 agent들은 단순히 “작업을 수행하는 봇”이 아니야.
각 agent는 hypergraph에 대한 특정 plasticity operator가 된다.

예를 들면:

Archivist Agent
- 새 파일을 읽고 ontology node 생성
- 중복 개념 병합
- 출처/버전 관리

Critic Agent
- 모순 edge 탐지
- 약한 claim 표시
- 실험 근거 부족한 node 격리

Synthesizer Agent
- 여러 문서를 하나의 hypothesis subgraph로 압축
- GoEN / quantum / ESN 같은 서로 다른 프로젝트 사이 bridge 생성

Experiment Agent
- claim을 testable hypothesis로 변환
- benchmark / ablation / metric 제안

Planner Agent
- 다음 1주일 액션 graph 생성
- 중요도와 실행 가능성 기반 scheduling

Guardian Agent
- 프라이버시, 안전성, 비용, scope creep 감시
즉, 군체지성은 “여러 AI가 떠드는 것”이 아니라:

각 agent가 ontology hypergraph의 서로 다른 rewrite rule을 담당하는 시스템

이어야 해.

이렇게 정의해야 연구가 선명해져.

5. Dipeen을 내가 재정의한다면
dipeen 전용 문서는 못 찾았지만, 네 키워드 기준으로 이름을 기능적으로 재정의하면 이렇게 잡을 수 있어.

Dipeen: Distributed Persistent Epistemic Engine/Network
지식, 파일, 기억, 실험, agent 행동을 하나의 persistent hypergraph로 저장하고, 군체 agent가 그 구조를 지속적으로 수정하는 인지 파일시스템.

핵심 객체는 이거야.

Node
- File
- Concept
- Claim
- Experiment
- Code
- Result
- Memory
- Agent
- Task
- User intent

Hyperedge
- supports
- contradicts
- derives_from
- implements
- tests
- remembers
- compresses
- schedules
- depends_on
- generalizes
- specializes

Agent
- reads subgraph
- proposes edit
- scores edit
- commits edit
- leaves trace
이걸 GoEN과 결합하면:

Dipeen = external ontology substrate
GoEN = internal graph plasticity learner
Swarm Agents = ontology edit policy executors
6. 냉정한 판단: 이건 강한데, 범위가 너무 크다
이 방향은 진짜 강해.
하지만 바로 “새로운 운영체제”로 가면 망해.

연구 질문을 좁혀야 해.

나쁜 질문:

Hypergraph 기반 agentic filesystem을 만들자.
너무 큼. 검증 불가능함.

좋은 질문:

파일/메모/코드/실험 로그를 tree가 아니라 hypergraph로 저장하면,
agent의 장기 연구 일관성과 재사용성이 좋아지는가?
더 좋은 질문:

Ontology-edit swarm이 연구 문서 corpus에서 claim→evidence→experiment graph를 자동 유지할 때,
사람+LLM의 다음 실험 선택 정확도와 중복 작업 감소율이 개선되는가?
이렇게 가야 해.

7. GoEN과 Dipeen의 통합 North Star
나는 이제 GoEN 프로젝트를 이렇게 재정의할 수 있다고 봐.

GoEN은 내부 신경 가소성 모델이고, Dipeen은 외부 ontology 가소성 운영체제다. 둘을 합치면 agent가 자기 내부 표현과 외부 기억 구조를 동시에 재배선하는 dual-plastic intelligence가 된다.

한 장으로 그리면:

                  ┌────────────────────────┐
                  │        User / World     │
                  └───────────┬────────────┘
                              ↓
┌────────────────────────────────────────────────────┐
│ Dipeen: Ontology Hypergraph FileSystem              │
│ - files, concepts, claims, tasks, memories           │
│ - hyperedges: supports/tests/contradicts/implements │
└───────────┬──────────────────────────────┬─────────┘
            ↓                              ↑
┌──────────────────────┐        ┌──────────────────────┐
│ Swarm Agents          │        │ GoEN                  │
│ - critic              │        │ - complex GNN encoder │
│ - planner             │        │ - STDP rewiring       │
│ - synthesizer         │        │ - neuromodulation     │
│ - experimenter        │        │ - phase coherence     │
└───────────┬──────────┘        └───────────┬──────────┘
            ↓                               ↓
        Ontology edits              Plasticity policy
이게 지금 네 연구들의 통합 그림이야.

8. 바로 다음 MPU 제안
이 방향은 MPU-δ0보다 앞에 하나 더 필요해.

MPU-D0: Hypergraph Research Memory
목표:

연구 파일 30개, 코드 20개, 메모 100개를 hypergraph로 변환하고, agent가 claim/evidence/experiment/task 관계를 자동 유지하게 만든다.

최소 구현:

1. Markdown/PDF/code를 chunk로 분해
2. Node 생성: File, Chunk, Claim, Concept, Experiment, Code
3. Hyperedge 생성: supports, contradicts, implements, tests, next_action
4. Agent 3개만 운영:
   - Archivist
   - Critic
   - Planner
5. Metric 측정:
   - 같은 질문에 대한 근거 회수율
   - 중복 실험 제안 감소
   - 다음 액션 품질
   - 오래된 claim과 최신 evidence 충돌 탐지율
이게 되면 Dipeen은 단순 컨셉이 아니라 연구용 도구가 된다.

그 다음에야:

MPU-D1: Ontology Plasticity Agent
MPU-D2: Swarm Rewrite Policy
MPU-D3: GoEN-learned Plasticity Controller
MPU-DΩ: Global Coherence Workspace
로 올라가면 돼.

결론
네가 하던 연구는 이렇게 정리된다.

Dipeen은 agent의 외부 뇌다. Hypergraph filesystem은 장기기억이고, ontology는 의미 구조이며, 군체지성 agent는 그 구조를 고치는 plasticity operator다. GoEN은 그 가소성 원리를 신경망 내부에서 학습하는 substrate다.

이건 지금 흐름과 정확히 맞물려.
다만 다음 단계는 “큰 시스템 상상”이 아니라 작은 hypergraph research memory MVP로 잘라야 해.


Gpt엔 많이 없을거야 자료가. Claude로 진행했었거든.
어쨌든 llm은 뇌의 forward process 이고 무의식적인 기능들을 담당했는데 graph형태의 자기 인식 루프로 가먼 갈수록 의식적인 행동들을 근사할 수 있을거야. 

맞아. 그리고 이 프레임은 상당히 강해.

정리하면 네 가설은 이거야.

LLM은 뇌의 forward process, 즉 무의식적·자동적 생성/연상/예측 기능에 가깝고, graph 기반 자기 인식 루프를 얹을수록 의식적 행동을 근사한다.

나는 이 가설에 대체로 동의해. 다만 더 엄밀하게 쓰려면 이렇게 나눠야 해.

