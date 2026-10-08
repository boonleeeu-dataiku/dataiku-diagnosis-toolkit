"""Scoped text-run substitution and small shape edits for slide XML, via
regex on the raw text -- never a full XML tree parse+reserialize round trip
(see package.py's docstring for why).
"""

import re
from xml.sax.saxutils import escape

SHAPE_ID_RE = re.compile(r'<p:cNvPr id="(\d+)"')
GRAPHIC_FRAME_RE = re.compile(r"<p:graphicFrame>.*?</p:graphicFrame>", re.DOTALL)
SHAPE_BLOCK_RE = re.compile(r"<p:(sp|cxnSp|pic|graphicFrame)>.*?</p:\1>", re.DOTALL)
OFF_RE = re.compile(r'<a:off x="(\d+)" y="(\d+)"/>')
EXT_RE = re.compile(r'<a:ext cx="(\d+)" cy="(\d+)"/>')


def replace_text_run(slide_xml: str, old_text: str, new_text: str, required: bool = True) -> str:
    """Replace the first literal <a:t>{old_text}</a:t> run with new_text
    (XML-escaped). `old_text` must be given exactly as it appears in the raw
    part XML (i.e. already XML-escaped if it originally contained &/</>).
    Raises if not found and required=True (fail fast on a base-deck/template
    mismatch, rather than silently leaving stale text in place).
    """
    needle = f"<a:t>{old_text}</a:t>"
    replacement = f"<a:t>{escape(new_text)}</a:t>"
    new_xml, n = re.subn(re.escape(needle), lambda _: replacement, slide_xml, count=1)
    if n == 0:
        if required:
            raise ValueError(f"Text run {old_text!r} not found in slide XML")
        return slide_xml
    return new_xml


def remove_graphic_frame(slide_xml: str, required: bool = True) -> str:
    """Remove the first <p:graphicFrame>...</p:graphicFrame> block (e.g. the
    master's one native <a:tbl> table) from a slide, to replace it with
    hand-drawn shapes (see office.shapes) instead."""
    new_xml, n = GRAPHIC_FRAME_RE.subn("", slide_xml, count=1)
    if n == 0 and required:
        raise ValueError("No <p:graphicFrame> found in slide XML")
    return new_xml


def strip_to_title_only(slide_xml: str) -> str:
    """Remove every top-level shape (<p:sp>/<p:cxnSp>/<p:pic>/<p:graphicFrame>)
    except the one containing <p:ph type="title"/>. Used when a template
    slide's own decorative/content shapes (e.g. the KPI-tiles slide's 6
    number tiles and connector lines) are being replaced wholesale by
    hand-drawn shapes (see office.shapes), but its title placeholder and the
    slide's own background/theming should survive.
    """
    return SHAPE_BLOCK_RE.sub(lambda m: m.group(0) if '<p:ph type="title"' in m.group(0) else "", slide_xml)


def next_shape_id(slide_xml: str) -> int:
    nums = [int(n) for n in SHAPE_ID_RE.findall(slide_xml)]
    return (max(nums) if nums else 0) + 1


def insert_shape(slide_xml: str, shape_xml: str) -> str:
    """Insert a new shape (<p:sp>...</p:sp> etc.) just before </p:spTree>,
    i.e. as the last (topmost) shape on the slide."""
    marker = "</p:spTree>"
    if marker not in slide_xml:
        raise ValueError("No </p:spTree> found in slide XML")
    return slide_xml.replace(marker, shape_xml + marker, 1)


def set_shape_bounds(
    slide_xml: str,
    shape_id: int,
    *,
    x: int | None = None,
    y: int | None = None,
    cx: int | None = None,
    cy: int | None = None,
) -> str:
    """Reposition/resize one shape (<p:sp>, <p:cxnSp>, ...) by id, overriding
    only the <a:off>/<a:ext> attributes given (others left untouched). Used
    when a template shape's own geometry was sized for its original
    placeholder text and needs adjusting after real, longer text is
    substituted in (see build_deck.build_methodology_slide())."""
    needle = f'<p:cNvPr id="{shape_id}"'
    for m in SHAPE_BLOCK_RE.finditer(slide_xml):
        block = m.group(0)
        if needle not in block:
            continue
        new_block = block
        if x is not None or y is not None:
            off_m = OFF_RE.search(new_block)
            if off_m is None:
                raise ValueError(f"Shape id {shape_id} has no <a:off> to reposition")
            cur_x, cur_y = int(off_m.group(1)), int(off_m.group(2))
            new_off = f'<a:off x="{cur_x if x is None else x}" y="{cur_y if y is None else y}"/>'
            new_block = OFF_RE.sub(lambda _: new_off, new_block, count=1)
        if cx is not None or cy is not None:
            ext_m = EXT_RE.search(new_block)
            if ext_m is None:
                raise ValueError(f"Shape id {shape_id} has no <a:ext> to resize")
            cur_cx, cur_cy = int(ext_m.group(1)), int(ext_m.group(2))
            new_ext = f'<a:ext cx="{cur_cx if cx is None else cx}" cy="{cur_cy if cy is None else cy}"/>'
            new_block = EXT_RE.sub(lambda _: new_ext, new_block, count=1)
        return slide_xml[: m.start()] + new_block + slide_xml[m.end() :]
    raise ValueError(f"No shape with id {shape_id} found in slide XML")
