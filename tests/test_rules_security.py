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
    ("SEC-009", facts(sso_and_ldap=sso(ldap=True, groups=0)), "Needs Review"),
    ("SEC-009", facts(sso_and_ldap=sso(ldap=False)), "Not Applicable"),
    ("SEC-009", facts(sso_and_ldap=sso(ldap="ABSENT")), "Needs Review"),
    ("SEC-009", facts(sso_and_ldap=sso(ldap=True, groups="ABSENT")), "Needs Review"),
    ("SEC-009", facts(), "Needs Review"),
    # SEC-010: SSO on is Pass and off is Fail, whatever LDAP is
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=False, ldap=False)), "Fail"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=False, ldap=True)), "Fail"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=False)), "Fail"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=True, ldap=True)), "Pass"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=True, ldap=False)), "Pass"),
    ("SEC-010", facts(sso_and_ldap=sso(sso_enabled=True)), "Pass"),
    ("SEC-010", facts(sso_and_ldap=sso()), "Needs Review"),
    ("SEC-010", facts(), "Needs Review"),
])
def test_rule_status_on_edge_cases(check_id, doc, expected):
    assert status(check_id, doc) == expected


def test_verdict_reasons_never_carry_secret_looking_values():
    out = verdicts.compute(facts(node={"installid": "X1"}, sso_and_ldap=sso(sso_enabled=True, ldap=True)),
                           [{"id": "SEC-010", "title": verdicts.RULES["SEC-010"][0]}])["verdicts"][0]
    assert set(out["deciding_values"]) == {"sso_enabled", "sso_protocol"}


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


# --- the `security` settings block (Batch 3a) --------------------------------------------------------------------

SEC_BLOCK = {"ADVSEC-001", "ADVSEC-002", "ADVSEC-003", "ADVSEC-004", "ADVSEC-005", "ADVSEC-006", "ADVSEC-010", "ADVSEC-012", "SEC-007"}


def sec(**kw):
    base = {"hideErrorStacks": "ABSENT", "hideVersionStringsWhenNotLogged": "ABSENT", "sessionsMaxTotalTimeMinutes": "ABSENT",
            "sessionsMaxIdleTimeMinutes": "ABSENT", "forceSingleSessionPerUser": "ABSENT", "restrictUsersAndGroupsVisibility": "ABSENT",
            "postLogoutBehavior": "ABSENT", "sameSiteNoneCookies": "ABSENT", "secureCookies": "ABSENT",
            "enableEmailAndDisplayNameModification": "ABSENT", "disableDataTableLinks": "ABSENT", "postLogoutCustomURL_scheme": "ABSENT"}
    base.update(kw)
    return facts(security_settings=base)


def test_the_security_block_rules_are_registered():
    assert SEC_BLOCK <= set(verdicts.RULES)


@pytest.mark.parametrize("check_id,key,on,off,off_status", [
    ("ADVSEC-001", "hideErrorStacks", True, False, "Fail"),
    ("ADVSEC-002", "hideVersionStringsWhenNotLogged", True, False, "Fail"),
    ("ADVSEC-004", "forceSingleSessionPerUser", True, False, "Fail"),
    ("ADVSEC-005", "restrictUsersAndGroupsVisibility", True, False, "Needs Review"),   # may be deliberately left off
    ("SEC-007", "secureCookies", True, False, "Needs Review"),                          # only safe once all access is HTTPS
    ("ADVSEC-012", "enableEmailAndDisplayNameModification", False, True, "Needs Review"),  # secure value is false
])
def test_simple_toggles(check_id, key, on, off, off_status):
    assert status(check_id, sec(**{key: on})) == "Pass"
    assert status(check_id, sec(**{key: off})) == off_status
    assert status(check_id, sec()) == "Needs Review"                 # key missing from the block
    assert status(check_id, facts()) == "Needs Review"               # whole block missing


