Production 기준으로 보면 지금은 **좋은 prototype / dev harness** 단계고, 아직 **production-grade Hive Mind / MemoryOS runtime**까지는 몇 가지 핵심 축이 부족해.

내 판단:

```text
현재 상태:
- mos / hive CLI-TUI 골격: 좋음
- run blackboard 구조: 좋음
- local worker 개념: 좋음
- provider artifact 구조: 시작됨
- production 자동화/안전성/검증/설치성: 아직 부족
```

현재 repo는 `.runs/<run_id>` 기반 blackboard, `task.yaml`, `context_pack.md`, `handoff.yaml`, `events.jsonl`, `verification.yaml`, `memory_drafts.json`, `final_report.md` 구조가 이미 잡혀 있고, `mos` TUI/CLI가 이를 운영하는 형태로 문서화되어 있어.  또 local worker는 `intent_router`, `classifier`, `memory_extractor`, `context_compressor`, `handoff_drafter`, `log_summarizer`, `capability_extractor`, `diff_reviewer`로 나뉘어 있어 방향은 맞다. 

아래는 production 가기 전에 필요한 부족분이다.

---

# 1. Hardware / Runtime Doctor가 더 강해야 함

지금 `mos local status/setup`은 좋은 시작이지만, production에서는 **하드웨어 체킹이 더 깊어야 해.**

현재 필요한 것:

```text
CPU
RAM
GPU
VRAM
OS / arch
disk space
Python version
Node version
Ollama availability
llama.cpp availability
Docker availability
ports availability
provider CLI paths
network availability
```

지금은 local model manifests와 Ollama wrapper 중심으로 보이는데, production에서는 “이 컴퓨터에서 어떤 모델을 어떤 역할로 돌릴 수 있는가”를 자동 판단해야 해.

필요한 출력 예:

```text
Hardware Profile

CPU: 12 cores
RAM: 32GB
GPU: NVIDIA RTX 4070
VRAM: 12GB
Disk free: 240GB

Recommended local roles:
- qwen3:1.7b → classifier
- qwen3:8b → context compressor
- deepseek-coder:6.7b → log summarizer
- deepseek-coder-v2:16b → diff reviewer, only if VRAM available

Warnings:
- deepseek-coder-v2:16b may be slow on CPU-only mode
- Ollama server not running
- Codex CLI detected but gated
```

추가해야 할 명령:

```bash
hive doctor hardware
hive doctor providers
hive doctor models
hive doctor permissions
hive doctor all
```

---

# 2. Local LLM 자동 세팅이 아직 production급 아님

지금 local worker route table은 좋다. 하지만 production에서는 단순히 “모델이 있다”가 아니라:

```text
모델 설치
모델 benchmark
역할별 성능 측정
schema-validity 측정
latency 측정
fallback 설정
routing 자동 생성
```

까지 되어야 해.

필요한 flow:

```bash
hive local setup --auto
```

동작:

```text
1. Ollama / local runtime 확인
2. 없으면 설치 가이드 또는 자동 설치
3. 추천 모델 pull
4. 각 모델 smoke test
5. JSON schema 출력 테스트
6. role별 benchmark
7. local_model_profile.json 생성
8. routing.yaml 자동 업데이트
```

예:

```json
{
  "models": {
    "qwen3:1.7b": {
      "recommended_roles": ["classifier", "short_json"],
      "json_validity": 0.93,
      "latency_ms": 180
    },
    "qwen3:8b": {
      "recommended_roles": ["context_compressor", "memory_extractor"],
      "json_validity": 0.87,
      "latency_ms": 900
    },
    "deepseek-coder:6.7b": {
      "recommended_roles": ["log_summarizer", "error_classifier"],
      "json_validity": 0.81,
      "latency_ms": 1100
    }
  }
}
```

즉, production에서는 **사용자에게 “이 모델을 이 역할로 쓰세요”라고 자동 배정**해야 한다.

---

# 3. Agent 역할 분리가 더 명확해야 함

