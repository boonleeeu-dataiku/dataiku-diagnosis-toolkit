#!/usr/bin/env bash
# Lazy-bootstraps mcp-server-review-generator/ (venv + pip install) on first
# run, then execs the server. See README's "One-time setup" for the manual
# equivalent of what this automates.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/../mcp-server-review-generator"
cd "$SERVER_DIR"

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

STAMP=".venv/.build-stamp"
REQ_HASH="$(shasum requirements.txt | cut -d' ' -f1)"

if [[ ! -x .venv/bin/python3 || "$(cat "$STAMP" 2>/dev/null || true)" != "$REQ_HASH" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "start-review-generator.sh: python3 not found on PATH" >&2
    exit 1
  fi
  {
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
    echo "$REQ_HASH" > "$STAMP"
  } 1>&2 # MCP talks JSON-RPC over stdout; build output must not land there
fi

exec .venv/bin/python3 scripts/mcp_server.py
