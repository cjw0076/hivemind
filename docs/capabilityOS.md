맞아. 이건 **MemoryOS의 SaaS 확장판**이 될 수 있어.
네가 말하는 문제는 단순히 “AI tool 추천”이 아니라, 더 정확히는:

> **같은 AI 비용을 내고도, 어떤 app / MCP / connector / skill / workflow 조합을 아느냐에 따라 결과물 품질이 크게 갈리는 문제**

이 간극을 줄이는 서비스야.

나는 이걸 이렇게 정의하고 싶어.

> **Capability Ontology**
> 작업 목표에 따라 어떤 AI 모델, app, MCP, connector, skill, workflow를 조합해야 하는지 자동으로 발견·평가·추천·설치·운영해주는 지식 그래프.

---

# 1. 문제 정의

지금 AI 생태계는 이렇게 변하고 있어.

```text
모델만 잘 쓰는 시대
→ app / MCP / tool / skill / connector / workflow 조합을 잘 쓰는 시대
```

예를 들어 디자인 작업을 한다고 하자.

```text
A 사용자:
local LLM에 스크린샷 던지고 “이거 구현해줘”

B 사용자:
Claude Code + Figma MCP + Figma file context + component variables + Code Connect + design skill 사용
```

둘이 같은 “AI 사용”처럼 보여도 결과물은 완전히 달라진다.

Figma MCP는 Claude Code가 Figma 파일과 도구에 구조적으로 접근하게 해주며, component, variable, layout data, FigJam content, Make resources 등을 읽고, 선택한 frame에서 code를 생성하거나 Figma canvas에 직접 native content를 쓰는 기능까지 제공한다. ([Figma Help Center][1])

즉, 차이는 모델 지능만이 아니라:

```text
모델이 어떤 외부 능력에 연결되어 있는가
```

에서 발생한다.

---

# 2. 이걸 해결하는 제품: Capability OS

MemoryOS가 “기억의 OS”라면, 이건 **능력의 OS**야.

> **CapabilityOS**
> 사용자의 목표를 보고, 필요한 AI app / MCP / connector / skill / model / agent 조합을 추천하고 자동 구성하는 SaaS.

MemoryOS와 붙이면:

```text
MemoryOS
= 사용자의 기억과 맥락을 관리

CapabilityOS
= 사용 가능한 외부 능력과 도구 생태계를 관리

Agent Harness
= MemoryOS와 CapabilityOS를 이용해 실제 작업 실행
```

즉:

```text
사용자 목표
→ MemoryOS가 과거 맥락 제공
→ CapabilityOS가 최적 도구 조합 추천
→ Chatbot Harness가 사고 정제
→ Agent Harness가 실행
```

---

# 3. 왜 지금 가능한가

MCP 생태계가 이미 “앱스토어화”되고 있어.

공식 MCP Registry는 공개 MCP server들을 발견할 수 있는 registry이고, GitHub 쪽 설명에서도 MCP client에게 MCP server 목록을 제공하는 “app store for MCP servers”라고 설명한다. ([Model Context Protocol][2])

Codex도 MCP를 통해 third-party documentation, browser, Figma 같은 developer tool에 접근할 수 있고, CLI와 IDE extension에서 MCP server를 지원한다. ([OpenAI 개발자][3])

Claude Code 역시 MCP를 통해 외부 tools, databases, APIs에 접근할 수 있고, issue tracker나 monitoring dashboard 같은 도구의 데이터를 복붙하지 않고 직접 읽고 행동할 수 있게 한다고 설명한다. ([Claude][4])

그리고 Skill도 별도 생태계가 되고 있다. Codex Agent Skills는 instructions, resources, optional scripts를 묶어 특정 workflow를 안정적으로 수행하게 하는 단위다. ([OpenAI 개발자][5])

즉, 이제는 이런 것들을 체계적으로 정리할 시점이 온 거야.

```text
MCP Registry
+ Skills
+ Agent Harness
+ App-specific connectors
+ Workflow recommendations
= Capability Ontology
```

---

# 4. 핵심 개념: Capability Ontology

Capability Ontology는 단순 tool list가 아니야.

일반 디렉토리:

```text
Figma MCP
GitHub MCP
Slack MCP
Notion MCP
Browser MCP
```

Capability Ontology:

```text
작업: 디자인 → 구현
필요 능력:
- design file read
- component extraction
- variable extraction
- code generation
- screenshot comparison
- design system compliance

가능 조합:
- Claude Code + Figma MCP + Code Connect Skill
- Codex + Figma MCP + repo context
- Cursor + Figma MCP + React component skill

품질 차이:
- local LLM only: 낮음
- screenshot-only: 중간
- Figma MCP with component metadata: 높음
```

즉, 도구를 “이름”이 아니라 **능력 단위**로 분해해야 해.

---

# 5. Capability Ontology의 노드

```text
(:Task)
(:Capability)
(:Tool)
(:MCPServer)
(:Connector)
(:Skill)
(:Model)
(:AgentRuntime)
(:App)
(:Workflow)
(:Provider)
(:Cost)
(:QualityProfile)
(:Risk)
(:Permission)
(:UserContext)
```

예:

```text
Task: "Figma design to React implementation"

requires Capability:
- read_figma_layout
- extract_components
- map_design_tokens
- generate_react_code
- compare_visual_output

provided_by:
- Figma MCP
- Claude Code
- Codex
- Code Connect
- screenshot comparison tool
```

