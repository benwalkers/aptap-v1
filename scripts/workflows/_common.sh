#!/usr/bin/env bash
# Shared helper: locate the project root even when invoked from another directory.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
VENV_PY="$ROOT/.venv/bin/python"
need_venv() {
  if [[ ! -x "$VENV_PY" ]]; then
    echo "ERROR: Missing .venv. Run: bash scripts/workflows/00_setup_venv.sh" >&2
    exit 2
  fi
}
heading() { printf '\n===== %s =====\n' "$*"; }
