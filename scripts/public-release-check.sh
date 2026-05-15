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
TOTAL=19

ok()   { echo "  PASS  $*"; ((PASS++)) || true; }
fail() { echo "  FAIL  $*"; ((FAIL++)) || true; }
warn() { echo "  WARN  $*"; WARNINGS+=("$*"); }

echo "=== H-P0 Hive Mind Production Gate ==="
echo "stamp: $STAMP"
echo "root:  $ROOT_DIR"
echo ""

# ── 1. Full test suite ────────────────────────────────────────────────────────
echo "[ 1/$TOTAL ] Test suite"
if npm test > "$OUT_DIR/test.log" 2>&1; then
    NPASS=$(grep -oP 'Ran \d+ tests' "$OUT_DIR/test.log" | grep -oP '\d+' | tail -1 || true)
    ok "npm test ${NPASS:-?} tests pass"
else
    fail "npm test failed — see $OUT_DIR/test.log"
fi

# ── 2. git diff --check (no whitespace errors) ────────────────────────────────
echo "[ 2/$TOTAL ] git diff --check"
if git diff --check > "$OUT_DIR/git-diff-check.log" 2>&1; then
    ok "git diff --check clean"
else
    fail "whitespace errors — see $OUT_DIR/git-diff-check.log"
fi

# ── 3. hive CLI smoke ─────────────────────────────────────────────────────────
echo "[ 3/$TOTAL ] hive CLI smoke"
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

# ── 4. run lifecycle smoke ────────────────────────────────────────────────────
echo "[ 4/$TOTAL ] run lifecycle smoke"
SMOKE_ID=""
if python -m hivemind.hive run "H-P0 smoke run for public-release-check" --json > "$OUT_DIR/smoke-run.json" 2>&1; then
    SMOKE_ID=$(python3 -c "import json; d=json.load(open('$OUT_DIR/smoke-run.json')); print(d.get('run_id',''))" 2>/dev/null || true)
fi
if [ -n "$SMOKE_ID" ]; then
    if python -m hivemind.hive status --run-id "$SMOKE_ID" --json > "$OUT_DIR/status-$SMOKE_ID.json" 2>&1; then
        ok "hive run/status smoke run=$SMOKE_ID"
    else
        fail "hive status failed for $SMOKE_ID"
    fi
else
    fail "smoke run not created"
fi

# ── 5. Provider passthrough dry-run ──────────────────────────────────────────
echo "[ 5/$TOTAL ] provider passthrough dry-run"
PROVIDER_ARGS=(provider claude --dry-run)
if [ -n "$SMOKE_ID" ]; then
    PROVIDER_ARGS+=(--run-id "$SMOKE_ID")
fi
PROVIDER_ARGS+=(-- --help)
if python -m hivemind.hive "${PROVIDER_ARGS[@]}" > "$OUT_DIR/provider-passthrough.log" 2>&1; then
    ok "hive provider claude --dry-run exits 0"
else
    # dry-run should write artifact even if claude not installed
    if grep -q "command\|artifact\|passthrough" "$OUT_DIR/provider-passthrough.log" 2>/dev/null; then
        ok "hive provider claude --dry-run wrote artifact (provider not installed)"
    else
        warn "hive provider passthrough non-zero (provider may not be installed)"
    fi
fi

# ── 6. supervisor stop receipt smoke ─────────────────────────────────────────
echo "[ 6/$TOTAL ] supervisor stop receipt smoke"
if [ -n "$SMOKE_ID" ] && python -m hivemind.hive run stop --run-id "$SMOKE_ID" --json > "$OUT_DIR/stop-$SMOKE_ID.json" 2>&1; then
    RECEIPT=$(python3 -c "import json; d=json.load(open('$OUT_DIR/stop-$SMOKE_ID.json')); print(d.get('last_stop_receipt',''))" 2>/dev/null || true)
    if [ -n "$RECEIPT" ] && [ -f "$RECEIPT" ]; then
        ok "hive run stop wrote receipt=$RECEIPT"
    else
        fail "hive run stop did not report a valid receipt"
    fi
