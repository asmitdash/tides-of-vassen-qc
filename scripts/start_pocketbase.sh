#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
./pocketbase.exe serve --http=127.0.0.1:8090 "$@"
