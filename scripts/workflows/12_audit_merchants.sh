#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "12 | Audit 92 merchant descriptors and produce read-only governance proposals"
"$VENV_PY" scripts/audit_merchant_registry.py
