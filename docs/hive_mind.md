# Hive Mind

Hive Mind is the swarm harness layer for `hive`: a user-governed control plane that coordinates Claude, Codex, Gemini, local LLM workers, and Hive Mind run artifacts without replacing the provider CLIs.

확인 기준을 “**hive = 흩어진 Claude/Codex/Gemini/local LLM CLI를 군체지성처럼 묶는 wrapped CLI**”로 잡으면, 현재 구현은 꽤 좋은 1차 골격이 있어. 다만 아직 **진짜 swarm loop**라기보다는 **structured blackboard + provider artifact generator + TUI** 단계야.

## 현재 잘 된 부분

`hive`의 핵심 방향은 이미 맞게 구현되어 있어. `harness.py`에 `.runs` 기반 구조화 blackboard가 있고, pipeline도 `intake → route → context → deliberate → handoff → execute → verify → memory → close`로 정의되어 있어. 이건 여러 CLI가 하나의 run 상태를 공유하게 만드는 핵심 골격이다. 

local worker도 꽤 좋다. `intent_router`, `classifier`, `memory_extractor`, `context_compressor`, `handoff_drafter`, `log_summarizer`, `capability_extractor`, `diff_reviewer`가 이미 역할별 worker로 정의되어 있고, 모델도 `qwen3`, `deepseek-coder`, `deepseek-coder-v2`로 잘 나뉘어 있다. 특히 `confidence`, `should_escalate`, `escalation_reason`을 schema에 넣은 건 아주 좋다. 

검증도 시작되어 있다. `run_validation.py`에서 run artifact, event taxonomy, memory draft schema, provider result schema를 검사하고 있고, provider result에 `schema_version`, `agent`, `role`, `status`, `provider_mode`를 요구한다. 이건 “agent들이 말만 하고 끝나는 게 아니라, artifact contract를 지키게 하는” 방향이라 중요하다. 

즉 현재 상태는:

```text
manual shared folder
→ structured blackboard
→ wrapper CLI
→ TUI status
```

까지는 잘 와 있음.

---

## 부족한 부분 1: Swarm의 “상호작용”이 아직 약함

지금은 각 provider가 artifact를 남기는 구조는 있는데, **agent들이 서로의 결과를 읽고 다음 행동을 결정하는 feedback loop**가 아직 약해.

현재는 대략:

```text
local route
→ claude prompt 준비
→ codex prompt 준비
→ gemini prompt 준비
→ verify / memory draft
```

에 가깝다.

최종 목표는:

```text
local router가 작업 분해
→ Claude가 설계/비판
→ Codex가 구현
→ Gemini가 대안 리뷰
→ local diff_reviewer가 위험 요약
→ Claude가 최종 판단
→ local memory_extractor가 기억 초안 생성
→ hive가 다음 action 추천
```

처럼 **다단계 상호 반응**이 되어야 해.

필요한 추가 객체:

```text
PeerReviewArtifact
AgentResponseSummary
FollowupAction
SwarmRound
```

추천 TODO:

```text
- Add swarm round artifact: .runs/<run>/rounds/round_001.yaml
- Add peer review command: hive review peer --from gemini --target codex
- Add synthesis step: hive synthesize
- Add next-action planner that reads all provider results, not just missing artifacts
```

---

## 부족한 부분 2: `hive next`가 필요함

현재 `recommend_next_action()`은 구현되어 있고 `hive status`/TUI에서 next action을 보여주는 구조는 있어. 그런데 독립 명령으로 `hive next`가 있으면 훨씬 좋아.

군체지성 wrapped CLI에서 제일 중요한 질문은 이거야.

> “지금 다음에 누가 뭘 해야 하지?”

따라서:

```bash
hive next
```

출력은 이렇게 되어야 해.

```text
Next recommended action:
  hive invoke claude --role planner --execute

Reason:
  handoff.yaml is missing and task_type=implementation.

If you want faster local-only path:
  hive invoke local --role handoff --complexity strong
```

이 명령 하나가 있으면 사용자는 Claude/Codex/Gemini를 각각 켜서 고민할 필요가 줄어든다.

---

## 부족한 부분 3: Provider Adapter의 실제 실행 안정성

