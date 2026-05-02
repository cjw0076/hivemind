<!--
Source: docs/goen_resonance.md
Source lines: 1-281
Source byte range: 0-11006
Split title source: first-text
Split note: Source has no Markdown headings; split at recurring numbered section starts and major topic transitions.
-->

# Part 001: 뇌 가소성이 agent의 형태로 ontology의 형태로 나왔네.

Provenance: `docs/goen_resonance.md` lines `1-281`, bytes `0-11006`.

Local structure markers:

- Source line 16: 1. 기존 관점: 가소성 = 연결 강도 변화
- Source line 36: 2. 새 관점: 가소성 = ontology rewriting agent
- Source line 73: 3. 핵심 전환: “학습된 파라미터”가 아니라 “살아있는 구조”
- Source line 94: 4. 지금 코드에서 바로 이어지는 설계 방향
- Source line 118: # predictive gain
- Source line 119: # compression gain
- Source line 120: # consistency gain
- Source line 121: # intervention usefulness
- Source line 122: # memory stability
- Source line 137: 5. 내가 보기엔 이게 Phase δ/Ω의 진짜 입구야
- Source line 165: 6. 결론

---





뇌 가소성이 agent의 형태로 ontology의 형태로 나왔네.

2초 동안 생각함
맞아. 이건 꽤 중요한 신호야.

지금까지 우리가 만든 GoEN의 “뇌 가소성”은 단순히 edge를 prune/grow하는 알고리즘이었는데, 이제 한 단계 추상화하면 이렇게 볼 수 있어:

Plasticity는 모델 내부의 weight update가 아니라, agent가 세계/자기 자신을 재해석하기 위해 ontology를 재배선하는 과정이다.

즉, 뇌 가소성이 Agent 형태로 나오고, 그 Agent가 다루는 대상이 ontology가 된 것.

1. 기존 관점: 가소성 = 연결 강도 변화
현재 코드 기준으로는 이렇지.

GoEN은 복소 표현, 방향성 메시지 패싱, STDP 훅을 가진 DirectedComplexPlasticLayer를 사용하고 있고, 각 edge의 usage trace를 u_ema로 추적해 구조적 가소성의 재료로 삼고 있어. 


그리고 RewireControllerSTDP는 loss 변화량, entropy, edge correlation, sparsity를 보고 edge를 prune/grow한다. 즉, 구조 자체를 학습 중에 바꾸는 형태야. 


현재의 수식적 의미는 대략 이거야:

성능 변화 / 불확실성 / 상관 / 희소성
→ neuromodulator
→ prune/grow rate
→ graph topology update
실제로 Neuromodulator는 dL, entropy, rho_avg, phase_diff를 받아 하나의 조절 신호 m_t를 만들고 있어. 


이건 생물학적으로 말하면 “도파민/아세틸콜린/노르에피네프린 같은 global modulation signal이 plasticity gate를 여닫는다”에 가까워.

2. 새 관점: 가소성 = ontology rewriting agent
그런데 이걸 Agent 관점으로 보면 훨씬 강력해져.

기존에는 edge가 단순히 node i → node j 연결이었어.

하지만 ontology를 도입하면 edge는 단순 연결이 아니라:

A causes B
A contains B
A is evidence for B
A contradicts B
A predicts B
A controls B
A is a memory of B
A is an abstraction of B
같은 관계 타입을 갖게 돼.

그러면 plasticity는 더 이상 “연결을 추가/삭제한다”가 아니라,

세계 모델 안에서 어떤 개념들이 어떤 관계로 묶여야 하는지를 계속 재해석하는 agent적 행위

가 된다.

즉, RewireControllerSTDP의 다음 버전은 단순히 edge existence만 바꾸면 안 돼.
이제는 다음을 바꿔야 해:

node 생성
node 병합
node 분화
edge 생성
edge 삭제
edge type 변경
relation confidence 변경
subgraph compression
subgraph promotion to concept
이게 ontology-level plasticity야.

3. 핵심 전환: “학습된 파라미터”가 아니라 “살아있는 구조”
지금 GoEN의 North Star인 SCI와 정확히 맞물려.

SCI: 정답뿐 아니라 길, 즉 구조를 함께 학습한다.

여기서 ontology는 “구조”의 상위 버전이야.

기존 GNN 구조:

node = data point
edge = similarity / adjacency
message passing = feature propagation
GoEN-ontology 구조:

