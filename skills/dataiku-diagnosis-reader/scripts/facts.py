#!/usr/bin/env python3
"""Key settings of a Dataiku diagnosis bundle in one deterministic, secret-safe JSON report.

Usage: facts.py <bundle_root>

Prints one JSON object, `{fact_name: {"value": ..., "source": "<path relative to the mirror>: <key>"}}`.
A setting that is not in the bundle is reported as `{"value": "ABSENT", "searched": [...]}`, so
"absent" is never confused with `false` or `0`. A fact that could not be read is reported as
`{"value": "ERROR", "error": "..."}`; one bad file never stops the others.

It exists so a reviewer quotes these values instead of re-reading a ~large general-settings.json by
hand (hand reads have mis-stated hosts, flags and limits, and missed keys that sit under an
unexpected block). Concurrency limits are found by leaf-key search of the whole file, so a limit under
`jekSettings` is not missed. The `config/` size comes from `config_listing.txt`, not `du`.

Read-only; no network calls; Python 3 stdlib only. Passwords and other secrets are never printed
(only a boolean says whether the internal database password is stored in plaintext). Redaction reuses
`peek.py` when it sits next to this file, with a built-in fallback if it does not.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from peek import describe_scalar
except ImportError:  # copied on its own: redact every string under a secret-looking key
    _SECRET = re.compile(r"pass|pwd|secret|token|key|credential|auth|cert|private|salt|hash", re.I)

    def describe_scalar(key, value):
        if isinstance(value, str) and key is not None and _SECRET.search(str(key)):
            return "<redacted>"
        return json.dumps(value)

ABSENT = "ABSENT"
CONCURRENCY_KEYS = ("maxRunningJobs", "maxRunningActivities", "maxRunningActivitiesPerJob")
LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]", "0.0.0.0"}
FACTS = {}


def safe(value, key=None):
    """JSON-ready value with strings run through the redaction used by peek.py."""
    if value == ABSENT:  # the marker is not a secret, even under a key name like "authenticationEnabled"
        return value
    if isinstance(value, str):
        shown = describe_scalar(key, value)
        try:
            return json.loads(shown)
        except ValueError:
            return shown
    return value


def fact(name):
    """Register a fact function; an exception becomes an ERROR entry for that fact only."""
    def deco(fn):
        def run():
            try:
                FACTS[name] = fn()
            except Exception as exc:  # noqa: BLE001 - one bad file must not abort the report
                FACTS[name] = {"value": "ERROR", "error": f"{type(exc).__name__}: {exc}"}
        run.__name__ = fn.__name__
        RUNNERS.append(run)
        return run
    return deco


RUNNERS = []
ROOT = MIRROR = None


def found(value, source):
    return {"value": value, "source": source}


def absent(*searched):
    return {"value": ABSENT, "searched": list(searched)}


def load_json(rel):
    path = os.path.join(MIRROR, rel)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def dig(node, dotted):
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return ABSENT
    return node


def leaf_search(node, names, path=""):
    """Every (dotted path, value) whose last key is in `names`, anywhere in the document."""
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}" if path else str(k)
            if k in names and not isinstance(v, (dict, list)):
                hits.append((p, v))
            hits.extend(leaf_search(v, names, p))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits.extend(leaf_search(v, names, f"{path}[{i}]"))
    return hits


def settings_fact(*dotted_paths):
    """Value of each dotted path in general-settings.json (ABSENT when missing)."""
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    return {"source": src, "value": {p: safe(dig(gs, p), p.rsplit(".", 1)[-1]) for p in dotted_paths}}


def parse_ini(path):
    """{'section.key': value} for an INI file, tolerant of odd lines (no configparser strictness)."""
    out, section = {}, ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line[0] in "#;":
                continue
            m = re.match(r"\[(.+)\]$", line)
            if m:
                section = m.group(1).strip()
            elif "=" in line:
                k, v = line.split("=", 1)
                out[f"{section}.{k.strip()}"] = v.strip()
    return out


def mem_total_kb():
    path = os.path.join(ROOT, "diag.txt")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.match(r"MemTotal:\s+(\d+)\s*kB", line)
            if m:
                return int(m.group(1))
    return None


def to_gib(text):
    """'190G' / '512M' / a byte count -> GiB, or None."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([KMGT]?)i?B?\s*", str(text), re.I)
    if not m:
        return None
    unit = {"": 1, "K": 1024, "M": 1024 ** 2, "G": 1024 ** 3, "T": 1024 ** 4}[m.group(2).upper()]
    return float(m.group(1)) * unit / 1024 ** 3


