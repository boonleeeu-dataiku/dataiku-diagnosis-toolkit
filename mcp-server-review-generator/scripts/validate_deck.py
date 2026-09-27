"""Structural self-checks for a generated .pptx, run automatically at the
end of build_deck.py. No LibreOffice/pdftoppm is available on this machine,
so no automated visual QA is possible -- these checks catch the failure
modes a bug in this generator could plausibly introduce (malformed XML,
dangling relationships, leftover placeholder text), not layout/overflow
issues. Manual visual review in PowerPoint/Keynote is still required.
"""

import re
import sys
import xml.dom.minidom as minidom
import zipfile
from pathlib import Path

import common

PLACEHOLDER_PATTERNS = [
    re.compile(r"lorem ipsum", re.IGNORECASE),
    re.compile(r"\bTODO\b"),
    re.compile(r"\[insert", re.IGNORECASE),
    re.compile(r"\bxxx\b", re.IGNORECASE),
    # Branding-master-specific placeholder tells (resources/Dataiku Branding
    # Template 2026.pptx is heavily Lorem-Ipsum-templated; these catch a
    # forgotten replace_text_run on a base-deck-specific literal that the
    # generic patterns above wouldn't).
    re.compile(r"customer logo", re.IGNORECASE),
    re.compile(r"subtitle here if needed", re.IGNORECASE),
    re.compile(r"please try best to shorten", re.IGNORECASE),
    re.compile(r"basic slide", re.IGNORECASE),
    re.compile(r"this is a key numbers slide", re.IGNORECASE),
    re.compile(r"title of chapter", re.IGNORECASE),
]


def validate(pptx_path: Path) -> list[str]:
    """Return a list of problem descriptions; empty means all checks passed."""
    problems = []

    with zipfile.ZipFile(pptx_path, "r") as z:
        bad_entry = z.testzip()
        if bad_entry is not None:
            problems.append(f"Corrupt zip entry: {bad_entry}")
            return problems  # can't safely inspect further

        names = set(z.namelist())

        # 1. Every XML/rels part must be well-formed.
        for name in sorted(names):
            if name.endswith(".xml") or name.endswith(".rels"):
                try:
                    minidom.parseString(z.read(name))
                except Exception as e:
                    problems.append(f"Malformed XML in {name}: {e}")

        if "ppt/presentation.xml" not in names or "ppt/_rels/presentation.xml.rels" not in names:
            problems.append("Missing ppt/presentation.xml or its .rels part.")
            return problems

        pres_xml = z.read("ppt/presentation.xml").decode("utf-8")
        pres_rels_xml = z.read("ppt/_rels/presentation.xml.rels").decode("utf-8")
        ct_xml = z.read("[Content_Types].xml").decode("utf-8") if "[Content_Types].xml" in names else ""

        # 2. Every r:id in sldIdLst resolves to a relationship whose target exists.
        rids = re.findall(r'<p:sldId id="\d+" r:id="(rId\d+)"/>', pres_xml)
        if not rids:
            problems.append("presentation.xml has no <p:sldId> entries at all.")
        for rid in rids:
            m = re.search(rf'<Relationship Id="{re.escape(rid)}"[^>]*Target="([^"]+)"', pres_rels_xml)
            if m is None:
                problems.append(f"sldIdLst references {rid}, but it has no relationship entry.")
                continue
            target = "ppt/" + m.group(1)
            if target not in names:
                problems.append(f"Relationship {rid} points to missing part: {target}")
            slide_part = f"/{target}"
            if f'PartName="{slide_part}"' not in ct_xml:
                problems.append(f"{target} has no [Content_Types].xml Override entry.")

        # 3. No leftover placeholder text on any slide actually included in the deck.
        included_slides = set()
        for rid in rids:
            m = re.search(rf'<Relationship Id="{re.escape(rid)}"[^>]*Target="([^"]+)"', pres_rels_xml)
            if m:
                included_slides.add("ppt/" + m.group(1))
        for slide_part in sorted(included_slides):
            if slide_part not in names:
                continue
            text = z.read(slide_part).decode("utf-8")
            for pattern in PLACEHOLDER_PATTERNS:
                if pattern.search(text):
                    problems.append(f"Placeholder-looking text ({pattern.pattern}) still present in {slide_part}")

    return problems


MANUAL_QA_CHECKLIST = """
Automated visual QA is unavailable on this machine (no LibreOffice/pdftoppm
installed), so please open the generated deck in PowerPoint/Keynote/Google
Slides and manually check:
  - Card and table text is not overflowing its shape/slide (long checklist
    text was truncated to a fixed character budget, not auto-shrunk to fit
    -- fixed card heights and computed column widths/row heights are
    estimates, not rendered-and-verified). Check both a page with a full
    slide's worth of cards/rows and a page with just 1-2.
  - The Table of Contents matches the 3 divider slides' titles (the TOC's
    2 unused slots are left blank by design, not removed).
  - The Executive Summary KPI tiles show the right count in the right
    status color (Pass=teal, Fail=orange, Partial=periwinkle, Needs
    Review=peach, Not Applicable=gray), and the Top Risk callout (if
    present) reads sensibly.
  - The Results by Section scorecard's 5 status columns are colored
    consistently with the KPI tiles.
  - Status colors are consistent everywhere they appear: Critical Findings
    card IDs, Section Detail card IDs/status pills or fallback table cells,
    and the Other Must-Have Items table's Status column.
  - At least one Section Detail slide uses the card layout and, if any
    section has enough flagged items, at least one uses the table fallback
    -- both should read cleanly with the status line above them.
  - No placeholder text (Lorem ipsum, "Basic slide", etc.) remains anywhere.
  - The closing slide's Next Steps list and the Recommendations cards read
    sensibly and aren't duplicated confusingly.
""".strip()


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] in ("--version", "-V"):
        print(f"validate_deck.py {common.VERSION}")
        sys.exit(0)
    if len(sys.argv) != 2:
        print("Usage: python3 validate_deck.py <path-to-deck.pptx>", file=sys.stderr)
        sys.exit(2)
    path = Path(sys.argv[1])
    problems = validate(path)
    if problems:
        print(f"FAILED structural validation for {path} ({len(problems)} issue(s)):")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)
    print(f"OK: {path} passed all structural checks.")
    print()
    print(MANUAL_QA_CHECKLIST)
