좋아. 그건 단순 multi-agent가 아니라 **Agent Auto Society**야.

핵심 아이디어는 이거야.

> 각 agent가 작업을 수행하고, 그 결과에 대한 사용자 반응·다른 agent의 평가·검증 결과·실패 로그를 바탕으로 자기 역할, 프롬프트, routing rule, 추론 디자인을 점진적으로 수정하는 시스템.

즉:

```text
Agent가 일함
→ 결과가 남음
→ 사용자/다른 agent/테스트가 평가함
→ 성과와 실패가 기록됨
→ agent profile과 prompt가 업데이트됨
→ 다음에는 더 적합한 역할을 맡음
```

이건 강력하지만, 네 말대로 리스크도 크다. 그래서 **자가수정 루프를 직접 프롬프트에 반영하는 게 아니라, “제안 → 검증 → 승인 → 적용” 구조로 제한**해야 해.

---

# 1. 이 시스템의 이름

나는 이렇게 부르고 싶어.

## **Agent Auto Society**

여러 agent가 각자의 전문 영역, 성과 기록, 실패 패턴, 상호 평가를 바탕으로 역할을 분화하고 진화하는 agent 사회.

구성 요소:

```text
Agent Profile
Capability Score
Performance Memory
Peer Review
User Feedback
Prompt Mutation
Routing Policy Update
Safety Gate
```

한 문장으로:

> **Agent Auto Society는 agent들이 작업 로그와 피드백을 통해 자신의 역할과 사용법을 점진적으로 교정하는 자기조직화 agent 운영 시스템이다.**

---

# 2. 왜 필요한가

지금은 네가 머리로 이렇게 판단하고 있어.

```text
이건 Claude에게 맡기자.
이건 Codex가 낫다.
이건 local LLM으로 충분하다.
이건 직접 봐야 한다.
```

그런데 작업이 많아지면 이 판단도 시스템화해야 해.

예를 들어:

```text
Claude는 architecture handoff는 잘하지만 구현 세부 파일 경로를 자주 과하게 추측한다.
Codex는 명확한 acceptance criteria가 있으면 잘하지만, 제품 철학이 모호하면 잘못 구현한다.
local LLM은 memory draft는 싸게 잘 만들지만, decision과 idea를 종종 혼동한다.
DeepSeek coder는 테스트 로그 요약은 잘하지만, 보안 위험은 잘 못 본다.
```

이런 경험이 쌓이면 agent profile이 바뀌어야 해.

---

# 3. 핵심 루프

```text
Run
→ Observe
→ Evaluate
→ Attribute
→ Update Proposal
→ Safety Review
→ Apply
→ Monitor
```

풀면:

```text
1. Run
   agent가 작업 수행

2. Observe
   로그, diff, 테스트, 사용자 반응, peer review 수집

3. Evaluate
   결과 품질 평가

4. Attribute
   성공/실패 원인을 agent, prompt, context, tool, task ambiguity로 분해

5. Update Proposal
   agent profile, routing rule, prompt, skill 수정안 생성

6. Safety Review
   자동 적용 가능한지 검토

7. Apply
   낮은 위험 수정만 적용

8. Monitor
   다음 run에서 성과 변화 확인
```

---

# 4. 저장해야 할 로그

자가수정 루프를 만들려면 단순 대화 로그가 아니라 **성과 로그**가 필요해.

```json
{
  "run_id": "run_001",
  "task_type": "implementation",
  "project": "MemoryOS",
  "assigned_agents": ["claude_planner", "codex_executor", "local_summarizer"],
  "context_refs": ["mem_123", "he_456"],
  "handoff_quality": 0.82,
  "execution_success": true,
  "tests_passed": true,
  "user_satisfaction": "accepted_with_minor_edits",
  "peer_reviews": [
    {
      "reviewer": "claude",
      "target": "codex",
      "score": 0.78,
      "notes": "Implementation met criteria but missed raw_refs inspector detail."
    }
  ],
  "failure_modes": [
    "acceptance_criteria_partial"
  ],
  "cost": {
    "local_tokens": 12000,
    "paid_tokens": 3500
  }
}
```

이걸 기반으로 agent별 성과가 축적돼.

---

# 5. Agent Profile이 자동으로 진화해야 함

각 agent는 이런 profile을 가진다.

```yaml
agent_id: codex_executor
role: implementation_agent

strengths:
  - repo_editing
  - test_fixing
  - multi_file_changes

weaknesses:
  - vague_product_strategy
  - unclear_acceptance_criteria

requires:
  - explicit_files_or_search_scope
  - acceptance_criteria
  - context_pack_under_4000_tokens

scores:
  implementation_success: 0.86
  test_fixing: 0.82
  product_alignment: 0.61
  instruction_following: 0.79
  cost_efficiency: 0.72

routing:
  prefer_for:
    - implementation
    - refactor
    - parser
    - mcp_server
  avoid_for:
    - early_ideation
    - ambiguous_strategy
```

그리고 시간이 지나면 이렇게 수정된다.

