# Limitations and known gaps

## Verified scope

This skill's documentation was built from 3 real extracted diagnosis bundles: 2 from `design`
nodes, 1 from an `automation` node. Everything in `references/data-dir-config.md` and
`references/data-dir-runtime-and-codeenvs.md` is grounded in one or more of those samples.

**`deployer`-node bundles (and any node type other than `design`/`automation`) are unverified** —
no sample was available. If you're handed one, apply the general 3-tier content model
(`SKILL.md`) and the root-file docs (`references/root-files.md` — these are node-type-agnostic),
but inspect `config/`/`run/` subtrees directly rather than assuming they match the design or
automation docs.

## The #1 content gap: job/scenario/audit history

Job run history, scenario run logs, dataset build timelines, and audit-log *content* are
frequently represented **only** as path/size/date entries in `datadir_listing.txt` (Tier 3) —
not as retrievable content in the bundle. Concretely, in the samples surveyed:

- `config/projects/<KEY>/scenarios/<name>.json` gives you a scenario's **definition** (steps,
  triggers, reporters) — never its run history.
- Directories like `jobs/`, `scenarios/<proj>/<scenario>/`, and `timelines/` under the live
  `DATA_DIR` typically appear only as entries in `datadir_listing.txt`.
- `run/audit/audit.log.N` (rotated, often ~100MB each) was **not observed as real content in any
  of the 3 samples surveyed** — only as a listing entry in `datadir_listing.txt`. Don't assume
  it's ever mirrored as content; verify per-bundle.

When asked about this kind of history, check `datadir_listing.txt` for existence/size/last-modified
and say plainly that content isn't retrievable from the bundle, rather than guessing or fabricating.

## Capture completeness varies

Which tier is populated, and how completely, differs by DSS version, site configuration, and
probably size limits on the diagnosis collector itself. Examples observed:

- One automation sample mirrored only build *logs* for `acode-envs/`, not the underlying
  `desc/{spec,actual}` files (see `references/node-types.md`).
- `docker_images_listing.txt` only appears when container/K8s execution is configured — its
  absence doesn't imply anything about node type.
- `r.txt` was absent in one sample because the R diagnostic command's output was written to a
  scratch tmp path that wasn't copied into the final bundle, even though the command clearly ran
  (visible in `diag.txt`).

Treat every "X doesn't exist in this bundle" finding as evidence for *this* bundle, not a
universal rule — always note whether something is "not observed" vs. structurally impossible.

## Other things to know

- `config/license.json` may be a signed/opaque blob (`{content, r1Sig, r1Pub, r1PubSig}`) — not
  always fully human-readable without decoding.
- `config/general-settings.json` and other config JSON can contain encrypted-but-present
  credentials (e.g. LDAP bind passwords, API keys as `e:AES:...` blobs) and PII (user emails,
  display names). Handle bundle contents as sensitive data — don't echo secrets/PII unnecessarily,
  and don't assume a bundle is safe to share further just because it's a "diagnostic" export.
- The instance-wide resource-governance blocks in `general-settings.json`
  (`cgroupSettings`/`containerSettings`/`sparkSettings`/`k8sPoliciesSettings`, and `clusters/*.json`
  overrides — see `references/data-dir-config.md`) are grounded in all 3 samples. But the
  **recipe-level field that selects one of these named profiles**
  (`params.engineParams.spark.sparkConfig.inheritConf` / `containerSelection`) was confirmed in
  only one Spark/join recipe in one sample — don't assume the same field names apply to other
  recipe engines, scenario steps, or notebook kernels without checking.

## Large-file hazards — never load these fully into context

| File | Observed size range |
|---|---|
| `datadir_listing.txt` | ~340MB to ~2.3GB |
| `installdir_listing.txt` | ~13-14MB |
| `stacks.txt` | ~680KB to ~3.8MB |
| `run/install.log` | up to ~90-100MB |
| `run/*.log.N` (rotated backend/frontend/nginx/ipython logs) | individually up to ~100MB |
| `run/audit/audit.log.N` (when present as real content) | ~100MB each |

Always `grep`/`awk`/`wc -l`/`head`/`tail` these — see `references/listings-and-manifests.md` for
safe query patterns on the `find -ls` manifest files specifically.
