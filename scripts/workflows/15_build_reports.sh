#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "15 | Offline commercial and inference-risk reports (read-only)"
if [[ "${1:-}" == "--with-minilm" || "${DASHBOARD_MINILM:-0}" == "1" ]]; then
  HF_HUB_OFFLINE=1 "$VENV_PY" scripts/build_risk_dashboard.py --with-minilm
else
  "$VENV_PY" scripts/build_risk_dashboard.py
fi
printf 'One-page commercial report: report/one_page_report.html\n'
printf 'Interactive dashboard: report/risk_dashboard.html\n'
