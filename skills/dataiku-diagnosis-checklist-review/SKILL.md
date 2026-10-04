---
name: "dataiku-diagnosis-checklist-review"
description: "Evaluate a Dataiku DSS diagnosis bundle against a checklist spreadsheet using the dataiku-diagnosis-reader skill, filling in validation results and a summary tab. Falls back to a bundled default checklist template if the user doesn't have one. Use when the user asks to review/validate a Dataiku diagnosis against a checklist, or run a Dataiku instance health/compliance review."
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
- **How to read the bundle comes from the reader, not from this skill.** Before touching the
  bundle, load the `dataiku-diagnosis-reader` skill. If skills can't be loaded here, read the
  reader's `SKILL.md` and its `references/limitations.md` and `references/listings-and-manifests.md`
  files directly. Use its `lookup-table` / `data-dir-config` references to find where a setting
  lives.
- Read bundle files with your normal read/search tools, following the reader's `limitations.md`
  ("Large-file hazards") and `listings-and-manifests.md`: grep/head/wc the big files, never load
  them whole. If the reader lacks a layout fact you need, say so in your final summary rather than
  recording it in this skill.
- Load the `xlsx` skill before reading/writing the spreadsheet.
- If the checklist has a version-currency check, confirm a web search tool is available; it is
  needed to look up the latest Dataiku DSS release (procedure below).

### Files on a linked computer

Only when this session is linked to the user's computer (remote-devices tools present) and the
paths are local: request folder access to the common parent of both
(`device_request_folder_access`), `device_stage_files` the checklist into the container, run
`orient.sh` and bundle reads through `device_bash`, and `device_list_dir` (recursive) to see the
bundle's structure. At the end, write the result back with `device_commit_files` (step 7).

The `dataiku-review-generator` tools (`write_summary`, `analyze_checklist`, the deck build) run on
the user's computer, not in your container, so they only see device paths. Pass the device path as
`checklist_path`. Anything you write in the container (checklist, narrative) must be committed
with `device_commit_files` before you call them. After `write_summary` rewrites the checklist on
the device, your container copy is stale: re-stage it before editing again. If `orient.sh` cannot
be run (it lives in the plugin, not on the device), follow the reader's fallback for orienting by
hand and say so in your report.

### Secrets

Follow the reader's "Handling secrets" section. In addition, never copy a secret into
`evidence_found`, `notes`, the narrative or the deck, and if one does get printed, say so in your
final summary, name the file, and tell the user to rotate it.

## 1. Orient

Run the reader's `scripts/orient.sh <bundle_root>` first. It reports node type/version, the
largest files, and which key troubleshooting files are present. This
tells you what evidence is realistically available before you plan reads.

If it shows a node type the reader hasn't verified (e.g. `deployer`) or no data-dir mirror, say what
the bundle cannot support and mark the rows that depend on it **Needs Review**, not Fail.

## 2. Read the checklist fully

Dump every sheet's rows into a working file — don't try to hold 50+ rows of context in your head.
Keep at least `id`, `priority`, `check_type`, `statement`, `parameter_hint`, `operator`,
`expected_value`, `unit`, `expected_condition_notes`, `supporting_evidence`, `contradicting_evidence`,
`insufficient_evidence_handling` and `ambiguity_notes` when present. Note the exact result-column
headers and their column positions per sheet (they may differ sheet to sheet).

`priority` is `must_have` or `nice_to_have`. "Must-have" below means `priority == must_have`.

## 3. Plan evidence gathering by theme, not by row

Group checklist rows by the source they need (settings, host/OS, logs, crash dumps, deployers,
clusters) and read each source once for all of its rows, rather than re-reading it per row. Find
each source via the reader's `lookup-table` and the other reader references.

## 4. Evaluate every row

First read `references/calibrations.md` in full and apply it to every matching row. Where a row's
`insufficient_evidence_handling` says what to do when the bundle lacks the evidence, follow it; a
matching calibration overrides it.

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
- `validated_at` / `validated_by`: today's date (`YYYY-MM-DD`) and, verbatim,
  `Claude (AI-assisted review of <bundle name>)`.

### Format of `notes`

Plain text, no markdown. One headline line, then bullets, separated by
newlines, each bullet starting with `• `:

```
<Headline: verdict + impact, ≤ 80 chars>
• <Key fact with the actual value or count, ≤ 80 chars>
• <Key fact or "so what", ≤ 80 chars>
• Action: <one concrete recommendation, ≤ 80 chars>
```

- **Length:** at most 320 characters in total and at most 3 bullets under
  the headline. For **Pass** and **Not Applicable**, use the headline plus at
  most one bullet, ≤ 140 characters in total.
- **Not Applicable headline:** `Not applicable: <one reason>` (e.g. `Not applicable: no local
  Hugging Face`), never a chain of colons.
- **Self-contained:** carry the decisive values (e.g. `backend.xmx=2g`,
  `4 OOM crashes in 30 days`) so a reader needs nothing else. Do **not**
  include file paths or JSON key dumps; those belong in `evidence_found`.
- **Impact first:** lead with what it means, not how you found it. One idea
  per bullet, fragments rather than sentences, no filler.
- **Cross-references:** a final bullet such as `• See SEC-004 (root cause)`
  when items are causally linked.
- **Needs Review:** the `Action:` bullet must say what to verify and with
  whom, naming a team so the deck can suggest an owner (e.g. `Action: confirm with infra team`,
  `security team`, `platform team`).

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

### Version-currency lookup

Which status to give is in `references/calibrations.md`. To find the latest GA release: use the
**extended** web-search mode every run (a standard search can miss a newer major). Search "Dataiku
DSS latest version release notes", then once more for the next major above the one found (e.g.
"Dataiku DSS 15 release notes"). Take the highest GA version confirmed by an official Dataiku source
(release notes, changelog, docs.dataiku.com). If results are links only, `WebFetch` the official
release-notes page for the newest major. Never answer from training knowledge.

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
- `key_points`: `{item id: one line, <= 90 characters}` for **every** must-have item (`priority == must_have`) that is Fail,
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

Before delivering, check: every id has one of the five statuses; each `notes` is within budget with
no file paths or secrets; the Summary was written after the last edit.

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
`dataiku-review-deck-builder` skill and follow its order of work in full, including the narrative
(`<checklist_stem>_narrative.json`). Do not build the deck without one; if you cannot, say so in your
final summary.
