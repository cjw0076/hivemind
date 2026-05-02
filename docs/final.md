최종적으로는 이렇게 봐야 해.

> **MemoryOS는 기억을 저장하고, CapabilityOS는 능력을 지도화하고, Surfer는 세계를 탐색하고, Discriminator는 가치를 판별하고, Chatbot Harness는 사고를 정제하고, Agent Harness는 실행하며, 결과는 다시 MemoryOS와 CapabilityOS로 환류된다.**

즉 최종 시스템은 하나의 앱이 아니라 **Human–AI–Agent Operating Stack**이야.

---

# 1. 최종 전체 구조

```text
User / Human Intent
        ↓
Chatbot Harness
        ↓
Deliberation Layer
        ↓
MemoryOS ←→ CapabilityOS
        ↓
Agent Handoff
        ↓
Agent Harness
        ↓
Execution Agents
        ↓
Verifier / Discriminator
        ↓
MemoryOS Update + CapabilityOS Update
        ↓
Next Better Action
```

더 크게 보면:

```text
                 ┌─────────────────────────────┐
                 │        Human / User          │
                 │  intention, taste, decision  │
                 └──────────────┬──────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────┐
│                  Chatbot Harness                         │
│  GPT / Claude / Gemini / Grok / Perplexity / DeepSeek     │
│  - idea expansion                                         │
│  - debate                                                 │
│  - critique                                               │
│  - synthesis                                              │
│  - specification                                          │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│                  Deliberation Layer                      │
│  - multi-model debate                                    │
│  - contradiction detection                               │
│  - decision extraction                                   │
│  - handoff generation                                    │
└──────────────────────┬───────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌───────────────────┐       ┌────────────────────┐
│     MemoryOS       │       │    CapabilityOS     │
│ user memory        │       │ tool/app/MCP graph  │
│ project state      │       │ workflow recipes    │
│ decisions          │       │ capability modules  │
│ hyperedges         │       │ quality scores      │
│ context packs      │       │ legacy comparisons  │
└─────────┬─────────┘       └──────────┬─────────┘
          │                            │
          └──────────────┬─────────────┘
                         ▼
┌──────────────────────────────────────────────────────────┐
│                    Agent Handoff                         │
│ objective / context / constraints / files / tests / refs  │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│                    Agent Harness                         │
│ Codex / Claude Code / Cursor / local agents / tools       │
│ - implementation                                          │
│ - automation                                              │
│ - testing                                                 │
│ - integration                                             │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│              Verifier + Discriminator                     │
│ quality / risk / security / usefulness / legacy relation  │
└──────────────────────┬───────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│                  Feedback Loop                           │
│ memory update / capability update / workflow refinement   │
└──────────────────────────────────────────────────────────┘
```

---

# 2. 각 컴포넌트의 최종 역할

## 2.1 MemoryOS

**개인/팀/프로젝트의 기억 계층.**

저장하는 것:

```text
- AI 대화
- 사람의 결정
- agent 실행 기록
- 프로젝트 상태
- 성공/실패한 workflow
- 사용자의 선호
- 코드/문서/산출물
- memory object
- hyperedge event
```

MemoryOS의 핵심 질문:

```text
“우리는 과거에 무엇을 생각했고, 무엇을 결정했고, 지금 어디까지 와 있는가?”
```

MemoryOS가 제공하는 것:

```text
project.get_state
memory.search
hypergraph.search
context.build_pack
memory.write_draft
context.commit_session
```

---

## 2.2 CapabilityOS

**세계의 도구/능력/워크플로우 지도.**

저장하는 것:

```text
- AI app
- MCP server
- connector
- skill
- workflow recipe
- capability module
- GitHub repo
- 논문/기술
- provider별 강점
- quality tier
- risk
- legacy comparison
```

CapabilityOS의 핵심 질문:

```text
“이 작업을 가장 잘하려면 어떤 모델, 앱, MCP, Skill, workflow를 조합해야 하는가?”
```

CapabilityOS가 제공하는 것:

```text
capability.search
workflow.recommend
capability.gap_analysis
tool.install_plan
module.find
legacy.compare
```

---

## 2.3 Surfer

**세계를 탐색하는 agent.**

대상:

```text
- X / Threads
- Reddit
- GitHub
- arXiv
- Papers with Code
- MCP Registry
- Product changelog
- AI app docs
- 커뮤니티
- 논문
- 블로그
```

Surfer의 역할:

```text
새로운 기술 신호를 발견한다.
새 MCP, 새 tool, 새 app, 새 workflow, 새 paper, 새 repo를 가져온다.
```

하지만 Surfer는 판단하지 않는다.
Surfer는 “발견자”다.

---

## 2.4 Discriminator

**기술의 진짜 가치를 판별하는 agent.**

판단하는 것:

```text
- 이게 진짜 혁신인가?
- 기존 방식보다 나은가?
- 작업물 품질이 올라가는가?
- 보안/비용/권한 문제는 없는가?
- 데모용인가 production용인가?
- legacy 대비 무엇이 달라졌는가?
- 누구에게 유용한가?
```

Discriminator는 CapabilityOS를 정화한다.

```text
Surfer가 많이 가져온다.
Discriminator가 걸러낸다.
CapabilityOS가 구조화한다.
```

---

## 2.5 Chatbot Harness

**사고 정제 계층.**

역할:

```text
- 아이디어 확장
- 여러 모델 토론
- 반박/비판
- 관점 비교
- 전략 정리
- PRD 작성
- 작업 명세화
- Agent Handoff 생성
```

핵심 원칙:

```text
모호한 생각은 Agent에게 바로 보내지 않는다.
먼저 Chatbot Harness에서 정제한다.
```

---

## 2.6 Agent Harness

**실행 계층.**

역할:

```text
- Codex 실행
- Claude Code 실행
- local coding agent 실행
- repo 수정
- 테스트 실행
- MCP tool 호출
- 파일 생성
- 배포 준비
- 결과 검증
```

Agent Harness는 “생각”보다 “행동”에 집중한다.

```text
Chatbot Harness = Think
Agent Harness = Act
MemoryOS = Remember
CapabilityOS = Know what is possible
```

---

# 3. 최종 Workflow: 사용자가 무언가를 만들고 싶을 때

예를 들어 사용자가 말한다.

```text
“MemoryOS Desktop에 Hypergraph Explorer를 제대로 구현하고 싶어.”
```

최종 시스템은 이렇게 움직인다.

---

## Step 1. User Intent Intake

사용자 요청 수집.

```json
{
  "user_intent": "MemoryOS Desktop에 Hypergraph Explorer 구현",
  "project": "MemoryOS",
  "task_type": "product_feature_implementation"
}
```

---

## Step 2. MemoryOS Context Retrieval

MemoryOS가 관련 기억을 가져온다.

```text
- Desktop visual north star
- v0.1에서는 graph visualization을 과하게 만들지 말자는 결정
- Hyperedge는 cognitive event라는 정의
- Draft Review / Ask Memory / Import Center 우선순위
- React Flow 초기 후보
- Hypergraph Explorer는 v0.2~v0.3에서 강화
```

출력:

```text
Context Pack
```

---

## Step 3. CapabilityOS Capability Planning

CapabilityOS가 필요한 능력을 분해한다.

```text
Task: Hypergraph Explorer 구현

Required capabilities:
- graph canvas rendering
- node detail inspector
- hyperedge grouping
- filter by type/status/project
- evidence panel
- graph search
- zoom/pan interaction
```

가능한 tool/module 후보:

```text
- React Flow
- Cytoscape.js
- Sigma.js
- D3 force graph
- existing graph UI modules
- custom HyperedgeCard component
```

CapabilityOS가 추천한다.

```text
초기 MVP:
React Flow + custom hyperedge node + right inspector

고급 버전:
Sigma.js/Cytoscape.js + graph layout engine
```

---

## Step 4. Surfer Optional Update

Surfer가 최신 기술을 확인한다.

```text
- 최근 graph visualization library 변화
- MCP/agent UI 관련 repo
- React Flow examples
- knowledge graph UI 사례
```

이 단계는 항상 도는 게 아니라, 최신성이 중요한 경우에만 돈다.

---

## Step 5. Discriminator Evaluation

Discriminator가 후보를 평가한다.

```text
React Flow:
+ 빠른 구현
+ custom node 쉬움
- 대규모 graph에는 약할 수 있음

Cytoscape:
+ graph analysis 강함
- UI 커스터마이징 비용 높음

Sigma:
+ 대규모 graph 시각화 강함
- React app MVP에는 초기 복잡도 높음
```

결론:

```text
v0.1~v0.2는 React Flow.
대규모 graph explorer는 나중에 Cytoscape/Sigma adapter 고려.
```

---

## Step 6. Chatbot Harness Deliberation

여러 chatbot 모델이 사고한다.