현재 Claude/Codex/Gemini/local worker 역할 분리는 문서상 좋다. Claude는 planner/critic, Codex는 executor, Gemini는 reviewer, local은 worker로 잡혀 있다. Provider Harness 문서도 이 방향을 잘 설명한다. 

하지만 production에서는 역할이 문서가 아니라 **policy + schema + runtime routing**으로 고정되어야 한다.

필요한 구조:

```yaml
agents:
  claude.planner:
    allowed_actions:
      - read_context
      - write_handoff
      - critique
    forbidden_actions:
      - repo_write
      - memory_commit
    default_mode: plan

  codex.executor:
    allowed_actions:
      - repo_read
      - repo_write_with_approval
      - run_tests
    forbidden_actions:
      - memory_commit
      - raw_export_access
    default_mode: workspace_write

  local.context:
    allowed_actions:
      - compress_context
      - classify
      - draft_memory
    forbidden_actions:
      - repo_write
      - final_decision
```

추가해야 할 것:

```text
- agent role registry
- permission policy
- role-specific prompt templates
- provider-specific execution modes
- fallback roles
- escalation rules
```

명령:

```bash
hive agents roles
hive agents policy
hive agents explain codex.executor
```

---

# 4. Context 추론 디자인이 production의 핵심 병목

현재 `context_pack.md`는 존재하지만, production에서는 context가 그냥 “관련 문서 모음”이면 안 돼.

Context는 아래 순서로 만들어져야 한다.

```text
1. Task understanding
2. Project state retrieval
3. Relevant memory selection
4. Capability recommendation
5. Risk / policy filtering
6. Context compression
7. Agent-specific context packing
```

agent별 context가 달라야 한다.

## Claude Planner용 context

```text
- project north star
- active decisions
- unresolved questions
- conceptual risks
- relevant disagreements
```

## Codex Executor용 context

```text
- objective
- files to modify
- constraints
- acceptance criteria
- tests to run
- forbidden scope
```

## Local Worker용 context

```text
- short input
- strict JSON schema
- raw_refs
- confidence/escalation fields
```

즉, production에서는:

```bash
hive context build --for claude.planner
hive context build --for codex.executor
hive context build --for local.memory
```

가 필요하다.

그리고 context pack에는 반드시 이 필드가 있어야 한다.

```yaml
context_pack:
  objective:
  project_state:
  active_decisions:
  constraints:
  relevant_memories:
  capability_recommendations:
  open_questions:
  risks:
  forbidden_scope:
  raw_refs:
  output_contract:
```

현재 local `context_compressor` worker는 좋은 시작이지만, 더 강한 **Context Builder / Context Budgeter / Context Validator**가 필요하다.

---

# 5. Provider Result Schema가 더 단단해야 함

현재 provider result validation은 최소 필드 중심이다. `run_validation.py`는 provider result에 `schema_version`, `agent`, `role`, `status`, `provider_mode`를 요구한다. 

production에서는 부족하다.

필요한 필드:

```yaml
schema_version: 1
provider: codex
agent: codex-executor
role: executor
status: completed
provider_mode: execute_supported
permission_mode: workspace_write

prompt_path:
command_path:
stdout_path:
stderr_path:
output_path:

returncode:
started_at:
finished_at:
duration_ms:

files_changed:
commands_run:
tests_run:
artifacts_created:

risk_level:
policy_violations:
memory_refs_used:
capability_refs_used:
```

이게 있어야 swarm agent들이 서로의 결과를 신뢰하고 이어받을 수 있다.

---

# 6. Multi-session Hive Console이 필요함

지금 TUI는 한 화면에 모든 정보를 넣으려는 구조라 production에서는 답답해진다.

production에서는 다음 view들이 분리되어야 한다.

```bash
hive board
hive events --follow
hive transcript
hive agents
hive artifacts
hive diff
hive memory
hive society
```

그리고 듀얼 모니터 / tmux layout 지원이 필요하다.

```bash
hive workspace --layout dev
hive workspace --layout dual
```