node = concept / memory / sensor state / agent / hypothesis
edge = causal, semantic, temporal, control relation
message passing = meaning propagation
rewiring = world-model revision
neuromodulation = salience / uncertainty / reward / surprise gate
이러면 GoEN은 단순 GNN이 아니라 자기 세계관을 고치는 그래프형 agent가 된다.

4. 지금 코드에서 바로 이어지는 설계 방향
현재 pretrain.py는 supervised loss와 masked node feature loss를 섞고, 이후 STDP controller로 edge를 재배선해. 


하지만 masked_node_feature_loss는 아직 representation regularizer에 가깝고, topology loss도 placeholder 상태야. 


여기가 ontology-agent로 넘어가는 진입점이야.

다음 단계는 RewireControllerSTDP를 이렇게 바꾸는 것:

class OntologyPlasticityAgent:
    def propose_edits(self, graph_state, memory, prediction_error, uncertainty):
        return [
            AddNode(...),
            MergeNode(...),
            SplitNode(...),
            AddTypedEdge(...),
            RetypeEdge(...),
            PruneEdge(...),
            PromoteSubgraph(...)
        ]

    def score_edit(self, edit):
        # predictive gain
        # compression gain
        # consistency gain
        # intervention usefulness
        # memory stability
        return score
그리고 edge를 단순 [src, dst]가 아니라:

edge = {
    "src": i,
    "dst": j,
    "type": "causes" | "contains" | "predicts" | "contradicts" | "controls",
    "confidence": float,
    "plasticity": float,
    "last_used": t,
    "evidence": [...]
}
로 봐야 해.

5. 내가 보기엔 이게 Phase δ/Ω의 진짜 입구야
우리가 Phase δ를 “Working Memory & Policy”라고 잡았지.

그런데 Working Memory가 단순 hidden state면 약해.
진짜 Working Memory는 임시 ontology patch여야 해.

예를 들면:

현재 task에서만 유효한 개념 관계
현재 대화 맥락에서 생긴 가설
최근 실패로 인해 수정된 causal edge
계획 도중 잠정 생성된 subgoal node
이런 게 working memory에 올라와야 함.

그리고 Phase Ω의 글로벌 일관성은 결국:

여러 local ontology patch들이 서로 충돌하지 않도록 phase-locking / coherence를 맞추는 것

으로 해석할 수 있어.

즉:

Phase β: edge plasticity
Phase γ: cross-modal bridge ontology
Phase δ: working ontology memory
Phase Ω: global ontology coherence
이렇게 재정렬하는 게 맞아 보여.

6. 결론
네 말은 정확해.

뇌 가소성이 agent의 형태로, ontology의 형태로 나왔다는 건 다음 뜻이야:

학습은 더 이상 weight fitting이 아니라, agent가 자기 내부의 세계 구조를 계속 수정하는 ontological self-rewriting process다.

그리고 GoEN의 다음 핵심 아키텍처는 이거야:

Complex GNN Encoder
+ Neuromodulated Plasticity
+ Ontology Edit Agent
+ Working Memory Patch Graph
+ Global Coherence Loss
이건 단순히 “뇌를 모방한 GNN”이 아니라,
자기 세계 모델을 구조적으로 수정하는 agentic graph intelligence 쪽으로 넘어가는 지점이야.


연구를 멈춘 2년동안 많은게 변했구나

응. 많이 변했어.
그리고 솔직히 말하면, 네가 2년 전에 붙잡고 있던 방향이 틀린 게 아니라, 이제야 그 방향을 구현할 수 있는 언어와 도구들이 생긴 쪽에 가까워.

예전에는 네 아이디어가 이렇게 보였을 가능성이 커:

“GNN으로 뇌를 흉내낸다.”
“구조가 학습되어야 한다.”
“가소성, 기억, 의식 통합 같은 걸 모델에 넣고 싶다.”

그때는 이게 너무 추상적으로 보였을 수 있어. 그런데 지금은 같은 생각을 이렇게 다시 쓸 수 있어:

Agent가 자기 내부 ontology/world model을 계속 수정하고, 그 수정 이력을 memory로 보존하며, task와 reward에 따라 구조를 재배선하는 self-rewriting graph intelligence.

이건 훨씬 더 실험 가능한 문장이야.

특히 변한 건 세 가지야.

