#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "02 | Full local regression suite (ingestion, CDC, governance, packaging)"
if ! "$VENV_PY" -c 'import pytest' 2>/dev/null; then
  echo "pytest not installed in .venv. Run step 00 without --offline (or install approved pytest wheels)." >&2
  exit 2
fi
"$VENV_PY" -m pytest -q tests/
