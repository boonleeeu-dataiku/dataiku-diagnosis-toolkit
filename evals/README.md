# Plugin evals

Behavioural eval cases for `claude plugin eval`. Run them on demand, for example when changing
a skill or switching models. Each case is graded from Claude's reply and its tool calls, and the
plugin's MCP servers are **mocked** (`<case>/mocks/`). So these cases need no real bundle, no
branding template, and no tool grants.

```sh
claude plugin eval . --runs 3 --max-cost-usd 5            # all cases, with/without-plugin delta
claude plugin eval . --case 'deck-*' --ablation none      # cheaper: deck cases, plugin arm only
claude plugin eval . --model <model-id> --json evals/results/<name>.json
```

| Case | Checks |
|---|---|
| `reader-crash-triage` | The reader skill calls `run_orient` first and identifies node type, version, and the memory-exhaustion crash cause. Mocks are built from `tests/fixtures/bundles/synthetic_design_baseline` |
| `deck-missing-base` | On "Base deck not found", the deck builder relays the error and asks for the template. It doesn't retry with a guessed path |
| `deck-data-warnings` | When the build returns `data_warnings`, the deck builder surfaces them and says to fix the checklist, not the deck |

The **checklist-review** skill is evaluated separately by `tests/evals/run_review_eval.py`. Its
output is an `.xlsx` workbook, which plugin-eval graders can't score item by item: there are no
custom-code graders, and the LLM judges refuse binary files. See the top-level README's Testing
section.

`mocks/<server>/_tools.json` holds each server's real `tools/list` response, so mocked tools show
their real schemas. After changing a tool's signature, regenerate them with
`scripts/refresh-eval-tool-schemas.sh`. If the orient output format changes, regenerate
`reader-crash-triage/mocks/.../fixtures/orient.txt` from the same synthetic bundle the same way.
