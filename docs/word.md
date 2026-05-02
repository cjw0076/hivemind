좋아. 이 프로젝트는 일반적인 “multi-agent orchestration”보다 더 커.
그래서 기존 용어만 쓰면 부족하고, **우리만의 기술 어휘 체계**가 필요해.

아래는 MemoryOS / Agent Harness / Hypergraph Memory 시스템의 핵심 용어집 초안이야.

---

# MemoryOS Technical Lexicon v0.1

## 0. 최상위 개념

### **MemoryOS**

개인 디바이스에서 실행되는 local-first AI memory operating system.

사용자의 AI 대화, 문서, 코드 작업, agent 실행 기록을 정규화하고, memory graph / hypergraph / project state로 변환하여 Claude, Codex, local LLM, custom agent들이 MCP를 통해 공유 memory로 사용할 수 있게 하는 시스템.

```text
AI conversations → structured memory → hypergraph → agent context → action → new memory
```

---

### **Agent Memory Kernel**

MemoryOS의 핵심 엔진.

대화 export, 작업 로그, agent 결과물을 받아서 memories, nodes, hyperedges, project states, embeddings, run events로 변환하고 저장하는 local memory core.

일반 앱의 database가 아니라, agent들이 반복적으로 읽고 쓰는 **인지 커널**에 가깝다.

---

### **Cognitive Substrate**

agent들이 공유하는 외부 인지 기반층.

LLM 내부 context window에 갇힌 임시 기억이 아니라, 여러 agent가 공통으로 참조하는 durable memory layer.

```text
LLM context = short-term working memory
Cognitive Substrate = long-term shared memory
```

---

## 1. Agent 실행 계층

### **Harness**

여러 agent, CLI, API, local model, MCP tool을 하나의 작업 루프로 묶는 상위 실행 제어 계층.

Harness는 직접 “생각”하기보다 다음을 담당한다.

```text
task routing
context building
agent invocation
handoff control
permission enforcement
event logging
memory commit control
```

즉, Harness는 agent들의 지휘자다.

---

### **Agent Harness**

MemoryOS에서 Claude, Codex, local LLM, research agent, extraction worker 등을 실행자로 등록하고, 작업 목적에 맞게 호출하는 실행 프레임워크.

```text
User task
→ Harness
→ context pack
→ selected agent
→ result
→ review
→ memory draft
→ commit
```

---

### **Orchestration**

여러 agent와 tool을 순서, 역할, 권한, 상태에 따라 배치하고 실행하는 과정.

일반적인 orchestration은 “무엇을 누구에게 맡길 것인가”에 가깝고, 우리 시스템에서는 다음까지 포함한다.

```text
memory retrieval
agent selection
handoff generation
tool permission
result verification
memory update
```

---

### **Agent Router**

사용자 요청을 분석하여 어떤 agent에게 맡길지 결정하는 Harness 내부 모듈.

예:

```text
architecture → Claude
implementation → Codex
bulk extraction → local LLM
web research → research agent
memory validation → memory agent
```

---

### **Agent Adapter**

Claude CLI, Codex CLI, local LLM, API LLM처럼 서로 다른 실행 환경을 Harness가 공통 방식으로 호출할 수 있게 감싸는 wrapper.

```text
Claude CLI Adapter
Codex CLI Adapter
Ollama Adapter
OpenAI API Adapter
Anthropic API Adapter
```

공통 인터페이스:

```text
run(task, context_pack) → agent_result
```

---

### **CLI-as-Worker**

Claude CLI, Codex CLI 등을 독립된 수동 도구로 쓰지 않고, Harness가 headless worker처럼 호출하는 실행 방식.

핵심은 CLI의 provider-native 기능은 유지하면서, 상태와 기억은 MemoryOS에 외부화하는 것이다.

```text
CLI owns execution
MemoryOS owns memory
Harness owns loop
```

---

### **Agent Runtime**

각 agent가 실제로 실행되는 환경.

예:

```text
Claude Code runtime
Codex CLI runtime
Ollama runtime
Browser automation runtime
Local extraction worker
```

---

## 2. Agent 간 협업 용어

### **Handoff**

한 agent가 다른 agent에게 작업을 넘기기 위한 구조화된 인수인계 artifact.

일반 대화가 아니라 YAML/JSON 형태의 작업 계약이다.

```yaml
objective:
constraints:
context_refs:
files_to_modify:
acceptance_criteria:
unresolved_questions:
```

---

### **Handoff Artifact**

agent 간 전달되는 구조화 문서.

예:

```text
Claude → implementation handoff → Codex
Codex → implementation result → Claude reviewer
Local LLM → memory draft report → Harness
```

---

### **Agent Run**

Harness가 특정 agent에게 하나의 작업을 맡긴 실행 단위.

하나의 run은 다음을 가진다.

