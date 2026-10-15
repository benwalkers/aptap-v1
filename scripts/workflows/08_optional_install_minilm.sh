#!/usr/bin/env bash
# ONLINE PROVISIONING ONLY. Requires bank-approved dependencies and model source.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
need_venv
heading "08 | OPTIONAL online provisioning: install MiniLM dependencies and download weights"
"$VENV_PY" -m pip install -r requirements-minilm.txt
"$VENV_PY" scripts/download_model.py --destination models/minilm
printf '\nModel stored locally in models/minilm. Future inference can run without network.\n'
