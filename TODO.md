# TODO

## Status and start here (updated 2026-10-08)

Versions: toolkit **0.38.2** (tag `v0.38.2`), reader **0.20.0** (`skill-v0.20.0`, upstream repo `../Diagnosis Reader/`), Checklist Generator
**0.4.0** (`v0.4.0`, `../Dataiku Checklist Generator/`; ids and titles frozen in its `config/id_registry.yaml`). Everything is pushed.

Done: the verdict framework (Batch 0) and rules for **62 of 67 checks**, one module per area: `rules_security.py` (SEC-001/002/005/006/007/009/010,
ADVSEC-001 to 012), `rules_platform.py` (ARCH-001, SEC-004, ARCH-004, SCALE-001/002/003/004/006/007/008/009/010/011/012/013/014/015), `rules_genai.py`
(GENAI-001/003/004/005/006/007/008/009) and `rules_review.py` (always Needs Review: ARCH-009/012, SEC-008/011, SCALE-005/016, GENAI-010) and `rules_k8s.py` (ARCH-005/006/007/008/010/011/013/014/015/016/017). `run_step.py verdicts` computes them, `verify` fails on any
workbook status that differs.

The rule specs are in `skills/dataiku-diagnosis-checklist-review/references/verdict-rules.md` (one row per rule, kept in step by
`tests/test_verdict_rules_doc.py`; the model does not read it). `calibrations.md` was restructured in 0.38.1 (4,900 to 2,400 words): it now
holds only the model's `notes`/`Action:` guidance for rule-decided checks and the status logic of the model-decided ones.

Codex runs reviewed: 0.32.0 (found two gaps, fixed in 0.32.1), 0.33.1 (all six Batch 2 rules matched, `RUN VERIFY: PASS`), 0.35.0 (Batch 3, 14 rules
matched, `RUN VERIFY: PASS`). 0.38.1 was run in Codex on 2026-10-08: all 46 ruled statuses matched `<stem>_verdicts.json`, `RUN VERIFY: PASS`. **Not yet run in Codex: 0.38.2** (16 new rules plus the ADVSEC-005/006/011 policy changes); owner runs it once.
Policy changes made after the 0.38.0 review of the rule table (all in 0.38.1 or earlier): ARCH-006/011 one or identical configs = Needs Review; ARCH-007 fixed namespace =
Needs Review; ARCH-016 default cluster set = Pass, none = Fail, no cluster = Not Applicable; the Kubernetes-only checks are Not Applicable with no
cluster attached; SEC-009 LDAP on with no groups = Needs Review; SEC-010 SSO on = Pass whatever LDAP is.

**0.38.2 (2026-10-08, pushed):** 62 of 67 checks are ruled. Added: ARCH-001, ARCH-008/014/015, the seven always-Needs-Review checks (`rules_review.py`), SCALE-012 to 015 (reader 0.20.0 `connections.cloud_storage` / `warehouses`) and GENAI-008. Policy changes: ADVSEC-005 not restricted = Fail; ADVSEC-006 http(s) URL or default page = Pass, else Needs Review; ADVSEC-011 not disabled = Needs Review. Known issues (also in `CHANGELOG.md`): the Snowflake, Databricks, Redshift and Synapse setting names are unverified; SCALE-012 is Not Applicable when no S3, Azure or GCS connection exists.

**Next:** (1) the Codex run on 0.38.2, compare the 62 ruled rows to `<stem>_verdicts.json` (expect ADVSEC-006 Pass and ARCH-008/014/015 per the cluster fact on the GE design bundle); (2) the last 5 stay with the model: ARCH-002/003 (web lookups), SEC-003, GENAI-002 and GENAI-011 (each waits on a reader fact or a sample); (3) when a bundle with Snowflake, Databricks, Redshift or Synapse connections appears, confirm the warehouse setting names in the reader; (4) optional: apply the DSS version gate in code (see Other open items).

### Playbook for a batch (what worked)
1. Read the checklist rows and any matching model-decided entries in `calibrations.md` for the batch (`openpyxl` on `skills/dataiku-diagnosis-checklist-review/resources/checklist_template.xlsx`).
2. Check what `facts.py` already exposes for each check (`python3 skills/dataiku-diagnosis-reader/scripts/facts.py <fixture bundle>`). If a fact is missing, inspect the three real
   bundles in `../Diagnosis Reader/resources/` read-only (print key names and counts, never values or secrets).
