# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project purpose

This repo (`dataiku-diagnosis-toolkit`) is a **deployable Claude Code plugin** that compiles
several related capabilities for reviewing Dataiku DSS diagnosis bundles. See `README.md` for
what each piece does. The plugin as a whole is versioned via `.claude-plugin/plugin.json`'s
top-level `version` field, bumped independently of the versions carried by the individual pieces
below.

## Vendored vs. authored-here components

- **`skills/dataiku-diagnosis-reader/` + `mcp-server/`** are **vendored** from a separate upstream
  repo, `github.com/boonleeeu-dataiku/dataiku-diagnosis-reader`, which is their actual source of
  truth. That repo versions the two independently (SemVer in `SKILL.md`'s `version` frontmatter
  / `mcp-server/package.json`, each with its own `CHANGELOG.md`) per its own `CLAUDE.md`.

  To re-sync after upstream changes: diff the upstream repo's `dataiku-diagnosis-reader/` and
  `mcp-server/` directories against this repo's `skills/dataiku-diagnosis-reader/` and
  `mcp-server/` copies (content, `references/*.md`, `scripts/orient.sh`, `src/**`,
  `package.json`, version frontmatter, `CHANGELOG.md`), and port over whatever differs. Don't
  hand-edit content in these two directories here expecting it to persist — fix it upstream and
  re-sync, or the next sync will silently overwrite the fix.

- **`skills/dataiku-diagnosis-checklist-review/`** is authored directly in this repo. It has no
  upstream and currently carries no independent `version`/`CHANGELOG.md` — don't add versioning
  to it speculatively; that decision is deferred until it needs to be shared/versioned on its own.

## Security / privacy

Never commit real Dataiku diagnosis bundle data (or copy any into this repo) — see the README's
"Security / privacy" section. `.gitignore` guards against the common shapes of this
(`dku_diagnosis_*/`, `diagnosis*.zip`) as defense-in-depth, but the rule is: this toolkit ships
code and docs only, never bundle data.

## Working on the MCP server

Edits to `mcp-server/src/**/*.ts` require `npm run build` (see README's one-time setup) before
they take effect — the plugin ships TypeScript source only, no build output, no `node_modules/`.