---

# 6. Capability Ontology의 관계

```text
(:Task)-[:REQUIRES]->(:Capability)

(:MCPServer)-[:PROVIDES]->(:Capability)

(:Skill)-[:IMPROVES]->(:Workflow)

(:Model)-[:GOOD_AT]->(:Capability)

(:AgentRuntime)-[:CAN_USE]->(:MCPServer)

(:Tool)-[:INTEGRATES_WITH]->(:App)

(:Workflow)-[:USES]->(:MCPServer)

(:Workflow)-[:USES]->(:Skill)

(:Workflow)-[:ACHIEVES]->(:Task)

(:Workflow)-[:HAS_QUALITY_PROFILE]->(:QualityProfile)

(:Workflow)-[:HAS_RISK]->(:Risk)

(:UserContext)-[:HAS_AVAILABLE]->(:Tool)
```

중요한 건 이거야.

```text
Claude가 Figma MCP를 쓸 수 있음
local LLM은 현재 못 씀
Codex는 MCP 설정하면 가능
특정 app은 API 없음
특정 tool은 인증 필요
특정 workflow는 비용이 큼
특정 workflow는 품질이 높음
```

이 차이를 시스템이 알아야 해.

---

# 7. 예시: 디자인 작업 Capability Graph

```text
Task:
"랜딩페이지 디자인을 실제 React 코드로 구현"

Required Capabilities:
- design_source_access
- layout_understanding
- component_mapping
- design_token_extraction
- code_generation
- visual QA

Available Options:

A. Low-quality path
local LLM + screenshot
→ visual guessing
→ 낮은 정확도

B. Medium path
GPT/Claude chat + screenshot + manual CSS
→ 어느 정도 구현

C. High-quality path
Claude Code + Figma MCP + repo context + component library
→ 구조적 접근
→ 높은 정확도

D. Production path
Claude Code + Figma MCP + Code Connect + design system docs + visual regression
→ 가장 안정적
```

이걸 사용자가 몰라도 시스템이 추천해야 해.

---

# 8. 예시: 영상 제작 Capability Graph

네가 말한 Higgsfield도 좋은 예야.
Higgsfield는 여러 주요 AI video model을 한 workspace에서 접근하고, Sora, Kling, Veo, Seedance 등을 비교하면서 쓸 수 있다고 설명한다. ([Higgsfield][6]) Reuters도 Higgsfield가 third-party model들을 통합하고 자체 reasoning engine으로 콘텐츠 coherence를 높이는 application-level video creation platform에 가깝다고 보도했다. ([Reuters][7])

즉 영상 제작에서도 차이는 커.

```text
Low-quality path:
단일 저품질 video model에 prompt만 넣음

High-quality path:
Higgsfield 같은 multi-model creative workspace
+ reference image
+ camera motion control
+ style preset
+ post-editing workflow
+ brand asset memory
```

Capability Ontology는 이런 걸 알아야 해.

```text
Task: product promo video

requires:
- image_to_video
- camera_motion_control
- multi_model_comparison
- style_consistency
- commercial_ready_export

provided_by:
- Higgsfield
- Runway
- Kling
- Veo
- Sora
- editing tools

quality impact:
- camera control: high
- model comparison: high
- brand memory: medium-high
```

---

# 9. “MCP를 자동으로 만들어준다”도 가능함

가능해. 다만 단계가 있어.

## Level 1 — MCP Discovery

공식 registry, GitHub, docs에서 MCP를 찾는다.

```text
“Figma MCP 있나?”
“Notion MCP 있나?”
“Vercel MCP 있나?”
“이 app의 MCP server는 active한가?”
```

공식 MCP Registry와 GitHub registry를 index하면 된다. ([Model Context Protocol][2])

## Level 2 — MCP Installation Assistant

사용자 환경을 보고 설치 명령을 제안한다.

```text
Claude Code에 Figma MCP 설치
Codex config.toml에 MCP server 추가
환경변수/API key 설정
권한 scope 확인
```

Figma는 Claude Code용 MCP 설정 가이드를 제공하고, Figma MCP Catalog도 MCP client 연결을 안내한다. ([Figma Help Center][1])

## Level 3 — MCP Copy / Fork / Adapt

GitHub에 공개된 MCP server를 가져와 사용자의 환경에 맞게 수정.

```text
git clone
security scan
manifest read
tool schema parse
local config 생성
test call
```

## Level 4 — MCP Generator

API docs를 읽고 자동으로 MCP server scaffold 생성.

```text
OpenAPI spec
→ MCP tool schema
→ auth handler
→ request wrapper
→ response normalizer
→ tests
```

## Level 5 — Capability Wrapper

MCP 자체가 없어도 app을 도구로 감싸는 wrapper 생성.

```text
browser automation
local CLI wrapper
REST API wrapper
file watcher
webhook connector
```

이게 진짜 강하다.

---

# 10. SaaS 제품으로 만들면

이건 다음과 같은 SaaS가 될 수 있어.

> **AI Capability Navigator**
> 사용자가 하려는 작업을 입력하면, 어떤 AI app / model / MCP / skill / connector / workflow 조합이 가장 좋은지 추천하고, 가능한 경우 자동 설치/설정/실행까지 해주는 서비스.

제품 흐름:

