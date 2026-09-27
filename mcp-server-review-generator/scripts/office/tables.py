"""Native PPTX table (<a:tbl>) cloning: turn one template data row into N
rows of real content, via regex-scoped string templating -- never a full
XML tree parse+reserialize round trip (see package.py's docstring for why).

All row/cell locations are found with re.finditer and spliced by match span
(start()/end()), not by re-searching for matched text with str.index(), so
this is safe even when two rows/cells happen to be byte-identical.
"""

import re
from xml.sax.saxutils import escape

TBL_RE = re.compile(r"<a:tbl>.*?</a:tbl>", re.DOTALL)
TR_RE = re.compile(r"<a:tr\b.*?</a:tr>", re.DOTALL)
TC_RE = re.compile(r"<a:tc>.*?</a:tc>", re.DOTALL)
TEXT_RE = re.compile(r"(<a:t>)(.*?)(</a:t>)", re.DOTALL)
GRID_COL_RE = re.compile(r'<a:gridCol w="\d+"')
TR_OPEN_RE = re.compile(r'^<a:tr h="\d+"')
SCHEME_CLR_RE = re.compile(r'<a:schemeClr val="[^"]*"/>')
RPR_OPEN_RE = re.compile(r"<a:rPr\b[^>]*>")
SZ_RE = re.compile(r'sz="\d+"')
BODY_PR_EMPTY_RE = re.compile(r"<a:bodyPr/>")
FRAME_XFRM_RE = re.compile(r'(<p:xfrm><a:off x=")\d+(" y=")\d+("/><a:ext cx=")\d+(" cy=")\d+("/></p:xfrm>)')


def extract_table(slide_xml: str) -> str:
    """Return the (first) <a:tbl>...</a:tbl> block in a slide's XML."""
    m = TBL_RE.search(slide_xml)
    if m is None:
        raise ValueError("No <a:tbl> found in slide XML")
    return m.group(0)


def replace_table(slide_xml: str, new_tbl_xml: str) -> str:
    """Replace the (first) <a:tbl> block in a slide's XML with new_tbl_xml."""
    m = TBL_RE.search(slide_xml)
    if m is None:
        raise ValueError("No <a:tbl> found in slide XML")
    return slide_xml[: m.start()] + new_tbl_xml + slide_xml[m.end() :]


def extract_rows(tbl_xml: str) -> list[str]:
    """Return every <a:tr>...</a:tr> block, in document order."""
    return TR_RE.findall(tbl_xml)


def extract_cells(row_xml: str) -> list[str]:
    """Return every <a:tc>...</a:tc> block in a row, in document order."""
    return TC_RE.findall(row_xml)


def row_template(tbl_xml: str, header_row_count: int = 1) -> str:
    """Return the first data row (just after the header row(s)) as a
    reusable template for cloning."""
    rows = extract_rows(tbl_xml)
    if header_row_count >= len(rows):
        raise ValueError(
            f"Table has {len(rows)} row(s), fewer than header_row_count={header_row_count}"
        )
    return rows[header_row_count]


def expected_column_count(template_row_xml: str) -> int:
    return len(extract_cells(template_row_xml))


def _fill_cell(cell_xml: str, value: str) -> str:
    """Put `value` (escaped) into the cell's first text run; blank any other
    text runs in the same cell so multi-run placeholder styling doesn't
    duplicate text. A cell with no text run at all is left untouched."""
    matches = list(TEXT_RE.finditer(cell_xml))
    if not matches:
        return cell_xml
    escaped_value = escape(str(value))
    pieces = []
    pos = 0
    for i, m in enumerate(matches):
        pieces.append(cell_xml[pos : m.start()])
        text = escaped_value if i == 0 else ""
        pieces.append(f"{m.group(1)}{text}{m.group(3)}")
        pos = m.end()
    pieces.append(cell_xml[pos:])
    return "".join(pieces)


def fill_row(template_row_xml: str, values: list[str]) -> str:
    """Clone a template <a:tr> with each cell's text replaced by the
    corresponding value (in column order). Raises if the value count doesn't
    match the template's cell count, rather than silently misaligning
    columns."""
    matches = list(TC_RE.finditer(template_row_xml))
    if len(matches) != len(values):
        raise ValueError(
            f"Row template has {len(matches)} cell(s) but {len(values)} value(s) were given"
        )
    pieces = []
    pos = 0
    for m, value in zip(matches, values):
        pieces.append(template_row_xml[pos : m.start()])
        pieces.append(_fill_cell(m.group(0), value))
        pos = m.end()
    pieces.append(template_row_xml[pos:])
    return "".join(pieces)


def build_rows_xml(template_row_xml: str, rows: list[list[str]]) -> str:
    """Fill the template row once per item in `rows` and concatenate."""
    return "".join(fill_row(template_row_xml, values) for values in rows)


