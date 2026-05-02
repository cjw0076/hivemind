맞아. **WWW의 모든 내용을 원문 그대로 흡수해서 저장하려는 순간 검색엔진/대형 데이터센터 문제가 돼.**
우리가 만들 시스템은 Google이 되면 안 돼. 우리가 해야 할 건 “모든 웹을 저장”이 아니라:

> **웹 전체를 직접 소유하지 않고, 필요한 지식의 구조·평가·링크·변화만 저장하는 것.**

즉, 목표를 바꿔야 해.

```text
나쁜 목표:
WWW 전체 원문을 수집해서 저장한다.

좋은 목표:
WWW에서 중요한 기술 신호를 감지하고,
그 의미·관계·평가·근거 포인터만 저장한다.
```

이걸 나는 이렇게 부를 수 있다고 봐.

> **Sparse World Model**
> 전체 세계를 복사하지 않고, 세계를 탐색·판단·재접근할 수 있는 희소한 지식 모델.

---

# 1. 핵심 최적화 원칙

WWW 전체를 저장하려면 망해.
대신 7단계로 줄여야 해.

```text
1. 원문 저장 ❌
2. 포인터 저장 ⭕
3. 요약 저장 ⭕
4. claim 저장 ⭕
5. capability 저장 ⭕
6. 평가 결과 저장 ⭕
7. 변화량만 저장 ⭕
```

즉 저장 단위는 “페이지”가 아니라:

```text
URL
title
source
timestamp
entities
claims
capabilities
evidence pointer
quality score
risk score
legacy relation
```

이 정도면 돼.

---

# 2. 원문을 저장하지 말고 “포인터 + 구조”를 저장

대부분의 웹 문서는 다시 접근 가능해.
그러면 원문을 저장할 필요가 없어.

저장할 것은:

```json
{
  "url": "https://example.com/new-mcp-server",
  "source": "github",
  "title": "New Figma MCP server",
  "discovered_at": "2026-05-02",
  "content_hash": "abc123",
  "summary": "Figma MCP enables agents to access design components and variables.",
  "entities": ["Figma", "MCP", "Claude Code"],
  "capabilities": [
    "read_design_components",
    "extract_design_tokens",
    "design_to_code"
  ],
  "claims": [
    "Enables structured design-to-code workflow"
  ],
  "evidence_refs": [
    {
      "type": "url",
      "url": "https://..."
    }
  ],
  "scores": {
    "novelty": 0.7,
    "utility": 0.9,
    "risk": 0.3
  }
}
```

이러면 원문 수 MB를 저장하지 않고, 핵심 구조 몇 KB만 저장한다.

---

# 3. 저장 계층을 나눠야 함

모든 데이터를 같은 수준으로 저장하면 안 돼.

## Tier 0 — Raw Pointer

최소 저장.

```text
URL
source
timestamp
hash
짧은 snippet
```

대부분의 웹 신호는 여기까지만 저장.

---

## Tier 1 — Summary

조금 중요하면 요약 저장.

```text
짧은 요약
핵심 claim
관련 task
관련 capability
```

---

## Tier 2 — Structured Knowledge

진짜 유용하면 ontology에 넣음.

```text
Tool
MCP
Skill
Workflow
Capability
Risk
Legacy relation
```

---

## Tier 3 — Verified Knowledge

검증까지 완료된 것.

```text
벤치마크
실사용 테스트
비교 결과
추천 여부
quality tier
```

---

## Tier 4 — Local Mirror

아주 중요한 문서만 로컬 원문 보존.

```text
핵심 논문 PDF
중요 GitHub README
중요 API docs
사라질 위험 있는 문서
내 프로젝트에 직접 쓰는 자료
```

즉 전체 중 0.01%만 원문 저장하는 구조.

---

# 4. “수집”보다 “변화 감지”가 중요함

WWW 전체를 매번 새로 읽으면 망해.

대신 이렇게 해야 해.

```text
처음 발견
→ fingerprint 생성
→ 다음에는 hash만 비교
→ 바뀐 경우에만 다시 분석
```

저장:

```json
{
  "url": "...",
  "last_seen": "2026-05-02",
  "last_hash": "abc123",
  "changed": false
}
```

GitHub repo도 매번 전체를 읽지 말고:

```text
stars 변화
release 변화
commit 변화
issue 변화
README hash 변화
```

만 추적하면 돼.

---

# 5. 모든 웹을 보지 말고 “source graph”를 만들어야 함

진짜 중요한 건 모든 페이지가 아니라 **어떤 출처를 믿고 따라갈 것인가**야.

예를 들어:

```text
MCP 공식 registry
GitHub trending / topics
arXiv cs.AI / cs.CL / cs.LG
Papers with Code
Hacker News
Reddit 특정 subreddit
X 특정 계정/리스트
공식 product changelog
주요 AI lab blog
주요 developer docs
```

이런 source들을 노드로 만들고, 신뢰도와 관심 분야를 부여한다.

