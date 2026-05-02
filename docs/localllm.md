가능해. 다만 핵심은 **local LLM이 Claude/Codex를 완전히 대체하는 것**이 아니라, 비싼 모델이 할 일을 **80% 줄여주는 전처리·정리·분류·검증·반복 작업자**로 만드는 거야.

정확히 말하면:

```text
Claude / GPT급 모델
= 깊은 사고, 아키텍처 판단, 모호한 문제 정리, 최종 synthesis

Codex / Claude Code
= 실제 repo 수정, 테스트, refactor, integration

Local LLM
= 대량 처리, memory extraction, tagging, summarization, routing, draft generation, cheap review
```

즉 local LLM은 “두뇌 전체”가 아니라 **저비용 cognitive worker layer**로 깎아야 해.

---

# 1. Local LLM이 맡기 좋은 일

MemoryOS / CapabilityOS 개발에서 local LLM에게 많이 위임할 수 있는 작업은 이런 것들이야.

```text
1. 대화 export 정리
2. message / pair / segment 분류
3. memory draft 추출
4. concept / project / action / decision tagging
5. 중복 memory 탐지
6. legacy / frontier 분류 초안
7. GitHub README / MCP docs 요약
8. TechnologyCard 초안 생성
9. Capability 추출
10. WorkflowRecipe 초안 생성
11. agent run log 요약
12. PR diff 요약
13. 테스트 실패 로그 1차 분류
14. handoff 문서 초안 생성
15. 긴 context 압축
```

이런 일은 비싼 모델에게 맡기면 토큰이 너무 많이 나가.
local LLM이 가장 잘해야 하는 건 **대량의 지저분한 텍스트를 구조화된 JSON 초안으로 바꾸는 것**이야.

---

# 2. Local LLM이 맡기면 안 되는 일

반대로 이런 건 local LLM에게 단독으로 맡기면 위험해.

```text
1. 핵심 아키텍처 최종 결정
2. 보안 정책 결정
3. DB schema 대규모 변경
4. 복잡한 repo-wide refactor
5. production bug fix
6. 모호한 제품 전략 판단
7. 여러 기술 간 trade-off 최종 판단
8. 외부에 공개할 문서의 최종본
9. memory commit 최종 승인
10. 비싼 작업을 실행할지 말지 최종 판단
```

local LLM은 초안을 만들고, Claude/Codex는 **고난도 판단과 실행**을 맡아야 해.

---

# 3. 역할 분담 구조

나는 이렇게 나누는 게 제일 좋다고 봐.

```text
User
  ↓
Local LLM Layer
  - 정리
  - 분류
  - 압축
  - 초안
  - 후보 생성
  ↓
Claude / GPT Chatbot Harness
  - 깊은 사고
  - architecture
  - synthesis
  - 최종 작업 명세
  ↓
Codex / Claude Code Agent Harness
  - 구현
  - 테스트
  - refactor
  - repo 수정
  ↓
Local LLM Layer
  - 결과 요약
  - memory draft 생성
  - log 정리
  ↓
MemoryOS
```

즉 local LLM은 앞뒤에 둘 다 들어가.

```text
Before expensive model:
local LLM이 context를 줄여준다.

After expensive model:
local LLM이 결과를 정리해서 memory로 만든다.
```

---

# 4. 가장 중요한 패턴: Cheap First, Expensive Last

토큰비를 줄이려면 무조건 이 원칙을 가져가야 해.

> **Cheap first, expensive last.**

즉:

```text
1. local LLM이 먼저 읽고 정리한다.
2. local LLM이 후보를 만든다.
3. local LLM이 필요 없는 부분을 버리거나 압축한다.
4. Claude/GPT는 압축된 핵심만 본다.
5. Codex는 명확한 handoff만 받는다.
```

나쁜 흐름:

```text
대화 100개 전체 → Claude
repo 전체 → Claude
GitHub README 50개 → GPT
```

