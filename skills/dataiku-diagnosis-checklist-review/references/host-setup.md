# Host setup: Python, preflight tiers and the virtualenv

Read this when `preflight.sh` reports a tier other than `FULL`, when a script fails for lack of Python or openpyxl, or
before running an ad-hoc workbook script.

## Python

- The deck and MCP tools need Python 3.10 or newer. `run_step.py` itself tolerates older versions, so a host with an old
  Python can still run the orient, facts and verify steps.
- If `python3 --version` is older than 3.10, run the scripts with a newer interpreter (for example `python3.12`, or the
  review generator's `.venv/bin/python3`).
- `run_step.py verdicts` and `verify` need openpyxl. When the default Python lacks it they re-run themselves under the
  plugin's own virtualenv. If they cannot find one, set `DATAIKU_PYTHON` to a Python 3.10+ that has openpyxl.
- For ad-hoc workbook scripts, use the interpreter that `python3 <this skill>/scripts/run_step.py python` prints. The default
  `python3` often lacks openpyxl, and that command names one that has it.

## Preflight tiers

`bash <plugin root>/scripts/preflight.sh` needs no Python and prints a `TIER=` line, plus a `fix=` line when something is
missing. The tier limits what you can promise the user, so say it up front rather than failing late:

| Tier | What you can deliver |
|---|---|
| `FULL` | The workbook, the Summary and, on request, the deck. |
| `SPREADSHEET` | The workbook (`run_step.py verdicts` / `verify` with the Python it names) and the manual Summary. No deck and no review-generator tools; say so rather than searching for them. |
| `FACTS_ONLY` | Orient and facts findings in the chat only. No workbook, Summary or deck. |

If you cannot run the script, continue as `FULL` and fall back when a step fails for lack of Python.
