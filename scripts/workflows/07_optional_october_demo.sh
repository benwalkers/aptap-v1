#!/usr/bin/env bash
# Runs in a separate demo workspace; does NOT modify data/ or the primary work/ state.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "07 | Optional isolated October schema + replay + invalid-record demo"
demo="work/demo_october"
mkdir -p "$demo/data" "$demo/outputs" "$demo/report"
cp data/transactions_2026_07.csv data/transactions_2026_08.csv \
   data/transactions_2026_09.jsonl data/merchant_labels.csv "$demo/data/"
"$VENV_PY" scripts/generate_october_fixture.py --output "$demo/data/transactions_2026_10.jsonl"
"$VENV_PY" -m pipeline "$demo/data" --engine lexical --as-of 2026-10-31 \
  --work-dir "$demo/state" --output-dir "$demo/outputs" \
  --report-path "$demo/report/one_page_report.html"
echo "Demo-only outputs in: $demo/outputs; primary outputs/ unaffected."
