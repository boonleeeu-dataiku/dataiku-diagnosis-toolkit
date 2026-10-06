"""Bundle-reading knowledge (file layout, safe extraction, log/column quirks) is owned by the
reader (skills/dataiku-diagnosis-reader). The checklist-review skill
holds checklist judgment only, and must point at the reader instead of re-documenting it.

A new "where/how do I read X" fact belongs in the reader's references (upstream, then re-sync), not
in the checklist skill. When this test fails, move the fact to the reader and point to it."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REVIEW_DIR = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review"

# Reader-owned layout facts: they must not creep into the checklist skill's own text.
READER_OWNED_TERMS = ["ROTA", "lsblk", "[ERROR]", "defaultK8sClusterId", "hs_err_pid", "datadir_listing.txt",
                      "config_listing.txt", "dip.properties", "detailsReadability", "hdfsInterface",
                      "sanity-check.json", "config/clusters", "general-settings.json", "install.ini",
                      "jekSettings", "localAIServerSettings", "managedNamespace", "kubernetesNamespace",
                      "containerSettings", "deployerClientSettings", "project-deployer", "api-deployer",
                      "dss-version.json", "du -sh", "sessionsMax", "forceSingleSessionPerUser",
                      "disableDataTableLinks", "canObtainAPITicket", "lastRunTimestamp", "agent-hub",
                      "userRules", "groupRules",
                      "metastoreCatalogsSettings", "graphicsExportsEnabled", "synchronizeTo",
                      "custom_python", "step_based", "envSelection"]


def _files():
    return [REVIEW_DIR / "SKILL.md", *sorted((REVIEW_DIR / "references").glob("*.md"))]


@pytest.mark.parametrize("path", _files(), ids=lambda p: p.name)
def test_checklist_skill_does_not_document_bundle_layout(path):
    text = path.read_text(encoding="utf-8")
    found = [t for t in READER_OWNED_TERMS if t in text]
    assert not found, f"{path.name} documents reader-owned layout {found}; put it in the reader (upstream)"


def test_checklist_skill_makes_the_reader_a_prerequisite():
    text = (REVIEW_DIR / "SKILL.md").read_text(encoding="utf-8")
    for phrase in ("load the `dataiku-diagnosis-reader` skill", "orient.sh", "facts.py", "limitations.md"):
        assert phrase in text, f"SKILL.md no longer says {phrase!r}"
