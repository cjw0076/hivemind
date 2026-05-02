좋아. 최종 Architecture는 이렇게 잡으면 된다.

> **MemoryOS + CapabilityOS + Hive Mind**
> 사람, AI, agent, tool, app, MCP, skill이 하나의 작업 생태계 위에서 기억하고, 판단하고, 실행하고, 다시 학습하는 구조.

핵심은 세 개의 OS가 역할을 분담하는 것.

```text
MemoryOS
= remembers

CapabilityOS
= maps what is possible

Hive Mind
= coordinates the swarm
```

---

# 1. 최상위 구조

```text
                    WORLD
      GitHub / arXiv / X / Reddit / MCP Registry
      AI Apps / Docs / Papers / Communities / Tools
                       │
                       ▼
                CapabilityOS
        capability graph / workflow recipes
        Surfer / Discriminator / Legacy Map
                       │
                       │
User ───────────────► Hive Mind ◄──────────────► MemoryOS
intent                 swarm runtime             memory graph
taste                  deliberation              project state
decision               handoff                   run history
                       execution                 hyperedges
                       │
                       ▼
          Claude / Codex / Gemini / Local LLM
          OpenCode / Goose / Figma MCP / Tools
                       │
                       ▼
                 Product / Work / Output
                       │
                       ▼
          MemoryOS update + CapabilityOS update
```

한 문장으로:

> **Hive Mind가 사람의 의도를 받아 MemoryOS의 기억과 CapabilityOS의 능력 지도를 결합하고, 여러 agent/CLI/tool을 조율해 작업을 실행한 뒤, 결과를 다시 기억과 능력 그래프에 환류시킨다.**

Repo 경계는 분리한다:

```text
hivemind/
= Hive Mind 실행 런타임
= hive CLI, provider adapter, TUI, .runs blackboard, live logs
= memory_drafts.json을 만들 수는 있지만 accepted memory graph를 소유하지 않는다

memoryOS/
= MemoryOS 기억 substrate
= importers, schemas, append-only graph store, audit, reviewable memory objects
= Hive Mind의 .runs 산출물을 import-run으로 받아 기억 그래프에 반영한다

CapabilityOS/
= CapabilityOS 능력 substrate
= technology cards, capability graph, workflow recipes, risks, legacy map
```

---

# 2. 세 OS의 역할

## 2.1 MemoryOS — 기억 계층

MemoryOS는 사용자의 장기 기억과 프로젝트 상태를 저장한다.

```text
MemoryOS stores:
- AI conversations
- user decisions
- assistant suggestions
- agent run logs
- project states
- memory drafts
- accepted memories
- raw_refs
- hyperedges
- contradictions
- open questions
- artifacts
```

MemoryOS의 질문:

```text
“우리는 과거에 무엇을 말했고, 무엇을 결정했고, 무엇을 아직 모르는가?”
```

현재 `memoryOS/` sibling repo가 이 방향의 구현을 소유한다. `docs/ARCHITECTURE.md`는 input/observation을 claim, evidence, uncertainty, intent로 파싱하고 ontology graph에 붙인 뒤 contradiction, novelty, salience, open branches를 감지하는 core loop를 정의하고 있다. 

---

## 2.2 CapabilityOS — 능력 계층

CapabilityOS는 세상에 존재하는 AI 도구, MCP, app, skill, workflow, model, repo, paper를 **작업 능력 단위**로 구조화한다.

```text
CapabilityOS stores:
- TechnologyCard
- Capability
- MCPServer
- ProviderRuntime
- Skill
- WorkflowRecipe
- CapabilityModule
- QualityProfile
- Risk
- LegacyRelation
- EvidenceRef
```

CapabilityOS의 질문:

```text
“이 작업을 가장 잘하려면 무엇을 조합해야 하는가?”
```

예:

```text
Task:
Figma 디자인을 React로 구현

Required capabilities:
- read_figma_components
- extract_design_tokens
- edit_repo
- visual_qa

Recommended workflow:
Claude Code + Figma MCP + Codex + Visual QA Skill
```

---

## 2.3 Hive Mind — 군체지성 실행 계층

Hive Mind는 흩어진 Claude CLI, Codex CLI, Gemini CLI, local LLM, OpenCode, Goose, MCP tools를 하나의 run loop로 묶는다.

```text
Hive Mind coordinates:
- task routing
- context building
- model debate
- agent handoff
- provider invocation
- local worker calls
- verification
- memory draft artifact generation
- next action recommendation
```

