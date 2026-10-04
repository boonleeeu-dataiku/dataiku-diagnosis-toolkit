# Changelog

All notable changes to the `dataiku-diagnosis-reader` skill package are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this package
adheres to [Semantic Versioning](https://semver.org/). The version tracked here is the one in
`SKILL.md`'s `version` frontmatter field — the two must always match.

Versioning is scoped to this directory (`dataiku-diagnosis-reader/`) only, since it's the unit
that gets copied/symlinked into a skills root independently of the rest of this repo.

## [0.3.0] - 2026-10-04

### Added

- `SKILL.md`: "Handling secrets" section (read only what is needed, extract specific keys, never copy
  secrets into outputs, report and rotate if printed).

### Changed

- `SKILL.md`: shorter `description`; "Quick lookup" trimmed to the highest-traffic rows (the full index
  stays in `references/lookup-table.md`); "Known limitations" reduced to a pointer plus the key caveats;
  step 7 now says to run `scripts/orient.sh` first when triaging a whole bundle; quoted frontmatter values.

## [0.2.0] - 2026-10-04

### Added

- `references/data-dir-config.md`: how to tell whether a Kubernetes cluster is attached
  (`config/clusters/` and `defaultK8sClusterId`), cluster `type`/`architecture`, observed
  deployer subtree shape, a "finding a setting reliably" section (leaf-key search, limits under
  other blocks, `dip.properties`/`install.ini`, feature-in-use signals) and connection
  `detailsReadability`/`params.root`/`hdfsInterface`.
- `references/data-dir-runtime-and-codeenvs.md`: backend log line format (bracketed levels),
  per-file time windows, `hs_err_pid*.log` header reading; `sanity-check.json` documented with both
  observed shapes and the codes seen.
- `references/root-files.md`, `data-dir-identity.md`, `listings-and-manifests.md`,
  `lookup-table.md`: `lsblk -t` `ROTA` column, `[javaopts]` heap keys, sizing `config/` from
  `config_listing.txt`, and matching lookup rows.

### Changed

- Facts from these additions that no sample could verify (`agentBuildingSettings`, an
  `INTERNAL_huggingface` code env, `jek.xmx`/`fek.xmx`, a populated `project-deployer/`'s
  `infras/` and `deployments/`, the `type` value of a DSS-provisioned cluster) are marked as
  unverified in the text rather than asserted.

## [0.1.0] - 2026-09-21

### Added

- Initial skill: `SKILL.md` 3-tier content model and step-by-step investigation workflow,
  `scripts/orient.sh`, and `references/` covering root files, the data-dir mirror (identity,
  config, runtime/code-envs), listings/manifests, node-type differences, the quick lookup table,
  and documented limitations.
- Spark-on-Kubernetes namespace fields documented in `references/data-dir-runtime-and-codeenvs.md`.

[0.2.0]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/releases/tag/skill-v0.2.0
[0.1.0]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/releases/tag/skill-v0.1.0