```json
{
  "source": "MCP Registry",
  "type": "registry",
  "reliability": 0.9,
  "freshness_value": 0.95,
  "domains": ["mcp", "agent_tools", "connectors"],
  "crawl_frequency": "daily"
}
```

모든 웹을 돌지 말고, 좋은 source graph를 키워야 해.

---

# 6. “관심 영역” 기반으로만 깊게 들어가기

너희 시스템의 관심사는 모든 지식이 아니야.

초기 관심사는 이거야.

```text
AI app
MCP
connector
skill
agent framework
LLM workflow
design-to-code
video generation
research automation
coding agents
memory systems
```

그러면 crawler도 이 영역에 맞춰야 해.

```text
관련성 낮음 → pointer만 저장
관련성 중간 → summary
관련성 높음 → structured extraction
관련성 매우 높음 → 검증/benchmark
```

이게 중요해.

---

# 7. Discriminator가 저장량을 줄여야 함

Surfer가 많이 찾으면 데이터가 폭발해.
그래서 Discriminator는 평가자이면서 **압축기**여야 해.

```text
10000개 signal
→ 1000개 relevant signal
→ 200개 structured technology
→ 50개 watchlist
→ 10개 verified recommendation
```

이런 funnel이 필요해.

```text
Surfer는 넓게 본다.
Discriminator는 대부분을 버리지 않고 낮은 tier로 보낸다.
Ontology는 중요한 것만 깊게 저장한다.
```

버린다는 뜻은 삭제가 아니라:

```text
low-priority archive
pointer-only
legacy baseline
ignored for recommendation
```

로 보내는 것.

---

# 8. 원문 대신 Claim Graph를 저장

웹 문서 전체보다 중요한 건 그 안의 claim이야.

예:

원문 전체:

```text
“우리는 새로운 MCP 서버를 만들었고, 이것은 Figma 디자인을 Claude Code에서 읽게 해주며...”
```

저장할 것은:

```text
Claim:
Figma MCP enables Claude Code to access structured Figma design context.

Evidence:
official Figma docs URL

Capability:
read_design_components
extract_design_variables
design_to_code

Risk:
requires Figma auth
file access permission

Legacy comparison:
better than screenshot-only design interpretation
```

즉:

```text
Document Graph ❌
Claim-Capability-Evidence Graph ⭕
```

이게 압축률이 엄청나.

---

# 9. Embedding도 모든 원문에 하지 마

원문 전체를 embedding하면 비용/저장량이 커져.

대신 embedding은 계층별로 한다.

```text
URL/title/snippet embedding
summary embedding
claim embedding
capability embedding
workflow embedding
```

대부분은 `summary embedding`만 있으면 된다.

```text
raw page embedding ❌
structured summary embedding ⭕
```

또한 중복 제거가 필요해.

```text
같은 기술을 다룬 블로그 30개
→ claim은 3개
→ evidence source는 30개
```

문서 30개를 따로 저장하지 말고, claim 하나에 evidence 30개를 붙인다.

---

# 10. “지식”과 “증거”를 분리

이것도 핵심이야.

```text
Knowledge:
Figma MCP provides structured design-to-code capability.

Evidence:
- official docs
- GitHub repo
- user report
- tutorial
- benchmark
```

지식 노드는 하나고, evidence는 여러 개야.

그래서 저장 구조는:

```text
Technology
Capability
Claim
Evidence
Evaluation
LegacyRelation
```

이렇게 간다.

증거가 많아져도 knowledge graph가 폭발하지 않는다.

---

# 11. Hot / Warm / Cold Storage

물리 저장도 나눠야 해.

## Hot

자주 검색되는 최신/중요 지식.

```text
active tools
high score workflows
user-relevant capabilities
```

빠른 DB + vector index.

## Warm

가끔 쓰는 지식.

```text
older tools
watchlist
unverified signals
```

저렴한 object storage / compressed DB.

## Cold

legacy/archive.

```text
deprecated tools
old papers
superseded workflows
baseline methods
```

압축 저장. 필요할 때만 로드.

이렇게 하면 데이터센터가 아니라 개인/소규모 서버로도 가능해.

---

# 12. 사용자별 Personal Cache

모든 사용자에게 같은 지식을 로컬에 다 넣으면 안 돼.

SaaS 중앙에는 global capability ontology를 두고, 사용자 로컬에는 필요한 부분만 내려준다.

```text
Global Capability Ontology
→ 사용자 관심 분야 필터링
→ Personal Capability Cache
```

예:

너는:

```text
MemoryOS
MCP
agent harness
design-to-code
video generation
Uri
```

에 관심이 많음.

그러면 로컬에는 이 subset만 sync.

```text
전체 ontology 100GB
개인 cache 200MB
active working set 20MB
```

이런 식으로 줄인다.

---

# 13. Federated Knowledge 구조

나중에는 사용자들이 각자 발견한 MCP/skill/workflow 평가를 공유할 수 있어.