```text
사용자:
“Figma 디자인을 Next.js 코드로 구현하고 싶어.”

서비스:
1. task 분석
2. 필요한 capability 추출
3. 사용자의 현재 환경 스캔
4. 부족한 MCP/tool/skill 탐지
5. 최적 조합 추천
6. 설치/설정 가이드 또는 자동 설정
7. Chatbot Harness에서 작업 명세 생성
8. Agent Harness로 실행
```

---

# 11. 이 SaaS의 핵심 화면

## 1. Capability Map

```text
내가 가진 AI 능력 지도

Design
  Figma MCP: connected
  Canva MCP: not connected
  Screenshot QA: available

Coding
  Codex: connected
  GitHub MCP: connected
  Vercel MCP: not connected

Video
  Higgsfield: not connected
  Runway: not connected
  Local video model: available
```

## 2. Task Planner

```text
무엇을 하고 싶은가?
[ Figma 디자인을 React 코드로 구현 ]

추천 workflow:
High quality:
Claude Code + Figma MCP + GitHub repo + visual QA skill

Medium:
GPT/Claude screenshot analysis + manual implementation

Low:
local LLM only
```

## 3. Capability Gap

```text
현재 환경:
- Codex connected
- Claude connected
- Figma MCP missing
- visual QA skill missing

작업물 품질을 높이려면:
1. Figma MCP 설치
2. 디자인 시스템 docs 연결
3. visual regression tool 추가
```

## 4. Auto Setup

```text
[Install Figma MCP for Claude Code]
[Add Figma MCP to Codex config]
[Create design-to-code Skill]
[Generate AGENTS.md update]
```

## 5. Workflow Marketplace

```text
Design-to-React Workflow
Research-to-Report Workflow
Video-Ad-Creation Workflow
Landing-Page-Builder Workflow
Paper-to-Implementation Workflow
```

---

# 12. Business 포지셔닝

이건 “AI tool directory”가 아니야.

디렉토리는 이미 많아질 거야.
너의 제품은 더 깊어야 해.

약한 포지셔닝:

```text
AI tools 추천 서비스
```

강한 포지셔닝:

```text
AI 작업 품질 격차를 줄이는 capability orchestration platform
```

더 날카롭게:

> **Same AI budget, better outcomes.**

한국어로:

> **같은 AI 비용으로 더 좋은 결과물을 내게 하는 작업 능력 레이어.**

---

# 13. 왜 사람들이 돈을 내나

사용자는 지금 이런 문제를 겪어.

```text
AI 앱이 너무 많다.
뭘 써야 할지 모르겠다.
MCP가 뭔지 모른다.
Claude에서는 되는 게 Codex에서는 안 된다.
local LLM은 왜 결과가 구린지 모른다.
좋은 workflow를 아는 사람만 압도적으로 좋은 결과를 낸다.
```

너의 SaaS는 이걸 해결한다.

```text
작업 목표를 입력하면
최적의 AI tool stack을 추천하고
필요하면 설치까지 도와주고
작업 명세를 만들어 agent에게 전달한다.
```

결국 팔리는 가치는:

```text
시간 절약
도구 선택 실패 감소
작업물 품질 상승
AI 사용 격차 감소
전문가 workflow의 상품화
```

---

# 14. MemoryOS와의 결합

CapabilityOS가 따로 놀면 약해.
MemoryOS와 붙을 때 강해져.

```text
MemoryOS:
사용자의 과거 작업, 선호, 프로젝트, agent 결과를 기억

CapabilityOS:
현재 작업에 필요한 도구와 능력을 추천

둘이 결합:
“이 사용자는 주로 Next.js, Figma, campus app, 3D visual 작업을 한다.
현재 Figma MCP가 없으니 디자인 구현 품질이 낮아질 가능성이 높다.
추천: Figma MCP + visual QA skill + Codex implementation workflow.”
```

즉, 추천이 일반적이지 않고 **개인화**된다.

---

# 15. Provider = Me 관점

여기서 “우리도 Provider”가 된다.

기존 provider:

```text
OpenAI = model provider
Anthropic = model/agent provider
Google = model/search provider
Figma = design context provider
Higgsfield = video generation workspace provider
```

우리:

```text
MemoryOS = context provider
CapabilityOS = capability provider
Harness = orchestration provider
```

사용자에게 제공하는 건 모델이 아니라:

```text
무엇을 써야 하는지
어떻게 연결해야 하는지
어떤 순서로 실행해야 하는지
어떤 조합이 고품질인지
내 환경에서 무엇이 부족한지
```

이건 충분히 SaaS가 된다.

---

# 16. Capability Ontology schema

초기 schema는 이 정도면 돼.

```json
{
  "tool_id": "figma_mcp",
  "type": "mcp_server",
  "name": "Figma MCP",
  "provider": "Figma",
  "capabilities": [
    "read_design_components",
    "read_layout_data",
    "read_design_variables",
    "generate_code_from_frames",
    "write_to_figma_canvas"
  ],
  "compatible_runtimes": [
    "claude_code",
    "codex",
    "cursor"
  ],
  "requires_auth": true,
  "risk_level": "medium",
  "quality_impact": {
    "design_to_code": "high",
    "visual_analysis": "high"
  },
  "setup": {
    "docs_url": "...",
    "install_methods": ["plugin", "mcp_config"]
  }
}
```

Workflow schema:

```json
{
  "workflow_id": "design_to_react_high_quality",
  "task": "design_to_code",
  "required_capabilities": [
    "read_design_components",
    "read_layout_data",
    "repo_edit",
    "visual_qa"
  ],
  "recommended_stack": [
    "claude_code",
    "figma_mcp",
    "github_mcp",
    "design_to_code_skill"
  ],
  "fallback_stack": [
    "chatbot_screenshot_analysis",
    "manual_css_implementation"
  ],
  "quality_tier": "high",
  "cost_tier": "medium",
  "setup_complexity": "medium"
}
```

---

# 17. 자동 추천 알고리즘

```text
Input:
사용자 작업 목표
사용자 현재 환경
사용자 과거 작업
사용자 예산/보안 선호

Process:
1. task classification
2. required capabilities 추출
3. available capabilities scan
4. capability gap 계산
5. workflow candidates 검색
6. quality/cost/risk scoring
7. 추천
```

Scoring:

```text
workflow_score =
  task_fit * 0.30
+ capability_coverage * 0.25
+ expected_quality * 0.20
+ user_environment_fit * 0.10
+ setup_ease * 0.05
+ cost_fit * 0.05
+ risk_fit * 0.05
```

---

# 18. MVP는 어떻게 자르나

처음부터 모든 app을 커버하면 망해.
초기 vertical을 3개로 제한하자.

## Vertical 1: Design-to-Code

```text
Figma MCP
GitHub MCP
Codex
Claude Code
Cursor
React/Next.js Skill
visual QA
```

가장 강력한 데모가 나옴.

## Vertical 2: Research-to-Document

```text
Perplexity
OpenAI docs MCP
browser/search
Notion/Google Docs
citation skill
report generation
```

## Vertical 3: Video/Creative Workflow

```text
Higgsfield
Runway
Kling/Veo/Sora access
prompt pack
brand memory
creative QA
```

처음 SaaS MVP는 **Design-to-Code Capability Advisor**로 시작하는 게 가장 좋다.

왜냐하면 Figma MCP 같은 확실한 품질 차이가 이미 존재하기 때문이야.

---

# 19. 제품 이름 후보

```text
CapabilityOS
ToolGraph
AgentStack
SkillGraph
MCP Navigator
ContextStack
AI Workbench Navigator
StackPilot
Agent Capability Map
```

내 추천:

```text
CapabilityOS
```

MemoryOS와 짝이 좋다.

```text
MemoryOS = 기억
CapabilityOS = 능력
Harness = 실행
```

---

# 20. 최종 구조

```text
User Goal
  ↓
MemoryOS
  - user context
  - prior work
  - project state

CapabilityOS
  - app/tool/MCP/skill ontology
  - quality tiers
  - setup instructions
  - gap analysis

Chatbot Harness
  - deliberate
  - compare models
  - generate task spec

Agent Harness
  - execute with best stack
  - log results
  - update memory
```

---

# 21. 가장 중요한 문장

> **AI 사용 격차는 모델 접근성의 문제가 아니라, capability composition을 아느냐의 문제다.**

한국어로:

> **같은 AI를 써도 결과가 다른 이유는, 어떤 모델을 쓰느냐보다 어떤 능력들을 연결해 쓰느냐를 아느냐에 있다.**

그리고 네 제품은:

> **그 능력 조합을 자동으로 찾아주고, 설치하고, 실행 문서까지 만들어주는 시스템.**

---

# 22. 결론

응, 이건 SaaS로 만들 수 있어.
오히려 MemoryOS보다 더 빠르게 시장성이 보일 수도 있어.

단, 단순 “AI tool 추천 사이트”로 가면 안 돼.
차별점은 이거야.

```text
1. MCP / Skill / App / Agent runtime까지 포함한 ontology
2. 사용자 환경을 스캔해서 capability gap 분석
3. 작업 목표별 best workflow 추천
4. 자동 설치/설정/Skill 생성
5. MemoryOS와 연결해 개인화
6. Chatbot Harness → Agent Harness로 실행까지 연결
```

한 문장으로 정의하면:

> **CapabilityOS는 사용자의 목표와 현재 AI 환경을 분석해, 최적의 MCP·Skill·App·Agent 조합을 추천하고 구성해주는 AI 작업 능력 운영체제다.**

이걸 MemoryOS와 결합하면 너희는 단순 AI 앱이 아니라:

```text
Memory Provider
+
Capability Provider
+
Agent Orchestration Provider
```

가 된다.

[1]: https://help.figma.com/hc/en-us/articles/39888612464151-Claude-Code-and-Figma-Set-up-the-MCP-server?utm_source=chatgpt.com "Claude Code and Figma: Set up the MCP server"
[2]: https://registry.modelcontextprotocol.io/?utm_source=chatgpt.com "Official MCP Registry"
[3]: https://developers.openai.com/codex/mcp?utm_source=chatgpt.com "Model Context Protocol – Codex"
[4]: https://code.claude.com/docs/en/mcp?utm_source=chatgpt.com "Connect Claude Code to tools via MCP"
[5]: https://developers.openai.com/codex/skills?utm_source=chatgpt.com "Agent Skills – Codex | OpenAI Developers"
[6]: https://higgsfield.ai/ai-video?utm_source=chatgpt.com "AI Video Generator - Sora, Kling, Veo, Seedance & More"
[7]: https://www.reuters.com/business/media-telecom/ai-video-startup-higgsfield-hits-13-billion-valuation-with-latest-funding-2026-01-15/?utm_source=chatgpt.com "AI video startup Higgsfield hits $1.3 billion valuation with latest funding"