3. Where the calibration is silent, ask the owner for the policy (one `AskUserQuestion` per open case). Don't guess a status.
4. Reader first: add the fact in `../Diagnosis Reader/dataiku-diagnosis-reader/scripts/facts.py` (whitelisted keys, no paths or secrets), bump `SKILL.md` version
   and `CHANGELOG.md`, verify on fixtures and the real bundles, commit, tag `skill-vX.Y.Z`; then copy `SKILL.md`, `CHANGELOG.md`, `scripts/facts.py` (and any changed
   reference) into `skills/dataiku-diagnosis-reader/` and `diff -r` the two.
5. Rules go in `skills/dataiku-diagnosis-checklist-review/scripts/rules_*.py` (`@rule(id, anchor_title)`; anchor = the template title). Unit-test every branch in
   `tests/test_rules_*.py` and check each rule against the fixtures' `expected/*.yaml`.
6. Spec: add a row per rule to `references/verdict-rules.md` under the module's section (`tests/test_verdict_rules_doc.py` fails without it). In `calibrations.md` add only the `evidence_found`/`notes`/`Action:` guidance for the check, and a row in its "Check anchors" table if you cite the id there.
7. Release: bump the version in the 4 manifests, add a `CHANGELOG.md` entry, tick the batch here, `scripts/test.sh fast`, commit, tag `vX.Y.Z`. **Push only when the owner says so.**
8. The owner runs Codex **once** per release; review the delivered folder with `run_step.py verify <bundle at the path Codex used> --manifest ... --checklist ... --deck ...`
   and compare the ruled rows to `<stem>_verdicts.json`. Don't ask for more runs unless told. Don't run `scripts/test.sh eval` unless asked (it costs model usage).

### Pitfalls found so far
- A fact can look sufficient and not be (SEC-005: a JEK target configured and no JEK category both read as an empty list). Compare the real bundles and the fixtures before writing the rule.
- A missing fact is **Needs Review**, never an assumed Fail, unless the calibration says otherwise (SCALE-006, ADVSEC-007/008 with no properties file).
- A rule may return `None` ("undecided") when the facts can't settle a case; the row then gets no verdict and the model decides it.
- `tests/test_skill_boundaries.py` rejects reader-owned layout terms (file names, JSON keys, `lsblk`, `dip.properties`...) in SKILL.md, `references/*.md` and `scripts/*.py`.
  Rule modules may only name the keys the reader publishes in `SECURITY_KEYS`. Describe a setting in words in `verdict-rules.md` and `calibrations.md`.
- Keep the verdict `reason` one line; quote deciding values, never secrets or paths.
- Chain `scripts/test.sh fast && git commit` (not `;`): twice a commit went in with a failing test and had to be amended.
- Synthetic fixtures must mimic the real file formats (the fixture `backend.log` once lacked the bracketed level), or a reader fact that parses the real format reads zero on them.
- Fixtures are synthetic; never derive them from a real bundle. The three real bundles are for inspection only and must never be committed or copied.

## Deterministic verdicts (`verdicts.py`)

Goal: the status of every check that facts can decide comes from code, not from the model reading calibrations.
The model keeps the evidence/notes wording, web lookups (ARCH-002/003), log reading and live-check `Action:` notes.

Design: `skills/dataiku-diagnosis-checklist-review/scripts/verdicts.py` reads `<stem>_facts.json` and returns
`{id, status, deciding_values, reason}` per check; `run_step.py verify` compares the workbook statuses to it and fails naming
the item. Rules live in the checklist skill (judgment); any fact a rule needs is added to the reader upstream first (then re-sync
and run Codex). Each rule's row in `verdict-rules.md` is its human-readable spec; `calibrations.md` carries only the model's notes guidance.

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
- [x] SEC-001, SEC-002, SEC-005, SEC-009, SEC-010 (0.32.0). SEC-005 needed the new reader fact `cgroups.target_counts` (reader 0.13.0). SEC-002 enabled with no rules = Partial. SEC-009 LDAP on with no groups = Needs Review and SEC-010 SSO on = Pass whatever LDAP is (both changed in 0.38.0).
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
- Reader 0.19.0 added the `kubernetes` fact (cluster attachment, container and Spark execution configs, container defaults). A cluster is attached when a cluster definition file exists or a default cluster id is set.
- [x] ARCH-005, 006, 007, 010, 011, 013, 016, 017 (0.38.0; reader 0.19.0 `kubernetes`). No cluster attached = Not Applicable for the Kubernetes-only ones; ARCH-005/006 Spark off = Not Applicable; ARCH-006 one or identical configs and ARCH-007 fixed namespace = Needs Review; ARCH-011 one or identical configs = Needs Review; ARCH-016 cluster attached: default cluster set = Pass, none = Fail, no cluster = Not Applicable; ARCH-017 unset = Needs Review.
- [x] ARCH-008, ARCH-014 and ARCH-015 (0.38.2): live checks a bundle can't settle. No cluster = Not Applicable, cluster attached = Needs Review (the model adds the `Action:`).
- [x] Codex run on 0.38.1 reviewed: all 46 ruled statuses matched (covers 4a, 4b and 4c). The 0.38.2 run is the next one.