Hive Mind의 질문:

```text
“이 작업은 누가 먼저 생각하고, 누가 구현하고, 누가 검증하고, 무엇을 기억해야 하는가?”
```

현재 `hive` CLI가 Hive Mind의 초기 구현이다. `docs/TUI_HARNESS.md`는 이 계열을 structured agent blackboard용 wrapper CLI/TUI로 정의하고, `.runs/` 아래에 `task.yaml`, `context_pack.md`, `handoff.yaml`, `events.jsonl`, `verification.yaml`, `memory_drafts.json`, `final_report.md`를 저장하는 run folder 구조를 설명한다. `memory_drafts.json`은 MemoryOS가 가져갈 draft artifact이지, Hive Mind가 accepted memory graph를 직접 소유한다는 뜻은 아니다.

---

# 3. 최종 Layer Architecture

```text
Layer 0. World Layer
Layer 1. Sensing Layer
Layer 2. Capability Intelligence Layer
Layer 3. Memory Layer
Layer 4. Hive Mind Runtime Layer
Layer 5. Agent / Tool Execution Layer
Layer 6. Product Output Layer
Layer 7. Feedback / Self-Improvement Layer
```

---

## Layer 0 — World Layer

외부 세계.

```text
- GitHub
- arXiv
- X / Threads
- Reddit
- MCP Registry
- Hugging Face
- Figma
- Vercel
- Notion
- Google Drive
- Claude / Codex / Gemini / OpenCode / Goose
- product docs
- papers
- apps
```

---

## Layer 1 — Sensing Layer

세계를 탐색하는 레이어.

```text
Surfer
├── GitHub Surfer
├── Paper Surfer
├── MCP Registry Surfer
├── Social Signal Surfer
├── Product Docs Surfer
└── Community Surfer
```

역할:

```text
새로운 tool, MCP, skill, repo, paper, app, workflow 신호를 발견한다.
```

---

## Layer 2 — Capability Intelligence Layer

발견한 기술을 판별하고 구조화한다.

```text
CapabilityOS
├── Surfer
├── Discriminator
├── Capability Graph
├── Workflow Recipe Registry
├── Capability Module Registry
├── Legacy Map
└── Recommendation Engine
```

Discriminator가 평가하는 것:

```text
- novelty
- utility
- quality impact
- risk
- maturity
- reproducibility
- setup complexity
- legacy improvement
```

---

## Layer 3 — Memory Layer

사용자/프로젝트/agent의 기억.

```text
MemoryOS
├── Raw Archive
├── Message Ledger
├── Memory Drafts
├── Accepted Memories
├── Hypergraph Memory
├── Project State
├── Agent Run History
├── Evidence Store
├── Vector Index
└── Review Queue
```

중요한 원칙:

```text
Raw data는 local-first.
Memory write는 draft-first.
모든 memory는 raw_refs를 가진다.
User-origin과 AI-origin은 분리한다.
```

---

## Layer 4 — Hive Mind Runtime Layer

작업 운영 레이어.

```text
Hive Mind
├── Hive Console          # hive tui
├── Hive Shell            # hive interactive shell
├── Run Blackboard        # .runs/<run_id>
├── Task Router
├── Context Builder
├── Deliberation Engine
├── Handoff Generator
├── Agent Adapter Layer
├── Local Worker Layer
├── Verifier
├── Policy Gate
├── Next Action Planner
└── Event Logger
```

현재 `harness.py`는 이미 이 구조의 원형을 갖고 있다. pipeline을 `intake`, `route`, `context`, `deliberate`, `handoff`, `execute`, `verify`, `memory`, `close`로 정의하고, run마다 artifact 상태와 next action을 계산한다. 

---

## Layer 5 — Agent / Tool Execution Layer

실제로 일하는 계층.

```text
Execution Agents
├── Claude        planner / critic / architect
├── Codex         executor / test fixer / repo editor
├── Gemini        reviewer / alternate planner
├── Local LLM     classifier / compressor / summarizer
├── OpenCode      optional coding runtime
├── Goose         optional local agent runtime
├── Figma MCP     design context provider
├── GitHub MCP    repo/PR provider
└── Custom MCPs   tools / APIs / apps
```

