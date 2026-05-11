# CapabilityOS Design Notes From The Hive Sprint

This document captures what the Hive Mind production/public-alpha sprint taught
us about what CapabilityOS must produce. It is not the CapabilityOS vision doc;
it is an implementation checklist for the first useful CapabilityOS loop.

Hive acted as the runtime/chair. MemoryOS acted as the accepted-memory
substrate. CapabilityOS should become the capability recommendation substrate:

```text
User goal
  -> Hive asks MemoryOS what context matters
  -> Hive asks CapabilityOS what tools/models/workflows can do the job
  -> Hive executes through provider/native CLIs
  -> Hive records receipts and outcomes
  -> MemoryOS remembers accepted decisions
  -> CapabilityOS updates capability quality from evidence
```

## North Star For CapabilityOS

CapabilityOS should answer:

```text
For this task, which tools, models, skills, MCP servers, workflows, and
provider modes should be composed, and why should the operator trust that
recommendation?
```

It should not be a tool directory. A directory says "Figma MCP exists."
CapabilityOS should say:

```text
For design-to-code work:
- use Figma MCP to read component/variable context
- use Codex for repo edits
- use a visual QA skill before merge
- use Claude/Gemini as foreign-context reviewers when design intent is ambiguous
- avoid local 1.7B models for final component judgment
- evidence: previous run outcomes, latency, failure rate, review notes
```

## Lesson 1: Start With Artifacts, Not A Smart Router

Hive became useful only after it had durable artifacts:

- run folders
- provider result receipts
- execution ledger
- inspect reports
- release gate artifacts
- reviewer attack packs

CapabilityOS should copy that pattern. Before building a recommendation engine,
define the files it must emit.

Minimum first artifacts:

```text
.capabilityos/
  registry/
    capabilities.jsonl
    tools.jsonl
    models.jsonl
    skills.jsonl
    mcp_servers.jsonl
    workflows.jsonl
  observations/
    capability_observations.jsonl
  recommendations/
    <recommendation_id>.json
  reviews/
    <recommendation_id>_review.md
  benchmarks/
    <capability_or_workflow_id>.json
```

## Lesson 2: Capability Cards Need Evidence, Not Marketing

A `CapabilityCard` should be small, testable, and evidence-backed.

Suggested shape:

```json
{
  "schema_version": 1,
  "capability_id": "design_to_react_implementation",
  "label": "Design-to-React implementation",
  "description": "Turn structured design context into repo changes with visual QA.",
  "inputs": ["figma_file", "repo", "design_system_rules"],
  "outputs": ["code_diff", "visual_qa_report", "review_notes"],
  "required_tools": ["figma_mcp", "repo_editor", "browser_visual_qa"],
  "candidate_providers": ["codex", "claude", "gemini"],
  "risk_classes": ["repo_write", "visual_regression", "design_semantics"],
  "quality_metrics": ["test_pass_rate", "visual_match_score", "review_blocker_rate"],
  "evidence_refs": ["hive_run:<run_id>", "review:<path>", "benchmark:<path>"],
  "status": "candidate"
}
```

Do not accept vendor descriptions as truth. Store them as source evidence, then
attach observed results from Hive runs.

## Lesson 3: Workflows Are First-Class Capabilities

The Hive sprint showed that the valuable unit is often not one tool. It is a
workflow composition:

```text
quickstart demo
  -> route
  -> produce artifacts
  -> inspect
  -> memory draft
  -> observability graph

memory-loop demo
  -> Hive run
  -> MemoryOS import
  -> approve
  -> context build
  -> next Hive run
```

CapabilityOS should store `WorkflowRecipe`, not just `Tool`.

Suggested `WorkflowRecipe` fields:

```json
{
  "workflow_id": "public_alpha_review_loop",
  "goal": "Validate whether a repo is ready for public alpha.",
  "steps": [
    {"capability": "run_release_gate", "owner": "codex"},
    {"capability": "foreign_context_review", "owner": "claude"},
    {"capability": "fix_public_entrypoint", "owner": "codex"},
    {"capability": "review_recheck", "owner": "claude"}
  ],
  "barriers": [
    "release_gate_pass",
    "no_high_medium_review_blockers"
  ],
  "outputs": [
    "review_report",
    "gate_report",
    "commit_ref"
  ],
  "when_to_use": ["public_release", "package_publish", "security_sensitive_docs"],
  "when_not_to_use": ["trivial_one_shot_cli"]
}
```

## Lesson 4: Recommendations Need Receipts

CapabilityOS recommendations should leave a receipt, just like Hive execution.

Minimum `CapabilityRecommendation`:

```json
{
  "schema_version": 1,
  "recommendation_id": "crec_...",
  "task": "Make the README public-alpha ready.",
  "task_features": {
    "repo_write": true,
    "public_claims": true,
    "needs_foreign_review": true,
    "memory_feedback": false
  },
  "recommended_workflow": "public_alpha_review_loop",
  "recommended_capabilities": [
    "release_gate_check",
    "readme_public_onboarding",
    "foreign_context_review"
  ],
  "provider_routing": {
    "executor": "codex",
    "reviewer": "claude-haiku-4-5",
    "local_worker": "none"
  },
  "why": [
    "public-facing wording requires review separate from implementation momentum",
    "release gate must remain green after docs changes"
  ],
  "risk_level": "medium",
  "required_proofs": [
    "tests_pass",
    "release_gate_pass",
    "reviewer_no_high_medium_blockers"
  ],
  "fallbacks": [
    "manual reviewer if provider CLI unavailable",
    "dry-run only if repo is dirty"
  ]
}
```

Hive should be able to call this as:

```text
capabilityos recommend --for hive --task "<prompt>" --json
```

and receive a recommendation artifact it can attach to the run.

## Lesson 5: The Same Tool Has Different Modes

Hive learned this with provider passthrough:

- Claude as planner
- Claude as foreign-context reviewer
- Codex as executor
- Codex as reviewer
- native CLI passthrough
- role-adapter prompt board
- dry-run
- execute

CapabilityOS must model mode separately from tool identity.

Suggested nodes:

```text
ProviderRuntime: claude_cli
ProviderMode: claude_cli.plan
ProviderMode: claude_cli.review_foreign_context
ProviderMode: claude_cli.execute_with_permissions
ProviderMode: claude_cli.native_passthrough_dry_run
ProviderMode: claude_cli.native_passthrough_execute
```

Quality and risk attach to the mode, not only the provider.

## Lesson 6: Foreign-Context Review Is A Capability

The public-alpha review found a real blocker that the in-directory executor was
too close to notice: README internal-context leakage. That is a reusable
capability.

CapabilityOS should store:

```text
capability: foreign_context_review
input: compact artifact pack, public claim, target audience
provider candidates: Claude, Gemini, human reviewer
quality signal: number/severity of blockers found, false-positive rate
required proof: written review artifact and recheck result
```

When to route:

- public docs
- security boundaries
- provider permission policy
- architecture claims
- MemoryOS/Hive/CapabilityOS contract changes
- research framing

## Lesson 7: Negative Recommendations Matter

Hive's value benchmark explicitly says direct CLI is better for trivial
one-shot tasks. CapabilityOS should be willing to recommend "do not use Hive"
or "do not use this workflow."

Recommendation examples:

```text
Task: "show claude version"
Recommendation: direct provider CLI
Reason: Hive adds audit overhead with no coordination value

Task: "public alpha release"
Recommendation: Hive workflow + Claude review + release gate
Reason: needs receipts, adversarial review, and repeatable gate evidence
```

Negative routing is what makes the system trustworthy.

## Lesson 8: Quality Memory Must Come From Outcomes

CapabilityOS should not update quality profiles from opinions alone. It should
consume outcomes:

- tests passed/failed
- release gate passed/failed
- reviewer blocker severity
- timeout/latency
- operator override
- rework required after recommendation
- artifact drift or missing receipt
- whether MemoryOS accepted the resulting memory

