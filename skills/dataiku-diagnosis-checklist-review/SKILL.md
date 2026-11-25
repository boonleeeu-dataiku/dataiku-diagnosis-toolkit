---
name: "dataiku-diagnosis-checklist-review"
description: "Review a Dataiku DSS diagnosis bundle (a dku_diagnosis_* folder or an unzipped diagnosis.zip) against a checklist spreadsheet: fills in validation_status, evidence_found and slide-ready notes for every check, then adds a Summary tab. Falls back to a bundled default checklist when the user has none. Use whenever the user wants to review, validate, audit, score or health-check a Dataiku instance or diagnosis against a checklist, fill in the platform-review checklist, or run a Dataiku compliance or best-practice review, even if they never say 'checklist'. Does not do log-error triage (that is the separate, off-by-default dataiku-diagnosis-log-review) and does not build the PowerPoint from a finished review (that is dataiku-review-deck-builder)."
---

# Dataiku diagnosis checklist review

Given (1) a Dataiku DSS diagnosis bundle directory and (2) a checklist spreadsheet of check items with empty result
columns (`validation_status`, `evidence_found`, `notes`, `validated_at`, `validated_by`), evaluate every row against the
bundle's actual contents, write the results back into the spreadsheet, and add or update a Summary tab.

The work splits between code and judgment. Scripts decide what the facts settle by rule (step 2); you decide the rest and
write the words around every status (step 4). Keeping that split is what makes two runs on the same bundle agree.

**Log analysis is off here.** The log review is experimental and runs only when the user explicitly asks for it. Do not run
the reader's `scripts/logscan.py`, do not invoke the log-review skill and do not produce log findings or a log workbook
as part of this review. Reading a specific log line as evidence for a single check stays as it is.

## Reference files (in this skill's `references/` directory)

| File | Read it |
|---|---|
| `calibrations.md` | **In full before evaluating any row** (step 4). It holds the user's check-specific interpretations, which override a literal reading of the checklist: what to write around a rule-decided status, and the status logic of checks no rule decides. |
| `notes-format.md` | Before writing the first `notes` (step 4). The `notes` format and length budget. |
| `secrets.md` | Before touching the bundle. What must never reach the workbook, and the fixed wording for reporting a plaintext credential. |
| `host-setup.md` | When preflight reports a tier other than `FULL`, or a script fails for lack of Python or openpyxl. |
| `summary-layout.md` | Only if `write_summary` is unavailable (step 6). |
| `linked-computer.md` | Only on a linked computer (step 0). Device staging and the commit-verify loop. |

## 0. Inputs, access and tools

- **Host preflight (first).** Run `bash <plugin root>/scripts/preflight.sh` (from this skill's directory that is
  `../../scripts/preflight.sh`; it needs no Python) and read its `TIER=` line. Tell the user the tier and any `fix=` line in
  one sentence, and limit the deliverable to what the tier allows (`FULL`, `SPREADSHEET` or `FACTS_ONLY`; table in
  `references/host-setup.md`). Doing this first means the user hears about a missing Python before an hour of work, not after.
- **Ask for both paths, nothing else up front:** the diagnosis bundle and the checklist file. Start once you have both.
- **Never pick a checklist yourself**, even when the folder holds one obvious candidate or several similar templates (for
  example dated `*_checklist_template.xlsx` copies). A wrong guess silently changes every result. Ask, or offer the bundled
  default.
- **No checklist handy?** Offer the bundled default at `resources/checklist_template.xlsx` (relative to this skill's
  directory), and say plainly, once you proceed, that you are using the default and not a user-supplied checklist.
- **How to read the bundle comes from the reader, not from this skill.** Before touching the bundle,
  load the `dataiku-diagnosis-reader` skill (if skills can't be loaded, read its `SKILL.md`, `references/limitations.md` and
  `references/listings-and-manifests.md`). Use its `lookup-table` / `data-dir-config` references to find where a setting
  lives, and its large-file rules (grep/head/wc, never load whole). If the reader lacks a layout fact you need, say so in
  your final summary instead of recording it here: layout facts live upstream so every skill benefits from one fix.
- Load the `xlsx` skill before reading or writing the spreadsheet.
- If the checklist has a version-currency or supported-OS check, confirm a web search tool is available. It is needed to
  look up the latest Dataiku DSS release (procedure in `references/calibrations.md`, DSS version currency).
- **Linked computer.** If the session is linked to the user's computer (remote-devices tools present) and the paths are
  local, read `references/linked-computer.md` before step 1.
- **Secrets.** Read `references/secrets.md` before opening the bundle.

## 1. Orient

Run the reader's `orient.sh` through this skill's wrapper:
`scripts/run_step.py run orient <bundle_root> --manifest <stem>_run_manifest.json`.
`<stem>` is the review workbook's name without `.xlsx`; keep the manifest beside it. The wrapper passes the output through
unchanged and records that the step ran, which `verify` checks in step 7. The output gives node type and version, the
largest files, and which key troubleshooting files are present, so you know what evidence is realistically available
before you plan reads.