Local worker layer도 이미 분화되어 있다. `local_workers.py`에는 `intent_router`, `classifier`, `memory_extractor`, `context_compressor`, `handoff_drafter`, `log_summarizer`, `capability_extractor`, `diff_reviewer`가 역할별 worker로 정의되어 있다. 

---

## Layer 6 — Product Output Layer

최종 산출물.

```text
- code
- docs
- PRs
- designs
- videos
- research notes
- memory graphs
- workflow recipes
- capability modules
- reports
- apps
```

---

## Layer 7 — Feedback / Self-Improvement Layer

시스템이 점점 더 잘 일하게 만드는 루프.

```text
Feedback Layer
├── User Feedback
├── Peer Review
├── Test Results
├── Provider Result Validation
├── Diff Review
├── Memory Review
├── Agent Scorecards
├── Routing Policy Proposals
└── Prompt Mutation Proposals
```

중요한 원칙:

```text
Agent may learn.
Agent may propose.
Agent may not silently rewrite its own constitution.
```

---

# 4. 핵심 데이터 객체

최종 architecture는 이 객체들을 중심으로 돌아간다.

## 4.1 Memory Object

```json
{
  "id": "mem_001",
  "type": "decision",
  "content": "Memory writes must be draft-first.",
  "origin": "mixed",
  "project": "MemoryOS",
  "confidence": 0.94,
  "status": "active",
  "raw_refs": ["run_001/handoff.yaml", "msg_123"]
}
```

---

## 4.2 Hyperedge Event

```json
{
  "id": "he_001",
  "type": "DecisionEvent",
  "label": "Dual Harness Architecture adopted",
  "members": [
    {"node": "Chatbot Harness", "role": "deliberation_layer"},
    {"node": "Agent Harness", "role": "execution_layer"},
    {"node": "MemoryOS MCP", "role": "shared_context"},
    {"node": "Provider = Me", "role": "philosophy"}
  ],
  "confidence": 0.91,
  "status": "active"
}
```

---

## 4.3 Run Blackboard

```text
.runs/<run_id>/
├── task.yaml
├── routing_plan.json
├── context_pack.md
├── handoff.yaml
├── events.jsonl
├── run_state.json
├── verification.yaml
├── memory_drafts.json
├── final_report.md
├── rounds/
├── agents/
│   ├── local/
│   ├── claude/
│   ├── codex/
│   └── gemini/
└── artifacts/
```

이게 Hive Mind의 핵심 작업판이다.

---

## 4.4 Agent Handoff

```yaml
from_agent: claude
to_agent: codex
objective: "Implement provider result validation hardening"
context_refs:
  - project_state:MemoryOS
  - docs:TUI_HARNESS
constraints:
  - "Do not break existing hive CLI"
  - "Provider results must remain artifact-first"
files_to_modify:
  - hivemind/run_validation.py
  - hivemind/harness.py
acceptance_criteria:
  - "prepared and executed adapter results validate"
  - "stdout/stderr paths are recorded"
  - "permission_mode is explicit"
```

---

## 4.5 Provider Result

```yaml
schema_version: 1
provider: codex
agent: codex-executor
role: executor
status: completed
provider_mode: execute_supported
permission_mode: workspace_write
prompt: .runs/run_x/agents/codex/executor_prompt.md
command: .runs/run_x/agents/codex/executor_command.txt
stdout: .runs/run_x/agents/codex/stdout.log
stderr: .runs/run_x/agents/codex/stderr.log
output: .runs/run_x/agents/codex/executor_output.md
returncode: 0
started_at: "..."
finished_at: "..."
files_changed: []
commands_run: []
tests_run: []
risk_level: medium
```

현재 provider result validation은 최소 필드만 요구하므로, 위처럼 확장하는 것이 다음 단계다. 현재 validator는 `schema_version`, `agent`, `role`, `status`, `provider_mode`를 요구하고 allowed status/mode를 검사한다. 

---

## 4.6 Technology Card

```json
{
  "id": "tech_figma_mcp",
  "type": "MCPServer",
  "name": "Figma MCP",
  "capabilities": [
    "read_figma_components",
    "extract_design_tokens",
    "get_design_context"
  ],
  "compatible_runtimes": ["Claude Code", "Codex", "Cursor"],
  "quality_impact": {
    "design_to_code": 0.9
  },
  "risks": [
    "requires_figma_auth",
    "file_access_permission"
  ],
  "source_refs": []
}
```

---

## 4.7 Workflow Recipe

