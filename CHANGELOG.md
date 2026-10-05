# Changelog

All notable changes to the `dataiku-diagnosis-toolkit` plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/). This tracks the plugin's own
top-level version (`.claude-plugin/plugin.json`), independent of the versions carried by
vendored components (`skills/dataiku-diagnosis-reader/`, `mcp-server-review-generator/`) — see
`CLAUDE.md`.

## [Unreleased]

## [0.22.0] - 2026-10-05

### Added

- Missing branding template no longer ends a run with no deck. The deck-builder skill now asks the user for the
  template first; if none is available (or the run is unattended) it calls the generator with
  `allow_standard_deck=true` for a standard, unbranded v2 deck and says plainly that it is not branded.
  Never a stub base deck.

### Changed

- Re-synced the vendored review generator to 0.10.0 (adds `allow_standard_deck`, and the `base_deck_used` and
  `branded` result keys; the "Base deck not found" error now names both remedies).

## [0.21.2] - 2026-10-05

### Changed

- Re-synced the vendored reader skill to 0.4.1: when `orient.sh` can't run where the bundle is, pipe it there
  (`bash -s -- <root>`) before orienting by hand.

## [0.21.1] - 2026-10-05

### Changed

- Checklist-review skill: linked-computer guidance now covers retrying a failed folder-access request, the
  stage/edit/commit/call/re-stage loop, and redacting values (not key names) in staged configs.
- Deck-builder skill: concrete render-to-image recipe for the visual check.

## [0.21.0] - 2026-10-05

### Changed

- Re-synced the vendored review generator to 0.9.1: the default v2 deck now has speaker notes. Its Findings slides
  carry each item's full Statement, Evidence and Notes, so text the table clips is still available. v1 output is
  unchanged. `finding_note_lines()` moved to `deck_shared.py`.

## [0.20.0] - 2026-10-05

### Changed

- Re-synced the vendored review generator to 0.9.0: deck styles are a registry, and the v2 deck no longer builds
  the full v1 deck to get its cover and end card. Deck output is unchanged. `tests/test_contracts.py` and
  `tests/lib/check_review_output.py` follow the helpers that moved (`data_checks`, `deck_shared`). The generator's
  `requirements.txt` already listed `python-pptx`; an existing `.venv` needs `pip install -r
  mcp-server-review-generator/requirements.txt`.

## [0.19.0] - 2026-10-04

### Changed

- Re-synced `skills/dataiku-diagnosis-reader/` to upstream 0.4.0: new `scripts/peek.py` (secret-masking view of
  bundle JSON), a stricter "Handling secrets" section, and the correct `connections.json` shape
  (`{"connections": {<name>: ...}}`). Prompted by a Codex run that guessed the shape wrong and printed a
  plaintext internal-DB password.
- Checklist-review skill: points to `peek.py`, and tells the agent to report plaintext credentials found in the
  bundle (file and kind only, never the value) with a rotate recommendation.
- Deck-builder skill: the success message now says up front that the deck needs a visual check.

## [0.18.0] - 2026-10-04

### Changed

- Re-synced `mcp-server-review-generator/` to upstream 0.8.0: `analyze_checklist`'s `shape` lists the allowed
  `tone`/`state`/`effort` values, owner suggestions cover every default-template ID prefix and more team names,
  and `analyze_checklist` / the build result report resolved paths and modified times.
