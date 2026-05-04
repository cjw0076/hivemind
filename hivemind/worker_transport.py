"""WorkerTransport interface — boundary definition only.

Current transports (all local-first, filesystem blackboard):
  local_subprocess   harness.invoke_external_agent via subprocess
  provider_cli       same — provider CLIs (claude, codex, gemini)
  local_llm_backend  harness.invoke_local → Ollama HTTP

Deferred (interface reserved, not implemented):
  future_remote_worker  multi-machine, HTTP/WebSocket dispatch

Do NOT implement remote transports until:
  1. local DAG transaction protocol (dag_state.py) is stable
  2. parallel fan-out (barrier join) is proven with local workers

The Protocol here is a type boundary, not a runtime base class.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

# Transport name constants
TRANSPORT_LOCAL_SUBPROCESS: str = "local_subprocess"
TRANSPORT_PROVIDER_CLI: str = "provider_cli"        # alias, same as subprocess
TRANSPORT_LOCAL_LLM: str = "local_llm_backend"
TRANSPORT_REMOTE_WORKER: str = "future_remote_worker"  # deferred

TRANSPORTS_IMPLEMENTED: frozenset[str] = frozenset({
    TRANSPORT_LOCAL_SUBPROCESS,
    TRANSPORT_PROVIDER_CLI,
    TRANSPORT_LOCAL_LLM,
})
TRANSPORTS_DEFERRED: frozenset[str] = frozenset({TRANSPORT_REMOTE_WORKER})


@runtime_checkable
class WorkerTransport(Protocol):
    """Execution backend for a single DAG step.

    All local transports currently go through harness.invoke_external_agent
    (subprocess) or harness.invoke_local (Ollama HTTP). This Protocol is the
    boundary that a future remote transport will implement.

    Contract:
    - invoke() is synchronous from the caller's perspective.
    - Returns {ok: bool, artifact_path: str|None, status: str, idempotency_key: str}.
    - The returned idempotency_key must match the lease key used to acquire the
      step lease, so callers can detect and skip duplicate invocations.
    - Raises RuntimeError only for unrecoverable transport-level errors.
      Application-level failures (step returned status=failed) are NOT exceptions;
      they are surfaced in the result dict.
    """

    def invoke(
        self,
        *,
        step_id: str,
        owner_role: str,
        provider: str,
        role: str,
        prompt: str,
        run_id: str,
        execute: bool,
    ) -> dict[str, Any]:
        """Execute a step and return result."""
        ...

    def transport_name(self) -> str:
        """Return one of the TRANSPORT_* constants."""
        ...