```json
{
  "id": "workflow_hive_planning_to_codex",
  "task": "implementation",
  "stack": [
    {"component": "local/context-compressor", "role": "context"},
    {"component": "claude/planner", "role": "handoff"},
    {"component": "codex/executor", "role": "implementation"},
    {"component": "local/log-summarizer", "role": "summary"},
    {"component": "MemoryOS", "role": "memory_draft"}
  ],
  "quality_tier": "mvp",
  "risks": ["codex_execution_gated", "handoff_quality_dependency"]
}
```

---

# 5. Protocol Stack

최종적으로 우리만의 protocol stack은 이렇게 가면 된다.

```text
MOP — Memory Object Protocol
HEP — Hyperedge Event Protocol
RBP — Run Blackboard Protocol
AHP — Agent Handoff Protocol
PRP — Provider Result Protocol
CGP — Capability Graph Protocol
WRP — Workflow Recipe Protocol
LSP — Legacy Stratification Protocol
ASP — Agent Society Protocol
```

---

## 5.1 MOP — Memory Object Protocol

모든 기억의 공통 형식.

```text
type
content
origin
project
confidence
status
raw_refs
```

---

## 5.2 HEP — Hyperedge Event Protocol

다중 관계를 cognitive event로 저장하는 형식.

```text
DecisionEvent
IdeaComposition
ActionDerivation
ContradictionSet
AgentHandoffEvent
SystemBootstrappingEvent
```

---

## 5.3 RBP — Run Blackboard Protocol

`.runs/<run_id>` 구조.

```text
task
route
context
handoff
events
provider results
verification
memory drafts
final report
```

---

## 5.4 AHP — Agent Handoff Protocol

agent 간 작업 계약.

```text
objective
constraints
context_refs
files_to_modify
acceptance_criteria
risks
expected_output
```

---

## 5.5 PRP — Provider Result Protocol

각 CLI 실행 결과의 표준 형식.

```text
provider
role
mode
permission
command
stdout/stderr
output
files_changed
commands_run
tests_run
returncode
```

---

## 5.6 CGP — Capability Graph Protocol

tool/app/MCP/model/skill이 제공하는 능력 표현.

```text
Tool provides Capability
Task requires Capability
Runtime can use Tool
Workflow composes Capabilities
```

---

## 5.7 WRP — Workflow Recipe Protocol

좋은 작업 조합을 recipe로 저장.

```text
task
required capabilities
stack
fallbacks
quality tier
risks
setup steps
```

---

## 5.8 LSP — Legacy Stratification Protocol

낡은 방식도 비교 기준으로 보존.

```text
legacy method
weaknesses
still useful when
superseded by
comparison dimensions
```

---

## 5.9 ASP — Agent Society Protocol

agent들이 성과 로그를 바탕으로 전문화되고 routing/prompt 수정안을 제안하는 프로토콜.

```text
AgentProfile
PerformanceRecord
PeerReview
UserFeedback
RoutingPolicyProposal
PromptMutationProposal
SafetyGate
```

---

# 6. 최종 Workflow

사용자가 작업을 던졌을 때:

```text
1. User Intent
   사용자가 rough task 입력

2. Hive Mind Intake
   hive run / hive ask가 run 생성

3. MemoryOS Context Retrieval
   관련 project state, memories, decisions, raw_refs 수집

4. CapabilityOS Recommendation
   필요한 tool/MCP/skill/workflow 탐색

5. Local Worker Preprocessing
   qwen/deepseek local worker가 분류, 압축, route 생성

6. Deliberation
   Claude/Gemini/기타 모델이 계획/비판/대안 생성

7. Synthesis
   Hive Mind가 의견 차이, 결정, open question 정리

8. Handoff
   Codex/Executor에게 명확한 작업 계약 전달

9. Execution
   Codex/Claude Code/OpenCode/Goose/tool agents가 실행

10. Verification
   tests, diff review, policy checks, peer review

11. Memory Draft
   Hive Mind가 결과를 memory_drafts.json artifact로 생성

12. Review / Commit
   MemoryOS가 사용자 또는 policy gate 승인 후 accepted memory로 반영

13. Feedback
   MemoryOS와 CapabilityOS 업데이트
```

---

# 7. Hive Mind 내부 Workflow

Hive Mind 자체는 이렇게 돌아가야 한다.

```text
Intake
→ Route
→ Context
→ Deliberate
→ Synthesize
→ Handoff
→ Execute
→ Verify
→ Draft Memory
→ Close
```