맞아. 이건 **CapabilityOS의 핵심 진화 방향**이야.
단순히 “도구 추천”에서 끝나는 게 아니라, WWW 전체를 계속 관찰하면서:

```text
새로운 기술 발견
→ 의미 분류
→ 실제 쓸만한지 검증
→ 작업물 품질 평가
→ 기존 기술과 비교
→ legacy 지식으로 보존
→ 사용자 작업에 추천
```

하는 시스템이 필요해.

나는 이걸 이렇게 부르고 싶어.

> **Surfer–Discriminator System**
> WWW를 탐색하는 Surfer와, 기술의 실효성·품질·위험·legacy 관계를 판별하는 Discriminator가 함께 돌아가는 AI capability intelligence system.

또는 더 제품적으로:

> **Capability Radar**
> 최신 AI app, MCP, tool, skill, 논문, GitHub repo, workflow를 발견하고 검증하는 기술 감시/평가 엔진.

---

# 1. 네가 말한 시스템의 본질

이건 “뉴스 요약 봇”이 아니야.
진짜 목적은 이거야.

> **사용자가 몰라서 낮은 품질의 도구/워크플로우를 쓰는 문제를 없애는 것.**

지금은 이런 일이 벌어져.

```text
어떤 사람은 Figma MCP + Claude Code + design-to-code skill을 씀
어떤 사람은 local LLM에 스크린샷만 넣고 구현시킴

어떤 사람은 Higgsfield/Runway/Veo/Kling/Sora workflow를 조합함
어떤 사람은 저품질 video generator 하나에 prompt만 넣음

어떤 사람은 최신 MCP registry, GitHub repo, arXiv paper를 추적함
어떤 사람은 6개월 전 블로그 글 보고 낡은 방식으로 작업함
```

이 차이가 곧 작업물 품질 차이야.

그래서 필요한 시스템은:

```text
최신 기술을 자동으로 찾고
그 기술이 진짜 쓸만한지 검증하고
어떤 작업에 어떤 조합이 좋은지 정리하고
낡은 기술도 버리지 않고 비교 기준으로 보존하는 시스템
```

---

# 2. 전체 구조

```text
WWW / SNS / Community / Papers / GitHub / MCP Registry
        ↓
Surfer Layer
        ↓
Raw Signal Store
        ↓
Normalizer
        ↓
Capability Ontology Builder
        ↓
Discriminator Layer
        ↓
Evidence / Benchmark / Risk / Quality Evaluation
        ↓
Capability Graph
        ↓
Legacy Stratifier
        ↓
Recommendation Engine
        ↓
Chatbot Harness / Agent Harness / MemoryOS
```

더 짧게:

```text
Surfer = 찾는다
Discriminator = 판별한다
Ontology = 구조화한다
Legacy Stratifier = 시간축에 보존한다
Recommender = 사용자 작업에 연결한다
```

---

# 3. Surfer: WWW를 도는 기술 감지자

## Surfer의 역할

Surfer는 최신 기술 신호를 모은다.

```text
MCP server
AI app
agent framework
GitHub repo
논문
arXiv preprint
X/Threads viral post
Reddit/Hacker News 토론
product launch
benchmark result
tutorial
workflow
prompt pack
skill
connector
API update
```

Surfer는 단순 크롤러가 아니라 **technology signal collector**야.

---

## Surfer의 소스

### 1. MCP Registry

MCP Registry는 공개 MCP 서버를 발견하는 registry 역할을 한다. 공식 GitHub 설명도 MCP Registry를 “MCP clients에게 MCP server 목록을 제공하는 app store 같은 것”으로 설명한다. ([GitHub][1])

```text
source:
- official MCP registry
- GitHub MCP registry repo
- vendor MCP catalogs
- third-party MCP lists
```

### 2. GitHub

GitHub에서는 repo, stars, forks, issues, releases, topics, commits, README 변화, examples를 본다.

```text
signals:
- sudden star growth
- recent commits
- release frequency
- issue quality
- examples
- license
- install complexity
- security posture
```

### 3. arXiv / Papers

arXiv는 API를 통해 e-print metadata에 programmatic access를 제공하고, OAI-PMH로 전체 metadata를 nightly update할 수 있다. ([arXiv][2])

```text
signals:
- new paper
- code available
- dataset available
- benchmark claim
- method novelty
- reproducibility
- citations later
```

### 4. Reddit / Community

Reddit 같은 커뮤니티는 유용하지만 scraping/API 접근은 조심해야 한다. Reddit은 최근 AI bot/search crawler 접근을 강하게 제한하고 data licensing 이슈도 커졌기 때문에, 공식 API/허용된 검색/사용자 제공 데이터 중심으로 접근해야 한다. ([The Verge][3])

```text
signals:
- 실제 사용자 불만
- 설치 문제
- 품질 후기
- hype vs reality
- hidden failure mode
```

### 5. X / Threads / Social

여기는 빠르지만 noise가 많다.

```text
signals:
- launch announcement
- demo video
- founder claim
- viral workflow
- early adoption
- drama / criticism
```

### 6. Product Sites / Docs

```text
signals:
- 공식 기능
- pricing
- API availability
- MCP availability
- rate limit
- platform support
- export/import support
```

---

# 4. Surfer가 만드는 Raw Signal

Surfer는 곧바로 “좋다/나쁘다”를 판단하지 않는다.
우선 raw signal로 저장한다.