@fact("node")
def node():
    ini = os.path.join(MIRROR, "install.ini")
    kv = parse_ini(ini)
    ver = load_json("dss-version.json") or {}
    pick = lambda k: next((v for key, v in kv.items() if key.split(".", 1)[1] == k), ABSENT)  # noqa: E731
    return found({"nodetype": pick("nodetype"), "nodeid": pick("nodeid"), "installid": pick("installid"),
                  "product_version": ver.get("product_version", ABSENT)}, "install.ini, dss-version.json")


@fact("heap_sizes")
def heap_sizes():
    kv = parse_ini(os.path.join(MIRROR, "install.ini"))
    xmx = {k: v for k, v in kv.items() if "xmx" in k.lower()}
    if not xmx:
        return absent("install.ini (no *.xmx key; DSS defaults apply)")
    return found(xmx, "install.ini")


@fact("host_memory")
def host_memory():
    kb = mem_total_kb()
    if kb is None:
        return absent("diag.txt MemTotal")
    return found({"MemTotal_kB": kb, "GiB": round(kb / 1024 / 1024, 1)}, "diag.txt: MemTotal")


@fact("config_folder_size")
def config_folder_size():
    rel = "config_listing.txt"
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return absent(rel)
    total = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            f = line.split(None, 10)
            if len(f) >= 11 and f[2].startswith("-") and f[6].isdigit():
                total += int(f[6])
    return found({"bytes": total, "MiB": round(total / 1024 ** 2, 1), "GiB": round(total / 1024 ** 3, 2)},
                 f"{rel}: sum of regular-file sizes (not du)")


@fact("internal_database")
def internal_database():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    conn = dig(gs, "internalDatabase.connection")
    if conn == ABSENT or not isinstance(conn, dict):
        return absent(f"{src}: internalDatabase.connection")
    params = conn.get("params") or {}
    host = params.get("host", ABSENT)
    pw = params.get("password")
    return found({
        "type": conn.get("type", ABSENT),
        "host": host,
        "host_is_loopback": (str(host).lower() in LOOPBACK) if host != ABSENT else ABSENT,
        "port": params.get("port", ABSENT),
        "password_stored_in_plaintext": (bool(pw) and not str(pw).startswith("e:")) if "password" in params else ABSENT,
    }, f"{src}: internalDatabase.connection (password value never printed)")


@fact("concurrency_limits")
def concurrency_limits():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    value = {}
    for name in CONCURRENCY_KEYS:
        hits = [{"path": p, "value": v} for p, v in leaf_search(gs, {name})]
        value[name] = hits or ABSENT
    return found(value, f"{src}: leaf-key search of the whole file (a 0 under jekSettings means unsized)")


@fact("sso_and_ldap")
def sso_and_ldap():
    return settings_fact("ssoSettings.enabled", "ssoSettings.protocol",
                         "ldapSettings.enabled", "ldapSettings.authenticationEnabled")


@fact("user_isolation")
def user_isolation():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    imp = dig(gs, "impersonation")
    if imp == ABSENT:
        return absent(f"{src}: impersonation")
    return found({"enabled": imp.get("enabled", ABSENT), "user_rules": len(imp.get("userRules") or []),
                  "group_rules": len(imp.get("groupRules") or [])},
                 f"{src}: impersonation (rule counts only, account names not printed)")


