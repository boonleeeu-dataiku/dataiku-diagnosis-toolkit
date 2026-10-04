#!/usr/bin/env python3
"""Secret-safe structural view of a JSON file from a Dataiku diagnosis bundle.

Usage: peek.py <file.json> [--path a.b.c] [--depth N]

Prints one line per node: the dotted path, the type, and (for scalars) the value.
Values whose key looks sensitive (password, secret, token, key, credential, ...) are
shown as <redacted>, as are strings that embed credentials (password=..., user:pass@host).
Long strings are truncated. Read-only; no network calls; Python 3 stdlib only.

--path walks into the file first (dict keys, or list indexes as integers). Connection
and user names can contain dots, so quote the path in the shell and, if a key itself
contains a dot, pass it with --path-sep to use another separator.
--depth caps how deep to descend below the starting point (default 3).
Redaction is by key name and value shape, so it is a guardrail, not a guarantee:
still never `cat` or `jq .` the files named in SKILL.md "Handling secrets".
"""
import argparse
import json
import re
import sys

SENSITIVE_KEY = re.compile(
    r"pass|pwd|secret|token|(?<![a-z])key(?!s)|[a-z]Key(?!s)|credential|auth|cert|private|signature|bind|salt|hash",
    re.IGNORECASE,
)
# Posture fields that name a mode, not a secret, and would otherwise match above.
SAFE_KEYS = {"credentialsMode", "authType", "authMode"}
EMBEDDED_SECRET = re.compile(
    r"(password|passwd|pwd|secret|token|apikey|api_key)\s*[=:]|://[^/\s:@]+:[^/\s@]+@",
    re.IGNORECASE,
)
MAX_STR = 80
MAX_ITEMS = 40


def describe_scalar(key, value):
    if key is not None and str(key) not in SAFE_KEYS and SENSITIVE_KEY.search(str(key)):
        return "<redacted>"
    if isinstance(value, str):
        if EMBEDDED_SECRET.search(value):
            return "<redacted: embeds credential>"
        shown = value if len(value) <= MAX_STR else value[:MAX_STR] + f"... ({len(value)} chars)"
        return json.dumps(shown)
    return json.dumps(value)


def walk(node, path, key, depth, out):
    label = path or "(root)"
    if isinstance(node, dict):
        out.append(f"{label}: object, {len(node)} keys")
        if depth == 0:
            return
        for i, (k, v) in enumerate(node.items()):
            if i >= MAX_ITEMS:
                out.append(f"{label}: ... {len(node) - MAX_ITEMS} more keys")
                break
            walk(v, f"{path}.{k}" if path else str(k), k, depth - 1, out)
    elif isinstance(node, list):
        out.append(f"{label}: array, {len(node)} items")
        if depth == 0 or not node:
            return
        for i, v in enumerate(node[:3]):
            walk(v, f"{label}[{i}]", key, depth - 1, out)
        if len(node) > 3:
            out.append(f"{label}: ... {len(node) - 3} more items")
    else:
        out.append(f"{label}: {type(node).__name__} = {describe_scalar(key, node)}")


def descend(node, parts):
    key = None
    for part in parts:
        if isinstance(node, dict) and part in node:
            node, key = node[part], part
        elif isinstance(node, list) and part.lstrip("-").isdigit() and -len(node) <= int(part) < len(node):
            node = node[int(part)]
        else:
            sys.exit(f"peek.py: path segment '{part}' not found")
    return node, key


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--path", default="")
    ap.add_argument("--path-sep", default=".")
    ap.add_argument("--depth", type=int, default=3)
    args = ap.parse_args()

    try:
        with open(args.file, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        sys.exit(f"peek.py: cannot read {args.file}: {exc}")

    parts = [p for p in args.path.split(args.path_sep) if p] if args.path else []
    node, key = descend(data, parts)
    out = []
    walk(node, args.path, key, args.depth, out)
    print("\n".join(out))


if __name__ == "__main__":
    main()
