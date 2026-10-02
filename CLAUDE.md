# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project purpose

This repo (`dataiku-diagnosis-toolkit`) is a **deployable Claude Code plugin** that compiles
several related capabilities for reviewing Dataiku DSS diagnosis bundles. See `README.md` for
what each piece does. The plugin as a whole is versioned via `.claude-plugin/plugin.json`'s
top-level `version` field, bumped independently of the versions carried by the individual pieces
below.

The repo also carries `.claude-plugin/marketplace.json`, making it self-hostable as its own
single-plugin marketplace (`dataiku-local`) — see README's [Installation](README.md#installation)
section for the `/plugin marketplace add` / `/plugin install` flow this enables, both locally and
from GitHub.

## Plugin-level version bumps

Whenever the plugin's top-level version is bumped, update it in **all four** of these files
together — they must always carry the same value:

1. `.claude-plugin/plugin.json` — `version` (Claude plugin manifest)
2. `.claude-plugin/marketplace.json` — `plugins[0].version` (mirrors the plugin manifest)
3. `plugin.json` (repo root) — `version` (Codex's primary manifest)
4. `.codex-plugin/plugin.json` — `version` (Codex plugin manifest)

Also add a corresponding entry to the top-level `CHANGELOG.md`. This is independent of the
versions carried by the vendored components (see below) and by the two authored-here skills,
which have none.

## Vendored vs. authored-here components

- **`skills/dataiku-diagnosis-reader/` + `mcp-server-diagnosis-reader/`** are **vendored** from a
  separate upstream repo, `github.com/boonleeeu-dataiku/dataiku-diagnosis-reader`, which is their
  actual source of truth. That repo versions the two independently (SemVer in `SKILL.md`'s
  `version` frontmatter / `mcp-server-diagnosis-reader/package.json`, each with its own
  `CHANGELOG.md`) per its own `CLAUDE.md`. Note: upstream's directory is also named
  `mcp-server-diagnosis-reader/` as of its rename from `mcp-server/` — both repos stay in sync on
  the name, so re-syncing needs no path mapping.

  To re-sync after upstream changes: diff the upstream repo's `dataiku-diagnosis-reader/` and
  `mcp-server-diagnosis-reader/` directories against this repo's `skills/dataiku-diagnosis-reader/`
  and `mcp-server-diagnosis-reader/` copies (content, `references/*.md`, `scripts/orient.sh`,
  `src/**`, `test/**`, `scripts/smoke-test.mjs`, `package.json`, version frontmatter,
  `CHANGELOG.md`), and port over whatever differs.
  Don't hand-edit content in these two directories here expecting it to persist — fix it upstream
  and re-sync, or the next sync will silently overwrite the fix.

- **`skills/dataiku-diagnosis-checklist-review/`** and **`skills/dataiku-review-deck-builder/`**
  are authored directly in this repo. Neither has an upstream, and neither currently carries an
  independent `version`/`CHANGELOG.md` — don't add versioning to either speculatively; that
  decision is deferred until one needs to be shared/versioned on its own.

  `skills/dataiku-diagnosis-checklist-review/resources/checklist_template.xlsx` is a bundled
  default checklist the skill falls back to when the user has no checklist of their own — unlike
  the gitignored, user-supplied/sample assets under `mcp-server-review-generator/resources/`
  (see below), this one is **tracked in git**: it's not customer data, it's small, and it must
  ship with the plugin for the default to work for anyone installing it via the marketplace.

- **`mcp-server-review-generator/`** is **vendored** from a separate upstream repo,
  `github.com/boonleeeu-dataiku/dataiku-review-generator`, which is its actual source of truth.
  That repo versions itself independently (SemVer in its own `VERSION` file, `CHANGELOG.md`, git
  tags) per its own `CLAUDE.md`.

  To re-sync after upstream changes: diff the upstream repo's `scripts/`, `config/`, `tests/`,
  `VERSION`, `CHANGELOG.md`, `requirements.txt`, `requirements-dev.txt`, and `pytest.ini` against
  this repo's `mcp-server-review-generator/` copy, and port over whatever differs. Don't hand-edit
  content here expecting it to persist — fix it upstream and re-sync, or the next sync will
  silently overwrite the fix.

  `resources/` is out of scope for this sync: the branding template is a manual, gitignored,
  user-supplied asset (see below), and the sample completed checklist
  (`dku_diagnosis_2026-07-22_checklist_review.xlsx`) is likewise gitignored here — it's a demo
  artifact for the checklist-to-deck pipeline, not referenced by any code, docs, or config, so
  there's nothing to keep in sync.

## Security / privacy

Never commit real Dataiku diagnosis bundle data (or copy any into this repo) — see the README's
"Security / privacy" section. `.gitignore` guards against the common shapes of this
(`dku_diagnosis_*/`, `diagnosis*.zip`) as defense-in-depth, but the rule is: this toolkit ships
code and docs only, never bundle data.

Separately, `mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx` (134MB) is
gitignored for a different reason — it's an internal brand asset over GitHub's 100MB file limit,
not customer data — and is never vendored in from upstream either; it's a manual, one-time,
user-supplied placement step (see README's "One-time setup").

`mcp-server-review-generator/resources/dku_diagnosis_2026-07-22_checklist_review.xlsx` is also
gitignored, for a third reason: it's a sample completed checklist with no customer data and no
runtime dependents (nothing passes it as a default `--checklist` path), so there's no reason to
carry it in the repo. It still exists locally for anyone who has it; it's just untracked.

## Working on the MCP servers

Edits to `mcp-server-diagnosis-reader/src/**/*.ts` require `npm run build` (see README's one-time
setup) before they take effect — the plugin ships TypeScript source only, no build output, no
`node_modules/`.

Edits to `mcp-server-review-generator/scripts/**/*.py` take effect immediately (no build step),
but require the one-time `.venv` setup (see README) to exist before the server can launch at all
— the plugin ships Python source only, no committed virtualenv.

Whenever Claude makes edits to `mcp-server-diagnosis-reader/` or `mcp-server-review-generator/`,
remind the user afterward to also run Codex, so Codex can pick up the changes — Codex only
adapts to Claude-side changes post-hoc (see `AGENTS.md`) and won't see these updates otherwise.

## Testing

See README's "Testing" section for the three tiers.
- **Before handing back any change**, run `scripts/test.sh fast`. It makes no model calls.
- After re-syncing from upstream, `tests/test_vendored_drift.py` confirms the copies match. It
  skips if the sibling upstream checkouts aren't on disk.
- **When you add or change a calibration** in `skills/dataiku-diagnosis-checklist-review/SKILL.md`,
  extend the eval fixtures to cover it (see `tests/fixtures/README.md`):
  1. Add the item to `EVAL_ITEM_IDS` in `tests/fixtures/build_fixtures.py`.
  2. Shape a synthetic bundle so it triggers the calibration.
  3. Record the expected answer in `tests/fixtures/expected/*.yaml`.
  4. Regenerate the fixtures.
- **When you change a skill's wording that another component depends on** (status names,
  Summary block headers, the deck tool's return keys or error text), check
  `tests/test_contracts.py`.
- Strict `xfail` tests mark known gaps (see `CHANGELOG.md` → Unreleased → Known issues).
  When you fix one, remove its marker. Strict mode makes it fail as an unexpected pass until
  you do.
- Fixtures are synthetic only. The same rule as "Security / privacy" above applies: never derive
  them from a real bundle.
- `scripts/test.sh eval` and the scripts under `tests/evals/` cost real model usage. Run them only
  when the user asks, or after a skill or model change they want checked. Don't run them as
  routine verification.