```text
run_id
agent_id
task
context_pack
tools_used
result
events
memory_refs
created_drafts
status
```

---

### **Run State**

현재 작업 루프의 상태.

```text
objective
current_phase
assigned_agents
pending_handoffs
used_memories
generated_artifacts
pending_memory_drafts
```

Run State가 있어야 CLI들이 독립적이어도 하나의 agent loop처럼 동작한다.

---

### **Event Log**

agent 실행 중 발생한 모든 사건의 append-only 기록.

예:

```text
agent_started
memory_searched
handoff_created
file_modified
test_ran
draft_memory_created
agent_finished
```

Event Log는 디버깅, audit, memory extraction의 근거가 된다.

---

### **Agent Society**

MemoryOS에 등록된 여러 agent들의 역할, 능력, 권한, 관계의 총합.

```text
Claude = architect/reviewer
Codex = implementation agent
Local LLM = batch extraction worker
Harness = coordinator
MemoryOS = shared cognitive substrate
```

---

### **Agent Orientation**

시스템 초기 구동 시 agent들이 자신과 서로의 역할, 사용 가능한 tool, memory system, 사용자 작업 패턴을 파악하는 bootstrapping phase.

결과물:

```text
agent_registry
tool_registry
routing_policy
user_work_profile
memory_policy
```

---

### **Capability Registry**

각 agent가 어떤 작업을 잘하고 못하는지 기록한 운영 지도.

```yaml
agent: codex
strengths:
  - code_editing
  - test_fixing
weaknesses:
  - vague_product_strategy
permissions:
  - repo_write
  - memory_read
```

---

### **Routing Policy**

작업 유형별로 어떤 agent를 primary / reviewer / fallback으로 쓸지 정의한 정책.

예:

```yaml
implementation:
  primary: codex
  planner: claude
  memory_required: true

architecture:
  primary: claude
  reviewer: codex
```

---

## 3. Memory 계층

### **Memory Object**

MemoryOS에서 저장되는 최소 의미 기억 단위.

일반 message가 아니라, LLM/worker가 추출한 durable semantic unit이다.

타입:

```text
idea
decision
question
action
preference
constraint
artifact
reflection
fact
```

필수 필드:

```text
type
content
origin
source
confidence
importance
status
raw_refs
```

---

### **Atomic Memory**

더 이상 쪼개지 않아도 되는 의미 단위.

예:

```text
“Memory writes should be draft-first.”
“Parser should be deterministic code.”
“Uri is not a dating app but an ESN.”
```

---

### **Memory Draft**

아직 승인되지 않은 memory 후보.

LLM이나 agent가 추출한 memory는 바로 저장되지 않고 draft 상태로 들어간다.

```text
extracted memory → draft → validation → commit
```

---

### **Committed Memory**

검증 또는 승인 후 active memory로 승격된 기억.

Agent가 기본적으로 신뢰하고 사용할 수 있는 memory다.

---

### **Memory Lifecycle**

memory가 생성되고, 사용되고, 수정되고, 폐기되는 상태 변화.

```text
draft
→ active
→ reinforced
→ stale
→ superseded
→ rejected
→ archived
```

---

### **Memory Hygiene**

memory graph가 오염되지 않도록 관리하는 품질 관리 과정.

포함:

```text
deduplication
conflict detection
origin correction
stale memory detection
supersession
confidence adjustment
```

---

### **Origin Separation**

사용자가 직접 말한 것과 AI가 제안한 것을 분리하는 원칙.

```text
origin:
- user
- assistant
- mixed
- unknown
```

MemoryOS의 핵심 신뢰 원칙 중 하나다.

---

### **Raw Ref**

memory가 어떤 원문 message, conversation, file, agent run에서 나온 것인지 가리키는 근거 참조.

```text
memory → raw_refs → original messages
```

모든 memory는 raw_refs를 가져야 한다.

---

## 4. Hypergraph 계층

### **Node**

MemoryOS hypergraph의 기본 원자.

타입:

```text
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
```

---

### **Hyperedge**

여러 node를 하나의 의미 사건으로 묶는 다항 관계.

일반 graph edge가 1:1 관계라면, hyperedge는 1:N 또는 N:N 의미 결합이다.

예:

```text
DecisionEvent {
  MCP,
  Skill,
  Harness,
  MemoryOS,
  Draft-first Write
}
```

---

### **Cognitive Event**

Hyperedge로 표현되는 사고 사건.

하나의 대화 턴, 결정, 아이디어 조합, action 도출, agent handoff처럼 여러 요소가 동시에 결합한 사건이다.

```text
Node = 기억의 원자
Hyperedge = 생각의 사건
```

---

### **TurnEvent**

하나의 user-assistant pair를 묶는 기본 hyperedge.

```text
user message
assistant message
intent
concepts
project
source model
timestamp
```