def replace_header_row(tbl_xml: str, new_header_values: list[str], header_row_index: int = 0) -> str:
    """Re-label a header row's cell text in place (e.g. relabeling a reused
    table template's column headers for a new context)."""
    matches = list(TR_RE.finditer(tbl_xml))
    if header_row_index >= len(matches):
        raise ValueError(f"Table has {len(matches)} row(s), fewer than header_row_index={header_row_index}")
    header_match = matches[header_row_index]
    new_header_xml = fill_row(header_match.group(0), new_header_values)
    return tbl_xml[: header_match.start()] + new_header_xml + tbl_xml[header_match.end() :]


def replace_data_rows(tbl_xml: str, new_rows_xml: str, header_row_count: int = 1) -> str:
    """Keep the header row(s) verbatim; replace every row after them with
    new_rows_xml (typically the output of build_rows_xml)."""
    matches = list(TR_RE.finditer(tbl_xml))
    if header_row_count >= len(matches):
        raise ValueError(
            f"Table has {len(matches)} row(s), fewer than header_row_count={header_row_count}"
        )
    start = matches[header_row_count].start()
    end = matches[-1].end()
    return tbl_xml[:start] + new_rows_xml + tbl_xml[end:]


def set_column_widths(tbl_xml: str, widths: list[int]) -> str:
    """Replace each <a:gridCol w="..."/> in a table, in order, with the given
    widths (EMU). Raises if the count doesn't match, rather than silently
    truncating/ignoring extra widths."""
    matches = list(GRID_COL_RE.finditer(tbl_xml))
    if len(matches) != len(widths):
        raise ValueError(f"Table has {len(matches)} gridCol(s) but {len(widths)} width(s) were given")
    pieces = []
    pos = 0
    for m, width in zip(matches, widths):
        pieces.append(tbl_xml[pos : m.start()])
        pieces.append(f'<a:gridCol w="{width}"')
        pos = m.end()
    pieces.append(tbl_xml[pos:])
    return "".join(pieces)


def set_row_height(row_xml: str, height_emu: int) -> str:
    """Replace a single <a:tr h="..."> row's height attribute."""
    new_xml, n = TR_OPEN_RE.subn(f'<a:tr h="{height_emu}"', row_xml, count=1)
    if n == 0:
        raise ValueError('No leading <a:tr h="..."> tag found in row XML')
    return new_xml


def set_column_no_wrap(row_xml: str, col_indices: list[int]) -> str:
    """Disable text wrapping (wrap="none") on the given 0-indexed columns'
    cells in a single <a:tr> row -- for short, enum/code-like columns (an ID,
    a priority/count value) that should stay on one line rather than wrap
    just because the column happens to be narrow. Raises if a targeted
    cell's <a:bodyPr> isn't the template's bare, unstyled <a:bodyPr/> (i.e.
    it's already been customized some other way)."""
    cells = list(TC_RE.finditer(row_xml))
    targets = set(col_indices)
    pieces = []
    pos = 0
    for i, m in enumerate(cells):
        pieces.append(row_xml[pos : m.start()])
        cell_xml = m.group(0)
        if i in targets:
            cell_xml, n = BODY_PR_EMPTY_RE.subn('<a:bodyPr wrap="none"/>', cell_xml, count=1)
            if n == 0:
                raise ValueError(f"Cell {i} has no bare <a:bodyPr/> to set wrap on")
        pieces.append(cell_xml)
        pos = m.end()
    pieces.append(row_xml[pos:])
    return "".join(pieces)


def set_table_no_wrap(tbl_xml: str, col_indices: list[int]) -> str:
    """Apply set_column_no_wrap() to every row in the table, header included
    -- e.g. an "ID" header should stay one line same as its data cells."""
    rows = list(TR_RE.finditer(tbl_xml))
    pieces = []
    pos = 0
    for row_m in rows:
        pieces.append(tbl_xml[pos : row_m.start()])
        pieces.append(set_column_no_wrap(row_m.group(0), col_indices))
        pos = row_m.end()
    pieces.append(tbl_xml[pos:])
    return "".join(pieces)


