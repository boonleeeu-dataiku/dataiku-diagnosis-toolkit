"""The platform/sizing verdict rules (scripts/rules_platform.py): edge cases on hand-built facts and agreement with the
fixtures' expected answers."""
import json
import subprocess
import sys

import pytest
import yaml

from conftest import FIXTURES, REPO_ROOT

SCRIPTS = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "scripts"
FACTS_PY = REPO_ROOT / "skills" / "dataiku-diagnosis-reader" / "scripts" / "facts.py"
sys.path.insert(0, str(SCRIPTS))
import rules_platform  # noqa: E402,F401
import verdicts  # noqa: E402

RULED = {"SEC-004", "SCALE-001", "SCALE-006", "SCALE-009", "SCALE-011", "ARCH-004"}


def facts(**blocks):
    return {"facts": {name: {"value": value, "source": "test"} for name, value in blocks.items()}}


def run(check_id, doc):
    anchor = verdicts.RULES[check_id][0]
    out = verdicts.compute(doc, [{"id": check_id, "title": anchor}])
    return out["verdicts"][0]["status"] if out["verdicts"] else "undecided"


def cg(pct, enabled=True):
    return {"enabled": enabled, "limits": [{"cgroup": "memory/DSS", "value": "x", "pct_of_MemTotal": pct}] if pct is not None else "ABSENT"}


def host(gib):
    return {"GiB": gib, "MemTotal_kB": int(gib * 1048576)}


def limits(jobs=5, acts=40, per=5):
    wrap = lambda v: [{"path": "p", "value": v}]
    return {"maxRunningJobs": wrap(jobs), "maxRunningActivities": wrap(acts), "maxRunningActivitiesPerJob": wrap(per)}


def test_the_platform_rules_are_registered():
    assert RULED <= set(verdicts.RULES)


@pytest.mark.parametrize("ram,tier_pct", [(250, 75), (120, 66), (62.5, 66), (60, 66), (45, None), (30, None), (16, 50)])
def test_sec004_tier_targets(ram, tier_pct):
    """Pass exactly at the tier target; the target is 75% over 120 GiB, 66% for 60-120, RAM-20 for 30-60, 50% below 30."""
    target = {250: 0.75 * 250, 120: 0.66 * 120, 62.5: 0.66 * 62.5, 60: 0.66 * 60, 45: 25, 30: 10, 16: 8}[ram]
    assert run("SEC-004", facts(cgroups=cg(round(target / ram * 100, 1)), host_memory=host(ram))) == "Pass"


@pytest.mark.parametrize("pct,expected", [
    (66.0, "Pass"), (72.0, "Pass"),            # 9% above a 66% target (62.5 GiB host: 41.25 GiB)
    (74.0, "Needs Review"), (55.0, "Needs Review"),   # more than 10% away either side
    (80.0, "Needs Review"), (95.0, "Needs Review"),   # 80% or more is checked first
])
def test_sec004_band_and_the_80_percent_override(pct, expected):
    assert run("SEC-004", facts(cgroups=cg(pct), host_memory=host(62.5))) == expected


@pytest.mark.parametrize("doc,expected", [
    (facts(cgroups=cg(None, enabled=False), host_memory=host(62.5)), "Fail"),
    (facts(cgroups=cg(None), host_memory=host(62.5)), "Needs Review"),         # enabled, no memory limit
    (facts(cgroups="ABSENT", host_memory=host(62.5)), "Needs Review"),
    (facts(cgroups={"enabled": "ABSENT"}, host_memory=host(62.5)), "Needs Review"),
    (facts(cgroups=cg(66.0), host_memory="ABSENT"), "Needs Review"),
])
def test_sec004_disabled_missing_and_unlimited(doc, expected):
    assert run("SEC-004", doc) == expected


def test_sec004_uses_the_largest_memory_limit_when_several_are_listed():
    two = {"enabled": True, "limits": [{"pct_of_MemTotal": 10.0}, {"pct_of_MemTotal": 66.0}, {"pct_of_MemTotal": None}]}
    assert run("SEC-004", facts(cgroups=two, host_memory=host(62.5))) == "Pass"


@pytest.mark.parametrize("db,expected", [
    ({"type": "PostgreSQL", "host_is_loopback": False}, "Pass"),
    ({"type": "postgresql", "host_is_loopback": True}, "Pass"),   # locally installed: Pass, with a comment
    ({"type": "H2", "host_is_loopback": "ABSENT"}, "Fail"),
    ({"type": "ABSENT", "host_is_loopback": "ABSENT"}, "Needs Review"),
    ({"type": "PostgreSQL", "host_is_loopback": "ABSENT"}, "Needs Review"),
    ("ABSENT", "Needs Review"),
])
def test_scale001_database(db, expected):
    assert run("SCALE-001", facts(internal_database=db)) == expected


@pytest.mark.parametrize("sc,expected", [
    ({"present": True, "empty": False, "messages": 3}, "Pass"),
    ({"present": True, "empty": True, "messages": 0}, "Fail"),
    ("ABSENT", "Fail"),       # a missing sanity check is a Fail here, per the calibration; never Partial or Needs Review
])
def test_scale006_presence_only(sc, expected):
    assert run("SCALE-006", facts(sanity_check=sc)) == expected