- Re-synced `skills/dataiku-diagnosis-reader/` to upstream 0.3.1 (what to do when `orient.sh` can't run).
- Checklist-review and deck-builder skills: explain that the review-generator tools run on the user's
  computer (device paths, commit files before calling, container copies go stale after `write_summary`),
  advise passing `output_path`, list the narrative enum values (`state`, `tone`, `effort`), name a team in
  `Action:` lines so owners can be suggested, point to the reader's by-hand orient fallback, and tell the agent to
  compare the reported modified times against what it wrote.
- Re-synced `mcp-server-review-generator/` to upstream 0.7.6: v2 decks no longer silently drop items with an
  unrecognised/blank status or overwrite duplicate IDs (counted as Needs Review / first kept, with warnings).
- Re-synced `mcp-server-review-generator/` to upstream 0.7.5 (shared leading-number stripper, `STACK_ORDER`
  rename, shared default constants; no deck-output change).
- Hygiene pass: removed stale reader-MCP-era wording from README / checklist-review skill description,
  regenerated the eval mock tool schema (now all 4 tools), removed the obsolete
  `docs/upstream-reader-spec.md`.
- Re-synced `mcp-server-review-generator/` to upstream 0.7.4 (dead-code removal, config parsed once,
  v2-specific manual QA checklist; see its CHANGELOG).
- Small trims: one-server loop in `scripts/refresh-eval-tool-schemas.sh`, redundant `.gitignore` line,
  hoisted a test import.

## [0.17.1] - 2026-10-04

### Changed

- Re-synced `skills/dataiku-diagnosis-reader/` to upstream 0.3.0 (secrets section, shorter description,
  trimmed quick lookup, `orient.sh` first when triaging).
- `dataiku-diagnosis-checklist-review`: Secrets section now points at the reader's "Handling secrets"
  instead of carrying its own rules.
- Codex companion: host-specific `validated_by` label and version-lookup adaptation.

## [0.17.0] - 2026-10-04

### Changed

- `dataiku-diagnosis-checklist-review`: defines "must-have" as `priority == must_have`; reads each row's
  `insufficient_evidence_handling` before deciding; fixed `validated_by` string; one notes budget (320
  chars, bullets <= 80); stop rule for unverified node types; final self-check; linked-computer steps
  gathered into one block; version-lookup procedure moved from `calibrations.md` into the skill;
  secrets guidance made self-contained.
- `calibrations.md`: judgment only. An attached cluster with no containerized config is now an explicit
  **Fail**; the config-variety rule is stated precisely; item ids are examples, not keys.
- `dataiku-review-deck-builder`: narrative key list replaced by a pointer to `analyze_checklist`'s `shape`;
  host-neutral tool loading; machine-specific path reference removed.
- `dataiku-codex-workflow`: dropped facts duplicated from the task skills.
- `docs/upstream-reader-spec.md` §6: reader skill hygiene changes to make upstream.

## [0.16.0] - 2026-10-04

### Removed

- `mcp-server-diagnosis-reader/` (and `scripts/start-reader.sh`, the `reader` Codex launcher, the
  `dataiku-diagnosis-reader` entries in `.mcp.json`/`mcp.json`/`.codex-plugin/plugin.json`, and the
  `reader-crash-triage` plugin eval). It only re-exposed the reader skill's docs as MCP resources
  and `orient.sh` as a `run_orient` tool; the skill and `scripts/orient.sh` (run with Bash) cover both.
  The plugin no longer needs Node.js/npm. Removed upstream too.

### Changed

- `dataiku-diagnosis-checklist-review`: orient step runs the reader's `scripts/orient.sh` instead of
  `run_orient`; the no-skills fallback reads the reader's `SKILL.md` and `references/` directly.
- Re-synced `skills/dataiku-diagnosis-reader/CHANGELOG.md` (dropped the MCP versioning note).

## [0.15.3] - 2026-10-04

### Fixed

- Re-synced `mcp-server-review-generator` to upstream v0.7.3: narrative `risk1`/`risk2`/`risk3` titles now get the
  "Risk N:" lead added when missing, so slides 4-6 are always labelled.

## [0.15.2] - 2026-10-04

### Changed

- `dataiku-diagnosis-checklist-review`: never print secrets (parse selected keys only, don't read stray notes
  files); never pick a checklist among similar templates; search `dip.properties` for advanced-security keys;
  bracketed `[ERROR]` log grep with time windows; full SCALE-008 rule (3x config folder, dead zone, jek/fek);
  `WebFetch` fallback for the version lookup; cleaner Not Applicable headline wording.
- `dataiku-review-deck-builder`: ask for the customer name instead of inferring it; narrative figures must be
  quoted from checklist cells, not self-tallied; `risk1`-`risk3` titles must carry their "Risk N: " prefix.

## [0.15.1] - 2026-10-04

### Fixed

- Re-synced `mcp-server-review-generator` to upstream v0.7.2: a `risk3` card whose `ids` is a string (allowed by
  the narrative shape) no longer fails the deck build with `KeyError: 'S'`.

## [0.15.0] - 2026-10-04

### Added

- Re-synced `mcp-server-review-generator` to upstream v0.7.1: a narrative with a wrong-typed field (a list where
  a string is expected, e.g. `risk2.positives`) is now rejected with every offending field named by path instead
  of a bare type error, and `analyze_checklist` returns a `shape` map of the expected types.

### Changed

- `dataiku-review-deck-builder`: the narrative key list now states field types, and says to fix the field named
  in a rejection rather than reading the generator's source.

- `dataiku-diagnosis-checklist-review`: the version-currency check now requires an extended web search plus a
  look for the next major; `diag.txt` (`lsblk` ROTA) is a named source for SSD checks; new calibrations make
  GenAI feature-conditional checks Not Applicable when the feature is unused, say to search for a hinted
  setting's leaf key before calling it absent, and treat `jekSettings.maxRunningJobs=0` as a Fail and
  HDFS connection-detail sanity findings as Partial.
- Default checklist template: GENAI-003 `parameter_hint` now points at
  `generativeAISettings > llmTraceSettings > traceExplorerDefaultWebApp`.

## [0.14.0] - 2026-10-03

### Added

- Re-synced `mcp-server-review-generator` to upstream v0.7.0: a new `write_summary` tool writes the checklist's
  Summary sheet deterministically (metadata, block headers and their one shared style, counts, per-section
  tallies and finding rows come from the section sheets), so its layout no longer varies with the model that
  wrote it. Critical Findings / Other Must-Have blocks are now read with all five columns, so a Summary status
  that disagrees with the section sheet is reported.

### Changed

- `dataiku-diagnosis-checklist-review` step 6 now has Claude call `write_summary` with a key point per must-have
  finding and the ordered recommendations, instead of hand-writing the sheet. The layout stays documented as the
  fallback if the tool is unavailable. `dataiku-review-deck-builder` notes the Summary must be written first.
- `tests/lib/check_review_output.py` also checks the Summary's block headers, counts and finding ids against the
  section sheets; `tests/test_contracts.py` pins the skill to `write_summary`'s parameters.

## [0.13.0] - 2026-10-02

### Added

- Re-synced `mcp-server-review-generator` to upstream v0.6.0: a new `analyze_checklist` tool returns the facts a
  v2 narrative must cite (checklist hash and narrative path, Needs Review and Not Applicable ids, quick-win
  candidates, validation rules), and a v2 build with no narrative now returns `narrative_missing` /
  `narrative_warning` (the CLI warns too).

### Changed

- `dataiku-review-deck-builder` now has Claude call `analyze_checklist` before drafting the narrative, and treat
  `narrative_missing` as a prompt to draft one and rebuild.

## [0.12.0] - 2026-10-02

### Changed

- `dataiku-review-deck-builder`: drafting the v2 `narrative.json` is now a required step whenever Claude runs
  the skill (finalize checklist, draft narrative from that bundle's rows, record `checklist_sha256`, then build;
  fix and rebuild if the tool rejects it; report whether `narrative_used`). Only a plain script run with no LLM
  may build without one. Previously this was guidance a run could skip, giving a generic fallback deck.
- `dataiku-diagnosis-checklist-review`: when the user also asks for a deck, it hands off to the deck builder
  and its narrative step instead of building without one.

### Added

- Contract tests that fail if either skill drops the narrative requirement.

## [0.11.0] - 2026-10-02

### Changed

- Re-synced `mcp-server-review-generator` to upstream v0.5.0: v2 is the default style, a v2 build
  auto-discovers `<checklist_stem>_narrative.json` beside the checklist, and warns when the checklist changed
  since the narrative was written. `*_narrative.json` is gitignored (it holds customer findings).
- The deck-builder skill now states that the reviewer who owns the checklist owns the narrative.

## [0.10.0] - 2026-10-02

### Added

- Verdict-first "v2" Platform Review deck: re-synced `mcp-server-review-generator` to upstream v0.4.0, adding
  `style="v2"` (now the default; `"v1"` keeps the old deck) and an optional `narrative_path` to `build_platform_review_deck`. The `dataiku-review-deck-builder`
  skill now asks for v2 and drafts the `narrative.json`, which the tool validates against item statuses.
- `python-pptx` is a new dependency of the review generator (v2 only); the launcher reinstalls on the next start.

### Changed

- The generator sync also picks up upstream v0.3.1 (Other Must-Have Items drops empty trailing columns).

## [0.9.0] - 2026-10-02

### Changed

- Updated the bundled `checklist_template.xlsx`: every item sheet gains a `statement_short` column
  (a one-sentence, slide-ready rewrite of `statement`).
- Re-synced `mcp-server-review-generator` to upstream v0.3.0: `statement_short` is now a required
  checklist column, and the deck's findings table and critical-finding cards show it (falling back to
  `statement` when empty). Speaker notes keep the full statement.

## [0.8.0] - 2026-10-02

### Changed

- `dataiku-diagnosis-checklist-review`: the `notes` column is now a crisp, slide-ready summary (a
  headline plus up to 3 `•` bullets, ~320 characters, no file paths), so a downstream deck can use
  it on its own. `evidence_found` stays the detailed audit trail (paths, keys, log lines). The
  Summary `Key point` column is held to one short line too.
- `tests/lib/check_review_output.py` lints `notes` for length, bullet count and file paths.
- Re-synced `mcp-server-review-generator` to upstream v0.2.0: the deck's findings table now shows
  `notes` only (falling back to `evidence_found` when empty), multi-line cells render as one
  paragraph per line, and speaker notes list Evidence and Notes separately.

## [0.7.0] - 2026-10-02

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
