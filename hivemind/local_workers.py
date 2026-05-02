"""Local LLM worker prompts and runtime adapters.

This module keeps local LLM usage schema-first and optional. The Hive Mind
pipeline can render prompts without a runtime, and can call a configured local
backend when one is available on the machine.
"""

from __future__ import annotations

import json
import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class WorkerSpec:
    name: str
    purpose: str
    default_model: str
    fast_model: str
    strong_model: str
    system: str
    output_schema: dict[str, Any]
    timeout_seconds: int = 120


WORKERS: dict[str, WorkerSpec] = {
    "intent_router": WorkerSpec(
        name="intent_router",
        purpose="Decompose a user prompt into local/provider roles and ordered harness actions.",
        default_model="qwen3:1.7b",
        fast_model="qwen3:1.7b",
        strong_model="deepseek-coder-v2:16b",
        system=(
            "You are LocalIntentRouter for Hive Mind. Decompose the user's prompt into a small, "
            "safe harness plan. Route work to local workers, Claude planner/reviewer, Codex executor, "
            "and Gemini reviewer by role. Do not execute code. Return valid JSON only."
        ),
        output_schema={
            "intent": "implementation|review|research|memory_import|documentation|planning|debugging|unknown",
            "summary": "one sentence task summary",
            "complexity": "fast|default|strong",
            "actions": [
                {
                    "provider": "local|claude|codex|gemini",
                    "role": "context|handoff|memory|summarize|review|classify|planner|executor|reviewer",
                    "reason": "why this role is needed",
                    "execute": False,
                }
            ],
            "risks": [],
            "open_questions": [],
            "confidence": 0.0,
            "should_escalate": False,
            "escalation_reason": "",
        },
        timeout_seconds=60,
    ),
    "classifier": WorkerSpec(
        name="classifier",
        purpose="Classify short snippets into task, project, memory type, and escalation hints.",
        default_model="phi4-mini",
        fast_model="qwen3:1.7b",
        strong_model="phi4-mini",
        system=(
            "You are LocalClassifier for Hive Mind. Classify short text only. "
            "Do not summarize or decide. Return valid JSON only."
        ),
        output_schema={
            "task_type": "memory_extraction|capability_extraction|context_compression|handoff|log_summary|diff_review|other",
            "project": "project name or unknown",
            "memory_type_candidates": [],
            "confidence": 0.0,
            "should_escalate": False,
            "escalation_reason": "",
        },
    ),
    "json_normalizer": WorkerSpec(
        name="json_normalizer",
        purpose="Normalize rough local output into strict JSON for downstream schemas.",
        default_model="phi4-mini",
        fast_model="qwen3:1.7b",
        strong_model="phi4-mini",
        system=(
            "You are LocalJsonNormalizer for Hive Mind. Convert rough input into strict JSON only. "
            "Do not add claims. Preserve uncertainty and include confidence."
        ),
        output_schema={
            "ok": True,
            "normalized": {},
            "confidence": 0.0,
            "should_escalate": False,
            "escalation_reason": "",
        },
    ),
    "memory_extractor": WorkerSpec(
        name="memory_extractor",
        purpose="Extract reviewable memory drafts from a conversation or note segment.",
        default_model="phi4-mini",
        fast_model="qwen3:1.7b",
        strong_model="qwen3:8b",
        system=(
            "You are LocalMemoryExtractor for Hive Mind. Extract only draft memory objects. "
            "Do not make final decisions. Preserve uncertainty and raw references. "
            "Return valid JSON only."
        ),
        output_schema={
            "memory_drafts": [
                {
                    "type": "idea|decision|action|question|constraint|preference|artifact|reflection",
                    "content": "short faithful draft",
                    "origin": "user|assistant|mixed|unknown",
                    "confidence": 0.0,
                    "raw_refs": ["source-local-reference"],
                    "needs_review": True,
                }
            ],
            "uncertain_items": [{"content": "ambiguous item", "reason": "why uncertain"}],
            "needs_human_or_claude_review": True,
        },
    ),
    "context_compressor": WorkerSpec(
        name="context_compressor",
        purpose="Compress retrieved memory/context into a small handoff pack for Claude/Codex.",
        default_model="qwen3:8b",
        fast_model="phi4-mini",
        strong_model="qwen3:8b",
        system=(
            "You are LocalContextCompressor for Hive Mind. Compress context without adding new claims. "
            "Keep decisions, constraints, source IDs, risks, and open questions. Return valid JSON only."
        ),
        output_schema={
            "context_pack": {
                "objective": "what this context is for",
                "relevant_decisions": [],
                "constraints": [],
                "source_refs": [],
                "open_questions": [],
                "risks": [],
                "compressed_summary": "2-4KB maximum",
            },
            "needs_claude_review": False,
        },
    ),
    "handoff_drafter": WorkerSpec(
        name="handoff_drafter",
        purpose="Draft an implementation handoff before Codex edits the repo.",
        default_model="deepseek-coder-v2:16b",
        fast_model="qwen3:8b",
        strong_model="deepseek-coder-v2:16b",
        system=(
            "You are LocalHandoffDrafter for Hive Mind. Draft a concrete engineering handoff. "
            "Do not claim the plan is final. Return valid JSON only."
        ),
        output_schema={
            "handoff": {
                "objective": "",
                "constraints": [],
                "candidate_files": [],
                "steps": [],
                "acceptance_criteria": [],
                "risks": [],
                "unknowns": [],
            },
            "needs_codex": True,
            "needs_claude_review": False,
        },
    ),
    "log_summarizer": WorkerSpec(
        name="log_summarizer",
        purpose="Summarize run logs, diffs, and test output into memory update candidates.",
        default_model="deepseek-coder:6.7b",
        fast_model="qwen2.5-coder:7b",
        strong_model="deepseek-coder-v2:16b",
        system=(
            "You are LocalLogSummarizer for Hive Mind. Summarize what changed, what passed, "
            "what failed, and what should be remembered. Return valid JSON only."
        ),
        output_schema={
            "changed": [],
            "verification": [],
            "unresolved": [],
            "memory_update_candidates": [],
            "needs_followup": False,
        },
    ),
    "capability_extractor": WorkerSpec(
        name="capability_extractor",
        purpose="Draft CapabilityOS technology cards from README/docs text.",
        default_model="phi4-mini",
        fast_model="qwen3:8b",
        strong_model="qwen2.5-coder:7b",
        system=(
            "You are LocalCapabilityExtractor for CapabilityOS. Extract tool capabilities, "
            "setup steps, risks, compatible runtimes, and workflow fit. Return valid JSON only."
        ),
        output_schema={
            "technology_card": {
                "name": "",
                "category": "",
                "capabilities": [],
                "setup_steps": [],
                "compatible_runtimes": [],
                "risks": [],
                "workflow_fit": [],
                "confidence": 0.0,
            },
            "uncertain_items": [],
            "needs_claude_review": False,
        },
    ),
    "diff_reviewer": WorkerSpec(
        name="diff_reviewer",
        purpose="Review a git diff and test output for risks before Claude/Codex final review.",
        default_model="deepseek-coder-v2:16b",
        fast_model="qwen2.5-coder:14b",
        strong_model="deepseek-coder-v2:16b",
        system=(
            "You are LocalDiffReviewer for Hive Mind. Review diffs as a first-pass risk scanner. "
            "Focus on behavioral regressions, schema changes, security/privacy risks, and missing tests. "
            "Return valid JSON only."
        ),
        output_schema={
            "risk_summary": "",
            "findings": [
                {
                    "severity": "high|medium|low",
                    "file_path": "",
                    "line_hint": "",
                    "issue": "",
                    "recommended_check": "",
                }
            ],
            "missing_tests": [],
            "safe_to_skip_claude": False,
            "confidence": 0.0,
            "should_escalate": True,
            "escalation_reason": "",
        },
    ),
}


