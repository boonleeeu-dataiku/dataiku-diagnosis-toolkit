# Changelog

All notable changes to the `dataiku-diagnosis-reader` skill package are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this package
adheres to [Semantic Versioning](https://semver.org/). The version tracked here is the one in
`SKILL.md`'s `version` frontmatter field — the two must always match.

Versioning is scoped to this directory (`dataiku-diagnosis-reader/`) only, since it's the unit
that gets copied/symlinked into a skills root independently of the rest of this repo. See
`../CLAUDE.md` for how this relates to `mcp-server-diagnosis-reader/`'s own versioning.

## [0.1.0] - 2026-09-21

### Added

- Initial skill: `SKILL.md` 3-tier content model and step-by-step investigation workflow,
  `scripts/orient.sh`, and `references/` covering root files, the data-dir mirror (identity,
  config, runtime/code-envs), listings/manifests, node-type differences, the quick lookup table,
  and documented limitations.
- Spark-on-Kubernetes namespace fields documented in `references/data-dir-runtime-and-codeenvs.md`.

[0.1.0]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/releases/tag/skill-v0.1.0
