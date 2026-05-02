#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python}"
EDITOR_CMD="${EDITOR:-nano}"

mkdir -p .memoryos/logs

if [[ $# -gt 0 ]]; then
  "$PYTHON" -m memoryos.mos run "$*"
elif [[ ! -s .runs/current ]]; then
  "$PYTHON" -m memoryos.mos run "MemoryOS workbench session"
fi

"$PYTHON" -m memoryos.mos settings detect >/dev/null
eval "$("$PYTHON" -m memoryos.mos settings shell)"

if [[ "${MOS_START_OLLAMA:-1}" == "1" ]]; then
  if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    if [[ -x scripts/start-ollama-local.sh ]]; then
      nohup scripts/start-ollama-local.sh > .memoryos/logs/ollama.log 2>&1 &
      sleep 2
    fi
  fi
fi

context_path="$("$PYTHON" -m memoryos.mos context)"
handoff_path="$("$PYTHON" -m memoryos.mos handoff)"

if [[ "${MOS_SKIP_EDIT:-0}" != "1" ]]; then
  "$EDITOR_CMD" "$context_path"
fi

"$PYTHON" -m memoryos.mos invoke claude --role planner >/dev/null
"$PYTHON" -m memoryos.mos invoke codex --role executor >/dev/null
"$PYTHON" -m memoryos.mos invoke gemini --role reviewer >/dev/null

if [[ "${MOS_RUN_LOCAL_CONTEXT:-1}" == "1" ]]; then
  "$PYTHON" -m memoryos.mos invoke local --role context >/dev/null || true
fi

"$PYTHON" -m memoryos.mos verify >/dev/null

echo "MemoryOS workbench ready"
echo "Context: $context_path"
echo "Handoff: $handoff_path"
echo "Provider env loaded from: .memoryos/settings_profile.json"
echo ""
echo "Useful commands:"
echo "  mos tui"
echo "  mos status"
echo "  mos settings shell"
echo ""

if [[ "${MOS_OPEN_TUI:-1}" == "1" ]]; then
  "$PYTHON" -m memoryos.mos tui
fi
