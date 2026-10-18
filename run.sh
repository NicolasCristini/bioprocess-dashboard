#!/usr/bin/env bash
# Build the static site and preview it locally. Usage: ./run.sh [--base /repo-name/]
set -euo pipefail
cd "$(dirname "$0")"
[ -f web/vendor/pyodide/pyodide.mjs ] || python3 scripts/vendor_runtime.py
BASE="/"
if [ "${1:-}" = "--base" ]; then BASE="$2"; fi
python3 scripts/build_site.py --base "$BASE"
PORT="${PORT:-8765}"
(sleep 1 && open "http://localhost:$PORT$BASE") &
exec python3 scripts/serve.py "$PORT" --base "$BASE"