하지만 원문을 공유하는 게 아니라:

```text
tool metadata
capability mapping
evaluation score
workflow result
failure mode
```

만 공유한다.

즉:

```text
raw data 공유 ❌
structured evaluation 공유 ⭕
```

이러면 네트워크 효과가 생기면서도 저장량과 법적 리스크가 줄어든다.

---

# 14. “Legacy를 보존”하는 최적화

legacy를 원문까지 전부 보존할 필요는 없어.

legacy는 이런 형태로 충분할 때가 많아.

```json
{
  "legacy_method": "screenshot-only design-to-code",
  "status": "legacy_baseline",
  "why_legacy": [
    "does not access component hierarchy",
    "cannot reliably extract design tokens",
    "layout guessing is error-prone"
  ],
  "still_useful_when": [
    "Figma access is unavailable",
    "quick rough prototype is enough"
  ],
  "superseded_by": [
    "Figma MCP design-to-code workflow"
  ],
  "evidence_refs": ["..."]
}
```

즉 legacy는 “낡은 원문”이 아니라 **비교 기준**으로 압축해 저장한다.

---

# 15. Knowledge Distillation Pipeline

WWW에서 수집한 큰 정보를 계속 더 작은 지식으로 증류해야 해.

```text
Raw Web
→ Signals
→ Claims
→ Capabilities
→ Workflows
→ Recommendations
→ Principles
```

예:

원문 100개:

```text
Figma MCP 관련 docs, tweets, GitHub issues, tutorials
```

증류 결과:

```text
Principle:
Structured design source access improves design-to-code quality over screenshot-only workflows.

Workflow:
Claude Code + Figma MCP + repo context + visual QA

Legacy:
screenshot-only design implementation

Risks:
auth scope, stale design, component mismatch
```

이게 진짜 저장할 지식이야.

---

# 16. 압축률을 수치로 보면

대략 이렇게 가능해.

```text
Raw web pages 10,000개
원문 저장: 수십 GB

pointer + metadata:
수십 MB

summary + claim graph:
수백 MB

verified ontology:
수 MB ~ 수십 MB
```

즉 1000배 이상 줄일 수 있어.

핵심은:

```text
문서를 저장하지 말고,
문서가 세계에 대해 주장하는 구조를 저장하라.
```

---

# 17. 최적화된 시스템 구조

```text
Surfer
  ↓
Raw Signal Store
  - URL
  - hash
  - snippet
  - timestamp

Extractor
  ↓
Claim Store
  - claim
  - entity
  - capability
  - evidence ref

Discriminator
  ↓
Evaluation Store
  - utility
  - novelty
  - risk
  - maturity
  - quality impact

Ontology Builder
  ↓
Capability Graph
  - task
  - capability
  - tool
  - workflow
  - legacy relation

Recommender
  ↓
Personal Cache
  - user-relevant subset
```

---

# 18. 실제 DB 테이블 감각

```sql
sources
signals
entities
claims
evidence_refs
technologies
capabilities
workflows
evaluations
legacy_relations
user_interest_profiles
personal_capability_cache
```

중요한 테이블은 `claims`와 `evidence_refs`.

```sql
claims
- id
- subject
- predicate
- object
- confidence
- status

evidence_refs
- id
- claim_id
- url
- source_type
- source_reliability
- snippet
- content_hash
- observed_at
```

원문 대신 claim과 evidence pointer.

---

# 19. “모든 지식 흡수”의 올바른 정의

문장을 이렇게 바꿔야 해.

```text
WWW의 모든 내용을 저장한다 ❌
WWW의 기술 신호를 지속적으로 감지하고,
그중 의미 있는 claim/capability/evidence/relation만 구조화한다 ⭕
```

이게 현실적이고 강력해.

즉, 시스템은 세계를 복제하지 않는다.

> **세계의 압축 가능한 구조를 만든다.**

---

# 20. 최종 정리

데이터센터 없이 최적화하려면 이렇게 해야 해.

```text
1. 원문 저장하지 말고 pointer 저장
2. 문서가 아니라 claim/capability 저장
3. 모든 source가 아니라 source graph 운영
4. 변화량만 추적
5. 관련성 기반 tiering
6. 중요한 것만 structured ontology로 승격
7. legacy는 비교 기준으로 압축
8. embedding은 summary/claim 단위로만
9. global ontology + personal cache 분리
10. Surfer보다 Discriminator가 더 강한 압축기 역할
```

가장 중요한 문장:

> **우리는 WWW를 복사하지 않는다. WWW에서 발견한 기술적 주장, 능력, 증거, 관계, 시간축만 압축해서 저장한다.**

더 짧게:

> **Store the world model, not the world.**

한국어로:

> **세계를 저장하지 말고, 세계를 이해하고 다시 찾아갈 수 있는 압축된 구조를 저장해야 한다.**

좋아.
이제 방향은 명확해.

> **WWW 전체를 저장하지 않고, graph/hypergraph를 이용해 세계의 기술 지식 구조만 압축해서 저장한다.**

