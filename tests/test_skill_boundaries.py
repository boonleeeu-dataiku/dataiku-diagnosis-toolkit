"""Bundle-reading knowledge (file layout, safe extraction, log/column quirks) is owned by the
reader (skills/dataiku-diagnosis-reader + mcp-server-diagnosis-reader). The checklist-review skill
holds checklist judgment only, and must point at the reader instead of re-documenting it.

docs/upstream-reader-spec.md lists what is moving upstream. `calibrations.md` is the one file
allowed to quote key locations in the interim; delete INTERIM_ALLOWED when that spec has shipped."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_DIR = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review"

# Reader-owned layout facts: they must not creep into the checklist skill's own text.
READER_OWNED_TERMS = ["ROTA", "lsblk", "[ERROR]", "defaultK8sClusterId", "hs_err_pid", "datadir_listing.txt",
                      "dip.properties", "detailsReadability", "sanity-check.json"]
INTERIM_ALLOWED = {"calibrations.md"}


def _files():
    return [REVIEW_DIR / "SKILL.md", *sorted((REVIEW_DIR / "references").glob("*.md"))]


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_checklist_skill_does_not_document_bundle_layout(path):
    if path.name in INTERIM_ALLOWED:
        pytest.skip("interim: see docs/upstream-reader-spec.md")
    text = path.read_text(encoding="utf-8")
    found = [t for t in READER_OWNED_TERMS if t in text]
    assert not found, f"{path.name} documents reader-owned layout {found}; put it in the reader (upstream)"


def test_checklist_skill_makes_the_reader_a_prerequisite():
    text = (REVIEW_DIR / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("load the `dataiku-diagnosis-reader` skill", "`skill-guide`", "`safe_read`"):
        assert phrase in text, f"SKILL.md no longer says {phrase!r}"
