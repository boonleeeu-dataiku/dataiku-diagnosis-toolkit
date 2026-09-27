# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
