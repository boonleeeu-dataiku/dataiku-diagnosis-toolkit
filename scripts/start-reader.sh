#!/usr/bin/env bash
# Lazy-bootstraps mcp-server-diagnosis-reader/ (npm install + build) on first
# run, then execs the built server. See README's "One-time setup" for the
# manual equivalent of what this automates.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/../mcp-server-diagnosis-reader"
cd "$SERVER_DIR"

# A GUI-launched Claude app doesn't inherit your shell's PATH, so `node`/`npm`
# may not resolve without help.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

STAMP="dist/.build-stamp"
LOCK_HASH="$(shasum package-lock.json | cut -d' ' -f1)"

if [[ ! -f dist/index.js || "$(cat "$STAMP" 2>/dev/null || true)" != "$LOCK_HASH" ]]; then
  if ! command -v npm >/dev/null 2>&1; then
    echo "start-reader.sh: npm not found on PATH; install Node.js >= 18.17" >&2
    exit 1
  fi
  {
    npm install
    npm run build
    echo "$LOCK_HASH" > "$STAMP"
  } 1>&2 # MCP talks JSON-RPC over stdout; build output must not land there
fi

exec node dist/index.js