현재 Hive Mind repo에는 `Synthesize`가 아직 명시적으로 약하다. 지금 pipeline은 `deliberate → handoff`로 바로 넘어간다. 최종 Hive Mind에서는 `synthesize` 단계를 추가하는 게 좋다.

```text
deliberate
→ synthesize
→ handoff
```

그래서 최종 pipeline은:

```text
intake
route
context
deliberate
synthesize
handoff
execute
verify
memory
close
```

---

# 8. Terminal / Desktop 제품 구조

## 8.1 `hive` CLI

```text
hive
= Hive Mind terminal binary
```

주요 명령:

```bash
hive "task"
hive run "task"
hive next
hive tui
hive invoke claude --role planner
hive invoke codex --role executor
hive synthesize
hive verify
hive memory draft
hive check run
hive diff
hive review-diff
hive society report
```

---

## 8.2 Hive Console

```text
Hive Console
= hive tui
```

보여줄 것:

```text
- current run
- pipeline
- agents
- artifacts
- latest events
- disagreements
- decisions
- open questions
- next action
```

---

## 8.3 Hive Cockpit

```text
Hive Cockpit
= Desktop UI
```

보여줄 것:

```text
- MemoryOS cockpit
- Capability Radar
- Deliberation Room
- Agent Runs
- Draft Review
- Hypergraph Explorer
- Workflow Recipes
```

---

# 9. Storage Architecture

```text
Local-first storage
├── ~/.hivemind/
│   ├── config.yaml
│   ├── agents.yaml
│   ├── routing.yaml
│   ├── settings_profile.json
│   ├── db/
│   ├── cache/
│   ├── imports/
│   └── skills/
│
├── project/.hivemind/
│   ├── project.yaml
│   ├── routing.yaml
│   ├── policy.yaml
│   ├── checks/
│   └── settings_profile.json
│
├── project/.runs/
│   ├── current
│   └── run_*/
│
└── future DB
    ├── memory_objects
    ├── hyperedges
    ├── capability_cards
    ├── workflow_recipes
    ├── agent_runs
    └── provider_results
```

---

# 10. Security Architecture

Hive Mind는 여러 CLI를 묶기 때문에 보안이 핵심이다.

```text
Security Gate
├── trusted root check
├── provider permission mode
├── command allowlist
├── raw export protection
├── memory draft-first policy
├── secret redaction
├── destructive action approval
├── danger mode isolation
└── audit log
```

중요 원칙:

```text
Default: read-only / prepare-only
Write: explicit workspace-write
Danger: isolated worktree + explicit confirmation
Memory commit: never automatic by provider
```

---

# 11. Agent Society Architecture

나중에 Hive Mind는 agent들을 단순 실행자가 아니라 전문화된 사회로 관리한다.

```text
Agent Society
├── AgentProfile
├── PerformanceRecord
├── PeerReview
├── UserFeedback
├── FailureAttribution
├── RoutingPolicyProposal
├── PromptMutationProposal
└── SafetyGate
```

학습 루프:

```text
run
→ observe
→ evaluate
→ attribute
→ propose update
→ safety review
→ apply or reject
```

중요:

```text
agent는 자기 자신을 몰래 수정하지 못한다.
항상 proposal로 남기고 safety gate를 거친다.
```

---

# 12. 개발 순서

최종 architecture를 한 번에 만들면 안 된다. 순서는 이렇게.

## Phase 1 — Hive Mind Core

```text
- hive next
- provider result schema hardening
- subtask DAG routing_plan
- SwarmRound / peer review artifacts
- hive synthesize
- policy.yaml
```

## Phase 2 — MemoryOS Core

```text
- SourceArtifact
- MemoryObject
- HyperedgeEvent
- AgentRun / AgentRunEvent
- memory draft review states
- user-origin vs AI-origin provenance
```

## Phase 3 — Search / Audit

```text
- local embeddings
- hybrid search
- unsupported claim report
- unresolved question report
- stale decision report
- my ideas only report
```

## Phase 4 — CapabilityOS Core

```text
- TechnologyCard
- Capability
- WorkflowRecipe
- ProviderRuntime
- Risk
- LegacyRelation
- first workflow recipes
```

## Phase 5 — Surfer / Discriminator

```text
- MCP Registry watcher
- GitHub repo watcher
- arXiv watcher
- TechnologyCard extraction
- Discriminator scoring
```