---

### **EpisodeEvent**

여러 turn이 하나의 주제 흐름을 형성할 때 생성되는 hyperedge.

예:

```text
“MemoryOS architecture discussion”
“Uri mobile experience planning”
```

---

### **DecisionEvent**

특정 결정이 여러 근거, 개념, 제약, 대안과 함께 형성된 사건.

예:

```text
Decision:
“Memory access should be exposed through MCP.”

Members:
MCP
Skill
Harness
Agent Memory
Security Constraint
```

---

### **IdeaComposition**

여러 개념이 합쳐져 하나의 아이디어가 만들어진 사건.

예:

```text
AI conversation export
+ embedding
+ hypergraph
+ MCP
+ agent harness
= MemoryOS
```

---

### **ConceptCluster**

자주 함께 등장하거나 같은 문제의식에 속하는 개념 묶음.

예:

```text
ontology
hypergraph
agent memory
personal latent space
cognitive substrate
```

---

### **ActionDerivation**

특정 action이 decision, question, constraint에서 파생된 사건.

예:

```text
Decision: start with ChatGPT importer
→ Action: implement parse_chatgpt_export()
```

---

### **ContradictionSet**

서로 충돌하거나 대체 관계에 있는 memory들을 묶는 hyperedge.

예:

```text
Old: Uri is close to dating app
New: Uri is ESN
Winner: ESN positioning
```

---

### **SystemBootstrappingEvent**

MemoryOS가 처음 agent, tool, user profile, routing policy를 탐색하고 자기 구조를 정의한 사건.

Agent Orientation 결과를 hypergraph에 저장하는 단위.

---

### **AgentHandoffEvent**

한 agent가 다른 agent에게 작업을 넘긴 사건.

멤버:

```text
from_agent
to_agent
objective
context_refs
constraints
acceptance_criteria
result
```

---

## 5. Retrieval / Context 계층

### **Retrieval Orchestrator**

사용자 질문이나 agent task에 맞게 여러 검색 방식을 조합하는 모듈.

```text
keyword search
vector search
hypergraph search
project state retrieval
recency search
reranking
```

---

### **Hybrid Retrieval**

단순 vector search가 아니라 여러 신호를 조합하는 검색.

```text
semantic similarity
graph relevance
hyperedge relevance
importance
confidence
recency
status
```

---

### **Hypergraph Retrieval**

query와 관련된 node 또는 hyperedge를 찾고, 그 hyperedge에 속한 다른 node들을 확장하여 context를 구성하는 방식.

```text
query
→ related nodes
→ containing hyperedges
→ member expansion
→ context pack
```

---

### **Context Pack**

agent에게 작업 전에 주입되는 압축된 작업 맥락.

구성:

```text
task
project_state
relevant_memories
relevant_hyperedges
active_decisions
open_questions
constraints
raw_refs
output_policy
```

LLM에게 raw memory를 무작정 넣는 것이 아니라, agent가 바로 쓸 수 있는 형태로 포장한 context다.

---

### **Memory-First Workflow**

중요한 작업 전에 반드시 memory를 먼저 조회하고, 기존 project state / decisions / constraints를 반영한 뒤 작업하는 절차.

Skill로 정의된다.

```text
detect project
→ get project state
→ search memories
→ search hyperedges
→ build context pack
→ answer/act
→ create memory draft
```

---

### **Evidence Pack**

특정 답변이나 agent action이 어떤 memory와 raw_refs에 근거했는지 보여주는 근거 묶음.

```text
answer
→ evidence memories
→ hyperedges
→ raw messages
```

---

## 6. Project State 계층

### **Project State**

특정 프로젝트의 현재 상태를 요약한 operational memory.

예:

```text
current_stage
north_star
active_goals
active_constraints
active_decisions
open_questions
next_actions
```

Agent는 매번 과거 대화 전체를 뒤지기보다 Project State를 먼저 읽어야 한다.

---

### **Active Decision**

현재 유효한 결정.

예:

```text
“MemoryOS v0.1 should start with ChatGPT export importer.”
```

---

### **Open Question**

아직 결정되지 않았지만 프로젝트 진행에 중요한 질문.

예:

```text
“SQLite-first or Postgres-first?”
“Desktop shell should be Tauri or Electron?”
```

---

### **Next Action**

현재 상태에서 실행 가능한 구체 행동.

예:

```text
“Implement ChatGPT export parser.”
“Create memory.search MCP tool.”
```

---

### **North Star**

프로젝트의 방향성을 결정하는 압축된 최상위 목표.

예:

```text
MemoryOS:
“Local-first memory layer for AI agents.”
```

---

## 7. MCP / Skill 계층

### **Memory MCP**

MemoryOS를 Claude, Codex, Cursor, local agent가 사용할 수 있도록 노출하는 MCP server.

