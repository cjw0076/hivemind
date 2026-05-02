<!--
Source: docs/memoryOS.md
Source lines: 3501-4200
Source byte range: 101259-119693
Split title source: numbered-section
Split note: Source is mostly a raw conversation/export planning document with long heading-less stretches; split into stable line windows while preserving order.
-->

# Part 006: 4. Modify the smallest set of files required.

Provenance: `docs/memoryOS.md` lines `3501-4200`, bytes `101259-119693`.

Local structure markers:

- Source line 3501: 4. Modify the smallest set of files required.
- Source line 3502: 5. Run the documented test/lint/typecheck commands.
- Source line 3503: 6. Return:
- Source line 3509: 7. Do not commit memory directly. Use `context.commit_session` only with draft updates.
- Source line 3510: 21. Memory MCP tool contract 예시
- Source line 3552: 22. “Claude, Codex, local LLM” 각각의 역할
- Source line 3587: 23. 제일 중요한 설계 원칙
- Source line 3628: 24. 최종 추천 구조
- Source line 3647: 1. memory-os-mcp부터 만든다.
- Source line 3648: 2. read-only tools 3개만 연다.
- Source line 3652: 3. Codex와 Claude Code에 연결한다.
- Source line 3653: 4. AGENTS.md에 메모리 사용 원칙을 박는다.

---

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
