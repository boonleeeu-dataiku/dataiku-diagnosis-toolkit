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
- **`mcp-server-diagnosis-reader/`** — a local MCP server exposing `dataiku-diagnosis-reader`'s
  docs as resources and `run_orient` / `safe_read` as tools, for MCP-compatible agents that can't
  load Claude Skills directly (Cursor, other Claude Desktop installs, etc.). It contains no
  diagnostic logic of its own — it reads `skills/dataiku-diagnosis-reader/` from disk at
  request time via the `DATAIKU_SKILL_DIR` env var set in `.mcp.json`, and shells out to
  `orient.sh` — so the skill stays the single source of truth. Vendored alongside the reader
  skill, see below.
- **`skills/dataiku-review-deck-builder/`** — step 2 of the workflow: turns a completed checklist
  (produced by `dataiku-diagnosis-checklist-review`) into a branded, customer-facing Platform
  Review `.pptx` deck, via the `mcp-server-review-generator` tools below. Authored directly in
  this repo.
- **`mcp-server-review-generator/`** — a local Python MCP server exposing
  `build_platform_review_deck` and `validate_deck` tools that generate/validate the deck. Vendored
  from a separate upstream repo — see [Versioning & maintenance](#versioning--maintenance) below.

## One-time setup

The MCP server ships as TypeScript source only (no `node_modules/`, no build output) to keep
the plugin small and avoid shipping a build that can drift from source. After installing this
plugin, build it once:

```sh
cd mcp-server-diagnosis-reader
npm install
npm run build
```

This produces `mcp-server-diagnosis-reader/dist/index.js`, which `.mcp.json` points to. Requires
Node.js >= 18.17 and `bash` on `PATH` (macOS/Linux native; Windows needs WSL or Git Bash, since
`orient.sh` is a shell script).

`mcp-server-review-generator/` ships as Python source only (no committed virtualenv), for the same
reason. After installing this plugin, set it up once:

```sh
cd mcp-server-review-generator
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

This produces `mcp-server-review-generator/.venv/`, whose interpreter `.mcp.json` points to
directly. You'll also need the Dataiku branding template — an internal Dataiku brand asset, not
committed here (134MB, and not customer data — see "Security / privacy" below for why that's a
different concern from diagnosis-bundle data). Obtain it separately and place it at
`mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx`. Until that's done,
deck generation still works if you pass an explicit path to your own copy (the
`dataiku-review-deck-builder` skill will ask for one if the default path is missing).

## Using it elsewhere (Cursor, another Claude Desktop, etc.)

`mcp-server-diagnosis-reader/` speaks plain MCP over stdio, so any MCP-compatible client can use
it — not just Claude. Point that client's MCP config at `mcp-server-diagnosis-reader/dist/index.js`
the same way `.mcp.json` does here, setting `DATAIKU_SKILL_DIR` to this plugin's
`skills/dataiku-diagnosis-reader` folder (or copy that skill folder alongside the server and let
it fall back to the sibling-directory default — see `mcp-server-diagnosis-reader/README.md`).

## Security / privacy

This server only ever touches paths explicitly passed as `bundle_root`/`relative_path` by the
calling agent. **No diagnosis bundle data ships with this plugin** — never point it at, or copy
into it, real customer diagnosis bundles; treat any such bundle as private data to be supplied
by whoever is running a review, not part of the toolkit itself.

The Dataiku branding template used by `mcp-server-review-generator/` is a separate concern: it's
an internal Dataiku brand asset, not customer/bundle data, so it isn't covered by the warning
above — it's simply not committed here because of its size (134MB, over GitHub's 100MB limit),
the same reason its own upstream repo doesn't commit it either.

## Versioning & maintenance

This plugin's own release is versioned via `.claude-plugin/plugin.json`'s top-level `version`.

`skills/dataiku-diagnosis-reader/` and `mcp-server-diagnosis-reader/` are vendored from a separate
upstream repo (`dataiku-diagnosis-reader`), which is their actual source of truth and versions
each independently (see their own `CHANGELOG.md` files and `SKILL.md`'s `version` frontmatter /
`mcp-server-diagnosis-reader/package.json`). `mcp-server-review-generator/` is likewise vendored,
from `dataiku-review-generator`, versioned independently via its own `VERSION`/`CHANGELOG.md`.
`skills/dataiku-diagnosis-checklist-review/` and `skills/dataiku-review-deck-builder/` are
authored directly here and have no separate version. See `CLAUDE.md` for how to re-sync this
plugin with upstream changes.