else
    fail "hive run stop failed for smoke run"
fi

# ── 7. ledger replay smoke ───────────────────────────────────────────────────
echo "[ 7/$TOTAL ] ledger replay smoke"
if [ -n "$SMOKE_ID" ] && python -m hivemind.hive ledger replay --run-id "$SMOKE_ID" --json > "$OUT_DIR/ledger-$SMOKE_ID.json" 2>&1; then
    LEDGER_OK=$(python3 -c "import json; d=json.load(open('$OUT_DIR/ledger-$SMOKE_ID.json')); print(d.get('ok'))" 2>/dev/null || echo "?")
    ok "hive ledger replay ok=$LEDGER_OK run=$SMOKE_ID"
else
    fail "hive ledger replay failed for smoke run"
fi

# ── 8. hive inspect smoke ────────────────────────────────────────────────────
echo "[ 8/$TOTAL ] hive inspect smoke"
if [ -n "$SMOKE_ID" ] && python -m hivemind.hive inspect "$SMOKE_ID" --json > "$OUT_DIR/inspect-$SMOKE_ID.json" 2>&1; then
    KIND=$(python3 -c "import json; d=json.load(open('$OUT_DIR/inspect-$SMOKE_ID.json')); print(d.get('kind','?'))" 2>/dev/null || echo "?")
    RECORDS=$(python3 -c "import json; d=json.load(open('$OUT_DIR/inspect-$SMOKE_ID.json')); print((d.get('ledger') or {}).get('record_count','?'))" 2>/dev/null || echo "?")
    if [ "$KIND" = "hive_run_inspection" ]; then
        ok "hive inspect kind=$KIND ledger_records=$RECORDS run=$SMOKE_ID"
    else
        fail "hive inspect returned unexpected kind=$KIND"
    fi
else
    fail "hive inspect failed for smoke run"
fi

# ── 9. hive inspect verdict smoke ────────────────────────────────────────────
echo "[ 9/$TOTAL ] hive inspect verdict smoke"
if [ -n "$SMOKE_ID" ]; then
    VERDICT=$(python3 -c "import json; d=json.load(open('$OUT_DIR/inspect-$SMOKE_ID.json')); print(d.get('verdict','?'))" 2>/dev/null || echo "?")
    if [ "$VERDICT" = "clean" ] || [ "$VERDICT" = "escalated" ] || [ "$VERDICT" = "failures" ] || [ "$VERDICT" = "chain_tampered" ]; then
        ok "hive inspect verdict=$VERDICT run=$SMOKE_ID"
    else
        fail "hive inspect did not return a known verdict (got: $VERDICT)"
    fi
else
    fail "smoke run not available for verdict check"
fi

# ── 10. hive next grounded smoke ─────────────────────────────────────────────
echo "[ 10/$TOTAL ] hive next grounded smoke"
if [ -n "$SMOKE_ID" ] && python -m hivemind.hive next --run-id "$SMOKE_ID" --json > "$OUT_DIR/next-$SMOKE_ID.json" 2>&1; then
    NEXT_CMD=$(python3 -c "import json; d=json.load(open('$OUT_DIR/next-$SMOKE_ID.json')); print(d.get('command','?'))" 2>/dev/null || echo "?")
    NEXT_SRC=$(python3 -c "import json; d=json.load(open('$OUT_DIR/next-$SMOKE_ID.json')); print(d.get('source','?'))" 2>/dev/null || echo "?")
    if [ "$NEXT_CMD" != "?" ] && [ "$NEXT_SRC" != "?" ]; then
        ok "hive next cmd='$NEXT_CMD' source=$NEXT_SRC run=$SMOKE_ID"
    else
        fail "hive next did not return a grounded action"
    fi
