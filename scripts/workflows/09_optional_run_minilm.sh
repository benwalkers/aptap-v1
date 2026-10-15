#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
as_of="${1:-auto}"
if [[ ! -e models/minilm/modules.json ]]; then
  echo 'Missing models/minilm/modules.json. First run step 08 online or provision an approved offline model directory.' >&2
  exit 2
fi
heading "09 | OPTIONAL offline MiniLM inference and benchmark"
if [[ "$as_of" == "auto" ]]; then
  HF_HUB_OFFLINE=1 "$VENV_PY" -m pipeline data/ --engine minilm
else
  HF_HUB_OFFLINE=1 "$VENV_PY" -m pipeline data/ --engine minilm --as-of "$as_of"
fi
HF_HUB_OFFLINE=1 "$VENV_PY" -m categorise examples.csv outputs/examples_minilm.csv \
  --engine minilm --review-output outputs/examples_minilm_review.csv
HF_HUB_OFFLINE=1 "$VENV_PY" scripts/benchmark_classifiers.py --with-minilm
