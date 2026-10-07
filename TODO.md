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

### Batch 0 - foundation and design decisions (do first)
- [ ] Decide the override policy: code status is final, or the model may deviate with a stated reason (shown in `notes`).
- [ ] Module skeleton, verdict JSON schema, `run_step.py verdicts` command, `verify` comparison, test harness on `tests/fixtures`.
- [ ] Decide how the model receives the verdicts (before its worksheet fill step) and how `write_summary` key points use them.

### Batch 1 - pilot: flags and counts already in `facts.py` (5)
- [ ] SEC-001, SEC-002, SEC-005, SEC-009, SEC-010

### Batch 2 - numeric and tiered rules, facts exist (6)
- [ ] SEC-004 (RAM tiers, +/-10% band, >=80%), SCALE-001, SCALE-008, SCALE-009, SCALE-011, ARCH-004

### Batch 3 - security settings toggles (14; needs a new reader `security_settings` fact)
- [ ] ADVSEC-001 to ADVSEC-012, SEC-006, SEC-007

### Batch 4a - Kubernetes, Spark and containers (10; conditional on a cluster; may need reader facts)
- [ ] ARCH-005, ARCH-006, ARCH-007, ARCH-010, ARCH-011, ARCH-013, ARCH-014, ARCH-015, ARCH-016, ARCH-017

### Batch 4b - GenAI (8)
- [ ] GENAI-001, GENAI-002, GENAI-003, GENAI-004, GENAI-005, GENAI-006, GENAI-007, GENAI-011

### Batch 4c - scale, connections, logs (9; SCALE-007 needs a log-count fact)
- [ ] SCALE-002, SCALE-003, SCALE-004, SCALE-007, SCALE-010, SCALE-012, SCALE-013, SCALE-014, SCALE-015

### Stays with the model (15; never moved to code)
- Web lookups: ARCH-002, ARCH-003
- Live or external checks (Needs Review plus an `Action:`): ARCH-001, ARCH-008, ARCH-009, ARCH-012, SEC-003, SEC-008, SEC-011,
  SCALE-005, SCALE-006, SCALE-016, GENAI-008, GENAI-009, GENAI-010

(Count check: 5 + 6 + 14 + 10 + 8 + 9 + 15 = 67.)

## Other open items
- [ ] Codex stages outputs in sandbox work dirs, so the run manifest isn't copied beside the deliverables: add a skill rule to copy it.
- [ ] Review the remaining Needs Review items (GENAI-004/007/008) for fixed verdicts, if no batch above covers them.
- [ ] GENAI-005/006 field names (`mainLLMId`, `referenceProjectKey`) are unverified against a populated bundle: confirm when one appears.
- [ ] Run Codex on 0.29.1 and compare 3 runs (target: 0 differing items).
