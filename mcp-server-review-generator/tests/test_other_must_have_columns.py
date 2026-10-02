"""v0.3.1: Other Must-Have Items slides carried 3 empty trailing columns left
over from the 6-column table template."""

import re
import zipfile

import pytest

import build_deck
import common
from office import tables
from test_golden_deck import golden_sections


def _tbl(cols=4):
    grid = "".join(f'<a:gridCol w="{100 * (i + 1)}"/>' for i in range(cols))
    row = lambda tag: "<a:tr h=\"1\">" + "".join(f"<a:tc><a:t>{tag}{i}</a:t></a:tc>" for i in range(cols)) + "</a:tr>"
    return f"<a:tbl><a:tblGrid>{grid}</a:tblGrid>{row('h')}{row('d')}</a:tbl>"


def test_delete_columns_drops_grid_and_cells():
    out = tables.delete_columns(_tbl(4), [1, 3])
    assert re.findall(r'<a:gridCol w="(\d+)"', out) == ["100", "300"]
    assert re.findall(r"<a:t>([^<]*)", out) == ["h0", "h2", "d0", "d2"]


def test_delete_columns_rejects_out_of_range():
    with pytest.raises(ValueError):
        tables.delete_columns(_tbl(3), [3])


@pytest.mark.skipif(not common.BRANDING_TEMPLATE.exists(), reason="branding template not present")
def test_regression_v0_3_1_other_must_have_no_empty_columns(tmp_path):
    from conftest import build_checklist

    checklist = build_checklist(tmp_path / "c_2026-07-22.xlsx", golden_sections())
    output = build_deck.build_deck(
        checklist_path=checklist, customer="Test Co", output_path=tmp_path / "deck.pptx",
        base_deck=common.BRANDING_TEMPLATE, logo_path=None, rows_per_slide=4, include_pass_items=True,
    )
    found = 0
    with zipfile.ZipFile(output) as z:
        for name in z.namelist():
            if not re.fullmatch(r"ppt/slides/slide\d+\.xml", name):
                continue
            xml = z.read(name).decode()
            if "Other Must-Have Items" not in xml:
                continue
            found += 1
            assert len(re.findall(r"<a:gridCol\b", xml)) == 3
            for tr in re.findall(r"<a:tr\b.*?</a:tr>", xml, re.S):
                cells = re.findall(r"<a:tc>.*?</a:tc>", tr, re.S)
                assert len(cells) == 3
                assert all("".join(re.findall(r"<a:t>([^<]*)", c)).strip() for c in cells)
    assert found >= 1