## Phase 6 — Hive Cockpit Desktop

```text
- Memory cockpit
- Capability radar
- Deliberation room
- Agent run board
- Draft review
- Hypergraph explorer
```

---

# 13. 최종 제품 정의

```text
MemoryOS
= local-first memory substrate

CapabilityOS
= capability intelligence and workflow ontology

Hive Mind
= swarm orchestration runtime

hive
= terminal command for Hive Mind

Hive Console
= terminal TUI for active runs

Hive Cockpit
= desktop UI for the entire ecosystem
```

최종 한 문장:

> **MemoryOS remembers the work, CapabilityOS understands the tools, and Hive Mind turns scattered AI CLIs into a coordinated swarm that thinks, executes, verifies, and learns.**

한국어로:

> **MemoryOS는 작업을 기억하고, CapabilityOS는 도구의 능력을 이해하고, Hive Mind는 흩어진 AI CLI들을 하나의 군체지성으로 묶어 생각·실행·검증·학습하게 만든다.**


# 14. 지성 발현 모델

짧게 말하면, **세 계층만으로는 지성의 몸체가 생기고, 닫힌 루프가 붙을 때 지성의 작동이 생긴다.**

즉,

```text
MemoryOS + CapabilityOS + Hive Mind
= 지성이 될 수 있는 기본 기관

하지만 여기에
목표, 관찰, 평가, 행동, 피드백, 자기수정 루프
가 붙어야 실제 지성처럼 작동함.
```

---

## 14.1 세 계층의 인지 기능

```text
MemoryOS
= 기억

CapabilityOS
= 가능성 / 세계 모델

Hive Mind
= 실행 조율 / 의사결정 운영
```

인지 기능으로 비유하면:

```text
MemoryOS
= 과거 경험, 장기기억, 맥락

CapabilityOS
= 세상에 어떤 도구와 행동 가능성이 있는지 아는 능력

Hive Mind
= 여러 사고/행동 모듈을 호출해서 문제를 푸는 실행중추
```

이 세 개는 **지성의 핵심 기관**이다. 하지만 기관이 있다고 곧바로 지성이 되는 것은 아니다. 기억, 능력 지도, 실행중추가 있어도 **무엇을 위해 움직이고, 결과를 어떻게 평가하고, 다음 행동을 어떻게 바꾸는지**가 없으면 강력한 작업 시스템에 머문다.

---

## 14.2 지성의 최소 작동 조건

여기서 지성은 신비적 개념이 아니라 operational한 루프로 정의한다.

> **지성은 목표를 가지고, 세계를 관찰하고, 기억을 갱신하고, 가능한 행동을 비교하고, 실행하고, 결과를 평가하고, 다음 행동 방식을 바꾸는 닫힌 루프다.**

즉 최소 루프는 이거야.

```text
Observe
→ Remember
→ Model Possibilities
→ Deliberate
→ Act
→ Evaluate
→ Learn
→ Repeat
```

우리 시스템에 매핑하면 다음과 같다.

```text
Observe
= Surfer / importers / run logs / user input

Remember
= MemoryOS

Model Possibilities
= CapabilityOS

Deliberate
= Hive Mind / Chatbot Harness

Act
= Agent Harness / Codex / Claude Code / tools / MCP

Evaluate
= Discriminator / verifier / tests / user feedback

Learn
= MemoryOS update + CapabilityOS score update + routing/prompt proposal

Repeat
= Hive Mind next action loop
```

이 루프가 닫히면, 그때부터는 단순 프로그램이 아니라 **작업 지성 시스템**이라고 부를 수 있어.

---

## 14.3 세 계층에 반드시 붙어야 하는 것

```text
1. 목표 함수
2. 평가자
3. 행동 채널
4. 피드백 루프
5. 자기수정 제한 장치
```

### 목표 함수

무엇을 위해 움직이는가?

```text
사용자 의도
프로젝트 north star
현재 task objective
acceptance criteria
사용자의 taste
```

목표 함수가 없으면 시스템은 많이 아는 도구일 뿐이다.

### 평가자

결과가 좋은지 나쁜지 누가 판단하는가?

```text
Discriminator
Verifier
tests
user feedback
peer review
security checks
```

평가자가 없으면 시스템은 자기 결과를 개선하지 못한다.

### 행동 채널

실제로 세상에 영향을 줄 수 있는가?