좋은 흐름:

```text
대화 100개 → local LLM 요약/분류
→ 핵심 10개 memory만 Claude

GitHub README 50개 → local LLM TechnologyCard 초안
→ 상위 5개만 Claude 검토

repo diff → local LLM 요약
→ 문제 있는 파일만 Codex/Claude Code
```

---

# 5. Local LLM을 “잘 깎는다”의 의미

그냥 local model 하나 띄우는 게 아니라, **역할별 작은 worker**로 만들어야 해.

## 5.1 Memory Extractor

```text
입력:
conversation segment

출력:
memory_drafts JSON
- idea
- decision
- action
- question
- constraint
- preference
- artifact
```

이 worker는 MemoryOS의 핵심이야.

---

## 5.2 Capability Extractor

```text
입력:
GitHub README / MCP docs / product docs

출력:
TechnologyCard
Capability list
Risk list
Setup steps
Compatible runtimes
```

CapabilityOS의 핵심 worker.

---

## 5.3 Legacy Classifier

```text
입력:
기술/워크플로우 설명

출력:
emerging / useful / mainstream / legacy / deprecated
supersedes
still_useful_when
```

---

## 5.4 Handoff Drafter

```text
입력:
사용자 요청 + project state + 관련 memory

출력:
Agent Handoff 초안
- objective
- constraints
- files_to_modify 후보
- acceptance criteria
- risks
```

단, 최종 handoff는 Claude가 한 번 검토하는 게 좋다.

---

## 5.5 Log Summarizer

```text
입력:
Codex/Claude Code run log
test output
diff summary

출력:
- 무엇을 바꿨는지
- 테스트 결과
- unresolved issue
- memory update candidate
```

---

## 5.6 Context Compressor

```text
입력:
긴 memory 검색 결과 30개

출력:
Claude/Codex에 넣을 2~4KB context pack
```

이게 토큰 절약에 가장 직접적으로 도움 된다.

---

# 6. 모델 선택 감각

local LLM은 무조건 큰 모델 하나보다, **작업별로 적절한 모델**이 좋아.

```text
작은 모델:
- 분류
- 태깅
- JSON extraction
- 중복 감지

중간 모델:
- 요약
- 문서 초안
- capability card 생성

큰 local model:
- 가벼운 reasoning
- local synthesis
- private context 분석
```

예시 구조:

```text
Small local model
→ tagger / classifier / router

Mid local model
→ summarizer / extractor / draft generator

Best available paid model
→ final architect / strategic judge

Codex/Claude Code
→ implementation
```

---

# 7. Local LLM을 언제 Claude로 escalate할지

local LLM이 모든 걸 처리하려고 하면 품질이 떨어져.
그래서 escalation rule을 만들어야 해.

Claude/GPT로 올리는 조건:

```text
1. confidence < 0.75
2. memory conflict 발생
3. architecture decision 필요
4. security/privacy 관련
5. schema migration 필요
6. user-facing 중요한 문서
7. 여러 project가 얽힘
8. local LLM 결과끼리 충돌
9. 예상 비용/위험이 큰 작업
```

Codex/Claude Code로 올리는 조건:

```text
1. 실제 repo 수정 필요
2. 테스트 실행 필요
3. 타입 오류 수정 필요
4. multi-file refactor 필요
5. MCP server 구현 필요
6. parser/worker 실제 코드 작성 필요
```

local에서 끝내는 조건:

```text
1. 단순 요약
2. 분류
3. draft 생성
4. 로그 정리
5. 중복 탐지
6. context 압축
7. schema에 맞춘 JSON 변환
```

---

# 8. 비용 절감 루프

MemoryOS / CapabilityOS 개발에서 비용을 줄이는 실제 루프는 이거야.

