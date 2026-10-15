#!/usr/bin/env bash
# Run the local, exploratory leave-one-description-out PR benchmark.
# Usage: bash scripts/workflows/14_evaluate_pr_curves.sh [--with-minilm]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "14 | Exploratory PR curves, per-category AP and top-1 F1"
if [[ "${1:-}" == "--with-minilm" ]]; then
  if [[ ! -f models/minilm/modules.json ]]; then
    echo "Model missing: run step 08 before --with-minilm" >&2
    exit 2
  fi
  HF_HUB_OFFLINE=1 "$VENV_PY" scripts/benchmark_pr_curves.py --with-minilm
elif [[ "$#" -eq 0 ]]; then
  "$VENV_PY" scripts/benchmark_pr_curves.py
else
  echo "Usage: $0 [--with-minilm]" >&2
  exit 2
fi
printf 'Results: outputs/pr_evaluation/\n'
