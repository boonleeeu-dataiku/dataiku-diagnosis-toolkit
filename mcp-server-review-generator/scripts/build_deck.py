#!/usr/bin/env python3
"""Generate a branded Dataiku "Platform Review" deck (.pptx) from a
completed platform-review checklist (.xlsx).

Usage:
    python3 scripts/build_deck.py \\
        --checklist resources/checklist_template_reviewed_dku_diagnosis_2026-07-22.xlsx \\
        --customer "Acme Corp" \\
        [--logo path/to/acme_logo.png] \\
        [--output output/Acme_Corp_Platform_Review.pptx] \\
        [--rows-per-slide 4] \\
        [--include-pass-items] \\
        [--base-deck "resources/Dataiku Branding Template 2026.pptx"]

No LLM/Claude session is used at runtime -- this is a plain, rerunnable
Python script. See CLAUDE.md and config/*.yaml for the design this follows.
"""

import argparse
import logging
import mimetypes
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import common
import read_checklist
import section_names
import validate_deck
from office import notes, package, shapes, slides, tables, text

logger = logging.getLogger("build_deck")

# Slide filenames in "resources/Dataiku Branding Template 2026.pptx" (the
# default --base-deck), out of its 62-slide library. If a different base
# deck is ever supplied, these anchors must match its structure or this
# script fails fast with a clear error, rather than silently mis-editing the
# wrong slide.
TITLE_SLIDE = "slide15.xml"
TOC_SLIDE = "slide16.xml"
DIVIDER_TEMPLATE_SLIDE = "slide19.xml"       # "01." chapter-divider layout
METHODOLOGY_SLIDE = "slide27.xml"            # "Basic slide - Full text" layout
TABLE_TEMPLATE_SLIDE = "slide50.xml"         # the master's one real <a:tbl>, 6 cols
KPI_SLIDE = "slide55.xml"                    # 6-tile "Key numbers" layout
CLOSING_SLIDE = "slide60.xml"                # "Thank You."
CONTACT_SLIDE = "slide62.xml"                # footer/contact info

# Every slide in the 62-slide master except the 4 edited in place (title,
# TOC, closing, contact). This includes the slides used as clone templates
# above (19/27/50/55) -- their content is fully consumed by clones inserted
# elsewhere, so the originals are deleted same as any other unused slide,
# once all structural edits are done.
SLIDES_CONSUMED_AS_TEMPLATES = [
    f"slide{n}.xml" for n in range(1, 63)
    if f"slide{n}.xml" not in {TITLE_SLIDE, TOC_SLIDE, CLOSING_SLIDE, CONTACT_SLIDE}
]

# The 5 checklist status categories, and the color used for each everywhere
# status appears (KPI tiles, card IDs/pills, table cell text, the
# results-by-section scorecard) -- a green -> amber -> orange -> red-orange
# severity gradient. Pass/Needs Review/Partial/Not Applicable stay on the
# branding template's own theme accents (dk2/accent6/accent4 respectively);
# Fail deliberately breaks from the theme's accent4 orange (reassigned to
# Partial) into a deeper, more alarming red-orange, since it's the single
# most important signal in a risk report and the theme has no true red.
STATUS_ORDER = ["Pass", "Fail", "Partial", "Needs Review", "Not Applicable"]
STATUS_COLORS = {
    "Pass": "3EDAB2",           # theme dk2 (brand teal-green)
    "Fail": "C0392B",           # deep red-orange, off-theme by design (see above)
    "Partial": "EDAB4F",        # theme accent4 (orange)
    "Needs Review": "F8DDB9",   # theme accent6 (peach)
    "Not Applicable": shapes.TEXT_GRAY_LIGHT,  # neutral gray, not a theme "signal" color
}
STATUS_COLORS_LOWER = {k.lower(): v for k, v in STATUS_COLORS.items()}
STATUS_COL = 3  # 0-indexed column in the 6-col findings row: ID/Title/Priority/Status/Statement/Notes

# The master's table template ships sized for short, single-line quarterly
# figures (12pt header / 11pt data, 551,975 EMU rows). build_deck.py reuses
# it at taller row heights (see *_ROW_HEIGHT constants below) for
# multi-line prose, but at the native font size that prose wraps onto more
# lines than the row height holds -- PowerPoint then auto-expands the row at
# render time, pushing the table past the slide's bottom edge. Shrinking the
# font keeps wrapped text within the row heights actually declared below.
TABLE_HEADER_FONT_SIZE = 1000  # 10pt
TABLE_DATA_FONT_SIZE = 900     # 9pt

# Column widths (EMU) for each tabular use of TABLE_TEMPLATE_SLIDE's 6-column
# template, each summing to its native total width (8,334,075 EMU) so no
# table overflows the slide's right edge. ID/Priority (Findings) and ID
# (Other Must-Have) are widened beyond their original share -- see
# STATUS_COL's no-wrap columns below -- so a wrap="none" ID/Priority value
# (up to "GENAI-001", 9 chars, and "Nice to have", 12 chars, in the sample
# checklist) has room to render on one line instead of overflowing into the
# next column; Statement/Evidence & Notes (which have the most slack -- see
# cell_char_limits in config/deck_layout.yaml) give up the difference. Other
# Must-Have's ID width instead comes from its 3 always-empty trailing
# columns (see build_other_must_have_rows).
FINDINGS_WIDTHS = [850000, 1500000, 950000, 700000, 2167038, 2167037]
OTHER_MUST_HAVE_WIDTHS = [850000, 5500000, 1000000, 328025, 328025, 328025]

# Row height (EMU) sized for a guaranteed 3 wrapped lines at
# TABLE_DATA_FONT_SIZE (9pt): 3 x ~137,160 EMU/line + 2x45,720 EMU top/bottom
# cell insets + a small buffer. The previous flat 950,000 EMU was picked
# independently of the row content, and left the default 4-row table only
# ~29,000 EMU of margin above the slide's bottom edge (899,584 top + 414,675
# header + 4x950,000 rows = 5,114,259 EMU, vs. a 5,143,500 EMU slide height)
# -- virtually zero tolerance for a row needing even one extra wrapped line.
# Statement/Evidence & Notes (see FINDINGS_FONT_FIT_COLS below) shrink their
# own font instead of wrapping past this budget, so this stays a hard cap.
FINDINGS_ROW_HEIGHT = 560000
OTHER_MUST_HAVE_ROW_HEIGHT = 560000
SCORECARD_WIDTHS = [3834075, 900000, 900000, 900000, 900000, 900000]
SCORECARD_ROW_HEIGHT = 420000