```text
Raw data
  ↓
Local LLM extraction
  ↓
Structured draft
  ↓
Cheap validation
  ↓
Only uncertain/high-impact items
  ↓
Claude/GPT review
  ↓
Codex implementation only when spec is clear
  ↓
Local LLM result summarization
  ↓
MemoryOS update
```

이렇게 하면 Claude/Codex에 들어가는 토큰은 많이 줄어.

---

# 9. 구체적인 작업 분배표

## MemoryOS 개발

| 작업                   | Local LLM | Claude/GPT | Codex/Claude Code |
| -------------------- | --------: | ---------: | ----------------: |
| ChatGPT export 샘플 분석 |     1차 가능 |     필요시 검토 |         parser 구현 |
| message/pair 구조 추출   |        가능 |     거의 불필요 |                구현 |
| memory draft 추출      |     매우 적합 |   샘플 품질 검토 |               불필요 |
| hyperedge 후보 생성      |        적합 |      설계 검토 |                구현 |
| DB schema 설계         |     초안 가능 |      최종 판단 |      migration 구현 |
| MCP tool schema      |     초안 가능 |         검토 |                구현 |
| README 초안            |        가능 |  최종 polish |               불필요 |
| 테스트 실패 요약            |        가능 |    복잡하면 검토 |                수정 |

---

## CapabilityOS 개발

| 작업                  | Local LLM |     Claude/GPT | Codex/Claude Code |
| ------------------- | --------: | -------------: | ----------------: |
| GitHub README 요약    |     매우 적합 |          일부 검토 |               불필요 |
| MCP capability 추출   |     매우 적합 |          샘플 검토 |               불필요 |
| TechnologyCard 생성   |        적합 |  최종 scoring 검토 |               불필요 |
| WorkflowRecipe 초안   |        적합 | 중요 workflow 검토 |               불필요 |
| Discriminator 점수 초안 |        가능 |          최종 평가 |               불필요 |
| Surfer pipeline 구현  |     초안 가능 |          구조 검토 |                구현 |
| ontology schema 설계  |     초안 가능 |          최종 설계 |                구현 |
| 추천 알고리즘             |     초안 가능 |   trade-off 판단 |                구현 |

---

# 10. Local LLM을 위한 내부 Worker 이름

너희 시스템 안에서는 local LLM을 하나의 agent로 부르지 말고 역할별 worker로 나누자.

```text
LocalMemoryExtractor
LocalCapabilityExtractor
LocalContextCompressor
LocalHandoffDrafter
LocalLogSummarizer
LocalLegacyClassifier
LocalDuplicateDetector
LocalRiskPreScanner
```

이렇게 해야 harness가 잘 배정할 수 있어.

---

# 11. 실전 Harness Routing Rule

```yaml
routing:
  memory_extraction:
    primary: local_memory_extractor
    reviewer: claude_if_low_confidence
    auto_commit: false

  capability_card_generation:
    primary: local_capability_extractor
    reviewer: claude_for_top_ranked_items

  architecture_decision:
    primary: claude
    local_support: context_compressor

  implementation:
    primary: codex
    preprocessor: local_handoff_drafter
    reviewer: claude_optional

  log_summarization:
    primary: local_log_summarizer

  conflict_resolution:
    primary: claude
    local_support: duplicate_detector
```

---

# 12. Local LLM에게 넘길 context도 작게

local LLM도 context를 많이 주면 느리고 품질이 떨어져.

그래서 local worker 입력은 항상 작게 잘라야 해.

```text
대화 전체 ❌
segment 단위 ⭕

repo 전체 ❌
관련 파일 diff ⭕

문서 50개 ❌
문서별 README 요약 chunk ⭕

memory 100개 ❌
상위 10개 candidate ⭕
```

Local LLM은 “작은 작업을 많이” 시키는 게 좋다.

---

# 13. Local LLM 결과는 항상 schema-first

자유문으로 받으면 후처리가 힘들어.
항상 JSON schema로 받아야 해.

예:

```json
{
  "memory_drafts": [
    {
      "type": "decision",
      "content": "...",
      "origin": "user",
      "confidence": 0.82,
      "raw_refs": ["msg_123"]
    }
  ],
  "uncertain_items": [
    {
      "content": "...",
      "reason": "ambiguous whether user accepted this decision"
    }
  ],
  "needs_human_or_claude_review": true
}
```

핵심은 `uncertain_items`와 `needs_review`야.
local LLM이 확신 없는 걸 솔직히 올리게 해야 해.

---

# 14. 가장 좋은 전략: Local LLM을 “filter”로 써라

비싼 모델을 호출하기 전에 local LLM이 필터링한다.

```text
100개 후보
→ local LLM이 20개로 압축
→ rule/scoring으로 5개 선택
→ Claude가 최종 판단
```

이 구조가 비용 절감에 제일 크다.

특히 CapabilityOS에서 중요해.

```text
GitHub repo 100개
→ local LLM TechnologyCard 초안
→ Discriminator 점수
→ 상위 10개만 Claude review
→ 상위 3개만 agent workflow 생성
```

---

# 15. Fine-tuning / LoRA를 한다면

나중에 local LLM을 더 잘 깎으려면, 처음부터 로그를 모아야 해.

저장할 데이터:

```text
input segment
local LLM draft
Claude corrected version
user accepted/rejected
final committed memory
```

이게 쌓이면 나중에 local LLM을 MemoryOS 전용 extractor로 fine-tune할 수 있어.

학습 목표:

```text
conversation segment → memory draft JSON
README/docs → TechnologyCard JSON
user request + context → handoff draft JSON
run log → execution summary JSON
```

이건 아주 좋은 fine-tuning 데이터야.

---

# 16. 품질 관리

local LLM을 많이 쓰면 반드시 품질 관리가 필요해.

## 자동 검증

```text
JSON schema valid?
raw_refs 존재?
confidence 있음?
origin 있음?
content가 너무 길지 않음?
type이 허용값인가?
중복인가?
```

## LLM 검증

중요한 것만 Claude가 검토.

```text
importance > 0.85
confidence < 0.75
type = decision
project_state 변경
security/risk 관련
```

## 사용자 검증

```text
preference
long-term goal
project north star
final decision
```

이런 건 사용자가 직접 승인해야 함.

---

# 17. 실제 비용 절감 예상

대략 구조가 잘 잡히면:

```text
memory extraction 비용:
Claude/GPT 100% 사용 대비
local LLM으로 70~90% 절감 가능

capability crawling 정리:
80~95% 절감 가능

architecture decision:
local로 완전 대체 어렵지만
context 압축으로 30~60% 절감 가능

coding agent 비용:
명확한 handoff 생성으로 재시도 횟수 감소
30~50% 절감 가능
```

가장 큰 절감은 **비싼 모델에게 긴 raw context를 안 먹이는 것**에서 나온다.

---

# 18. 최종 역할 분담

```text
Local LLM
= 읽고, 줄이고, 분류하고, 초안을 만든다.

Claude/GPT
= 모호한 것을 해석하고, 중요한 결정을 내리고, 최종 문서를 정제한다.

Codex/Claude Code
= 명확한 지시를 받아 실제 repo를 바꾼다.

MemoryOS
= 모든 결과를 기억하고 다음 작업의 context를 제공한다.

CapabilityOS
= 필요한 tool/module/workflow를 찾고 추천한다.

Harness
= 누가 뭘 할지 정하고, 비용과 품질을 통제한다.
```

한 문장으로:

> **Local LLM은 비싼 모델의 대체재가 아니라, 비싼 모델이 볼 세계를 압축해주는 저비용 인지 전처리층이다.**

더 짧게:

> **Local LLM은 worker, Claude는 judge, Codex는 executor.**

나는 이 역할 분담이 가장 좋다고 봐.