def list_workers() -> list[dict[str, str]]:
    return [
        {
            "name": spec.name,
            "purpose": spec.purpose,
            "fast_model": spec.fast_model,
            "default_model": spec.default_model,
            "strong_model": spec.strong_model,
        }
        for spec in WORKERS.values()
    ]


def worker_route_table() -> dict[str, Any]:
    return {
        name: {
            "purpose": spec.purpose,
            "models": {
                "fast": spec.fast_model,
                "default": spec.default_model,
                "strong": spec.strong_model,
            },
            "expected_schema": spec.output_schema,
            "escalation_fields": ["confidence", "should_escalate", "escalation_reason"],
        }
        for name, spec in WORKERS.items()
    }


def validate_worker_result(worker_name: str, result: dict[str, Any]) -> dict[str, Any]:
    spec = get_worker(worker_name)
    parsed = result.get("parsed")
    issues: list[str] = []
    if not isinstance(parsed, dict):
        issues.append("worker output parsed payload is not an object")
        parsed = {}
    if parsed.get("json_parse_error"):
        issues.append("worker output was not valid JSON")
    for key in spec.output_schema:
        if key not in parsed:
            issues.append(f"worker output missing expected key: {key}")
    confidence = extract_confidence(parsed)
    should_escalate = bool(
        parsed.get("should_escalate")
        or parsed.get("needs_claude_review")
        or parsed.get("needs_human_or_claude_review")
        or parsed.get("needs_followup")
        or issues
    )
    escalation_reason = parsed.get("escalation_reason") or ("; ".join(issues) if issues else "")
    return {
        "valid": not issues,
        "issues": issues,
        "confidence": confidence,
        "should_escalate": should_escalate,
        "escalation_reason": escalation_reason,
    }


