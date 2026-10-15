#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
as_of="${1:-auto}"
engine="${2:-lexical}"
heading "06 | Verify rerun idempotency, checkpoint and 4 required CSV hashes"
if [[ "$as_of" == "auto" ]]; then
  "$VENV_PY" scripts/verify_rerun.py --engine "$engine"
else
  "$VENV_PY" scripts/verify_rerun.py --as-of "$as_of" --engine "$engine"
fi
