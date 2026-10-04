# Codex setup

This repository can be installed as a local Codex plugin while keeping its Claude plugin files intact. Codex uses the root `plugin.json` and `mcp.json`; `.codex-plugin/plugin.json` is a compatibility manifest. Both configurations reuse the existing scripts and MCP servers.

## Install

From this repository, run `codex plugin marketplace list`. Codex may already discover the existing `dataiku-local` marketplace from `.claude-plugin/marketplace.json`. If it does not, run `codex plugin marketplace add /absolute/path/to/this/repo`. Then run `codex plugin add dataiku-diagnosis-toolkit@dataiku-local` and start a new Codex session.

The plugin launches two local stdio MCP servers. It needs `bash`, Node.js 18.17 or newer with `npm`, and Python 3. The Codex launcher mirrors only the server source into Codex's writable `PLUGIN_DATA` directory and runs the existing launch scripts there. The first launch installs dependencies in that directory.

## Branding template

Deck generation requires `Dataiku Branding Template 2026.pptx`. This 134 MB file is gitignored and is **not included in a fresh GitHub checkout or GitHub-sourced plugin install**. The Codex launcher links its runtime `resources/` directory to the installed plugin's `mcp-server-review-generator/resources/` directory, which is where the deck tool looks by default.

For the default lookup, copy the template to:

```text
~/.codex/plugins/cache/<marketplace>/dataiku-diagnosis-toolkit/<version>/mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx
```

Use the marketplace and version shown by `codex plugin list` (the local marketplace in this repo is `dataiku-local`). If you install from a local clone that already contains the template, check this cache location first: the local install may already have copied it.

The cache can be replaced when you reinstall or update the plugin. For a durable location, keep the template outside the plugin cache and provide its absolute path in the `base_deck_path` argument when asking Codex to build a deck. Do not place the template in `PLUGIN_DATA`; that directory holds the server runtime, and its `resources/` entry points back to the installed plugin.

## Verify

In a new session, ask Codex to use `dataiku-diagnosis-reader` on an extracted test bundle. It should have the `run_orient` and `safe_read` tools. To check the bundled checklist fallback, ask for a diagnosis review without supplying a checklist, then confirm that Codex offers the default template and saves a completed workbook outside the plugin directory. For a completed checklist and branding template, ask it to use `dataiku-review-deck-builder`; it should have `analyze_checklist`, `build_platform_review_deck`, and `validate_deck`. Confirm that Codex analyzes the final checklist, saves the narrative beside it, and reports a populated `narrative_used` after the v2 build. The `dataiku-codex-workflow` companion explains Codex-specific tool and file-access differences without changing the original task skills.

Local plugins install into a Codex cache. Refresh or reinstall the plugin after changing this repository, then use a new session to load the updated skills and tools.