현재 provider result validation은 있지만, TODO에도 “Harden provider result validation”이 남아 있고, Codex는 아직 prepare-only 중심인 것으로 보인다. `PROVIDER_HARNESS_GUIDE.md`에서도 Codex execution이 local access prompt에 의해 gated될 수 있고, 실패를 artifact로 남기는 상태라고 되어 있다. 

이건 좋은 방어지만, 최종적으로는 provider별 adapter contract를 더 강하게 해야 해.

필요한 필드:

```yaml
schema_version: 1
provider: codex
agent: codex-executor
role: executor
provider_mode: prepare_only | execute_supported | unavailable
permission_mode: read_only | plan | workspace_write | full_auto | danger
command:
prompt_path:
stdout_path:
stderr_path:
output_path:
returncode:
started_at:
finished_at:
files_changed:
commands_run:
tests_run:
risk_level:
```

지금 provider result schema는 최소한만 요구하고 있으니, swarm 실행용으로는 너무 얇다.

추천 TODO:

```text
- Expand ProviderResult schema with permission_mode, stdout/stderr, started_at/finished_at, files_changed, commands_run.
- Add provider adapter smoke tests for claude/gemini/local; codex prepare-only fixture.
- Add provider execution policy: read-only default, workspace-write explicit, danger forbidden unless env flag.
```

---

## 부족한 부분 4: Task decomposition이 아직 “역할 지정” 수준

local `intent_router`가 actions를 뽑는 구조는 좋지만, 최종적으로는 작업을 subtask graph로 만들어야 해.

현재 action schema는:

```json
{
  "provider": "local|claude|codex|gemini",
  "role": "...",
  "reason": "...",
  "execute": false
}
```

이건 시작으로 좋지만, 군체지성에는 부족하다.

필요한 건:

```json
{
  "subtask_id": "st_001",
  "depends_on": [],
  "objective": "...",
  "assigned_agent": "claude",
  "role": "planner",
  "expected_artifact": "handoff.yaml",
  "acceptance_criteria": [],
  "risk": "medium",
  "fallback_agent": "gemini"
}
```

즉, `routing_plan.json`이 단순 list가 아니라 **task DAG**가 되어야 해.

추천 TODO:

```text
- Upgrade routing_plan.json from action list to subtask DAG.
- Add dependency-aware next action.
- Add hive plan graph/text view.
```

---

## 부족한 부분 5: MemoryOS와 연결이 아직 run-local에 머물러 있음

지금 `memory_drafts.json`은 run artifact로는 좋다. 하지만 최종 목표는 MemoryOS graph substrate로 넘어가야 해.

현재 부족한 것:

```text
- AgentRun / AgentRunEvent record화
- run-derived memory draft → raw refs 연결
- graph edit queue
- accepted/rejected memory lifecycle
- user-origin vs AI-origin provenance
```

TODO에도 이 부분이 남아 있다. 이건 다음 큰 병목이 맞다.

추천 순서:

```text
1. Define AgentRun / AgentRunEvent schema.
2. Import .runs/<run_id> into MemoryOS as Observation.
3. Link provider outputs as Evidence.
4. Convert memory_drafts.json to reviewable MemoryDraft records.
5. Add accepted/rejected state.
```

---

## 부족한 부분 6: Oh-my-openagent식 “battery included setup”은 아직 약함

`hive init`, `hive local setup`, `hive agents detect`, `hive settings shell`은 좋다. 그런데 Oh-my-openagent/oh-my-opencode류처럼 “한 번 설치하면 바로 좋은 프리셋이 깔리는 느낌”은 더 필요해.

추가하면 좋은 것:

```bash
hive preset install default
hive preset install memoryos-dev
hive preset install coding-swarm
hive preset install docs-router
```

각 preset이 설치하는 것:

```text
.hivemind/checks/*.md
.hivemind/skills/*.md
.hivemind/routing.yaml
.hivemind/agents.yaml
AGENTS.md patch suggestion
```

즉, 현재는 config 파일을 만들긴 하지만, “swarm operating preset” 경험이 약하다.

---

## 부족한 부분 7: TUI는 좋지만 “군체지성 회의판”은 아직 아님

현재 TUI는 run health/provider/missing artifacts 중심이다. 이건 좋다. 다음은 **agent들의 의견 차이**를 보여줘야 해.

추가 패널 후보:

```text
Disagreements
- Claude: Codex implementation misses raw_refs
- Gemini: UI scope too broad
- Local reviewer: schema risk medium

Decisions
- Use React Flow for MVP
- Keep Codex prepare-only until execution verified

Open Questions
- Should memory draft approval be blocking?
```

즉 TUI가 단순 진행판에서 **swarm deliberation board**로 진화해야 함.

---

## 부족한 부분 8: 권한 정책이 더 명시적이어야 함

군체지성 harness에서 제일 위험한 부분은 “여러 CLI가 각자 권한을 가지고 실행되는 것”이야.

지금도 safe/read-only를 기본으로 보는 철학은 들어가 있지만, 제품 수준에서는 `policy.yaml`이 필요해.

예:

```yaml
permissions:
  default:
    shell: deny
    repo_write: deny
    memory_commit: deny

  claude.planner:
    repo_read: allow
    repo_write: deny
    memory_write_draft: allow

  codex.executor:
    repo_read: allow
    repo_write: allow_with_approval
    shell: allowlist
    memory_commit: deny

  local.memory_extractor:
    repo_read: deny
    memory_write_draft: allow
```

그리고 `hive invoke` 전에 항상 policy check.

추천 TODO:

```text
- Add .hivemind/policy.yaml.
- Add hive policy check.
- Provider invocation must record effective permissions.
- Danger/full-auto modes require explicit --confirm-danger and isolated worktree.
```

---

## 부족한 부분 9: Reference 대비 차별점은 있는데 README에 더 선명해야 함

Claude CLI / Codex CLI / OpenCode / Oh-my-openagent와 비교했을 때 `hive`의 포지션은:

```text
Not another coding agent.
A swarm harness for existing CLIs.
```

README 첫 문장을 바꾸면 좋다.

추천 문장:

```md
# MemoryOS / hive

`hive` is a swarm harness CLI for coordinating Claude, Codex, Gemini, local LLM workers, and Hive Mind run artifacts.

It does not replace provider CLIs.
It wraps them into one structured blackboard loop:
task → route → context → deliberate → handoff → execute → verify → memory.
```

이걸 확실히 박아야 해.

---

# 내 판단: 현재 hive 완성도

목표가 “군체지성용 wrapped CLI”라면:

```text
Core blackboard: 75%
CLI command surface: 70%
TUI/status board: 60%
Provider wrapping: 50%
Local worker layer: 55%
Swarm interaction loop: 25%
MemoryOS integration: 20%
Safety/policy layer: 30%
```

전체로 보면 **약 45%** 정도야.

단순 TODO 완료율은 31%였지만, `hive` 자체만 놓고 보면 훨씬 더 진척되어 있어. 다만 “흩어진 CLI들이 군체지성처럼 동작”하려면 아직 **peer review / synthesis / task DAG / policy / memory import**가 필요하다.

---

# 바로 넣을 다음 TODO 제안

지금 repo에 추가할 “hive Swarm Hardening” 섹션은 이렇게 쓰면 좋아.

```md
## hive Swarm Hardening

- [ ] Add `hive next` to print the dependency-aware next recommended action.
- [ ] Expand `routing_plan.json` into a subtask DAG with dependencies, expected artifacts, and fallback agents.
- [ ] Add `SwarmRound` artifact under `.runs/<run_id>/rounds/`.
- [ ] Add peer review artifacts: `peer_review_<reviewer>_on_<target>.yaml`.
- [ ] Add `hive synthesize` to merge Claude/Codex/Gemini/local outputs into one decision/handoff summary.
- [ ] Expand provider result schema with permission mode, stdout/stderr paths, files_changed, commands_run, started_at, finished_at.
- [ ] Add `.hivemind/policy.yaml` and enforce it in `hive invoke`.
- [ ] Add `AgentRun` and `AgentRunEvent` import from `.runs/<run_id>`.
- [ ] Add MemoryOS review queue for run-derived memory drafts.
- [ ] Add TUI panel for disagreements, decisions, and open questions.
```

---

# 가장 중요한 다음 작업 3개

내가 지금 바로 Codex에게 시킨다면 이 순서야.

```text
1. Add `hive next`
2. Expand provider result schema + validation
3. Add SwarmRound / peer review / synthesize artifacts
```

왜냐하면 이 셋이 들어가면 `hive`가 단순 artifact generator에서 **진짜 군체지성 조율 CLI**로 넘어가기 시작해.