```text
Claude:
정보 구조, UX 원칙, graph abstraction 정리

GPT:
화면 구성, user flow, component hierarchy 정리

Gemini:
visual/interaction alternative 제안

DeepSeek:
구현 난이도와 라이브러리 trade-off 분석

Local LLM:
MemoryOS 과거 결정 요약
```

Synthesis Agent가 정리한다.

결과:

```text
Hypergraph Explorer 구현 명세
```

---

## Step 7. Agent Handoff 생성

Agent Harness로 넘길 문서 생성.

```yaml
handoff:
  objective: "Implement initial Hypergraph Explorer screen for MemoryOS Desktop"
  project: "MemoryOS"
  background:
    - "Hyperedge represents cognitive event."
    - "v0.1 should avoid overbuilding graph visualization."
  decisions:
    - "Use React Flow for initial implementation."
    - "Use right-side inspector for selected node/hyperedge."
  files_to_create:
    - "apps/desktop/src/routes/HypergraphExplorer.tsx"
    - "apps/desktop/src/components/graph/HypergraphCanvas.tsx"
    - "apps/desktop/src/components/graph/HyperedgeInspector.tsx"
  constraints:
    - "Use mock data if backend is not ready."
    - "Keep API boundary clean."
    - "Do not implement full large-scale graph engine yet."
  acceptance_criteria:
    - "Shows nodes and hyperedges."
    - "Can select hyperedge."
    - "Right inspector shows type, summary, members, confidence, status."
    - "Filters by hyperedge type."
    - "Matches dark cognitive cockpit style."
  memory_refs:
    - "project_state:MemoryOS"
    - "decision:desktop_visual_cognitive_cockpit"
    - "concept:hyperedge_as_cognitive_event"
```

---

## Step 8. Agent Harness Execution

Codex / Claude Code가 실행한다.

```text
- 파일 생성
- 컴포넌트 구현
- mock data 작성
- 타입 정의
- 테스트/빌드 실행
```

---

## Step 9. Verifier 검증

Verifier가 확인한다.

```text
- 타입 통과?
- lint 통과?
- UI acceptance criteria 충족?
- architecture decision과 충돌 없음?
- 보안 문제 없음?
- 과도한 scope creep 없음?
```

---

## Step 10. Discriminator 결과 평가

작업 결과물을 다시 평가한다.

```text
- 품질이 충분한가?
- 기존 방식보다 나은가?
- 사용자가 의도한 visual north star와 맞는가?
- 더 좋은 tool/module이 있었는가?
- 이 workflow를 재사용 가능한 recipe로 저장할 수 있는가?
```

---

## Step 11. MemoryOS Update

MemoryOS에 저장한다.

```text
New memories:
- Hypergraph Explorer v0.1 uses React Flow.
- Hyperedge Inspector pattern adopted.
- Large-scale graph engine deferred.

New action:
- Later evaluate Cytoscape/Sigma for v0.3.

New artifact:
- HypergraphExplorer.tsx
- HypergraphCanvas.tsx

New AgentRun:
- Codex implemented initial UI.
```

---

## Step 12. CapabilityOS Update

CapabilityOS도 업데이트한다.

```text
WorkflowRecipe:
"Small-to-medium knowledge graph UI in React"
stack:
- React Flow
- custom inspector
- mock graph adapter

Quality:
good for MVP
not ideal for massive graph

Legacy comparison:
better than static card list
less powerful than full graph engine
```

---

## Step 13. Loop 완료

다음에는 더 똑똑해진다.

```text
다음 graph UI 작업 때:
MemoryOS는 이전 결정을 기억하고,
CapabilityOS는 React Flow workflow의 성능을 알고,
Agent Harness는 비슷한 모듈을 재사용한다.
```

---

# 4. 전체 시스템의 최종 Loop

이 시스템의 핵심은 닫힌 루프야.

```text
Discover
→ Judge
→ Remember
→ Deliberate
→ Specify
→ Execute
→ Verify
→ Learn
→ Recommend better next time
```

각 단계는 이렇게 대응된다.

```text
Discover     = Surfer
Judge        = Discriminator
Remember     = MemoryOS
Know Tools   = CapabilityOS
Deliberate   = Chatbot Harness
Specify      = Handoff Generator
Execute      = Agent Harness
Verify       = Verifier
Learn        = MemoryOS + CapabilityOS update
```

한 줄로:

```text
Surfer finds.
Discriminator judges.
MemoryOS remembers.
CapabilityOS maps.
Chatbot Harness thinks.
Agent Harness acts.
Verifier checks.
The system learns.
```

