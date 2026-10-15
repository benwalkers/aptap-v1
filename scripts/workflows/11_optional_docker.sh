#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/_common.sh"
heading "11 | OPTIONAL offline Docker execution of local Python pipeline"
command -v docker >/dev/null || { echo 'Docker CLI not installed.' >&2; exit 2; }
mkdir -p work outputs report
as_of="${1:-auto}"
docker build -f infrastructure/docker/Dockerfile -t aptap-incremental:release2 .
args=(data/ --engine lexical)
if [[ "$as_of" != "auto" ]]; then args+=(--as-of "$as_of"); fi
docker run --rm --network none \
  -v "$ROOT/data:/app/data:ro" \
  -v "$ROOT/work:/app/work" \
  -v "$ROOT/outputs:/app/outputs" \
  -v "$ROOT/report:/app/report" \
  aptap-incremental:release2 "${args[@]}"
