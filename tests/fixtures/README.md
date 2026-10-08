# Test fixtures

**Everything here is synthetic.** These files were hand-designed for tests and contain no real
diagnosis bundle data. Never copy real bundle data into this directory (see the README's
"Security / privacy" section). Directory names deliberately avoid the `dku_diagnosis_*` prefix,
which `.gitignore` excludes.

| Path | What it is |
|---|---|
| `bundles/<scenario>/` | Minimal fake bundles, each designed to trigger specific checklist-review calibrations. See the docstrings in `build_fixtures.py` |
| `checklists/eval_checklist.xlsx` | A trimmed copy of the bundled default template, keeping 51 items that each exercise one calibration (`EVAL_ITEM_IDS` in `build_fixtures.py`) |
| `expected/<scenario>.yaml` | The answers a correct review should give for that bundle: allowed statuses plus required mentions. Maintained by hand |

Regenerate the bundles and checklist after editing `build_fixtures.py`:

```sh
mcp-server-review-generator/.venv/bin/python tests/fixtures/build_fixtures.py
```

When you add or change a verdict rule (`docs/verdict-rules.md` and `scripts/rules_*.py`) or a model-decided calibration (`references/calibrations.md`), update these
fixtures to cover it:
1. Add the item's ID to `EVAL_ITEM_IDS`.
2. Shape a bundle so it triggers the calibration.
3. Add the expected answer to the matching `expected/*.yaml`.
