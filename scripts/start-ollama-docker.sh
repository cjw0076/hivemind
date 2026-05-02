#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${OLLAMA_DOCKER_IMAGE:-ollama/ollama:latest}"
NAME="${OLLAMA_DOCKER_NAME:-hivemind-ollama}"
PORT="${OLLAMA_PORT:-11434}"
MODELS_DIR="${OLLAMA_MODELS_DIR:-$ROOT_DIR/.local/ollama/models}"
GPU_ARGS=()

if [[ ! "$PORT" =~ ^[0-9]+$ ]] || (( PORT < 1 || PORT > 65535 )); then
  echo "OLLAMA_PORT must be an integer from 1 to 65535." >&2
  exit 1
fi

mkdir -p "$MODELS_DIR"

if command -v nvidia-smi >/dev/null 2>&1; then
  GPU_ARGS=(--gpus all)
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is not installed or not on PATH." >&2
  exit 1
fi

if docker ps --format '{{.Names}}' | grep -qx "$NAME"; then
  echo "Ollama Docker container already running: $NAME"
  exit 0
fi

if docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  docker start "$NAME" >/dev/null
  echo "Started existing Ollama Docker container: $NAME"
  exit 0
fi

docker run -d \
  --name "$NAME" \
  "${GPU_ARGS[@]}" \
  -p "127.0.0.1:${PORT}:11434" \
  -v "$MODELS_DIR:/root/.ollama" \
  "$IMAGE" >/dev/null

echo "Started Ollama Docker container: $NAME"
echo "Endpoint: http://127.0.0.1:${PORT}"
echo "Models: $MODELS_DIR"
