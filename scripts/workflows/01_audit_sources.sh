#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "01 | Read-only EDA: date formats, source periods and SHA-256"
"$VENV_PY" scripts/inspect_inputs.py --data-dir data --output outputs/source_eda.json
