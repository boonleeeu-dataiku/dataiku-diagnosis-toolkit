"""Read a completed Dataiku platform-review checklist (.xlsx) into
structured data for the deck generator.

The workbook has a "Summary" sheet (bundle metadata + several narrative
blocks) and one sheet per review section (one row per checklist item, 26
fixed columns). Narrative blocks on the Summary sheet are located
generically -- by matching the visual style (bold/size/fill) of two
structurally-guaranteed anchor headers, "Overall Status Counts" and
"Per-Section Breakdown" -- rather than by hardcoded row numbers, since row
counts vary between checklist instances.
"""

import logging
import re
from dataclasses import dataclass

import openpyxl

import section_names

logger = logging.getLogger(__name__)

REQUIRED_ITEM_COLUMNS = [
    "id", "priority", "check_type", "subtopic", "title", "statement",
    "statement_short", "parameter_hint", "operator", "expected_value", "unit",
    "expected_condition_notes", "supporting_evidence", "contradicting_evidence",
    "insufficient_evidence_handling", "rationale", "dataiku_concepts",
    "source_document", "source_page", "source_section", "confidence",
    "ambiguity_notes", "validation_status", "evidence_found", "notes",
    "validated_at", "validated_by",
]

NON_APPLICABLE_STATUSES = {"pass", "not applicable"}


class ChecklistFormatError(ValueError):
    """Raised when the workbook doesn't match the expected checklist schema."""


@dataclass
class ChecklistItem:
    id: str
    priority: str
    title: str
    statement: str
    statement_short: str
    validation_status: str
    evidence_found: str
    notes: str
    sheet_tab_name: str

    @property
    def slide_statement(self) -> str:
        """Slide-ready statement: `statement_short`, falling back to the full `statement`."""
        return (self.statement_short or self.statement or "").strip()

    @property
    def is_must_have(self) -> bool:
        return (self.priority or "").strip().lower() == "must_have"

    @property
    def is_flagged(self) -> bool:
        status = (self.validation_status or "").strip().lower()
        return status not in NON_APPLICABLE_STATUSES


@dataclass
class ChecklistData:
    bundle_metadata: dict
    overall_counts: dict
    per_section_breakdown: list
    critical_findings: list
    other_must_have: list
    recommendations: list
    items_by_sheet: dict
    sheet_tab_names: list


def _style_signature(cell):
    fill = cell.fill
    fg = fill.fgColor.rgb if fill is not None and fill.fgColor is not None else None
    return (cell.font.bold, cell.font.sz, fg)


def find_section_blocks(ws) -> list[tuple[int, str]]:
    """Scan column A top-to-bottom for header cells; a "header" is any cell
    sharing the style signature of the 'Overall Status Counts' anchor cell
    (found by exact text match, since that label is structurally guaranteed
    to be present in any checklist produced by the sibling checklist-writer
    tooling). Returns [(row, header_text), ...] in document order.
    """
    anchor_row = None
    for row in range(1, ws.max_row + 1):
        val = ws.cell(row=row, column=1).value
        if isinstance(val, str) and val.strip().lower() == "overall status counts":
            anchor_row = row
            break
    if anchor_row is None:
        raise ChecklistFormatError(
            "Summary sheet is missing the 'Overall Status Counts' section header; "
            "this doesn't look like a checklist produced by the shared schema."
        )
    anchor_sig = _style_signature(ws.cell(row=anchor_row, column=1))

    blocks = []
    for row in range(1, ws.max_row + 1):
        cell = ws.cell(row=row, column=1)
        val = cell.value
        if isinstance(val, str) and val.strip() and _style_signature(cell) == anchor_sig:
            blocks.append((row, val.strip()))
    return blocks


def _block_range(blocks: list[tuple[int, str]], index: int, max_row: int) -> tuple[int, int]:
    start = blocks[index][0] + 1
    end = (blocks[index + 1][0] - 1) if index + 1 < len(blocks) else max_row
    return start, end


