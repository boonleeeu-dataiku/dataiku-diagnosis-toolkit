#!/usr/bin/env bash
# Lazy-bootstraps mcp-server-review-generator/ (venv + pip install) on first
# run, then execs the server. See README's "One-time setup" for the manual
# equivalent of what this automates.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/../mcp-server-review-generator"
cd "$SERVER_DIR"

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# mcp>=2 needs Python >=3.10; the system python3 may be older, so pick a suitable one.
PY=""
for cand in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$cand" >/dev/null 2>&1 \
     && "$cand" -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null; then
    PY="$cand"
    break
  fi
done

STAMP=".venv/.build-stamp"
REQ_HASH="$(shasum requirements.txt | cut -d' ' -f1)"

venv_ok() {
  [[ -x .venv/bin/python3 ]] && .venv/bin/python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))' 2>/dev/null
}

if ! venv_ok || [[ "$(cat "$STAMP" 2>/dev/null || true)" != "$REQ_HASH" ]]; then
  if [[ -z "$PY" ]]; then
    echo "start-review-generator.sh: Python >=3.10 required but not found on PATH (python3 is: $(python3 --version 2>&1 || echo missing))" >&2
    exit 1
  fi
  {
    rm -rf .venv
    "$PY" -m venv .venv
    .venv/bin/pip install -r requirements.txt
    echo "$REQ_HASH" > "$STAMP"
  } 1>&2 # MCP talks JSON-RPC over stdout; build output must not land there
fi

exec .venv/bin/python3 scripts/mcp_server.py
