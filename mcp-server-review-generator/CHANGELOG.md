# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.7.0] - 2026-10-04

### Added

- `write_summary` MCP tool (`scripts/write_summary.py`): writes the checklist's Summary sheet deterministically.
  Metadata labels, the five block headers and their single shared style, status counts, per-section tallies and
  the Critical Findings / Other Must-Have rows (ID, Section, Title, Status) are computed from the section sheets,
  so the layout the reader expects no longer depends on which model wrote it. The caller supplies only a one-line
  key point per listed finding (<= 90 chars, dict order = row order) and the ordered recommendations. Bad input
  (missing/extra key point, unknown id, blank status, empty recommendations) fails before the file is touched, and
  the saved sheet is re-read with `read_checklist` and compared before it replaces the original.

### Fixed

- Critical Findings / Other Must-Have blocks are now read with `num_cols=5`, so the `Status` and `Key point`
  columns are no longer dropped. A Summary status that disagrees with the section sheet is now reported (the
  `xfail` test recording this gap is removed).

## [0.6.0] - 2026-10-02

### Added

- `analyze_checklist` MCP tool: returns the facts a v2 narrative must cite (checklist hash and default narrative
  path, counts, ids by status, root-cause groups, quick-win candidates, Needs Review items with suggested owners,
  Not Applicable items, open items, validation rules), so a drafted narrative validates first time.
  Backed by `narrative.scaffold()`.
- A v2 build with no narrative now says so: `narrative_missing` (and `narrative_warning`) in the MCP result, and a
  warning from the CLI and the log. Previously only `narrative_used: null` hinted at it.

## [0.5.0] - 2026-10-02

### Added

- A v2 build with no narrative given uses `<checklist_stem>_narrative.json` beside the checklist when it
  exists, and reports `narrative_used` (MCP result).
- A narrative may carry `checklist_sha256`; if the checklist changed since, the build warns that the prose may
  be stale. `tests/fixtures/narrative_example.json` is a synthetic schema example.

## [0.4.0] - 2026-10-02

### Added

- A v2 deck style (`--style v2`, MCP `style="v2"`): a verdict-first ~20-slide storyline (verdict, instance
  snapshot, three risks, quick wins, what we need from you, roadmap, then an appendix of non-Pass/non-N/A
  findings). The headline is Pass / applicable (N/A excluded); the TOC, section dividers, "Thank You" and
  generator-version line are dropped. v2 is the default; `--style v1` / `style="v1"` keeps the previous deck unchanged.
- `scripts/deck_analysis.py`: applicable denominator, notes parser (headline / evidence / Action), root-cause
  grouping, quick-win classifier (Fail + single setting), Needs Review split by owner keywords, N/A groups,
  and a warning when the checklist's own recommendations cite a Pass or N/A item.
- Optional `narrative.json` (`--narrative`, MCP `narrative_path`) for the human-judgment text. It is validated
  in `scripts/narrative.py`: cited IDs must exist and their status must support the claim (a Pass item needs an
  explicit `caveats` entry), risk-tile figures must appear in the cited row, owner groups must equal the Needs
  Review total. Omitted keys fall back to text derived from checklist cells.
- The MCP build tool also returns `slide_count`, `applicable_count`, `pass_count`, `quick_wins` and
  `owner_groups` for v2 builds.
- `config/deck_layout.yaml` `v2:` block (row cap, title truncation, owner keywords).

### Changed

- `python-pptx` is now a dependency, used only by the v2 module. The raw-OOXML rule still governs the v1 path.

## [0.3.1] - 2026-10-02

### Fixed

- The Other Must-Have Items slides no longer carry 3 empty trailing columns. They came from the 6-column
  table template; `make_table_slides()` now drops them (`drop_cols`, `tables.delete_columns()`) and the ID/
  Title/Status columns take the full width.

## [0.3.0] - 2026-10-02

### Changed

- The checklist item sheets now carry a `statement_short` column (right after `statement`), written by
  the checklist generator. `read_checklist.REQUIRED_ITEM_COLUMNS` requires it, so a checklist without the
  column is rejected with `ChecklistFormatError`.
- The findings table's `Statement` column and the critical-finding cards show `statement_short`
  (via `ChecklistItem.slide_statement`), falling back to the full `statement` when it's empty. Speaker
  notes still carry the full statement.

## [0.2.0] - 2026-10-02

### Changed

- The findings table's last column (now headed `Notes`) shows the checklist's `notes` column
  instead of `evidence_found` + `notes` joined, so slides carry the crisp, bulleted summary the
  checklist-review skill now writes. Falls back to `evidence_found` when `notes` is empty. The
  full `evidence_found` and `notes` still go to the slide's speaker notes, as separate lines.