예:

```text
Monitor 1:
- hive board --control

Monitor 2:
- hive events --follow
- hive transcript
- hive agents
- hive diff
```

추가로 controller lock이 필요하다.

```text
controller session: 명령 실행 가능
observer session: 읽기 전용
worker session: 특정 agent 실행
```

없으면 두 터미널에서 동시에 같은 run을 수정하는 문제가 생긴다.

---

# 7. Policy / Permission Gate가 아직 부족함

Production에서 가장 위험한 부분이다.

Hive Mind는 여러 CLI를 묶는다.
Codex, Claude, Gemini, local scripts, MCP tools가 모두 실행되면 권한 관리가 필수다.

필요한 policy file:

```yaml
default:
  repo_write: deny
  shell: deny
  memory_commit: deny
  raw_export_access: deny

roles:
  claude.planner:
    repo_read: allow
    repo_write: deny
    memory_draft: allow

  codex.executor:
    repo_read: allow
    repo_write: allow_with_approval
    shell: allowlist
    memory_commit: deny

  local.memory_extractor:
    memory_draft: allow
    repo_write: deny

danger_modes:
  allowed: false
```

명령:

```bash
hive policy check
hive policy explain codex.executor
hive invoke codex --role executor --mode workspace-write
```

위험 모드는 반드시:

```bash
--confirm-danger
--isolated-worktree
```

같은 보호장치가 필요하다.

---

# 8. 실제 MemoryOS DB / Graph로 넘어가는 부분이 부족함

현재 `.runs` blackboard는 훌륭하지만, production MemoryOS는 run-local artifact만으로 부족하다.

필요한 persistence:

```text
AgentRun
AgentRunEvent
MemoryDraft
MemoryObject
HyperedgeEvent
SourceArtifact
ProviderResult
ProjectState
```

현재는 `.runs`에 남고, `memory_drafts.json`으로 생기지만, 이걸 실제 durable memory graph로 import해야 한다.

필요한 명령:

```bash
hive memory import-run .runs/<run_id>
hive memory list drafts
hive memory approve <draft_id>
hive memory reject <draft_id>
hive memory search "query"
```

---

# 9. CapabilityOS는 아직 production 관점에서 거의 없음

현재 local worker에 `capability_extractor`는 있지만, CapabilityOS의 실제 schema/registry/recommendation layer는 아직 초기다.

필요한 것:

```text
TechnologyCard
Capability
WorkflowRecipe
ProviderRuntime
QualityProfile
Risk
LegacyRelation
EvidenceRef
```

그리고 최소 기능:

```bash
hive capability extract <README_or_url>
hive capability gap "Figma design to React"
hive workflow recommend "landing page implementation"
```

초기 workflow recipe 하나라도 넣어야 한다.

```text
workflow:
mos planning -> Claude handoff -> Codex implementation -> local summarize -> MemoryOS draft
```

---

# 10. Agent Society / 자기수정 루프는 아직 위험하게 미완성

이건 production에 넣기 전에 proposal-only로 시작해야 한다.

필요한 객체:

```text
AgentProfile
PerformanceRecord
PeerReview
UserFeedback
RoutingPolicyProposal
PromptMutationProposal
SafetyGate
```

하지만 자동 적용은 금지.

```text
허용:
- score 업데이트
- low-risk metric 업데이트

승인 필요:
- prompt 변경
- role 변경
- routing 변경
- permission 변경
```

명령:

```bash
hive society report
hive society propose
hive society approve <proposal_id>
```

---

# 11. Tests / Fixtures가 부족함

현재 TODO에도 parser fixture가 많이 남아 있다. Production에서는 fixture 없이는 안 된다.

필수 fixture:

```text
tests/fixtures/exports/chatgpt_redacted.json
tests/fixtures/exports/perplexity_markdown.zip
tests/fixtures/runs/minimal_valid_run/
tests/fixtures/providers/claude_prepared_result.yaml
tests/fixtures/providers/codex_failed_result.yaml
tests/fixtures/providers/local_worker_invalid_json.json
```

