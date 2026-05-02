좋아. 지금 TUI는 **Hive Mind Console v0.1**로는 꽤 좋다.
특히 이미 다음 요소가 보인다.

```text
Run
Health
Pipeline
Agents
Artifacts
Latest Events
Live Transcript
Next
```

이건 `mos`/`hive`가 단순 채팅 CLI가 아니라 **structured blackboard control plane**이라는 걸 잘 보여준다. repo 문서에서도 `.runs/<run_id>/` 아래 `task.yaml`, `context_pack.md`, `handoff.yaml`, `events.jsonl`, `verification.yaml`, `memory_drafts.json`, `final_report.md`를 두는 구조가 명시되어 있어서, 지금 UI는 그 방향과 잘 맞는다. 

다만 네 말이 맞아. **한 terminal에 전부 넣으려니까 안 보임.**
Hive Mind는 단일 TUI dashboard가 아니라 **multi-session terminal cockpit**으로 가야 한다.

---

# 1. 지금 TUI의 좋은 점

현재 화면에서 좋은 점:

```text
1. Run 단위가 명확함
2. Pipeline이 보임
3. Agent별 상태가 보임
4. Artifact 상태가 보임
5. Latest Events가 있음
6. Next action이 있음
7. Safe Mode / Local 상태가 보임
```

특히 `Next` 패널이 중요하다.

```text
Next:
1. hive invoke local --role context
Reason: context compression has not completed
```

이건 Hive Mind의 핵심 질문인:

> “지금 다음에 누가 뭘 해야 하지?”

에 답하는 부분이야. 이 기능은 계속 중심에 둬야 한다.

---

# 2. 지금 부족한 부분

## 2.1 너무 많은 정보가 한 화면에 있음

현재는 모든 걸 한 화면에 넣고 있다.

```text
Pipeline
Agents
Artifacts
Events
Transcript
Next
```

이 구조는 snapshot에는 좋지만, 실제 작업 중에는 답답해진다.

특히:

```text
- artifact path가 잘림
- live transcript가 너무 작음
- latest events가 너무 적음
- agents detail이 부족함
- next action은 보이지만 왜 그런지 깊게 보기 어려움
```

---

## 2.2 Artifact와 Agent 상태가 약간 충돌해 보임

스크린샷에서 `context_pack` artifact는 `ok`인데, agent 쪽 `local-context-compressor`는 `pending`이고, Next는 `context compression has not completed`라고 말하고 있어.

이건 사용자가 헷갈릴 수 있다.

앞으로는 artifact status를 두 단계로 나눠야 해.

```text
artifact exists
artifact fresh
artifact produced_by_expected_agent
artifact validated
```

예:

```text
context_pack.md       exists ✓
local/context result  missing ○
freshness             stale !
```

즉 “파일이 있음”과 “그 단계가 완료됨”은 다르다.

---

## 2.3 Live Transcript는 별도 화면으로 빼야 함

지금 Live Transcript는 작은 박스에 raw log가 들어가 있어서 의미를 보기 어렵다.

이건 main board에 넣기보다 별도 terminal에서:

```bash
hive watch transcript
```

또는:

```bash
hive tui --view transcript
```

로 보는 게 맞다.

---

## 2.4 Disagreement / Decisions / Open Questions가 없음

Hive Mind는 단순 task runner가 아니라 군체지성이니까, 반드시 이 패널이 필요해.

```text
Disagreements
- Claude: implementation scope too broad
- Gemini: reviewer says missing acceptance criteria
- Local diff reviewer: schema risk medium

Decisions
- Use local context compressor first
- Keep Codex pending until handoff validated

Open Questions
- Should Codex execute or prepare-only?
- Is context_pack stale?
```

지금은 agent들이 각각 남긴 결과가 “의견 구조”로 보이지 않는다.

---

## 2.5 Agent 상태가 너무 얇음

현재 Agents 패널은:

```text
Agent / Role
Status
```

정도만 보인다.

군체지성용으로는 아래가 필요하다.

```text
provider
role
mode
permission
model
confidence
last artifact
last event
cost/latency
risk
```

예:

```text
claude/planner
provider: Claude
mode: plan
permission: read-only
status: prepared
artifact: planner_result.yaml
risk: low

codex/executor
provider: Codex
mode: workspace-write
permission: approval-required
status: pending
reason: waiting for handoff validation
```

---