---

# 5. 최종 Architecture Layer

최종적으로는 7개 레이어로 볼 수 있어.

---

## Layer 0. World Layer

외부 세계.

```text
WWW
SNS
GitHub
arXiv
MCP Registry
AI apps
product docs
community
papers
benchmarks
```

---

## Layer 1. Sensing Layer

세계를 감지한다.

```text
Surfer
Crawler
RSS watcher
GitHub watcher
arXiv watcher
MCP registry watcher
Social signal watcher
```

---

## Layer 2. Evaluation Layer

감지한 것을 평가한다.

```text
Discriminator
Risk evaluator
Quality evaluator
Legacy comparator
Reproducibility checker
Security scanner
```

---

## Layer 3. Knowledge Layer

지식을 구조화한다.

```text
CapabilityOS
Capability Ontology
Workflow Recipes
Technology Cards
Legacy Maps
Capability Modules
```

---

## Layer 4. Memory Layer

사용자/프로젝트/agent의 기억을 저장한다.

```text
MemoryOS
Project State
Memory Objects
Hyperedges
Run Events
Handoff History
Personal Context
```

---

## Layer 5. Thought Layer

사고를 정제한다.

```text
Chatbot Harness
Deliberation Room
Multi-model debate
Synthesis Agent
Context Pack Builder
```

---

## Layer 6. Action Layer

실행한다.

```text
Agent Harness
Codex
Claude Code
Cursor
Local agents
MCP tools
Automation workers
```

---

## Layer 7. Product / Ecosystem Layer

결과물이 생긴다.

```text
Apps
Documents
Code
Designs
Videos
Research
Workflows
Skills
Modules
Products
```

그리고 다시 Layer 4와 3으로 환류된다.

---

# 6. 최종 시스템의 주요 데이터 객체

이 시스템은 결국 몇 개의 핵심 객체로 돌아간다.

## 6.1 Memory Object

```text
사용자/agent/프로젝트의 의미 기억
```

예:

```json
{
  "type": "decision",
  "content": "Memory writes should be draft-first.",
  "origin": "mixed",
  "project": "MemoryOS",
  "status": "active",
  "raw_refs": ["msg_123"],
  "confidence": 0.94
}
```

---

## 6.2 Hyperedge Event

```text
여러 memory, concept, decision, action이 결합된 사고 사건
```

예:

```json
{
  "type": "DecisionEvent",
  "label": "Dual Harness Architecture adopted",
  "members": [
    "Chatbot Harness",
    "Agent Harness",
    "MemoryOS MCP",
    "Provider = Me"
  ]
}
```

---

## 6.3 Technology Card

```text
외부 기술/app/MCP/tool의 구조화된 정보
```

예:

```json
{
  "name": "Figma MCP",
  "type": "MCPServer",
  "capabilities": [
    "read_design_components",
    "extract_design_tokens"
  ],
  "quality_impact": {
    "design_to_code": "high"
  }
}
```

---

## 6.4 Workflow Recipe

```text
특정 작업을 고품질로 수행하는 조합
```

예:

```json
{
  "task": "figma_to_react",
  "stack": [
    "Claude Code",
    "Figma MCP",
    "GitHub MCP",
    "Visual QA Skill"
  ],
  "quality_tier": "production"
}
```

---

## 6.5 Capability Module

```text
agent가 가져다 붙일 수 있는 검증된 능력 단위
```

예:

```json
{
  "module": "memory-draft-review-ui",
  "provides": [
    "draft_review_ui",
    "human_approval_workflow"
  ],
  "requires": [
    "memory.list_drafts",
    "memory.commit_drafts"
  ]
}
```

---

## 6.6 Agent Handoff

```text
사고에서 실행으로 넘어가는 계약서
```

예:

```yaml
objective:
constraints:
files_to_modify:
acceptance_criteria:
memory_refs:
expected_output:
```

---

## 6.7 Run Event

```text
agent가 실제로 무엇을 했는지 남기는 실행 기록
```

예:

```json
{
  "agent": "codex",
  "task": "implement ChatGPT parser",
  "files_changed": [],
  "tests_run": [],
  "memory_used": [],
  "result": "success"
}
```

---

# 7. 최종 제품군 구조

최종적으로 제품은 하나가 아니라 suite가 될 수 있어.

```text
MemoryOS
= 기억 계층

CapabilityOS
= 능력/도구/워크플로우 계층

Chatbot Harness
= 사고 정제 계층

Agent Harness
= 실행 계층

Capability Radar
= Surfer + Discriminator 기반 기술 감시 계층

Desktop Cockpit
= 전체를 조작하는 UI
```

