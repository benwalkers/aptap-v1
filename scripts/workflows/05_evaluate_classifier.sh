#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "05 | Exploratory leave-one-description-out classifier benchmark"
if [[ "${1:-}" == "--with-minilm" ]]; then
  HF_HUB_OFFLINE=1 "$VENV_PY" scripts/benchmark_classifiers.py --with-minilm
else
  "$VENV_PY" scripts/benchmark_classifiers.py
fi
printf '\nBenchmark: outputs/classifier_benchmark.json\n'