### Batch 4b - GenAI (8; 6 ruled in 0.36.0 plus GENAI-009)
- Existing facts: `byo_llm`, `trace_explorer`, `plugins`, `default_preferences`. GENAI-005/006 field names are unverified against a populated bundle (see Other open items). Version gate: a check's minimum DSS version above the bundle's = Needs Review, never Fail or Not Applicable. Check each row's calibration in the "GenAI" section before writing rules.
- [x] GENAI-001, 003, 004, 005, 006, 007 (and GENAI-009, listed under the model-only checks but ruled: installed = Needs Review, else Not Applicable) in 0.36.0 (reader 0.17.0 `genai_settings`). GENAI-001: internal = Pass, non-internal = Needs Review, none set = Fail. GENAI-003: block present but unset = Fail.
- [ ] GENAI-002 (Hugging Face env, unverified fact) and GENAI-011 (group impersonation scope; needs to know which group runs the Agent Hub webapp) stay with the model unless a fact is found.

### Batch 4c - scale, connections, logs (10; SCALE-007 and SCALE-008 need a log-count fact)
- Reader 0.18.0 added `backend_log` (per-file ERROR/FATAL/WARN and OutOfMemoryError counts with time windows, counts only) and `metastore_and_exports`. SCALE-012 to 015 are not inspected yet: the next step is a reader `connections` fact (no params or secrets).
- [x] SCALE-002, 003, 004, 007, 008, 010 (0.37.0; reader 0.18.0 `metastore_and_exports`, `backend_log`). SCALE-008: any confirmed miss = Fail, missing input = Needs Review; SCALE-010 treats DSS's default storage-format list as blank.
- [x] SCALE-012, SCALE-013, SCALE-014, SCALE-015 (0.38.2; reader 0.20.0 `connections.cloud_storage` / `warehouses`). Warehouse fast-write, Spark native and UDF settings are found by name pattern and a non-blank value counts as set (no Snowflake, Databricks, Redshift or Synapse sample exists to verify names: confirm when one appears). All set = Pass, some = Partial, none = Fail, no such connection = Not Applicable. GENAI-008: always Needs Review, with a DSS 14.7 reason.

### Stays with the model (5; no rule yet)
- Web lookups: ARCH-002, ARCH-003
- Live or external checks (Needs Review plus an `Action:`): SEC-003
- Waiting for a reader fact: GENAI-002 (Hugging Face env), GENAI-011 (Agent Hub group impersonation)

(Count check: 62 ruled + 5 with the model = 67.)

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
- [ ] Re-save the eval baseline (`scripts/test.sh eval ... --save-baseline`, costs model usage) when the owner asks; it is stale (2 scenarios x 11 items vs 3 x 41).
- [ ] Minor: notes should not name files (SEC-003 on the 0.32.0 run mentioned a security config file); consider a line in SKILL.md or leave it.
- [x] GENAI-004/007 now have rules (0.36.0); GENAI-008 stays with the model.
- [ ] GENAI-005/006 field names (`mainLLMId`, `referenceProjectKey`) are unverified against a populated bundle: confirm when one appears.
- [x] Reader `kubernetes` fact for cluster attachment (0.19.0).
- [ ] The rules do not apply the version gate (a check's minimum DSS version above the bundle's = Needs Review). It works only because settings are missing on older DSS; GENAI-003 present-but-unset on an old DSS would still Fail. Decide whether to read the bundle's DSS version in the GenAI rules.
- [ ] `calibrations.md` now omits the long-form specs: if a model-decided check gains a rule, move its entry into `verdict-rules.md` and keep only the notes guidance.
