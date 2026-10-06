---
name: "dataiku-diagnosis-reader"
description: "Navigate and interpret an extracted Dataiku DSS diagnosis.zip support bundle (also: DSS diagnostic export, instance diagnostic archive, a folder named dku_diagnosis_*) to answer troubleshooting questions on instance configuration, crashes/OOMs, performance, users, connections, projects, code environments, plugins and logs, without re-deriving the bundle layout. Use whenever the user provides or asks about a Dataiku diagnosis bundle or wants to diagnose a DSS instance from one."
version: 0.8.0
---

# Dataiku DSS diagnosis.zip reader

A `diagnosis.zip` is DSS's built-in self-diagnostic export (run via `dssadmin diagnosis` or the
Administration UI). It is **not** a full backup — it's a curated mix of OS command captures, a
partial copy of the DSS data directory (`DATA_DIR`), and metadata-only file listings of the rest.
This skill tells you what's where, so you can route a question straight to the right file.

## The 3-tier content model

Every bundle mixes three kinds of content. Knowing which tier a file belongs to tells you whether
you're looking at real content or just a path/size record:

1. **OS/host diagnostic command outputs** — flat `.txt` files at the bundle root, each the
   captured stdout of one shell command (`uname -a`, `ps auxf`, `free -m`, `sysctl -a`, ...).
   `diag.txt` inlines only the *smaller* commands' output; big-output commands (package listings,
   `dmesg`, `sysctl`, `ps auxf`, `find -ls` scans, the JVM stack dump) run but leave only a bare
   timestamp placeholder in `diag.txt` — their real output is in their own dedicated file only.
   `timings.txt` is the complete, authoritative ledger of every step (including the ones
   `diag.txt` stubs out) with start/end times — see `references/root-files.md` before assuming
   something is or isn't in `diag.txt`.
2. **Real, fully-copied files** from a curated subset of `DATA_DIR` — under a "data-dir mirror"
   directory (see below) — covering `install.ini`, `config/`, `code-envs/`, `run/` logs, etc.
3. **Metadata-only manifests** (`find -ls` output — path/size/owner/mtime, **no content**) of the
   rest of `DATA_DIR` and the install dir: `datadir_listing.txt`, `installdir_listing.txt`,
   `config_listing.txt`, `lib_listing.txt`, `code_envs_desc_listing.txt`. **Job run history,
   scenario run logs, dataset build timelines, and audit-log content are frequently *only*
   present here** — you can confirm they exist/their size/when they last changed, but you cannot
   read their content from the bundle. Say so plainly rather than guessing.

How completely each tier is populated varies by DSS version, site, and size limits — treat this
as a structural model, not a byte-identical layout guaranteed across every bundle.

## Step-by-step investigation workflow

1. **Confirm you're at the bundle root**: look for `diag.txt` + `timings.txt` + `*_listing.txt`
   siblings.
2. **Locate the data-dir mirror**: `find <bundle_root> -maxdepth 5 -name install.ini`. Its parent
   directory is the mirror root. The path varies by site — observed examples include
   `apps/dss/data_design/`, `data_dataiku/design/`, and `data_dataiku/automation/` — but it
   commonly (not always) follows a `<something>/<nodetype>/` shape.
3. **Identify the node**: read `install.ini` → `[general] nodetype` and the sibling
   `dss-version.json` → `product_version`. `design` and `automation` node internals are verified
   by this skill (see `references/node-types.md` for what differs between them). Any other
   `nodetype` (e.g. `deployer`) is an **unverified gap** — apply the general 3-tier model, but
   inspect its subtrees directly rather than assuming parity with the design/automation docs here.
4. **Route the actual question** through `references/lookup-table.md` (or the condensed table
   below for common cases).
5. **Never load large manifest/log files whole.** `datadir_listing.txt` alone has been observed
   from ~340MB to ~2.3GB; rotated `run/*.log.N` files can individually reach ~100MB. Always
   `grep`/`awk`/`wc -l` first — see `references/listings-and-manifests.md` for safe patterns.
6. **If asked about job/scenario run history, dataset build timelines, or audit content**, check
   up front whether it's Tier-3 (listing-only) before promising an answer — see
   `references/limitations.md`.
7. When triaging a whole bundle, run `scripts/orient.sh <bundle_root>` first (before steps 2-3 if you
   like): node type, version, mirror path, biggest files, and presence of key troubleshooting files.
   If the script can't run (it lives in the skill folder, which may be on a different machine from
   the bundle, e.g. a sandbox agent with the bundle on a linked computer), don't skip orientation.
   First choice: pipe the script to the machine that holds the bundle. It is read-only,
   self-contained and ~4.5KB, so run `bash -s -- <root>` there with the script body on stdin (e.g. a
   quoted heredoc: `bash -s -- <root> <<'ORIENT'` ... `ORIENT`). Pipe the whole script verbatim, not a
   condensed copy, so the output matches what the script prints elsewhere (it needs `bash` plus
   standard `find`/`du`/`grep`; on Windows run it where the bundle is, in WSL or Git Bash). If stdin can't be passed, do the
   same by hand with read-only commands run where the bundle is: `find <root> -maxdepth 6 -name
   install.ini` (the mirror is its directory), `grep -m1 DKU_NODE_TYPE <root>/diag.txt` and
   `<mirror>/dss-version.json` for node type and version, `find <root> -type f -size +50M -exec ls -lh {} +`
   for the biggest files, and `ls` for `diag.txt`, `dmesg.txt`, `<mirror>/run/` and
   `<mirror>/config/general-settings.json`. Say in your output that you oriented by hand.

