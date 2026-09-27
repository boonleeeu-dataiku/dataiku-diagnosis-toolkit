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

## [Unreleased]

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

[Unreleased]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/compare/mcp-server-diagnosis-reader-v0.2.0...HEAD
[0.2.0]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/compare/mcp-server-v0.1.0...mcp-server-diagnosis-reader-v0.2.0
[0.1.0]: https://github.com/boonleeeu-dataiku/dataiku-diagnosis-reader/releases/tag/mcp-server-v0.1.0