한 줄 결론:

> 지금 `hive`는 “군체지성 CLI의 뼈대”는 이미 있다. 부족한 건 agent들이 서로의 산출물을 평가·종합하고, dependency-aware next action을 따라 실제 loop를 도는 swarm coordination layer다.

응. **TUI/CLI control surface는 `Hive Mind`로 재명명하는 게 맞아.**
다만 정확히는 이렇게 잡는 게 좋아.

> **Hive Mind는 MemoryOS와 CapabilityOS 위에서 여러 agent/CLI/local LLM을 군체지성처럼 조율하는 실행·토론·작업 운영 계층이다.**

즉, `Hive Mind = TUI`만은 아니고, TUI는 **Hive Mind Console**이야.

---

# 최종 3대 축

```text
MemoryOS
= 기억 계층

CapabilityOS
= 능력/도구/워크플로우 계층

Hive Mind
= 여러 AI/agent/CLI를 조율하는 군체지성 실행 계층
```

한 문장으로:

> **MemoryOS는 기억하고, CapabilityOS는 무엇이 가능한지 알고, Hive Mind는 여러 agent를 모아 생각하고 실행한다.**

---

# 각자의 역할

## 1. MemoryOS

사용자와 프로젝트의 장기 기억.

```text
- AI 대화
- 결정
- 미해결 질문
- agent run logs
- memory drafts
- hyperedges
- raw_refs
- project state
```

질문:

```text
“우리는 과거에 무엇을 생각했고, 무엇을 결정했는가?”
```

현재 Hive Mind repo의 `.runs` blackboard와 memory draft artifact 흐름은 MemoryOS가 ingest할 실행 증거 기반이야. `docs/TUI_HARNESS.md`에서도 run folder가 `task.yaml`, `context_pack.md`, `handoff.yaml`, `events.jsonl`, `verification.yaml`, `memory_drafts.json`, `final_report.md`를 가진 structured blackboard로 정의돼 있어. 

---

## 2. CapabilityOS

세계의 능력 지도.

```text
- MCP
- provider CLI
- local model
- app
- skill
- workflow recipe
- capability module
- legacy comparison
- quality/risk profile
```

질문:

```text
“이 작업을 가장 잘하려면 어떤 모델, 앱, MCP, Skill, workflow를 써야 하는가?”
```

CapabilityOS 안에는 나중에 이런 서브시스템이 들어감.

```text
Capability Radar
├── Surfer
│   └── 최신 MCP / 앱 / 논문 / GitHub / 커뮤니티 탐색
└── Discriminator
    └── 쓸만한지, 위험한지, legacy 대비 나은지 평가
```

---

## 3. Hive Mind

여러 agent를 하나의 집단 지능처럼 묶는 orchestration layer.

```text
- Claude planner
- Codex executor
- Gemini reviewer
- local context compressor
- local memory extractor
- local diff reviewer
- future opencode/goose/openclaude adapters
```

질문:

```text
“이 작업을 위해 누가 먼저 생각하고, 누가 구현하고, 누가 검증하고, 무엇을 기억해야 하는가?”
```

현재 `hive`는 이미 Hive Mind의 초기형이야. `harness.py`에 pipeline이 `intake → route → context → deliberate → handoff → execute → verify → memory → close`로 잡혀 있고, 이것이 곧 Hive Mind의 작업 진행 순서가 된다. 

---

# 이름 구조 제안

나는 이렇게 명명하는 게 제일 좋다고 봐.

```text
MemoryOS
  기억 substrate

CapabilityOS
  능력 ontology / workflow registry

Hive Mind
  agent swarm harness / deliberation + execution control plane

hive
  Hive Mind를 실행하는 CLI binary

Hive Console
  hive tui / terminal UI

Hive Cockpit
  나중에 만드는 Desktop UI
```

즉:

```bash
hive run "task"
hive tui
hive hive
```

이런 식으로 갈 수 있어.

---

# 기존 용어와의 매핑

기존에 말하던 것들을 정리하면:

```text
Chatbot Harness
→ Hive Mind의 Deliberation Layer

Agent Harness
→ Hive Mind의 Execution Layer

Local LLM Workers
→ Hive Mind의 Clerk / Scout / Reviewer workers

Surfer / Discriminator
→ CapabilityOS의 Radar Layer

Memory Graph / Hypergraph
→ MemoryOS의 Core Substrate

hive TUI
→ Hive Console
```

