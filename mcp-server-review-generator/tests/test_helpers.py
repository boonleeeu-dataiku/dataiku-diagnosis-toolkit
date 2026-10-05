"""Pure helpers in section_names.py and build_deck.py."""

from pathlib import Path

import build_deck
import common
import deck_shared
import read_checklist
import section_names


def test_normalize_curated_section(section_config):
    sec = section_names.normalize_section_name("  Scalable   Performance, Stability ", section_config)
    assert sec == {"display": "Scalable Performance, Stability", "order": 4, "key": "scalable performance, stability"}


def test_normalize_uncurated_section_falls_back_to_title_case(section_config):
    sec = section_names.normalize_section_name("data governance ", section_config)
    assert sec["display"] == "Data Governance"
    assert sec["order"] == 1000


def test_order_sections_curated_first_then_sheet_order(section_config):
    names = ["Zeta Extra", "Scalable Performance, Stability", "Alpha Extra", "Architecture, Compute & Infrast"]
    ordered = [s["sheet_tab_name"] for s in section_names.order_sections(names, section_config)]
    assert ordered == ["Architecture, Compute & Infrast", "Scalable Performance, Stability", "Zeta Extra", "Alpha Extra"]


def test_find_narrative_block_aliases(section_config):
    assert section_names.find_narrative_block("Recommendations (priority order)", "recommendations", section_config)
    assert section_names.find_narrative_block("Per section breakdown", "per_section_breakdown", section_config)
    assert not section_names.find_narrative_block("Appendix", "recommendations", section_config)


def test_canonical_status_is_case_insensitive():
    assert build_deck._canonical_status(" needs review ") == "Needs Review"
    assert build_deck._canonical_status("Passed") is None


def test_truncate():
    assert build_deck.truncate("short", 10) == "short"
    assert build_deck.truncate("abcdefghijkl", 5) == "abcd…"
    assert build_deck.truncate(None, 5) == ""


def test_strip_leading_number():
    assert build_deck._strip_leading_number("1. Fix it") == "Fix it"
    assert build_deck._strip_leading_number("12) Fix it") == "Fix it"
    assert build_deck._strip_leading_number("Fix 1. it") == "Fix 1. it"
    # one shared, tolerant implementation (v1, v2 and the Summary sheet all use it)
    assert common.strip_leading_number("1 . Fix it") == "Fix it"
    assert common.strip_leading_number(None) == ""


def test_format_month_year():
    assert deck_shared.format_month_year("2026-07-22 10:00") == "Jul 2026"
    assert deck_shared.format_month_year("2026-07-22 08:21 UTC") == "Jul 2026"
    assert deck_shared.format_month_year("") == ""


def test_format_priority():
    assert build_deck.format_priority("must_have") == "Must Have"
    assert build_deck.format_priority("nice_to_have") == "Nice to have"


def test_default_output_path_uses_checklist_date():
    path = common.default_output_path(Path("dku_diagnosis_2026-07-22_review.xlsx"), "Acme Corp!")
    assert path == common.OUTPUT_DIR / "Acme_Corp_Platform_Review_2026-07-22.pptx"


def test_fit_cell_text_shrinks_then_truncates():
    text, size = build_deck._fit_cell_text("short", 2_000_000, 500_000)
    assert (text, size) == ("short", build_deck.TABLE_FONT_FIT_SIZE_STEPS[0])
    text, size = build_deck._fit_cell_text("x" * 100_000, 500_000, 300_000)
    assert size == build_deck.TABLE_FONT_FIT_SIZE_STEPS[-1]
    assert text.endswith("…") and len(text) < 100_000


def test_version_file_is_semver():
    import re

    assert re.fullmatch(r"\d+\.\d+\.\d+", common.VERSION)


def _finding(**kw):
    return read_checklist.ChecklistItem(id="X-1", title="T", priority="must_have", validation_status="Fail",
                                        statement="S", statement_short="", evidence_found="", notes="",
                                        sheet_tab_name="Sheet", **kw)


def test_findings_row_shows_notes_only_and_keeps_evidence_in_speaker_notes():
    it = _finding()
    it.evidence_found, it.notes = "a/b.json: key=1", "Headline\n• point"
    assert build_deck.build_findings_rows([it])[0][5] == "Headline\n• point"
    assert "Evidence: a/b.json: key=1" in build_deck._finding_note_lines(it)
    assert "Notes: Headline\n• point" in build_deck._finding_note_lines(it)


def test_findings_row_falls_back_to_evidence_when_notes_empty():
    it = _finding()
    it.evidence_found = "a/b.json: key=1"
    assert build_deck.build_findings_rows([it])[0][5] == "a/b.json: key=1"


def test_fill_cell_splits_lines_into_paragraphs():
    from office import tables
    cell = ('<a:tc><a:txBody><a:p><a:pPr/><a:r><a:rPr sz="900"/><a:t>x</a:t></a:r></a:p>'
            '</a:txBody></a:tc>')
    out = tables._fill_cell(cell, "Head & co\n• one\n• two")
    assert out.count("<a:p>") == 3
    assert "<a:t>Head &amp; co</a:t>" in out and "<a:t>• two</a:t>" in out
    assert tables._fill_cell(cell, "single").count("<a:p>") == 1


def test_fit_cell_text_counts_each_line_as_a_paragraph():
    one_line = "x" * 40
    multi = "\n".join(["x" * 10] * 4)  # same chars as 1 line of 40, but 4 paragraphs
    _, size_one = build_deck._fit_cell_text(one_line, 2167037, 560000)
    _, size_multi = build_deck._fit_cell_text(multi, 2167037, 560000)
    assert size_multi <= size_one
