"""Hand-drawn card/tile/pill shapes for the redesigned deck's KPI rows,
card-list findings/recommendations, and the "top risk" callout -- raw <p:sp>
XML built from explicit EMU coordinates and hex colors, following the same
pattern already used by build_legend_shapes()/add_logo() in build_deck.py
and office.text.placeholder_text_box(). Spliced onto a slide via
office.text.insert_shape(); never a parsed-and-reserialized tree (see
package.py's docstring for why).

Composite builders (more than one shape) return (xml, next_shape_id) so
callers chain multiple calls without re-scanning the slide for free ids.
Single-shape builders (rounded_rect, text_box) return just the XML string.
"""

from xml.sax.saxutils import escape

BODY_FONT = "Roboto"
NUMERAL_FONT = "Spectral"

TEXT_DARK = "1A1A1A"
TEXT_GRAY = "5F6368"
TEXT_GRAY_LIGHT = "9AA0AC"
CARD_FILL = "FFFFFF"
CARD_BORDER = "E2E5EA"

KPI_TILE_GAP = 120000
# Wide enough for the longest ID in the sample checklist ("GENAI-001"/
# "SCALE-009", 9 chars) at the card ID column's bold 12pt font with margin to
# spare -- 780,000 EMU wasn't: bold text renders wider than the ~0.5em/char
# estimate used elsewhere in this project (no font-metrics library is
# available -- see build_deck.py's CARD_HEIGHT_CRITICAL comment), so a 9-char
# ID actually wrapped onto 2 lines there even before wrap="none" was added.
ID_COL_WIDTH = 1050000
# card_list_row's numbered-rank cards (recommendations) hold a much shorter
# value than a checklist ID -- "1".."99" -- so they use this narrower width
# instead of ID_COL_WIDTH to avoid a large empty gap before the card body.
NUMBERED_ID_COL_WIDTH = 400000
PILL_WIDTH = 900000
CARD_PAD = 140000


def _run(text: str, size: int, color_hex: str, bold: bool = False, font: str = BODY_FONT) -> str:
    b = ' b="1"' if bold else ""
    return (
        f'<a:r><a:rPr lang="en-US" sz="{size}"{b}>'
        f'<a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
        f'<a:latin typeface="{font}"/><a:ea typeface="{font}"/>'
        f'<a:cs typeface="{font}"/><a:sym typeface="{font}"/></a:rPr>'
        f"<a:t>{escape(str(text))}</a:t></a:r>"
    )


def rounded_rect(shape_id: int, name: str, x: int, y: int, cx: int, cy: int,
                  fill_hex: str, line_hex: str | None = None, line_w: int = 9525,
                  radius_pct: int = 8000) -> str:
    """Base card/tile/pill background: a rounded rectangle with an optional
    1px-ish border. `radius_pct` is the OOXML adj guide (in 1/1000 of a
    percent of the shape's shorter side) -- ~6000-10000 reads as a card,
    ~50000 as a fully rounded pill."""
    ln = (
        f'<a:ln w="{line_w}"><a:solidFill><a:srgbClr val="{line_hex}"/></a:solidFill></a:ln>'
        if line_hex else "<a:ln><a:noFill/></a:ln>"
    )
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/>'
        f"<p:cNvSpPr/><p:nvPr/></p:nvSpPr>"
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val {radius_pct}"/></a:avLst></a:prstGeom>'
        f'<a:solidFill><a:srgbClr val="{fill_hex}"/></a:solidFill>{ln}</p:spPr>'
        f"<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody></p:sp>"
    )


def text_box(shape_id: int, name: str, x: int, y: int, cx: int, cy: int,
             paragraphs: list, align: str = "l", anchor: str = "t", wrap: str = "square") -> str:
    """A borderless text box with one or more paragraphs. `paragraphs` is a
    list of lists of run dicts: {"text", "size", "color", "bold"?, "font"?}.
    `wrap="none"` is for short, enum/code-like content (e.g. an ID column)
    that should stay on one line rather than wrap just because the box is
    narrow -- default stays "square" for everything else.
    """
    ps = []
    for runs in paragraphs:
        run_xml = "".join(
            _run(r["text"], r["size"], r["color"], r.get("bold", False), r.get("font", BODY_FONT))
            for r in runs
        )
        ps.append(f'<a:p><a:pPr algn="{align}"/>{run_xml}</a:p>')
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/>'
        f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
        f'<p:txBody><a:bodyPr wrap="{wrap}" anchor="{anchor}" lIns="0" tIns="0" rIns="0" bIns="0">'
        f"<a:noAutofit/></a:bodyPr><a:lstStyle/>"
        f'{"".join(ps)}</p:txBody></p:sp>'
    )


def kpi_tile(start_shape_id: int, x: int, y: int, cx: int, cy: int,
             value: str, label: str, color_hex: str) -> tuple[str, int]:
    """One KPI tile: a white rounded-rect card with a big colored numeral
    over a small gray caption -- the tile's own white fill keeps its text
    legible regardless of the slide's own background color."""
    card = rounded_rect(start_shape_id, f"KPI tile - {label}", x, y, cx, cy, CARD_FILL, CARD_BORDER, radius_pct=10000)
    pad = 130000
    box = text_box(
        start_shape_id + 1, f"KPI tile text - {label}", x + pad, y, cx - 2 * pad, cy,
        paragraphs=[
            [{"text": value, "size": 2400, "color": color_hex, "bold": True, "font": NUMERAL_FONT}],
            [{"text": label, "size": 1000, "color": TEXT_GRAY}],
        ],
        align="ctr", anchor="ctr",
    )
    return card + box, start_shape_id + 2


