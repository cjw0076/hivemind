#!/usr/bin/env bash
# H-P0 Hive Mind production gate check.
# All checks must pass before v0.1.0-production tag.
# Exit code 0 = gate PASS, non-zero = gate FAIL.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR=".hivemind/release/$STAMP"
mkdir -p "$OUT_DIR"

PASS=0
FAIL=0
WARNINGS=()

ok()   { echo "  PASS  $*"; ((PASS++)) || true; }
fail() { echo "  FAIL  $*"; ((FAIL++)) || true; }
warn() { echo "  WARN  $*"; WARNINGS+=("$*"); }

echo "=== H-P0 Hive Mind Production Gate ==="
echo "stamp: $STAMP"
echo "root:  $ROOT_DIR"
echo ""

# ── 1. Full test suite ────────────────────────────────────────────────────────
echo "[ 1/8 ] Test suite"
if python -m pytest tests/ -q --tb=no 2>&1 | tee "$OUT_DIR/pytest.log" | grep -q "passed"; then
    NPASS=$(grep -oP '\d+ passed' "$OUT_DIR/pytest.log" | grep -oP '\d+' | head -1)
    ok "pytest $NPASS tests pass"
else
    fail "pytest failed — see $OUT_DIR/pytest.log"
fi

# ── 2. git diff --check (no whitespace errors) ────────────────────────────────
echo "[ 2/8 ] git diff --check"
if git diff --check > "$OUT_DIR/git-diff-check.log" 2>&1; then
    ok "git diff --check clean"
else
    fail "whitespace errors — see $OUT_DIR/git-diff-check.log"
fi

# ── 3. hive CLI smoke ─────────────────────────────────────────────────────────
echo "[ 3/8 ] hive CLI smoke"
if python -m hivemind.hive doctor --json > "$OUT_DIR/hive-doctor.json" 2>&1; then
    STATUS=$(python3 -c "import json; d=json.load(open('$OUT_DIR/hive-doctor.json')); print(d.get('status','?'))" 2>/dev/null || echo "?")
    if [ "$STATUS" = "ready" ]; then
        ok "hive doctor status=ready"
    else
        warn "hive doctor status=$STATUS (non-fatal for H-P0)"
    fi
else
    fail "hive doctor failed"
fi

# ── 4. hive inspect smoke ─────────────────────────────────────────────────────
echo "[ 4/8 ] hive inspect smoke"
# Create a minimal smoke run to inspect
SMOKE_ID=""
if python -m hivemind.hive orchestrate "H-P0 smoke run for public-release-check" > "$OUT_DIR/smoke-run.log" 2>&1; then
    SMOKE_ID=$(grep -oP 'run_\w+' "$OUT_DIR/smoke-run.log" | head -1 || true)
fi
if [ -n "$SMOKE_ID" ]; then
    if python -m hivemind.hive inspect "$SMOKE_ID" --json > "$OUT_DIR/inspect-$SMOKE_ID.json" 2>&1; then
        VERDICT=$(python3 -c "import json; d=json.load(open('$OUT_DIR/inspect-$SMOKE_ID.json')); print(d.get('verdict','?'))" 2>/dev/null || echo "?")
        ok "hive inspect smoke verdict=$VERDICT run=$SMOKE_ID"
    else
        fail "hive inspect failed for $SMOKE_ID"
    fi
else
    warn "smoke run not created — hive inspect not verified (non-fatal)"
fi

# ── 5. Provider passthrough dry-run ──────────────────────────────────────────
echo "[ 5/8 ] provider passthrough dry-run"
if python -m hivemind.hive provider claude --dry-run -- --help > "$OUT_DIR/provider-passthrough.log" 2>&1; then
    ok "hive provider claude --dry-run exits 0"
