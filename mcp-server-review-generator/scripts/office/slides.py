"""Slide duplication/deletion bookkeeping for an unpacked .pptx package.

Reimplemented from the public OOXML/ECMA-376 package structure (verified
directly against a real Google-Slides-exported .pptx: [Content_Types].xml,
ppt/presentation.xml, ppt/_rels/presentation.xml.rels, and a slide's own
.rels file) -- not copied from any third-party tool. All edits are scoped
string/regex substitutions on the raw part text, never a full XML tree
parse+reserialize round trip (see package.py's docstring for why).

Structural edits (duplicate/delete) must all happen before any content edits
(text/table fills), and clean_orphans() should run last, after all
structural edits are final.
"""

import re
from pathlib import Path

SLIDE_RE = re.compile(r"^slide(\d+)\.xml$")
CONTENT_TYPES = "[Content_Types].xml"
PRES_XML = "ppt/presentation.xml"
PRES_RELS = "ppt/_rels/presentation.xml.rels"
SLIDE_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
)
SLIDE_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide"
)


def _slides_dir(unpacked_dir: Path) -> Path:
    return unpacked_dir / "ppt" / "slides"


def _rels_path_for(unpacked_dir: Path, slide_filename: str) -> Path:
    return _slides_dir(unpacked_dir) / "_rels" / f"{slide_filename}.rels"


def _next_slide_number(unpacked_dir: Path) -> int:
    nums = []
    for p in _slides_dir(unpacked_dir).glob("slide*.xml"):
        m = SLIDE_RE.match(p.name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) if nums else 0) + 1


def _next_rid(rels_xml: str) -> str:
    nums = [int(n) for n in re.findall(r'Id="rId(\d+)"', rels_xml)]
    return f"rId{(max(nums) if nums else 0) + 1}"


def _next_sld_id(presentation_xml: str) -> int:
    nums = [int(n) for n in re.findall(r'<p:sldId id="(\d+)"', presentation_xml)]
    return (max(nums) if nums else 255) + 1


def _slide_filename_for_rid(pres_rels_xml: str, rid: str) -> str | None:
    m = re.search(
        rf'<Relationship Id="{re.escape(rid)}"[^>]*Target="slides/([^"]+)"', pres_rels_xml
    )
    return m.group(1) if m else None


def _rid_for_slide_filename(pres_rels_xml: str, slide_filename: str) -> str | None:
    m = re.search(
        rf'<Relationship Id="(rId\d+)"[^>]*Target="slides/{re.escape(slide_filename)}"',
        pres_rels_xml,
    )
    return m.group(1) if m else None


def duplicate_slide_from_xml(
    unpacked_dir: Path,
    slide_xml: str,
    rels_xml: str | None,
    after: str | None = None,
) -> str:
    """Register a new slide from in-memory XML text (rather than an existing
    slide file). Use this when the same 'template' slide needs to be cloned
    several times but has already been (or will be) edited/deleted in place
    -- snapshot its original XML/.rels text once, then call this once per
    clone, instead of re-reading a source file
    that may no longer hold the original template content.

    Returns the new slide's filename (e.g. 'slide23.xml'). The clone's
    .rels drops any notesSlide relationship, so clones never inherit the
    source's speaker notes. `after` is an existing slide filename (already
    present in sldIdLst) to insert the new slide after; None appends at the
    end.
    """
    new_num = _next_slide_number(unpacked_dir)
    new_filename = f"slide{new_num}.xml"

    dst_path = _slides_dir(unpacked_dir) / new_filename
    dst_path.write_text(slide_xml, encoding="utf-8")

    if rels_xml is not None:
        rels_xml = re.sub(
            r'<Relationship [^>]*Type="[^"]*/notesSlide"[^>]*/>', "", rels_xml
        )
        dst_rels_path = _rels_path_for(unpacked_dir, new_filename)
        dst_rels_path.parent.mkdir(parents=True, exist_ok=True)
        dst_rels_path.write_text(rels_xml, encoding="utf-8")

    # 1. Register the new part's content type.
    ct_path = unpacked_dir / CONTENT_TYPES
    ct_xml = ct_path.read_text(encoding="utf-8")
    override = (
        f'<Override ContentType="{SLIDE_CONTENT_TYPE}" '
        f'PartName="/ppt/slides/{new_filename}"/>'
    )
    ct_xml = ct_xml.replace("</Types>", override + "</Types>")
    ct_path.write_text(ct_xml, encoding="utf-8")

    # 2. Register a new relationship from the presentation to the new slide.
    rels_path = unpacked_dir / PRES_RELS
    pres_rels_xml = rels_path.read_text(encoding="utf-8")
    new_rid = _next_rid(pres_rels_xml)
    new_rel = (
        f'<Relationship Id="{new_rid}" Type="{SLIDE_REL_TYPE}" '
        f'Target="slides/{new_filename}"/>'
    )
    pres_rels_xml = pres_rels_xml.replace("</Relationships>", new_rel + "</Relationships>")
    rels_path.write_text(pres_rels_xml, encoding="utf-8")

    # 3. Insert a <p:sldId> into the slide list, after the requested slide.
    pres_path = unpacked_dir / PRES_XML
    pres_xml = pres_path.read_text(encoding="utf-8")
    new_sld_id = _next_sld_id(pres_xml)
    new_sld_id_el = f'<p:sldId id="{new_sld_id}" r:id="{new_rid}"/>'

    if after is not None:
        after_rid = _rid_for_slide_filename(pres_rels_xml, after)
        if after_rid is None:
            raise ValueError(f"Cannot find relationship for after={after!r}")
        anchor = re.search(
            rf'<p:sldId id="\d+" r:id="{re.escape(after_rid)}"/>', pres_xml
        )
        if anchor is None:
            raise ValueError(f"Cannot find sldId entry for after={after!r} (rid={after_rid})")
        insert_at = anchor.end()
        pres_xml = pres_xml[:insert_at] + new_sld_id_el + pres_xml[insert_at:]
    else:
        pres_xml = pres_xml.replace("</p:sldIdLst>", new_sld_id_el + "</p:sldIdLst>")

    pres_path.write_text(pres_xml, encoding="utf-8")
    return new_filename