@pytest.mark.parametrize("total,idle,expected", [
    (0, 0, "Fail"), (480, 0, "Pass"), (0, 30, "Pass"), (480, 30, "Pass"),
    ("ABSENT", "ABSENT", "Needs Review"), (0, "ABSENT", "Needs Review"), ("ABSENT", 30, "Pass"),
])
def test_advsec003_session_timeouts_zero_means_unlimited(total, idle, expected):
    assert status("ADVSEC-003", sec(sessionsMaxTotalTimeMinutes=total, sessionsMaxIdleTimeMinutes=idle)) == expected


@pytest.mark.parametrize("behavior,scheme,expected", [
    ("LOGGED_OUT_PAGE", "ABSENT", "Not Applicable"), ("ABSENT", "ABSENT", "Not Applicable"),
    ("CUSTOM_URL", "https", "Pass"), ("CUSTOM_URL_POST", "http", "Pass"),
    ("CUSTOM_URL", "other", "Fail"), ("CUSTOM_URL", "ABSENT", "Fail"),
])
def test_advsec006_custom_logout_redirect(behavior, scheme, expected):
    assert status("ADVSEC-006", sec(postLogoutBehavior=behavior, postLogoutCustomURL_scheme=scheme)) == expected


@pytest.mark.parametrize("same_site,secure,expected", [
    (False, True, "Pass"), (False, False, "Pass"), (False, "ABSENT", "Pass"),
    (True, True, "Needs Review"),            # enabled with secure cookies: ask for the documented iframe need
    (True, False, "Fail"),                   # enabled without secure cookies
    (True, "ABSENT", "Needs Review"),
    ("ABSENT", True, "Needs Review"),
])
def test_advsec010_iframe_hosting(same_site, secure, expected):
    assert status("ADVSEC-010", sec(sameSiteNoneCookies=same_site, secureCookies=secure)) == expected


@pytest.mark.parametrize("scenario", sorted(p.stem for p in (FIXTURES / "expected").glob("*.yaml")))
def test_security_block_rules_agree_with_the_fixtures_expected_answers(scenario):
    proc = subprocess.run([sys.executable, "-B", str(FACTS_PY), str(FIXTURES / "bundles" / scenario)], capture_output=True, text=True, check=True)
    expected = yaml.safe_load((FIXTURES / "expected" / f"{scenario}.yaml").read_text())["items"]
    rows = [{"id": i, "title": verdicts.RULES[i][0]} for i in SEC_BLOCK]
    got = {v["id"]: v["status"] for v in verdicts.compute(json.loads(proc.stdout), rows)["verdicts"]}
    assert set(got) == SEC_BLOCK
    for check_id, status_ in got.items():
        if check_id in expected:
            assert status_ in expected[check_id]["status"], f"{scenario} {check_id}: verdict {status_}, expected {expected[check_id]['status']}"


# --- server settings: HTTPS, exports, uploads, links, headers (Batch 3b) ------------------------------------------------

SERVER_RULES = {"SEC-006", "ADVSEC-007", "ADVSEC-008", "ADVSEC-009", "ADVSEC-011"}
CORE = {"content-security-policy": "script-src 'self'", "x-frame-options": "SAMEORIGIN", "x-content-type-options": "nosniff",
        "x-xss-protection": "1;mode=block", "hsts-max-age": "31536000", "referrer-policy": "same-origin"}


def server(**kw):
    base = {"ssl": "ABSENT", "ssl_certificate_configured": False, "security_headers": {}, "dip_properties_present": True,
            "exports": {}, "wiki_upload_extensions": "ABSENT", "data_table_links_enabled": "ABSENT"}
    base.update(kw)
    return base


def test_the_server_rules_are_registered():
    assert SERVER_RULES <= set(verdicts.RULES)


@pytest.mark.parametrize("cfg,expected", [
    (server(ssl="true", ssl_certificate_configured=True), "Pass"),
    (server(ssl="True", ssl_certificate_configured=True), "Pass"),
    (server(ssl="true", ssl_certificate_configured=False), "Needs Review"),     # TLS on but no certificate
    (server(ssl="false", ssl_certificate_configured=True), "Needs Review"),
    (server(), "Needs Review"),                                                  # plain HTTP: a proxy can't be ruled out, never Fail
])
def test_sec006_https(cfg, expected):
    assert status("SEC-006", facts(server_config=cfg)) == expected
    assert status("SEC-006", facts()) == "Needs Review"


