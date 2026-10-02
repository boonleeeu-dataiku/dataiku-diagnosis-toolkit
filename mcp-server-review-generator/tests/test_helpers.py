"""Pure helpers in section_names.py and build_deck.py."""

from pathlib import Path

import build_deck
import common
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


def test_format_month_year():
    assert build_deck.format_month_year("2026-07-22 10:00") == "Jul 2026"
    assert build_deck.format_month_year("2026-07-22 08:21 UTC") == "Jul 2026"
    assert build_deck.format_month_year("") == ""


def test_format_priority():
    assert build_deck.format_priority("must_have") == "Must Have"
    assert build_deck.format_priority("nice_to_have") == "Nice to have"


def test_default_output_path_uses_checklist_date():
    path = build_deck.default_output_path(Path("dku_diagnosis_2026-07-22_review.xlsx"), "Acme Corp!")
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
