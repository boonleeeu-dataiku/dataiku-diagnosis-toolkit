"""Scoped text-run substitution and small shape edits for slide XML, via
regex on the raw text -- never a full XML tree parse+reserialize round trip
(see package.py's docstring for why).
"""

import re
from xml.sax.saxutils import escape

SHAPE_ID_RE = re.compile(r'<p:cNvPr id="(\d+)"')
PIC_RE = re.compile(r"<p:pic>.*?</p:pic>", re.DOTALL)
SP_RE = re.compile(r"<p:sp>.*?</p:sp>", re.DOTALL)
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


def replace_within_shape(slide_xml: str, anchor_text: str, edits: list[tuple[str, str]]) -> str:
    """Find the single <p:sp>...</p:sp> shape containing the literal
    <a:t>{anchor_text}</a:t> run, apply a sequence of (old, new)
    replace_text_run edits scoped to just that shape's XML, and splice the
    edited shape back into slide_xml.

    Use this instead of a slide-wide replace_text_run when the same
    placeholder text is repeated identically across several shapes on one
    slide (e.g. repeated per-tile captions in a KPI grid) -- a slide-wide
    call would land on the first remaining occurrence in document order,
    which doesn't necessarily correspond to the shape you mean to edit.
    """
    needle = f"<a:t>{anchor_text}</a:t>"
    for m in SP_RE.finditer(slide_xml):
        if needle in m.group(0):
            shape_xml = m.group(0)
            for old, new in edits:
                shape_xml = replace_text_run(shape_xml, old, new, required=True)
            return slide_xml[: m.start()] + shape_xml + slide_xml[m.end() :]
    raise ValueError(f"No <p:sp> shape containing {anchor_text!r} found")


def remove_picture(slide_xml: str, required: bool = True) -> str:
    """Remove the first <p:pic>...</p:pic> block (and its r:embed reference)
    from a slide. The now-unreferenced image relationship should also be
    dropped from the slide's .rels (see remove_relationship_by_rid below);
    office.slides.clean_orphans() then removes the orphaned media file
    package-wide once all structural edits are done.
    """
    new_xml, n = PIC_RE.subn("", slide_xml, count=1)
    if n == 0 and required:
        raise ValueError("No <p:pic> found in slide XML")
    return new_xml


def remove_graphic_frame(slide_xml: str, required: bool = True) -> str:
    """Remove the first <p:graphicFrame>...</p:graphicFrame> block (e.g. the
    master's one native <a:tbl> table) from a slide, to replace it with
    hand-drawn shapes (see office.shapes) instead."""
    new_xml, n = GRAPHIC_FRAME_RE.subn("", slide_xml, count=1)
    if n == 0 and required:
        raise ValueError("No <p:graphicFrame> found in slide XML")
    return new_xml


def remove_relationship_by_rid(rels_xml: str, rid: str) -> str:
    return re.sub(rf'<Relationship Id="{re.escape(rid)}"[^>]*/>', "", rels_xml)


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


def placeholder_text_box(
    slide_xml: str,
    text: str,
    x: int,
    y: int,
    cx: int,
    cy: int,
    name: str = "Placeholder",
) -> str:
    """Build a minimal dashed-border text-box shape (EMU coordinates) used
    for manual-completion placeholders (e.g. the Architecture Diagram slide).
    Not styled from the branding template -- a plain, clearly-a-placeholder
    box is the point.
    """
    shape_id = next_shape_id(slide_xml)
    return (
        f'<p:sp><p:nvSpPr><p:cNvPr id="{shape_id}" name="{escape(name)}"/>'
        f'<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        f'<p:spPr><a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/>'
        f'<a:ln w="19050"><a:solidFill><a:srgbClr val="999999"/></a:solidFill>'
        f'<a:prstDash val="dash"/></a:ln></p:spPr>'
        f'<p:txBody><a:bodyPr wrap="square" anchor="ctr"><a:spAutoFit/></a:bodyPr>'
        f"<a:lstStyle/><a:p><a:pPr algn=\"ctr\"/><a:r>"
        f'<a:rPr lang="en-US" sz="1400" i="1"><a:solidFill><a:srgbClr val="999999"/>'
        f"</a:solidFill></a:rPr><a:t>{escape(text)}</a:t></a:r></a:p></p:txBody></p:sp>"
    )


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
