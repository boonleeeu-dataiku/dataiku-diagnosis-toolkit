# Locating and identifying the data-dir mirror

Every diagnosis bundle contains a "data-dir mirror" directory: a partial, real copy of the DSS
`DATA_DIR` at the time the diagnosis was captured. Its path is **not fixed** — it reflects each
site's own DSS install location. Observed examples:

- `apps/dss/data_design/...` (a design node)
- `data_dataiku/design/...` (a design node)
- `data_dataiku/automation/...` (an automation node)

Don't hardcode a path. Instead:

```
find <bundle_root> -maxdepth 5 -name install.ini
```

The parent directory of the `install.ini` that returns is the mirror root. A `<mirror>/<nodetype>/`-
shaped convention shows up often (e.g. `data_dataiku/automation/`) but two of the three real
samples used a site-specific path instead — don't assume the shape, just find `install.ini`.

## `install.ini`

Plain INI. Key fields observed:

```ini
[general]
nodetype = automation        ; design | automation | deployer | ... — see references/node-types.md
installid = <opaque id>
nodeid = prod-automation      ; free-text, site-chosen

[server]
port = 10000
ssl = true
ssl_certificate = /path/to/cert

[git]
mode = project                ; DSS versions project/config metadata with internal git repos

[javaopts]
backend.xmx = 8g               ; backend JVM heap size — relevant to OOM investigations

[mus]
exec_wrapper_location = /etc/dataiku-security/<installid>/execwrapper.sh   ; OS-user impersonation wrapper, used for running jobs as specific users
```

`nodetype` is the authoritative way to determine what kind of node produced this bundle — always
read it before assuming the `config/`/`run/` structure documented for one node type applies to
another (see `references/node-types.md`).

## `dss-version.json`

Sits both at `<mirror>/dss-version.json` and (as a stub, install-metadata only) under an install-dir
mirror if one exists:

```json
{"product_version": "14.2.1", "conf_version": "14210", "product_commitid": ""}
```

`product_version` is the DSS release; `conf_version` is the internal config-schema version (useful
for spotting config compatibility issues across an upgrade).

## `bin/` — manual-patch detection

`<mirror>/bin/` holds the env shell scripts (`env-default.sh`, `env-hadoop.sh`, `env-site.sh`,
`env-spark.sh`). Watch for siblings like `env-hadoop.sh_original`, `env-hadoop.sh_modified`, or
dated backups (`env-site.sh_15Apr2026`) — these are evidence an admin manually patched the live
env script, which is worth surfacing when investigating unexpected runtime behavior (e.g. Hadoop/
Spark integration issues) since the *active* file may no longer match what ships by default.