- Table cells render a multi-line value as one paragraph per line (a raw newline in a single
  run doesn't break the line in PowerPoint), and the font-fit heuristic counts each line.

## [0.1.6] - 2026-10-02

### Added

- A pytest suite under `tests/` (`python3 -m pytest`; config in `pytest.ini`, dev dependencies in
  `requirements-dev.txt`). It covers checklist parsing, every `data_warnings` check, the v0.1.4/v0.1.5
  fixes as regression tests, `validate_deck` problem classes, MCP error surfacing, and a golden deck
  snapshot. The snapshot is skipped when the branding template is absent.
- An `xfail` test recording a known gap: Critical Findings / Other Must-Have blocks are read with
  `num_cols=3`, so a `Status` column in the 4th position (the checklist-review skill's standard
  `ID | Section | Title | Status | Key point` layout) is never compared against the section sheets.

## [0.1.5] - 2026-09-30

### Fixed

- The Findings & Risks chapter divider said "0 checklist items assessed" when the Summary sheet's
  Overall Status Counts block had no `Total` row. It now uses the section sheets' item count, the
  same number the Executive Summary shows. A `Total` row that disagrees with that count is reported
  in `data_warnings`.
- Critical Findings cards and the Executive Summary's Top-risk callout showed no section when the
  Summary sheet's Critical Findings block had no `Section` column. Section now falls back to the
  display name of the ID's section sheet, with one warning per block.
- Critical Findings cards showed Excel-truncated section names (e.g. "Advanced Security Options (DSS")
  when the Summary block did have a `Section` column. The card now always shows the curated display
  name of the ID's section sheet, using the block's own text only for an ID no section sheet holds.

## [0.1.4] - 2026-09-30

### Fixed

- A section sheet whose tab name had stray whitespace (e.g. the default template's
  `"Advanced Security Options (DSS "`, trailing space) showed all zeros in the Results by Section
  scorecard. `parse_section_breakdown()` strips the Summary sheet's section names, but
  `build_scorecard_rows()` looked them up by the raw tab name. Both sides are now normalized.
- Critical Findings / Other Must-Have Items silently showed blank titles, and every Other Must-Have
  item as "Needs Review", when the Summary block had no column named exactly `Title`/`Status` (the
  sample checklist's Other Must-Have block has no Status column at all, so Partial items were mislabeled).
  Missing fields now fall back to that ID's own `title`/`validation_status` from its section sheet, with
  one warning per block; the hard-coded "Needs Review" default is gone.
- Long checklist IDs wrapped mid-code in narrow table ID columns in renderers that ignore `wrap="none"`
  on table cells (e.g. LibreOffice). The ID column is now widened to fit the longest ID (up to a cap,
  taken from a prose column), and any ID still too long shrinks its own font; card IDs step down from
  12pt likewise.

### Added

- `data_warnings` in `build_platform_review_deck`'s MCP result (and printed by the CLI): Summary-vs-
  section-sheet consistency checks that structural validation can't catch — scorecard totals vs.
  Overall Status Counts, sections missing from the Per-Section Breakdown, Summary IDs not found in any
  section sheet or with a disagreeing status, unrecognized status labels, uncurated section names.
- `config/section_names.yaml` entry for the "Advanced Security Options (DSS …" section (displayed as
  "Advanced Security Options", order 5) — previously shown via the title-cased fallback as
  "Advanced Security Options (Dss".

## [0.1.3] - 2026-09-28

### Fixed

- The Methodology slide's ("How this Dataiku Platform Review was conducted") divider line cut through
  its intro sentence's text box. Root cause: that slide is cloned from the branding master's "Basic
  slide – Full text" layout, whose intro text box, divider line, and body paragraph box all keep the
  Google-Slides-authored geometry sized for the template's own short Lorem Ipsum placeholder text;
  `build_methodology_slide()` only ever substituted the text runs, never the shape geometry, so the
  real (longer) substituted sentence wrapped to more lines than the box was sized for and rendered
  straight through the divider line below it.
- The same slide's intro/divider/body content additionally sat visibly low in the slide, under a large
  leftover gap below the subtitle inherited from the same template.

  Both fixed together: `build_methodology_slide()` now grows the intro box to fit the real sentence's
  wrap, then recenters the intro/divider/body block as one group within the slide (preserving the
  template's own internal gaps between them), via a new reusable `office.text.set_shape_bounds()`
  helper (id-scoped `<a:off>`/`<a:ext>` setter, mirroring `office.tables.set_graphic_frame_bounds()`).

## [0.1.2] - 2026-09-27

### Fixed

- The Executive Summary slide's "N checklist items assessed across M sections" caption sat inside the
  KPI tile row's vertical span and was painted behind the tiles, so it was hidden. Root cause:
  `build_deck.py`'s `build_exec_summary_kpi_slide()` positioned the caption at a hardcoded
  `CONTENT_TOP + 800400` offset that didn't account for `KPI_ROW_Y`. The caption's y-position is now
  computed from `KPI_ROW_Y` itself (via new `EXEC_SUMMARY_CAPTION_HEIGHT`/`EXEC_SUMMARY_CAPTION_GAP`
  constants), so it always sits in the clear space above the tiles.

## [0.1.1] - 2026-09-27

### Fixed

- Critical Findings card slides (and the Executive Summary's "Top risk" callout) showed only each
  finding's Section name and no indication of what the check actually was. Root cause:
  `read_checklist.py` read the Summary sheet's "Critical Findings" block with `num_cols=2`, silently
  dropping the block's own `Title` column (the sheet is `ID | Section | Title`, same layout as "Other
  Must-Have Items", which already read `num_cols=3` correctly). Cards now show the check's Title as
  the bold headline with Section as supporting context beneath it.

## [0.1.0] - 2026-09-27

### Added

- First versioned release. Introduces the versioning mechanism itself (`VERSION` file,
  `common.VERSION`, `--version` flags, MCP server version metadata, and a version stamp on the
  title slide of every generated deck).
- Everything else — the checklist-to-deck generator (`build_deck.py`), structural validator
  (`validate_deck.py`), and MCP server wrapper (`mcp_server.py`) — predates versioning and is
  captured here as the 0.1.0 baseline.