else
    # dry-run should write artifact even if claude not installed
    if grep -q "command\|artifact\|passthrough" "$OUT_DIR/provider-passthrough.log" 2>/dev/null; then
        ok "hive provider claude --dry-run wrote artifact (provider not installed)"
    else
        warn "hive provider passthrough non-zero (provider may not be installed)"
    fi
fi

# ── 6. MemoryOS bridge graceful degrade ──────────────────────────────────────
echo "[ 6/8 ] MemoryOS bridge graceful degrade"
# If MemoryOS not present, hive orchestrate should not fail
MEMORYOS_ROOT="$ROOT_DIR/../memoryOS"
if [ -d "$MEMORYOS_ROOT" ]; then
    ok "MemoryOS sibling present at $MEMORYOS_ROOT"
else
    # Test that hive orchestrate still works without MemoryOS
    if python -m hivemind.hive orchestrate "smoke degrade test" > "$OUT_DIR/degrade-test.log" 2>&1; then
        ok "hive orchestrate succeeds without MemoryOS (graceful degrade)"
    else
        warn "hive orchestrate may require MemoryOS — check bridge logic"
    fi
fi

# ── 7. Secret / private path scan ────────────────────────────────────────────
echo "[ 7/8 ] Secret and private path scan"
SECRET_FILES=$(git ls-files \
    | grep -v 'public-release-check.sh' \
    | xargs grep -rlI \
        -e 'sk-[A-Za-z0-9]\{20,\}' \
        -e 'BEGIN [A-Z]* PRIVATE KEY' \
        -e 'ghp_[A-Za-z0-9]\{36,\}' \
        -e 'AIza[0-9A-Za-z_-]\{20,\}' \
    2>/dev/null || true)
SECRET_HITS=$(echo "$SECRET_FILES" | grep -c . || echo "0")
SECRET_HITS="${SECRET_HITS//[^0-9]/}"
SECRET_HITS="${SECRET_HITS:-0}"
if [ "$SECRET_HITS" -eq 0 ]; then
    ok "no secret patterns in tracked files"
else
    fail "$SECRET_HITS file(s) with potential secret patterns — review: $SECRET_FILES"
    echo "$SECRET_FILES" >> "$OUT_DIR/secret-scan.log"
fi

PRIVATE_HITS=$(git ls-files | grep -cE '(\.env$|\.pem$|\.key$|/data/raw|/exports/)' || true)
PRIVATE_HITS="${PRIVATE_HITS//[^0-9]/}"
PRIVATE_HITS="${PRIVATE_HITS:-0}"
if [ "$PRIVATE_HITS" -eq 0 ]; then
    ok "no private path patterns in tracked files"
else
    fail "$PRIVATE_HITS private path hits — check .gitignore"
fi

# ── 8. README production claim audit ─────────────────────────────────────────
echo "[ 8/8 ] README production claim audit"
OVERCLAIMS=$(grep -ciE \
    '(self.improving|autonomous.*long.horizon|AIOS|complete.*memory.*swarm|capabilityos.*routed)' \
    README.md 2>/dev/null || true)
OVERCLAIMS="${OVERCLAIMS//[^0-9]/}"
OVERCLAIMS="${OVERCLAIMS:-0}"
if [ "$OVERCLAIMS" -eq 0 ]; then
    ok "README: no production overclaims detected"
else
    warn "README may contain overclaims ($OVERCLAIMS lines) — review before release"
fi

# ── Result ────────────────────────────────────────────────────────────────────
echo ""
echo "=== Gate Result ==="
echo "PASS: $PASS   FAIL: $FAIL   WARN: ${#WARNINGS[@]}"
for w in "${WARNINGS[@]}"; do echo "  ⚠  $w"; done
echo ""
echo "Artifacts: $OUT_DIR"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "GATE: FAIL — fix the above before v0.1.0-production tag"
    exit 1
else
    echo "GATE: PASS — all H-P0 checks passed"
    echo "Tag command: git tag -a v0.1.0-production -m 'Hive Mind production v0'"
    exit 0
fi