If it shows a node type the reader hasn't verified (for example `deployer`) or no data-dir mirror, say what the bundle
cannot support and mark the rows that depend on it **Needs Review**, not Fail.

Then run `scripts/run_step.py run facts <bundle_root> --manifest <stem>_run_manifest.json` once. It runs the reader's
`facts.py` and saves the JSON beside the manifest as `<stem>_facts.json`. It prints the key settings many checks depend on,
each with its `source`, and an explicit `ABSENT` for a setting that isn't in the bundle. Step 4 says how to use it. If it
can't run or errors, say so in your final summary and use the reader's normal procedure.

## 2. Verdicts

Run `scripts/run_step.py verdicts <bundle_root> --manifest <stem>_run_manifest.json --checklist <checklist.xlsx>`. It only
reads the checklist (use the file you were given), prints JSON and saves it as `<stem>_verdicts.json`. For each row whose
status the facts decide by rule, `verdicts` lists its `id`, `status`, `reason` and `deciding_values`.

- **Write each listed `status` as that row's `validation_status`, exactly.** Code is final here: `verify` fails and names any
  row whose workbook status differs. Make `evidence_found` and `notes` agree with the status, paraphrasing the reason and
  quoting `deciding_values` in plain words ("cluster_attached is false"), never as a raw dump (skip them when empty). If you
  think a rule is wrong, say so in your final summary, never in the workbook.
- A row that is not listed has no rule: decide it as in step 4. The list may be empty. `undecided` names rows that have a
  rule but whose case the facts cannot settle; decide those as in step 4 too.
- `title_mismatch` and `probable_renumber` name rows whose id and title don't both match a rule (usually a changed
  checklist). They get no verdict: decide them as in step 4 and name them in your final summary.

## 3. Read the checklist fully

Dump every sheet's rows into a working file; don't try to hold 50+ rows in your head. Keep at least `id`, `priority`,
`check_type`, `statement`, `parameter_hint`, `operator`, `expected_value`, `unit`, `expected_condition_notes`,
`supporting_evidence`, `contradicting_evidence`, `insufficient_evidence_handling` and `ambiguity_notes` when present. Note
the exact result-column headers and their column positions per sheet (they may differ sheet to sheet).

`priority` is `must_have` or `nice_to_have`, and "must-have" below means `priority == must_have`. Read it from the column,
never from the wording of the statement: a row that sounds mandatory can be `nice_to_have`, and `write_summary` rejects a
`key_points` entry for one.

For the rows no rule decides, group them by the source they need and read each source once, finding it via the reader's
`lookup-table` and other references.

## 4. Evaluate every row

**Treat the `facts.py` output as the source of truth** for every value it covers. Take the value from it, cite its `source`
in `evidence_found`, and quote the raw value behind any Pass or Fail on a setting. Don't re-derive such a value by hand and
never contradict it from memory: hand reads were what made repeat reviews of one bundle disagree. `ABSENT` is not yet a
Fail; follow the reader's "Finding a setting reliably" before calling a setting absent. For a check it doesn't cover, read
the bundle the normal way.

Read `references/calibrations.md` in full and apply it to every matching row. Match by what the check is about, not by id
alone: ids can change between checklists, so if a row's id matches an entry but its title is about something else, don't
apply the entry. Where a row's `insufficient_evidence_handling` says what to do when the bundle lacks the evidence, follow
it; a matching calibration overrides it. A row with a verdict keeps that status, and `calibrations.md` then only tells you
what to add to `evidence_found` and `notes`.

Give each item one of five statuses, used consistently across the workbook: **Pass**, **Fail**, **Partial**,
**Needs Review**, **Not Applicable**. When to use the last two is in `calibrations.md` (General principles).

For each item, write:

- `evidence_found`: the audit trail. Give concrete citations with exact file paths and the specific key/value or log lines
  that support the finding. It stays detailed and is not shown on slides. Don't put recommendations here.
- `notes`: the slide-ready summary. The deck builder shows this text to the customer in a table cell, so it must be crisp,
  scannable and self-contained, in the format of `references/notes-format.md`. It carries the verdict, the decisive values,
  and the recommendation or caveat, and cross-references causally linked findings by id.
- `validated_at` / `validated_by`: today's date (`YYYY-MM-DD`) and, verbatim,
  `<agent name> (AI-assisted review of <bundle name>)`, where `<agent name>` is the AI agent doing the review (for example
  `Claude`, `Codex`), unless the user supplied a reviewer name.

Look actively for causal chains across items (for example a resource limit set to a disabling value, paired with crash
dumps and recurring error-log entries, all pointing to one root cause). Call these out and prioritise them instead of
reporting each row in isolation: customers act on root causes, not on a list of symptoms.