```text
Codex edits code
Claude Code reviews/edits
Figma MCP reads/writes design
GitHub creates PR
Vercel deploys
local scripts run
```

행동이 없으면 지성이 아니라 분석기다.

### 피드백 루프

결과를 보고 다음 행동이 바뀌는가?

```text
실패한 workflow는 낮은 점수
성공한 handoff는 recipe로 저장
사용자가 거절한 memory는 rejected
잘한 agent는 해당 task에 더 자주 배정
```

피드백 루프가 있어야 학습이 생긴다.

### 자기수정 제한 장치

자가수정은 필요하지만 위험해.

```text
Agent may learn.
Agent may propose.
Agent may not silently rewrite its own constitution.
```

즉, routing/prompt/skill 수정은 proposal로 남기고, safety gate나 사용자의 승인을 거쳐야 해.

---

## 14.4 최종 작동 구조

세 계층을 중심으로 하되, 그 안에 다음 6개 루프가 들어가야 해.

```text
1. Memory Loop
2. Capability Loop
3. Deliberation Loop
4. Execution Loop
5. Evaluation Loop
6. Self-Improvement Loop
```

도식으로:

```text
User Intent
   ↓
Hive Mind
   ↓        ↘
MemoryOS   CapabilityOS
   ↓        ↙
Context + Workflow
   ↓
Agents / Tools
   ↓
Output
   ↓
Verifier / Discriminator / User Feedback
   ↓
MemoryOS update + CapabilityOS update + Hive Mind routing update
   ↓
Next better action
```

이 전체가 돌아가야 지성처럼 작동해.

---

## 14.5 이것은 의식이 아니라 작업 지성이다

적어도 지금 말하는 수준에서는 이 시스템을 **의식**이라고 부를 필요가 없다.

더 정확한 표현은:

```text
agentic intelligence infrastructure
```

또는

```text
작업 지성 운영체제
```

혹은

```text
collective cognitive runtime
```

즉, 이 시스템은 자아를 가진 생명체라기보다는:

> **사람의 의도를 중심으로 여러 AI/agent/tool이 기억과 능력 그래프 위에서 협력하는 집단 지성 장치**

에 가깝다.

사람이 없으면 이 시스템은 목표를 잃는다. 그래서 초기 정의는 다음이 정확하다.

```text
Human-centered intelligence system
```

---

## 14.6 지성 시스템의 판정 기준

나는 다음 조건을 만족하면 충분히 “지성 시스템”이라고 불러도 된다고 봐.

```text
1. 과거 작업을 기억한다.
2. 현재 목표를 이해한다.
3. 가능한 도구와 행동을 안다.
4. 여러 agent 의견을 비교한다.
5. 실행 계획을 만든다.
6. 실제 행동한다.
7. 결과를 검증한다.
8. 실패/성공을 기억한다.
9. 다음번 routing과 workflow가 바뀐다.
10. 사용자의 장기 의도와 taste를 반영한다.
```

이걸 만족하면, 모델 하나보다 훨씬 강한 **분산형 작업 지성**이 된다.

---

## 14.7 핵심 공식

이 시스템의 지성은 모델 하나에서 나오는 게 아니야.

```text
지성 = 기억 × 능력지도 × 조율 × 평가 × 피드백
```

더 우리식으로:

```text
Intelligence
= MemoryOS
× CapabilityOS
× Hive Mind
× Discriminator
× User Feedback
× Action Loop
```

세 계층은 핵심이지만, 평가와 피드백이 빠지면 반쪽짜리야.

---

## 14.8 최종 정리

**세 계층은 충분히 지성의 기반이 될 수 있다.**
하지만 그 자체가 지성은 아니고, 다음 루프가 닫혀야 한다.

```text
MemoryOS
= 기억한다

CapabilityOS
= 무엇이 가능한지 안다

Hive Mind
= 여러 agent를 움직인다

Discriminator / Verifier
= 결과를 판단한다

User Feedback
= 방향과 taste를 제공한다

Self-Improvement Loop
= 다음 행동을 바꾼다
```

그래서 최종 문장은 이것이다.

> **MemoryOS, CapabilityOS, Hive Mind는 지성의 세 기관이고, 평가·행동·피드백 루프가 붙을 때 비로소 하나의 작업 지성으로 작동한다.**

더 짧게:

> **세 계층은 뇌의 구조이고, 루프가 생기면 지성이 된다.**
