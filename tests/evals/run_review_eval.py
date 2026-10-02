#!/usr/bin/env python3
"""On-demand LLM eval for the dataiku-diagnosis-checklist-review skill.

For each synthetic scenario in tests/fixtures/expected/, runs a headless Claude Code
session N times with this repo loaded as the plugin under test. Each session reviews that
scenario's bundle against the eval checklist and writes a workbook, which is then scored per
item with tests/lib/check_review_output.py.

    python tests/evals/run_review_eval.py [--model M] [--runs 3] [--scenario NAME] \
        [--max-budget-usd 3] [-j 2] [--save-baseline]

Why this isn't a `claude plugin eval` case: plugin evals have no custom-code graders, and their
LLM judges refuse binary files, so a .xlsx can't be scored item by item there. The
behavioural cases that can be graded from the reply or the tool calls live in evals/.

Each run costs real model usage (a full review of 11 items). Results go to
evals/results/review/<timestamp>/, which is gitignored. --save-baseline also copies the
summary to evals/baselines/review-<model>.json for tests/evals/compare.py.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
sys.path.insert(0, str(REPO_ROOT / "tests" / "lib"))

import check_review_output as cro  # noqa: E402

PLUGIN = "dataiku-diagnosis-toolkit"
ALLOWED_TOOLS = [
    "Read", "Write", "Edit", "Glob", "Grep", "Skill", "Bash", "TodoWrite",
    f"mcp__plugin_{PLUGIN}_dataiku-diagnosis-reader__run_orient",
    f"mcp__plugin_{PLUGIN}_dataiku-diagnosis-reader__safe_read",
]
# Web access is withheld on purpose: the version-currency calibration must then answer
# Needs Review and say it couldn't verify, rather than guess the latest release.
DISALLOWED_TOOLS = ["WebSearch", "WebFetch"]

PROMPT = """Review the Dataiku DSS diagnosis bundle at {bundle} against the checklist at \
{workdir}/checklist.xlsx. Save the completed workbook as {workdir}/review.xlsx and leave \
checklist.xlsx unchanged. Work through it on your own without asking me questions. Web search \
isn't available in this session."""


def run_once(scenario: str, run: int, args, out_dir: Path) -> dict:
    bundle = FIXTURES / "bundles" / scenario
    expected = FIXTURES / "expected" / f"{scenario}.yaml"
    run_dir = out_dir / scenario / f"run{run}"
    run_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="review-eval-") as tmp:
        workdir = Path(tmp)
        shutil.copy(FIXTURES / "checklists" / "eval_checklist.xlsx", workdir / "checklist.xlsx")
        cmd = [
            "claude", "-p", PROMPT.format(bundle=bundle, workdir=workdir),
            "--plugin-dir", str(REPO_ROOT),
            # user-level settings would also load any installed copy of this plugin
            "--setting-sources", "project,local",
            "--add-dir", str(bundle),
            "--allowedTools", *ALLOWED_TOOLS,
            "--disallowedTools", *DISALLOWED_TOOLS,
            "--max-turns", str(args.max_turns),
            "--max-budget-usd", str(args.max_budget_usd),
            "--output-format", "json",
            "--no-session-persistence",
        ]
        if args.model:
            cmd += ["--model", args.model]

        started = time.time()
        proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=args.timeout)
        elapsed = round(time.time() - started, 1)
        (run_dir / "claude-output.json").write_text(proc.stdout)
        if proc.stderr:
            (run_dir / "claude-stderr.txt").write_text(proc.stderr)
        try:
            meta = json.loads(proc.stdout)
        except json.JSONDecodeError:
            meta = {}

        usage = meta.get("modelUsage") or {}
        result = {
            "scenario": scenario, "run": run, "seconds": elapsed,
            # the model that did most of the work (sub-calls may use a smaller one)
            "model": max(usage, key=lambda k: usage[k].get("costUSD", 0)) if usage else None,
            "cost_usd": meta.get("total_cost_usd"), "num_turns": meta.get("num_turns"),
            "session_error": meta.get("is_error", proc.returncode != 0) and (meta.get("subtype") or f"exit {proc.returncode}"),
        }
        review = workdir / "review.xlsx"
        if not review.exists():
            result.update(produced=False, items={}, structure=["review.xlsx was not written"], citations=[])
            return result
        shutil.copy(review, run_dir / "review.xlsx")

    report = cro.check(run_dir / "review.xlsx", bundle, expected)
    (run_dir / "check-report.json").write_text(json.dumps(report.to_dict(), indent=2))
    spec_ids = cro.yaml.safe_load(expected.read_text())["items"]
    result.update(
        produced=True,
        structure=report.structure,
        citations=report.citations,
        items={i: {"status": report.items[i].status, "ok": report.items[i].ok,
                   "failures": report.items[i].failures} for i in spec_ids},
    )
    return result


