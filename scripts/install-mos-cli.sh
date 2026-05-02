#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python}"

"$PYTHON" -m pip install --user -e .

USER_BASE="$("$PYTHON" -m site --user-base)"
BIN_DIR="$USER_BASE/bin"

echo "Installed MemoryOS CLI."
echo "mos: $BIN_DIR/mos"
echo "memoryos: $BIN_DIR/memoryos"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo ""
    echo "Add this to your shell profile if mos is not found:"
    echo "  export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac

echo ""
"$BIN_DIR/mos" --version
"$BIN_DIR/mos" doctor
