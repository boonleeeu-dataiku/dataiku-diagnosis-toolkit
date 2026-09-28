# Codex setup

This repository can be installed as a local Codex plugin while keeping its Claude plugin files intact. Codex uses the root `plugin.json` and `mcp.json`; `.codex-plugin/plugin.json` is a compatibility manifest. Both configurations reuse the existing scripts and MCP servers.

## Install

From this repository, run `codex plugin marketplace list`. Codex may already discover the existing `dataiku-local` marketplace from `.claude-plugin/marketplace.json`. If it does not, run `codex plugin marketplace add /absolute/path/to/this/repo`. Then run `codex plugin add dataiku-diagnosis-toolkit@dataiku-local` and start a new Codex session.

The plugin launches two local stdio MCP servers. It needs `bash`, Node.js 18.17 or newer with `npm`, and Python 3. The Codex launcher mirrors only the server source into Codex's writable `PLUGIN_DATA` directory and runs the existing launch scripts there. The first launch installs dependencies in that directory. The Dataiku branding template is not in Git; see the main README for its one-time placement or pass an explicit `base_deck_path`.

## Verify

In a new session, ask Codex to use `dataiku-diagnosis-reader` on an extracted test bundle. It should have the `run_orient` and `safe_read` tools. For a completed checklist and branding template, ask it to use `dataiku-review-deck-builder`; it should have `build_platform_review_deck` and `validate_deck`. The `dataiku-codex-workflow` companion explains Codex-specific tool and file-access differences without changing the original task skills.

Local plugins install into a Codex cache. Refresh or reinstall the plugin after changing this repository, then use a new session to load the updated skills and tools.