def parse_bundle_metadata(ws, first_block_row: int) -> dict:
    metadata = {}
    for row in range(1, first_block_row):
        label = ws.cell(row=row, column=1).value
        value = ws.cell(row=row, column=2).value
        if isinstance(label, str) and label.strip().endswith(":"):
            metadata[label.strip().rstrip(":")] = value
    return metadata


def parse_two_col_counts(ws, start_row: int, end_row: int) -> dict:
    counts = {}
    for row in range(start_row, end_row + 1):
        label = ws.cell(row=row, column=1).value
        value = ws.cell(row=row, column=2).value
        if isinstance(label, str) and isinstance(value, (int, float)):
            counts[label.strip()] = int(value)
    return counts


def parse_section_breakdown(ws, start_row: int, end_row: int) -> list[dict]:
    rows = []
    header = None
    for row in range(start_row, end_row + 1):
        vals = [ws.cell(row=row, column=c).value for c in range(1, 7)]
        if vals[0] in (None, ""):
            continue
        if isinstance(vals[0], str) and vals[0].strip().lower() == "section":
            header = [str(v).strip() if v else "" for v in vals]
            continue
        section_name = str(vals[0]).strip()
        cols = header[1:] if header else ["Pass", "Fail", "Partial", "Needs Review", "Not Applicable"]
        counts = {
            col_name: int(v)
            for col_name, v in zip(cols, vals[1:])
            if isinstance(v, (int, float))
        }
        rows.append({"section": section_name, "counts": counts})
    return rows


def parse_id_led_table(ws, start_row: int, end_row: int, num_cols: int = 6) -> list[dict]:
    """Generic parser for the Critical Findings / Other Must-Have blocks:
    a header row starting with 'id', followed by one data row per item.
    Column names become dict keys (lowercased, spaces/slashes -> '_')."""
    rows = []
    header = None
    for row in range(start_row, end_row + 1):
        vals = [ws.cell(row=row, column=c).value for c in range(1, 1 + num_cols)]
        if not any(v not in (None, "") for v in vals):
            continue
        if isinstance(vals[0], str) and vals[0].strip().lower() == "id":
            header = [str(v).strip() if v else "" for v in vals]
            continue
        cols = header if header else [f"col{i}" for i in range(len(vals))]
        row_dict = {}
        for col_name, v in zip(cols, vals):
            if v not in (None, ""):
                key = re.sub(r"[^a-z0-9]+", "_", col_name.lower().strip()).strip("_")
                row_dict[key] = v
        if row_dict:
            rows.append(row_dict)
    return rows


def parse_recommendation_list(ws, start_row: int, end_row: int, num_cols: int = 3) -> list[str]:
    """Two known Summary-sheet Recommendations layouts:

    - a single-column, pre-numbered list ("1. Action text.") with everything
      in column A -- the standard checklist writer's format; or
    - a header-led table ("# | Action | Related IDs") that keeps the action
      text separate from the linked checklist IDs it groups.

    Detected generically (no hardcoded header text): if the first non-blank
    row in range has content beyond column A, it's the table form -- that
    row is a header (its own column A value, e.g. "#", is not itself a
    recommendation) and every column after "Action" is folded into the
    result string as "<header label>: <value>" so nothing is dropped.
    """
    rows_raw = []
    for row in range(start_row, end_row + 1):
        vals = [ws.cell(row=row, column=c).value for c in range(1, 1 + num_cols)]
        if any(v not in (None, "") for v in vals):
            rows_raw.append(vals)
    if not rows_raw:
        return []

    if any(v not in (None, "") for v in rows_raw[0][1:]):
        header = [str(v).strip() if v else "" for v in rows_raw[0]]
        items = []
        for vals in rows_raw[1:]:
            action = str(vals[1]).strip() if vals[1] not in (None, "") else ""
            if not action:
                continue
            extras = [
                f"{col_name or 'Notes'}: {str(v).strip()}"
                for col_name, v in zip(header[2:], vals[2:])
                if v not in (None, "")
            ]
            items.append(action + (f" ({'; '.join(extras)})" if extras else ""))
        return items

    return [str(vals[0]).strip() for vals in rows_raw if isinstance(vals[0], str) and vals[0].strip()]