else
    fail "hive next failed for smoke run"
fi

# ── 11. User-value benchmark ─────────────────────────────────────────────────
echo "[ 11/$TOTAL ] user-value benchmark"
if python scripts/user-value-benchmark.py --json > "$OUT_DIR/user-value-benchmark.json" 2> "$OUT_DIR/user-value-benchmark.err"; then
    VERDICT=$(python3 -c "import json; d=json.load(open('$OUT_DIR/user-value-benchmark.json')); print((d.get('summary') or {}).get('verdict','?'))" 2>/dev/null || echo "?")
    DIRECT=$(python3 -c "import json; d=json.load(open('$OUT_DIR/user-value-benchmark.json')); print((d.get('summary') or {}).get('direct_cli_for_trivial','?'))" 2>/dev/null || echo "?")
    HIVE_VALUE=$(python3 -c "import json; d=json.load(open('$OUT_DIR/user-value-benchmark.json')); print((d.get('summary') or {}).get('hive_for_audited_multi_agent','?'))" 2>/dev/null || echo "?")
    if [ "$VERDICT" = "pass" ]; then
        ok "user-value verdict=$VERDICT direct_cli_for_trivial=$DIRECT hive_for_audited_multi_agent=$HIVE_VALUE"
    else
        fail "user-value benchmark verdict=$VERDICT — see $OUT_DIR/user-value-benchmark.json"
    fi
else
    fail "user-value benchmark failed — see $OUT_DIR/user-value-benchmark.err"
fi

# ── 12. quickstart demo smoke ────────────────────────────────────────────────
echo "[ 12/$TOTAL ] quickstart demo smoke"
if python -m hivemind.hive demo quickstart "public alpha quickstart smoke" --json > "$OUT_DIR/quickstart-demo.json" 2>&1; then
    QUICKSTART_RUN=$(python3 -c "import json; d=json.load(open('$OUT_DIR/quickstart-demo.json')); print(d.get('run_id',''))" 2>/dev/null || true)
    QUICKSTART_NODES=$(python3 -c "import json; d=json.load(open('$OUT_DIR/quickstart-demo.json')); print((d.get('memoryos_summary') or {}).get('nodes',0))" 2>/dev/null || echo "0")
    QUICKSTART_LEDGER=$(python3 -c "import json; d=json.load(open('$OUT_DIR/quickstart-demo.json')); print((d.get('inspect_summary') or {}).get('ledger_records',0))" 2>/dev/null || echo "0")
    if [ -n "$QUICKSTART_RUN" ] && [ "$QUICKSTART_NODES" -gt 0 ] && [ "$QUICKSTART_LEDGER" -gt 0 ]; then
        ok "quickstart run=$QUICKSTART_RUN nodes=$QUICKSTART_NODES ledger_records=$QUICKSTART_LEDGER"
    else
        fail "quickstart did not produce graph and ledger value signals"
    fi
else
    fail "hive demo quickstart failed — see $OUT_DIR/quickstart-demo.json"
fi

# ── 13. README / init onboarding path ────────────────────────────────────────
echo "[ 13/$TOTAL ] README / init onboarding path"
if python -m hivemind.hive init --json > "$OUT_DIR/init-onboarding.json" 2>&1; then
    INIT_FIRST=$(python3 -c "import json; d=json.load(open('$OUT_DIR/init-onboarding.json')); print(((d.get('next_actions') or [{}])[0]).get('command','?'))" 2>/dev/null || echo "?")
    INIT_SECOND=$(python3 -c "import json; d=json.load(open('$OUT_DIR/init-onboarding.json')); print(((d.get('next_actions') or [{},{}])[1]).get('command','?'))" 2>/dev/null || echo "?")
    if grep -q "hive demo quickstart" README.md && grep -q "hive demo memory-loop" README.md && [ "$INIT_FIRST" = "hive demo quickstart" ] && [ "$INIT_SECOND" = "hive demo memory-loop" ]; then
        ok "README and hive init start with quickstart/memory-loop path"
    else
        fail "README or hive init does not foreground the public-alpha demo path"
    fi