def kpi_tile_row(start_shape_id: int, x: int, y: int, width: int, height: int, tiles: list) -> tuple[str, int]:
    """`tiles` is a list of {"value", "label", "color"} dicts, laid out as
    equal-width tiles spanning `width`."""
    n = len(tiles)
    tile_w = (width - KPI_TILE_GAP * (n - 1)) // n
    shape_id = start_shape_id
    parts = []
    for i, t in enumerate(tiles):
        tile_xml, shape_id = kpi_tile(shape_id, x + i * (tile_w + KPI_TILE_GAP), y, tile_w, height,
                                       t["value"], t["label"], t["color"])
        parts.append(tile_xml)
    return "".join(parts), shape_id


def compact_status_line(shape_id: int, x: int, y: int, cx: int, cy: int,
                         counts: dict, color_map: dict, order: list,
                         separator: str = "   ·   ") -> tuple[str, int]:
    """A single-line, single-shape status summary (e.g. "3 Fail  ·  2 Partial
    ·  ..."), used as the compact per-section equivalent of the full KPI
    tile row."""
    runs = []
    for i, status in enumerate(order):
        if i > 0:
            runs.append({"text": separator, "size": 1100, "color": TEXT_GRAY_LIGHT})
        runs.append({"text": str(counts.get(status, 0)), "size": 1200, "color": color_map[status], "bold": True})
        runs.append({"text": f" {status}", "size": 1100, "color": TEXT_GRAY})
    box = text_box(shape_id, "Status summary", x, y, cx, cy, paragraphs=[runs], align="l", anchor="ctr")
    return box, shape_id + 1


def status_pill(shape_id: int, x: int, y: int, cx: int, cy: int,
                 label: str, color_hex: str) -> tuple[str, int]:
    """A small pill-shaped badge: colored border/text on a white fill."""
    pill = rounded_rect(shape_id, f"Status pill - {label}", x, y, cx, cy, CARD_FILL, color_hex, radius_pct=50000)
    label_box = text_box(shape_id + 1, f"Status pill text - {label}", x, y, cx, cy,
                          paragraphs=[[{"text": label.upper(), "size": 800, "color": color_hex, "bold": True}]],
                          align="ctr", anchor="ctr")
    return pill + label_box, shape_id + 2


def card_list_row(start_shape_id: int, x: int, y: int, width: int, height: int,
                   id_text: str, id_color: str, title_text: str, description_text: str = "",
                   status_label: str | None = None, status_color: str | None = None,
                   id_col_width: int = ID_COL_WIDTH) -> tuple[str, int]:
    """The reused "molecule": a full-width white rounded-rect card with a
    colored ID/number at left, a dark title (+ optional gray description
    line) in the middle, and an optional right-aligned status pill. Used
    identically for critical findings, section fail/partial lists, and
    numbered recommendations (the latter pass id_col_width=NUMBERED_ID_COL_WIDTH,
    since a rank number needs far less room than a checklist ID)."""
    shape_id = start_shape_id
    parts = [rounded_rect(shape_id, f"Card - {id_text}", x, y, width, height, CARD_FILL, CARD_BORDER, radius_pct=6000)]
    shape_id += 1

    parts.append(text_box(
        shape_id, f"Card ID - {id_text}", x + CARD_PAD, y, id_col_width, height,
        paragraphs=[[{"text": id_text, "size": 1200, "color": id_color, "bold": True}]],
        align="l", anchor="ctr", wrap="none",
    ))
    shape_id += 1

    pill_reserved = (PILL_WIDTH + CARD_PAD) if status_label else 0
    body_x = x + CARD_PAD + id_col_width
    body_w = width - 2 * CARD_PAD - id_col_width - pill_reserved
    body_paragraphs = [[{"text": title_text, "size": 1050, "color": TEXT_DARK, "bold": True}]]
    if description_text:
        body_paragraphs.append([{"text": description_text, "size": 900, "color": TEXT_GRAY}])
    parts.append(text_box(shape_id, f"Card body - {id_text}", body_x, y, body_w, height,
                           paragraphs=body_paragraphs, align="l", anchor="ctr"))
    shape_id += 1

    if status_label:
        pill_h = min(340000, height - 120000)
        pill_x = x + width - CARD_PAD - PILL_WIDTH
        pill_y = y + (height - pill_h) // 2
        pill_xml, shape_id = status_pill(shape_id, pill_x, pill_y, PILL_WIDTH, pill_h, status_label, status_color)
        parts.append(pill_xml)

    return "".join(parts), shape_id


def callout_card(start_shape_id: int, x: int, y: int, width: int, height: int,
                  headline: str, body_text: str, fill_hex: str = "FDEAEA",
                  line_hex: str = "E8A0A0", headline_color: str = "9B2C2C") -> tuple[str, int]:
    """The single highlighted "Top risk" narrative card on the executive
    summary slide."""
    shape_id = start_shape_id
    parts = [rounded_rect(shape_id, "Top risk callout", x, y, width, height, fill_hex, line_hex, radius_pct=6000)]
    shape_id += 1
    pad = 180000
    parts.append(text_box(
        shape_id, "Top risk callout text", x + pad, y, width - 2 * pad, height,
        paragraphs=[
            [{"text": "Top risk: ", "size": 1100, "color": headline_color, "bold": True},
             {"text": headline, "size": 1100, "color": headline_color, "bold": True}],
            [{"text": body_text, "size": 1000, "color": TEXT_GRAY}],
        ],
        align="l", anchor="ctr",
    ))
    return "".join(parts), shape_id + 1
