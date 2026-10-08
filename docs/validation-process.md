# How a check gets its status

For maintainers. It explains how the toolkit decides each check's status in a platform review and where to change it. The per-rule
detail is in [`verdict-rules.md`](../skills/dataiku-diagnosis-checklist-review/references/verdict-rules.md); this page is the map.

## The idea

**Code decides every status that the bundle's facts can decide. The model decides the rest, and writes the evidence and notes for all of
them.** A status must not depend on which model or client runs the review (Claude, Codex, later others), so wherever a rule can state the
status, a rule does. The model's job is reading, wording and the `Action:` to confirm what a bundle can never show.

Two consequences shape everything below:

- **Code is final.** The model writes the verdict's status exactly as given. If it thinks a rule is wrong it says so in its final
  summary, never in the workbook, and the rule is fixed in code with a test.
- **A bundle that lacks a fact never earns a Fail.** A missing fact is Needs Review, except where a rule says otherwise.

## The flow

```
bundle (dku_diagnosis_*)
   │  run_step.py run orient        reader orient.sh   → what is in the bundle, node type
   │  run_step.py run facts         reader facts.py    → <stem>_facts.json  (values, each with its source, ABSENT when missing)
   ▼
   │  run_step.py verdicts          verdicts.compute() → <stem>_verdicts.json
   │      rules_security / rules_platform / rules_genai / rules_k8s / rules_review
   ▼
   │  the model fills the workbook: status copied from the verdict, evidence_found and notes written
   │  (rows with no verdict: the model decides them using calibrations.md)
   ▼
   │  write_summary (MCP), then  run_step.py verify
   │      facts hash matches · fresh facts.py matches · every ruled row's status == its verdict · Summary total == rows
   ▼
   deck (build_platform_review_deck, validate_deck)
```

`<stem>_run_manifest.json` records each step with its exit status and the SHA-256 of its output, so `verify` can tell a genuine run from an
edited one. Keep the manifest, facts and verdicts files beside the workbook.

## Who owns what

| Concern | Owner | Where |
|---|---|---|
| Where a setting lives, how to read a file, what a field means | **the reader** | `skills/dataiku-diagnosis-reader/` (vendored from the upstream reader repo), mainly `scripts/facts.py` and `references/*.md` |
| Which status a fact value earns | **the rules** | `skills/dataiku-diagnosis-checklist-review/scripts/rules_*.py` |
| The spec of each rule, in words | **`verdict-rules.md`** | one row per rule; the model does not read it |
| What the model adds around a status (observations, `Action:`) and the logic of the checks with no rule | **`calibrations.md`** | the model reads it in full |
| The model's step-by-step instructions | **`SKILL.md`** | checklist-review skill |
| Running the steps and verifying | **`run_step.py`**, **`verdicts.py`** | `scripts/` of the checklist skill |

The split between the reader and the rules is enforced: `tests/test_skill_boundaries.py` rejects layout terms (file names, JSON keys) in the
checklist skill. A rule may use only the facts the reader publishes. If a rule needs something new, the reader gets the fact first.

## The three kinds of check

1. **Decided by the facts.** The rule maps values to Pass, Fail, Partial, Needs Review or Not Applicable (for example a setting on or off,
   a count against a tier, a cluster attached or not). Most checks are here.
2. **Always Needs Review.** Live or organisational checks a bundle can never settle (backups, proxy, group design, network
   reachability, and similar). The status is fixed in code; the model reports what the bundle does show and an `Action:` to confirm the
   rest. These live in `rules_review.py`, or are constant inside a module where a condition applies (for example no cluster = Not
   Applicable). The authoritative list is `verdict-rules.md`.
3. **Decided by the model.** Only checks that need a live web lookup (the current GA release, the supported-OS page: ARCH-002 and
   ARCH-003). The logic is in `calibrations.md`. This is a permanent decision, not a backlog.

Counts change with each release; the current ones are in `TODO.md` and `CHANGELOG.md`, not repeated here.

## How a rule is matched to a row

`verdicts.compute()` gives a row a verdict only when **both** its id and its title match a rule (title compared with case, punctuation and
spacing ignored). The title is a guard against a renumbered or reworded checklist:

- id matches, title differs: reported under `title_mismatch`, no verdict, the model decides.
- title matches, id differs: reported under `probable_renumber`, no verdict.
- the rule returns `None` (the facts can't settle this case): listed under `undecided`, the model decides.

A rule returns `{status, reason, deciding_values}`. The reason is one line and quotes deciding values, never secrets or paths.

## Conventions every rule follows

- A fact or section missing from the bundle is **Needs Review**, not Fail or Not Applicable, unless the rule's row says otherwise.
- Pass, Fail and Partial are never given for want of a live test (backups, a proxy, who holds an OS identity). That is an `Action:`.
- Conditional checks are **Not Applicable** when the condition is absent (no cluster attached, feature not in use).
- A check's minimum DSS version above the bundle's should be Needs Review. Known gap: this is not applied in code (see `TODO.md`).

## Changing a status or adding a rule

1. **Decide the policy.** Where `calibrations.md` is silent, ask the owner; don't guess a status.
2. **Reader first, if a fact is missing.** Add it upstream (`github.com/boonleeeu-dataiku/dataiku-diagnosis-reader`, sibling checkout
   `../Diagnosis Reader/`): whitelisted keys only, no paths or secrets, spot-checked against real bundles (names and counts, never values),
   version bump and changelog. Then re-sync the vendored copy here. Never hand-edit `skills/dataiku-diagnosis-reader/` and expect it to persist.
3. **Write or change the rule** in the right `rules_*.py` with `@rule(id, anchor_title)`, the anchor being the check's title in the template.
4. **Update the spec row** in `verdict-rules.md`, and in `calibrations.md` only the notes/`Action:` guidance (plus a row in its "Check
   anchors" table if you cite the id there).
5. **Test it**: a unit test per branch in `tests/test_rules_*.py`, and the eval fixtures (add the id to `EVAL_ITEM_IDS` in
   `tests/fixtures/build_fixtures.py`, shape a synthetic bundle, record `tests/fixtures/expected/*.yaml`, regenerate).
6. **Run `scripts/test.sh fast`** (no model calls) before handing back a change. Chain it with the commit so a failing test can't be committed.
7. **Release**: bump the version in the four manifests, add a `CHANGELOG.md` entry, tag. Push only when the owner says so.
8. **Codex**: the owner runs it once per release; compare the ruled rows to `<stem>_verdicts.json`.

## Why we can trust it

- **Tests that guard the contract** (`scripts/test.sh fast`): rule edge cases (`test_rules_*.py`), rule-to-fixture agreement, the spec
  matching the registered rules (`test_verdict_rules_doc.py`), stale ids in `calibrations.md` (`test_calibration_ids.py`), reader/checklist
  boundary (`test_skill_boundaries.py`), cross-component wording (`test_contracts.py`), and vendored copies matching upstream
  (`test_vendored_drift.py`).
- **`verify`** fails the review on any status that differs from its verdict, on facts that don't match their recorded hash, and on a stale Summary.
- **Cross-client runs.** Each release is run once in Codex and the ruled rows compared with the verdicts file. Fixtures are synthetic only;
  real bundles are used for inspection and never committed.
- **Model evals** (`scripts/test.sh eval`) cost real usage and run only on request, after a skill or model change.

## Known limits

See `TODO.md` ("Other open items") and the Known issues in `CHANGELOG.md`. At the time of writing: the DSS version gate isn't applied in
code, and some data-warehouse connection setting names are unverified against a real bundle.
