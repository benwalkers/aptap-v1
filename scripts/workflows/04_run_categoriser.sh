#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
engine="${1:-lexical}"
heading "04 | Standalone merchant categoriser (input + category output + reviews)"
"$VENV_PY" -m categorise examples.csv outputs/examples_categorised.csv \
  --engine "$engine" --review-output outputs/examples_review.csv