## 2.6 Multi-session 지원이 없음

이게 가장 중요하다.

Hive Mind는 한 terminal에서 모든 걸 볼 수 없다.
앞으로는 여러 terminal이 같은 run을 attach해서 각자 다른 view를 봐야 한다.

```text
terminal 1: board / controller
terminal 2: events
terminal 3: transcript
terminal 4: agents
terminal 5: diff/check
```

그러려면 TUI는 “한 화면”이 아니라 **view system**이어야 한다.

---

# 3. 새 구조: Hive Console은 multi-view TUI

`hive tui`는 기본 board고, 각 view를 분리해야 한다.

```bash
hive tui --view board
hive tui --view agents
hive tui --view artifacts
hive tui --view events
hive tui --view transcript
hive tui --view diff
hive tui --view memory
hive tui --view society
```

또는 짧게:

```bash
hive board
hive agents
hive events
hive transcript
hive diff
hive memory
hive society
```

---

# 4. View별 역할

## 4.1 `hive board` — 메인 컨트롤 보드

가장 중요한 화면.

```text
목적:
현재 run이 어디까지 왔고, 다음 action이 무엇인지 보여줌.
```

구성:

```text
Header
Run Summary
Pipeline
Next Action
Agent Summary
Critical Missing Artifacts
Recent Events
```

예시:

```text
┌ Hive Mind ─────────────────────────────────────────────┐
│ Run: run_...     Project: Hive Mind     Mode: Safe     │
│ Phase: orchestration -> ready       Health: GOOD       │
├ Pipeline ──────────────────────────────────────────────┤
│ ✓ Intake  ✓ Route  ✓ Context  ✓ Deliberate  ✓ Handoff │
│ ○ Execute ○ Verify ○ Memory ○ Close                   │
├ Next ──────────────────────────────────────────────────┤
│ hive invoke local --role context                       │
│ Reason: local context worker has not completed          │
├ Agents ────────────────────────────────────────────────┤
│ local/context      pending                             │
│ claude/planner     prepared                            │
│ codex/executor     pending                             │
│ gemini/reviewer    pending                             │
├ Critical Missing ──────────────────────────────────────┤
│ checks_report, git_diff_report, commit_summary          │
└ Events ────────────────────────────────────────────────┘
```

이 화면은 **작업판**이어야 한다. transcript를 길게 보여주지 말 것.

---

## 4.2 `hive events` — 이벤트 스트림

```bash
hive events --follow
```

용도:

```text
라이브 로그 전용
events.jsonl tail
severity / provider / artifact 필터
```

예시:

```text
12:10:18  local/context   prepared_member
12:10:18  claude/planner  prompt_created
12:10:20  claude/planner  prepared_result
12:10:21  hive-mind       society_plan_ready
```

필터:

```bash
hive events --agent claude
hive events --type agent_failed
hive events --since 10m
```

---

## 4.3 `hive transcript` — 토론/회의록 화면

```bash
hive transcript
```

용도:

```text
agent들이 남긴 생각, critique, synthesis를 읽는 화면
```

여기는 raw JSON보다 사람이 읽을 수 있는 narrative가 필요하다.

```text
Round 1 — Planner
Claude:
- ...

Round 2 — Reviewer
Gemini:
- ...

Synthesis:
- Decision:
- Risk:
- Next:
```

지금 screenshot의 Live Transcript는 너무 작으니 이 화면으로 분리.

---

## 4.4 `hive agents` — agent detail board

```bash
hive agents
```

용도:

```text
각 provider/local worker 상태와 권한, role, artifact 보기
```

예시:

```text
Agent                  Provider       Mode          Status      Last Artifact
local/context          qwen3:8b       local         pending     -
claude/planner         claude         plan          prepared    planner_result.yaml
codex/executor         codex          workspace     pending     -
gemini/reviewer        gemini         plan          pending     -
local-intent-router    qwen3:8b       local         completed   routing_plan.json
```

여기서 선택하면 해당 provider output을 열 수 있어야 함.

```text
Enter = open artifact
r     = rerun
p     = show prompt
o     = show output
```

---

## 4.5 `hive artifacts` — artifact navigator

```bash
hive artifacts
```

용도:

```text
task.yaml, context_pack.md, handoff.yaml 등 파일 탐색
```

현재 Artifacts 패널은 path가 잘려서 정보량이 부족하다. 별도 view에서 전체 경로, 상태, freshness, producer를 보여줘야 한다.