핵심 tools:

```text
project.get_state
memory.search
hypergraph.search
memory.write_draft
context.commit_session
handoff.create
run.log_event
```

---

### **Memory Resource**

MCP resource 형태로 노출되는 읽기 가능한 memory endpoint.

예:

```text
memory://projects/memoryos/state
memory://decisions/active
memory://concepts/hypergraph/history
memory://runs/current
```

---

### **Skill**

agent가 특정 작업을 일관되게 수행하도록 하는 workflow package.

우리 시스템에서 Skill은 기능 구현체가 아니라 **작업 절차와 판단 규칙**이다.

예:

```text
conversation-to-memory-graph
memory-first-workflow
implementation-handoff
boot-orientation
research-synthesis
```

---

### **Conversation-to-Memory Skill**

AI 대화 export를 정규화하고 memory graph로 변환하는 절차.

```text
detect source
parse
normalize
pair
segment
extract memory drafts
build hyperedges
validate
commit
```

---

### **Implementation Handoff Skill**

설계 agent가 coding agent에게 작업을 넘길 때 사용하는 인수인계 절차.

```text
objective
files_to_modify
constraints
acceptance_criteria
commands_to_run
relevant_memories
```

---

### **Boot Orientation Skill**

시스템 초기 구동 시 agent, tool, user profile, routing policy를 탐색하고 정의하는 절차.

---

## 8. Desktop / Visual 계층

### **Memory Cockpit**

MemoryOS Desktop의 홈 화면.

현재 memory graph 상태, active projects, recent decisions, pending drafts, agent runs를 보여주는 관제실.

---

### **Import Center**

ChatGPT, Claude, Gemini, Perplexity export를 가져와 parsing / extraction / graph build pipeline을 실행하는 화면.

---

### **Draft Review**

LLM/agent가 만든 memory draft를 사용자가 승인, 수정, 거절하는 화면.

Memory quality를 통제하는 핵심 UI.

---

### **Hypergraph Explorer**

MemoryOS의 node, hyperedge, concept cluster, decision event를 시각적으로 탐색하는 화면.

단순 예쁜 graph가 아니라, 사고 사건을 클릭하고 근거와 연결을 확인하는 탐색 도구다.

---

### **Agent Harness View**

등록된 agent, MCP tools, capability scores, recent runs, pending handoffs를 보여주는 화면.

---

### **Memory Pipeline View**

대화가 memory로 변환되는 과정을 보여주는 시각화.

```text
Raw Conversation
→ Pair
→ Segment
→ Memory Draft
→ Hyperedge
→ Project State
→ Agent Context
```

---

## 9. 우리 시스템의 핵심 문장들

### 제품 설명용

```text
MemoryOS is a local-first memory layer for AI agents.
```

```text
MemoryOS turns your AI conversations into a reusable local memory graph.
```

```text
Your agents should not start from zero every session.
```

```text
The desktop app is a cockpit for your AI memory graph.
```

---

### 기술 설명용

```text
Harness owns the loop.
MCP exposes the memory.
Skills define the workflow.
Hypergraph stores cognitive events.
Project State gives agents current context.
```

---

### 철학 설명용

```text
Node is a memory atom.
Hyperedge is a cognitive event.
Project State is the current self of a project.
Harness is the conductor.
MemoryOS is the cognitive substrate.
```

---

### 보안/신뢰 설명용

```text
Local-first by default.
Draft-first memory writes.
User-origin and assistant-origin separated.
Every memory links back to raw evidence.
Agents can suggest memories, but the harness controls commits.
```

---

## 10. 용어 간 관계 요약

```text
MemoryOS
└── Agent Memory Kernel
    ├── Memory Objects
    ├── Nodes
    ├── Hyperedges
    ├── Project States
    └── Embeddings

Agent Harness
├── Agent Router
├── Agent Adapters
├── Run State
├── Event Log
├── Handoff Artifacts
└── Capability Registry

Memory MCP
├── memory.search
├── hypergraph.search
├── project.get_state
├── memory.write_draft
├── context.commit_session
└── handoff.create

Skills
├── memory-first-workflow
├── conversation-to-memory-graph
├── implementation-handoff
└── boot-orientation

Desktop
├── Memory Cockpit
├── Import Center
├── Ask Memory
├── Draft Review
├── Project Memory
├── Hypergraph Explorer
└── Agent Harness View
```

---

# 11. 한 문장으로 전체 정리

> **MemoryOS는 개인 AI 대화와 작업 기록을 local hypergraph memory로 변환하고, Agent Harness가 Claude, Codex, local LLM을 공통 memory substrate 위에서 조율하게 만드는 local-first agent operating system이다.**

더 짧게:

> **Local memory kernel for agentic work.**

또는:

> **Your private cognitive substrate for AI agents.**
