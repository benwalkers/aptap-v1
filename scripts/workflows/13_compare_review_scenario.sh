#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "13 | Compare current demo registry with conservative proposal without changing SQLite"
"$VENV_PY" scripts/compare_merchant_scenarios.py