@fact("cgroups")
def cgroups():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    cg = dig(gs, "cgroupSettings")
    if cg == ABSENT:
        return absent(f"{src}: cgroupSettings")
    kb = mem_total_kb()
    placements_empty = [k for k, v in cg.items() if isinstance(v, dict) and not v.get("targets")]
    limits = []
    for entry in cg.get("cgroups") or []:
        for lim in entry.get("limits") or []:
            gib = to_gib(lim.get("value"))
            limits.append({
                "cgroup": entry.get("cgroupPathTemplate"), "limit": lim.get("key"), "value": lim.get("value"),
                "pct_of_MemTotal": round(100 * gib / (kb / 1024 / 1024), 1) if gib and kb and "memory" in str(lim.get("key")) else None,
            })
    return found({"enabled": cg.get("enabled", ABSENT), "version": cg.get("cgroupsVersion", ABSENT),
                  "limits": limits or ABSENT, "workload_categories_with_no_placement": placements_empty},
                 f"{src}: cgroupSettings (pct uses G=GiB against diag.txt MemTotal in GiB)")


@fact("connections")
def connections():
    src = "config/connections.json"
    doc = load_json(src)
    if doc is None:
        return absent(src)
    conns = doc.get("connections", doc) if isinstance(doc, dict) else {}
    return found({"count": len(conns), "filesystem_root_present": "filesystem_root" in conns},
                 f"{src}: connections (names only, no params)")


@fact("trace_explorer")
def trace_explorer():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    hits = leaf_search(gs, {"projectKey", "webAppId"}, "")
    hits = [(p, v) for p, v in hits if "traceExplorerDefaultWebApp" in p]
    trace = dig(gs, "generativeAISettings.llmTraceSettings")
    if not hits:
        return found({"configured": False, "llmTraceSettings": safe(trace)} if trace != ABSENT
                     else ABSENT, f"{src}: generativeAISettings.llmTraceSettings")
    return found({"configured": all(v for _, v in hits), "fields": {p: v for p, v in hits}},
                 f"{src}: generativeAISettings.llmTraceSettings.traceExplorerDefaultWebApp")


@fact("default_preferences")
def default_preferences():
    src = "config/general-settings.json"
    gs = load_json(src)
    if gs is None:
        return absent(src)
    names = ("preferedConnection", "forcedPreferedConnection", "preferedUploadConnection", "preferedStorageFormats")
    dflt = dig(gs, "defaultDatasetCreationSettings")
    engines = dig(gs, "recipeEnginesPreferences")
    return found({
        "defaultDatasetCreationSettings": {n: (safe(dflt.get(n, ABSENT), n) if isinstance(dflt, dict) else ABSENT) for n in names},
        "recipeEnginesPreferences_nonempty": ({k: v for k, v in engines.items() if v} if isinstance(engines, dict) else ABSENT),
    }, f"{src}: defaultDatasetCreationSettings, recipeEnginesPreferences (key ABSENT or empty = blank)")


@fact("plugins")
def plugins():
    rel = "config/plugins"
    path = os.path.join(MIRROR, rel)
    if not os.path.isdir(path):
        return absent(rel)
    names = sorted(d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d)))
    return found({"installed_config_dirs": names, "agent_hub_installed": "agent-hub" in names,
                  "AGENT_HUB_project_present": os.path.isdir(os.path.join(MIRROR, "config/projects/AGENT_HUB"))},
                 f"{rel}: directory names (agent_hub_installed = an agent-hub dir exists)")


def find_mirror(root):
    for dirpath, dirs, files in os.walk(root):
        if dirpath[len(root):].count(os.sep) > 6:
            dirs[:] = []
            continue
        if "install.ini" in files:
            return dirpath
    return None


def main():
    global ROOT, MIRROR
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("Usage: facts.py <bundle_root>")
    ROOT = os.path.abspath(sys.argv[1])
    MIRROR = find_mirror(ROOT)
    if MIRROR is None:
        sys.exit("facts.py: no install.ini found under the bundle (searched 6 levels deep)")
    for run in RUNNERS:
        run()
    print(json.dumps({"bundle_root": ROOT, "mirror": MIRROR, "facts": FACTS}, indent=2, default=str))


if __name__ == "__main__":
    main()
