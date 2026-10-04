---
name: "dataiku-diagnosis-checklist-review"
description: "Evaluate a Dataiku DSS diagnosis bundle against a checklist spreadsheet using the dataiku-diagnosis-reader tool, filling in validation results and a summary tab. Falls back to a bundled default checklist template if the user doesn't have one. Use when the user asks to review/validate a Dataiku diagnosis against a checklist, or run a Dataiku instance health/compliance review."
---

# Dataiku diagnosis checklist review

Given (1) a Dataiku DSS diagnosis bundle directory and (2) a checklist spreadsheet
listing check items (typically columns like `id`, `priority`, `check_type`,
`statement`, `parameter_hint`, `expected_value`, `supporting_evidence`,
`contradicting_evidence`, and empty result columns such as `validation_status`,
`evidence_found`, `notes`, `validated_at`, `validated_by`), evaluate every row
against the bundle's actual contents and write the results back into the
spreadsheet, plus add/update a Summary tab.

## Reference files (in this skill's `references/` directory)

- `calibrations.md` — **read in full before evaluating any row** (step 4). It holds the user's
  check-specific interpretations, which override a literal reading of the checklist.
- `summary-layout.md` — manual Summary layout. Read only if `write_summary` is unavailable (step 6).

## 0. Inputs, access and tools

- If the user hasn't given both paths, ask for the diagnosis bundle path and the checklist file
  path, nothing else up front. Start once you have both.
- Never pick a checklist yourself, even when the folder holds one obvious candidate or several
  similar templates (e.g. dated `*_checklist_template.xlsx` copies): a wrong guess silently changes
  the results. Ask, or offer the bundled default.
