"""End-to-end golden snapshots, one per deck style: build a deck from a fixed
synthetic checklist and compare a text-level summary of it (slide order + every
text run per slide) against tests/golden/deck_summary_<style>.json. A new style
adds its own case to CASES and its own golden file, so it can't disturb another's.

Needs the branding template, which is gitignored (134MB), so this skips
wherever it isn't present. After an intended output change, refresh with:
    python3 -m pytest tests/test_golden_deck.py --update-golden  (all styles; add -k v2 for one)
and review the JSON diff before committing it.
"""

import json
import re
import zipfile

import pytest

import common
import styles
import validate_deck
from conftest import item

GOLDEN_DIR = common.REPO_ROOT / "tests" / "golden"
NARRATIVE = common.REPO_ROOT / "tests" / "fixtures" / "narrative_example.json"

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


def v2_sections():
    from test_deck_v2 import sections  # the synthetic checklist narrative_example.json is written against
    return sections()


# style -> (checklist sections, extra BuildRequest fields). v2 gets the example narrative so its
# golden covers narrative-driven text rather than the generic fallback.
CASES = {
    "v1": (golden_sections, {"rows_per_slide": 4, "include_pass_items": True}),
    "v2": (v2_sections, {"narrative_path": NARRATIVE}),
}


def test_every_registered_style_has_a_golden_case():
    assert set(CASES) == set(styles.STYLES)


@pytest.mark.parametrize("style", sorted(CASES))
def test_golden_deck(style, tmp_path, request):
    from conftest import build_checklist

    make_sections, extra = CASES[style]
    golden = GOLDEN_DIR / f"deck_summary_{style}.json"
    checklist = build_checklist(tmp_path / "golden_2026-07-22.xlsx", make_sections())
    built = styles.build(style, styles.BuildRequest(
        checklist_path=checklist, customer="Golden Test Co", output_path=tmp_path / "deck.pptx",
        base_deck=common.BRANDING_TEMPLATE, **extra,
    ))
    output = built["output_path"]

    assert validate_deck.validate(output) == []
    assert built["warnings"] == [] or style == "v2"  # v2 also reports analysis/narrative notes

    summary = summarize(output)
    if request.config.getoption("--update-golden") or not golden.exists():
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        pytest.skip(f"golden file written to {golden}; review and commit it")

    expected = json.loads(golden.read_text(encoding="utf-8"))
    assert [s["texts"][:1] for s in summary] == [s["texts"][:1] for s in expected], "slide order/titles changed"
    assert summary == expected
