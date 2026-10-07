# TODO

## Status and start here (updated 2026-10-07)

Versions: toolkit **0.37.0** (tag `v0.37.0`, local only), reader **0.18.0** (`skill-v0.18.0`, local only, upstream repo `../Diagnosis Reader/`), Checklist Generator
**0.4.0** (`v0.4.0`, `../Dataiku Checklist Generator/`; ids and titles frozen in its `config/id_registry.yaml`). 0.37.0 and reader 0.18.0 are committed and tagged, not pushed.

Done: the verdict framework (Batch 0) and rules for **38 of 67 checks**: SEC-001/002/004/005/006/007/009/010, SCALE-001/006/009/011,
ARCH-004, ADVSEC-001 to 012 and (0.36.0) GENAI-001/003/004/005/006/007/009 and (0.37.0) SCALE-002/003/004/007/008/010. `run_step.py verdicts` computes them, `verify` fails on any workbook status that differs.
Codex runs reviewed (2026-10-07: 0.35.0 added): 0.32.0 (found two gaps, fixed in 0.32.1), 0.33.1 (all six Batch 2 rules matched, `RUN VERIFY: PASS`).
0.35.0 (Batch 3, 14 rules matched, `RUN VERIFY: PASS`).

**Next: Batch 4a** (needs a Kubernetes reader fact first) or the rest of 4c (SCALE-012 to 015, needs a connections fact). 4b and most of 4c are done. Codex run on 0.37.0 (covers 0.36.0 too) still to do.

### Playbook for a batch (what worked)
1. Read the checklist rows and the matching `calibrations.md` entries for the batch (`openpyxl` on `skills/dataiku-diagnosis-checklist-review/resources/checklist_template.xlsx`).
2. Check what `facts.py` already exposes for each check (`python3 skills/dataiku-diagnosis-reader/scripts/facts.py <fixture bundle>`). If a fact is missing, inspect the three real
   bundles in `../Diagnosis Reader/resources/` read-only (print key names and counts, never values or secrets).
3. Where the calibration is silent, ask the owner for the policy (one `AskUserQuestion` per open case). Don't guess a status.
4. Reader first: add the fact in `../Diagnosis Reader/dataiku-diagnosis-reader/scripts/facts.py` (whitelisted keys, no paths or secrets), bump `SKILL.md` version
   and `CHANGELOG.md`, verify on fixtures and the real bundles, commit, tag `skill-vX.Y.Z`; then copy `SKILL.md`, `CHANGELOG.md`, `scripts/facts.py` (and any changed
   reference) into `skills/dataiku-diagnosis-reader/` and `diff -r` the two.
5. Rules go in `skills/dataiku-diagnosis-checklist-review/scripts/rules_*.py` (`@rule(id, anchor_title)`; anchor = the template title). Unit-test every branch in
   `tests/test_rules_*.py` and check each rule against the fixtures' `expected/*.yaml`.
6. `calibrations.md`: mark the entry `[code-decided]`, record every case, add a row to the "Check anchors" table.
7. Release: bump the version in the 4 manifests, add a `CHANGELOG.md` entry, tick the batch here, `scripts/test.sh fast`, commit, tag `vX.Y.Z`. **Push only when the owner says so.**
8. The owner runs Codex **once** per release; review the delivered folder with `run_step.py verify <bundle at the path Codex used> --manifest ... --checklist ... --deck ...`
   and compare the ruled rows to `<stem>_verdicts.json`. Don't ask for more runs unless told. Don't run `scripts/test.sh eval` unless asked (it costs model usage).

### Pitfalls found so far
- A fact can look sufficient and not be (SEC-005: a JEK target configured and no JEK category both read as an empty list). Compare the real bundles and the fixtures before writing the rule.
- A missing fact is **Needs Review**, never an assumed Fail, unless the calibration says otherwise (SCALE-006, ADVSEC-007/008 with no properties file).
- A rule may return `None` ("undecided") when the facts can't settle a case; the row then gets no verdict and the model decides it.
- `tests/test_skill_boundaries.py` rejects reader-owned layout terms (file names, JSON keys, `lsblk`, `dip.properties`...) in SKILL.md, `references/*.md` and `scripts/*.py`.
  Rule modules may only name the keys the reader publishes in `SECURITY_KEYS`. Describe a setting in words in `calibrations.md`.