def parse_summary_sheet(ws, config: dict) -> dict:
    blocks = find_section_blocks(ws)
    bundle_metadata = parse_bundle_metadata(ws, blocks[0][0]) if blocks else {}

    overall_counts, per_section_breakdown = {}, []
    critical_findings, other_must_have, recommendations = [], [], []

    for i, (row, header_text) in enumerate(blocks):
        start, end = _block_range(blocks, i, ws.max_row)
        if section_names.find_narrative_block(header_text, "overall_status_counts", config):
            overall_counts = parse_two_col_counts(ws, start, end)
        elif section_names.find_narrative_block(header_text, "per_section_breakdown", config):
            per_section_breakdown = parse_section_breakdown(ws, start, end)
        elif section_names.find_narrative_block(header_text, "critical_findings", config):
            critical_findings = parse_id_led_table(ws, start, end, num_cols=3)
        elif section_names.find_narrative_block(header_text, "other_must_have", config):
            other_must_have = parse_id_led_table(ws, start, end, num_cols=3)
        elif section_names.find_narrative_block(header_text, "recommendations", config):
            recommendations = parse_recommendation_list(ws, start, end)
        else:
            logger.info(
                "Summary sheet block %r (row %d) did not match any configured "
                "narrative_block_aliases; ignoring it.", header_text, row,
            )

    return {
        "bundle_metadata": bundle_metadata,
        "overall_counts": overall_counts,
        "per_section_breakdown": per_section_breakdown,
        "critical_findings": critical_findings,
        "other_must_have": other_must_have,
        "recommendations": recommendations,
    }


def parse_section_sheet(ws, sheet_tab_name: str) -> list[ChecklistItem]:
    header = [str(c.value).strip() if c.value else "" for c in next(ws.iter_rows(min_row=1, max_row=1))]
    header = header[: len(REQUIRED_ITEM_COLUMNS)]
    if header != REQUIRED_ITEM_COLUMNS:
        missing = [c for c in REQUIRED_ITEM_COLUMNS if c not in header]
        raise ChecklistFormatError(
            f"Sheet {sheet_tab_name!r} does not have the expected checklist column "
            f"header. Missing/misnamed column(s): {missing or 'header order differs'}."
        )

    col = {name: idx + 1 for idx, name in enumerate(REQUIRED_ITEM_COLUMNS)}
    items = []
    for row in ws.iter_rows(min_row=2):
        item_id = row[col["id"] - 1].value
        if not item_id:
            continue

        def get(name):
            return row[col[name] - 1].value

        items.append(
            ChecklistItem(
                id=str(get("id")).strip(),
                priority=str(get("priority") or "").strip(),
                title=str(get("title") or "").strip(),
                statement=str(get("statement") or "").strip(),
                statement_short=str(get("statement_short") or "").strip(),
                validation_status=str(get("validation_status") or "").strip(),
                evidence_found=str(get("evidence_found") or "").strip(),
                notes=str(get("notes") or "").strip(),
                sheet_tab_name=sheet_tab_name,
            )
        )
    return items


def read_checklist(xlsx_path, config: dict) -> ChecklistData:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    if "Summary" not in wb.sheetnames:
        raise ChecklistFormatError(f"{xlsx_path} has no 'Summary' sheet.")

    section_sheet_names = [n for n in wb.sheetnames if n != "Summary"]
    if not section_sheet_names:
        raise ChecklistFormatError(f"{xlsx_path} has no checklist-item sheets besides 'Summary'.")

    summary = parse_summary_sheet(wb["Summary"], config)

    items_by_sheet = {}
    for name in section_sheet_names:
        items_by_sheet[name] = parse_section_sheet(wb[name], name)

    return ChecklistData(
        bundle_metadata=summary["bundle_metadata"],
        overall_counts=summary["overall_counts"],
        per_section_breakdown=summary["per_section_breakdown"],
        critical_findings=summary["critical_findings"],
        other_must_have=summary["other_must_have"],
        recommendations=summary["recommendations"],
        items_by_sheet=items_by_sheet,
        sheet_tab_names=section_sheet_names,
    )
