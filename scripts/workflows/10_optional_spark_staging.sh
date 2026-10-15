#!/usr/bin/env bash
# Staging demonstration only; Spark/Iceberg MERGE requires a separate approved runtime.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "10 | OPTIONAL generate line-numbered Bronze staging files for Spark"
mkdir -p work/spark_stage
for input in data/transactions_*.csv data/transactions_*.jsonl; do
  [[ -f "$input" ]] || continue
  name="$(basename "$input")"
  "$VENV_PY" scripts/make_bronze_stage.py "$input" "work/spark_stage/${name}.staged.jsonl"
done
printf '\nStaging ready in work/spark_stage/. The Spark/Iceberg job is a reference and is not executed by this script.\n'
