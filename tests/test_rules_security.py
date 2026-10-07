"""The security verdict rules (scripts/rules_security.py): edge cases on hand-built facts, agreement with the fixtures'
expected answers, and anchors that match the bundled checklist's titles."""
import json
import subprocess
import sys

import openpyxl
import pytest
import yaml

from conftest import FIXTURES, REPO_ROOT, TEMPLATE

SCRIPTS = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "scripts"
FACTS_PY = REPO_ROOT / "skills" / "dataiku-diagnosis-reader" / "scripts" / "facts.py"
sys.path.insert(0, str(SCRIPTS))
import rules_platform  # noqa: E402,F401  (registered so the title-anchor test sees every rule)
import rules_security  # noqa: E402,F401  (registers the rules)
import verdicts  # noqa: E402

RULED = {"SEC-001", "SEC-002", "SEC-005", "SEC-009", "SEC-010"}


def facts(**blocks):
    return {"facts": {name: {"value": value, "source": "test"} for name, value in blocks.items()}}


def status(check_id, doc):
    anchor = verdicts.RULES[check_id][0]
    out = verdicts.compute(doc, [{"id": check_id, "title": anchor}])["verdicts"]
    return out[0]["status"]


def sso(sso_enabled="ABSENT", ldap="ABSENT", groups="ABSENT"):
    return {"ssoSettings.enabled": sso_enabled, "ssoSettings.protocol": "ABSENT",
            "ldapSettings.enabled": ldap, "ldapSettings.authorizedGroups_count": groups}


def test_the_security_rules_are_registered():
    assert RULED <= set(verdicts.RULES)


@pytest.mark.parametrize("check_id,doc,expected", [
    # SEC-001: instance id
    ("SEC-001", facts(node={"installid": "X1"}), "Pass"),
    ("SEC-001", facts(node={"installid": "ABSENT"}), "Fail"),
    ("SEC-001", facts(node="ABSENT"), "Needs Review"),
    ("SEC-001", facts(), "Needs Review"),
    # SEC-002: UIF
    ("SEC-002", facts(user_isolation={"enabled": True, "user_rules": 1, "group_rules": 0}), "Pass"),
    ("SEC-002", facts(user_isolation={"enabled": True, "user_rules": 0, "group_rules": 2}), "Pass"),
    ("SEC-002", facts(user_isolation={"enabled": True, "user_rules": 0, "group_rules": 0}), "Partial"),
    ("SEC-002", facts(user_isolation={"enabled": False, "user_rules": 3, "group_rules": 0}), "Fail"),
    ("SEC-002", facts(user_isolation={"enabled": "ABSENT", "user_rules": 0, "group_rules": 0}), "Needs Review"),
    ("SEC-002", facts(user_isolation="ABSENT"), "Needs Review"),
    # SEC-005: no JEK-specific cgroup target
    ("SEC-005", facts(cgroups={"target_counts": {"pythonRRecipes": 1}}), "Pass"),            # no JEK category at all
    ("SEC-005", facts(cgroups={"target_counts": {"jobExecutionKernels": 0}}), "Pass"),
    ("SEC-005", facts(cgroups={"target_counts": {"jobExecutionKernels": 1}}), "Fail"),
    ("SEC-005", facts(cgroups={"enabled": False, "target_counts": {"jobExecutionKernels": 2}}), "Fail"),  # configured though disabled
    ("SEC-005", facts(cgroups="ABSENT"), "Needs Review"),
    ("SEC-005", facts(cgroups={"enabled": True}), "Needs Review"),                          # older facts.py without target_counts
    # SEC-009: LDAP authorized groups
    ("SEC-009", facts(sso_and_ldap=sso(ldap=True, groups=2)), "Pass"),
    ("SEC-009", facts(sso_and_ldap=sso(ldap=True, groups=0)), "Fail"),
    ("SEC-009", facts(sso_and_ldap=sso(ldap=False)), "Not Applicable"),
    ("SEC-009", facts(sso_and_ldap=sso(ldap="ABSENT")), "Needs Review"),
    ("SEC-009", facts(sso_and_ldap=sso(ldap=True, groups="ABSENT")), "Needs Review"),
    ("SEC-009", facts(), "Needs Review"),
    # SEC-010: SSO (checked in the calibration's order: SSO disabled is Fail whatever LDAP is)
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=False, ldap=False)), "Fail"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=False, ldap=True)), "Fail"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=False)), "Fail"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=True, ldap=True)), "Pass"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=True, ldap=False)), "Needs Review"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=True)), "Needs Review"),
    ("SEC-010", facts(sso_and_ldap=sso()), "Needs Review"),
    ("SEC-010", facts(), "Needs Review"),
])
def test_rule_status_on_edge_cases(check_id, doc, expected):
    assert status(check_id, doc) == expected


def test_verdict_reasons_never_carry_secret_looking_values():
    out = verdicts.compute(facts(node={"installid": "X1"}, sso_and_ldap=sso(sso_enabled=True, ldap=True)),
                           [{"id": "SEC-010", "title": verdicts.RULES["SEC-010"][0]}])["verdicts"][0]
    assert set(out["deciding_values"]) == {"sso_enabled", "ldap_enabled", "sso_protocol"}


@pytest.mark.parametrize("scenario", sorted(p.stem for p in (FIXTURES / "expected").glob("*.yaml")))
def test_rules_agree_with_the_fixtures_expected_answers(scenario):
    """Each ruled item's verdict on the fixture bundle's real facts must be one the expected answer allows."""
    proc = subprocess.run([sys.executable, "-B", str(FACTS_PY), str(FIXTURES / "bundles" / scenario)],
                          capture_output=True, text=True, check=True)
    expected = yaml.safe_load((FIXTURES / "expected" / f"{scenario}.yaml").read_text())["items"]
    rows = [{"id": i, "title": verdicts.RULES[i][0]} for i in RULED]
    got = {v["id"]: v["status"] for v in verdicts.compute(json.loads(proc.stdout), rows)["verdicts"]}
    checked = 0
    for check_id, status_ in got.items():
        if check_id in expected:
            assert status_ in expected[check_id]["status"], f"{scenario} {check_id}: verdict {status_}, expected {expected[check_id]['status']}"
            checked += 1
    assert checked >= len(RULED & set(expected))


def test_every_rule_anchor_equals_its_title_in_the_bundled_checklist():
    titles = {}
    for ws in openpyxl.load_workbook(TEMPLATE, read_only=True).worksheets:
        rows = list(ws.iter_rows(values_only=True))
        head = list(rows[0])
        titles.update({r[head.index("id")]: r[head.index("title")] for r in rows[1:] if r and r[0]})
    for check_id, (anchor, _) in verdicts.RULES.items():
        assert check_id in titles, f"{check_id} is not in the bundled checklist"
        assert verdicts.norm(titles[check_id]) == verdicts.norm(anchor), f"{check_id}: anchor {anchor!r} vs template {titles[check_id]!r}"
