"""check_data_consistency() / collect_data_warnings() -- one test per warning
type, plus regression tests for the silent-wrong-output bugs fixed in v0.1.4
and v0.1.5 (see CHANGELOG.md). These cover the cases where a deck still builds
and looks plausible but shows wrong numbers or labels."""

import pytest

import build_deck
import read_checklist
import section_names
from conftest import STATUSES, default_sections, item


def _load(path, section_config):
    data = read_checklist.read_checklist(path, section_config)
    return data, section_names.order_sections(data.sheet_tab_names, section_config)


def _warnings(path, section_config):
    data, ordered = _load(path, section_config)
    return build_deck.check_data_consistency(data, ordered, section_config)


def test_self_consistent_checklist_has_no_warnings(checklist_factory):
    assert build_deck.collect_data_warnings(checklist_factory()) == []


def test_uncurated_section_name_warns(checklist_factory, section_config):
    sections = {"Brand New Section": [item("NEW-001", "Pass")]}
    warnings = _warnings(checklist_factory(sections=sections), section_config)
    assert any("'Brand New Section' has no curated entry" in w for w in warnings)


def test_section_missing_from_breakdown_warns(checklist_factory, section_config):
    breakdown = {"Architecture, Compute & Infrast": {"Pass": 1, "Fail": 1, "Needs Review": 1}}
    warnings = _warnings(checklist_factory(breakdown=breakdown), section_config)
    assert any("'Enterprise-grade Security, Perm' has no row" in w for w in warnings)


def test_scorecard_total_disagreeing_with_overall_counts_warns(checklist_factory, section_config):
    overall = {s: 1 for s in STATUSES}
    overall["Fail"] = 5
    warnings = _warnings(checklist_factory(overall=overall), section_config)
    assert any("total for Fail is 1, but Overall Status Counts says 5" in w for w in warnings)


def test_total_row_disagreeing_with_item_count_warns(checklist_factory, section_config):
    warnings = _warnings(checklist_factory(total_override=99), section_config)
    assert any("says Total 99, but the section sheets hold 6 items" in w for w in warnings)


def test_unknown_status_warns(checklist_factory, section_config):
    sections = default_sections()
    sections["Architecture, Compute & Infrast"].append(item("ARCH-004", "Passed"))
    warnings = _warnings(checklist_factory(sections=sections), section_config)
    assert any("unrecognized validation_status value(s) ['Passed']" in w for w in warnings)


def test_summary_id_not_in_any_sheet_warns(checklist_factory, section_config):
    critical = [{"id": "GHOST-001", "title": "Ghost", "status": "Fail"}]
    warnings = _warnings(checklist_factory(critical=critical), section_config)
    assert any("lists ID 'GHOST-001', which isn't in any section sheet" in w for w in warnings)


def test_summary_status_disagreeing_with_sheet_warns(checklist_factory, section_config):
    other = [{"id": "SEC-001", "title": "x", "status": "Needs Review"}]  # sheet says Partial
    path = checklist_factory(other=other, other_cols=("ID", "Title", "Status"))
    warnings = _warnings(path, section_config)
    assert any("shows SEC-001 as 'Needs Review', but its section sheet says 'Partial'" in w for w in warnings)


def test_summary_status_in_fourth_column_is_checked(checklist_factory, section_config):
    other = [{"id": "SEC-001", "section": "x", "title": "x", "status": "Needs Review"}]
    warnings = _warnings(checklist_factory(other=other), section_config)
    assert any("shows SEC-001 as 'Needs Review'" in w for w in warnings)


def test_critical_finding_that_is_not_fail_warns(checklist_factory, section_config):
    critical = [{"id": "ARCH-001", "title": "x", "status": "Needs Review"}]
    warnings = _warnings(checklist_factory(critical=critical), section_config)
    assert any("Critical Findings lists ARCH-001" in w and "not Fail" in w for w in warnings)


# --- Regressions -----------------------------------------------------------

def test_regression_v014_tab_name_with_trailing_whitespace(checklist_factory, section_config):
    """v0.1.4: a section tab with stray whitespace (the default template's
    "Advanced Security Options (DSS ") zeroed its scorecard row."""
    sections = {"Advanced Security Options (DSS ": [item("ADVSEC-001", "Fail"), item("ADVSEC-002", "Pass")]}
    data, ordered = _load(checklist_factory(sections=sections), section_config)

    assert ordered[0]["display"] == "Advanced Security Options"
    rows = build_deck.build_scorecard_rows(data, ordered)
    assert rows[0] == ["Advanced Security Options", "1", "1", "0", "0", "0"]
    assert build_deck.check_data_consistency(data, ordered, section_config) == []


def test_regression_v014_summary_blocks_without_title_status_columns(checklist_factory, section_config):
    """v0.1.4: Critical Findings / Other Must-Have showed blank titles and
    "Needs Review" when the Summary block had no Title/Status column."""
    path = checklist_factory(
        critical_cols=("ID",), critical=[{"id": "ARCH-002"}],
        other_cols=("ID",), other=[{"id": "SEC-001"}],
    )
    data, ordered = _load(path, section_config)

    assert build_deck.build_critical_finding_blocks(data, ordered) == [
        ("ARCH-002", "Title of ARCH-002", "Architecture, Compute & Infrastructure"),
    ]
    other_rows = build_deck.build_other_must_have_rows(data, {})
    assert other_rows[0] == ["SEC-001", "Title of SEC-001", "Partial"]


def test_regression_v015_no_total_row(checklist_factory, section_config):
    """v0.1.5: a missing Total row made the chapter divider say "0 checklist
    items assessed". The item count now comes from the section sheets, and a
    missing Total row is not itself a warning."""
    data, ordered = _load(checklist_factory(include_total=False), section_config)
    assert "Total" not in data.overall_counts
    assert sum(len(v) for v in data.items_by_sheet.values()) == 6
    assert build_deck.check_data_consistency(data, ordered, section_config) == []


def test_regression_v015_critical_findings_without_section_column(checklist_factory, section_config):
    """v0.1.5: cards showed no section when the block had no Section column."""
    path = checklist_factory(critical_cols=("ID", "Title", "Status"))
    data, ordered = _load(path, section_config)
    _, _, section = build_deck.build_critical_finding_blocks(data, ordered)[0]
    assert section == "Architecture, Compute & Infrastructure"


def test_regression_v015_truncated_section_name_uses_curated_display(checklist_factory, section_config):
    """v0.1.5: cards showed the Excel-truncated tab name from the block's own
    Section column instead of the curated display name."""
    sections = {"Advanced Security Options (DSS ": [item("ADVSEC-001", "Fail")]}
    data, ordered = _load(checklist_factory(sections=sections), section_config)
    _, _, section = build_deck.build_critical_finding_blocks(data, ordered)[0]
    assert section == "Advanced Security Options"
    _, _, top_section = build_deck.build_top_risk(data, {}, ordered)
    assert top_section == "Advanced Security Options"