Suggested `CapabilityObservation`:

```json
{
  "schema_version": 1,
  "observation_id": "cobs_...",
  "source": "hive_run",
  "run_id": "run_...",
  "recommendation_id": "crec_...",
  "capability_ids": ["foreign_context_review", "readme_public_onboarding"],
  "workflow_id": "public_alpha_review_loop",
  "outcome": "passed_after_fix",
  "metrics": {
    "tests_passed": 291,
    "release_gate_passed": true,
    "high_blockers": 0,
    "medium_blockers_initial": 1,
    "medium_blockers_final": 0
  },
  "evidence_refs": [
    "docs/reviews/PUBLIC_ALPHA_FOREIGN_CONTEXT_REVIEW.md",
    ".hivemind/release/<stamp>"
  ]
}
```

## Lesson 9: CapabilityOS Needs Gates Too

Hive only became publishable when gates were explicit. CapabilityOS needs its
own release and recommendation gates.

Minimum gates:

```text
capabilityos validate registry
capabilityos recommend --dry-run <task-fixture>
capabilityos benchmark workflow <workflow_id>
capabilityos inspect recommendation <recommendation_id>
capabilityos audit evidence
```

Before a recommendation can drive Hive execution, it should pass:

- schema valid
- evidence refs resolvable
- risk class present
- fallback present
- required proof list present
- no unsupported provider mode
- no undocumented permission escalation

## First Sprint For CapabilityOS

Build the smallest loop that lets Hive ask for a recommendation and later feed
back the outcome.

### P0.1 Registry

Create:

```text
capabilityos init
capabilityos registry add/list/validate
```

with JSONL schemas for:

- ToolCard
- ProviderMode
- CapabilityCard
- SkillCard
- WorkflowRecipe
- RiskClass
- EvidenceRef

### P0.2 Recommendation

Create:

```text
capabilityos recommend --task "<task>" --for hive --json
capabilityos inspect <recommendation_id>
```

Start with deterministic rules and fixtures. Do not require LLM routing at
first.

### P0.3 Hive Bridge

Hive consumes:

```text
capabilityos recommend --for hive --task <prompt> --json
  -> .runs/<run_id>/artifacts/capability_recommendation.json
  -> run_state.capability_recommendation
  -> context_pack.md capability section
```

CapabilityOS consumes:

```text
hive inspect <run_id> --json
hive ledger replay --run-id <run_id> --json
docs/reviews/*.md
```

and writes `CapabilityObservation`.

### P0.4 Public Demo

The CapabilityOS equivalent of Hive's quickstart:

```text
capabilityos demo recommend
```

It should show:

```text
Task: make a public-alpha release decision
Recommendation:
  workflow = public_alpha_review_loop
  executor = codex
  reviewer = claude-haiku-4-5
  gates = tests, release gate, foreign-context review
Why:
  public-facing claim + repo-write + release risk
Proof required:
  review artifact + 17/17 gate + commit ref
```

## What Not To Build First

Do not start with:

- a web UI
- a SaaS account model
- embeddings as the primary substrate
- automatic installation of tools
- opaque LLM-only recommendations
- global marketplace crawling

Start with local, inspectable, evidence-backed recommendations. The product can
become SaaS later after the artifact loop is trustworthy.

## Boundary With Hive And MemoryOS

```text
Hive Mind
  owns execution, provider invocation, run ledger, proof, inspect, live surface

MemoryOS
  owns accepted memory, context retrieval, review lifecycle, memory provenance

CapabilityOS
  owns capability registry, workflow recipes, recommendation receipts, quality
  profiles, and capability outcome observations
```

Hive may execute a CapabilityOS recommendation. MemoryOS may remember the
decision. CapabilityOS should not directly execute provider CLIs or silently
accept memory.

## Working Rule

Every CapabilityOS recommendation should be auditable in one sentence:

```text
CapabilityOS recommended <workflow> for <task> because <evidence>, with
<risks>, requiring <proofs>.
```

If that sentence cannot be produced, the recommendation is not ready to drive
Hive.
