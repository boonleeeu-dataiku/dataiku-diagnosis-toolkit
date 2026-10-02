#!/usr/bin/env python3
"""Compare a checklist-review eval summary against a baseline and flag regressions.

    python tests/evals/compare.py BASELINE.json CANDIDATE.json [--tolerance 0.34]

Both files are summary.json outputs of run_review_eval.py (baselines live in
evals/baselines/). Flags every scenario metric or per-item pass rate that dropped by more
than --tolerance. The default of 0.34 ignores a one-run wobble out of 3 runs. Exit code 1
if anything regressed.
"""

import argparse
import json
import sys

RATE_METRICS = ("produced", "structure_clean", "citations_clean")


def compare(base: dict, cand: dict, tolerance: float) -> tuple[list[str], list[str]]:
    regressions, notes = [], []
    for scenario, b in base["scenarios"].items():
        c = cand["scenarios"].get(scenario)
        if c is None:
            notes.append(f"{scenario}: not in candidate run")
            continue
        for metric in RATE_METRICS:
            br, cr = b[metric] / b["runs"], c[metric] / c["runs"]
            if br - cr > tolerance:
                regressions.append(f"{scenario}: {metric} {br:.2f} -> {cr:.2f}")
        if b["accuracy"] - c["accuracy"] > tolerance / 3:
            regressions.append(f"{scenario}: accuracy {b['accuracy']:.2f} -> {c['accuracy']:.2f}")
        for item, br in b["item_pass_rate"].items():
            cr = c["item_pass_rate"].get(item)
            if cr is None:
                notes.append(f"{scenario}/{item}: not in candidate run")
            elif br - cr > tolerance:
                regressions.append(f"{scenario}/{item}: pass rate {br:.2f} -> {cr:.2f}")
            elif cr - br > tolerance:
                notes.append(f"{scenario}/{item}: improved {br:.2f} -> {cr:.2f}")
    return regressions, notes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("baseline")
    ap.add_argument("candidate")
    ap.add_argument("--tolerance", type=float, default=0.34)
    args = ap.parse_args(argv)
    with open(args.baseline) as f:
        base = json.load(f)
    with open(args.candidate) as f:
        cand = json.load(f)

    print(f"baseline:  {base['model']} ({base['created']})")
    print(f"candidate: {cand['model']} ({cand['created']})")
    for name, s in cand["scenarios"].items():
        b = base["scenarios"].get(name, {})
        print(f"  {name}: accuracy {b.get('accuracy', '-')} -> {s['accuracy']}")
    regressions, notes = compare(base, cand, args.tolerance)
    for n in notes:
        print(f"  note: {n}")
    for r in regressions:
        print(f"  REGRESSION: {r}")
    print("REGRESSED" if regressions else "OK: no regressions beyond tolerance")
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