@pytest.mark.parametrize("ext,expected", [("png,jpg,csv", "Pass"), ("ABSENT", "Fail"), ("  ", "Fail")])
def test_advsec007_wiki_upload_extensions(ext, expected):
    assert status("ADVSEC-007", facts(server_config=server(wiki_upload_extensions=ext))) == expected


@pytest.mark.parametrize("exports,expected", [
    ({"dku.exports.disableAllExports": "true"}, "Pass"),
    ({"dku.exports.disableAllDatasetExports": "TRUE", "dku.exports.disableCopySampleToClipboard": "false"}, "Pass"),   # one-of
    ({"dku.exports.disableCopySampleToClipboard": "false"}, "Fail"),
    ({}, "Fail"),
])
def test_advsec008_exports_any_one_key_true_passes(exports, expected):
    assert status("ADVSEC-008", facts(server_config=server(exports=exports))) == expected


def test_a_missing_dip_properties_file_means_nothing_is_set():
    cfg = server(dip_properties_present=False)
    assert status("ADVSEC-007", facts(server_config=cfg)) == "Fail" and status("ADVSEC-008", facts(server_config=cfg)) == "Fail"


@pytest.mark.parametrize("headers,expected", [
    (CORE, "Pass"),
    ({}, "Fail"),
    ({"permissions-policy": "geolocation=()"}, "Partial"),                         # set, but none of the core six
    ({k: v for k, v in CORE.items() if k != "hsts-max-age"}, "Partial"),          # one core header missing
    ({**CORE, "hsts-max-age": "0"}, "Partial"),                                    # HSTS off
    ({**CORE, "x-frame-options": "ALLOWALL"}, "Partial"),
    ({**CORE, "x-content-type-options": "sniff"}, "Partial"),
    ({**CORE, "x-xss-protection": "0"}, "Partial"),
    ({**CORE, "content-security-policy": " "}, "Partial"),
    ({**CORE, "x-frame-options": "deny"}, "Pass"),
])
def test_advsec009_six_core_headers(headers, expected):
    assert status("ADVSEC-009", facts(server_config=server(security_headers=headers))) == expected


def test_advsec009_extra_headers_are_notes_only():
    cfg = server(security_headers={**CORE, "permissions-policy": "x", "cross-origin-opener-policy": "same-origin"})
    assert status("ADVSEC-009", facts(server_config=cfg)) == "Pass"


@pytest.mark.parametrize("flag,prop,expected", [
    (True, "ABSENT", "Pass"), (False, "false", "Pass"), (False, "FALSE", "Pass"),   # either place counts
    (False, "ABSENT", "Fail"), (False, "true", "Fail"),
    ("ABSENT", "false", "Pass"), ("ABSENT", "ABSENT", "Needs Review"),
])
def test_advsec011_data_table_links_in_either_place(flag, prop, expected):
    doc = {**sec(disableDataTableLinks=flag)["facts"], **facts(server_config=server(data_table_links_enabled=prop))["facts"]}
    assert status("ADVSEC-011", {"facts": doc}) == expected


@pytest.mark.parametrize("scenario", sorted(p.stem for p in (FIXTURES / "expected").glob("*.yaml")))
def test_server_rules_agree_with_the_fixtures_expected_answers(scenario):
    proc = subprocess.run([sys.executable, "-B", str(FACTS_PY), str(FIXTURES / "bundles" / scenario)], capture_output=True, text=True, check=True)
    expected = yaml.safe_load((FIXTURES / "expected" / f"{scenario}.yaml").read_text())["items"]
    rows = [{"id": i, "title": verdicts.RULES[i][0]} for i in SERVER_RULES]
    got = {v["id"]: v["status"] for v in verdicts.compute(json.loads(proc.stdout), rows)["verdicts"]}
    assert set(got) == SERVER_RULES
    for check_id, status_ in got.items():
        if check_id in expected:
            assert status_ in expected[check_id]["status"], f"{scenario} {check_id}: verdict {status_}, expected {expected[check_id]['status']}"
