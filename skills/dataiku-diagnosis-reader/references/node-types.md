# Node types: design vs. automation vs. unverified others

DSS nodes declare their role in `install.ini` → `[general] nodetype`. This skill's docs are
verified against real samples for two roles:

- **`design`** — interactive project authoring (2 real samples surveyed)
- **`automation`** — runs deployed project bundles/scenarios on a schedule (1 real sample surveyed)

Any other value (most notably **`deployer`**, the node that hosts the Project/API Deployer) is an
**unverified gap** — no sample was available. For a `deployer`-node bundle, apply the general
3-tier content model, but inspect `config/`/`run/` subtrees directly rather than assuming they
match either table below.

## What's the same across design and automation

- All root-level OS/host diagnostic files (`diag.txt`, `timings.txt`, `*_listing.txt`, `stacks.txt`,
  `sockets.txt`, `sysctl.txt`, `dmesg.txt`, `syspackages.txt`, `ps.txt`, `pip.txt`) — same set,
  same format, and the **same full command sequence in `timings.txt`** (including the `find -ls`
  scans and the JVM stack-dump capture — these run on automation nodes too, not just design). The
  diagnostic-collection tooling itself is node-type-agnostic (see `references/root-files.md`).
  `r.txt` and `docker_images_listing.txt` were absent in the automation sample, but for incidental
  reasons (R's output went to an uncopied tmp path; no Docker configured on that host) — not a
  structural node-type difference.
- `config/projects/<KEY>/` has the same file inventory shape on both — datasets, recipes,
  analysis, saved_models, scenarios (as definitions), dashboards, insights, wiki, notebooks,
  project-local lib, per-project git history. On automation this is because *activating a bundle*
  expands its content in place, just like a live-authored project.
- `cgroups_usage.txt` uses the same `/DSS/<project>/<activityType>` cgroup taxonomy on both — only
  the *mix* of activity types differs (see below).
- `config/plugins/<id>/settings.json` (installed + enabled plugin state) exists and is populated
  on both — a plugin doesn't need to be *developed* on a node to be *used* there.

## What differs

| Aspect | design | automation |
|---|---|---|
| `config/projects/<KEY>/active-bundle.json` | Rare — usually absent, since design projects aren't normally "activated." One design sample had exactly one project with this file, apparently used to test-activate a bundle before deployment | Present for most projects: `{"bundleId": "...", "activatedOn": "2026-01-28T18:41:12+08:00"}` — the definitive record of which deployed bundle is live |
| Code environments | `code-envs/desc/python/<env>/` holds real, centrally/admin-managed env specs. Both `code-envs/desc` and `acode-envs/desc` are scanned by the collector on every node type (`find code-envs/desc acode-envs/desc -ls`), so the `acode-envs/` slot exists structurally on design nodes too — it's just typically empty there | `code-envs/desc/` may be empty; per-bundle envs instead live under `acode-envs/python/<name>/desc/{spec,actual}/...` ("activated code-envs", auto-created on bundle activation), with build logs at `acode-envs/logs/python/<env>/*.log` |
| `plugins/dev/<plugin>/` | Populated with real plugin source (`plugin.json`, `python-lib/`, `custom-recipes/`, etc.) when dev has happened | Present but **empty** — the directory slot exists in the schema, but no plugin development happens on an automation node |
| `code-studio-templates/` | May hold real Code Studio templates | Present but empty — no interactive Code Studio building on automation |
| `general-settings.json` → `deployerClientSettings.mode` | May be absent, or `REMOTE`/local depending on role; a node that also hosts deployer config carries full `api-deployer/`/`project-deployer/` directories under `config/` | Commonly `"REMOTE"`, pointing at a Project Deployer node URL + API key — this node is a **deployment target**, not a deployer host, and has **no** `api-deployer/`/`project-deployer/` config subtrees |
| `governIntegrationSettings` (Govern MLOps integration) | May be present | Observed enabled, pointing at a Govern node URL + API key — worth documenting as an example of enterprise MLOps wiring |
| `caches/reflected-events-v.json` | Generic reflected-event cache | Doubles as a **bundle-activation audit trail** — repeated `"message": "bundle-activate"` entries with timestamps |
| `caches/reflected-events-p.json` | Generic | Observed capturing failures of `unified-monitoring/automation/project-scenarios-run` and `.../project-models-status` public API calls — an automation/MLOps-monitoring-specific REST surface |
| `run/install-impersonation.log` + `install.ini`'s `[mus] exec_wrapper_location` | Present, less central | Directly tied to running *scheduled* jobs as specific OS users — most operationally relevant on automation |
| `cgroups_usage.txt` activity-type mix | Skews interactive: `jupyterKernels`, `pythonRRecipes` (interactive editing), `Devlambdaserver` | Skews scheduled/batch: `scenarioPython`, `pythonRRecipes` (recipe execution), `metricsChecks`, `mlKernels` |
| `run/audit/`, `run/user-last-activity.json`, `hs_err_pid*.log` | Observed present in design samples | **Not observed** in the one automation sample — treat as "not observed in this sample," not "never present," since capture completeness varies |

## Capture-completeness caveat

In the automation sample surveyed, `acode-envs/` had only its build **logs** physically mirrored
into the bundle (`acode-envs/logs/python/<env>/*.log`) — the actual `desc/{spec,actual}` files for
those envs were visible only via `datadir_listing.txt` (Tier 3, metadata only), not as real files.
Don't assume every automation bundle mirrors `acode-envs/` content the same way; check what's
actually there before asserting a package version came from a live file vs. a listing.