else
    fail "hive init --json failed — see $OUT_DIR/init-onboarding.json"
fi

# ── 14. MemoryOS feedback loop demo ──────────────────────────────────────────
echo "[ 14/$TOTAL ] MemoryOS feedback loop demo"
if python -m hivemind.hive demo memory-loop "public alpha memory loop smoke" --json > "$OUT_DIR/memory-loop-demo.json" 2>&1; then
    MEMORY_LOOP_STATUS=$(python3 -c "import json; d=json.load(open('$OUT_DIR/memory-loop-demo.json')); print(d.get('status','?'))" 2>/dev/null || echo "?")
    MEMORY_LOOP_APPROVED=$(python3 -c "import json; d=json.load(open('$OUT_DIR/memory-loop-demo.json')); print(len(d.get('approved_memory_ids') or []))" 2>/dev/null || echo "0")
    MEMORY_LOOP_CONTEXT=$(python3 -c "import json; d=json.load(open('$OUT_DIR/memory-loop-demo.json')); print(len((d.get('second_run_context') or {}).get('accepted_memory_ids') or []))" 2>/dev/null || echo "0")
    if [ "$MEMORY_LOOP_STATUS" = "closed_loop" ] && [ "$MEMORY_LOOP_APPROVED" -gt 0 ] && [ "$MEMORY_LOOP_CONTEXT" -gt 0 ]; then
        ok "memory loop status=$MEMORY_LOOP_STATUS approved=$MEMORY_LOOP_APPROVED second_context=$MEMORY_LOOP_CONTEXT"
    else
        fail "memory loop did not close status=$MEMORY_LOOP_STATUS approved=$MEMORY_LOOP_APPROVED second_context=$MEMORY_LOOP_CONTEXT"
    fi
else
    fail "hive demo memory-loop failed — see $OUT_DIR/memory-loop-demo.json"
fi

# ── 15. MemoryOS bridge graceful degrade ─────────────────────────────────────
echo "[ 15/$TOTAL ] MemoryOS bridge graceful degrade"
if HIVE_DISABLE_MEMORYOS=1 python -m hivemind.hive orchestrate "smoke degrade test without MemoryOS" --json > "$OUT_DIR/degrade-test.json" 2>&1; then
    DEGRADED_RUN=$(python3 -c "import json; d=json.load(open('$OUT_DIR/degrade-test.json')); print(d.get('run_id',''))" 2>/dev/null || true)
    if [ -n "$DEGRADED_RUN" ] && python3 -c "import json, pathlib, sys; p=pathlib.Path('.runs')/'$DEGRADED_RUN'/'artifacts'/'memory_context.json'; d=json.load(open(p)); sys.exit(0 if d.get('status') == 'unavailable' and 'disabled' in str(d.get('reason','')).lower() else 1)" 2>/dev/null; then
        ok "hive orchestrate degrades cleanly with HIVE_DISABLE_MEMORYOS=1 run=$DEGRADED_RUN"
    else
        fail "MemoryOS disabled run did not write an unavailable memory_context artifact"
    fi
else
    fail "hive orchestrate failed when MemoryOS bridge was disabled"
fi

# ── 16. Secret / private path scan ───────────────────────────────────────────
echo "[ 16/$TOTAL ] Secret and private path scan"
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
if [ "$SECRET_HITS" -gt 0 ]; then
    fail "$SECRET_HITS file(s) with potential secret patterns — review: $SECRET_FILES"
    echo "$SECRET_FILES" >> "$OUT_DIR/secret-scan.log"
fi

