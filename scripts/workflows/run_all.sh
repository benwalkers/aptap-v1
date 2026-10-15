#!/usr/bin/env bash
# Default safe workflow (no downloads, resets or October data mutation).
# Prerequisite: bash scripts/workflows/00_setup_venv.sh
# Optional: AS_OF=2026-10-31 ENGINE=lexical bash scripts/workflows/run_all.sh
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
as_of="${AS_OF:-auto}"
engine="${ENGINE:-lexical}"
heading "ApTap Release 2 | end-to-end from clean inputs"
bash scripts/workflows/01_audit_sources.sh
bash scripts/workflows/03_run_incremental.sh "$as_of" "$engine"
bash scripts/workflows/04_run_categoriser.sh "$engine"
bash scripts/workflows/05_evaluate_classifier.sh
bash scripts/workflows/12_audit_merchants.sh
bash scripts/workflows/13_compare_review_scenario.sh
bash scripts/workflows/14_evaluate_pr_curves.sh
bash scripts/workflows/15_build_reports.sh
bash scripts/workflows/02_run_tests.sh
bash scripts/workflows/06_verify_rerun.sh "$as_of" "$engine"
printf '\nSUCCESS. Required CSVs are in outputs/; commercial + offline dashboard in report/.\n'
