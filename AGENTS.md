# Codex guidance for this repository

This repository packages skills and two local MCP servers for reading Dataiku DSS diagnosis bundles, reviewing checklist workbooks, and generating Platform Review decks. Read `README.md` for the component overview and `CODEX_SETUP.md` for Codex installation and runtime details. When performing a diagnosis review or building a deck, follow the relevant task skill and `codex-skills/dataiku-codex-workflow/SKILL.md`.

## Component ownership

- `skills/dataiku-diagnosis-reader/` and `mcp-server-diagnosis-reader/` are vendored from `github.com/boonleeeu-dataiku/dataiku-diagnosis-reader`. That repository is their source of truth and versions the skill and server independently. Make lasting fixes upstream, then sync its reader skill (including references, `scripts/orient.sh`, version frontmatter, and changelog) and server (`src/`, `package.json`, lockfile, and changelog) into this repo. Compare upstream and local files before syncing; do not assume the copies still match.
- `mcp-server-review-generator/` is vendored from `github.com/boonleeeu-dataiku/dataiku-review-generator`. Make lasting fixes upstream, then sync `scripts/`, `config/`, `VERSION`, `requirements.txt`, and the changelog. Its `resources/` directory contains local assets and is outside that sync.
- `skills/dataiku-diagnosis-checklist-review/` and `skills/dataiku-review-deck-builder/` are authored here. They have no separate release version or changelog; do not add either speculatively.
- `codex-skills/dataiku-codex-workflow/`, root `plugin.json` and `mcp.json`, `.codex-plugin/plugin.json`, `scripts/codex-start.sh`, and `CODEX_SETUP.md` provide Codex integration. Claude plugin configuration and instructions are maintained separately. Keep changes scoped to the host the task concerns unless a shared component must change.

## Privacy and local assets

- Never commit or copy a real customer diagnosis bundle into this repository. The plugin ships code and documentation, not customer data. The `.gitignore` patterns are only a safeguard.
- `mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx` is a manually supplied, gitignored internal brand asset because it exceeds GitHub's file size limit. A fresh install may need an explicit `base_deck_path`; see `CODEX_SETUP.md`.
- The gitignored sample completed checklist under `mcp-server-review-generator/resources/` is a local demo artifact, not a runtime input or a file to sync from upstream.

## Build and verification

- The reader server is TypeScript. After editing `mcp-server-diagnosis-reader/src/`, run `npm run build` in that server directory before testing its local entry point. Neither `node_modules/` nor `dist/` is committed.
- The review generator is Python. Changes under `mcp-server-review-generator/scripts/` need no compilation, but the server requires the local `.venv` described in `README.md`. Do not commit that environment.
- Codex uses `scripts/codex-start.sh` to copy server source into writable `PLUGIN_DATA` and run the existing server launchers. An installed plugin is a cached copy of this repository: after editing plugin files, refresh or reinstall it and start a new Codex session before testing the installed behavior.
- For Codex-only work, verify the root manifests and compatibility manifest agree on the plugin identity and server wiring. Use `CODEX_SETUP.md` for the manual installation and smoke-check procedure.