```text
Artifact                  Status   Fresh   Producer              Path
task.yaml                 ok       yes     system                .runs/.../task.yaml
context_pack.md           ok       stale   system/local?          .runs/.../context_pack.md
handoff.yaml              ok       yes     claude/planner         .runs/.../handoff.yaml
verification.yaml         ok       initial system                .runs/.../verification.yaml
checks_report.json        missing  -       verifier              -
```

---

## 4.6 `hive diff` — git-first view

```bash
hive diff
```

용도:

```text
Aider 스타일 git diff / risk / commit summary
```

예시:

```text
Changed Files
M memoryos/harness.py
M memoryos/tui.py
A docs/HIVE_MIND.md

Risk
medium: TUI layout changed
low: docs added

Next
hive review-diff
hive check run
hive commit-summary
```

---

## 4.7 `hive memory` — memory draft review

```bash
hive memory
```

용도:

```text
이번 run에서 생성된 memory draft 검토
```

예시:

```text
Drafts

[decision] Hive Console should be multi-view, not one mega dashboard.
origin: mixed
confidence: 0.91
raw_refs: transcript.md, handoff.yaml

[Accept] [Edit] [Reject]
```

CLI에서는 완전 편집 UI보다 `approve/reject` 명령으로 시작해도 됨.

---

## 4.8 `hive society` — 군체지성 상태

```bash
hive society
```

용도:

```text
agent들의 역할, peer review, disagreement, performance를 보는 화면
```

예시:

```text
Disagreements
- Claude says Codex should wait for validated handoff.
- Local router says Codex can prepare dry-run command now.

Peer Reviews
- Gemini on Claude planner: pending
- Local diff reviewer on Codex output: not available

Agent Score Hints
- claude/planner: strong for architecture
- codex/executor: waiting for stable permission
- local/context: needs rerun
```

이건 아직 미래 기능이지만, Hive Mind라는 이름을 쓰려면 꼭 필요해진다.

---

# 5. 듀얼 모니터 / split session 구성

한 terminal에 전부 담지 말고, 공식적으로 **Hive Workspace Layout**을 지원하자.

## Layout A — 기본 듀얼 모니터

### Monitor 1: Controller

```bash
hive board --control
```

또는:

```bash
hive tui --view board --control
```

역할:

```text
- 현재 run 관리
- next action 실행
- agent invoke
- verify/memory/check 실행
```

### Monitor 2: Observers

터미널 2개 또는 tmux panes:

```bash
hive events --follow
hive transcript
hive agents
hive diff
```

구성:

```text
┌──────────────────────────────┐
│ hive events --follow          │
├──────────────────────────────┤
│ hive transcript               │
├──────────────────────────────┤
│ hive agents / hive diff       │
└──────────────────────────────┘
```

---

## Layout B — tmux 자동 생성

명령:

```bash
hive workspace --layout dual
```

자동으로 tmux 세션 생성:

```text
window 1: board
window 2: events
window 3: transcript
window 4: agents
window 5: diff
```

또는:

```bash
hive workspace --layout dev
```

```text
pane 1: hive board
pane 2: hive events --follow
pane 3: hive diff
pane 4: hive agents
```

---

# 6. 다중 세션을 위해 필요한 안전장치

여러 terminal에서 같은 run을 보면 좋지만, 동시에 명령 실행하면 위험하다.

그래서 session role이 필요하다.

```text
controller
observer
worker
```

## Controller

```text
명령 실행 가능
hive invoke
hive verify
hive memory draft
hive check run
```

## Observer

```text
읽기 전용
events/transcript/agents/artifacts 보기만 가능
```

## Worker

```text
특정 provider 실행 중인 session
```

명령:

```bash
hive attach current --role controller
hive attach current --role observer
```

lock 파일:

```text
.runs/<run_id>/control.lock
```

내용:

```json
{
  "session_id": "sess_...",
  "role": "controller",
  "started_at": "...",
  "last_heartbeat": "..."
}
```

이걸 안 하면 두 terminal에서 동시에 Codex 실행하는 사고가 날 수 있다.

---

# 7. 현재 UI에서 바로 고칠 것

## 7.1 `Phase`를 더 명확히

현재:

```text
Phase orchestration -> ready
```

이건 조금 추상적이다.

추천:

```text
Phase: handoff-ready
Next: local/context required
```

