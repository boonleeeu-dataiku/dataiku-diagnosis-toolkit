# TODO

Open work only. Release history is in `CHANGELOG.md`; the general process is in `docs/validation-process.md`.

## Status (updated 2026-10-08)

Toolkit **0.38.5**, reader **0.20.1** (upstream `../Diagnosis Reader/`), Checklist Generator **0.4.0** (`../Dataiku Checklist Generator/`; ids and
titles frozen in its `config/id_registry.yaml`). **65 of 67 checks are ruled** (`skills/dataiku-diagnosis-checklist-review/scripts/rules_*.py`, specs in
`docs/verdict-rules.md`). ARCH-002/003 stay with the model for good (they need a live web lookup). Code status is final: `run_step.py verify` fails on
any workbook status that differs from its verdict.

Codex: the 0.38.3 runs (2026-10-08) passed `RUN VERIFY` with all 65 ruled statuses matching. **0.38.4 has not been run in Codex yet.**

## Next
1. Optionally run Codex once on 0.38.4 to check the `SKILL.md` evidence wording and ARCH-009/012 (expect Not Applicable on the GE design bundle).
2. Slim pass (this session): skills trimmed, `notes` format moved to `references/notes-format.md`, calibration anchors moved to `tests/calibration_anchors.md`.
   Upstream follow-ups to hand to the two vendored repos: see "Upstream follow-ups" below.

### Playbook for a batch (what worked)
The general process (flow, ownership, how to change a rule) is in [`docs/validation-process.md`](docs/validation-process.md); this list is the working version.

1. Read the checklist rows and any matching model-decided entries in `calibrations.md` for the batch (`openpyxl` on `skills/dataiku-diagnosis-checklist-review/resources/checklist_template.xlsx`).
2. Check what `facts.py` already exposes for each check (`python3 skills/dataiku-diagnosis-reader/scripts/facts.py <fixture bundle>`). If a fact is missing, inspect the three real
   bundles in `../Diagnosis Reader/resources/` read-only (print key names and counts, never values or secrets).
3. Where the calibration is silent, ask the owner for the policy (one `AskUserQuestion` per open case). Don't guess a status.
4. Reader first: add the fact in `../Diagnosis Reader/dataiku-diagnosis-reader/scripts/facts.py` (whitelisted keys, no paths or secrets), bump `SKILL.md` version
   and `CHANGELOG.md`, verify on fixtures and the real bundles, commit, tag `skill-vX.Y.Z`; then copy `SKILL.md`, `CHANGELOG.md`, `scripts/facts.py` (and any changed
   reference) into `skills/dataiku-diagnosis-reader/` and `diff -r` the two.
5. Rules go in `skills/dataiku-diagnosis-checklist-review/scripts/rules_*.py` (`@rule(id, anchor_title)`; anchor = the template title). Unit-test every branch in
   `tests/test_rules_*.py` and check each rule against the fixtures' `expected/*.yaml`.
6. Spec: add a row per rule to `docs/verdict-rules.md` under the module's section (`tests/test_verdict_rules_doc.py` fails without it). In `calibrations.md` add only the `evidence_found`/`notes`/`Action:` guidance for the check, and a row in `tests/calibration_anchors.md` if you cite the id there.
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


## Multi-LLM portability (cross-cutting)

Goal: the same facts give the same statuses whichever client runs the review. Statuses come from code; only wording may differ.

- [ ] Replace Claude-specific wording in shared files ("load the `xlsx` skill", web-search mode, `WebFetch`, `ToolSearch`, `device_*` names in `linked-computer.md`; add a scope header there) so Codex overrides can go.
- [ ] Document minimum client requirements (shell, Python 3, openpyxl, file access; optional MCP and web search) and what degrades without them.
- [ ] Consider one wrapper command for the deterministic part (facts + verdicts + verify).
- [ ] Cross-client regression run after each batch; compare statuses, not wording.
- Ownership: `skills/` and `scripts/` are shared and `AGENTS.md` bars Codex from editing them. Codex-only files (`codex-skills/`, `CODEX_SETUP.md`) change only for a demonstrated Codex-specific gap.

## Other open items
- [ ] Re-save the eval baseline (`scripts/test.sh eval ... --save-baseline`, costs model usage) when the owner asks; it is stale (2 scenarios x 11 items vs 3 scenarios x 49).
- [ ] Minor: notes should not name files (SEC-003 once did). Guidance exists in `calibrations.md`; consider a general line in `notes-format.md`.
- [ ] Snowflake, Databricks, Redshift and Synapse setting names (SCALE-013 to 015) and GENAI-005/006 field names (`mainLLMId`, `referenceProjectKey`) are unverified: confirm against a populated bundle when one appears.
- [ ] The rules do not apply the version gate (minimum DSS version above the bundle's = Needs Review). It works only because settings are missing on older DSS; GENAI-003 present-but-unset on an old DSS would still Fail. Decide whether to read the DSS version in the GenAI rules.
- [ ] If a model-decided check gains a rule, move its `calibrations.md` entry into `verdict-rules.md` and keep only the notes guidance.

## Upstream follow-ups (vendored; fix there, then re-sync and run Codex)
- Reader: memoise `load_json` in `facts.py` (general-settings.json parsed ~14 times), read `diag.txt` and `install.ini` once; sets instead of identity dicts for `CLOUD_STORAGE_TYPES`/`WAREHOUSE_TYPES`; drop redundant `SENSITIVE_KEY_EXTRA` in `peek.py`.
- Review generator: `read_checklist.py` Summary parsing is O(rows^2) (read the sheet once with `iter_rows`); v1 loads the checklist twice (`data_checks.py:150` via `styles.py:68`); slide-package XML is rewritten per clone and ~57 `delete_slide` calls; `make_table_slides` re-parses identical table XML per page; delete dead code (`narrative.check_rows`, `office/text.placeholder_text_box`, `PIC_RE`, `SP_RE`, `remove_relationship_by_rid`, `slides.duplicate_slide`, `tables.extract_cells`, yaml `cell_char_limits.description`); fix stale comments (`mcp_server.py` "two CLI entry points", `read_checklist.py` 26 vs 27 columns, `build_deck_v2.py` cites missing `INTENT.md`, `validate_deck.py` colour names), the `requirements.txt` header, undeclared `lxml`, and the `include_pass_items` default mismatch.