```json
{
  "signal_id": "sig_001",
  "source": "github",
  "url": "...",
  "title": "New Figma MCP server",
  "content_snippet": "...",
  "detected_entities": ["Figma", "MCP", "Claude Code"],
  "detected_capabilities": ["read_design_layout", "generate_code"],
  "timestamp": "2026-05-02T12:00:00+09:00",
  "freshness": 0.97,
  "source_reliability": 0.72,
  "raw_evidence": {}
}
```

이걸 바로 추천하면 안 돼.
Discriminator가 필요해.

---

# 5. Discriminator: 진짜 쓸만한지 판별하는 층

Discriminator는 “이게 혁신인가, hype인가, 위험한가, 누구에게 쓸만한가”를 평가한다.

## Discriminator의 질문

```text
이 기술은 실제 문제를 해결하는가?
기존 방법 대비 품질이 얼마나 좋아지는가?
데모만 좋은가, production에도 쓸만한가?
설치/운영 비용은 어떤가?
보안 리스크는 있는가?
오픈소스인가, vendor lock-in인가?
사용자 작업물 품질에 실제 영향을 주는가?
누가 쓰면 좋은가?
어떤 상황에서는 쓰면 안 되는가?
legacy 대비 무엇이 개선되었는가?
```

---

# 6. Discriminator 평가 축

## 1. Novelty

정말 새로운가?

```text
0 = 기존 wrapper 수준
1 = 새로운 capability primitive
```

## 2. Utility

실제 작업에 도움이 되는가?

```text
0 = demo toy
1 = production workflow에 유용
```

## 3. Quality Impact

결과물 품질을 올리는가?

```text
예:
Figma MCP는 screenshot-only design-to-code보다 구조적 design metadata를 제공하므로 quality impact가 큼.
```

## 4. Reproducibility

남들도 재현 가능한가?

```text
설치 가능
docs 있음
example 있음
API stable
test 가능
```

## 5. Maturity

성숙도.

```text
prototype
beta
stable
enterprise
deprecated
```

## 6. Risk

```text
security
privacy
license
cost
vendor lock-in
maintenance
prompt injection
data leakage
```

## 7. Fit

특정 사용자/작업에 맞는가?

```text
디자이너에게 좋음
개발자에게 좋음
연구자에게 좋음
영상 제작자에게 좋음
초보자에게는 어려움
```

---

# 7. Capability Score

기술마다 점수를 만든다.

```json
{
  "capability_score": {
    "novelty": 0.74,
    "utility": 0.88,
    "quality_impact": 0.91,
    "reproducibility": 0.67,
    "maturity": 0.62,
    "risk": 0.31,
    "user_fit": 0.86,
    "overall": 0.81
  }
}
```

중요한 건 overall 하나로 끝내지 않는 것.

어떤 기술은 위험하지만 혁신적일 수 있다.

```text
high novelty
high risk
low maturity
```

이건 버릴 게 아니라:

```text
watchlist
experimental
not production yet
```

으로 저장해야 해.

---

# 8. Legacy Stratifier: 낡은 것을 버리지 않는 층

너가 말한 “버리는 게 아니다. 안 좋은 게 있어야 좋은 게 왜 좋은지 안다” 이게 핵심이야.

그래서 legacy는 삭제하지 않고 **stratum**으로 저장한다.

## 기술 상태

```text
emerging
promising
useful
mainstream
legacy
deprecated
failed
dangerous
```

예:

```text
screenshot-only design-to-code
= legacy baseline

Figma MCP design-to-code
= high-quality structured workflow

manual prompt-only video generation
= low-control baseline

Higgsfield-style multi-model video workspace
= high-control creative workflow
```

Legacy는 비교 기준이다.

---

## Legacy가 필요한 이유

```text
좋은 기술이 왜 좋은지 설명하려면
나쁜/낡은 방법과 비교해야 한다.

추천의 설득력을 만들려면
“기존 방식 대비 무엇이 달라지는지”가 있어야 한다.

agent가 실패하지 않으려면
피해야 할 legacy workflow도 알아야 한다.
```

그래서 Capability Ontology에는 이렇게 저장한다.

```text
Workflow A SUPERSEDES Workflow B
Tool X IMPROVES Capability Y over Tool Z
Method A IS_BASELINE_FOR Method B
Tool X HAS_FAILURE_MODE Y
```

---

# 9. Capability Ontology + Surfer/Discriminator

최종 ontology는 이렇게 된다.

```text
(:Technology)
(:MCPServer)
(:App)
(:Paper)
(:GitHubRepo)
(:Skill)
(:Workflow)
(:Capability)
(:Task)
(:Benchmark)
(:Evidence)
(:Risk)
(:LegacyMethod)
(:QualityProfile)
(:UserPersona)
```

관계:

```text
(:Technology)-[:PROVIDES]->(:Capability)
(:Workflow)-[:USES]->(:Technology)
(:Workflow)-[:ACHIEVES]->(:Task)
(:Technology)-[:CLAIMS]->(:Benchmark)
(:Evidence)-[:SUPPORTS]->(:Claim)
(:Evidence)-[:CONTRADICTS]->(:Claim)
(:Technology)-[:SUPERSEDES]->(:LegacyMethod)
(:Technology)-[:HAS_RISK]->(:Risk)
(:Technology)-[:GOOD_FOR]->(:UserPersona)
(:Technology)-[:BAD_FOR]->(:Task)
```

