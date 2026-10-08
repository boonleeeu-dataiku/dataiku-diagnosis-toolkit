"""Speaker-notes attachment for a generated slide.

Card-list layouts (critical findings, recommendations, section-detail cards)
still hard-truncate their long-form text to a fixed character budget (no
font-metrics library is available in this project's dependencies to shrink
text to fit a fixed-height card the way tables.set_cell_font_size() can for a
table row -- see build_deck.py's CARD_HEIGHT_CRITICAL comment). add_notes()
gives every truncated field a full, untruncated copy in that slide's speaker
notes, so nothing is ever actually lost, even where the visible card is.

Always builds a fresh notesSlideN.xml part rather than cloning one -- clones
made via office.slides.duplicate_slide_from_xml() never inherit a source
slide's notes relationship by design (see its docstring), so every generated
slide starts with no notes of its own. Raw XML string building, never a
parsed-and-reserialized tree (see package.py's docstring for why). Must run
before office.slides.clean_orphans() (it prunes any notesSlide part not
referenced by a remaining slide's .rels file).
"""

import re
from pathlib import Path
from xml.sax.saxutils import escape

NOTES_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"
NOTES_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide"
NOTES_MASTER_REL_TYPE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster"
NOTES_SLIDE_RE = re.compile(r"^notesSlide(\d+)\.xml$")


def _next_notes_number(unpacked_dir: Path) -> int:
    notes_dir = unpacked_dir / "ppt" / "notesSlides"
    nums = []
    if notes_dir.exists():
        for p in notes_dir.glob("notesSlide*.xml"):
            m = NOTES_SLIDE_RE.match(p.name)
            if m:
                nums.append(int(m.group(1)))
    return (max(nums) if nums else 0) + 1


def add_notes(unpacked_dir: Path, slide_filename: str, lines: list[str]) -> None:
    """Attach a new notes slide (one paragraph per item in `lines`) to an
    already-registered content slide (i.e. slide_filename must already exist
    under ppt/slides/ and be registered in presentation.xml -- any slide
    filename returned by office.slides.duplicate_slide_from_xml()
    qualifies). No-ops if `lines` is empty."""
    if not lines:
        return
    notes_dir = unpacked_dir / "ppt" / "notesSlides"
    (notes_dir / "_rels").mkdir(parents=True, exist_ok=True)

    n = _next_notes_number(unpacked_dir)
    notes_filename = f"notesSlide{n}.xml"

    paragraphs = "".join(
        f'<a:p><a:r><a:rPr lang="en-US" sz="1200"/><a:t>{escape(line)}</a:t></a:r></a:p>'
        for line in lines
    )
    notes_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Notes Placeholder"/>'
        '<p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr>'
        '<p:nvPr><p:ph type="body" idx="1"/></p:nvPr></p:nvSpPr>'
        '<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>'
        f'{paragraphs}</p:txBody></p:sp>'
        '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:notes>'
    )
    (notes_dir / notes_filename).write_text(notes_xml, encoding="utf-8")

    notes_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="{NOTES_MASTER_REL_TYPE}" Target="../notesMasters/notesMaster1.xml"/>'
        '</Relationships>'
    )
    (notes_dir / "_rels" / f"{notes_filename}.rels").write_text(notes_rels_xml, encoding="utf-8")

    ct_path = unpacked_dir / "[Content_Types].xml"
    ct_xml = ct_path.read_text(encoding="utf-8")
    override = f'<Override ContentType="{NOTES_CONTENT_TYPE}" PartName="/ppt/notesSlides/{notes_filename}"/>'
    ct_xml = ct_xml.replace("</Types>", override + "</Types>")
    ct_path.write_text(ct_xml, encoding="utf-8")

    slide_rels_path = unpacked_dir / "ppt" / "slides" / "_rels" / f"{slide_filename}.rels"
    if slide_rels_path.exists():
        slide_rels_xml = slide_rels_path.read_text(encoding="utf-8")
    else:
        slide_rels_path.parent.mkdir(parents=True, exist_ok=True)
        slide_rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            "</Relationships>"
        )
    nums = [int(m) for m in re.findall(r'Id="rId(\d+)"', slide_rels_xml)]
    new_rid = f"rId{(max(nums) if nums else 0) + 1}"
    new_rel = f'<Relationship Id="{new_rid}" Type="{NOTES_REL_TYPE}" Target="../notesSlides/{notes_filename}"/>'
    slide_rels_xml = slide_rels_xml.replace("</Relationships>", new_rel + "</Relationships>")
    slide_rels_path.write_text(slide_rels_xml, encoding="utf-8")
