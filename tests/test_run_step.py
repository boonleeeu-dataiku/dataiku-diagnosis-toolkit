"""run_step.py (checklist-review skill): records reader script runs and verifies a finished review."""
import json
import subprocess
import sys

import openpyxl

from conftest import FIXTURES, REPO_ROOT

SCRIPT = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "scripts" / "run_step.py"
BUNDLE = FIXTURES / "bundles" / "synthetic_design_baseline"


def _sh(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)


def _checklist(path, *, summary=True, total=2):
    wb = openpyxl.Workbook()
    wb.active.title = "Summary" if summary else "Other"
    if summary:
        wb["Summary"].append(["Total", total])
    ws = wb.create_sheet("Section")
    ws.append(["id", "validation_status"])
    ws.append(["A-1", "Pass"])
    ws.append(["A-2", "Fail"])
    wb.save(path)


def _record_both(manifest):
    for step in ("orient", "facts"):
        assert _sh("run", step, BUNDLE, "--manifest", manifest).returncode == 0


def test_run_records_steps_and_saves_facts(tmp_path):
    manifest = tmp_path / "r_run_manifest.json"
    _record_both(manifest)
    data = json.loads(manifest.read_text())
    assert set(data["steps"]) == {"orient", "facts"} and data["reader_version"] != "unknown"
    assert all(s["exit_status"] == 0 and len(s["stdout_sha256"]) == 64 for s in data["steps"].values())
    assert "facts" in json.loads((tmp_path / "r_facts.json").read_text())


def test_verify_passes_on_a_complete_run(tmp_path):
    manifest, xlsx = tmp_path / "r_run_manifest.json", tmp_path / "r.xlsx"
    _record_both(manifest)
    _checklist(xlsx)
    out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx)
    assert out.returncode == 0 and "PASS" in out.stdout, out.stdout


def test_verify_fails_when_facts_never_ran_or_hash_is_wrong(tmp_path):
    manifest, xlsx = tmp_path / "r_run_manifest.json", tmp_path / "r.xlsx"
    _checklist(xlsx)
    assert "orient not recorded" in _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx).stdout
    _record_both(manifest)
    data = json.loads(manifest.read_text())
    data["steps"]["facts"]["stdout_sha256"] = "0" * 64
    manifest.write_text(json.dumps(data))
    out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx)
    assert out.returncode == 1 and "does not match" in out.stdout


def test_verify_fails_on_missing_or_stale_summary_and_missing_deck(tmp_path):
    manifest = tmp_path / "r_run_manifest.json"
    _record_both(manifest)
    for kwargs, msg in (({"summary": False}, "not Summary"), ({"total": 5}, "stale")):
        xlsx = tmp_path / "x.xlsx"
        _checklist(xlsx, **kwargs)
        out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx)
        assert out.returncode == 1 and msg in out.stdout, out.stdout
    xlsx = tmp_path / "r.xlsx"
    _checklist(xlsx)
    out = _sh("verify", BUNDLE, "--manifest", manifest, "--checklist", xlsx, "--deck", tmp_path / "d.pptx")
    assert out.returncode == 1 and "missing" in out.stdout
