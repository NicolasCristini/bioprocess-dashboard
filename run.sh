#!/usr/bin/env bash
# Serve the in-browser app on localhost only (strict CSP) and open it. Usage: ./run.sh [page], e.g. ./run.sh spike/
set -euo pipefail
cd "$(dirname "$0")"
[ -f web/vendor/pyodide/pyodide.mjs ] || python3 scripts/vendor_runtime.py
PORT="${PORT:-8765}"
(sleep 1 && open "http://localhost:$PORT/${1:-}") &
exec python3 scripts/serve.py "$PORT"