def extract_confidence(parsed: dict[str, Any]) -> float | None:
    value = parsed.get("confidence")
    if value is None and isinstance(parsed.get("technology_card"), dict):
        value = parsed["technology_card"].get("confidence")
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, number))


def choose_model(worker_name: str, complexity: str = "default") -> str:
    spec = get_worker(worker_name)
    if complexity == "fast":
        return spec.fast_model
    if complexity == "strong":
        return spec.strong_model
    if complexity != "default":
        raise ValueError("complexity must be one of: fast, default, strong")
    return spec.default_model


def render_prompt(worker_name: str, input_text: str, source_ref: str = "manual") -> str:
    spec = get_worker(worker_name)
    schema = json.dumps(spec.output_schema, ensure_ascii=False, indent=2)
    return (
        f"{spec.system}\n\n"
        f"Output schema:\n{schema}\n\n"
        f"Source ref: {source_ref}\n\n"
        f"Input:\n{input_text.strip()}\n"
    )


def run_worker(
    worker_name: str,
    input_text: str,
    model: str | None = None,
    runtime: str = "auto",
    base_url: str = "http://127.0.0.1:11434",
    source_ref: str = "manual",
) -> dict[str, Any]:
    runtime = resolve_local_runtime(runtime)
    if runtime != "ollama":
        raise ValueError(f"Unsupported local worker runtime adapter: {runtime}")
    spec = get_worker(worker_name)
    chosen_model = model or spec.default_model
    prompt = render_prompt(worker_name, input_text, source_ref=source_ref)
    return call_ollama_generate(base_url=base_url, model=chosen_model, prompt=prompt, timeout=spec.timeout_seconds)


def resolve_local_runtime(runtime: str = "auto") -> str:
    if runtime == "auto":
        return os.environ.get("HIVE_LOCAL_BACKEND") or os.environ.get("HIVE_LOCAL_RUNTIME") or "ollama"
    return runtime


def get_worker(worker_name: str) -> WorkerSpec:
    try:
        return WORKERS[worker_name]
    except KeyError as exc:
        names = ", ".join(sorted(WORKERS))
        raise ValueError(f"Unknown local worker '{worker_name}'. Available: {names}") from exc


def read_input(path: Path | None, max_chars: int) -> tuple[str, str]:
    if path is None:
        raise ValueError("An input file is required for now.")
    text = path.read_text(encoding="utf-8")
    return text[:max_chars], path.as_posix()


def local_runtime_status() -> dict[str, Any]:
    local_ollama = Path(".local/ollama/bin/ollama")
    return {
        "ollama_binary": shutil.which("ollama") or (local_ollama.as_posix() if local_ollama.exists() else None),
        "llama_server_binary": shutil.which("llama-server"),
        "llama_cli_binary": shutil.which("llama-cli"),
        "workers": list_workers(),
    }


def call_ollama_generate(base_url: str, model: str, prompt: str, timeout: int | None = None) -> dict[str, Any]:
    timeout_seconds = int(os.environ.get("HIVE_LOCAL_WORKER_TIMEOUT", str(timeout or 120)))
    url = base_url.rstrip("/") + "/api/generate"
    payload = ollama_generate_payload(model, prompt)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(
            f"Could not complete Ollama request at {base_url} within {timeout_seconds}s. "
            "Start or tune that adapter, use a smaller model, or set HIVE_LOCAL_BACKEND to another supported runtime."
        ) from exc

    raw = body.get("response", "")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"raw_response": raw, "json_parse_error": True}
    return {
        "runtime": "ollama",
        "model": model,
        "parsed": parsed,
        "raw": raw,
        "done": body.get("done"),
    }


def ollama_generate_payload(model: str, prompt: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1},
    }
    if requires_no_think(model):
        payload["prompt"] = add_no_think(prompt)
        # Ollama expects `think` at the top level. Putting it in `options` does not
        # disable qwen3 thinking and can produce empty `{}` under `format: json`.
        payload["think"] = False
    return payload


def requires_no_think(model: str) -> bool:
    normalized = model.lower()
    return normalized.startswith("qwen3") or "qwen3" in normalized


def add_no_think(prompt: str) -> str:
    stripped = prompt.lstrip()
    if stripped.startswith("/no_think"):
        return prompt
    return "/no_think\n" + prompt
