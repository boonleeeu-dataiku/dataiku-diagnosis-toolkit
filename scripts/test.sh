#!/usr/bin/env bash
# Test runner for the whole toolkit.
#
#   scripts/test.sh fast                  deterministic tests, no model calls (run on every change):
#                                           mcp-server-review-generator pytest suite (vendored)
#                                           toolkit-level pytest suite (tests/)
#   scripts/test.sh eval [options]        on-demand LLM evals (cost real usage):
#                                           claude plugin eval (evals/: deck-builder cases)
#                                           tests/evals/run_review_eval.py (checklist-review scenarios)
#     --model <id>        model under test for both (default: Claude Code's default)
#     --runs <n>          runs per case/scenario (default 3)
#     --max-cost-usd <n>  ceiling for the plugin-eval part (default 5)
#
# Python tests use mcp-server-review-generator/.venv (see README's One-time setup); this
# installs pytest into it on first use via requirements-dev.txt.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
PY="$ROOT/mcp-server-review-generator/.venv/bin/python"

ensure_python() {
  if [ ! -x "$PY" ]; then
    echo "Creating mcp-server-review-generator/.venv ..." >&2
    python3 -m venv mcp-server-review-generator/.venv
  fi
  if ! "$PY" -c "import pytest, openpyxl, yaml" 2>/dev/null; then
    "$PY" -m pip install -q -r mcp-server-review-generator/requirements-dev.txt >&2
  fi
}

run_fast() {
  ensure_python
  local failed=0

  echo "== mcp-server-review-generator (pytest)"
  (cd mcp-server-review-generator && "$PY" -m pytest) || failed=1

  echo "== toolkit (pytest tests/)"
  "$PY" -m pytest tests || failed=1

  if [ "$failed" -ne 0 ]; then
    echo "FAILED: see output above" >&2
    exit 1
  fi
  echo "All fast tests passed."
}

run_eval() {
  ensure_python
  local model="" runs=3 max_cost=5
  while [ $# -gt 0 ]; do
    case "$1" in
      --model) model="$2"; shift 2 ;;
      --runs) runs="$2"; shift 2 ;;
      --max-cost-usd) max_cost="$2"; shift 2 ;;
      *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
  done
  local model_args=()
  [ -n "$model" ] && model_args=(--model "$model")

  local stamp
  stamp="$(date +%Y%m%d-%H%M%S)"
  echo "== claude plugin eval (evals/)"
  claude plugin eval . --runs "$runs" --max-cost-usd "$max_cost" --no-publish \
    --json "evals/results/plugin-eval-$stamp.json" ${model_args[@]+"${model_args[@]}"} || true

  echo "== checklist-review scenarios (tests/evals/run_review_eval.py)"
  "$PY" tests/evals/run_review_eval.py --runs "$runs" ${model_args[@]+"${model_args[@]}"}
  echo "Compare against a baseline with: $PY tests/evals/compare.py evals/baselines/<file>.json evals/results/review/<stamp>/summary.json"
}

case "${1:-fast}" in
  fast) run_fast ;;
  eval) shift; run_eval "$@" ;;
  *) echo "usage: scripts/test.sh [fast|eval [--model M] [--runs N] [--max-cost-usd N]]" >&2; exit 2 ;;
esac