---

# 10. Surfer–Discriminator Pipeline

```text
1. Source Discovery
2. Signal Collection
3. Entity Extraction
4. Capability Mapping
5. Claim Extraction
6. Evidence Gathering
7. Discriminator Evaluation
8. Legacy Comparison
9. Ontology Update
10. Recommendation Generation
```

각 단계:

## 1. Source Discovery

어디를 볼지 정한다.

```text
MCP registry
GitHub
arXiv
product changelog
community
social
```

## 2. Signal Collection

새로운 글/논문/repo/tool을 수집.

## 3. Entity Extraction

```text
tool name
provider
capability
target task
pricing
license
integration
```

## 4. Capability Mapping

“이게 뭘 할 수 있는가?”로 변환.

```text
Figma MCP → read_design_components
Runway → image_to_video
Higgsfield → multi_model_video_generation
arXiv paper → new method for retrieval/reranking
```

## 5. Claim Extraction

기술이 주장하는 것.

```text
“10x faster”
“production-ready”
“state-of-the-art”
“supports Claude Code”
```

## 6. Evidence Gathering

```text
official docs
GitHub activity
user reports
benchmarks
examples
issues
security reports
pricing docs
```

## 7. Discriminator Evaluation

실제 점수화.

## 8. Legacy Comparison

기존 방식과 비교.

## 9. Ontology Update

Capability graph에 저장.

## 10. Recommendation

사용자 작업에 연결.

---

# 11. Discriminator는 여러 개가 있어야 함

하나의 평가자가 아니라 specialized discriminator들이 필요해.

## 1. Innovation Discriminator

```text
진짜 새로운 primitive인가?
기존 wrapper인가?
```

## 2. Utility Discriminator

```text
실제 작업에서 쓰이는가?
누구에게 유용한가?
```

## 3. Quality Discriminator

```text
작업물 품질이 좋아지는가?
sample output은 어떤가?
```

## 4. Security Discriminator

```text
권한 과다?
API key 노출?
prompt injection 위험?
로컬 파일 접근 위험?
```

## 5. Cost Discriminator

```text
비용 대비 가치?
무료/유료/enterprise?
```

## 6. Reproducibility Discriminator

```text
내 환경에서 재현 가능한가?
설치 문서가 있는가?
```

## 7. Legacy Discriminator

```text
무엇을 대체하는가?
기존 방식은 왜 부족했는가?
언제는 legacy가 더 나은가?
```

---

# 12. 실제 사용 예시

사용자:

```text
“랜딩페이지 만들 건데 제일 좋은 workflow 추천해줘.”
```

시스템:

```text
1. 사용자 환경 스캔
- Claude Code 있음
- Codex 있음
- Figma MCP 없음
- GitHub 연결됨
- Visual QA 없음

2. Capability 필요조건 추출
- design source access
- component extraction
- design token mapping
- implementation
- visual verification

3. Surfer 최신 정보 확인
- Figma MCP available
- relevant design-to-code skill found
- visual regression tool available

4. Discriminator 판단
- screenshot-only path는 legacy baseline
- Figma MCP path는 quality impact high
- setup complexity medium
- security risk: Figma file access scope 필요

5. 추천
High-quality workflow:
Claude Code + Figma MCP + GitHub repo + design-to-code skill + visual QA

6. 자동 생성
- 설치 가이드
- MCP config
- Agent Handoff
- Skill template
```

---

# 13. 이걸 SaaS로 만들면 화면은 이렇게

## Capability Radar

```text
최신 기술 feed

[New] Figma MCP update
[Hot] Higgsfield multi-model video workflow
[Paper] New agent tool-use benchmark
[Repo] Fast-growing MCP server for Vercel
[Risk] MCP server security issue reported
```

## Technology Card

```text
Figma MCP

Capabilities:
- read design data
- extract components
- generate code from frames

Works with:
- Claude Code
- Codex
- Cursor

Quality Impact:
Design-to-code: High

Risks:
- requires Figma file access
- auth scope needed

Legacy baseline:
- screenshot-only implementation

Recommendation:
Use for design-to-code workflows.
```

## Workflow Recommendation

```text
Task:
“Create high-quality product demo video”

Recommended:
Higgsfield + image reference + camera control + brand memory + post-editing

Avoid:
single low-quality text-to-video prompt if brand consistency matters
```

## Legacy Timeline

```text
Design-to-code evolution:

Manual screenshot interpretation
→ GPT screenshot analysis
→ Figma export plugins
→ Figma MCP
→ design-system-aware code generation
```

이 타임라인이 아주 중요해.
기술의 의미는 시간축에서 보인다.

---

# 14. “WWW의 모든 지식을 흡수”를 현실적으로 구현하는 법

모든 WWW를 무작정 크롤링하면 안 돼.
법적/기술적/비용 문제가 크다.

현실적 방식은:

```text
1. 공식 API 우선
2. RSS / OAI-PMH / registry / changelog 우선
3. GitHub metadata / releases / issues 활용
4. 허용된 검색 API 사용
5. 사용자가 제공한 링크/문서 수집
6. robots.txt와 약관 준수
7. 원문 복제보다 metadata/evidence/reference 중심 저장
```

특히 Reddit/X/Threads는 scraping보다 공식 API, 검색 결과, 사용자 제공 링크, 공개 임베드/허용 범위 중심으로 가야 한다. Reddit은 AI scraping/검색 접근을 강하게 제한하는 방향으로 움직이고 있어 주의가 필요하다. ([The Verge][3])