def delete_slide(unpacked_dir: Path, slide_filename: str) -> None:
    """Remove slide_filename from the presentation's slide list. The slide's
    XML/.rels files and its Content_Types override are left in place for
    clean_orphans() to remove afterwards, once all structural edits are done.
    """
    rels_path = unpacked_dir / PRES_RELS
    pres_rels_xml = rels_path.read_text(encoding="utf-8")
    rid = _rid_for_slide_filename(pres_rels_xml, slide_filename)
    if rid is None:
        raise ValueError(f"Slide {slide_filename!r} is not registered in {PRES_RELS}")

    pres_path = unpacked_dir / PRES_XML
    pres_xml = pres_path.read_text(encoding="utf-8")
    new_pres_xml = re.sub(rf'<p:sldId id="\d+" r:id="{re.escape(rid)}"/>', "", pres_xml)
    if new_pres_xml == pres_xml:
        raise ValueError(f"No sldId entry found for {slide_filename!r} (rid={rid})")
    pres_path.write_text(new_pres_xml, encoding="utf-8")


def list_slide_order(unpacked_dir: Path) -> list[str]:
    """Return the slide filenames in presentation order, per sldIdLst."""
    pres_xml = (unpacked_dir / PRES_XML).read_text(encoding="utf-8")
    pres_rels_xml = (unpacked_dir / PRES_RELS).read_text(encoding="utf-8")
    rids = re.findall(r'<p:sldId id="\d+" r:id="(rId\d+)"/>', pres_xml)
    order = []
    for rid in rids:
        filename = _slide_filename_for_rid(pres_rels_xml, rid)
        if filename is not None:
            order.append(filename)
    return order


def clean_orphans(unpacked_dir: Path) -> dict:
    """Remove slide XML/.rels/Content_Types entries no longer reachable from
    sldIdLst, plus any media/notesSlide parts no longer referenced by any
    remaining part's relationships. Returns a summary dict for logging.
    Run this once, after all duplicate_slide_from_xml()/delete_slide() calls.
    """
    reachable = set(list_slide_order(unpacked_dir))
    slides_dir = _slides_dir(unpacked_dir)
    all_slide_files = {p.name for p in slides_dir.glob("slide*.xml")}
    orphaned_slides = sorted(all_slide_files - reachable)

    ct_path = unpacked_dir / CONTENT_TYPES
    ct_xml = ct_path.read_text(encoding="utf-8")
    rels_path = unpacked_dir / PRES_RELS
    pres_rels_xml = rels_path.read_text(encoding="utf-8")

    for filename in orphaned_slides:
        (slides_dir / filename).unlink(missing_ok=True)
        rels_file = _rels_path_for(unpacked_dir, filename)
        rels_file.unlink(missing_ok=True)
        ct_xml = re.sub(
            rf'<Override ContentType="{re.escape(SLIDE_CONTENT_TYPE)}" '
            rf'PartName="/ppt/slides/{re.escape(filename)}"/>',
            "",
            ct_xml,
        )
        rid = _rid_for_slide_filename(pres_rels_xml, filename)
        if rid is not None:
            pres_rels_xml = re.sub(
                rf'<Relationship Id="{re.escape(rid)}"[^>]*Target="slides/{re.escape(filename)}"[^>]*/>',
                "",
                pres_rels_xml,
            )

    ct_path.write_text(ct_xml, encoding="utf-8")
    rels_path.write_text(pres_rels_xml, encoding="utf-8")

    # Media/notesSlide reachability: union of targets referenced by every
    # remaining .rels file in the package (resolved relative to the part
    # that owns each .rels file).
    referenced_parts = set()
    for rels_file in unpacked_dir.rglob("_rels/*.rels"):
        owner_dir = rels_file.parent.parent
        rels_xml = rels_file.read_text(encoding="utf-8")
        for target in re.findall(r'Target="([^"]+)"', rels_xml):
            if target.startswith("http") or target.startswith("../../"):
                continue
            resolved = (owner_dir / target).resolve()
            referenced_parts.add(resolved)

    removed_media, removed_notes = [], []
    media_dir = unpacked_dir / "ppt" / "media"
    if media_dir.exists():
        for f in media_dir.iterdir():
            if f.is_file() and f.resolve() not in referenced_parts:
                removed_media.append(f.name)
                f.unlink()

    notes_dir = unpacked_dir / "ppt" / "notesSlides"
    if notes_dir.exists():
        for f in notes_dir.glob("notesSlide*.xml"):
            if f.resolve() not in referenced_parts:
                removed_notes.append(f.name)
                f.unlink()
                f_rels = notes_dir / "_rels" / f"{f.name}.rels"
                f_rels.unlink(missing_ok=True)

    return {
        "removed_slides": orphaned_slides,
        "removed_media": removed_media,
        "removed_notes": removed_notes,
    }
