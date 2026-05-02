#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODEL="${1:-${HIVE_BENCH_MODEL:-qwen3:1.7b}}"
BACKEND="${HIVE_LOCAL_BACKEND:-ollama}"
MODE="${HIVE_OLLAMA_MODE:-local}"
TIMEOUT="${HIVE_BENCH_TIMEOUT:-90}"

if [[ "$BACKEND" != "ollama" ]]; then
  python -m hivemind.hive local benchmark --backend "$BACKEND" --model "$MODEL" --timeout "$TIMEOUT"
  exit 0
fi

case "$MODE" in
  docker)
    scripts/start-ollama-docker.sh
    ;;
  local)
    mkdir -p .hivemind/logs
    if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      if [[ -x scripts/start-ollama-local.sh ]]; then
        nohup scripts/start-ollama-local.sh > .hivemind/logs/ollama.log 2>&1 &
        echo "Started workspace-local Ollama server. Log: .hivemind/logs/ollama.log"
        sleep 2
      else
        echo "scripts/start-ollama-local.sh is not executable." >&2
        exit 1
      fi
    fi
    ;;
  existing)
    ;;
  *)
    echo "Unknown HIVE_OLLAMA_MODE=$MODE. Use local, docker, or existing." >&2
    exit 1
    ;;
esac

if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama server is not reachable at http://127.0.0.1:11434." >&2
  exit 1
fi

if ! curl -fsS http://127.0.0.1:11434/api/tags | grep -q "\"name\":\"$MODEL\""; then
  echo "Model $MODEL is not loaded in the active Ollama server."
  echo "Attempting pull through the active server."
  if command -v ollama >/dev/null 2>&1; then
    ollama pull "$MODEL"
  elif [[ -x scripts/ollama-local.sh && "$MODE" == "local" ]]; then
    scripts/ollama-local.sh pull "$MODEL"
  else
    echo "No local ollama CLI available for pull. For Docker, run:" >&2
    echo "  docker exec -it ${OLLAMA_DOCKER_NAME:-hivemind-ollama} ollama pull $MODEL" >&2
    exit 1
  fi
fi

python -m hivemind.hive local benchmark --backend ollama --model "$MODEL" --timeout "$TIMEOUT"
