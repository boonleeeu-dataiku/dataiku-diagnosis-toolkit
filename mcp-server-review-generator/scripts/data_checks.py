"""Checklist-data helpers shared by every deck style: the Summary-vs-section-sheet
consistency checks (`check_data_consistency`/`collect_data_warnings`) and the
small data-shape helpers they rest on. No deck or slide knowledge lives here, so a
style can call these without importing another style's builder."""

import logging
from pathlib import Path

import common
import read_checklist
import section_names

logger = logging.getLogger("data_checks")


def items_by_id(data: read_checklist.ChecklistData) -> dict:
    """id -> ChecklistItem across every section sheet -- the authoritative
    source for an item's title/validation_status, which the Summary sheet's
    Critical Findings/Other Must-Have blocks only restate."""
    return {
        str(it.id).strip(): it
        for items in data.items_by_sheet.values()
        for it in items
    }


def build_scorecard_rows(data: read_checklist.ChecklistData, ordered_sections: list) -> list:
    # Keyed by normalized name on both sides: parse_section_breakdown()
    # strips the Summary sheet's section names, but a raw sheet tab name can
    # carry stray whitespace (e.g. a trailing space), which would otherwise
    # silently miss the lookup and zero out that section's row.
    breakdown_by_section = {
        section_names._normalize_key(b["section"]): b["counts"] for b in data.per_section_breakdown
    }
    rows = []
    totals = {status: 0 for status in read_checklist.STATUSES}
    for sec in ordered_sections:
        counts = breakdown_by_section.get(section_names._normalize_key(sec["sheet_tab_name"]), {})
        row = [sec["display"]]
        for status in read_checklist.STATUSES:
            v = int(counts.get(status, 0))
            row.append(str(v))
            totals[status] += v
        rows.append(row)
    if rows:
        rows.append(["Total"] + [str(totals[status]) for status in read_checklist.STATUSES])
    return rows


def check_data_consistency(data: read_checklist.ChecklistData, ordered_sections: list,
                           section_config: dict, style: str = "v1") -> list:
    """Cross-checks between the Summary sheet and the section sheets that
    structural validation (validate_deck.py) can't see -- each one a case
    where the deck would still build and look plausible, but show wrong or
    missing numbers/labels. Returns human-readable warning strings (empty if
    everything agrees); surfaced by main() and the MCP tool so a caller is
    told directly rather than having to spot it by rendering the deck.

    `style` only changes how two warnings describe the outcome: v1 leaves an
    unrecognised-status item out of the counts, v2 counts it as Needs Review;
    on a duplicate ID v1 shows every row, v2 keeps the first."""
    warnings = []

    configured = section_config.get("sections", {})
    breakdown_keys = {section_names._normalize_key(b["section"]) for b in data.per_section_breakdown}
    for sec in ordered_sections:
        if sec["key"] not in configured:
            warnings.append(
                f"Section sheet {sec['sheet_tab_name']!r} has no curated entry in config/section_names.yaml; "
                f"shown as {sec['display']!r}."
            )
        if data.per_section_breakdown and sec["key"] not in breakdown_keys:
            warnings.append(
                f"Section sheet {sec['sheet_tab_name']!r} has no row in the Summary sheet's Per-Section "
                f"Breakdown; its scorecard row will show all zeros."
            )

    scorecard = build_scorecard_rows(data, ordered_sections)
    if scorecard and data.overall_counts:
        total_row = scorecard[-1]
        for i, status in enumerate(read_checklist.STATUSES, start=1):
            overall = int(data.overall_counts.get(status, 0))
            if int(total_row[i]) != overall:
                warnings.append(
                    f"Results by Section total for {status} is {total_row[i]}, but Overall Status Counts "
                    f"says {overall}."
                )

    item_count = sum(len(v) for v in data.items_by_sheet.values())
    summary_total = data.overall_counts.get("Total")
    if summary_total not in (None, "") and int(summary_total) != item_count:
        warnings.append(
            f"Overall Status Counts says Total {int(summary_total)}, but the section sheets hold "
            f"{item_count} items; the deck shows {item_count}."
        )

    outcome = ("are counted as Needs Review in this deck" if style == "v2"
               else "are left out of status counts/colors")
    for sheet, items in data.items_by_sheet.items():
        unknown = sorted({it.validation_status for it in items
                          if it.validation_status and read_checklist.canonical_status(it.validation_status) is None})
        if unknown:
            ids = [it.id for it in items if it.validation_status in unknown]
            warnings.append(
                f"Section sheet {sheet!r} uses unrecognized validation_status value(s) {unknown} "
                f"(items {ids}); those items {outcome} (expected one of {read_checklist.STATUSES})."
            )
        blank = [it.id for it in items if not (it.validation_status or "").strip()]
        if blank:
            warnings.append(
                f"Section sheet {sheet!r} has item(s) {blank} with a blank validation_status; those "
                f"items {outcome} (expected one of {read_checklist.STATUSES})."
            )

    seen, dupes = set(), []
    for items in data.items_by_sheet.values():
        for it in items:
            key = str(it.id).strip()
            if key in seen and key not in dupes:
                dupes.append(key)
            seen.add(key)
    if dupes:
        shown = "only the first occurrence is used" if style == "v2" else "every row is shown"
        warnings.append(f"Duplicate item ID(s) {dupes} appear on more than one row; {shown}. "
                        f"Give each item a unique ID.")

    by_id = items_by_id(data)
    for block_name, entries in (("Critical Findings", data.critical_findings),
                                ("Other Must-Have Items", data.other_must_have)):
        for entry in entries:
            entry_id = str(entry.get("id", "")).strip()
            item = by_id.get(entry_id)
            if item is None:
                warnings.append(f"{block_name} lists ID {entry_id!r}, which isn't in any section sheet.")
                continue
            summary_status = entry.get("status")
            if summary_status and read_checklist.canonical_status(str(summary_status)) != read_checklist.canonical_status(item.validation_status):
                warnings.append(
                    f"{block_name} shows {entry_id} as {summary_status!r}, but its section sheet says "
                    f"{item.validation_status!r}."
                )
            if block_name == "Critical Findings" and read_checklist.canonical_status(item.validation_status) != "Fail":
                warnings.append(
                    f"Critical Findings lists {entry_id}, but its section sheet status is "
                    f"{item.validation_status!r}, not Fail."
                )
    return warnings


def collect_data_warnings(checklist_path: Path) -> list:
    """check_data_consistency() for a checklist file, loading its own config
    the same way build_deck() does."""
    section_config = common.load_config("section_names.yaml")
    data = read_checklist.read_checklist(checklist_path, section_config)
    ordered_sections = section_names.order_sections(data.sheet_tab_names, section_config)
    return check_data_consistency(data, ordered_sections, section_config)
