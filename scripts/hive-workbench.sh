#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python}"
EDITOR_CMD="${EDITOR:-nano}"

mkdir -p .hivemind/logs

if [[ $# -gt 0 ]]; then
  "$PYTHON" -m hivemind.hive run "$*"
elif [[ ! -s .runs/current ]]; then
  "$PYTHON" -m hivemind.hive run "Hive Mind workbench session"
fi

"$PYTHON" -m hivemind.hive settings detect >/dev/null
eval "$("$PYTHON" -m hivemind.hive settings shell)"

if [[ "${HIVE_START_OLLAMA:-1}" == "1" ]]; then
  if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    if [[ -x scripts/start-ollama-local.sh ]]; then
      nohup scripts/start-ollama-local.sh > .hivemind/logs/ollama.log 2>&1 &
      sleep 2
    fi
  fi
fi

context_path="$("$PYTHON" -m hivemind.hive context)"
handoff_path="$("$PYTHON" -m hivemind.hive handoff)"

if [[ "${HIVE_SKIP_EDIT:-0}" != "1" ]]; then
  "$EDITOR_CMD" "$context_path"
fi

"$PYTHON" -m hivemind.hive invoke claude --role planner >/dev/null
"$PYTHON" -m hivemind.hive invoke codex --role executor >/dev/null
"$PYTHON" -m hivemind.hive invoke gemini --role reviewer >/dev/null

if [[ "${HIVE_RUN_LOCAL_CONTEXT:-1}" == "1" ]]; then
  "$PYTHON" -m hivemind.hive invoke local --role context >/dev/null || true
fi

"$PYTHON" -m hivemind.hive verify >/dev/null

echo "Hive Mind workbench ready"
echo "Context: $context_path"
echo "Handoff: $handoff_path"
echo "Provider env loaded from: .hivemind/settings_profile.json"
echo ""
echo "Useful commands:"
echo "  hive tui"
echo "  hive status"
echo "  hive settings shell"
echo ""

if [[ "${HIVE_OPEN_TUI:-1}" == "1" ]]; then
  "$PYTHON" -m hivemind.hive tui
fi