def summarize(results: list[dict], model: str) -> dict:
    by_scenario = {}
    for r in results:
        s = by_scenario.setdefault(r["scenario"], {"runs": 0, "produced": 0, "structure_clean": 0,
                                                   "citations_clean": 0, "items": {}})
        s["runs"] += 1
        s["produced"] += bool(r["produced"])
        s["structure_clean"] += r["produced"] and not r["structure"]
        s["citations_clean"] += r["produced"] and not r["citations"]
        for item_id, item in r["items"].items():
            s["items"].setdefault(item_id, []).append(item["ok"])
    for s in by_scenario.values():
        s["item_pass_rate"] = {i: round(sum(v) / s["runs"], 3) for i, v in sorted(s["items"].items())}
        s["accuracy"] = round(sum(sum(v) for v in s["items"].values()) / max(1, s["runs"] * len(s["items"])), 3)
        del s["items"]
    costs = [r["cost_usd"] for r in results if r.get("cost_usd") is not None]
    return {
        "kind": "checklist-review-eval",
        "model": model or max({r.get("model") for r in results if r.get("model")} or {"default"},
                              key=lambda m: sum(r.get("model") == m for r in results)),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cost_usd": round(sum(costs), 2),
        "scenarios": by_scenario,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", help="model under test (default: Claude Code's default)")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--scenario", action="append", help="limit to these scenario names (repeatable)")
    ap.add_argument("--max-turns", type=int, default=80)
    ap.add_argument("--max-budget-usd", type=float, default=3.0, help="per-run spend cap")
    ap.add_argument("--timeout", type=int, default=1800, help="per-run wall-clock cap, seconds")
    ap.add_argument("-j", "--concurrency", type=int, default=1)
    ap.add_argument("--save-baseline", action="store_true")
    args = ap.parse_args(argv)

    scenarios = args.scenario or sorted(p.stem for p in (FIXTURES / "expected").glob("*.yaml"))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = REPO_ROOT / "evals" / "results" / "review" / stamp
    jobs = [(s, r) for s in scenarios for r in range(1, args.runs + 1)]
    print(f"{len(jobs)} run(s) -> {out_dir.relative_to(REPO_ROOT)}", file=sys.stderr)

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(lambda job: run_once(*job, args, out_dir), jobs))
    for r in results:
        bad = {i: v["status"] for i, v in r["items"].items() if not v["ok"]}
        print(f"  {r['scenario']} run{r['run']}: produced={r['produced']} structure={len(r['structure'])} "
              f"citations={len(r['citations'])} wrong={bad or '-'} cost=${r['cost_usd']}", file=sys.stderr)

    (out_dir / "runs.json").write_text(json.dumps(results, indent=2))
    summary = summarize(results, args.model)
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if args.save_baseline:
        dest = REPO_ROOT / "evals" / "baselines" / f"review-{summary['model']}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(summary, indent=2) + "\n")
        print(f"baseline saved: {dest.relative_to(REPO_ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
