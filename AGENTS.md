# Codex guidance for this repository

This repository packages skills and two local MCP servers for reading Dataiku DSS diagnosis bundles, reviewing checklist workbooks, and generating Platform Review decks. Read `README.md` for the component overview and `CODEX_SETUP.md` for Codex installation and runtime details. When performing a diagnosis review or building a deck, follow the relevant task skill and `codex-skills/dataiku-codex-workflow/SKILL.md`.

## Strict Codex-only edit scope

- Never attempt to modify code, instructions, configuration, documentation, or assets that Claude uses. Read shared files when needed for context, but treat them as read-only.
- Make changes only to files used exclusively by Codex. In this repository, those are `AGENTS.md`, `CODEX_SETUP.md`, `codex-skills/`, root `plugin.json` and `mcp.json`, `.codex-plugin/`, and `scripts/codex-start.sh`. New files must also be clearly Codex-only and placed with the Codex integration.
- In particular, do not edit `CLAUDE.md`, `.claude/`, `.claude-plugin/`, `.mcp.json`, `README.md`, `skills/`, either `mcp-server-*/` directory, `scripts/start-reader.sh`, `scripts/start-review-generator.sh`, or shared root files such as `.gitignore`. Do not sync changes from upstream into those shared paths from Codex.
- Before editing, check every intended target against this scope. If a requested fix requires a Claude-used or shared file, explain that dependency and stop before changing it. Do not work around this rule by editing a shared file indirectly through a build, generated output, or another checkout.

## Component ownership

- `skills/dataiku-diagnosis-reader/` and `mcp-server-diagnosis-reader/` are vendored from `github.com/boonleeeu-dataiku/dataiku-diagnosis-reader`. That repository is their source of truth and versions the skill and server independently. Their copies here are shared with Claude and are read-only for Codex changes.
- `mcp-server-review-generator/` is vendored from `github.com/boonleeeu-dataiku/dataiku-review-generator`. Its copy here is shared with Claude and is read-only for Codex changes. Its `resources/` directory contains local assets and is outside upstream syncs.
- `skills/dataiku-diagnosis-checklist-review/` and `skills/dataiku-review-deck-builder/` are authored here. They have no separate release version or changelog; do not add either speculatively.
- `codex-skills/dataiku-codex-workflow/`, root `plugin.json` and `mcp.json`, `.codex-plugin/plugin.json`, `scripts/codex-start.sh`, and `CODEX_SETUP.md` provide Codex integration. Make Codex changes within these files and `AGENTS.md` only.

## Privacy and local assets

- Never commit or copy a real customer diagnosis bundle into this repository. The plugin ships code and documentation, not customer data. The `.gitignore` patterns are only a safeguard.
- `mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx` is a manually supplied, gitignored internal brand asset because it exceeds GitHub's file size limit. A fresh install may need an explicit `base_deck_path`; see `CODEX_SETUP.md`.
- The gitignored sample completed checklist under `mcp-server-review-generator/resources/` is a local demo artifact, not a runtime input or a file to sync from upstream.

## Build and verification

- The reader server is TypeScript and the review generator is Python. Both are shared components; do not edit or rebuild them as part of a Codex-only change. Neither their dependencies nor their generated output belongs in a commit.
- Codex uses `scripts/codex-start.sh` to copy server source into writable `PLUGIN_DATA` and run the existing server launchers. An installed plugin is a cached copy of this repository: after editing plugin files, refresh or reinstall it and start a new Codex session before testing the installed behavior.
- Verify the root manifests and compatibility manifest agree on the plugin identity and server wiring. Use `CODEX_SETUP.md` for the manual installation and smoke-check procedure.
