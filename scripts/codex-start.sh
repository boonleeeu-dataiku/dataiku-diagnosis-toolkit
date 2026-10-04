#!/usr/bin/env bash
# Prepare a writable runtime for the existing Claude-compatible launch scripts.
# Codex's installed plugin tree may be read-only and copied virtualenv symlinks
# may not survive installation. PLUGIN_DATA is the plugin's writable directory.
set -euo pipefail

kind="${1:-}"
if [[ "$kind" != "reader" && "$kind" != "review-generator" ]]; then
  echo "codex-start.sh: expected reader or review-generator" >&2
  exit 2
fi

SOURCE_ROOT="${PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
if [[ -z "${PLUGIN_DATA:-}" ]]; then
  echo "codex-start.sh: PLUGIN_DATA is required for writable runtime files" >&2
  exit 1
fi

RUNTIME_ROOT="$PLUGIN_DATA/$kind"
mkdir -p "$RUNTIME_ROOT/scripts"

if [[ "$kind" == "reader" ]]; then
  SOURCE_SERVER="$SOURCE_ROOT/mcp-server-diagnosis-reader"
  RUNTIME_SERVER="$RUNTIME_ROOT/mcp-server-diagnosis-reader"
  mkdir -p "$RUNTIME_SERVER"
  cp "$SOURCE_SERVER/package.json" "$SOURCE_SERVER/package-lock.json" "$SOURCE_SERVER/tsconfig.json" "$RUNTIME_SERVER/"
  # Replace the source tree so files removed upstream cannot linger in a cached runtime.
  rm -rf -- "$RUNTIME_SERVER/src"
  cp -R "$SOURCE_SERVER/src" "$RUNTIME_SERVER/"
  cp "$SOURCE_ROOT/scripts/start-reader.sh" "$RUNTIME_ROOT/scripts/"

  # The original launcher stamps only the dependency lockfile. Invalidate that
  # stamp when TypeScript source or compiler configuration changes as well.
  SOURCE_HASH="$(find "$SOURCE_SERVER/src" -type f -exec shasum -a 256 {} + | shasum -a 256 | cut -d' ' -f1)"
  SOURCE_HASH="$(printf '%s\n' "$SOURCE_HASH" "$(shasum -a 256 "$SOURCE_SERVER/tsconfig.json" | cut -d' ' -f1)" | shasum -a 256 | cut -d' ' -f1)"
  if [[ "$(cat "$RUNTIME_SERVER/.codex-source-stamp" 2>/dev/null || true)" != "$SOURCE_HASH" ]]; then
    mkdir -p "$RUNTIME_SERVER/dist"
    : > "$RUNTIME_SERVER/dist/.build-stamp"
    printf '%s\n' "$SOURCE_HASH" > "$RUNTIME_SERVER/.codex-source-stamp"
  fi
  export DATAIKU_SKILL_DIR="$SOURCE_ROOT/skills/dataiku-diagnosis-reader"
  exec bash "$RUNTIME_ROOT/scripts/start-reader.sh"
fi

SOURCE_SERVER="$SOURCE_ROOT/mcp-server-review-generator"
RUNTIME_SERVER="$RUNTIME_ROOT/mcp-server-review-generator"
mkdir -p "$RUNTIME_SERVER"
cp "$SOURCE_SERVER/requirements.txt" "$SOURCE_SERVER/VERSION" "$RUNTIME_SERVER/"
cp -R "$SOURCE_SERVER/scripts" "$SOURCE_SERVER/config" "$RUNTIME_SERVER/"
cp "$SOURCE_ROOT/scripts/start-review-generator.sh" "$RUNTIME_ROOT/scripts/"
ln -sfn "$SOURCE_SERVER/resources" "$RUNTIME_SERVER/resources"
exec bash "$RUNTIME_ROOT/scripts/start-review-generator.sh"
