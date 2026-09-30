# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
