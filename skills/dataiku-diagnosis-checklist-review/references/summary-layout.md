# Summary sheet layout (manual fallback)

Use only if `write_summary` is unavailable.

The sheet it writes is what the `dataiku-review-deck-builder` skill's generator reads, so its
layout must not drift. If the tool is not available, write the sheet by hand to this layout and
use these header texts **verbatim**; differently worded headers make the deck show zeros or miss
whole sections.

1. **Metadata rows**, label in column A ending in a colon, value in column B: `Bundle:`,
   `Node / Version:`, `Diagnosis generated:`, `Report generated:` (today, `YYYY-MM-DD`), `Reviewer:`.
2. **Block headers**, each alone in column A, in this order:
   - `Overall Status Counts`
   - `Per-Section Breakdown`
   - `Critical Findings - Must-Have Items Failing`
   - `Other Must-Have Items: Partial / Needs Review`
   - `Priority-Ordered Recommendations`

   Give all five the **identical** font (bold, same size) and fill, and give no other column-A
   cell that style: the generator treats any cell matching it as a block header.
3. Under `Overall Status Counts`: one row per status (`Pass`, `Fail`, `Partial`, `Needs Review`,
   `Not Applicable`) with its count in column B, then a `Total` row.
4. Under `Per-Section Breakdown`: a header row
   `Section | Pass | Fail | Partial | Needs Review | Not Applicable`, then one row per section sheet
   with the tab name exactly as it appears.
5. Under the two must-have blocks: a header row `ID | Section | Title | Status | Key point`, then one
   row per item. If a block has no items, keep its header and column-header row and write no rows
   (never a placeholder such as `None`: the deck would show it as a finding whose ID is "None").
6. Under `Priority-Ordered Recommendations`: one pre-numbered action per row in column A (`1. ...`).

Write every count as a literal integer, never an Excel formula such as `COUNTIF`: openpyxl saves
formulas without cached values, so the deck generator would see them as empty.