# Columns that must never wrap -- short, enum/code-like values where wrapping
# only happens because the column is narrow, not because the content is
# genuinely long-form. The Status column is deliberately excluded: values
# like "Needs Review" may legitimately wrap onto two lines.
FINDINGS_NO_WRAP_COLS = [0, 2]       # ID, Priority
OTHER_MUST_HAVE_NO_WRAP_COLS = [0]   # ID
SCORECARD_NO_WRAP_COLS = [1, 2, 3, 4, 5]  # Pass/Fail/Partial/Needs Review/Not Applicable counts

# Statement/Evidence & Notes hold unbounded checklist prose that used to be
# hard-truncated with a trailing "..." at a fixed character budget -- losing
# context readers need. _fit_cell_text() below first tries to shrink the
# font (largest step in TABLE_FONT_FIT_SIZE_STEPS first) so the full text
# fits within FINDINGS_ROW_HEIGHT; real checklist evidence text can still run
# past what even the smallest (floor) size fits in that height, in which
# case the row is allowed to auto-expand (PowerPoint's normal wrap
# behavior), but only up to TABLE_FONT_FIT_MAX_LINES lines at the floor size
# -- past that, the display text (only) is truncated, capping how far any
# single outlier can blow up the slide. The full, untruncated text still
# reaches the reader either way, via that slide's speaker notes (see
# build_section_detail_slides).
FINDINGS_FONT_FIT_COLS = [4, 5]  # Statement, Evidence & Notes
TABLE_FONT_FIT_SIZE_STEPS = [900, 800, 700]  # 9pt -> 8pt -> 7pt (floor)
TABLE_FONT_FIT_MAX_LINES = 8  # hard cap on wrapped lines at the floor size

# Usable content-area geometry shared by every hand-drawn (shapes-based)
# slide, matching the branding master's own table-slide convention
# (TABLE_TEMPLATE_SLIDE's graphicFrame sits at x=359970, y=899584).
SLIDE_WIDTH = 9144000   # matches <p:sldSz cx="..."> in presentation.xml
SLIDE_HEIGHT = 5143500  # matches <p:sldSz cy="..."> in presentation.xml
CONTENT_LEFT = 360000
CONTENT_TOP = 899584
CONTENT_WIDTH = SLIDE_WIDTH - 2 * CONTENT_LEFT
CONTENT_BOTTOM_MARGIN = 250000
CONTENT_BOTTOM = SLIDE_HEIGHT - CONTENT_BOTTOM_MARGIN

# Card/tile sizing. No font-metrics library is available in this project's
# dependencies, so cards are fixed-height with hard character-limit
# truncation (see cell_char_limits in config/deck_layout.yaml), not
# variable-height/auto-fit.
CARD_HEIGHT_CRITICAL = 620000
CARD_GAP = 90000
CARD_HEIGHT_RECOMMENDATION = 580000
RECOMMENDATION_CARD_GAP = 80000
STATUS_LINE_HEIGHT = 300000
STATUS_LINE_GAP = 150000
SECTION_TABLE_ROWS_PER_SLIDE = 3  # fewer than the general default, to leave room for the status line above
KPI_ROW_Y = 1550000
KPI_TILE_HEIGHT = 1300000
EXEC_SUMMARY_CAPTION_HEIGHT = 300000
EXEC_SUMMARY_CAPTION_GAP = 150000  # clearance above the KPI tiles, so the caption never sits under them
EXEC_SUMMARY_CAPTION_Y = KPI_ROW_Y - EXEC_SUMMARY_CAPTION_GAP - EXEC_SUMMARY_CAPTION_HEIGHT
CALLOUT_Y = KPI_ROW_Y + KPI_TILE_HEIGHT + 250000
CALLOUT_HEIGHT = 850000
TITLE_FOOTER_X = CONTENT_LEFT
TITLE_FOOTER_Y = 4500000
TITLE_FOOTER_WIDTH = 6506100  # matches slide15's title/subtitle box width
TITLE_FOOTER_HEIGHT = 550000

CHAPTER_NAMES = [
    "Executive Summary",
    "Findings & Risks",
    "Recommendations & Next Steps",
]


# --------------------------------------------------------------------------
# Content shaping: checklist data -> table rows / shape content
# --------------------------------------------------------------------------