## 5. Write results back with openpyxl

Match each row by its `id` column, not by row number, so the mapping survives row reordering. Before saving, verify every id
in the sheet got a result and every result was consumed, so no mismatch goes unnoticed.

Run ad-hoc workbook scripts with the interpreter `python3 <this skill>/scripts/run_step.py python` prints (see
`references/host-setup.md`).

## 6. Add or update a Summary sheet

If the `write_summary` tool is not available, skip to the manual fallback at the end of this step. Otherwise, once every
item's `validation_status` is filled in, call the `write_summary` tool of the `dataiku-review-generator` MCP server. It
recreates the `Summary` sheet as the first tab, so re-running is idempotent. It computes the metadata labels, counts,
per-section tallies and finding rows (ID, Section, Title, Status) from the section sheets and applies one fixed style. You
supply only the judgment text:

- `checklist_path`, `reviewer`, `bundle`, and optionally `node_version` and `diagnosis_generated`. Fix their format so
  repeat runs produce the same Summary header:
  - `reviewer`: exactly the `validated_by` string.
  - `node_version`: `<nodetype> / DSS <product_version>` from `facts.py`'s `node`, for example `design / DSS 14.2.1`.
  - `diagnosis_generated`: an ISO date `YYYY-MM-DD`, from the timestamp in the bundle folder name
    (`dku_diagnosis_<node>_<YYYY-MM-DD-HH-MM-SS>`).
- `key_points`: `{item id: one line, <= 90 characters}` for **every** must-have item (`priority == must_have`) that is Fail,
  Partial or Needs Review, and for no other item. Echo the headline of the item's `notes`. The key order sets the row order
  within each block; list Fail items most causally central first.
- `recommendations`: the ordered actions, linked issues together and root cause before its symptoms. Write one action per
  root-cause group, at most 7, each naming its item ids in brackets (for example `[SCALE-008]`). Order the groups by the
  Fail key points first (the first Fail's group first), then Partial, then Needs Review. Leave out the numbering; the tool
  adds `1. `, `2. `, and so on.

The tool fails without touching the file if a key point is missing, extra, too long or multi-line, or if any item has a
blank or unknown status. Fix the input and call it again. It also re-reads the saved sheet as the deck generator will and
compares it to what it meant to write.

**Manual fallback** (tool unavailable): read `references/summary-layout.md` and write the sheet by hand to that layout. The
deck generator reads this sheet, so its layout must not drift. Use the header texts `Overall Status Counts`,
`Per-Section Breakdown`, `Critical Findings - Must-Have Items Failing`, `Other Must-Have Items: Partial / Needs Review` and
`Priority-Ordered Recommendations` **verbatim**, and the metadata labels `Bundle:`, `Node / Version:`, `Diagnosis
generated:`, `Report generated:`, `Reviewer:`.

## 7. Deliver

1. Run `scripts/run_step.py verify <bundle_root> --manifest <stem>_run_manifest.json --checklist <review.xlsx>` (add
   `--deck <deck.pptx>` when a deck was built) and put its one `RUN VERIFY` line in your final summary. It also fails when a
   row with a verdict has a different status in the workbook. On FAIL, fix the named problem (usually a skipped step, a
   stale Summary or a status that differs from its verdict) and run it again. If the bundle sits on a separate computer the
   scripts can't reach, say the run could not be verified.
2. Check that every id has one of the five statuses, each `notes` is within budget with no file paths or secrets, and the
   Summary was written after the last edit.
3. Keep the run files with the deliverable: copy `<stem>_run_manifest.json`, `<stem>_facts.json` and `<stem>_verdicts.json`
   into the same folder as the delivered workbook (an agent working in a staging folder must copy them out), so `verify`
   can be re-run later.
4. Send the updated file to the conversation. If the source came from the user's linked computer, also write it back to the
   same path (`references/linked-computer.md`) and say so in one line. With the bundled default template there is no
   original path: name the output `<bundle-name>_checklist_review.xlsx` (or the user's name for it).
5. Summarise headline results (counts plus the 1-3 most important findings) rather than repeating the checklist.
6. If the bundle holds a plaintext credential (`references/secrets.md` says how to spot and report one), put this line in
   your final summary every time, in exactly this form so repeat runs and reviewers can compare them: `Plaintext
   credential: the internal database password is stored in plaintext in <the settings file named in facts.py's
   internal_database source>; value not read. Rotate it and use a secrets store.` The SCALE-001 `notes` carry the matching
   `Action:` (see `references/calibrations.md`).

If the user also asks for a deck (or a "report and powerpoint"), continue with the `dataiku-review-deck-builder` skill and
follow its order of work in full, including the narrative (`<checklist_stem>_narrative.json`). Do not build the deck without
one; if you cannot, say so in your final summary.
