#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR=".hivemind/release/$STAMP"
mkdir -p "$OUT_DIR"

echo "== npm test =="
npm test | tee "$OUT_DIR/npm-test.log"

echo "== git diff --check =="
git diff --check | tee "$OUT_DIR/git-diff-check.log"

echo "== hive doctor all =="
python -m hivemind.hive doctor all --json | tee "$OUT_DIR/hive-doctor-all.json"

echo "== tracked secret scan =="
git ls-files \
  | rg -v '^(docs/(memoryOS|my_world|goen_resonance)|docs/split/|docs/local_llm_use\.md)' \
  | xargs rg -n --hidden --no-ignore-vcs -i \
    '(api[_-]?key|secret|token|password|BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY|sk-[A-Za-z0-9]|ghp_[A-Za-z0-9]|AIza[0-9A-Za-z_-]{20,})' \
  | tee "$OUT_DIR/secret-scan.log" || true

echo "== tracked private path scan =="
git ls-files \
  | rg '(^|/)(\.env|.*secret.*|.*token.*|.*key.*|.*\.pem|.*\.p12|.*\.pfx)$|(^|/)exports?/|(^|/)data/raw|(^|/)\.runs/|(^|/)\.hivemind/|(^|/)\.local/' \
  | tee "$OUT_DIR/private-path-scan.log" || true

echo "Release check artifacts: $OUT_DIR"
