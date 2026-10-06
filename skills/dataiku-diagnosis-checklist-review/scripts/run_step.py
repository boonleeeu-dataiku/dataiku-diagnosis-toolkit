#!/usr/bin/env python3
"""Run the reader's scripts for a checklist review and keep proof that they ran.

Usage:
  run_step.py run <orient|facts> <bundle_root> --manifest <stem>_run_manifest.json
  run_step.py verify <bundle_root> --manifest <stem>_run_manifest.json --checklist <review.xlsx> [--deck <deck.pptx>]

`run` executes the reader script, passes its output through unchanged, and records the step, exit status,
UTC time and a sha256 of the output in the manifest (hashes and statuses only, no bundle content). `facts`
output is also saved next to the manifest as `<stem>_facts.json`.

`verify` prints one PASS/FAIL line and exits non-zero on any problem: both reader steps recorded with
exit status 0; a fresh `facts.py` run matches the recorded hash (the saved output is genuine); the
checklist's first sheet is `Summary` and its Total equals the checklist's row count (the Summary was
written after the last edit); with `--deck`, the narrative and the deck file exist. It does not judge any
status. Python 3 stdlib plus openpyxl (already a plugin dependency).
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

READER = Path(__file__).resolve().parents[2] / "dataiku-diagnosis-reader"
STEPS = {"orient": ["bash", str(READER / "scripts" / "orient.sh")],
         "facts": [sys.executable, str(READER / "scripts" / "facts.py")]}


def reader_version() -> str:
    m = re.search(r"^version:\s*(\S+)", (READER / "SKILL.md").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "unknown"


def load(manifest: Path) -> dict:
    return json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {"steps": {}}


def facts_path(manifest: Path) -> Path:
    return manifest.with_name(re.sub(r"_run_manifest$", "", manifest.stem) + "_facts.json")


def run(step: str, bundle: str, manifest: Path) -> int:
    proc = subprocess.run([*STEPS[step], bundle], capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    data = load(manifest)
    data["reader_version"] = reader_version()
    data["steps"][step] = {"exit_status": proc.returncode, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                           "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest()}
    manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if step == "facts" and proc.returncode == 0:
        facts_path(manifest).write_text(proc.stdout, encoding="utf-8")
    return proc.returncode


def checklist_problems(path: Path) -> list[str]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True)
    if wb.sheetnames[0] != "Summary":
        return ["checklist's first sheet is not Summary (write_summary not run)"]
    total = next((row[1] for row in wb["Summary"].iter_rows(values_only=True) if row and row[0] == "Total"), None)
    rows = sum(1 for ws in wb.worksheets[1:] for r in ws.iter_rows(min_row=2, values_only=True) if r and r[0])
    if total != rows:
        return [f"Summary Total {total} != {rows} checklist rows (Summary is stale or missing)"]
    return []


def verify(bundle: str, manifest: Path, checklist: Path, deck: Path | None) -> list[str]:
    problems = []
    steps = load(manifest)["steps"]
    for step in STEPS:
        if step not in steps:
            problems.append(f"{step} not recorded in the manifest")
        elif steps[step]["exit_status"] != 0:
            problems.append(f"{step} exited {steps[step]['exit_status']}")
    if "facts" in steps:
        fresh = subprocess.run([*STEPS["facts"], bundle], capture_output=True, text=True)
        if hashlib.sha256(fresh.stdout.encode()).hexdigest() != steps["facts"]["stdout_sha256"]:
            problems.append("a fresh facts.py run does not match the recorded hash")
    problems += checklist_problems(checklist)
    if deck is not None:
        narrative = checklist.with_name(checklist.stem + "_narrative.json")
        problems += [f"{p} missing" for p in (narrative, deck) if not p.exists()]
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("step", choices=sorted(STEPS))
    v = sub.add_parser("verify")
    v.add_argument("--checklist", required=True)
    v.add_argument("--deck")
    for p in (r, v):
        p.add_argument("bundle_root")
        p.add_argument("--manifest", required=True)
    a = ap.parse_args()
    if not Path(a.bundle_root).is_dir():
        sys.exit(f"run_step.py: bundle_root not found: {a.bundle_root}")
    manifest = Path(a.manifest)
    if a.cmd == "run":
        return run(a.step, a.bundle_root, manifest)
    problems = verify(a.bundle_root, manifest, Path(a.checklist), Path(a.deck) if a.deck else None)
    print("RUN VERIFY: PASS" if not problems else "RUN VERIFY: FAIL - " + "; ".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