def style_cell_text(row_xml: str, cell_index: int, color_hex: str, bold: bool = True) -> str:
    """Recolor (and optionally bold) the given 0-indexed cell's first run in
    a single <a:tr> row, via a scoped splice on that cell's slice only --
    swaps its run's <a:schemeClr .../> for a literal <a:srgbClr val="{color_hex}"/>
    and injects b="1" into the run's <a:rPr> if not already bold."""
    cells = list(TC_RE.finditer(row_xml))
    if cell_index >= len(cells):
        raise ValueError(f"Row has {len(cells)} cell(s), fewer than cell_index={cell_index}")
    m = cells[cell_index]
    cell_xml = m.group(0)

    cell_xml, n = SCHEME_CLR_RE.subn(f'<a:srgbClr val="{color_hex}"/>', cell_xml, count=1)
    if n == 0:
        raise ValueError("No <a:schemeClr .../> found in cell to recolor")

    if bold:
        rpr_m = RPR_OPEN_RE.search(cell_xml)
        if rpr_m is not None and ' b="' not in rpr_m.group(0):
            new_open = rpr_m.group(0)[:-1] + ' b="1">'
            cell_xml = cell_xml[: rpr_m.start()] + new_open + cell_xml[rpr_m.end() :]

    return row_xml[: m.start()] + cell_xml + row_xml[m.end() :]


def style_cell_text_by_value(row_xml: str, cell_index: int, value: str,
                              value_color_map: dict, bold: bool = True) -> str:
    """Recolor cell_index's text via style_cell_text() if `value`
    (case-insensitively) is a key in value_color_map; otherwise return
    row_xml unchanged. Generalizes a single-status conditional (e.g.
    "Fail only") into an N-way status->color lookup so every status value
    gets its own color, not just one."""
    color = value_color_map.get(str(value).strip().lower())
    if color is None:
        return row_xml
    return style_cell_text(row_xml, cell_index, color, bold=bold)


def style_column_text(tbl_xml: str, col_index: int, color_hex: str,
                       header_row_count: int = 1, bold: bool = True) -> str:
    """Recolor every data row's col_index-th cell text unconditionally
    (regardless of the cell's value) -- e.g. a scorecard table where each
    status column is always tinted that status's color."""
    rows = list(TR_RE.finditer(tbl_xml))
    if header_row_count >= len(rows):
        raise ValueError(f"Table has {len(rows)} row(s), fewer than header_row_count={header_row_count}")
    pieces = [tbl_xml[: rows[header_row_count].start()]]
    pos = rows[header_row_count].start()
    for row_m in rows[header_row_count:]:
        pieces.append(tbl_xml[pos : row_m.start()])
        pieces.append(style_cell_text(row_m.group(0), col_index, color_hex, bold=bold))
        pos = row_m.end()
    pieces.append(tbl_xml[pos:])
    return "".join(pieces)


def set_graphic_frame_bounds(slide_xml: str, x: int, y: int, cx: int, cy: int) -> str:
    """Reposition/resize a slide's <p:graphicFrame> (its outer xfrm, not the
    <a:tbl>'s own column/row grid) -- used to make room above a native table
    for hand-drawn content (e.g. a section-detail slide's compact status
    line), since a table's own gridCol/row heights control its rendered
    size but the graphicFrame's xfrm still anchors its position."""
    new_xml, n = FRAME_XFRM_RE.subn(
        lambda m: f"{m.group(1)}{x}{m.group(2)}{y}{m.group(3)}{cx}{m.group(4)}{cy}{m.group(5)}",
        slide_xml, count=1,
    )
    if n == 0:
        raise ValueError("No <p:graphicFrame><p:xfrm> found in slide XML")
    return new_xml


def set_font_size(xml: str, size: int) -> str:
    """Replace every run's sz="..." font-size attribute (hundredths of a
    point, e.g. 900 = 9pt) within the given XML fragment (a single row or a
    whole table). Raises if no run has a size to resize, rather than
    silently no-op'ing on a mismatched fragment."""
    new_xml, n = SZ_RE.subn(f'sz="{size}"', xml)
    if n == 0:
        raise ValueError('No sz="..." attribute found to resize')
    return new_xml


def set_cell_font_size(row_xml: str, cell_index: int, size: int) -> str:
    """Replace every sz="..." attribute within one 0-indexed cell of a
    single <a:tr> row -- scoped to that cell only, unlike set_font_size()'s
    whole-fragment replace, so one unusually long cell's font can shrink
    without affecting the rest of its row."""
    cells = list(TC_RE.finditer(row_xml))
    if cell_index >= len(cells):
        raise ValueError(f"Row has {len(cells)} cell(s), fewer than cell_index={cell_index}")
    m = cells[cell_index]
    cell_xml, n = SZ_RE.subn(f'sz="{size}"', m.group(0))
    if n == 0:
        raise ValueError('No sz="..." attribute found in cell to resize')
    return row_xml[: m.start()] + cell_xml + row_xml[m.end() :]


def paginate(items: list, rows_per_slide: int) -> list[list]:
    """Chunk items into fixed-size pages for one table slide each."""
    if rows_per_slide <= 0:
        raise ValueError("rows_per_slide must be positive")
    return [items[i : i + rows_per_slide] for i in range(0, len(items), rows_per_slide)]