- If the user has no checklist handy, offer the bundled default template at
  `resources/checklist_template.xlsx` (relative to this skill's own directory), and say plainly once
  you proceed that you're using the default rather than a user-supplied checklist.
- If this session is linked to the user's computer (remote-devices tools present) and the paths are
  local, request folder access to the common parent directory of both
  (`device_request_folder_access`), then `device_stage_files` the checklist into the container to
  read/write it, and `device_list_dir` (recursive) on the bundle to see its structure.
- **How to read the bundle comes from the reader, not from this skill.** Before touching the
  bundle, load the `dataiku-diagnosis-reader` skill. If skills can't be loaded here, read the
  reader MCP server's `skill-guide`, `reference-limitations` and `reference-listings-and-manifests`
  resources instead. Use its `lookup-table` / `data-dir-config` references to find where a setting
  lives.
- Load the reader's `run_orient` tool if deferred (`ToolSearch` with `select:...run_orient`, using
  whatever prefix — bare or `mcp__remote-devices__` — is present in the tool list). The reader has
  no file-reading tool: read bundle files with your normal read/search tools (or the linked
  device's shell, `device_bash`), following the reader's `reference-limitations` ("Large-file
  hazards") and `reference-listings-and-manifests` guidance: grep/head/wc the big files, never
  load them whole. If you find the reader lacks a layout fact you need, say so in your final
  summary rather than recording it in this skill.
- Load the `xlsx` skill before reading/writing the spreadsheet.
- If the checklist has a version-currency check, confirm a web search tool is available; it is
  needed to look up the latest Dataiku DSS release.

### Secrets

Bundles hold live credentials, and tool output lands in the transcript. Follow the reader's
secret-handling guidance; never copy a secret into `evidence_found`, `notes`, the narrative or the
deck. If one does get printed, say so in your final summary, name the file, and tell the user to
rotate it. (The reader's guidance is being added upstream; see `docs/upstream-reader-spec.md`.)

## 1. Orient

Run `run_orient` on the bundle root first. It reports node type/version, the
largest files, and which key troubleshooting files are present. This
tells you what evidence is realistically available before you plan reads.

## 2. Read the checklist fully

Dump every sheet's rows (id, priority, check_type, statement, parameter_hint,
operator, expected_value, supporting_evidence, contradicting_evidence,
rationale, source references) into a working file — don't try to hold 50+
rows of context in your head. Note the exact result-column headers and their
column positions per sheet (they may differ sheet to sheet).

## 3. Plan evidence gathering by theme, not by row

Group checklist rows by the source they need (settings, host/OS, logs, crash dumps, deployers,
clusters) and read each source once for all of its rows, rather than re-reading it per row. Find
each source and the safe way to read it via the reader's `lookup-table` and the other reader
references. Never read a large file whole (the reader's `listings-and-manifests` reference covers
the safe patterns).

## 4. Evaluate every row

First read `references/calibrations.md` in full and apply it to every matching row.

For each checklist item, decide one of a small fixed set of statuses (keep
this consistent across the whole workbook): **Pass**, **Fail**, **Partial**,
**Needs Review**, **Not Applicable**. Use "Not Applicable" when the check is
conditional (e.g., "if using Snowflake") and the precondition isn't met.
Use "Needs Review" honestly for anything requiring a live functional test,
an external system (Fleet Manager, K8s cluster metrics, CMDB), or a
customer conversation that a static diagnostic snapshot cannot answer —
don't guess Pass/Fail on those.

For each item, write:
- `evidence_found`: the audit trail — concrete citations with exact file
  path(s) and the specific key/value or log line(s) that support the finding.
  This stays detailed; it is not shown on slides. Don't put recommendations
  here.
- `notes`: the slide-ready summary. The deck builder shows this text to the
  customer in a table cell, so it must be crisp, scannable and self-contained
  (see "Format of `notes`" below). It carries the verdict, the decisive
  values, and the recommendation or caveat, and cross-references related
  findings by id when they're causally linked (e.g., an OOM crash pattern
  linked to a concurrency-limit setting).
- `validated_at` / `validated_by`: today's date and a reviewer label noting
  this was an AI-assisted review against the specific bundle.

### Format of `notes`

Plain text, no markdown. One headline line, then bullets, separated by
newlines, each bullet starting with `• `:

```
<Headline: verdict + impact, ≤ 80 chars>
• <Key fact with the actual value or count, ≤ 90 chars>
• <Key fact or "so what", ≤ 90 chars>
• Action: <one concrete recommendation, ≤ 90 chars>
```

- **Length:** at most ~320 characters in total and at most 3 bullets under
  the headline. For **Pass** and **Not Applicable**, use the headline plus at
  most one bullet, ≤ 140 characters in total.
- **Self-contained:** carry the decisive values (e.g. `backend.xmx=2g`,
  `4 OOM crashes in 30 days`) so a reader needs nothing else. Do **not**
  include file paths or JSON key dumps; those belong in `evidence_found`.
- **Impact first:** lead with what it means, not how you found it. One idea
  per bullet, fragments rather than sentences, no filler.
- **Cross-references:** a final bullet such as `• See SEC-004 (root cause)`
  when items are causally linked.
- **Needs Review:** the `Action:` bullet must say what to verify and with
  whom (e.g. `Action: confirm with infra team`).

Good:

```
Backend heap too small for workload
• backend.xmx=2g on 64GB host
• 4 OOM crashes in 30 days
• Action: raise to 8g+; see PERF-003
```

Bad (too long, method-first, file paths):

```
In apps/dss/design/<some config file> the backend.xmx key is set to 2g, and then
when we looked at the crash dump we found OutOfMemoryError ...
```

Look actively for causal chains across items (e.g., a resource limit set to
a disabling value, paired with crash dumps and recurring error-log entries,
all pointing to one root cause) — call these out explicitly and prioritize
them, rather than reporting each row in isolation.

## 5. Write results back with openpyxl

Match each row by its `id` column (not by row number) when writing results,
so the mapping is robust to row reordering. Verify every id in the sheet got
a result and every result was consumed (no silent mismatches) before saving.

## 6. Add/update a Summary sheet

Once every item's `validation_status` is filled in, call the `write_summary` tool of the
`dataiku-review-generator` MCP server. It recreates the `Summary` sheet as the first tab, so
re-running is idempotent. It computes the metadata labels, counts, per-section tallies and finding
rows (ID, Section, Title, Status) from the section sheets and applies one fixed style. You supply
only the judgment text:

- `checklist_path`, `reviewer`, `bundle`, and optionally `node_version` and `diagnosis_generated`.
- `key_points`: `{item id: one line, <= 90 characters}` for **every** must-have item that is Fail,
  Partial or Needs Review, and for no other item. Echo the headline of the item's `notes`. The key
  order sets the row order within each block. List Fail items most causally central first.
- `recommendations`: the ordered actions, linked issues together and root cause before its
  symptoms. Leave out the numbering; the tool adds `1. `, `2. `, ...

The tool fails without touching the file if a key point is missing, extra, too long or multi-line,
or if any item has a blank or unknown status. Fix the input and call it again. It also re-reads
the saved sheet as the deck generator will and compares it to what it meant to write.

Call it **before** drafting the deck narrative: the narrative pins a hash of the final file, so
changing the Summary afterwards makes the narrative look stale.

If the tool is not available, read `references/summary-layout.md` and write the sheet by hand to
that layout. The deck generator reads this sheet, so its layout must not drift. Use the header
texts `Overall Status Counts`, `Per-Section Breakdown`,
`Critical Findings - Must-Have Items Failing`, `Other Must-Have Items: Partial / Needs Review` and
`Priority-Ordered Recommendations` **verbatim**, and the metadata labels `Bundle:`,
`Node / Version:`, `Diagnosis generated:`, `Report generated:`, `Reviewer:`.

## 7. Deliver

Send the updated file to the conversation. If the source file came from the
user's linked computer, write the result back to the same path via
`device_commit_files` as well, and say so in one line. If you used the
bundled default template instead of a user-supplied checklist, there is no
original path to write back to — just name the output after the diagnosis
bundle (e.g. `<bundle-name>_checklist_review.xlsx`) and send it back to the
conversation. Give a short summary of headline results (counts + the 1-3
most important findings) rather than repeating the whole checklist back in
chat.

If the user also asked for a deck (or a "report and powerpoint"), continue with the
`dataiku-review-deck-builder` skill and follow its order of work in full, including drafting the
`<checklist_stem>_narrative.json` from this bundle's results before building. Do not build the deck
without a narrative; if you cannot, say so in your final summary.