또는:

```text
Phase: deliberate.completed / execute.pending
```

---

## 7.2 `Local 4/9` 설명

상단의 `Local 4/9`가 무엇인지 직관적이지 않다.

추천:

```text
Workers: Local 4/9
```

또는:

```text
Local Workers: 4 of 9 ready
```

---

## 7.3 Missing Artifacts 분류

현재 missing artifacts는 3개:

```text
checks_report
git_diff_report
commit_summary
```

하지만 이들은 지금 단계에서 필수인지 optional인지 다르다.

분류 필요:

```text
Required for current phase
Optional
Post-execution
```

예:

```text
Missing Artifacts
Required: none
Post-execution: git_diff_report, commit_summary
Optional: checks_report
```

---

## 7.4 Agent status에 reason 추가

```text
codex-executor  pending
```

보다:

```text
codex-executor  pending  reason: waiting for validated handoff
```

이 좋다.

---

## 7.5 Transcript는 raw JSON 숨기기

현재 Live Transcript에 raw JSON snippet이 보인다.
기본은 사람이 읽는 요약, raw는 toggle.

```text
t = toggle raw
```

---

# 8. 새 TUI 구성안

## 기본 `hive board`

```text
┌─ Hive Mind ──────────────────────────────────────────────────────┐
│ Run run_...  Project Hive Mind  Mode Safe workspace-write  12:11 │
├─ Current ────────────────────────┬─ Next ────────────────────────┤
│ Task: hi it's a test             │ 1. hive invoke local --role... │
│ Phase: handoff-ready             │ Reason: local context missing  │
│ Health: GOOD                     │ 2. hive status                 │
│ Missing: 0 required / 3 optional │ 3. hive check run              │
├─ Pipeline ───────────────────────┴───────────────────────────────┤
│ ✓ Intake ✓ Route ✓ Context ✓ Deliberate ✓ Handoff                │
│ ○ Execute ○ Verify ○ Memory ○ Close                              │
├─ Agents ─────────────────────────────────────────────────────────┤
│ local/context      pending     qwen3:8b       reason: not run     │
│ claude/planner     prepared    claude         planner_result ok   │
│ codex/executor     pending     codex          waiting handoff     │
│ gemini/reviewer    pending     gemini         optional            │
│ local/router       completed   qwen3:8b       routing_plan ok     │
├─ Decisions / Open Questions ─────────────────────────────────────┤
│ Decision: current run should clarify provider/local member roles  │
│ Open: should Codex execute or remain prepare-only?                │
├─ Latest Events ──────────────────────────────────────────────────┤
│ 12:10:21 hive-mind society_plan_ready                             │
└──────────────────────────────────────────────────────────────────┘
```

핵심은 **board에서는 긴 artifact list를 줄이고, decision/open question을 넣는 것**.

Artifact 상세는 `hive artifacts`로 빼자.

---

# 9. 명령 체계 제안

현재 `mos`가 있다면, `hive`는 alias 또는 새 binary로.

```bash
hive board
hive events --follow
hive transcript
hive agents
hive artifacts
hive diff
hive memory
hive society
hive next
```

기존 명령과 연결:

```bash
mos tui
= hive board

mos status
= hive status

mos invoke ...
= hive invoke ...
```

처음에는 `mos` 유지하고, UI 안에서 branding만 `Hive Mind`로 해도 된다.

---

# 10. 구현 우선순위

바로 해야 할 순서:

```text
1. Add `hive next` or `mos next`
2. Add TUI views: board/events/agents/artifacts/transcript
3. Make transcript a separate full view
4. Add controller/observer session mode
5. Add artifact freshness/producer metadata
6. Add decisions/open questions/disagreements panel
7. Add tmux workspace layout generator
```

---

# 11. 한 줄 결론

현재 TUI는 **좋은 단일 run snapshot**이다.
하지만 Hive Mind의 최종 목표에는 한 화면이 너무 좁다.

앞으로는:

```text
Hive Console
= multi-view terminal cockpit

hive board
= controller

hive events / transcript / agents / diff
= observer sessions

hive workspace --layout dual
= 듀얼 모니터용 split launcher
```

로 가야 한다.

가장 중요한 설계 원칙:

> **Hive Mind는 하나의 큰 TUI가 아니라, 같은 run을 여러 terminal view가 동시에 관찰하고 조작하는 multi-session control plane이어야 한다.**
