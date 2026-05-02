#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python}"

"$PYTHON" -m pip install --user -e .

USER_BASE="$("$PYTHON" -m site --user-base)"
BIN_DIR="$USER_BASE/bin"

echo "Installed Hive Mind CLI."
echo "hive: $BIN_DIR/hive"
echo "hivemind: $BIN_DIR/hivemind"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo ""
    echo "Add this to your shell profile if hive is not found:"
    echo "  export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac

echo ""
"$BIN_DIR/hive" --version
"$BIN_DIR/hive" doctor
