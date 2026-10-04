#!/usr/bin/env bash
# Prepare a writable runtime for the existing Claude-compatible launch scripts.
# Codex's installed plugin tree may be read-only and copied virtualenv symlinks
# may not survive installation. PLUGIN_DATA is the plugin's writable directory.
set -euo pipefail

kind="${1:-}"
if [[ "$kind" != "review-generator" ]]; then
  echo "codex-start.sh: expected review-generator" >&2
  exit 2
fi

SOURCE_ROOT="${PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
if [[ -z "${PLUGIN_DATA:-}" ]]; then
  echo "codex-start.sh: PLUGIN_DATA is required for writable runtime files" >&2
  exit 1
fi

RUNTIME_ROOT="$PLUGIN_DATA/$kind"
mkdir -p "$RUNTIME_ROOT/scripts"

SOURCE_SERVER="$SOURCE_ROOT/mcp-server-review-generator"
RUNTIME_SERVER="$RUNTIME_ROOT/mcp-server-review-generator"
mkdir -p "$RUNTIME_SERVER"
cp "$SOURCE_SERVER/requirements.txt" "$SOURCE_SERVER/VERSION" "$RUNTIME_SERVER/"
cp -R "$SOURCE_SERVER/scripts" "$SOURCE_SERVER/config" "$RUNTIME_SERVER/"
cp "$SOURCE_ROOT/scripts/start-review-generator.sh" "$RUNTIME_ROOT/scripts/"
ln -sfn "$SOURCE_SERVER/resources" "$RUNTIME_SERVER/resources"
exec bash "$RUNTIME_ROOT/scripts/start-review-generator.sh"