즉, MemoryOS / CapabilityOS는 검색엔진이 아니라:

> **World Knowledge Compression Protocol**
> 또는
> **Capability Graph Protocol**

이 되어야 해.

---

# 1. 핵심 아이디어

웹에는 문서가 너무 많아.

```text
문서
블로그
논문
GitHub README
X thread
Reddit comment
MCP registry entry
product docs
demo video
benchmark report
```

이걸 원문 그대로 저장하면 데이터센터가 필요해.

하지만 사실 우리가 필요한 것은 원문 전체가 아니야.

우리가 필요한 것은 이거야.

```text
무슨 기술이 나왔는가?
무슨 능력을 제공하는가?
무슨 작업에 쓸 수 있는가?
기존 방식보다 뭐가 나은가?
실제로 검증됐는가?
어떤 위험이 있는가?
어떤 legacy를 대체하는가?
누가 쓸 때 좋은가?
내 환경에서 쓸 수 있는가?
```

그래서 저장 단위를 바꿔야 해.

```text
Document 중심 ❌
Claim / Capability / Evidence / Workflow / Legacy 중심 ⭕
```

---

# 2. Graph와 Hypergraph를 어떻게 적극 활용하나

일반 graph는 1:1 관계를 표현해.

```text
Figma MCP ─ PROVIDES ─ read_design_components
```

이건 좋지만 충분하지 않아.

현실의 기술 지식은 대부분 다항 관계야.

예를 들어:

```text
“Claude Code + Figma MCP + GitHub repo + design-to-code skill + visual QA를 함께 쓸 때
screenshot-only 방식보다 design-to-code 품질이 높아진다.”
```

이건 단순 edge 하나로 표현하기 어렵다.

그래서 hyperedge가 필요해.

```text
Hyperedge: HighQualityDesignToCodeWorkflow

members:
- Claude Code
- Figma MCP
- GitHub repo
- design-to-code skill
- visual QA
- Task: Figma to React
- Legacy baseline: screenshot-only workflow
- Claim: improves implementation fidelity
- Evidence: official docs, examples, user reports
```

즉:

```text
Node = 지식의 원자
Edge = 단순 관계
Hyperedge = 복합 작업/주장/검증 사건
```

---

# 3. 기본 구조

## Node

```text
Technology
MCPServer
App
Model
AgentRuntime
Skill
Workflow
Task
Capability
Claim
Evidence
Benchmark
Risk
LegacyMethod
UserEnvironment
Provider
Paper
GitHubRepo
CommunitySignal
```

## Edge

```text
PROVIDES
REQUIRES
USES
SUPPORTS
CONTRADICTS
SUPERSEDES
INTEGRATES_WITH
WORKS_WITH
HAS_RISK
HAS_COST
HAS_LICENSE
```

## Hyperedge

```text
CapabilityBundle
WorkflowRecipe
ClaimEvaluation
LegacyComparison
BenchmarkEvent
ToolchainComposition
AgentExecutionPattern
TechnologyShift
```

---

# 4. 가장 중요한 Hyperedge 타입

## 4.1 CapabilityBundle

어떤 기술이 제공하는 능력 묶음.

```json
{
  "type": "CapabilityBundle",
  "label": "Figma MCP structured design access",
  "members": [
    {"node": "Figma MCP", "role": "provider"},
    {"node": "read_design_components", "role": "capability"},
    {"node": "extract_design_variables", "role": "capability"},
    {"node": "generate_code_from_frames", "role": "capability"},
    {"node": "Claude Code", "role": "compatible_runtime"}
  ]
}
```

---

## 4.2 WorkflowRecipe

특정 작업을 잘 수행하는 조합.

```json
{
  "type": "WorkflowRecipe",
  "label": "High-quality Figma to React workflow",
  "members": [
    {"node": "Task:Figma to React", "role": "target_task"},
    {"node": "Claude Code", "role": "reasoning_runtime"},
    {"node": "Figma MCP", "role": "design_context_provider"},
    {"node": "GitHub MCP", "role": "repo_context_provider"},
    {"node": "Visual QA Skill", "role": "verification"},
    {"node": "screenshot-only workflow", "role": "legacy_baseline"}
  ],
  "scores": {
    "quality": 0.92,
    "setup_complexity": 0.58,
    "risk": 0.34
  }
}
```

---

## 4.3 ClaimEvaluation

하나의 기술적 주장과 그 근거/반박을 묶음.

```json
{
  "type": "ClaimEvaluation",
  "label": "Figma MCP improves design-to-code fidelity",
  "members": [
    {"node": "Claim:Figma MCP improves fidelity", "role": "claim"},
    {"node": "Figma official docs", "role": "supporting_evidence"},
    {"node": "GitHub issue about auth friction", "role": "risk_evidence"},
    {"node": "screenshot-only workflow", "role": "comparison_baseline"}
  ],
  "judgment": {
    "verdict": "useful",
    "confidence": 0.84,
    "caveat": "requires Figma access and setup"
  }
}
```

