"""v2 deck: analysis rules (pure), narrative validation, and a build smoke test
(skipped without the branding template)."""

import json

import pytest

import common
import deck_analysis as da
import narrative
import read_checklist
import section_names
from conftest import item

OWNERS = {"AI platform owner": ["ai platform"], "Infrastructure": ["infra team"], "Platform team": ["platform"]}


def notes(head, ev="", action=""):
    return "\n".join([head] + ([f"• {ev}"] if ev else []) + ([f"• Action: {action}"] if action else []))


def sections():
    return {
        "Architecture, Compute & Infrast": [
            item("ARCH-001", "Needs Review", notes=notes("Automation node unconfirmed", "", "confirm with platform team")),
            item("ARCH-002", "Needs Review", notes=notes("Backups unknown", "", "ask infra team for the schedule")),
            item("ARCH-003", "Pass"),
            item("ARCH-004", "Not Applicable"),
        ],
        "Enterprise-grade Security, Perm": [
            item("SEC-001", "Partial", notes=notes("Shared ceiling", "98 memory kills", "size limits; see SCALE-009")),
            item("SEC-009", "Pass", notes="Groups populated"),
        ],
        "Scalable Performance, Stability": [
            item("SCALE-009", "Fail", notes=notes("Uncapped jobs", "maxRunningJobs=0", "set finite cap; see SEC-001")),
            item("SCALE-010", "Fail", notes=notes("Stacks visible", "hideErrorStacks=false", "set true after confirming support flow")),
        ],
    }


@pytest.fixture
def analysis(checklist_factory, section_config):
    path = checklist_factory(sections(), recommendations=("1. Fix SEC-001 first.", "2. Tidy up SEC-009."))
    data = read_checklist.read_checklist(path, section_config)
    ordered = section_names.order_sections(data.sheet_tab_names, section_config)
    return data, da.analyze(data, ordered, {"owner_keywords": OWNERS})


def test_applicable_denominator_excludes_na(analysis):
    _, a = analysis
    assert (a.total, a.na, a.applicable, a.counts["Pass"]) == (8, 1, 7, 2)


def test_parse_notes_three_lines():
    assert da.parse_notes("Head\n• ev one\n• Action: do it") == ("Head", ["ev one"], "do it")


def test_root_cause_groups_follow_cross_references(analysis):
    _, a = analysis
    assert sorted(a.root_causes[0]) == ["SCALE-009", "SEC-001"]


def test_quick_wins_are_single_setting_fails_outside_root_cause(analysis):
    _, a = analysis
    assert [(q.id, q.setting, q.to) for q in a.quick_wins] == [("SCALE-010", "hideErrorStacks", "true")]
    assert a.remaining_fails == ["SCALE-009"]


def test_owner_split_covers_every_needs_review_item(analysis):
    _, a = analysis
    assert dict(a.owners) == {"Infrastructure": ["ARCH-002"], "Platform team": ["ARCH-001"]}


def test_recommendation_citing_a_pass_item_is_flagged(analysis):
    _, a = analysis
    assert any("SEC-009" in w and "Pass" in w for w in a.warnings)
    assert not any("SEC-001" in w for w in a.warnings)


def test_expand_ids_handles_slash_shorthand():
    assert da.expand_ids("Fix (SCALE-007/008) and SEC-004") == ["SCALE-007", "SCALE-008", "SEC-004"]


def test_narrative_rejects_pass_item_cited_as_problem(analysis):
    _, a = analysis
    with pytest.raises(narrative.NarrativeError, match="SEC-009.*Pass"):
        narrative.validate({"roadmap": {"now": [{"effort": "S", "action": "x", "ids": ["SEC-009"]}]}}, a)


def test_narrative_allows_pass_with_declared_caveat(analysis):
    _, a = analysis
    narrative.validate({"caveats": ["SEC-009"], "roadmap": {"now": [{"effort": "S", "action": "x", "ids": ["SEC-009"]}]}}, a)


