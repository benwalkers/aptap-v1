#!/usr/bin/env bash
# Usage: bash scripts/workflows/00_setup_venv.sh [--offline]
# --offline skips local test and PR-evaluation dependency installation. Core pipeline needs no external packages.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
heading "00 | Create or reuse .venv"
python_bin="${PYTHON_BIN:-python3}"
if [[ ! -x "$VENV_PY" ]]; then
  command -v "$python_bin" >/dev/null || { echo "Python interpreter not found: $python_bin" >&2; exit 2; }
  "$python_bin" - <<'PY'
import sys
assert sys.version_info >= (3,11), 'Python 3.11+ is required.'
print('Python', sys.version.split()[0])
PY
  "$python_bin" -m venv .venv
fi
"$VENV_PY" --version
if [[ "${1:-}" != "--offline" ]]; then
  heading "Install local test + PR evaluation dependencies"
  "$VENV_PY" -m pip install -r requirements.txt
else
  echo "Offline setup: dependencies not installed; use an approved local wheelhouse for tests and PR evaluation."
fi
cat <<'MSG'
Environment ready. In this Terminal, optional activation:
  source .venv/bin/activate
Or run the numbered scripts, which always use .venv/bin/python directly.
No MiniLM weights and no Spark packages are installed by this step.
MSG