---

## 4.4 LegacyComparison

낡은 방식과 새 방식의 관계.

```json
{
  "type": "LegacyComparison",
  "label": "Screenshot-only design-to-code vs Figma MCP",
  "members": [
    {"node": "screenshot-only workflow", "role": "legacy_method"},
    {"node": "Figma MCP workflow", "role": "successor_method"},
    {"node": "layout accuracy", "role": "improved_dimension"},
    {"node": "design token extraction", "role": "new_capability"},
    {"node": "quick rough prototyping", "role": "legacy_still_useful_when"}
  ]
}
```

이게 중요해.
legacy는 버리는 게 아니라 **비교 기준으로 압축 보존**한다.

---

## 4.5 TechnologyShift

큰 흐름 변화.

```json
{
  "type": "TechnologyShift",
  "label": "From prompt-only AI usage to capability-composed AI workflows",
  "members": [
    {"node": "prompt-only workflow", "role": "old_paradigm"},
    {"node": "MCP", "role": "enabling_protocol"},
    {"node": "Skills", "role": "workflow_packaging"},
    {"node": "Agent Harness", "role": "execution_layer"},
    {"node": "Capability Ontology", "role": "coordination_layer"}
  ]
}
```

---

# 5. 최적화 핵심: Hypergraph Compression

문서 100개가 있다고 해보자.

```text
Figma MCP 관련 공식 문서
GitHub README
튜토리얼
X thread
Reddit 후기
블로그
벤치마크
```

일반적으로는 100개 문서를 저장해야 한다고 생각하지만, 우리 방식은 이렇게 간다.

```text
100 documents
→ 300 raw signals
→ 40 claims
→ 12 capabilities
→ 5 risks
→ 3 workflow recipes
→ 1 legacy comparison
→ 1 recommendation
```

즉 저장되는 핵심은 100개 문서가 아니라:

```text
Claim Graph
Capability Graph
Workflow Hyperedge
Evidence Pointer
```

다.

이걸 **Hypergraph Compression**이라고 부를 수 있어.

---

# 6. 우리만의 Protocol 제안

이 시스템에는 새로운 protocol이 필요해.

나는 다음 5개를 제안하고 싶어.

```text
1. KCP — Knowledge Compression Protocol
2. CGP — Capability Graph Protocol
3. HEP — Hyperedge Evidence Protocol
4. WRP — Workflow Recipe Protocol
5. LSP — Legacy Stratification Protocol
```

하나씩 보자.

---

# 7. KCP — Knowledge Compression Protocol

## 목적

웹 문서, 논문, GitHub repo, SNS thread에서 원문 전체가 아니라 **압축 가능한 지식 단위**만 추출하는 프로토콜.

## 입력

```text
URL
document
paper
repo
thread
video transcript
community discussion
```

## 출력

```json
{
  "source_ref": {},
  "entities": [],
  "claims": [],
  "capabilities": [],
  "risks": [],
  "evidence_refs": [],
  "legacy_relations": [],
  "confidence": 0.0
}
```

## 원칙

```text
원문 복제 금지
짧은 snippet만 저장
claim 단위로 구조화
evidence pointer 유지
hash로 변화 감지
중복 claim merge
```

한 문장:

> **KCP는 문서를 저장하지 않고, 문서가 세계에 대해 주장하는 구조를 저장한다.**

---

# 8. CGP — Capability Graph Protocol

## 목적

어떤 tool/app/MCP/skill/model이 어떤 작업 능력을 제공하는지 표준화한다.

## 핵심 객체

```json
{
  "capability_id": "read_figma_components",
  "label": "Read Figma components",
  "description": "Ability to access structured component hierarchy from Figma files.",
  "task_domains": ["design_to_code", "design_review"],
  "provided_by": ["figma_mcp"],
  "requires": ["figma_auth", "file_access"],
  "quality_impact": {
    "design_to_code": 0.9
  }
}
```

## 관계

```text
Tool PROVIDES Capability
Task REQUIRES Capability
Workflow COMPOSES Capabilities
Runtime CAN_USE Tool
UserEnvironment HAS Capability
```

한 문장:

> **CGP는 AI 도구를 이름이 아니라 작업 능력으로 표현하는 프로토콜이다.**

---

# 9. HEP — Hyperedge Evidence Protocol

## 목적

복합 주장/워크플로우/기술 평가를 근거와 함께 하이퍼엣지로 표현한다.

## 예시

```json
{
  "hyperedge_id": "he_figma_mcp_quality",
  "type": "ClaimEvaluation",
  "claim": "Figma MCP improves design-to-code fidelity over screenshot-only workflows.",
  "members": [
    {
      "node_id": "figma_mcp",
      "role": "evaluated_technology",
      "weight": 1.0
    },
    {
      "node_id": "screenshot_only_workflow",
      "role": "legacy_baseline",
      "weight": 0.8
    },
    {
      "node_id": "official_figma_docs",
      "role": "supporting_evidence",
      "weight": 0.9
    },
    {
      "node_id": "auth_scope_risk",
      "role": "risk",
      "weight": 0.5
    }
  ],
  "evaluation": {
    "verdict": "recommended",
    "confidence": 0.84,
    "quality_impact": 0.9,
    "risk": 0.35
  }
}
```