def truncate(value, limit: int) -> str:
    value = (value or "").strip()
    if len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def _fit_cell_text(text_value: str, col_width_emu: int, row_height_emu: int,
                    steps: list = TABLE_FONT_FIT_SIZE_STEPS,
                    max_lines_cap: int = TABLE_FONT_FIT_MAX_LINES,
                    side_inset_emu: int = 91440, top_bottom_inset_emu: int = 45720) -> tuple:
    """Returns (display_text, font_size) for a col_width_emu x row_height_emu
    table cell, using the same ~0.5em/char, ~1.2x line-height heuristic used
    to size FINDINGS_ROW_HEIGHT (no font-metrics library is available in
    this project's dependencies -- see CARD_HEIGHT_CRITICAL's comment).
    Tries each size in `steps` (largest first) at the row's own declared
    height; if the text still doesn't fit at the smallest size, lets the row
    expand up to max_lines_cap lines at that size instead of shrinking
    further (illegible below ~7pt); if even that isn't enough, truncates
    display_text to what fits in max_lines_cap, so one pathological outlier
    can't blow the row past what the rest of the slide budgeted for."""
    text_value = (text_value or "").strip()
    usable_w = col_width_emu - 2 * side_inset_emu
    usable_h = row_height_emu - 2 * top_bottom_inset_emu

    for size in steps:
        font_pt = size / 100
        avg_char_w = 0.5 * font_pt * 12700
        line_h = 1.2 * font_pt * 12700
        chars_per_line = max(1, int(usable_w // avg_char_w))
        max_lines = max(1, int(usable_h // line_h))
        if len(text_value) <= chars_per_line * max_lines:
            return text_value, size

    floor_size = steps[-1]
    avg_char_w = 0.5 * (floor_size / 100) * 12700
    chars_per_line = max(1, int(usable_w // avg_char_w))
    max_chars = chars_per_line * max_lines_cap
    if len(text_value) <= max_chars:
        return text_value, floor_size
    return text_value[: max(0, max_chars - 1)].rstrip() + "…", floor_size


def format_priority(priority: str) -> str:
    return "Must Have" if (priority or "").strip().lower() == "must_have" else "Nice to have"


def format_month_year(date_str) -> str:
    if not date_str:
        return ""
    s = str(date_str).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[: len(fmt) + 2], fmt).strftime("%b %Y")
        except ValueError:
            continue
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).strftime("%b %Y")
    return s


LEADING_NUMBER_RE = re.compile(r"^\s*\d+[.)]\s*")


def _strip_leading_number(value: str) -> str:
    """Recommendations in the checklist's Summary sheet are already written
    as a priority-ordered, pre-numbered list (e.g. "1. Fix ..."). Card/list
    layouts add their own numeral badge, so strip the source's own leading
    "N. " to avoid showing the number twice."""
    return LEADING_NUMBER_RE.sub("", value or "")


def _canonical_status(status: str) -> str | None:
    status = (status or "").strip().lower()
    for canon in STATUS_ORDER:
        if canon.lower() == status:
            return canon
    return None


def format_title_metadata_lines(data: read_checklist.ChecklistData) -> list:
    """Bundle/Node-Version/Report-generated as a short footer for the title
    slide, mirroring how the reference deck carries this metadata directly
    on its title slide instead of a dedicated table slide."""
    lines = []
    bundle = data.bundle_metadata.get("Bundle")
    if bundle:
        lines.append(f"Bundle: {truncate(str(bundle), 90)}")
    node_version = data.bundle_metadata.get("Node / Version")
    if node_version:
        lines.append(f"Node / Version: {truncate(str(node_version), 90)}")
    report_generated = data.bundle_metadata.get("Report generated")
    if report_generated:
        lines.append(f"Report generated: {truncate(str(report_generated), 60)}")
    lines.append(f"Generated by Dataiku Review Generator v{common.VERSION}")
    return lines


def build_overall_status_counts(data: read_checklist.ChecklistData) -> dict:
    return {k: data.overall_counts.get(k, 0) for k in STATUS_ORDER}


def build_scorecard_rows(data: read_checklist.ChecklistData, ordered_sections: list) -> list:
    breakdown_by_section = {b["section"]: b["counts"] for b in data.per_section_breakdown}
    rows = []
    totals = {status: 0 for status in STATUS_ORDER}
    for sec in ordered_sections:
        counts = breakdown_by_section.get(sec["sheet_tab_name"], {})
        row = [sec["display"]]
        for status in STATUS_ORDER:
            v = int(counts.get(status, 0))
            row.append(str(v))
            totals[status] += v
        rows.append(row)
    if rows:
        rows.append(["Total"] + [str(totals[status]) for status in STATUS_ORDER])
    return rows


def _finding_note_lines(item) -> list:
    """Full, untruncated Statement/Evidence & Notes for one checklist item,
    as speaker-notes paragraphs (a trailing "" is a blank-paragraph
    separator before the next item). Shared by both a section's card layout
    and its table fallback -- see build_section_detail_slides -- so every
    findings slide's notes read the same way regardless of which layout its
    visible content ended up using."""
    comments = " ".join(x for x in [item.evidence_found, item.notes] if x)
    return [
        f"{item.id}: {item.title}",
        f"Statement: {(item.statement or '—').strip()}",
        f"Evidence & Notes: {(comments or '—').strip()}",
        "",
    ]


def build_findings_rows(items: list) -> list:
    """Statement/Evidence & Notes are left untruncated -- make_table_slides()
    shrinks their font per-cell to fit instead (see FINDINGS_FONT_FIT_COLS),
    so a long value only loses context to a trailing "..." in the rare case
    even that can't make it fit (see _fit_cell_text()'s docstring) -- the
    full text still reaches speaker notes either way."""
    rows = []
    for item in items:
        comments = " ".join(x for x in [item.evidence_found, item.notes] if x)
        rows.append([
            item.id,
            truncate(item.title, 60),
            format_priority(item.priority),
            item.validation_status or "—",
            (item.statement or "").strip(),
            comments.strip(),
        ])
    return rows


def build_other_must_have_rows(data: read_checklist.ChecklistData, cell_limits) -> list:
    rows = []
    for entry in data.other_must_have:
        rows.append([
            entry.get("id", ""),
            truncate(entry.get("title", ""), 90),
            entry.get("status", "") or "Needs Review",
            "", "", "",
        ])
    return rows


def _finding_title_and_section(entry: dict) -> tuple[str, str]:
    """The Critical Findings/Other Must-Have blocks' own Title column (a
    short, human-readable check name -- e.g. "External PostgreSQL Runtime
    Database") is what actually tells a reader what failed; Section is
    supporting context, not a substitute for it. Falls back to whatever
    non-id/-section column exists, for a Summary sheet laid out without a
    Title column."""
    section = entry.get("section", "")
    if "title" in entry:
        return entry["title"], section
    fallback_key = next((k for k in entry if k not in ("id", "section")), None)
    return (entry.get(fallback_key, "") if fallback_key else ""), section


def build_critical_finding_blocks(data: read_checklist.ChecklistData) -> list:
    """Full, untruncated (id, title, section) triples -- build_critical_finding_card_slides()
    truncates the title for the visible card itself, and keeps a full copy for speaker
    notes."""
    blocks = []
    for entry in data.critical_findings:
        title, section = _finding_title_and_section(entry)
        blocks.append((entry.get("id", ""), title, section))
    return blocks


def build_top_risk(data: read_checklist.ChecklistData, cell_limits):
    """The Executive Summary's single "Top risk" callout: the first critical
    finding, in list order. The checklist schema doesn't document this list
    as severity-ordered (only `recommendations` is documented as
    priority-ordered) -- this is a known assumption, worth revisiting if it
    ever surfaces a poor headline finding in practice."""
    if not data.critical_findings:
        return None
    entry = data.critical_findings[0]
    limit = cell_limits.get("critical_finding_card", 150)
    title, section = _finding_title_and_section(entry)
    return entry.get("id", ""), truncate(title, limit), section


# --------------------------------------------------------------------------
# Slide-building helpers
# --------------------------------------------------------------------------

def set_multi_run_title(slide_xml: str, old_runs: list, new_title: str) -> str:
    """Titles sometimes split across several adjacent <a:t> runs (e.g. a
    chapter-title sentence with a differently-colored middle phrase). Put the
    full new title in the first run and blank the rest, so no stale fragment
    survives next to it."""
    slide_xml = text.replace_text_run(slide_xml, old_runs[0], new_title, required=True)
    for extra in old_runs[1:]:
        slide_xml = text.replace_text_run(slide_xml, extra, "", required=False)
    return slide_xml


def make_table_slides(work_dir: Path, template_xml: str, template_rels: str | None,
                       header_row_count: int, rows_per_page: list, after: str,
                       title_new_fn, header_values: list, column_widths: list, row_height: int,
                       status_col: int | None = None, status_color_map: dict | None = None,
                       no_wrap_cols: list[int] | None = None, font_fit_cols: list[int] | None = None,
                       header_font_size: int = TABLE_HEADER_FONT_SIZE,
                       data_font_size: int = TABLE_DATA_FONT_SIZE) -> list:
    """Clone template_xml (TABLE_TEMPLATE_SLIDE's snapshot) once per page in
    rows_per_page, resize its table to column_widths/row_height, fill its
    data rows (optionally recoloring status_col via status_color_map, an
    N-way status(lowercased)->hex lookup; disabling wrap on no_wrap_cols; and
    shrinking font_fit_cols' font per-cell via _fit_cell_text(), for any
    value too long to fit column_widths/row_height at data_font_size -- with
    a capped, rare fallback to truncation for pathologically long outliers,
    see _fit_cell_text()'s docstring), relabel its header, set its title via
    title_new_fn(page_idx, total_pages), and insert each clone after the
    previous one (starting after `after`). Returns the new slide filenames,
    in order."""
    new_filenames = []
    tmpl_tbl = tables.set_column_widths(tables.extract_table(template_xml), column_widths)
    if no_wrap_cols:
        tmpl_tbl = tables.set_table_no_wrap(tmpl_tbl, no_wrap_cols)
    row_template = tables.set_row_height(tables.row_template(tmpl_tbl, header_row_count=header_row_count), row_height)
    row_template = tables.set_font_size(row_template, data_font_size)

    def _finalize_row(values):
        values = list(values)
        font_sizes = {}
        if font_fit_cols:
            for col in font_fit_cols:
                display_text, size = _fit_cell_text(values[col], column_widths[col], row_height)
                values[col] = display_text
                if size != data_font_size:
                    font_sizes[col] = size
        row_xml = tables.fill_row(row_template, values)
        if status_col is not None and status_color_map:
            row_xml = tables.style_cell_text_by_value(row_xml, status_col, values[status_col], status_color_map)
        for col, size in font_sizes.items():
            row_xml = tables.set_cell_font_size(row_xml, col, size)
        return row_xml

    insert_after = after
    total_pages = len(rows_per_page)
    for page_idx, page_rows in enumerate(rows_per_page, start=1):
        new_filename = slides.duplicate_slide_from_xml(work_dir, template_xml, template_rels, after=insert_after)
        slide_path = work_dir / "ppt" / "slides" / new_filename
        slide_xml = slide_path.read_text(encoding="utf-8")
        slide_xml = text.replace_text_run(slide_xml, "Table", title_new_fn(page_idx, total_pages))

        tbl = tables.set_column_widths(tables.extract_table(slide_xml), column_widths)
        if no_wrap_cols:
            tbl = tables.set_table_no_wrap(tbl, no_wrap_cols)
        tbl = tables.set_font_size(tbl, header_font_size)  # header row's size; data rows below are replaced wholesale
        rows_xml = "".join(_finalize_row(v) for v in page_rows)
        new_tbl = tables.replace_data_rows(tbl, rows_xml, header_row_count=header_row_count)
        new_tbl = tables.replace_header_row(new_tbl, header_values)
        slide_xml = tables.replace_table(slide_xml, new_tbl)

        slide_path.write_text(slide_xml, encoding="utf-8")
        new_filenames.append(new_filename)
        insert_after = new_filename
    return new_filenames


def build_scorecard_slide(work_dir: Path, template_xml: str, template_rels: str | None,
                           after: str, rows: list) -> str:
    """Clone TABLE_TEMPLATE_SLIDE's snapshot into the "Results by Section"
    scorecard: one row per checklist section plus a Total row, one column
    per status, each column unconditionally tinted its status color -- the
    reference deck's own recipe for per-section breakdown (a static table,
    not a chart)."""
    new_filename = slides.duplicate_slide_from_xml(work_dir, template_xml, template_rels, after=after)
    slide_path = work_dir / "ppt" / "slides" / new_filename
    slide_xml = slide_path.read_text(encoding="utf-8")
    slide_xml = text.replace_text_run(slide_xml, "Table", "Results by Section")

    tmpl_tbl = tables.set_column_widths(tables.extract_table(template_xml), SCORECARD_WIDTHS)
    tmpl_tbl = tables.set_table_no_wrap(tmpl_tbl, SCORECARD_NO_WRAP_COLS)
    row_template = tables.set_row_height(tables.row_template(tmpl_tbl, header_row_count=1), SCORECARD_ROW_HEIGHT)
    row_template = tables.set_font_size(row_template, TABLE_DATA_FONT_SIZE)

    tbl = tables.set_column_widths(tables.extract_table(slide_xml), SCORECARD_WIDTHS)
    tbl = tables.set_table_no_wrap(tbl, SCORECARD_NO_WRAP_COLS)
    tbl = tables.set_font_size(tbl, TABLE_HEADER_FONT_SIZE)
    rows_xml = tables.build_rows_xml(row_template, rows)
    new_tbl = tables.replace_data_rows(tbl, rows_xml, header_row_count=1)
    new_tbl = tables.replace_header_row(new_tbl, ["Section"] + STATUS_ORDER)
    for i, status in enumerate(STATUS_ORDER, start=1):
        new_tbl = tables.style_column_text(new_tbl, i, STATUS_COLORS[status], header_row_count=1, bold=False)
    slide_xml = tables.replace_table(slide_xml, new_tbl)

    slide_path.write_text(slide_xml, encoding="utf-8")
    return new_filename


def build_critical_finding_card_slides(work_dir: Path, template_xml: str, template_rels: str | None,
                                        after: str, blocks: list, per_slide: int, cell_limits) -> list:
    """Card-list version of the Critical Findings slides: clone
    TABLE_TEMPLATE_SLIDE, drop its native table, and stack one
    shapes.card_list_row per must-have item currently failing -- the check's
    own title as the bold headline, its section as supporting context below.
    The card itself still truncates the title to a fixed budget (no
    font-metrics library is available to shrink-to-fit a fixed-height card --
    see CARD_HEIGHT_CRITICAL's comment); the full text goes into that slide's
    speaker notes instead, so nothing is actually lost."""
    limit = cell_limits.get("critical_finding_card", 150)
    pages = tables.paginate(blocks, per_slide)
    new_filenames = []
    insert_after = after
    total_pages = len(pages)
    for page_idx, page_blocks in enumerate(pages, start=1):
        slide_title = "Critical Findings" + (f" ({page_idx}/{total_pages})" if total_pages > 1 else "")
        slide_xml = text.replace_text_run(template_xml, "Table", slide_title)
        slide_xml = text.remove_graphic_frame(slide_xml)

        shape_id = text.next_shape_id(slide_xml)
        parts = []
        note_lines = []
        y = CONTENT_TOP
        for finding_id, finding_title, section in page_blocks:
            card_xml, shape_id = shapes.card_list_row(
                shape_id, CONTENT_LEFT, y, CONTENT_WIDTH, CARD_HEIGHT_CRITICAL,
                id_text=finding_id, id_color=STATUS_COLORS["Fail"],
                title_text=truncate(finding_title, limit), description_text=section,
            )
            parts.append(card_xml)
            y += CARD_HEIGHT_CRITICAL + CARD_GAP
            note_lines += [f"{finding_id}: {finding_title.strip()} ({section})" if section else f"{finding_id}: {finding_title.strip()}", ""]
        slide_xml = text.insert_shape(slide_xml, "".join(parts))

        new_filename = slides.duplicate_slide_from_xml(work_dir, slide_xml, template_rels, after=insert_after)
        notes.add_notes(work_dir, new_filename, note_lines)
        new_filenames.append(new_filename)
        insert_after = new_filename
    return new_filenames


def build_recommendation_card_slides(work_dir: Path, template_xml: str, template_rels: str | None,
                                      after: str, recommendations: list, per_slide: int, cell_limits) -> list:
    """Numbered card-list version of the Recommendations slides. Each card
    still truncates to a fixed budget (see build_critical_finding_card_slides'
    docstring for why); the full recommendation text goes into that slide's
    speaker notes."""
    pages = tables.paginate(recommendations, per_slide)
    new_filenames = []
    insert_after = after
    total_pages = len(pages)
    limit = cell_limits.get("recommendation_card", 120)
    counter = 1
    for page_idx, page_items in enumerate(pages, start=1):
        title = "Recommendations" + (f" ({page_idx}/{total_pages})" if total_pages > 1 else "")
        slide_xml = text.replace_text_run(template_xml, "Table", title)
        slide_xml = text.remove_graphic_frame(slide_xml)

        shape_id = text.next_shape_id(slide_xml)
        parts = []
        note_lines = []
        y = CONTENT_TOP
        for rec in page_items:
            full_text = _strip_leading_number(rec).strip()
            card_xml, shape_id = shapes.card_list_row(
                shape_id, CONTENT_LEFT, y, CONTENT_WIDTH, CARD_HEIGHT_RECOMMENDATION,
                id_text=str(counter), id_color=shapes.TEXT_DARK,
                title_text=truncate(full_text, limit),
                id_col_width=shapes.NUMBERED_ID_COL_WIDTH,
            )
            parts.append(card_xml)
            y += CARD_HEIGHT_RECOMMENDATION + RECOMMENDATION_CARD_GAP
            note_lines += [f"{counter}. {full_text}", ""]
            counter += 1
        slide_xml = text.insert_shape(slide_xml, "".join(parts))

        new_filename = slides.duplicate_slide_from_xml(work_dir, slide_xml, template_rels, after=insert_after)
        notes.add_notes(work_dir, new_filename, note_lines)
        new_filenames.append(new_filename)
        insert_after = new_filename
    return new_filenames


def build_section_detail_slides(work_dir: Path, template_xml: str, template_rels: str | None,
                                 after: str, section_display: str, items: list,
                                 include_pass_items: bool, cell_limits, threshold: int) -> list:
    """One or more "Findings -- {section}" slides: always a compact
    status-count line at top, then either a stacked card-list (<= threshold
    flagged items) or a fallback native table (> threshold), matching the
    reference deck's own card-vs-table rule for dense sections."""
    counts = {status: 0 for status in STATUS_ORDER}
    for it in items:
        canon = _canonical_status(it.validation_status)
        if canon:
            counts[canon] += 1

    selected = items if include_pass_items else [it for it in items if it.is_flagged]
    selected = sorted(selected, key=lambda it: (not it.is_must_have, it.id))
    if not selected:
        return []

    status_y = CONTENT_TOP + 60000

    if len(selected) <= threshold:
        slide_xml = text.replace_text_run(template_xml, "Table", f"Findings — {section_display}")
        slide_xml = text.remove_graphic_frame(slide_xml)
        shape_id = text.next_shape_id(slide_xml)
        status_xml, shape_id = shapes.compact_status_line(
            shape_id, CONTENT_LEFT, status_y, CONTENT_WIDTH, STATUS_LINE_HEIGHT, counts, STATUS_COLORS, STATUS_ORDER,
        )
        parts = [status_xml]
        note_lines = []
        y = status_y + STATUS_LINE_HEIGHT + STATUS_LINE_GAP
        for it in selected:
            status_key = _canonical_status(it.validation_status) or "Needs Review"
            color = STATUS_COLORS.get(status_key, shapes.TEXT_GRAY)
            card_xml, shape_id = shapes.card_list_row(
                shape_id, CONTENT_LEFT, y, CONTENT_WIDTH, CARD_HEIGHT_CRITICAL,
                id_text=it.id, id_color=color,
                title_text=truncate(it.title, 60),
                description_text=truncate(it.statement, cell_limits.get("critical_finding_card", 150)),
                status_label=it.validation_status or status_key, status_color=color,
            )
            parts.append(card_xml)
            y += CARD_HEIGHT_CRITICAL + CARD_GAP
            note_lines += _finding_note_lines(it)
        slide_xml = text.insert_shape(slide_xml, "".join(parts))
        new_filename = slides.duplicate_slide_from_xml(work_dir, slide_xml, template_rels, after=after)
        notes.add_notes(work_dir, new_filename, note_lines)
        return [new_filename]

    item_pages = tables.paginate(selected, SECTION_TABLE_ROWS_PER_SLIDE)
    pages = tables.paginate(build_findings_rows(selected), SECTION_TABLE_ROWS_PER_SLIDE)
    new_filenames = make_table_slides(
        work_dir, template_xml, template_rels, header_row_count=1,
        rows_per_page=pages, after=after,
        title_new_fn=lambda i, n, name=section_display: f"Findings — {name}" + (f" ({i}/{n})" if n > 1 else ""),
        header_values=["ID", "Title", "Priority", "Status", "Statement", "Evidence & Notes"],
        column_widths=FINDINGS_WIDTHS, row_height=FINDINGS_ROW_HEIGHT,
        status_col=STATUS_COL, status_color_map=STATUS_COLORS_LOWER,
        no_wrap_cols=FINDINGS_NO_WRAP_COLS, font_fit_cols=FINDINGS_FONT_FIT_COLS,
    )
    table_top = status_y + STATUS_LINE_HEIGHT + STATUS_LINE_GAP
    for filename, page_items in zip(new_filenames, item_pages):
        slide_path = work_dir / "ppt" / "slides" / filename
        slide_xml = slide_path.read_text(encoding="utf-8")
        shape_id = text.next_shape_id(slide_xml)
        status_xml, _ = shapes.compact_status_line(
            shape_id, CONTENT_LEFT, status_y, CONTENT_WIDTH, STATUS_LINE_HEIGHT, counts, STATUS_COLORS, STATUS_ORDER,
        )
        slide_xml = text.insert_shape(slide_xml, status_xml)
        slide_xml = tables.set_graphic_frame_bounds(slide_xml, CONTENT_LEFT, table_top, CONTENT_WIDTH, CONTENT_BOTTOM - table_top)
        slide_path.write_text(slide_xml, encoding="utf-8")
        note_lines = [line for it in page_items for line in _finding_note_lines(it)]
        notes.add_notes(work_dir, filename, note_lines)
    return new_filenames


def make_divider_slide(work_dir: Path, template_xml: str, template_rels: str | None,
                        after: str, number: int, title: str, subtitle: str) -> str:
    xml = set_multi_run_title(
        template_xml,
        ["This is a chapter title, please try best to shorten your title ", "within three lines", "."],
        title,
    )
    xml = text.replace_text_run(xml, "01.", f"{number:02d}.")
    xml = text.replace_text_run(xml, "Subtitle if needed and make it as short.", subtitle)
    return slides.duplicate_slide_from_xml(work_dir, xml, template_rels, after=after)


def build_exec_summary_kpi_slide(work_dir: Path, template_xml: str, template_rels: str | None,
                                  after: str, counts: dict, total_items: int, section_count: int,
                                  top_risk) -> str:
    """The Executive Summary's KPI tiles: strip the template's own 6 uniform
    tiles/connector lines, keep only its title placeholder and dark themed
    background, and splice in 5 status-colored tiles plus (if there's a
    critical finding to feature) a "Top risk" callout card."""
    slide_xml = text.replace_text_run(template_xml, "This is a key numbers slide", "Executive Summary")
    slide_xml = text.strip_to_title_only(slide_xml)
    shape_id = text.next_shape_id(slide_xml)

    caption = f"{total_items} checklist items assessed across {section_count} sections"
    caption_xml = shapes.text_box(
        shape_id, "Executive summary caption", CONTENT_LEFT, EXEC_SUMMARY_CAPTION_Y, CONTENT_WIDTH, EXEC_SUMMARY_CAPTION_HEIGHT,
        paragraphs=[[{"text": caption, "size": 1200, "color": "FFFFFF"}]],
    )
    shape_id += 1

    tiles = [{"value": str(counts.get(status, 0)), "label": status, "color": STATUS_COLORS[status]} for status in STATUS_ORDER]
    tiles_xml, shape_id = shapes.kpi_tile_row(shape_id, CONTENT_LEFT, KPI_ROW_Y, CONTENT_WIDTH, KPI_TILE_HEIGHT, tiles)

    parts = [caption_xml, tiles_xml]
    if top_risk:
        finding_id, title, section = top_risk
        body_text = f"{title} ({section})" if section else title
        callout_xml, shape_id = shapes.callout_card(
            shape_id, CONTENT_LEFT, CALLOUT_Y, CONTENT_WIDTH, CALLOUT_HEIGHT,
            headline=finding_id, body_text=body_text,
        )
        parts.append(callout_xml)

    slide_xml = text.insert_shape(slide_xml, "".join(parts))
    return slides.duplicate_slide_from_xml(work_dir, slide_xml, template_rels, after=after)


def build_methodology_slide(work_dir: Path, template_xml: str, template_rels: str | None,
                             after: str, data: read_checklist.ChecklistData) -> str:
    slide_xml = text.replace_text_run(template_xml, "Basic slide – Full text", "Platform Review Service")
    slide_xml = text.replace_text_run(
        slide_xml, "Subtitle here if needed", "How this Dataiku Platform Review was conducted"
    )
    slide_xml = text.replace_text_run(
        slide_xml,
        "Lorem Ipsum is simply dummy text of the printing and typesetting industry. ",
        "This report summarizes an automated, checklist-driven review of your Dataiku DSS "
        "instance against Dataiku's platform best practices.",
    )
    slide_xml = text.replace_text_run(
        slide_xml,
        "Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has "
        "been the industry’s standard dummy text ever since the 1500s, when an unknown printer took "
        "a galley of type and scrambled it to make a type specimen book. It has survived not only "
        "five centuries, but also the leap into electronic typesetting, remaining essentially "
        "unchanged. It was popularised in the 1960s with the release of Letraset sheets containing "
        "Lorem Ipsum passages, and more recently with desktop publishing software  including "
        "versions of Lorem Ipsum.",
        "Each finding in this deck is derived from a structured diagnostic bundle exported from your "
        "DSS instance and evaluated against a standardized checklist covering architecture and "
        "infrastructure, security and permissions, generative AI readiness, and scalability. Every "
        "checklist item is scored Pass, Fail, Partial, Needs Review, or Not Applicable based on the "
        "evidence available in the diagnosis, with must-have items flagged separately from "
        "nice-to-have recommendations.",
    )

    extra_bits = []
    diagnosis_generated = data.bundle_metadata.get("Diagnosis generated")
    if diagnosis_generated:
        extra_bits.append(f"a diagnosis generated on {diagnosis_generated}")
    reviewer = data.bundle_metadata.get("Reviewer")
    if reviewer:
        extra_bits.append(f"reviewed by {reviewer}")
    closing_sentence = (
        "The following sections present the overall results, a breakdown by review area, the most "
        "critical must-have items currently failing, and a prioritized set of recommendations to "
        "address them."
    )
    if extra_bits:
        closing_sentence += f" This review is based on {' and '.join(extra_bits)}."

    slide_xml = text.replace_text_run(
        slide_xml,
        "It was popularised in the 1960s with the release of Letraset sheets containing Lorem Ipsum "
        "passages, and more recently with desktop publishing software  including versions of Lorem "
        "Ipsum.≈",
        closing_sentence,
    )
    return slides.duplicate_slide_from_xml(work_dir, slide_xml, template_rels, after=after)


def add_logo(work_dir: Path, logo_path: Path) -> None:
    """Add the customer logo as a picture on the title slide, positioned
    over the title layout's own 'Customer logo' placeholder box."""
    ext = logo_path.suffix.lstrip(".").lower() or "png"
    content_type = mimetypes.guess_type(logo_path.name)[0] or "image/png"

    media_dir = work_dir / "ppt" / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in media_dir.glob("image*.*")}
    n = 1
    while f"image{n}.{ext}" in existing or (media_dir / f"image{n}.{ext}").exists():
        n += 1
    media_name = f"image{n}.{ext}"
    shutil.copyfile(logo_path, media_dir / media_name)

    ct_path = work_dir / "[Content_Types].xml"
    ct_xml = ct_path.read_text(encoding="utf-8")
    if f'Extension="{ext}"' not in ct_xml:
        default = f'<Default ContentType="{content_type}" Extension="{ext}"/>'
        ct_xml = ct_xml.replace("<Default", default + "<Default", 1)
        ct_path.write_text(ct_xml, encoding="utf-8")

    rels_path = work_dir / "ppt" / "slides" / "_rels" / f"{TITLE_SLIDE}.rels"
    rels_xml = rels_path.read_text(encoding="utf-8") if rels_path.exists() else (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'
    )
    nums = [int(m) for m in re.findall(r'Id="rId(\d+)"', rels_xml)]
    new_rid = f"rId{(max(nums) if nums else 0) + 1}"
    new_rel = (
        f'<Relationship Id="{new_rid}" '
        f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
        f'Target="../media/{media_name}"/>'
    )
    rels_xml = rels_xml.replace("</Relationships>", new_rel + "</Relationships>")
    rels_path.parent.mkdir(parents=True, exist_ok=True)
    rels_path.write_text(rels_xml, encoding="utf-8")

    # Position/size match the title layout's own "Customer logo" placeholder
    # box (slide15.xml, shape "Google Shape;348;p40"), so the image lands
    # exactly where that dashed placeholder box is.
    slide_path = work_dir / "ppt" / "slides" / TITLE_SLIDE
    slide_xml = slide_path.read_text(encoding="utf-8")
    pic_id = text.next_shape_id(slide_xml)
    pic_xml = (
        f'<p:pic><p:nvPicPr><p:cNvPr id="{pic_id}" name="Uploaded Logo"/>'
        f'<p:cNvPicPr preferRelativeResize="0"/><p:nvPr/></p:nvPicPr>'
        f'<p:blipFill><a:blip r:embed="{new_rid}"><a:alphaModFix/></a:blip>'
        f'<a:stretch><a:fillRect/></a:stretch></p:blipFill>'
        f'<p:spPr><a:xfrm><a:off x="1668725" y="182575"/><a:ext cx="1445700" cy="394500"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'
    )
    slide_xml = text.insert_shape(slide_xml, pic_xml)
    slide_path.write_text(slide_xml, encoding="utf-8")


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------

def build_deck(checklist_path: Path, customer: str, output_path: Path, base_deck: Path,
                logo_path: Path | None, rows_per_slide: int, include_pass_items: bool) -> Path:
    section_config = common.load_config("section_names.yaml")
    layout_config = common.load_config("deck_layout.yaml")
    cell_limits = layout_config.get("cell_char_limits", {})
    critical_per_slide = layout_config.get("critical_findings_per_slide", 5)
    recommendations_per_slide = layout_config.get("recommendations_per_slide", 6)
    section_card_table_threshold = layout_config.get("section_card_table_threshold", 5)

    logger.info("Reading checklist: %s", checklist_path)
    data = read_checklist.read_checklist(checklist_path, section_config)
    ordered_sections = section_names.order_sections(data.sheet_tab_names, section_config)

    with tempfile.TemporaryDirectory(prefix="deckgen_") as tmp:
        work_dir = Path(tmp) / "unpacked"
        logger.info("Unpacking base deck: %s", base_deck)
        package.unpack(base_deck, work_dir)

        slides_dir = work_dir / "ppt" / "slides"

        def read_slide(name):
            return (slides_dir / name).read_text(encoding="utf-8")

        def read_rels(name):
            p = slides_dir / "_rels" / f"{name}.rels"
            return p.read_text(encoding="utf-8") if p.exists() else None

        def write_slide(name, xml_text):
            (slides_dir / name).write_text(xml_text, encoding="utf-8")

        # Snapshot every template's ORIGINAL content before any edits, since
        # each template slide is consumed (cloned N times, then deleted).
        divider_tmpl_xml, divider_tmpl_rels = read_slide(DIVIDER_TEMPLATE_SLIDE), read_rels(DIVIDER_TEMPLATE_SLIDE)
        methodology_tmpl_xml, methodology_tmpl_rels = read_slide(METHODOLOGY_SLIDE), read_rels(METHODOLOGY_SLIDE)
        table_tmpl_xml, table_tmpl_rels = read_slide(TABLE_TEMPLATE_SLIDE), read_rels(TABLE_TEMPLATE_SLIDE)
        kpi_tmpl_xml, kpi_tmpl_rels = read_slide(KPI_SLIDE), read_rels(KPI_SLIDE)

        # --- Title slide ---
        report_date_str = data.bundle_metadata.get("Report generated") or data.bundle_metadata.get("Diagnosis generated")
        slide_xml = read_slide(TITLE_SLIDE)
        slide_xml = text.replace_text_run(
            slide_xml, "This is your presentation title, please try best to shorten your title within three lines.",
            customer.upper(),
        )
        subtitle = f"Platform Review — {format_month_year(report_date_str)}" if report_date_str else "Platform Review"
        slide_xml = text.replace_text_run(slide_xml, "Subtitle if needed and make it short.", subtitle)
        slide_xml = text.replace_text_run(slide_xml, "Customer logo", "", required=False)

        metadata_lines = format_title_metadata_lines(data)
        if metadata_lines:
            shape_id = text.next_shape_id(slide_xml)
            footer_xml = shapes.text_box(
                shape_id, "Bundle metadata", TITLE_FOOTER_X, TITLE_FOOTER_Y, TITLE_FOOTER_WIDTH, TITLE_FOOTER_HEIGHT,
                paragraphs=[[{"text": line, "size": 900, "color": "8A93A3"}] for line in metadata_lines],
            )
            slide_xml = text.insert_shape(slide_xml, footer_xml)

        write_slide(TITLE_SLIDE, slide_xml)
        if logo_path:
            logger.info("Adding customer logo: %s", logo_path)
            add_logo(work_dir, logo_path)

        # --- Table of Contents: 3 fixed chapters, blank the unused slots ---
        slide_xml = read_slide(TOC_SLIDE)
        for i, name in enumerate(CHAPTER_NAMES, start=1):
            slide_xml = text.replace_text_run(slide_xml, f" - Title of Chapter {i}", f" - {name}")
        for i in range(len(CHAPTER_NAMES) + 1, 6):
            slide_xml = text.replace_text_run(slide_xml, f"0{i}", "", required=False)
            slide_xml = text.replace_text_run(slide_xml, f" - Title of Chapter {i}", "", required=False)
        write_slide(TOC_SLIDE, slide_xml)

        last_inserted = TOC_SLIDE

        # --- Chapter 1: Executive Summary ---
        last_inserted = make_divider_slide(
            work_dir, divider_tmpl_xml, divider_tmpl_rels, after=last_inserted,
            number=1, title=CHAPTER_NAMES[0], subtitle="How this review was conducted",
        )
        last_inserted = build_methodology_slide(
            work_dir, methodology_tmpl_xml, methodology_tmpl_rels, after=last_inserted, data=data,
        )

        counts = build_overall_status_counts(data)
        total_items = sum(len(v) for v in data.items_by_sheet.values())
        top_risk = build_top_risk(data, cell_limits)
        last_inserted = build_exec_summary_kpi_slide(
            work_dir, kpi_tmpl_xml, kpi_tmpl_rels, after=last_inserted,
            counts=counts, total_items=total_items, section_count=len(ordered_sections), top_risk=top_risk,
        )

        scorecard_rows = build_scorecard_rows(data, ordered_sections)
        if scorecard_rows:
            last_inserted = build_scorecard_slide(
                work_dir, table_tmpl_xml, table_tmpl_rels, after=last_inserted, rows=scorecard_rows,
            )

        # --- Chapter 2: Findings & Risks ---
        last_inserted = make_divider_slide(
            work_dir, divider_tmpl_xml, divider_tmpl_rels, after=last_inserted,
            number=2, title=CHAPTER_NAMES[1], subtitle=f"{data.overall_counts.get('Total', 0)} checklist items assessed",
        )

        critical_blocks = build_critical_finding_blocks(data)
        if critical_blocks:
            new_slides = build_critical_finding_card_slides(
                work_dir, table_tmpl_xml, table_tmpl_rels, after=last_inserted,
                blocks=critical_blocks, per_slide=critical_per_slide, cell_limits=cell_limits,
            )
            last_inserted = new_slides[-1] if new_slides else last_inserted
        else:
            logger.info("No critical findings in the Summary sheet; skipping Critical Findings slide(s).")

        other_rows = build_other_must_have_rows(data, cell_limits)
        if other_rows:
            pages = tables.paginate(other_rows, rows_per_slide)
            new_slides = make_table_slides(
                work_dir, table_tmpl_xml, table_tmpl_rels, header_row_count=1,
                rows_per_page=pages, after=last_inserted,
                title_new_fn=lambda i, n: f"Other Must-Have Items" + (f" ({i}/{n})" if n > 1 else ""),
                header_values=["ID", "Title", "Status", "", "", ""],
                column_widths=OTHER_MUST_HAVE_WIDTHS, row_height=OTHER_MUST_HAVE_ROW_HEIGHT,
                status_col=2, status_color_map=STATUS_COLORS_LOWER,
                no_wrap_cols=OTHER_MUST_HAVE_NO_WRAP_COLS,
            )
            last_inserted = new_slides[-1] if new_slides else last_inserted

        for sec in ordered_sections:
            items = data.items_by_sheet.get(sec["sheet_tab_name"], [])
            new_slides = build_section_detail_slides(
                work_dir, table_tmpl_xml, table_tmpl_rels, after=last_inserted,
                section_display=sec["display"], items=items, include_pass_items=include_pass_items,
                cell_limits=cell_limits, threshold=section_card_table_threshold,
            )
            if not new_slides:
                logger.info("Section %r has no items to report; skipping its findings slide(s).", sec["display"])
            last_inserted = new_slides[-1] if new_slides else last_inserted

        # --- Chapter 3: Recommendations & Next Steps ---
        if data.recommendations:
            last_inserted = make_divider_slide(
                work_dir, divider_tmpl_xml, divider_tmpl_rels, after=last_inserted,
                number=3, title=CHAPTER_NAMES[2], subtitle="Priority-ordered next steps",
            )
            new_slides = build_recommendation_card_slides(
                work_dir, table_tmpl_xml, table_tmpl_rels, after=last_inserted,
                recommendations=data.recommendations, per_slide=recommendations_per_slide, cell_limits=cell_limits,
            )
            last_inserted = new_slides[-1] if new_slides else last_inserted
        else:
            logger.info("No recommendations in the Summary sheet; skipping Recommendations slide(s).")

        # --- Delete every consumed template slide, then clean up orphans ---
        for filename in SLIDES_CONSUMED_AS_TEMPLATES:
            slides.delete_slide(work_dir, filename)
        cleanup = slides.clean_orphans(work_dir)
        logger.info("Cleaned up orphaned parts: %s", cleanup)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        package.repack(work_dir, output_path)

    logger.info("Wrote deck: %s", output_path)
    return output_path


def default_output_path(checklist_path: Path, customer: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", customer).strip("_") or "deck"
    m = re.search(r"(\d{4}-\d{2}-\d{2})", checklist_path.stem)
    date_suffix = m.group(1) if m else datetime.now().strftime("%Y-%m-%d")
    return common.OUTPUT_DIR / f"{slug}_Platform_Review_{date_suffix}.pptx"


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--checklist", required=True, type=Path, help="Path to a completed checklist .xlsx")
    parser.add_argument("--customer", required=True, help="Customer name, shown on the title slide")
    parser.add_argument("--logo", type=Path, default=None, help="Optional path to a customer logo image")
    parser.add_argument("--output", type=Path, default=None, help="Output .pptx path (default: output/<customer>_Platform_Review_<date>.pptx)")
    parser.add_argument("--rows-per-slide", type=int, default=None, help="Max table rows per slide (default: config/deck_layout.yaml)")
    parser.add_argument("--include-pass-items", action="store_true", help="Include Pass/Not-Applicable items in findings tables too")
    parser.add_argument("--base-deck", type=Path, default=None, help='Base .pptx to build from (default: "resources/Dataiku Branding Template 2026.pptx")')
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {common.VERSION}")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")
    logger.info("Dataiku Review Generator v%s", common.VERSION)

    layout_config = common.load_config("deck_layout.yaml")
    base_deck = args.base_deck or (common.REPO_ROOT / layout_config.get("base_deck", "resources/Dataiku Branding Template 2026.pptx"))
    rows_per_slide = args.rows_per_slide or layout_config.get("table_rows_per_slide", 4)
    include_pass_items = args.include_pass_items or layout_config.get("include_pass_items", False)
    output_path = args.output or default_output_path(args.checklist, args.customer)

    if not args.checklist.exists():
        parser_error(f"Checklist file not found: {args.checklist}")
    if not base_deck.exists():
        parser_error(f"Base deck not found: {base_deck}")
    if args.logo and not args.logo.exists():
        parser_error(f"Logo file not found: {args.logo}")

    output_path = build_deck(
        checklist_path=args.checklist,
        customer=args.customer,
        output_path=output_path,
        base_deck=base_deck,
        logo_path=args.logo,
        rows_per_slide=rows_per_slide,
        include_pass_items=include_pass_items,
    )

    problems = validate_deck.validate(output_path)
    if problems:
        print(f"\nWARNING: {len(problems)} structural issue(s) found in the generated deck:")
        for p in problems:
            print(f"  - {p}")
    else:
        print(f"\nGenerated: {output_path}")
        print(validate_deck.MANUAL_QA_CHECKLIST)


def parser_error(message: str):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
