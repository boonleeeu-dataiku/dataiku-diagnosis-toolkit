"""Contracts between components that are authored separately and only meet at runtime:
the bundled checklist template, the checklist-review skill that fills it in, the review
generator that reads it, and the deck-builder skill that relays the generator's output."""

import re

import openpyxl
import pytest

import build_deck
import common
import read_checklist
import section_names
from conftest import REPO_ROOT, RG_DIR, TEMPLATE

REVIEW_SKILL = (REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "SKILL.md").read_text(encoding="utf-8")
DECK_SKILL = (REPO_ROOT / "skills" / "dataiku-review-deck-builder" / "SKILL.md").read_text(encoding="utf-8")
MCP_SERVER = (RG_DIR / "scripts" / "mcp_server.py").read_text(encoding="utf-8")
DECK_SHARED_SRC = (RG_DIR / "scripts" / "deck_shared.py").read_text(encoding="utf-8")  # the cover code reads the metadata labels


@pytest.fixture(scope="module")
def template():
    return openpyxl.load_workbook(TEMPLATE)


def test_template_item_sheets_parse_with_the_deck_generator_schema(template):
    for ws in template.worksheets:
        read_checklist.parse_section_sheet(ws, ws.title)  # raises on any column drift


def test_template_sheet_names_all_have_curated_display_names(template):
    config = common.load_config("section_names.yaml")
    uncurated = [ws.title for ws in template.worksheets
                 if section_names._normalize_key(ws.title) not in config["sections"]]
    assert uncurated == [], "add these to mcp-server-review-generator/config/section_names.yaml (upstream)"


def test_template_ids_unique_and_priorities_known(template):
    ids, bad_priority = [], []
    for ws in template.worksheets:
        for it in read_checklist.parse_section_sheet(ws, ws.title):
            ids.append(it.id)
            if it.priority not in ("must_have", "nice_to_have"):
                bad_priority.append((it.id, it.priority))
    assert len(ids) == len(set(ids)), "duplicate IDs in the template"
    assert bad_priority == []


def test_template_result_columns_are_blank(template):
    for ws in template.worksheets:
        for it in read_checklist.parse_section_sheet(ws, ws.title):
            assert not (it.validation_status or it.evidence_found or it.notes), f"{it.id} is pre-filled"


def test_review_skill_status_vocabulary_matches_deck_generator():
    """The skill's fixed status set must be exactly what build_deck counts and colors;
    any other label silently drops out of the deck."""
    for status in build_deck.STATUS_ORDER:
        assert f"**{status}**" in REVIEW_SKILL, f"SKILL.md no longer lists **{status}**"


SUMMARY_BLOCKS = [
    ("Overall Status Counts", "overall_status_counts"),
    ("Per-Section Breakdown", "per_section_breakdown"),
    ("Critical Findings - Must-Have Items Failing", "critical_findings"),
    ("Other Must-Have Items: Partial / Needs Review", "other_must_have"),
    ("Priority-Ordered Recommendations", "recommendations"),
]


@pytest.mark.parametrize("header,alias_key", SUMMARY_BLOCKS)
def test_review_skill_summary_headers_are_recognised_by_the_deck_generator(header, alias_key):
    """SKILL.md step 6 prescribes these header texts verbatim. Each must be recognised as its
    own block (and only that block), or the deck silently loses or misfiles it."""
    assert f"`{header}`" in REVIEW_SKILL, f"SKILL.md no longer prescribes {header!r}"
    config = common.load_config("section_names.yaml")
    matches = [key for _, key in SUMMARY_BLOCKS if section_names.find_narrative_block(header, key, config)]
    # parse_summary_sheet() takes the first matching alias in SUMMARY_BLOCKS order
    assert matches and matches[0] == alias_key, f"{header!r} is recognised as {matches}"


def test_review_skill_pins_summary_header_formats():
    assert "Claude (AI-assisted review of <bundle name>)" in REVIEW_SKILL
    assert "<nodetype> / DSS <product_version>" in REVIEW_SKILL
    assert "`YYYY-MM-DD`" in REVIEW_SKILL


def test_review_skill_anchor_header_matches_exact_text_lookup():
    """find_section_blocks() locates the anchor by exact (case-insensitive) text."""
    assert SUMMARY_BLOCKS[0][0].lower() == "overall status counts"