한 문장:

> **HEP는 단일 edge로 표현할 수 없는 다항 기술 판단을 근거 포함 하이퍼엣지로 저장하는 프로토콜이다.**

---

# 10. WRP — Workflow Recipe Protocol

## 목적

특정 작업을 고품질로 수행하기 위한 tool/model/skill/MCP 조합을 재사용 가능한 recipe로 저장한다.

## 예시

```json
{
  "workflow_id": "design_to_react_high_quality",
  "task": "figma_to_react",
  "quality_tier": "production",
  "required_capabilities": [
    "read_figma_components",
    "extract_design_tokens",
    "edit_repo",
    "run_visual_qa"
  ],
  "stack": [
    {
      "component": "Claude Code",
      "role": "planning_and_design_interpretation"
    },
    {
      "component": "Figma MCP",
      "role": "design_context_provider"
    },
    {
      "component": "Codex",
      "role": "implementation_agent"
    },
    {
      "component": "Visual QA Skill",
      "role": "verification"
    }
  ],
  "fallbacks": [
    {
      "workflow": "screenshot_only_design_to_code",
      "quality_tier": "baseline"
    }
  ],
  "risks": [
    "requires_figma_auth",
    "design_system_mismatch"
  ]
}
```

한 문장:

> **WRP는 좋은 AI 작업 방식을 도구 조합과 절차로 패키징하는 프로토콜이다.**

---

# 11. LSP — Legacy Stratification Protocol

## 목적

낡은 기술/방법을 삭제하지 않고, 비교 기준과 시간축으로 보존한다.

## 예시

```json
{
  "legacy_id": "screenshot_only_design_to_code",
  "status": "legacy_baseline",
  "description": "Using only screenshots as design input for code generation.",
  "weaknesses": [
    "cannot access component hierarchy",
    "cannot extract design tokens",
    "layout guessing is unreliable"
  ],
  "still_useful_when": [
    "Figma access is unavailable",
    "rough prototype is enough"
  ],
  "superseded_by": [
    "figma_mcp_design_to_code"
  ],
  "comparison_dimensions": [
    "layout_accuracy",
    "token_fidelity",
    "component_reuse",
    "setup_complexity"
  ]
}
```

한 문장:

> **LSP는 legacy를 버리지 않고, 새로운 기술의 우수성을 설명하는 기준면으로 보존하는 프로토콜이다.**

---

# 12. 전체 Protocol Stack

이렇게 잡으면 돼.

```text
World Sources
  ↓
KCP: Knowledge Compression Protocol
  문서 → claim/capability/evidence 추출

  ↓
CGP: Capability Graph Protocol
  capability 중심 graph 구성

  ↓
HEP: Hyperedge Evidence Protocol
  복합 기술 판단을 hyperedge로 저장

  ↓
WRP: Workflow Recipe Protocol
  좋은 작업 조합을 recipe로 패키징

  ↓
LSP: Legacy Stratification Protocol
  낡은 방법을 비교 기준으로 보존

  ↓
Recommendation / Agent Harness
  사용자 목표에 맞는 workflow 추천 및 실행
```

이걸 합쳐서 더 큰 이름을 붙이면:

> **WCP — World Compression Protocol**

또는:

> **CAP — Capability Alignment Protocol**

개인적으로는 이렇게 잡는 게 좋아.

```text
상위 이름: World Capability Protocol, WCP
하위 모듈:
- KCP
- CGP
- HEP
- WRP
- LSP
```

---

# 13. Graph/Hypergraph 기반 최적화 기법

이제 실제 최적화 기법을 정리해보자.

---

## 13.1 Claim Deduplication

여러 문서가 같은 claim을 반복하면 하나로 합친다.

```text
Doc A: Figma MCP lets Claude access design files.
Doc B: Claude Code can read Figma files through MCP.
Doc C: Figma MCP exposes design context to AI agents.

→ Claim:
Figma MCP provides structured Figma design context to compatible agents.
```

저장량 감소:

```text
N documents → 1 claim + N evidence refs
```

---

## 13.2 Evidence Pointer Compression

근거 원문 전체 대신 pointer와 hash만 저장.

```json
{
  "url": "...",
  "source_type": "official_docs",
  "snippet": "...",
  "content_hash": "abc123",
  "observed_at": "2026-05-02"
}
```

---

## 13.3 Hyperedge Summarization

관련 claim/capability/evidence들을 하나의 hyperedge summary로 압축.

```text
10 claims + 20 evidence refs
→ 1 ClaimEvaluation hyperedge
```