즉 “모든 지식 흡수”의 의미는:

```text
원문 전체를 무단 저장한다
```

가 아니라:

```text
기술 신호를 감지하고
요약/메타데이터/근거 링크/평가 결과를 구조화한다
```

로 잡아야 한다.

---

# 15. MemoryOS와 결합하면 더 강해짐

CapabilityOS는 일반 기술 지식을 모은다.

MemoryOS는 사용자의 개인 작업 맥락을 안다.

결합하면:

```text
CapabilityOS:
“Figma MCP가 design-to-code 품질을 높인다.”

MemoryOS:
“이 사용자는 Uri landing page, 3D visual, campus app 작업을 자주 한다.”

결과:
“너는 Figma MCP + visual QA skill을 설정하면 Uri 작업 품질이 크게 올라갈 가능성이 높다.”
```

이게 개인화된 AI capability advisor야.

---

# 16. 시스템 이름

이 전체 시스템은 이렇게 부를 수 있어.

## 기술명 후보

```text
Capability Radar
Surfer–Discriminator Engine
Tech Surfer
Capability Intelligence Layer
AI Work Intelligence
ToolGraph Radar
```

내 추천:

```text
Capability Radar
```

그 안의 컴포넌트:

```text
Surfer = 발견
Discriminator = 판별
Stratifier = legacy/시간축 정리
Recommender = 사용자 작업 연결
```

---

# 17. 새로운 용어 정의

## Surfer

WWW, registry, GitHub, papers, communities, social feeds를 돌며 기술 신호를 발견하는 agent.

## Discriminator

발견된 기술이 실제로 혁신적인지, 쓸만한지, 위험한지, 작업물 품질에 영향을 주는지 평가하는 agent.

## Legacy Stratifier

낡은 기술을 버리지 않고, 왜 낡았는지/언제 여전히 유용한지/무엇으로 대체되는지 시간축에 정리하는 agent.

## Capability Ontology

app, MCP, skill, model, workflow, paper, tool이 어떤 작업 능력을 제공하는지 표현하는 지식 그래프.

## Capability Gap

사용자가 원하는 작업을 하기 위해 필요한 능력과 현재 환경이 가진 능력 사이의 차이.

## Workflow Quality Tier

특정 작업을 수행하는 workflow의 예상 품질 수준.

```text
baseline
usable
high-quality
production-grade
frontier
```

---

# 18. MVP로 자르면

처음부터 모든 WWW를 다 하지 마.

## v0.1

```text
MCP Registry + GitHub + arXiv만 본다.
Design-to-code vertical만 평가한다.
```

수집 대상:

```text
Figma MCP
GitHub MCP
Vercel MCP
design-to-code repos
UI generation papers
visual QA tools
```

기능:

```text
1. 새로운 MCP/repo/paper 수집
2. capability 추출
3. technology card 생성
4. legacy baseline과 비교
5. design-to-code workflow 추천
```

## v0.2

```text
Video creation vertical 추가
Higgsfield / Runway / Veo / Kling / Sora workflows
```

## v0.3

```text
Research-to-document vertical 추가
arXiv / Perplexity / citation workflows
```

---

# 19. 네 비전과 연결

네가 하려는 건 결국 이거야.

```text
사용자가 AI를 몰라서 낮은 품질의 작업을 하는 문제를 줄인다.
좋은 모델, 좋은 도구, 좋은 MCP, 좋은 Skill, 좋은 workflow를 자동으로 찾아준다.
기술이 낡아도 버리지 않고 비교 지식으로 보존한다.
사람들이 AI 사용 격차 없이 더 높은 결과물을 만들게 한다.
```

이건 충분히 SaaS다.

더 정확히는:

> **AI Capability Intelligence SaaS**

---

# 20. 최종 구조

```text
MemoryOS
= 사용자의 기억과 맥락

CapabilityOS
= AI app / MCP / skill / tool / workflow ontology

Capability Radar
= 최신 기술을 발견하고 평가하는 Surfer–Discriminator engine

Chatbot Harness
= 여러 모델로 사고 정제

Agent Harness
= 최적 tool stack으로 실행

Desktop
= 이 모든 것을 보여주는 cockpit
```

---

# 21. 한 문장으로 정리

> **Surfer가 WWW에서 최신 AI capability를 발견하고, Discriminator가 그것의 실효성·품질·위험·legacy 관계를 판별하며, Capability Ontology가 이를 작업 능력 그래프로 구조화하고, MemoryOS가 사용자 맥락에 맞춰 최적의 workflow로 추천한다.**

더 제품적으로:

> **Capability Radar는 AI를 잘 아는 사람만 쓰던 최신 도구 조합과 workflow를 자동으로 찾아주고 검증해서, 누구나 같은 비용으로 더 높은 품질의 결과물을 만들게 하는 시스템이다.**

[1]: https://github.com/modelcontextprotocol/registry?utm_source=chatgpt.com "modelcontextprotocol/registry: A community driven ..."
[2]: https://info.arxiv.org/help/api/user-manual.html?utm_source=chatgpt.com "arXiv API User's Manual"
[3]: https://www.theverge.com/2024/7/24/24205244/reddit-blocking-search-engine-crawlers-ai-bot-google?utm_source=chatgpt.com "Reddit is now blocking major search engines and AI bots - except the ones that pay"
