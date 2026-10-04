#!/usr/bin/env bash
# Regenerate the plugin-eval mock input derived from the real MCP server:
#   evals/mocks/dataiku-review-generator/_tools.json   the server's real tools/list response
# Run after changing a tool's signature. Needs the .venv (see README's One-time setup).
set -euo pipefail
cd "$(dirname "$0")/.."

mcp-server-review-generator/.venv/bin/python - <<'EOF'
import json, os, subprocess

def tools_list(cmd):
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    def send(obj):
        p.stdin.write(json.dumps(obj) + "\n"); p.stdin.flush()
    def recv(i):
        while True:
            m = json.loads(p.stdout.readline())
            if m.get("id") == i:
                return m
    send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "refresh", "version": "0"}}})
    recv(1)
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    result = recv(2)["result"]
    p.kill()
    return result

cmd = ["mcp-server-review-generator/.venv/bin/python", "mcp-server-review-generator/scripts/mcp_server.py"]
path = "evals/mocks/dataiku-review-generator/_tools.json"
with open(path, "w") as f:
    f.write(json.dumps(tools_list(cmd), indent=2) + "\n")
print(f"wrote {path}")
EOF
