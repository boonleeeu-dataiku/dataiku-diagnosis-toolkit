# TODO

## Deterministic verdicts (`verdicts.py`)

Goal: the status of every check that facts can decide comes from code, not from the model reading `calibrations.md`.
The model keeps the evidence/notes wording, web lookups (ARCH-002/003), log reading and live-check `Action:` notes.

Design: `skills/dataiku-diagnosis-checklist-review/scripts/verdicts.py` reads `<stem>_facts.json` and returns
`{id, status, deciding_values, reason}` per check; `run_step.py verify` compares the workbook statuses to it and fails naming
the item. Rules live in the checklist skill (judgment); any fact a rule needs is added to the reader upstream first (then re-sync
and run Codex). Each rule keeps its `calibrations.md` entry as the human-readable spec until the rule is tested, then the entry
shrinks to a pointer.

Per batch: rule + unit tests on the synthetic fixtures, update `EVAL_ITEM_IDS` and the expected answers, bump the version in the
4 manifests + CHANGELOG, `scripts/test.sh fast`, then a 3-run Codex round to confirm zero differing items.

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
- [ ] Re-save the eval baseline (`scripts/test.sh eval ... --save-baseline`, costs model usage) when the owner asks; it is stale (2 scenarios x 11 items vs 3 x 34).

### Batch 2 - numeric and tiered rules, facts exist (7)
- [ ] SEC-004 (RAM tiers, +/-10% band, >=80%), SCALE-001, SCALE-006 (0.30.0: sanity-check present = Pass, missing or empty = Fail), SCALE-008, SCALE-009, SCALE-011, ARCH-004

### Batch 3 - security settings toggles (14; needs a new reader `security_settings` fact)
- [ ] ADVSEC-001 to ADVSEC-012, SEC-006, SEC-007

### Batch 4a - Kubernetes, Spark and containers (10; conditional on a cluster; may need reader facts)
- [ ] ARCH-005, ARCH-006, ARCH-007, ARCH-010, ARCH-011, ARCH-013, ARCH-014, ARCH-015, ARCH-016, ARCH-017

### Batch 4b - GenAI (8)
- [ ] GENAI-001, GENAI-002, GENAI-003, GENAI-004, GENAI-005, GENAI-006, GENAI-007, GENAI-011

### Batch 4c - scale, connections, logs (9; SCALE-007 needs a log-count fact)
- [ ] SCALE-002, SCALE-003, SCALE-004, SCALE-007, SCALE-010, SCALE-012, SCALE-013, SCALE-014, SCALE-015

### Stays with the model (14; never moved to code)
- Web lookups: ARCH-002, ARCH-003
- Live or external checks (Needs Review plus an `Action:`): ARCH-001, ARCH-008, ARCH-009, ARCH-012, SEC-003, SEC-008, SEC-011,
  SCALE-005, SCALE-016, GENAI-008, GENAI-009, GENAI-010

(Count check: 5 + 7 + 14 + 10 + 8 + 9 + 14 = 67.)

## Multi-LLM portability (cross-cutting; applies to every batch)

Goal: the same facts give the same statuses whichever client runs the review (Claude, Codex, later others). Statuses come from code;
only the `notes`/`evidence_found` wording may differ between clients.

- [ ] Replace Claude-specific wording in shared files ("load the `xlsx` skill", web-search mode, `WebFetch`, `ToolSearch`, `device_*` names in
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
- [x] Codex stages outputs in sandbox work dirs, so the run manifest isn't copied beside the deliverables: step 7 now says to copy the run files (0.32.1). Confirm on the next Codex run.
- [ ] Review the remaining Needs Review items (GENAI-004/007/008) for fixed verdicts, if no batch above covers them.
- [ ] GENAI-005/006 field names (`mainLLMId`, `referenceProjectKey`) are unverified against a populated bundle: confirm when one appears.
- [ ] Reader upstream: no `facts.py` key for Kubernetes cluster attachment (needed by Batch 4a, ARCH-010/013).