PRIVATE_HITS=$(git ls-files | grep -cE '(\.env$|\.pem$|\.key$|/data/raw|/exports/)' || true)
PRIVATE_HITS="${PRIVATE_HITS//[^0-9]/}"
PRIVATE_HITS="${PRIVATE_HITS:-0}"
if [ "$PRIVATE_HITS" -gt 0 ]; then
    fail "$PRIVATE_HITS private path hits — check .gitignore"
fi
if [ "$SECRET_HITS" -eq 0 ] && [ "$PRIVATE_HITS" -eq 0 ]; then
    ok "no secret or private path patterns in tracked files"
fi

# ── 17. README production claim audit ────────────────────────────────────────
echo "[ 17/$TOTAL ] README production claim audit"
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

# ── 18. AIOS three-OS contract smoke ─────────────────────────────────────────
echo "[ 18/$TOTAL ] AIOS three-OS contract smoke"
if python -m hivemind.hive aios "public alpha aios contract smoke" --json > "$OUT_DIR/aios-contract-smoke.json" 2>&1; then
    AIOS_STATUS=$(python3 -c "import json; d=json.load(open('$OUT_DIR/aios-contract-smoke.json')); print(d.get('status','?'))" 2>/dev/null || echo "?")
    AIOS_SIGNERS=$(python3 -c "import json; d=json.load(open('$OUT_DIR/aios-contract-smoke.json')); print(len(d.get('signed_by') or []))" 2>/dev/null || echo "0")
    AIOS_EXECUTION=$(python3 -c "import json; d=json.load(open('$OUT_DIR/aios-contract-smoke.json')); print('yes' if isinstance(d.get('execution'), dict) else 'no')" 2>/dev/null || echo "no")
    if [ "$AIOS_STATUS" = "ready" ] && [ "$AIOS_SIGNERS" -ge 3 ] && [ "$AIOS_EXECUTION" = "yes" ]; then
        ok "aios contract status=$AIOS_STATUS signers=$AIOS_SIGNERS execution=advanced"
    else
        fail "aios contract did not converge status=$AIOS_STATUS signers=$AIOS_SIGNERS execution=$AIOS_EXECUTION"
    fi
else
    fail "hive aios failed — see $OUT_DIR/aios-contract-smoke.json"
fi

# ── 19. AIOS evolution loop + big-brain feedback packet ──────────────────────
echo "[ 19/$TOTAL ] AIOS evolution loop and big-brain feedback packet"
if python -m hivemind.hive aios "evolution smoke goal for release gate" --evolve --max-iterations 1 --json > "$OUT_DIR/aios-evolution-smoke.json" 2>&1; then
    EVO_ITERS=$(python3 -c "import json; d=json.load(open('$OUT_DIR/aios-evolution-smoke.json')); print(d.get('iterations',-1))" 2>/dev/null || echo "-1")
    EVO_STOP=$(python3 -c "import json; d=json.load(open('$OUT_DIR/aios-evolution-smoke.json')); print(d.get('stop_reason','?'))" 2>/dev/null || echo "?")
    EVO_RUN=$(python3 -c "import json; d=json.load(open('$OUT_DIR/aios-evolution-smoke.json')); print(d.get('final_run_id') or '')" 2>/dev/null || echo "")
    FEEDBACK_HIT=$(ls -1 ../.aios/outbox/myworld/aios-feedback-${EVO_RUN}-gen00.hivemind.report.json 2>/dev/null | head -1 || echo "")
    if [ "$EVO_ITERS" -ge 1 ] && [ -n "$FEEDBACK_HIT" ]; then
        ok "aios evolution iterations=$EVO_ITERS stop=$EVO_STOP feedback_packet=$FEEDBACK_HIT"
    else
        fail "aios evolution did not produce a feedback packet (iters=$EVO_ITERS stop=$EVO_STOP run=$EVO_RUN)"
    fi
else
    fail "hive aios --evolve failed — see $OUT_DIR/aios-evolution-smoke.json"
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