@pytest.mark.parametrize("lim,expected", [
    (limits(5, 40, 5), "Pass"),
    (limits(5, 30, 5), "Pass"), (limits(5, 50, 5), "Pass"),
    (limits(0, 40, 5), "Fail"), (limits(5, 0, 5), "Fail"), (limits(5, 40, 0), "Fail"),
    (limits(None, 40, 5), "Fail"),                   # blank means unsized
    (limits(0, 0, 0), "Fail"),
    (limits(5, 10, 5), "Needs Review"), (limits(5, 60, 5), "Needs Review"), (limits(5, 40, 4), "Needs Review"),
])
def test_scale009_flow_limits(lim, expected):
    assert run("SCALE-009", facts(concurrency_limits=lim)) == expected


def test_scale009_a_missing_limit_is_needs_review_and_a_limit_in_another_place_still_counts():
    partial = limits()
    partial["maxRunningJobs"] = "ABSENT"
    assert run("SCALE-009", facts(concurrency_limits=partial)) == "Needs Review"
    assert run("SCALE-009", facts(concurrency_limits="ABSENT")) == "Needs Review"
    moved = limits(0, 40, 5)
    moved["maxRunningJobs"] = [{"path": "jekSettings.maxRunningJobs", "value": 0}]
    assert run("SCALE-009", facts(concurrency_limits=moved)) == "Fail"


@pytest.mark.parametrize("conns,expected", [
    ({"filesystem_root_present": True}, "Fail"), ({"filesystem_root_present": False}, "Pass"),
    ({"filesystem_root_present": "ABSENT"}, "Needs Review"), ("ABSENT", "Needs Review"),
])
def test_scale011_filesystem_root(conns, expected):
    assert run("SCALE-011", facts(connections=conns)) == expected


SSD, HDD = {"all_non_rotational": True}, {"all_non_rotational": False}
QUIET = {"empty": True, "messages": 0, "codes": []}
WARN_OTHER = {"empty": False, "messages": 4, "codes": ["WARN_PROJECT_LARGE_JOB_HISTORY", "WARN_MISC_CODE_ENV_USES_PYSPARK"]}
WARN_DISK = {"empty": False, "messages": 2, "codes": ["WARN_MISC_DATADIR_ON_ROTATIONAL_DISK", "WARN_SECURITY_NO_CGROUPS"]}
WARN_OLD = {"empty": False, "messages": 2}   # a facts.py without message codes


@pytest.mark.parametrize("vol,sanity,expected", [
    (SSD, QUIET, "Pass"), (SSD, "ABSENT", "Pass"),
    (SSD, WARN_OTHER, "Pass"),                 # sanity messages about other things do not block a Pass
    (SSD, WARN_DISK, "Fail"),                  # DSS's own sanity check is authoritative
    (HDD, QUIET, "Fail"), (HDD, WARN_OTHER, "Fail"),
    ("ABSENT", WARN_DISK, "Fail"),             # flagged even when lsblk could not be read
    ("ABSENT", WARN_OTHER, "Needs Review"), ("ABSENT", QUIET, "Needs Review"), ("ABSENT", "ABSENT", "Needs Review"),
    ({"backing_disks": []}, QUIET, "Needs Review"),
    (SSD, WARN_OLD, "undecided"), ("ABSENT", WARN_OLD, "undecided"),   # older facts: the model reads the sanity-check text
])
def test_arch004_disks_and_sanity_check(vol, sanity, expected):
    assert run("ARCH-004", facts(data_volume_device=vol, sanity_check=sanity)) == expected


def test_arch004_reason_names_the_flagging_code_and_matches_case_insensitively():
    doc = facts(data_volume_device=SSD, sanity_check={"empty": False, "messages": 1, "codes": ["warn_datadir_on_Rotational_disk"]})
    out = verdicts.compute(doc, [{"id": "ARCH-004", "title": "SSD Storage for DSS"}])["verdicts"][0]
    assert out["status"] == "Fail" and "warn_datadir_on_Rotational_disk" in out["reason"]


def test_scale001_loopback_reason_says_it_is_installed_locally():
    out = verdicts.compute(facts(internal_database={"type": "PostgreSQL", "host_is_loopback": True}),
                           [{"id": "SCALE-001", "title": verdicts.RULES["SCALE-001"][0]}])["verdicts"][0]
    assert out["status"] == "Pass" and "locally installed" in out["reason"]


def test_an_undecided_row_is_listed_and_gets_no_verdict():
    doc = verdicts.compute(facts(data_volume_device="ABSENT", sanity_check=WARN_OLD), [{"id": "ARCH-004", "title": "SSD Storage for DSS"}])
    assert doc["verdicts"] == [] and doc["undecided"] == [{"id": "ARCH-004", "title": "SSD Storage for DSS"}]


@pytest.mark.parametrize("scenario", sorted(p.stem for p in (FIXTURES / "expected").glob("*.yaml")))
def test_platform_rules_agree_with_the_fixtures_expected_answers(scenario):
    proc = subprocess.run([sys.executable, "-B", str(FACTS_PY), str(FIXTURES / "bundles" / scenario)], capture_output=True, text=True, check=True)
    expected = yaml.safe_load((FIXTURES / "expected" / f"{scenario}.yaml").read_text())["items"]
    rows = [{"id": i, "title": verdicts.RULES[i][0]} for i in RULED]
    doc = verdicts.compute(json.loads(proc.stdout), rows)
    decided = {v["id"]: v["status"] for v in doc["verdicts"]}
    assert len(decided) + len(doc["undecided"]) == len(RULED)
    for check_id, status in decided.items():
        if check_id in expected:
            assert status in expected[check_id]["status"], f"{scenario} {check_id}: verdict {status}, expected {expected[check_id]['status']}"