```yaml
learned_rule:
  - "Do not route vague UI/product tasks directly to codex. Require Claude handoff first."
```

---

# 6. 사용자 반응을 어떻게 반영하나

사용자 반응은 매우 중요하지만, 위험하게 쓰면 안 돼.

사용자 반응 종류:

```text
accepted
accepted_with_edits
rejected
asked_for_redo
said “이게 아니야”
continued_building_on_it
manually_fixed_output
ignored_output
```

이건 score로 바꿀 수 있어.

```text
accepted → +1
accepted_with_minor_edits → +0.6
major_redo_needed → -0.5
rejected → -1
manual_fix_after_agent → 실패 원인 분석 필요
```

단, 사용자 감정 하나로 prompt를 바로 바꾸면 안 돼.
여러 run의 패턴으로 봐야 해.

---

# 7. Peer Review도 필요함

다른 agent가 평가하게 하는 건 좋다.
단, **서로 자유롭게 칭찬/비판**하게 하면 의미가 약해.

구조화된 peer review가 필요해.

```json
{
  "reviewer": "claude_reviewer",
  "target_agent": "codex_executor",
  "artifact": "diff.patch",
  "criteria": {
    "meets_acceptance": 0.8,
    "code_quality": 0.75,
    "project_alignment": 0.7,
    "risk": 0.25
  },
  "found_issues": [
    "Raw refs inspector is not implemented, only stubbed."
  ],
  "recommendation": "request_followup_patch"
}
```

Peer Review는 user feedback보다 낮은 권한, tests보다 낮은 권한으로 둔다.

우선순위:

```text
1. 실제 테스트/빌드/검증 결과
2. 사용자 명시 피드백
3. 다른 agent의 구조화된 리뷰
4. agent self-report
```

agent self-report는 가장 낮게 봐야 해.

---

# 8. 추론 디자인 자가수정은 어떻게 하나

자가수정 대상은 5개로 나눠야 해.

## 1. Routing Policy 수정

가장 안전하고 유용함.

예:

```text
“UI feature task는 바로 Codex로 보내지 말고 Claude handoff를 먼저 거친다.”
```

## 2. Context Pack 형식 수정

예:

```text
Codex가 raw_refs 정책을 자주 놓침
→ context pack의 acceptance criteria에 raw_refs 관련 항목을 항상 명시
```

## 3. Prompt Template 수정

위험도 중간.

예:

```text
local memory extractor가 decision을 과추출함
→ “사용자가 명시적으로 수용하지 않은 것은 decision으로 표시하지 말 것” 추가
```

## 4. Skill 수정

위험도 중간~높음.

예:

```text
implementation-handoff skill에 “files_to_modify가 없으면 Codex 실행 금지” 추가
```

## 5. Agent Capability Profile 수정

안전함.

예:

```text
deepseek-coder:6.7b는 parser 초안은 잘하지만 최종 코드 리뷰에는 부적합
```

---

# 9. 자동 적용 가능한 것과 승인 필요한 것

여기가 중요해.

## 자동 적용 가능

```text
routing score 미세 조정
agent capability score 업데이트
context pack 압축 규칙 조정
low-risk prompt wording 개선안 draft 생성
model latency/cost 통계 업데이트
```

## 승인 필요

```text
system prompt 변경
Skill 수정
memory commit policy 변경
agent 권한 상승
repo write 권한 변경
external tool 연결
자동 commit 활성화
```

## 절대 자동 적용 금지

```text
보안 정책 완화
raw data 외부 전송 허용
agent에게 unrestricted shell 권한 부여
memory draft를 바로 active로 승격
사용자 선호/정체성 추론을 장기 기억으로 저장
```

---

# 10. 리스크

네가 감지한 리스크가 맞다. 꽤 크다.

## 1. Self-reinforcing error

agent가 잘못된 평가를 반복해서 자신을 이상한 방향으로 최적화할 수 있음.

예:

```text
Codex가 이상한 코드를 냄
local reviewer가 대충 pass 줌
routing policy가 Codex를 더 신뢰하게 됨
```

해결:

```text
실제 테스트/사용자 승인 없는 positive update 금지
```

---

## 2. Goodhart’s Law

점수에 맞춰 행동하다가 진짜 품질이 떨어질 수 있음.

예:

```text
agent가 테스트 통과만 최적화하고 제품 의도를 무시
```

해결:

```text
단일 score 금지
품질, 안정성, 사용자 만족, 비용, 장기 유지보수 분리 평가
```

---

## 3. Prompt drift

자동 수정이 누적되면서 prompt가 이상해짐.

해결:

```text
prompt versioning
rollback
A/B test
human approval
diff review
```

---

## 4. Agent collusion / mutual hallucination

agent끼리 서로의 오류를 강화.

해결:

```text
peer review보다 external evidence/test/user feedback 우선
```

---

## 5. 권한 상승 위험

성능이 좋다고 agent 권한을 자동으로 늘리면 위험.

해결:

```text
capability score와 permission은 분리
권한 상승은 항상 사용자 승인
```

---

# 11. 안전한 Agent Auto Society 구조

