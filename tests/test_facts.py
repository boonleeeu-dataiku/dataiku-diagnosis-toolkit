"""The reader's facts.py reports key settings deterministically and never leaks secrets.

Runs it on the synthetic fixture bundles only (never a real bundle). A value mis-stated or
missed by hand is what made repeat reviews disagree, so these pin the contract: explicit
ABSENT, leaf-key search finds a limit under jekSettings, loopback detection, no secret values."""

import json
import shutil
import subprocess
import sys

import pytest

from conftest import FIXTURES, REPO_ROOT

FACTS = REPO_ROOT / "skills" / "dataiku-diagnosis-reader" / "scripts" / "facts.py"
BUNDLES = FIXTURES / "bundles"


def run_facts(bundle):
    proc = subprocess.run([sys.executable, "-B", str(FACTS), str(BUNDLES / bundle)],
                          capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["facts"]


def test_loopback_database_and_limit_under_jek_settings():
    facts = run_facts("synthetic_design_baseline")
    db = facts["internal_database"]["value"]
    assert db["type"] == "PostgreSQL" and db["host"] == "127.0.0.1" and db["host_is_loopback"] is True
    jobs = facts["concurrency_limits"]["value"]["maxRunningJobs"]
    assert jobs == [{"path": "jekSettings.maxRunningJobs", "value": 0}]


def test_remote_database_is_not_loopback_and_agent_hub_is_detected():
    facts = run_facts("synthetic_design_k8s_remote")
    assert facts["internal_database"]["value"]["host_is_loopback"] is False
    assert facts["plugins"]["value"]["agent_hub_installed"] is True
    assert facts["connections"]["value"]["filesystem_root_present"] is False


def test_missing_settings_are_explicit_absent_never_false_or_zero():
    facts = run_facts("synthetic_design_baseline")
    assert facts["host_memory"]["value"] == "ABSENT"
    assert facts["trace_explorer"]["value"] == "ABSENT"
    sso = facts["sso_and_ldap"]["value"]
    # Not masked by the secret-key redaction either, even for a key name containing "auth".
    assert sso["ssoSettings.enabled"] == "ABSENT"
    assert sso["ldapSettings.authenticationEnabled"] == "ABSENT"


@pytest.mark.parametrize("bundle", sorted(p.name for p in BUNDLES.iterdir() if p.is_dir()))
def test_no_fact_errors(bundle):
    facts = run_facts(bundle)
    assert all(f["value"] != "ERROR" for f in facts.values()), facts


def test_plaintext_database_password_is_flagged_but_never_printed(tmp_path):
    secret = "Sup3r-S3cret-Value"
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLES / "synthetic_design_baseline", bundle)
    settings = next(bundle.rglob("general-settings.json"))
    doc = json.loads(settings.read_text())
    doc["internalDatabase"]["connection"].setdefault("params", {})["password"] = secret
    settings.write_text(json.dumps(doc))
    proc = subprocess.run([sys.executable, "-B", str(FACTS), str(bundle)], capture_output=True, text=True, check=True)
    assert secret not in proc.stdout
    assert json.loads(proc.stdout)["facts"]["internal_database"]["value"]["password_stored_in_plaintext"] is True
