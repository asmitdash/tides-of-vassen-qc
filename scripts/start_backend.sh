#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && source .env && set +a
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8787 --reload