## Quick lookup (most common questions)

| Question | Where |
|---|---|
| DSS version / node type | `<mirror>/dss-version.json`, `<mirror>/install.ini`, or `diag.txt` → `printenv`'s `DKU_NODE_TYPE` (fastest) |
| Any general OS question (CPU, memory, disk, env vars, JVM heap/ports) | `diag.txt` (small commands are inlined; `printenv` holds `DKU_*_JAVA_OPTS`/`DKU_*_PORT`); see `references/root-files.md` |
| Backend crash / OOM | `dmesg.txt` + `<mirror>/run/hs_err_pid*.log` + `cgroups_usage.txt` |
| Instance config (LDAP/SSO/proxy/concurrency/resources/internal DB) | `<mirror>/config/general-settings.json`; see `references/data-dir-config.md` |
| Users / connections / projects | `<mirror>/config/users.json`, `connections.json`, `projects/<KEY>/` |
| Backend/API/job execution trace, DSS self-diagnostics | `<mirror>/run/backend.log*`, `<mirror>/run/sanity-check.json` |
| Job/scenario run history, audit content | Usually **not in the bundle**: check `datadir_listing.txt` for existence/size only |

See `references/lookup-table.md` for the full index.

## Handling secrets

Bundles and files beside them hold live credentials (`general-settings.json` internal-DB, connection
and LDAP bind passwords; `connections.json`; `install.ini`; `dip.properties`; loose notes files). Tool
output lands in the transcript.

- Read only files you need; don't open notes or READMEs next to the bundle unless asked.
- **Open any config JSON with `scripts/peek.py <file> [--path a.b.c] [--depth N]`.** It prints the
  structure (keys, types, non-secret values) and masks passwords, tokens, keys and embedded
  credentials. Use it first to learn a file's shape; then `--path` to one key. For `.ini`/`.properties`,
  grep exact key names. A file has more than 40 keys at some level (`general-settings.json` has over
  100 at the top)? Add `--keys` (names only) or `--max-items 200`; don't fall back to a raw dump.
- Never `cat`, `jq .`, or `print(json.load(...))` whole `general-settings.json`, `connections.json`,
  `users.json`, `install.ini` or `dip.properties`; never run `printenv`/`env` or read user scripts in
  full. Never dump a whole settings block or connection.
- Don't open user project code to look for keys: a scenario or recipe script can hold a literal API key
  in its first lines, and `head`/`cat`/`sed -n` prints it. Count instead:
  `grep -rlE "DSSClient\([^)]*[\"'][A-Za-z0-9_-]{20,}[\"']" <mirror>/config/projects/*/scenarios/ | wc -l`
  (`-l` lists file names only; `-c` counts). Report file names and counts, never the matching lines.
- Never print a whole sub-object (`json.dumps(settings["deployerClientSettings"])`, a truncated
  `str(block)[:200]`): encrypted `e:AES:` blobs and keys sit inside them. Use `peek.py --path`, or print
  named non-secret leaves only. Don't print a secret's length or prefix either.
- Don't list or print customer-internal metadata you don't need (the full connection list, hostnames, proxy
  details, `install.ini`): summarise in code (counts, names of the few items that matter) before printing.
- Never copy a secret into findings, notes, reports or decks.
- If one is printed, say so, name the file, and tell the user to rotate it.

## Reference index

- `references/root-files.md` — the full command sequence (via `timings.txt`), which parts of it
  `diag.txt` actually inlines vs. stubs out, a detailed OS/system/environment table (CPU, memory,
  disk, network, ulimits, the `printenv` treasure trove, etc.), and a per-file deep dive on every
  standalone root `.txt` file (`sockets.txt`, `sysctl.txt`, `stacks.txt`, `cgroups_usage.txt`,
  `dmesg.txt`, `syspackages.txt`, `ps.txt`, `r.txt`, `pip.txt`, `bin_listing.txt`,
  `docker_images_listing.txt`) with ready-to-run grep patterns and real examples.
- `references/listings-and-manifests.md` — how to safely query the `find -ls` manifest files
  without loading them whole.
- `references/data-dir-identity.md` — how to find the data-dir mirror, `install.ini` and
  `dss-version.json` field reference.
- `references/node-types.md` — what's identical vs. different between `design` and `automation`
  node bundles (verified), and what's unverified (`deployer`, others).
- `references/data-dir-config.md` — the `config/` metastore, including the full
  `config/projects/<KEY>/` subtree, a dedicated resource-governance subsection tying together
  `cgroupSettings`/`containerSettings`/`sparkSettings`/`clusters/*.json` for cgroups/container/K8s/
  Spark resource questions, and a subsection on identifying the internal database (H2 vs.
  PostgreSQL) via `internalDatabase`.
- `references/data-dir-runtime-and-codeenvs.md` — `run/` logs, `code-envs/`/`acode-envs/`,
  `install-support/`, `plugins/dev/`.
- `references/lookup-table.md` — the full "where do I find X" index.
- `references/limitations.md` — verified scope, known content gaps, large-file hazards.

## Known limitations

`deployer`-node (and any other) internals are unverified: don't fabricate specifics. Job run history,
scenario run logs, dataset build timelines and audit content are commonly listing-only (Tier 3): check
that before promising an answer. Capture completeness varies bundle to bundle. Full list, including
verified scope: `references/limitations.md`.