따라서 구조는 이렇게 가야 해.

```text
Agent Auto Society
├── Performance Memory
├── Capability Registry
├── Routing Policy
├── Prompt/Skill Versioning
├── Peer Review
├── User Feedback
├── Evaluation Metrics
├── Update Proposal Generator
└── Safety Gate
```

핵심은:

> agent가 스스로를 직접 바꾸는 게 아니라, **수정안을 제안하고 Harness가 검증 후 적용**하는 것.

---

# 12. Update Proposal 형식

자가수정은 항상 proposal로 남겨.

```json
{
  "proposal_id": "prop_001",
  "target": "routing_policy",
  "reason": "Codex failed 3 times on vague UI tasks without prior handoff.",
  "evidence": [
    "run_010",
    "run_014",
    "run_021"
  ],
  "proposed_change": {
    "rule": "Route UI implementation tasks to Claude planner before Codex unless acceptance_criteria exists."
  },
  "risk_level": "low",
  "auto_apply_allowed": true,
  "expected_effect": "Reduce Codex rework rate for UI tasks."
}
```

Prompt 수정안은 이렇게.

```json
{
  "target": "local_memory_extractor_prompt",
  "reason": "Extractor overclassified ideas as decisions in 7 recent runs.",
  "proposed_diff": "- Extract decisions...\n+ Extract decisions only when the user explicitly accepts or commits to them...",
  "risk_level": "medium",
  "requires_approval": true
}
```

---

# 13. Agent 전문화는 어떻게 일어나나

전문화는 선언이 아니라 성과 기반으로 일어나야 해.

```text
처음:
local_llm_1 = general extractor

관찰:
memory extraction success 높음
code review 낮음

결과:
local_llm_1 → MemoryExtractor로 전문화
code review routing에서 제외
```

전문화 기준:

```text
success rate
user acceptance
peer review quality
test pass correlation
cost efficiency
latency
failure mode frequency
```

즉 agent role은 고정이 아니라:

```text
initial role
→ observed role
→ specialized role
→ restricted or promoted role
```

로 진화.

---

# 14. Agent Auto Society의 최소 MVP

처음부터 자율 사회를 만들지 말고, 이 5개만.

```text
1. 모든 run에 agent_id, task_type, result, user_feedback 저장
2. agent별 scorecard 자동 생성
3. routing policy 추천안 생성
4. prompt/skill 수정안은 proposal로만 생성
5. 사용자가 승인해야 적용
```

CLI로는:

```bash
hive society report
hive society propose-updates
hive society approve prop_001
hive society rollback prompt local_memory_extractor v3
```

출력:

```text
Agent Scorecard

codex_executor
- implementation success: 82%
- UI task rework rate: high
- works best with explicit handoff
- recommendation: require Claude planner for vague UI tasks

local_memory_extractor
- schema validity: 94%
- decision overclassification: 18%
- recommendation: update extraction prompt
```

---

# 15. 장기적으로는 “Agent Constitution”이 필요함

자가수정 사회에는 헌법이 있어야 해.

```md
# Agent Society Constitution

1. Agents may propose changes to prompts, skills, routing, and profiles.
2. Agents may not grant themselves new permissions.
3. Memory commits require draft-first validation.
4. User feedback overrides peer feedback.
5. Tests and verifiable artifacts override self-reports.
6. Prompt and skill changes must be versioned.
7. High-risk changes require explicit user approval.
8. Every update must cite run evidence.
9. Rollback must always be possible.
10. No agent may optimize solely for its own score.
```

이건 AGENTS.md보다 상위 개념으로 둘 수 있어.

---

# 16. 최종 구조

```text
User / Work Runs
        ↓
Event Log
        ↓
Performance Memory
        ↓
Agent Scorecards
        ↓
Update Proposal Generator
        ↓
Safety Gate
        ↓
Approved Updates
        ↓
Routing / Prompt / Skill / Profile Changes
        ↓
Better Future Runs
```

그리고 agent들은 점점 이렇게 된다.

```text
Claude Planner
Codex Executor
Local Memory Extractor
Local Capability Scout
Local Context Compressor
Security Reviewer
Verifier
Memory Curator
Handoff Drafter
```

각자 전문성과 권한이 다름.

---

# 17. 최종 답

아이디어는 좋고, 반드시 필요해.
다만 “agent가 스스로를 직접 고치는 사회”로 만들면 위험하고, **성과 로그 기반의 제안형 자기수정 사회**로 만들어야 해.

정리하면:

> **Agent Auto Society는 agent들이 사용자 반응, 검증 결과, peer review, 실행 로그를 바탕으로 자신의 역할과 추론 디자인을 개선해가는 시스템이다. 단, 모든 자기수정은 proposal로 남기고, Harness/Safety Gate/User가 승인한 것만 적용한다.**

가장 중요한 원칙:

```text
Agents may learn.
Agents may propose.
Agents may not silently rewrite their own constitution.
```

한국어로:

> **Agent는 배울 수 있고, 수정안을 제안할 수 있지만, 자기 헌법을 몰래 바꾸면 안 된다.**
