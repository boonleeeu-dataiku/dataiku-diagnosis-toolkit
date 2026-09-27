# Dataiku Diagnosis Toolkit

A plugin for reviewing a Dataiku DSS diagnosis bundle: understanding its structure, safely
reading files from it (including very large logs/manifests), and validating it against a
checklist spreadsheet.

## What's inside

- **`skills/dataiku-diagnosis-reader/`** — teaches the anatomy of a Dataiku DSS `diagnosis.zip`
  bundle: what files/directories exist, what format each is in, and where to find specific
  information. Includes `scripts/orient.sh`, which reports node type/version, the data-dir
  mirror location, and the largest/most relevant files in a bundle. Vendored from a separate
  upstream repo — see [Versioning & maintenance](#versioning--maintenance) below.
- **`skills/dataiku-diagnosis-checklist-review/`** — evaluates a diagnosis bundle against a
  checklist spreadsheet (columns like `id`, `priority`, `check_type`, `statement`,
  `expected_value`, etc.), filling in validation results and a summary tab. Authored directly in
  this repo.
- **`mcp-server/`** — a local MCP server exposing `dataiku-diagnosis-reader`'s docs as
  resources and `run_orient` / `safe_read` as tools, for MCP-compatible agents that can't load
  Claude Skills directly (Cursor, other Claude Desktop installs, etc.). It contains no
  diagnostic logic of its own — it reads `skills/dataiku-diagnosis-reader/` from disk at
  request time via the `DATAIKU_SKILL_DIR` env var set in `.mcp.json`, and shells out to
  `orient.sh` — so the skill stays the single source of truth. Vendored alongside the reader
  skill, see below.

## One-time setup

The MCP server ships as TypeScript source only (no `node_modules/`, no build output) to keep
the plugin small and avoid shipping a build that can drift from source. After installing this
plugin, build it once:

```sh
cd mcp-server
npm install
npm run build
```

This produces `mcp-server/dist/index.js`, which `.mcp.json` points to. Requires Node.js >= 18.17
and `bash` on `PATH` (macOS/Linux native; Windows needs WSL or Git Bash, since `orient.sh` is a
shell script).

## Using it elsewhere (Cursor, another Claude Desktop, etc.)

`mcp-server/` speaks plain MCP over stdio, so any MCP-compatible client can use it — not just
Claude. Point that client's MCP config at `mcp-server/dist/index.js` the same way `.mcp.json`
does here, setting `DATAIKU_SKILL_DIR` to this plugin's `skills/dataiku-diagnosis-reader`
folder (or copy that skill folder alongside the server and let it fall back to the
sibling-directory default — see `mcp-server/README.md`).

## Security / privacy

This server only ever touches paths explicitly passed as `bundle_root`/`relative_path` by the
calling agent. **No diagnosis bundle data ships with this plugin** — never point it at, or copy
into it, real customer diagnosis bundles; treat any such bundle as private data to be supplied
by whoever is running a review, not part of the toolkit itself.

## Versioning & maintenance

This plugin's own release is versioned via `.claude-plugin/plugin.json`'s top-level `version`.

`skills/dataiku-diagnosis-reader/` and `mcp-server/` are vendored from a separate upstream repo
(`dataiku-diagnosis-reader`), which is their actual source of truth and versions each
independently (see their own `CHANGELOG.md` files and `SKILL.md`'s `version` frontmatter /
`mcp-server/package.json`). `skills/dataiku-diagnosis-checklist-review/` is authored directly
here and has no separate version. See `CLAUDE.md` for how to re-sync this plugin with upstream
changes.
