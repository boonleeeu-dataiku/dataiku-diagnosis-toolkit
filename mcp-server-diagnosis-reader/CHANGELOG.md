# Changelog

All notable changes to `dataiku-diagnosis-reader-mcp` are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this package
adheres to [Semantic Versioning](https://semver.org/). The version tracked here is the one in
`package.json` — the two must always match.

Versioning is scoped to this directory (`mcp-server-diagnosis-reader/`) only, and is independent
of the `dataiku-diagnosis-reader/` skill package's own version — see `../CLAUDE.md`. Bump this
package's version when `src/**` changes (tool/resource contracts, behavior); editing
`references/*.md` or `scripts/orient.sh` in the skill package needs no version bump here, since
those are read from disk at runtime.

## [0.2.2] - 2026-10-02

### Fixed

- The server's MCP `initialize` response reported a stale hardcoded version (`0.1.0`). It now
  reads the version from `package.json` at startup, so the two can't drift. A test asserts they
  match.

## [0.2.1] - 2026-10-02

Dev tooling only — no change to `src/**`, tool/resource contracts, or server behavior.

### Added

- An `npm test` suite (`node:test`, no new dependencies) in `test/`, run against `dist/` over stdio
  JSON-RPC. It covers path containment (including symlink and prefix-sibling escapes), `safe_read`
  caps, filtering and binary refusal, `run_orient` on design/automation bundles, and resource-list
  sync with `references/*.md`.
- Synthetic fixture bundles under `test/fixtures/bundles/`. `scripts/smoke-test.mjs` now defaults
  to one of them when no bundle root is passed.

## [0.2.0] - 2026-09-27

### Changed

- Renamed this package's directory from `mcp-server/` to `mcp-server-diagnosis-reader/` for
  clarity. No change to tool/resource contracts or server behavior, but **breaking for any
  external MCP client config** (Claude Desktop, Cursor, etc.) with an absolute path hardcoded to
  the old `mcp-server/dist/index.js` — update those paths to
  `mcp-server-diagnosis-reader/dist/index.js`.

## [0.1.0] - 2026-09-18

### Added

- Initial MCP server: exposes the skill's `SKILL.md` + `references/*.md` as resources, and
  `run_orient` (wraps `scripts/orient.sh`) and `safe_read` (bounded, size/line-capped file
  read/grep) as tools.

[0.2.2]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/compare/mcp-server-diagnosis-reader-v0.2.1...mcp-server-diagnosis-reader-v0.2.2
[0.2.1]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/compare/mcp-server-diagnosis-reader-v0.2.0...mcp-server-diagnosis-reader-v0.2.1
[0.2.0]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/compare/mcp-server-v0.1.0...mcp-server-diagnosis-reader-v0.2.0
[0.1.0]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/releases/tag/mcp-server-v0.1.0