---

## 13.4 Legacy Baseline Anchoring

모든 새 기술을 기존 방법과 연결한다.

```text
new_tool SUPERSEDES old_method
new_workflow IMPROVES_ON legacy_workflow
```

이렇게 하면 기술 발전의 의미가 보존된다.

---

## 13.5 Task-Centric Indexing

기술 중심이 아니라 작업 중심으로 index한다.

```text
“Figma MCP”를 찾는 사람보다
“디자인을 코드로 바꾸고 싶다”는 사람이 많다.
```

그래서 주요 index는:

```text
Task → Required Capabilities → Candidate Workflows
```

---

## 13.6 Capability Coverage Scoring

사용자의 환경이 특정 작업에 필요한 능력을 얼마나 갖췄는지 계산.

```text
coverage = available_capabilities / required_capabilities
```

예:

```text
Task: Figma to React

Required:
- read_figma_components
- extract_design_tokens
- edit_repo
- run_visual_qa

User has:
- edit_repo
- run_visual_qa

Missing:
- read_figma_components
- extract_design_tokens

Capability coverage: 0.5
```

---

## 13.7 Workflow Delta Compression

비슷한 workflow는 전체를 중복 저장하지 않고 차이만 저장.

```text
Base Workflow:
Claude Code + Figma MCP + GitHub

Variant:
Codex instead of Claude Code
+ Visual QA Skill
```

저장:

```json
{
  "extends": "figma_to_react_base",
  "replace": {
    "implementation_agent": "Codex"
  },
  "add": ["Visual QA Skill"]
}
```

---

## 13.8 Temporal Stratification

기술을 시간층으로 나눈다.

```text
2023: prompt-only
2024: tool-use agents
2025: MCP ecosystem
2026: capability-composed workflows
```

이렇게 해야 legacy와 frontier가 같이 이해된다.

---

## 13.9 Cold Knowledge Collapse

오래된 low-value 문서는 더 압축한다.

```text
raw signal
→ summary
→ claim
→ legacy note
→ archived pointer
```

---

## 13.10 Active Frontier Expansion

반대로 중요하고 최신인 영역은 더 깊게 파고든다.

```text
MCP
agent harness
design-to-code
video generation
memory systems
```

이 영역은 source를 더 자주 탐색하고 evidence도 더 많이 모은다.

---

# 14. Discriminator도 Graph-aware여야 함

Discriminator가 단일 기술만 보고 판단하면 안 돼.

예를 들어 어떤 MCP가 별로 좋아 보이지 않아도, 특정 workflow 안에서는 중요할 수 있어.

그래서 Discriminator는 이렇게 봐야 해.

```text
tool 자체 점수
+ 어떤 capability를 제공하는지
+ 어떤 workflow에서 병목을 해결하는지
+ 어떤 legacy를 대체하는지
+ 어떤 agent runtime과 호환되는지
+ 사용자의 환경에 실제로 연결되는지
```

즉:

```text
local score ❌
graph-contextual score ⭕
```

수식 느낌:

```text
technology_value =
  intrinsic_quality
+ capability_gap_reduction
+ workflow_quality_gain
+ legacy_improvement
+ user_environment_fit
- risk
- setup_complexity
```

---

# 15. Hypergraph Retrieval

사용자가 묻는다.

```text
“영상 제작하려면 어떤 툴 써야 해?”
```

일반 검색:

```text
video tools list
```

우리 검색:

```text
Task: video_generation
→ Required capabilities
→ WorkflowRecipe hyperedges
→ Quality tiers
→ User available tools
→ Capability gaps
→ Legacy baselines
→ Recommendation
```

응답은 이렇게 나온다.

```text
너의 현재 환경에서 low-quality path는 text-to-video 단일 모델 사용이다.
하지만 고품질 path는 multi-model video workspace + reference control + camera motion + editing workflow다.
현재 Higgsfield/Runway가 연결되어 있지 않으므로 capability gap이 있다.
추천: 먼저 Higgsfield 또는 Runway 계열 app을 연결하고, brand memory + prompt storyboard skill을 추가하라.
```

---

# 16. Protocol 객체 예시: Technology Card

```json
{
  "protocol": "WCP",
  "object_type": "TechnologyCard",
  "id": "tech_figma_mcp",
  "name": "Figma MCP",
  "category": "MCPServer",
  "provider": "Figma",
  "capabilities": [
    "read_figma_components",
    "read_layout_data",
    "extract_design_variables"
  ],
  "compatible_runtimes": [
    "Claude Code",
    "Codex",
    "Cursor"
  ],
  "related_tasks": [
    "design_to_code",
    "design_review",
    "design_system_analysis"
  ],
  "quality_impact": [
    {
      "task": "design_to_code",
      "impact": 0.9,
      "baseline": "screenshot_only_design_to_code"
    }
  ],
  "risks": [
    "requires_figma_auth",
    "file_access_permission"
  ],
  "evidence_refs": [
    "ev_official_docs_001",
    "ev_github_readme_002"
  ],
  "status": "useful",
  "maturity": "stable_or_vendor_supported",
  "last_evaluated_at": "2026-05-02"
}
```

