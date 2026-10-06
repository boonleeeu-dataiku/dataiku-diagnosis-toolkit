"""calibrations.md cites check ids from the bundled default checklist. Ids can change when the
checklist does, and a renumbered id would silently send a calibration to the wrong check, so the
"Check anchors" table records each id's title and this test fails when the checklist drifts."""

import re

import openpyxl

from conftest import REPO_ROOT, TEMPLATE

CALIBRATIONS = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "references" / "calibrations.md"
ID = re.compile(r"\b(?:ARCH|SEC|SCALE|GENAI|ADVSEC)-\d{3}\b")


def _split():
    text = CALIBRATIONS.read_text(encoding="utf-8")
    body, sep, table = text.partition("## Check anchors")
    assert sep, "calibrations.md lost its 'Check anchors' section"
    return body, table


def _anchors():
    rows = re.findall(r"^\|\s*((?:ARCH|SEC|SCALE|GENAI|ADVSEC)-\d{3})\s*\|\s*(.+?)\s*\|\s*$", _split()[1], re.M)
    return dict(rows)


def _template_titles():
    wb = openpyxl.load_workbook(TEMPLATE, read_only=True)
    titles = {}
    for ws in wb.worksheets:
        rows = ws.iter_rows(values_only=True)
        header = list(next(rows))
        title = header.index("title")
        for row in rows:
            if row[0]:
                titles[row[0]] = row[title]
    return titles


def test_every_id_cited_in_calibrations_has_an_anchor():
    cited = set(ID.findall(_split()[0]))
    missing = sorted(cited - set(_anchors()))
    assert not missing, f"ids cited in calibrations.md but missing from 'Check anchors': {missing}"


def test_anchors_still_match_the_bundled_checklist():
    titles = _template_titles()
    stale = []
    for check_id, title in _anchors().items():
        if check_id not in titles:
            stale.append(f"{check_id}: no longer in the checklist (was '{title}')")
        elif titles[check_id] != title:
            stale.append(f"{check_id}: title is now '{titles[check_id]}' (anchored as '{title}')")
    assert not stale, "calibrations.md entries may now point at the wrong check, review them:\n  " + "\n  ".join(stale)
