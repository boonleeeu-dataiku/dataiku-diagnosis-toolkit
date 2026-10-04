# Spec for upstream: `dataiku-diagnosis-reader` (skill + MCP server)

Target repo: `github.com/boonleeeu-dataiku/dataiku-diagnosis-reader`. The vendored copies here are
read-only (see CLAUDE.md), so these changes must be made upstream and re-synced.

**Principle:** how to read a bundle (layout, safe extraction, secret handling) is owned by the
reader. The `dataiku-diagnosis-checklist-review` skill owns only checklist judgment. Status:
section 3 (layout facts) shipped in reader skill v0.2.0 and `calibrations.md` is now judgment-only;
sections 1, 2 and 4 are still open upstream, and the secrets pointer in the checklist skill is the
one remaining interim stopgap.

## 1. Secret handling rule (move from the checklist skill)

Add to the reader `SKILL.md` (and so the `skill-guide` resource), as a short section:

- Bundles and neighbouring files hold live credentials: `general-settings.json` (`internalDatabase`
  password, connection and LDAP bind passwords), `connections.json`, `install.ini`,
  `dip.properties`, and loose notes files beside the bundle (e.g. `Notes.txt` with an API key id
  and secret). Tool output lands in the transcript.
- Do not read files that were not asked for (notes, READMEs beside the bundle). Ask the user.
- Never dump a whole settings block. Extract only the specific keys needed (see section 2).
  For `.ini`/`.properties`, grep exact key names.
- If a secret is printed, say so, name the file, and tell the user to rotate it. Never copy
  secrets into findings, notes, narratives or decks.

**Interim stopgap in the checklist skill:** a one-line pointer to the reader's guidance. Remove
the pointer's "once shipped" caveat after re-sync.

## 2. `safe_read`: structured JSON key extraction: WITHDRAWN (tool removed, MCP server 0.3.0)

`safe_read` was removed: agents never called it and read bundle files with their own tools. The
text below is kept only as a record. If JSON extraction or secret redaction is wanted again, it
needs a new design (for example answer-shaped extraction tools), not a revival of this spec. Note
that §1 (secret handling) now matters more, because bundle reads are no longer guarded by any tool.

Problem: `safe_read` filters by regex per line, so it cannot pull nested keys out of
`general-settings.json` or `connections.json`. A run therefore fell back to `device_bash` with
ad-hoc Python, which also bypassed the pattern-filter's incidental secret protection.

Proposed: new optional parameter `json_path` (or `json_keys: string[]`) on `safe_read`.
- Parse the file as JSON and return only the selected paths (dotted, with `[*]` for arrays, e.g.
  `containerSettings.executionConfigs[*].kubernetesResources`, `connections.*.type`).
- Redact by default any key matching `password|secret|token|apikey|credential|privateKey` and
  `e:AES:` blobs, replacing the value with `<redacted>`; add `reveal_secrets: false` default.
- Same size and line caps as today; error clearly if the file is not valid JSON or too large.
- Also useful: `count_matches: true` returning `grep -c`-style counts and first/last timestamp
  for large logs, replacing the checklist's `device_bash` `grep -c | uniq -c` advice.

(End of the withdrawn §2.)

## 3. Layout facts missing from the reader docs: DONE (reader skill v0.2.0)

Shipped. Kept for the record of what moved and where; do not re-add these to the checklist skill.
New layout facts follow the same path (see CLAUDE.md).

Currently documented only in the checklist skill (`references/calibrations.md`). Add each to
the named reader reference, then the checklist skill can drop its copy.

| Fact | Add to |
|---|---|
| `diag.txt` → `lsblk -t`: the `ROTA` column, 0 = SSD/non-rotational, 1 = rotational; match the row to the volume holding the data dir | `root-files.md`, `lookup-table.md` |
| Backend log entries are bracketed (`[ERROR]`, `[FATAL]`); a bare `ERROR` pattern can return a false zero. Record first/last timestamp per rotated file so counts carry a time window | `data-dir-runtime-and-codeenvs.md` |
| No Kubernetes cluster attached = empty/absent `config/clusters/` **and** no `defaultK8sClusterId`/cluster reference in `general-settings.json` | `data-dir-config.md` (resource-governance subsection) |
| `hs_err_pid*.log`: the `^# ` header lines give the crash cause (OOM vs segfault); do not read the full file | `data-dir-runtime-and-codeenvs.md` |
| Advanced security keys (header settings, `dku.feature.*`, upload extensions) may be in `dip.properties` or `install.ini`, not `general-settings.json`; search all three before calling a setting absent | `data-dir-config.md`, `lookup-table.md` |
| `sanity-check.json` warnings are DSS's own diagnosis (SSD/rotational disk, missing cgroup limits, missing base images, connection detail-read gaps) | `data-dir-runtime-and-codeenvs.md` |
| Connection settings of interest: `detailsReadability`/`readableBy`, `hdfsInterface`, fast-write flags, `filesystem_root` | `data-dir-config.md` |
| Concurrency/sizing limits can sit under other blocks (e.g. `jekSettings.maxRunningJobs`) than their name suggests; search the whole file for the leaf key (e.g. `traceExplorerDefaultWebApp` is under `generativeAISettings.llmTraceSettings`) | `data-dir-config.md` |
| `backend.xmx` etc. in `install.ini`; the `config/` folder size from `du -sh` or summing `datadir_listing.txt` | `data-dir-identity.md`, `listings-and-manifests.md` |

Two table rows were refined once checked against real bundles: `sanity-check.json` has two shapes
(`messages[]` at top level, or under `report.messages`), and `project-deployer/` held only
`projects/` in the sample (`infras/`, `deployments/` were under `api-deployer/`). The cluster
`type` (`manual`) and `defaultK8sClusterId` were confirmed in one bundle.

## 4. Make the guide-first expectation explicit

- `run_orient` already says "Read the skill-guide resource first". (The `safe_read` items that were
  here are withdrawn with §2.)

## 5. Tests (upstream)

- (Withdrawn with §2.) `safe_read` `json_path`: nested key, array wildcard, missing path, invalid JSON, redaction of
  secret-named keys, oversize file.
- Resource list in `src/resources.ts` unchanged unless a new reference file is added.
- Bump `mcp-server-diagnosis-reader` and skill versions per upstream CLAUDE.md.

## After upstream ships

1. Re-sync here (see CLAUDE.md). `tests/test_vendored_drift.py` confirms the copy.
2. Update the checklist skill: drop the interim pointer caveat for the secrets guidance.
3. (Done) The interim allowlist in `tests/test_skill_boundaries.py` is gone; `calibrations.md` is guarded.
4. Remind the user to run Codex (the MCP server changed).
