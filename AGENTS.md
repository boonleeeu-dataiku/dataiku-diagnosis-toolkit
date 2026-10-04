# Codex guidance for this repository

This repository packages skills for reading Dataiku DSS diagnosis bundles and reviewing checklist workbooks, plus one local MCP server for checklist summaries and Platform Review decks. Read `README.md` for the component overview and `CODEX_SETUP.md` for Codex installation and runtime details. When performing a diagnosis review or building a deck, follow the relevant task skill and `codex-skills/dataiku-codex-workflow/SKILL.md`.

## Strict Codex-only edit scope

- Never attempt to modify code, instructions, configuration, documentation, or assets that Claude uses. Read shared files when needed for context, but treat them as read-only.
- Make changes only to files used exclusively by Codex. In this repository, those are `AGENTS.md`, `CODEX_SETUP.md`, `codex-skills/`, root `plugin.json` and `mcp.json`, `.codex-plugin/`, and `scripts/codex-start.sh`. New files must also be clearly Codex-only and placed with the Codex integration.
- In particular, do not edit `CLAUDE.md`, `.claude/`, `.claude-plugin/`, `.mcp.json`, `README.md`, `skills/`, `mcp-server-review-generator/`, `scripts/start-review-generator.sh`, or shared root files such as `.gitignore`. Do not sync changes from upstream into those shared paths from Codex.
- Before editing, check every intended target against this scope. If a requested fix requires a Claude-used or shared file, explain that dependency and stop before changing it. Do not work around this rule by editing a shared file indirectly through a build, generated output, or another checkout.

## Component ownership

- `skills/dataiku-diagnosis-reader/` is vendored from `github.com/boonleeeu-dataiku/dataiku-diagnosis-reader`. That repository is its source of truth. Its copy here is shared with Claude and is read-only for Codex changes. It has no MCP server: read its `SKILL.md` and `references/` directly and run `scripts/orient.sh` with the shell.
- `mcp-server-review-generator/` is vendored from `github.com/boonleeeu-dataiku/dataiku-review-generator`. Its copy here is shared with Claude and is read-only for Codex changes. Its `resources/` directory contains local assets and is outside upstream syncs.
- `skills/dataiku-diagnosis-checklist-review/` and `skills/dataiku-review-deck-builder/` are authored here. They have no separate release version or changelog; do not add either speculatively.
- `codex-skills/dataiku-codex-workflow/`, root `plugin.json` and `mcp.json`, `.codex-plugin/plugin.json`, `scripts/codex-start.sh`, and `CODEX_SETUP.md` provide Codex integration. Make Codex changes within these files and `AGENTS.md` only.

## Reviewing project updates for Codex

- When asked to review project changes, assess whether Codex can load and use the updated shared skill or server through the existing plugin wiring. A shared task skill is already the source of its task rules; do not repeat those rules in Codex-only instructions.
- Change Codex-only files only for a demonstrated Codex-specific gap, such as tool discovery, file access, launcher behavior, packaging, or installation guidance. If the existing integration already covers the update, report that no Codex file change is needed.
- Distinguish source compatibility from installed behavior: an installed plugin is cached and may need refresh or reinstall plus a new session before it exposes the updated shared content.

## Privacy and local assets

- Never commit or copy a real customer diagnosis bundle into this repository. The plugin ships code and documentation, not customer data. The `.gitignore` patterns are only a safeguard.
- `skills/dataiku-diagnosis-checklist-review/resources/checklist_template.xlsx` is a tracked, bundled default checklist that must ship with the plugin; it is distinct from customer data and the gitignored sample completed checklist.
- `mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx` is a manually supplied, gitignored internal brand asset because it exceeds GitHub's file size limit. A fresh install may need an explicit `base_deck_path`; see `CODEX_SETUP.md`.
- The gitignored sample completed checklist under `mcp-server-review-generator/resources/` is a local demo artifact, not a runtime input or a file to sync from upstream.

## Build and verification

- The review generator is Python and a shared component; do not edit or rebuild it as part of a Codex-only change. Its dependencies and generated output do not belong in a commit.
- Codex uses `scripts/codex-start.sh` to copy server source into writable `PLUGIN_DATA` and run the existing server launcher. An installed plugin is a cached copy of this repository: after editing plugin files, refresh or reinstall it and start a new Codex session before testing the installed behavior.
- Verify the root manifests and compatibility manifest agree on the plugin identity and server wiring. Use `CODEX_SETUP.md` for the manual installation and smoke-check procedure.