검증해야 할 것:

```text
- run artifact validation
- provider result validation
- memory draft validation
- event taxonomy validation
- local worker schema validation
- policy check validation
```

---

# 12. Install / Distribution이 아직 부족함

Production이라면 사용자가 이렇게 설치해야 한다.

```bash
pipx install memoryos
# or
curl -fsSL https://memoryos.dev/install.sh | bash
# or
npm install -g @memoryos/cli
```

현재 `pyproject.toml`에는 `mos = "memoryos.mos:main"` entrypoint가 있다. 
좋은 시작이지만 production에는 아래가 필요하다.

```text
- pipx install guide
- shell completion auto install
- hive alias
- binary health check
- first-run wizard
- uninstall command
- config migration
- versioned config schema
```

명령:

```bash
hive init
hive upgrade
hive doctor
hive doctor --fix
```

---

# 13. Observability / Auditability 부족

Production에서는 “무슨 일이 왜 일어났는지”가 보여야 한다.

필요한 로그:

```text
events.jsonl
provider stdout/stderr
policy decisions
context selection reasons
memory draft raw_refs
capability recommendation reasons
agent invocation commands
test results
```

그리고 명령:

```bash
hive audit run
hive audit provider codex
hive audit memory
hive audit policy
```

---

# 14. Production Readiness 기준

내 기준으로 production-ready v1은 아래를 만족해야 한다.

```text
1. 설치 후 hive doctor가 명확한 결과를 준다.
2. hardware/model/provider 상태를 자동 판단한다.
3. local model role routing이 benchmark 기반으로 설정된다.
4. 모든 provider invocation result가 공통 schema를 따른다.
5. policy gate 없이 repo write/shell/memory commit이 불가능하다.
6. .runs artifact는 validator를 통과한다.
7. run을 MemoryOS durable graph로 import할 수 있다.
8. memory draft review/approve/reject가 가능하다.
9. multi-session TUI view가 있다.
10. 실패한 provider/local worker도 artifact로 남는다.
11. 최소 fixture/test suite가 있다.
12. 사용자가 다음 action을 항상 알 수 있다.
```

---

# 15. 우선순위별 정리

## P0 — 지금 바로 해야 할 production hardening

```text
1. hive/mos next
2. provider result schema 확장
3. .memoryos/policy.yaml
4. hardware doctor
5. local model benchmark + role auto assignment
6. artifact freshness / producer tracking
7. run controller lock
8. tests/fixtures/runs/minimal_valid_run
```

## P1 — MemoryOS core

```text
1. AgentRun / AgentRunEvent
2. SourceArtifact
3. MemoryDraft durable records
4. HyperedgeEvent
5. user-origin vs AI-origin provenance
6. import-run command
```

## P2 — Hive Mind swarm

```text
1. SwarmRound
2. peer review artifacts
3. synthesize command
4. disagreements / decisions / open questions view
5. multi-session TUI views
```

## P3 — CapabilityOS

```text
1. TechnologyCard
2. Capability
3. WorkflowRecipe
4. ProviderRuntime
5. LegacyRelation
6. capability gap command
```

## P4 — Productization

```text
1. installer
2. desktop cockpit
3. backup/export/delete
4. privacy/security docs
5. encrypted local storage
```

---

# 최종 판단

현재는:

```text
Hive Mind prototype: 45~50%
MemoryOS production core: 20~25%
CapabilityOS production core: 5~10%
Production install/runtime: 20~30%
```

가장 부족한 건 기능 수가 아니라:

```text
1. hardware/runtime 자동 판단
2. local model benchmark 기반 role assignment
3. provider result contract 강화
4. permission/policy gate
5. run artifact → durable MemoryOS graph 연결
6. multi-session Hive Console
```

한 줄로:

> **지금은 Hive Mind의 뼈대가 있고, production으로 가려면 “자동 환경 진단, 역할 자동 배정, 안전한 provider execution, durable memory import, multi-session console”이 필요하다.**