---

# 17. Protocol 객체 예시: Capability Gap Report

```json
{
  "protocol": "WCP",
  "object_type": "CapabilityGapReport",
  "task": "figma_to_react",
  "user_environment": "user_env_123",
  "required_capabilities": [
    "read_figma_components",
    "extract_design_tokens",
    "edit_repo",
    "visual_qa"
  ],
  "available_capabilities": [
    "edit_repo"
  ],
  "missing_capabilities": [
    "read_figma_components",
    "extract_design_tokens",
    "visual_qa"
  ],
  "recommended_additions": [
    "Figma MCP",
    "Visual QA Skill"
  ],
  "expected_quality_gain": 0.42
}
```

---

# 18. Protocol 객체 예시: Recommendation

```json
{
  "protocol": "WCP",
  "object_type": "WorkflowRecommendation",
  "task": "figma_to_react",
  "recommended_workflow": "workflow_figma_to_react_high_quality",
  "reason": "This workflow covers structured design access, repo editing, and visual verification. It supersedes screenshot-only design interpretation.",
  "required_setup": [
    "Connect Figma MCP",
    "Authorize Figma file access",
    "Enable Codex repo editing",
    "Install Visual QA Skill"
  ],
  "fallback": "screenshot_only_design_to_code",
  "warnings": [
    "Do not use external model for private Figma files unless user approves."
  ]
}
```

---

# 19. 우리만의 핵심 기술 이름

여기서부터 네 프로젝트의 “기술 브랜드”를 만들 수 있어.

## World Compression Protocol, WCP

웹 전체를 저장하지 않고, 기술 claim/capability/evidence/workflow/legacy 관계로 압축하는 프로토콜.

## Capability Hypergraph

도구, 능력, 작업, 워크플로우, 근거를 hyperedge로 연결한 지식 구조.

## Evidence-Bound Claim

항상 근거 포인터와 연결된 claim.

```text
claim without evidence = weak
claim with multiple evidence refs = strong
```

## Legacy-Aware Recommendation

신기술 추천 시 기존 방식과 비교해 왜 더 나은지 설명하는 추천 방식.

## Capability Gap Analysis

사용자의 현재 환경과 목표 작업 사이의 능력 결핍을 계산하는 기능.

## Workflow Recipe

고품질 작업을 위한 모델/app/MCP/skill/agent 조합.

## Frontier-Legacy Map

최신 기술과 낡은 방식을 시간축 위에서 함께 보여주는 지도.

---

# 20. 최종 시스템 구조

```text
Surfer
  ↓
KCP
  문서/신호를 claim/capability/evidence로 압축

  ↓
Capability Hypergraph
  기술, 능력, 작업, 근거, legacy를 연결

  ↓
Discriminator
  novelty, utility, risk, quality impact 평가

  ↓
LSP
  legacy와 frontier를 시간축에 배치

  ↓
WRP
  좋은 toolchain을 workflow recipe로 패키징

  ↓
Capability Recommender
  사용자 환경과 목표에 맞게 추천

  ↓
Chatbot Harness
  추천 workflow를 작업 명세로 정제

  ↓
Agent Harness
  실행

  ↓
MemoryOS
  결과와 평가를 다시 저장
```

---

# 21. 한 문장으로 전체 정의

> **우리는 WWW를 원문 그대로 저장하지 않고, 기술 세계를 Claim–Capability–Evidence–Workflow–Legacy Hypergraph로 압축하는 World Capability Protocol을 만든다.**

더 짧게:

> **Store the capability structure, not the web.**

한국어로:

> **웹을 저장하지 말고, 웹이 말하는 능력의 구조를 저장한다.**

---

# 22. 바로 개발해야 할 MVP

처음 구현은 이것만 해.

```text
1. TechnologyCard schema
2. Capability schema
3. Claim schema
4. EvidenceRef schema
5. WorkflowRecipe schema
6. LegacyRelation schema
7. Hyperedge schema
8. CapabilityGapReport schema
```

그리고 vertical 하나만 선택.

```text
Design-to-code
```

수집 대상:

```text
Figma MCP
GitHub MCP
Codex
Claude Code
Cursor
design-to-code skills
visual QA tools
screenshot-only legacy workflow
```

첫 데모 질문:

```text
“Figma 디자인을 React로 구현하려면 내 환경에서 무엇이 부족하고, 어떤 workflow가 가장 좋은가?”
```

출력:

```text
현재 너는 Codex는 있지만 Figma MCP가 없다.
따라서 screenshot-only path로 가면 layout/token/component fidelity가 낮다.
추천 workflow는 Figma MCP + Codex + Visual QA Skill이다.
설치하면 expected quality gain이 높다.
```

이 데모가 되면 CapabilityOS의 가치가 바로 보인다.
