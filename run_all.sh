#!/usr/bin/env bash
# Convenience entrypoint from VS Code project root.
set -euo pipefail
exec bash "$(cd "$(dirname "$0")" && pwd)/scripts/workflows/run_all.sh"
