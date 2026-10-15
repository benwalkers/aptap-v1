#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
as_of="${1:-auto}"
engine="${2:-lexical}"
heading "03 | Incremental ingest -> canonical Silver -> classification -> bills/switches -> report"
if [[ "$as_of" == "auto" ]]; then
  "$VENV_PY" -m pipeline data/ --engine "$engine"
else
  "$VENV_PY" -m pipeline data/ --engine "$engine" --as-of "$as_of"
fi