제품 이름으로는:

```text
MemoryOS Desktop
MemoryOS MCP
CapabilityOS Radar
Agent Harness Runtime
Chatbot Deliberation Room
```

전체 suite:

```text
Human-Agent Operating System
```

또는:

```text
Cognitive Operating Stack
```

---

# 8. 최종 Desktop Workflow

사용자가 Desktop에서 보는 흐름은 이렇게 돼야 해.

## Home: Cockpit

```text
오늘 발견된 기술
진행 중 프로젝트
pending memory drafts
agent runs
capability gaps
recommended workflows
```

## Capability Radar

```text
Surfer가 발견한 최신 tool/paper/repo/MCP
Discriminator 평가
추천/보류/위험 표시
```

## MemoryOS

```text
내 프로젝트 상태
내 결정
내 미해결 질문
내 agent 실행 기록
```

## Deliberation Room

```text
여러 chatbot 모델 토론
synthesis
handoff 생성
```

## Agent Runs

```text
Codex / Claude Code / local agent 실행
로그
테스트
결과
```

## Draft Review

```text
새 memory 승인
새 capability card 승인
새 workflow recipe 승인
```

## Graph Explorer

```text
Memory Hypergraph
Capability Graph
Workflow Graph
Legacy Map
```

---

# 9. 모든 것이 완성됐을 때의 “하루 사용 시나리오”

아침에 앱을 켠다.

```text
Capability Radar:
- 새로운 Figma MCP 업데이트 발견
- 새 video workflow 발견
- arXiv에서 agent memory 관련 논문 발견
- GitHub에서 MCP security issue 발견
```

Discriminator가 평가한다.

```text
- Figma MCP update: useful, design-to-code 품질 향상
- video workflow: promising but expensive
- 논문: relevant to MemoryOS retrieval
- security issue: high-risk, MCP sandbox policy 업데이트 필요
```

MemoryOS가 개인 맥락에 맞춘다.

```text
“너는 지금 MemoryOS Desktop과 Uri visual 작업을 많이 하므로,
Figma MCP update와 visual QA workflow가 특히 관련 있음.”
```

사용자가 말한다.

```text
“Uri landing page hero section을 제대로 구현하고 싶어.”
```

Chatbot Harness가 사고한다.

```text
- 과거 Uri visual north star 검색
- 디자인 asset 대화 검색
- 최신 Figma/visual workflow 추천
- Claude/GPT/Gemini로 화면 기획 토론
- 구현 명세 생성
```

Agent Harness가 실행한다.

```text
- Codex가 React component 구현
- Figma MCP가 디자인 context 제공
- Visual QA가 screenshot 비교
- 결과 검증
```

결과가 저장된다.

```text
MemoryOS:
- Uri hero section 구현 decision 저장
- 사용된 workflow 저장
- 실패/수정 기록 저장

CapabilityOS:
- 이 workflow가 Uri 작업에 효과적이었다고 기록
```

다음번엔 더 잘한다.

---

# 10. 핵심 Feedback Loop 3개

최종 시스템은 3개의 루프가 동시에 돈다.

---

## Loop A. Personal Memory Loop

```text
사용자 대화/작업
→ MemoryOS 저장
→ 다음 작업 context로 사용
→ 더 좋은 결과
→ 다시 MemoryOS 저장
```

목표:

```text
AI가 나를 점점 더 잘 이해한다.
```

---

## Loop B. Capability Learning Loop

```text
Surfer 발견
→ Discriminator 평가
→ CapabilityOS 저장
→ workflow 추천
→ 실제 사용 결과 기록
→ 점수 업데이트
```

목표:

```text
시스템이 어떤 도구 조합이 좋은지 점점 더 잘 안다.
```

---

## Loop C. Agent Execution Loop

```text
Chatbot Harness 명세
→ Agent Harness 실행
→ Verifier 검증
→ 실패/성공 기록
→ 다음 handoff 개선
```

목표:

```text
agent가 점점 더 적은 시행착오로 실행한다.
```

---

# 11. 최종 Architecture의 핵심 원칙

## Principle 1. Do not execute before deliberation

```text
모호한 요청은 바로 agent에게 보내지 않는다.
먼저 Chatbot Harness에서 정제한다.
```

## Principle 2. Store structure, not raw everything