def test_review_skill_metadata_labels_are_the_ones_the_deck_reads():
    for label in ("Bundle:", "Node / Version:", "Report generated:"):
        assert f"`{label}`" in REVIEW_SKILL, label
        assert label.rstrip(":") in DECK_SHARED_SRC, f"deck_shared.py no longer reads {label!r}"


def test_deck_skill_lists_the_tools_return_keys():
    skill_keys = set(re.search(r"returns\s+`\{([^}]*)\}`", DECK_SKILL).group(1).replace(" ", "").split(","))
    body = MCP_SERVER.split("def build_platform_review_deck", 1)[1].split("@mcp.tool", 1)[0]
    server_keys = set(re.findall(r'^\s+"(\w+)":', body, re.MULTILINE))
    server_keys |= set(re.findall(r'result\["(\w+)"\]', body))
    assert skill_keys == server_keys


def test_deck_skill_error_phrase_matches_server_message():
    """The skill branches on the literal "Base deck not found" error text."""
    assert '"Base deck not found"' in DECK_SKILL
    assert 'f"Base deck not found: ' in MCP_SERVER


def test_deck_skill_fallback_flag_exists_on_the_tool():
    """The skill's last-resort step passes allow_standard_deck; the tool must accept it."""
    assert "allow_standard_deck" in DECK_SKILL
    assert "allow_standard_deck: bool = False" in MCP_SERVER


def test_deck_skill_requires_a_narrative_when_an_llm_runs_it():
    """The narrative is the judgment text the tool can't derive; skipping it gives a generic deck."""
    for phrase in ("Order of work (required", "checklist_sha256", "narrative_used", "Do not skip this step"):
        assert phrase in DECK_SKILL, f"deck skill no longer says {phrase!r}"


def test_review_skill_hands_off_to_the_deck_builder_with_a_narrative():
    assert "dataiku-review-deck-builder" in REVIEW_SKILL
    assert "_narrative.json" in REVIEW_SKILL


def test_deck_skill_uses_the_narrative_helper_tool_and_flag():
    """The skill drives analyze_checklist and branches on narrative_missing; both must exist in the server."""
    assert "def analyze_checklist" in MCP_SERVER and '"narrative_missing"' in MCP_SERVER
    for phrase in ("analyze_checklist", "narrative_missing"):
        assert phrase in DECK_SKILL


def test_review_skill_drives_write_summary_with_the_tools_real_parameters():
    """The skill tells the model to call write_summary; its argument names and the key-point limit
    must be the ones the server actually has."""
    import write_summary

    sig = MCP_SERVER.split("def write_summary(", 1)[1].split(") ->", 1)[0]
    for param in ("checklist_path", "reviewer", "bundle", "key_points", "recommendations", "node_version",
                  "diagnosis_generated"):
        assert f"`{param}`" in REVIEW_SKILL, f"SKILL.md no longer mentions write_summary's `{param}`"
        assert re.search(rf"\b{param}:", sig), f"mcp_server.write_summary has no `{param}` parameter"
    assert f"<= {write_summary.KEY_POINT_MAX_CHARS} characters" in REVIEW_SKILL


def test_write_summary_headers_are_the_ones_the_skill_prescribes_and_the_reader_matches():
    import write_summary

    assert list(write_summary.HEADERS.values()) == [h for h, _ in SUMMARY_BLOCKS]
    assert write_summary.STATUSES == build_deck.STATUS_ORDER


def test_deck_skill_orders_write_summary_before_the_narrative():
    assert "write_summary" in DECK_SKILL


def test_review_skill_defines_must_have_and_uses_insufficient_evidence_column():
    """Step 6 keys off must-have items and step 4 defers to the checklist's own fallback column."""
    for phrase in ("priority == must_have", "insufficient_evidence_handling", "Claude (AI-assisted review of"):
        assert phrase in REVIEW_SKILL, f"review skill no longer says {phrase!r}"


def test_review_skill_fixes_the_plaintext_credential_summary_line():
    flat = " ".join(REVIEW_SKILL.split())
    assert "Plaintext credential: the internal database password is stored in plaintext in" in flat
    assert "Rotate it and use a secrets store." in flat