def test_narrative_owner_groups_must_equal_needs_review_total(analysis):
    _, a = analysis
    bad = {"owners": {"groups": [{"owner": "X", "asks": [{"id": "ARCH-001", "ask": "a"}]}]}}
    with pytest.raises(narrative.NarrativeError, match="Needs Review total"):
        narrative.validate(bad, a)


def test_narrative_tile_figure_must_trace_to_cited_row(analysis):
    _, a = analysis
    with pytest.raises(narrative.NarrativeError, match="does not appear"):
        narrative.validate({"risk1": {"tiles": [{"number": "777", "label": "x", "id": "SEC-001"}]}}, a)
    narrative.validate({"risk1": {"tiles": [{"number": "98", "label": "x", "id": "SEC-001"}]}}, a)


def test_narrative_unknown_id_and_bad_effort(analysis):
    _, a = analysis
    with pytest.raises(narrative.NarrativeError, match="not in any checklist"):
        narrative.validate({"quick_wins": {"rows": [{"id": "NOPE-001"}]}}, a)
    with pytest.raises(narrative.NarrativeError, match="effort"):
        narrative.validate({"roadmap": {"now": [{"effort": "XL", "action": "x", "ids": []}]}}, a)


def test_narrative_load_errors(tmp_path):
    with pytest.raises(narrative.NarrativeError, match="not found"):
        narrative.load(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"; bad.write_text("{nope")
    with pytest.raises(narrative.NarrativeError, match="not valid JSON"):
        narrative.load(bad)


@pytest.mark.skipif(not common.BRANDING_TEMPLATE.exists(), reason="branding template not present")
def test_v2_build_smoke(checklist_factory, tmp_path):
    from pptx import Presentation
    import build_deck_v2
    import validate_deck

    path = checklist_factory(sections())
    out = tmp_path / "v2.pptx"
    res = build_deck_v2.build_v2(path, "Acme", out, common.BRANDING_TEMPLATE)
    assert res["applicable_count"] == 7 and res["pass_count"] == 2
    assert validate_deck.validate(out) == []
    prs = Presentation(str(out))
    titles = [s.shapes.title.text_frame.text if s.shapes.title is not None else "" for s in prs.slides]
    assert titles[1].startswith("2 of 7 applicable")      # verdict, N/A excluded
    assert any(t.startswith("Appendix") for t in titles)
    assert not any("Thank You" in t or "Table of Contents" in t for t in titles)
    names = {sh.name for s in prs.slides for sh in s.shapes}
    assert {"Headline stat", "Takeaway card 1", "Detail table"} <= names
    cover_text = " ".join(sh.text_frame.text for sh in prs.slides[0].shapes if sh.has_text_frame)
    assert "Generated by" not in cover_text


def test_narrative_default_path_and_staleness(tmp_path):
    assert narrative.default_path(tmp_path / "x_review.xlsx").name == "x_review_narrative.json"
    assert narrative.staleness_warnings({}, "abc") == []
    assert narrative.staleness_warnings({"checklist_sha256": "ABC"}, "abc") == []
    assert "different version" in narrative.staleness_warnings({"checklist_sha256": "zzz"}, "abc")[0]


def test_example_narrative_validates_against_synthetic_checklist(analysis):
    _, a = analysis
    ex = narrative.load(common.REPO_ROOT / "tests" / "fixtures" / "narrative_example.json")
    narrative.validate(ex, a)


@pytest.mark.skipif(not common.BRANDING_TEMPLATE.exists(), reason="branding template not present")
def test_v2_build_autodiscovers_narrative_beside_checklist(checklist_factory, tmp_path):
    import build_deck_v2
    path = checklist_factory(sections())
    (path.with_name(path.stem + "_narrative.json")).write_text(
        json.dumps({"verdict_title": "Auto-found verdict", "checklist_sha256": "stale"}))
    res = build_deck_v2.build_v2(path, "Acme", tmp_path / "o.pptx", common.BRANDING_TEMPLATE)
    assert res["narrative_used"].endswith("_narrative.json")
    assert any("different version" in w for w in res["warnings"])