그래서 최종 구조는:

```text
Hive Mind
├── Deliberation Layer
│   ├── Claude
│   ├── GPT
│   ├── Gemini
│   ├── Perplexity
│   └── local synthesis worker
│
├── Execution Layer
│   ├── Codex
│   ├── Claude Code
│   ├── Gemini CLI
│   ├── opencode
│   └── goose
│
├── Local Worker Layer
│   ├── context compressor
│   ├── handoff drafter
│   ├── memory extractor
│   ├── diff reviewer
│   └── log summarizer
│
└── Control Layer
    ├── run state
    ├── event log
    ├── handoff artifacts
    ├── policy
    └── next action planner
```

---

# 생태계 통합 그림

```text
                 WORLD
       GitHub / arXiv / X / Reddit / MCP
                  │
                  ▼
            CapabilityOS
     tools / MCP / skills / workflows
                  │
                  ▼
User ───────► Hive Mind ◄──────► MemoryOS
 intent       swarm control       memory / graph
                  │
                  ▼
          Agents / CLIs / Tools
                  │
                  ▼
              Product / Work
                  │
                  ▼
          MemoryOS + CapabilityOS update
```

---

# 핵심 철학

이제 네 시스템은 이렇게 정의할 수 있어.

> **MemoryOS는 기억의 OS, CapabilityOS는 능력의 OS, Hive Mind는 여러 AI/agent가 그 위에서 군체지성처럼 사고하고 실행하는 운영체제다.**

또는 더 짧게:

```text
MemoryOS = remembers
CapabilityOS = knows what is possible
Hive Mind = coordinates the swarm
```

한국어로:

```text
MemoryOS는 기억한다.
CapabilityOS는 가능성을 안다.
Hive Mind는 군체를 움직인다.
```

---

# 현재 Hive Mind repo 기준으로 다음 이름 변경 방향

지금 당장 대규모 rename을 하면 위험하니까, 단계적으로 가는 게 좋다.

## 1단계: 문서에서 개념 정리

추가할 문서:

```text
docs/hive_mind.md
```

내용:

```text
Hive Mind is the swarm harness layer of MemoryOS.
It coordinates provider CLIs, local LLM workers, run artifacts, peer review, synthesis, and next actions.
```

## 2단계: TUI 문서 rename

현재:

```text
docs/TUI_HARNESS.md
```

추가/변경:

```text
docs/HIVE_CONSOLE.md
```

또는 기존 문서 첫 줄에:

```text
The `hive` TUI is now called Hive Console.
```

## 3단계: CLI 명령 추가

기존 `hive tui` 유지하면서 alias 추가.

```bash
hive hive
hive hive status
hive hive next
```

처음에는 `hive hive` = `hive tui` alias면 충분해.

## 4단계: Swarm 기능 추가

```bash
hive next
hive synthesize
hive peer-review
hive hive report
```

---

# 네이밍 주의점

`Hive Mind`는 강력한 이름인데, 약간 위험한 느낌도 있어. 그래서 제품 메시지에서는 이렇게 완화하면 좋아.

```text
Hive Mind is not autonomous control.
Hive Mind is a user-governed agent swarm.
```

즉:

> **Hive Mind는 agent들이 마음대로 움직이는 시스템이 아니라, 사용자가 통제하는 군체지성 작업판이다.**

이 원칙은 꼭 박아야 해.

```text
Agents may suggest.
Hive Mind may coordinate.
User remains sovereign.
```

---

# 최종 결론

응, 방향은 이렇게 잡자.

```text
MemoryOS
= 개인/프로젝트/agent의 기억과 hypergraph substrate

CapabilityOS
= 세계의 AI tool / MCP / skill / workflow / legacy capability ontology

Hive Mind
= 흩어진 Claude, Codex, Gemini, local LLM, future agent CLI들을 하나의 군체지성 run loop로 묶는 orchestration layer

hive
= Hive Mind를 터미널에서 조작하는 wrapped CLI

Hive Console
= hive tui

Hive Cockpit
= 미래 Desktop UI
```

가장 좋은 최종 문장:

> **MemoryOS remembers, CapabilityOS maps capabilities, and Hive Mind coordinates agents into collective work.**