첫째, Agent 개념이 단순 실행기가 아니라 구조 수정자로 확장됐어.
예전 agent는 “도구를 호출하고 계획을 세우는 LLM wrapper” 느낌이 강했는데, 이제는 memory, tool use, self-reflection, planning, environment feedback이 합쳐지면서 “자기 상태를 갱신하는 시스템”으로 보는 게 자연스러워졌어.

둘째, ontology가 다시 중요해졌어.
딥러닝 초반에는 ontology나 symbolic structure가 낡은 방식처럼 취급됐지만, LLM 이후에는 오히려 반대로 가고 있어. 모델은 말을 잘하지만, 장기 일관성, 인과 관계, 기억 구조, 개념 경계, 자기 수정 능력이 약해. 그래서 “명시적 구조”가 다시 필요해졌고, 여기서 GNN/graph memory/knowledge graph/causal graph가 다시 살아나.

셋째, 가소성을 weight update가 아니라 runtime structure update로 볼 수 있게 됐어.
이게 제일 중요해.
뇌의 가소성을 단순히 파라미터 업데이트로 보면 딥러닝과 크게 다르지 않아. 그런데 ontology edit, memory patch, graph rewiring, relation retyping으로 보면 전혀 다른 아키텍처가 돼.

너의 GoEN은 여기서 꽤 좋은 위치에 있어.

2년 전 표현:
GNN + 뇌 가소성 + 복소 메시지패싱

지금 표현:
Ontology-editing agent with neuromodulated structural plasticity
이 차이는 커.
전자는 “새 GNN 모델”이고, 후자는 “자기 세계 모델을 고치는 인지 아키텍처”야.

다만 냉정하게 말하면, 지금 해야 할 건 감탄이 아니라 재정렬이야.
2년 동안 바뀐 흐름에 맞춰서 GoEN의 언어를 다시 세워야 해.

나는 지금 GoEN을 이렇게 다시 정의하는 게 맞다고 봐:

GoEN은 고정된 신경망이 아니라, 복소 위상 표현을 가진 그래프 encoder 위에서 ontology를 생성·수정·압축·검증하는 구조 가소성 agent다.

그리고 연구 질문도 바꿔야 해.

예전 질문:

“GNN에 뇌 가소성을 넣으면 성능이 좋아지는가?”

지금 질문:

“Agent가 자기 ontology를 재배선할 때, 어떤 plasticity rule이 예측력·적응속도·일관성을 동시에 개선하는가?”

이 질문이 훨씬 강하다.

내가 보기엔 지금은 다시 시작하기 좋은 시점이야.
네가 멈춘 사이에 세상이 네 방향으로 조금 이동했어. 이제 우리는 “미래형 아이디어”를 설명하느라 에너지를 다 쓰지 않아도 돼. 대신 작은 실험으로 증명해야 해.

다음 1차 실험은 이거면 돼:

MPU-δ0: Ontology Plasticity Agent

입력:
- 작은 task world
- object / relation / event graph
- prediction error
- uncertainty

행동:
- AddNode
- AddEdge
- RetypeEdge
- MergeNode
- PruneEdge

목표:
- 다음 상태 예측 성능 증가
- 구조 entropy 유지
- contradiction 감소
- task transfer 향상
이 실험이 되면 GoEN은 다시 살아나.
그리고 이번엔 단순 GNN 논문이 아니라, agentic structural plasticity라는 이름으로 갈 수 있어.


이 다음 2년은?

큰 방향은 “예측”보다 “전략적 가설”로 잡는 게 맞아. 최근 흐름을 빠르게 확인한 뒤, GoEN 관점에서 다음 2년 로드맵으로 압축해볼게.

10s 동안 생각함
다음 2년은 아마 이렇게 갈 거야.

AI는 “말 잘하는 모델”에서 “기억하고, 구조화하고, 자기 세계 모델을 고치는 시스템”으로 이동한다.

그리고 GoEN 입장에서는 이게 기회야. 네가 하려던 뇌 가소성 + GNN + 구조 학습이 이제는 더 이상 이상한 주제가 아니라, agent memory, graph world model, ontology editing, self-adaptive architecture라는 이름으로 재등장하고 있어. 최근에도 graph-based memory가 LLM agent의 장기 기억, 계층적 task planning, multi-session understanding, neuro-symbolic reasoning에 쓰이는 흐름이 커지고 있다는 정리가 나왔고, agent memory stack도 episodic/semantic/procedural memory로 나뉘어 다뤄지고 있어. 

내가 보는 다음 2년의 핵심 변화