- Keep the verdict `reason` one line; quote deciding values, never secrets or paths.
- Fixtures are synthetic; never derive them from a real bundle. The three real bundles are for inspection only and must never be committed or copied.

## Deterministic verdicts (`verdicts.py`)

Goal: the status of every check that facts can decide comes from code, not from the model reading `calibrations.md`.
The model keeps the evidence/notes wording, web lookups (ARCH-002/003), log reading and live-check `Action:` notes.

Design: `skills/dataiku-diagnosis-checklist-review/scripts/verdicts.py` reads `<stem>_facts.json` and returns
`{id, status, deciding_values, reason}` per check; `run_step.py verify` compares the workbook statuses to it and fails naming
the item. Rules live in the checklist skill (judgment); any fact a rule needs is added to the reader upstream first (then re-sync
and run Codex). Each rule's `calibrations.md` entry stays as its human-readable spec, marked `[code-decided]`.

Per batch: see the playbook above. The Codex check is a single run per release (usage limits), compared to the verdicts.

### Batch 0 - foundation and design decisions (do first, after the hygiene check)
- [x] **Depends on generator 0.4.0 (stable ids).** Rules are keyed by check id, so don't start them until the Dataiku Checklist Generator's
  `config/id_registry.yaml` (ids and titles frozen from the current 67; see that repo's README, "Stable ids and titles") has shipped and this
  repo's `checklist_template.xlsx` is re-synced (`scripts/sync_to_toolkit.py --apply` there; no diff expected today). With ids locked, the title
  anchor below is a cheap guard, not the main defence. Any later retitle or retirement in the registry means updating the calibrations anchors
  and the rules for that id.
- [x] Override policy decided: **code status is final**. `verify` fails, naming the item, on any workbook/verdict mismatch. No escape hatch by default.
- [x] Delivery decided: a separate `run_step.py verdicts` step (records in the manifest, saves `<stem>_verdicts.json`) and a new SKILL.md
  step after facts. `write_summary` key-point statuses come from that JSON.
- [x] Rule matching decided: id first, with the title anchor as a guard. A row gets a verdict only when id and title both match (normalised);
  mismatches are reported and fall back to the model.
- [x] Escape hatch decided: none. A wrong rule is fixed in code with a test.
- [x] Module skeleton, verdict JSON schema, `run_step.py verdicts` command, `verify` comparison (0.31.0; tests inject rules, real rules start in Batch 1).
- [x] Extend `tests/test_skill_boundaries.py` to cover `scripts/verdicts.py` and `run_step.py` (judgment only: no file paths or JSON-layout knowledge).
- [x] `run_step.py` rework for the new step: split `STEPS` into reader steps (orient, facts) and the local `verdicts` command (today `STEPS`
  drives `verify`, argparse choices and the "recorded" check, and runs reader scripts); generalise `facts_path` into a `sibling(manifest, suffix)` helper.
- [x] `verify` hashes the saved `<stem>_facts.json` against the manifest's recorded facts hash, so a hand-edited file can't feed
  verdicts. Cheap, and it may replace the second `facts.py` run.
- [x] Neutral `validated_by` (0.32.1): change `Claude (AI-assisted review of <bundle>)` to `<agent name> (AI-assisted review of <bundle>)` in
  SKILL.md (including the `reviewer` rule), update `tests/test_contracts.py` and `check_review_output`, and drop the Codex override.

### Batch 1 - pilot: flags and counts already in `facts.py` (5)
- [x] SEC-001, SEC-002, SEC-005, SEC-009, SEC-010 (0.32.0). SEC-005 needed the new reader fact `cgroups.target_counts` (reader 0.13.0). SEC-002 enabled with no rules = Partial.
- [x] Codex run on 0.32.0 reviewed (one run, by the owner's choice to save usage; further rounds only on request): the five ruled items matched their verdicts; the run left no manifest beside the workbook and wrote `Claude` as reviewer, both fixed in 0.32.1.

### Batch 2 - numeric and tiered rules, facts exist (6)
- [x] SEC-004 (RAM tiers, +/-10% band, >=80%), SCALE-001, SCALE-006 (sanity-check present = Pass, missing or empty = Fail), SCALE-009 (any 0 = Fail, out of range = Needs Review), SCALE-011, ARCH-004 (0.33.0; 0.33.2 reads the sanity-check message codes, so `undecided` is now only the older-facts fallback).
- Moved out: SCALE-008 needs `OutOfMemoryError` counts from the backend logs (and the config-folder size is often absent); now in Batch 4c with SCALE-007.
- [x] Codex run on 0.33.1 reviewed: the six rules matched, `RUN VERIFY: PASS`, run files beside the workbook. It showed ARCH-004 returning `undecided` needlessly, fixed in 0.33.2 (reader 0.14.0 `sanity_check.codes`).

### Batch 3a - security toggles in the `security` settings block (9; reader 0.15.0 `security_settings`)
- [x] ADVSEC-001, 002, 003, 004, 005, 006, 010, 012, SEC-007 (0.34.0). Off = Fail for ADVSEC-001/002/004; Needs Review where the checklist allows a deliberate choice (ADVSEC-005, 010, 012, SEC-007); ADVSEC-010 on with secure cookies off = Fail.
- [x] Codex run folded into the 0.35.0 run below (3a was pushed as 0.34.0).

### Batch 3b - settings in `dip.properties` and `install.ini` (5; reader 0.16.0 `server_config`)
- [x] ADVSEC-007, 008, 009, 011, SEC-006 (0.35.0). ADVSEC-009: Pass needs the six core headers set restrictively, Partial for some, Fail for none. A missing `dip.properties` means nothing is set (Fail for 007/008).
- [x] Codex run on 0.35.0 (once), covering 3a and 3b: the 14 Batch 3 rules match their verdicts, `RUN VERIFY: PASS`.

### Batch 4a - Kubernetes, Spark and containers (10; conditional on a cluster; needs reader facts first)
- Prerequisite: a reader fact for Kubernetes cluster attachment (see Other open items); the Kubernetes calibrations are in `calibrations.md`, section "Kubernetes, containers and Spark" (None attached = Not Applicable; attached with no valid container config = Fail). Inspect the rows and the real bundles' container, Spark and cluster settings before deciding what else is needed.
- [ ] ARCH-005, ARCH-006, ARCH-007, ARCH-010, ARCH-011, ARCH-013, ARCH-014, ARCH-015, ARCH-016, ARCH-017

### Batch 4b - GenAI (8; 6 ruled in 0.36.0 plus GENAI-009)
- Existing facts: `byo_llm`, `trace_explorer`, `plugins`, `default_preferences`. GENAI-005/006 field names are unverified against a populated bundle (see Other open items). Version gate: a check's minimum DSS version above the bundle's = Needs Review, never Fail or Not Applicable. Check each row's calibration in the "GenAI" section before writing rules.
- [x] GENAI-001, 003, 004, 005, 006, 007 (and GENAI-009, listed under the model-only checks but ruled: installed = Needs Review, else Not Applicable) in 0.36.0 (reader 0.17.0 `genai_settings`). GENAI-001: internal = Pass, non-internal = Needs Review, none set = Fail. GENAI-003: block present but unset = Fail.
- [ ] GENAI-002 (Hugging Face env, unverified fact) and GENAI-011 (group impersonation scope; needs to know which group runs the Agent Hub webapp) stay with the model unless a fact is found.
- [ ] Codex run on 0.36.0 (once).

### Batch 4c - scale, connections, logs (10; SCALE-007 and SCALE-008 need a log-count fact)
- Prerequisite for SCALE-007/008: a reader fact with `ERROR`/`WARN` and `OutOfMemoryError` counts from the backend log (reader work only: counts, never log text; mind the large-file hazards in the reader's `limitations.md`), plus the config-folder size, which is often absent. SCALE-002/003/004/010 have facts (`default_preferences`, `admin_cleanup_scenarios`, ...); SCALE-012 to 015 have not been inspected.
- [x] SCALE-002, 003, 004, 007, 008, 010 (0.37.0; reader 0.18.0 `metastore_and_exports`, `backend_log`). SCALE-008: any confirmed miss = Fail, missing input = Needs Review; SCALE-010 treats DSS's default storage-format list as blank.
- [ ] SCALE-012, SCALE-013, SCALE-014, SCALE-015 (need a reader connections fact: details readable by, HDFS interface, fast-write flags per type; field names unverified, no params or secrets)
- [ ] Codex run on 0.37.0 (once; also covers 0.36.0).

### Stays with the model (14; never moved to code)
- Web lookups: ARCH-002, ARCH-003
- Live or external checks (Needs Review plus an `Action:`): ARCH-001, ARCH-008, ARCH-009, ARCH-012, SEC-003, SEC-008, SEC-011,
  SCALE-005, SCALE-016, GENAI-008, GENAI-009, GENAI-010

(Count check: 5 + 6 + 9 + 5 + 10 + 8 + 10 + 14 = 67.)

## Multi-LLM portability (cross-cutting; applies to every batch)

Goal: the same facts give the same statuses whichever client runs the review (Claude, Codex, later others). Statuses come from code;
only the `notes`/`evidence_found` wording may differ between clients.

- [ ] (Partly done: `validated_by` is neutral since 0.32.1.) Replace Claude-specific wording in shared files ("load the `xlsx` skill", web-search mode, `WebFetch`, `ToolSearch`, `device_*` names in
  `linked-computer.md`; add a scope header there) so the Codex overrides can go.
- [x] Write the verdicts step in agent-neutral wording: "run this command, use this JSON". No dependence on skill loading, the `xlsx`
  skill or Claude-only tool names.
- [ ] Document minimum client requirements (shell, Python 3, openpyxl, file access to the bundle; optional MCP and web search) and what
  degrades without them: no MCP -> manual Summary layout; no web search -> ARCH-002/003 Needs Review.
- [ ] Consider one wrapper command for the deterministic part (facts + verdicts + verify).
- [ ] Cross-client regression run (Claude + Codex, later a third) after each batch; compare statuses, not wording.
- Ownership: `skills/` and `scripts/` are shared and `AGENTS.md` bars Codex from editing them, so this work is done Claude-side. Codex-only
  files (`codex-skills/dataiku-codex-workflow/`, `CODEX_SETUP.md`) change only for a demonstrated Codex-specific gap.

## Other open items
- [x] Hygiene check of code, skills, tests and docs: safe fixes applied (run_step.py error handling, test caching and cleanup, README and
  skill duplicates); the rest moved into Batch 0, portability and the items below.
- [x] Codex stages outputs in sandbox work dirs, so the run manifest isn't copied beside the deliverables: step 7 now says to copy the run files (0.32.1); confirmed on the 0.33.1 run.
- [ ] Re-save the eval baseline (`scripts/test.sh eval ... --save-baseline`, costs model usage) when the owner asks; it is stale (2 scenarios x 11 items vs 3 x 34).
- [ ] Minor: notes should not name files (SEC-003 on the 0.32.0 run mentioned a security config file); consider a line in SKILL.md or leave it.
- [ ] Review the remaining Needs Review items (GENAI-004/007/008) for fixed verdicts, if no batch above covers them.
- [ ] GENAI-005/006 field names (`mainLLMId`, `referenceProjectKey`) are unverified against a populated bundle: confirm when one appears.
- [ ] Reader upstream: no `facts.py` key for Kubernetes cluster attachment (needed by Batch 4a, ARCH-010/013).
