"""validate_deck.validate() against tiny hand-built .pptx packages, one per
problem class it is meant to catch."""

import zipfile

import pytest

import validate_deck

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Override PartName="/ppt/slides/slide1.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
    "</Types>"
)
PRESENTATION = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<p:sldIdLst><p:sldId id="256" r:id="rId2"/></p:sldIdLst></p:presentation>'
)
PRESENTATION_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
    'Target="slides/slide1.xml"/></Relationships>'
)


def slide(text="Platform Review"):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f"<p:cSld><p:spTree><a:t>{text}</a:t></p:spTree></p:cSld></p:sld>"
    )


def make_pptx(path, **overrides):
    parts = {
        "[Content_Types].xml": CONTENT_TYPES,
        "ppt/presentation.xml": PRESENTATION,
        "ppt/_rels/presentation.xml.rels": PRESENTATION_RELS,
        "ppt/slides/slide1.xml": slide(),
    }
    parts.update(overrides)
    with zipfile.ZipFile(path, "w") as z:
        for name, content in parts.items():
            if content is not None:
                z.writestr(name, content)
    return path


def test_minimal_valid_deck_passes(tmp_path):
    assert validate_deck.validate(make_pptx(tmp_path / "ok.pptx")) == []


def test_malformed_xml(tmp_path):
    problems = validate_deck.validate(make_pptx(tmp_path / "bad.pptx", **{"ppt/slides/slide1.xml": "<p:sld><unclosed>"}))
    assert any(p.startswith("Malformed XML in ppt/slides/slide1.xml") for p in problems)


def test_missing_presentation_part(tmp_path):
    problems = validate_deck.validate(make_pptx(tmp_path / "bad.pptx", **{"ppt/presentation.xml": None}))
    assert problems == ["Missing ppt/presentation.xml or its .rels part."]


def test_no_slides(tmp_path):
    pres = PRESENTATION.replace('<p:sldId id="256" r:id="rId2"/>', "")
    problems = validate_deck.validate(make_pptx(tmp_path / "bad.pptx", **{"ppt/presentation.xml": pres}))
    assert "presentation.xml has no <p:sldId> entries at all." in problems


def test_dangling_relationship_id(tmp_path):
    rels = PRESENTATION_RELS.replace('Id="rId2"', 'Id="rId9"')
    problems = validate_deck.validate(make_pptx(tmp_path / "bad.pptx", **{"ppt/_rels/presentation.xml.rels": rels}))
    assert "sldIdLst references rId2, but it has no relationship entry." in problems


def test_relationship_to_missing_slide_part(tmp_path):
    problems = validate_deck.validate(make_pptx(tmp_path / "bad.pptx", **{"ppt/slides/slide1.xml": None}))
    assert "Relationship rId2 points to missing part: ppt/slides/slide1.xml" in problems


def test_missing_content_type_override(tmp_path):
    ct = CONTENT_TYPES.replace("/ppt/slides/slide1.xml", "/ppt/slides/slide99.xml")
    problems = validate_deck.validate(make_pptx(tmp_path / "bad.pptx", **{"[Content_Types].xml": ct}))
    assert "ppt/slides/slide1.xml has no [Content_Types].xml Override entry." in problems


@pytest.mark.parametrize("text", ["Lorem ipsum dolor", "TODO fix", "[Insert chart]", "Customer logo", "Title of Chapter 4"])
def test_placeholder_text_is_flagged(tmp_path, text):
    problems = validate_deck.validate(make_pptx(tmp_path / "bad.pptx", **{"ppt/slides/slide1.xml": slide(text)}))
    assert any("Placeholder-looking text" in p for p in problems)


def test_placeholder_text_on_unlisted_slide_is_ignored(tmp_path):
    path = make_pptx(tmp_path / "ok.pptx", **{"ppt/slides/slide2.xml": slide("Lorem ipsum")})
    assert validate_deck.validate(path) == []