```text
웹 전체를 저장하지 않는다.
Claim, capability, evidence, workflow, legacy 관계를 저장한다.
```

## Principle 3. Draft-first memory

```text
agent가 만든 memory는 바로 commit하지 않는다.
항상 draft → 검증 → commit.
```

## Principle 4. Provider = Me

```text
모델 provider는 외부 회사일 수 있지만,
context provider는 사용자 자신이다.
```

## Principle 5. Agent does not code from scratch

```text
agent는 검증된 capability module과 workflow recipe를 조립한다.
```

## Principle 6. Legacy is not trash

```text
낡은 방식은 삭제하지 않는다.
좋은 방식이 왜 좋은지 설명하는 기준면으로 저장한다.
```

## Principle 7. Every recommendation must explain the gap

```text
추천은 “이걸 써라”가 아니라
“현재 네 환경에서 무엇이 부족하고, 이 조합이 무엇을 개선하는지”를 설명해야 한다.
```

---

# 12. 최종 시스템을 한 문장으로

> **MemoryOS와 CapabilityOS는 사람의 기억과 세계의 능력을 hypergraph로 구조화하고, Chatbot Harness는 생각을 정제하며, Agent Harness는 검증된 capability를 조립해 실행하고, Surfer와 Discriminator는 세계의 최신 기술을 계속 발견·평가하여 시스템 전체를 진화시키는 Human–Agent Operating Stack이다.**

더 짧게:

> **MemoryOS remembers. CapabilityOS knows what is possible. Chatbot Harness thinks. Agent Harness acts. Surfer discovers. Discriminator judges.**

한국어로:

> **MemoryOS는 기억하고, CapabilityOS는 가능성을 알고, Chatbot Harness는 생각하고, Agent Harness는 실행하고, Surfer는 발견하고, Discriminator는 판별한다.**

---

# 13. 최종 도식

```text
                WORLD
  GitHub / arXiv / X / Reddit / MCP / Apps
                  │
                  ▼
              Surfer
          discovers signals
                  │
                  ▼
           Discriminator
      judges utility / risk / quality
                  │
                  ▼
             CapabilityOS
   tools / skills / MCP / workflows / legacy
                  │
                  │
User ─────────────┼──────────────► Chatbot Harness
intent            │                  deliberates
                  │                       │
                  ▼                       ▼
              MemoryOS ◄────────── Context Pack
      user/project/agent memory           │
                  │                       ▼
                  └──────────────► Agent Handoff
                                          │
                                          ▼
                                    Agent Harness
                                executes via agents/tools
                                          │
                                          ▼
                                      Product
                                          │
                                          ▼
                                  Verification
                                          │
                                          ▼
                         MemoryOS + CapabilityOS update
```

---

# 14. 개발 순서로 다시 압축하면

이 모든 것을 한 번에 만들 수는 없어. 순서는 이렇게 가야 해.

## Phase 1. MemoryOS Core

```text
ChatGPT export
→ memory object
→ hyperedge
→ MCP search
```

## Phase 2. Agent Harness

```text
Codex/Claude CLI adapter
→ handoff
→ run log
→ memory update
```

## Phase 3. Chatbot Harness

```text
multi-model deliberation
→ synthesis
→ agent handoff
```

## Phase 4. CapabilityOS Core

```text
TechnologyCard
→ Capability
→ WorkflowRecipe
→ LegacyRelation
```

## Phase 5. Surfer + Discriminator

```text
MCP/GitHub/arXiv watcher
→ evaluation
→ capability graph update
```

## Phase 6. Desktop Cockpit

```text
Memory
Capability
Deliberation
Agent Runs
Radar
Graph Explorer
```

## Phase 7. Capability Module Assembly

```text
agent가 코드를 새로 쓰는 대신
verified capability modules를 조립
```

---

# 15. 최종 목표

너의 최종 목표는 “AI 앱”이 아니야.

최종 목표는:

> **사람, AI, agent가 같은 memory/capability field 위에서 생각하고 실행하고 배울 수 있는 새로운 작업 생태계.**

여기서 사용자는 단순 소비자가 아니라:

```text
intent provider
context provider
decision owner
memory owner
workflow curator
```

가 된다.

그리고 시스템은 이걸 해준다.

```text
세계를 탐색한다.
쓸만한 능력을 판별한다.
너의 기억과 연결한다.
여러 모델로 생각을 깊게 한다.
agent에게 명확히 실행시킨다.
결과를 다시 기억한다.
다음번엔 더 잘한다.
```

이게 최종 workflow이자 architecture야.
