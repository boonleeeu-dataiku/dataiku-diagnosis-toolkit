# `<mirror>/` runtime logs, code environments, plugins, and support config

All paths below are relative to the data-dir mirror root (see `references/data-dir-identity.md`).

## Code environments

**`code-envs/desc/python/<env-name>/`** — centrally/admin-managed Python environments (common on
design nodes; may be empty on an automation node):

- `desc.json` — env definition: `pythonInterpreter`, `corePackagesSet`, `deploymentMode`, creation/
  modification tags (who/when)
- `spec/requirements.txt`, `spec/environment.spec` — the **requested** spec (can be blank/unset)
- `actual/requirements.txt` — the **actually resolved, pinned** package list (e.g.
  `absl-py==2.3.1`) — **this is the answer to "what packages/versions are installed in env X"**,
  not `spec/requirements.txt`
- `actual/info.json` — build metadata (often minimal)
- `code-envs/logs/python/<env>/*.log` — install/build logs (pip resolution errors, etc.)
- Often has an internal `.git` history tracking env spec changes over time

**`acode-envs/python/<name>/`** — "activated code-envs", auto-created when a bundle activates on a
node. The collector scans this path on every node type (`find code-envs/desc acode-envs/desc -ls`
runs regardless of `nodetype`), but it's typically empty on design nodes and populated on
automation nodes where bundles get activated. Same shape as `code-envs/` (`desc/{spec,actual}/...`),
with build/activation logs at `acode-envs/logs/python/<env>/*.log` (`importPythonEnv.log`,
`handleCodeEnv.log`, `createEnv.log`, `updateEnvFolderAccordingToSpec.log`,
`installJupyterSupport.log`). **Capture-completeness caveat**: in the sample surveyed, only the
logs were physically mirrored into the bundle — the `desc/{spec,actual}` files themselves were
visible only via `datadir_listing.txt`, not as real files. Verify per-bundle.

## `caches/`

Backend runtime JSON caches — generally low troubleshooting value, with two automation-flavored
exceptions:

- `reflected-events-v.json` — on automation nodes, doubles as a **bundle-activation audit trail**:
  repeated `{"message": "bundle-activate", ...}` entries with timestamps.
- `reflected-events-p.json` — observed capturing failures of `unified-monitoring/automation/
  project-scenarios-run` and `.../project-models-status` public API calls (automation/MLOps
  monitoring endpoints).
- `reports.json` — cached `project-usage-summary-<PROJECT>` reports.

## `install-support/`

- `nginx.conf`, `supervisord.conf` — generated reverse-proxy and process-supervisor configs
- `backends.d/<NAME>/<id>.conf` — per-project/webapp nginx routing (folder names reveal registered
  webapps/special backends, e.g. deployed API endpoints). Notably absent on the automation sample
  surveyed.

## `plugins/dev/<plugin>/`

Locally-developed plugin **source code**: `plugin.json`, `python-lib/`, `python-runnables/`,
`custom-recipes/`, `webapps/`, `code-env/`, `parameter-sets/`, often with `README.md`/
`Jenkinsfile`/`CHANGELOG.md`. Populated on design nodes where plugin development happens; present
as an **empty placeholder directory** on automation nodes (the schema reserves the slot, but no
dev activity occurs there). This is separate from `config/plugins/<id>/settings.json`, which
records install/enable state on *any* node type (see `references/data-dir-config.md`).

## `run/` — live runtime logs and state

| File | Contains | Notes |
|---|---|---|
| `backend.log` (+ `.1`/`.2` rotated) | Main DSS backend Java process log: API call traces (`[dku.tracing] Start call: ... user=...`), job/scenario status, exceptions | **Primary app log** for "what happened and when" |
| `frontend.log.0`-`.4` | Node/JS frontend server logs | |
| `nginx.log` (+ rotated) | Reverse-proxy access/error log | |
| `ipython.log` (+ rotated) | Jupyter/ipython gateway process log | |
| `eventserver.log` (+ rotated) | Usage-tracking/telemetry log | |
| `supervisord.log` | Process-manager log: start/stop/restart events for backend/frontend/nginx/ipython/eventserver | |
| `install.log` | Full install/upgrade transcript | Can be ~90-100MB+; never load whole |
| `install-impersonation.log` | `dssadmin install-impersonation` output — sets up the OS-user impersonation wrapper referenced by `install.ini`'s `[mus] exec_wrapper_location` | Most operationally relevant for scheduled/unattended job execution (automation) |
| `hs_err_pid<N>.log` | **JVM fatal crash dumps** (HotSpot error logs) — native-mmap OOM failures, thread/heap/register dump | Primary source for crash/OOM root-cause; cross-reference with `dmesg.txt` (OOM-killer) and `cgroups_usage.txt` (which project/activity was responsible). Not observed in the one automation sample surveyed — absence doesn't rule it out generally |
| `sanity-check.json` | DSS's own self-diagnostic warnings: `{"messages":[{"severity","code","details"}]}` | Surfaces real misconfigurations DSS itself flagged, e.g. `WARN_CONNECTION_SPARK_NO_GROUP_WITH_DETAILS_READ_ACCESS`, `WARN_MISC_EVENT_SERVER_NO_TARGET` |
| `user-last-activity.json` | Per-login last activity/login timestamps | Can reveal auth/attack attempts in login strings. Not observed in the automation sample surveyed |
| `cde-images.json`, `built-base-images.json` | Code-env-in-container / Code Studio image build records | Not observed in the automation sample surveyed (consistent with no Code Studio building there) |
| `audit/audit.log.N` | Rotated audit trail (user actions) | Often ~100MB each. **Not observed as real content in any of the 3 samples surveyed** — only as path/size entries in `datadir_listing.txt`. Don't assume it's ever mirrored as content; verify per-bundle before promising to read it |

Cross-reference: when investigating a crash, check `hs_err_pid*.log` timestamps against
`dmesg.txt` OOM-killer entries and `cgroups_usage.txt` to identify which project/activity type was
responsible for the memory pressure.
