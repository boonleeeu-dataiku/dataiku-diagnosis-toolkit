# Changelog

All notable changes to the `dataiku-diagnosis-toolkit` plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/). This tracks the plugin's own
top-level version (`.claude-plugin/plugin.json`), independent of the versions carried by
vendored components (`mcp-server-diagnosis-reader/`, `mcp-server-review-generator/`) — see
`CLAUDE.md`.

## [Unreleased]

### Added

- A three-tier test setup. `scripts/test.sh fast` runs the deterministic tiers; `scripts/test.sh
  eval` runs the LLM evals. See README's Testing section.
  - Unit test suites for both vendored MCP servers (via re-sync to upstream
    `mcp-server-review-generator` v0.1.6 and `mcp-server-diagnosis-reader` v0.2.2):
    `mcp-server-review-generator/tests/` (pytest, including regression tests for the v0.1.4/v0.1.5
    fixes and a golden deck snapshot) and `mcp-server-diagnosis-reader/test/` (`node:test`).
  - Toolkit-level tests in `tests/`: cross-component contracts, manifest version and path
    consistency, vendored-copy drift against the upstream checkouts, and
    `tests/lib/check_review_output.py`, a checker for completed review workbooks.
  - Synthetic eval fixtures (`tests/fixtures/`): two hand-built bundles, a trimmed 11-item eval
    checklist, and expected answers that encode the checklist-review calibrations.
  - LLM evals: `claude plugin eval` cases in `evals/` (reader crash triage; deck builder's
    missing-template and `data_warnings` handling, with mocked tools), and
    `tests/evals/run_review_eval.py` + `compare.py` for scoring checklist-review runs per item
    and comparing them against a saved baseline.

### Changed

- `dataiku-diagnosis-checklist-review` step 6 now prescribes the exact Summary-sheet layout the
  deck generator parses. That covers header texts and order, a shared header style, metadata
  labels, table columns, and literal counts rather than `COUNTIF` formulas. Before this, the
  first live eval runs showed the model wording headers freely: one run titled the counts block
  "Overall status" and dropped the per-section header, which made the Summary unreadable by
  `build_platform_review_deck`. The skill's own earlier wording, "Per-section status
  breakdown", was also never recognized by the deck generator.
- The same step now says to leave an empty Critical Findings / Other Must-Have block with only
  its header rows. The baseline eval runs showed the model writing placeholder rows like "None -
  no must-have items failed.", which the deck generator would render as a finding with ID
  "None".

### Fixed

Via `mcp-server-diagnosis-reader` re-sync to upstream v0.2.2:

- The server's MCP `initialize` response reported a stale hardcoded version (`0.1.0`). It now
  reads the version from `package.json`. Re-run `npm run build` in `mcp-server-diagnosis-reader/`
  to pick this up.

### Known issues

Surfaced by the new tests and recorded as a strict `xfail` test rather than fixed:

- The review generator reads Critical Findings / Other Must-Have Summary blocks with only 3
  columns. In the skill's `ID | Section | Title | Status | Key point` layout, a Summary status
  that disagrees with the section sheet is never reported. The fix belongs upstream in
  `dataiku-review-generator`.

## [0.6.1] - 2026-09-30

### Fixed

Via `mcp-server-review-generator` re-sync to upstream v0.1.5:

- Findings & Risks chapter divider said "0 checklist items assessed" when the Summary sheet's
  Overall Status Counts block had no `Total` row; it now uses the section sheets' item count
  (matching the Executive Summary). A disagreeing `Total` row is reported in `data_warnings`.
- Critical Findings cards and the Executive Summary's Top-risk callout showed no section when the
  Critical Findings block had no `Section` column; section now falls back to the ID's section
  sheet display name.
- Critical Findings cards showed Excel-truncated section names (e.g.
  "Advanced Security Options (DSS"); they now always use the curated section display name.

## [0.6.0] - 2026-09-30

### Added

- `build_platform_review_deck` now returns `data_warnings` — Summary vs. section-sheet
  consistency checks (scorecard totals, missing sections, unknown or disagreeing IDs/statuses,
  uncurated section names) that structural validation can't catch (via
  `mcp-server-review-generator` re-sync to upstream v0.1.4).
- `dataiku-review-deck-builder`: surfaces `data_warnings` to the user and directs fixing the
  checklist and rebuilding, rather than hand-patching the generated deck.

### Fixed

Via `mcp-server-review-generator` re-sync to upstream v0.1.4:

- Results by Section scorecard showed all zeros for a section whose tab name has stray
  whitespace (e.g. the default template's `"Advanced Security Options (DSS "`).
- Critical Findings / Other Must-Have Items showed blank titles and mislabeled items as
  "Needs Review" when the Summary block lacked a `Title`/`Status` column; they now fall back to
  the section sheet's values.
- Long checklist IDs wrapping mid-code in narrow table ID columns.
- "Advanced Security Options" section now has a curated display name instead of the title-cased
  fallback "Advanced Security Options (Dss".

## [0.5.0] - 2026-09-30

### Added

- `dataiku-diagnosis-checklist-review`: new calibration for automation-node existence /
  Design–Automation separation checks (e.g. ARCH-001) on design-node bundles. Always marked
  **Needs Review**, since a design bundle cannot confirm a separate automation node. The review
  highlights a local deployer (`config/project-deployer/`, distinguishing populated from empty;
  `config/api-deployer/` noted separately as an API-node indication) or a remote deployer
  (`deployerClientSettings.mode = REMOTE`) as indications, and otherwise states that no
  definitive configuration exists and customer verification is needed. The deployer directories
  were also added to the skill's evidence-source list.

## [0.4.0] - 2026-09-28

### Added

- Bundled default checklist template for `dataiku-diagnosis-checklist-review`
  (`skills/dataiku-diagnosis-checklist-review/resources/checklist_template.xlsx`). If the user
  doesn't have their own checklist, the skill now offers to fall back to this bundled template
  instead of hard-requiring a user-supplied file.

## [0.3.0] - 2026-09-28

### Added

- Codex plugin support alongside Claude: repo-root `plugin.json` and `mcp.json` (Codex's own
  manifests), `.codex-plugin/plugin.json`, `codex-skills/dataiku-codex-workflow/SKILL.md`,
  `scripts/codex-start.sh`, `CODEX_SETUP.md`, and `AGENTS.md` repository guidance restricting
  Codex to its own files. Codex adapts to Claude-side changes post-hoc and never edits Claude's
  skills/MCP code.
