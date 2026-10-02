"""End-to-end golden snapshot: build a deck from a fixed synthetic checklist
and compare a text-level summary of it (slide order + every text run per
slide) against tests/golden/deck_summary.json.

Needs the branding template, which is gitignored (134MB), so this skips
wherever it isn't present. After an intended output change, refresh with:
    python3 -m pytest tests/test_golden_deck.py --update-golden
and review the JSON diff before committing it.
"""

import json
import re
import zipfile

import pytest

import build_deck
import common
import validate_deck
from conftest import item

GOLDEN = common.REPO_ROOT / "tests" / "golden" / "deck_summary.json"

pytestmark = pytest.mark.skipif(
    not common.BRANDING_TEMPLATE.exists(),
    reason=f"branding template not present at {common.BRANDING_TEMPLATE}",
)


def golden_sections():
    return {
        "Architecture, Compute & Infrast": [
            item("ARCH-001", "Needs Review", evidence="config/project-deployer/ present", notes="Confirm with customer."),
            item("ARCH-002", "Fail", evidence="install.ini: backend.xmx=2g", notes="Raise backend heap."),
            item("ARCH-003", "Pass", priority="nice_to_have"),
        ],
        "Enterprise-grade Security, Perm": [
            item("SEC-001", "Partial", notes="Only some connections restricted."),
            item("SEC-002", "Not Applicable", priority="nice_to_have"),
        ],
        "Advanced Security Options (DSS ": [
            item("ADVSEC-001", "Fail", title="Hiding error stacks"),
        ],
    }


def summarize(pptx_path):
    """[{"slide": n, "texts": [...]}] in presentation order, with the
    generator version normalized out so a version bump alone doesn't fail."""
    with zipfile.ZipFile(pptx_path) as z:
        pres = z.read("ppt/presentation.xml").decode()
        rels = z.read("ppt/_rels/presentation.xml.rels").decode()
        out = []
        for n, rid in enumerate(re.findall(r'<p:sldId id="\d+" r:id="(rId\d+)"/>', pres), start=1):
            target = re.search(rf'<Relationship Id="{rid}"[^>]*Target="([^"]+)"', rels).group(1)
            xml = z.read("ppt/" + target).decode()
            texts = [t for t in re.findall(r"<a:t>([^<]*)</a:t>", xml) if t.strip()]
            texts = [t.replace(f"v{common.VERSION}", "v<VERSION>") for t in texts]
            out.append({"slide": n, "texts": texts})
    return out


def test_golden_deck(tmp_path, request):
    from conftest import build_checklist

    checklist = build_checklist(tmp_path / "golden_2026-07-22.xlsx", golden_sections())
    output = build_deck.build_deck(
        checklist_path=checklist, customer="Golden Test Co", output_path=tmp_path / "deck.pptx",
        base_deck=common.BRANDING_TEMPLATE, logo_path=None, rows_per_slide=4, include_pass_items=True,
    )

    assert validate_deck.validate(output) == []
    assert build_deck.collect_data_warnings(checklist) == []

    summary = summarize(output)
    if request.config.getoption("--update-golden") or not GOLDEN.exists():
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        pytest.skip(f"golden file written to {GOLDEN}; review and commit it")

    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert [s["texts"][:1] for s in summary] == [s["texts"][:1] for s in expected], "slide order/titles changed"
    assert summary == expected
