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
    assert facts["config_folder_size"]["value"] == "ABSENT"
    assert facts["trace_explorer"]["value"] == "ABSENT"
    assert facts["sso_and_ldap"]["value"]["ssoSettings.enabled"] == "ABSENT"


def test_absent_marker_is_not_masked_by_secret_key_redaction(tmp_path):
    """A missing key whose name looks secret-ish ("authenticationEnabled") must still read ABSENT."""
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLES / "synthetic_design_baseline", bundle)
    settings = next(bundle.rglob("general-settings.json"))
    doc = json.loads(settings.read_text())
    doc.pop("ldapSettings")
    settings.write_text(json.dumps(doc))
    proc = subprocess.run([sys.executable, "-B", str(FACTS), str(bundle)], capture_output=True, text=True, check=True)
    assert json.loads(proc.stdout)["facts"]["sso_and_ldap"]["value"]["ldapSettings.authenticationEnabled"] == "ABSENT"


def test_cgroup_limit_is_reported_as_a_percentage_of_host_memory():
    cg = run_facts("synthetic_design_k8s_remote")["cgroups"]["value"]
    assert cg["enabled"] is True
    limit = cg["limits"][0]
    assert limit["value"] == "42G" and limit["pct_of_MemTotal"] == pytest.approx(67.2, abs=0.2)


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


def _facts_for(bundle_dir):
    proc = subprocess.run([sys.executable, "-B", str(FACTS), str(bundle_dir)], capture_output=True, text=True, check=True)
    return proc.stdout, json.loads(proc.stdout)["facts"]


def test_data_volume_device_follows_the_data_dir_to_its_disk_rota():
    vol = run_facts("synthetic_design_k8s_remote")["data_volume_device"]["value"]
    assert vol["mount_point"] == "/data/dataiku"
    assert vol["backing_disks"] == [{"disk": "sda", "rota": 0}] and vol["all_non_rotational"] is True
    assert run_facts("synthetic_design_baseline")["data_volume_device"]["value"] == "ABSENT"


def test_data_volume_device_reports_a_rotational_disk(tmp_path):
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLES / "synthetic_design_k8s_remote", bundle)
    diag = bundle / "diag.txt"
    diag.write_text(diag.read_text().replace("512    0 ", "512    1 "))
    _, facts = _facts_for(bundle)
    vol = facts["data_volume_device"]["value"]
    assert vol["backing_disks"] == [{"disk": "sda", "rota": 1}] and vol["all_non_rotational"] is False


def test_admin_cleanup_scenarios_summarise_type_activity_and_triggers_without_reading_scripts():
    healthy = run_facts("synthetic_design_k8s_remote")["admin_cleanup_scenarios"]["value"]["candidate_projects"]
    assert healthy["ADMINPROJECT"][0]["type"] == "step_based" and healthy["ADMINPROJECT"][0]["active"] is True
    assert healthy["ADMINPROJECT"][0]["triggers"] == [{"type": "temporal", "active": True}]
    py = run_facts("synthetic_design_admin_python")["admin_cleanup_scenarios"]["value"]["candidate_projects"]
    assert [s["file"] for s in py["ADMINISTRATIONPROJECT"]] == ["NIGHTLY_TASKS.json"]  # the .py is never listed or read
    assert py["ADMINISTRATIONPROJECT"][0]["type"] == "custom_python"


def test_deployer_reports_target_host_and_never_the_api_key(tmp_path):
    key = "Zk9-deployer-API-key-value"
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLES / "synthetic_design_k8s_remote", bundle)
    settings = next(bundle.rglob("general-settings.json"))
    doc = json.loads(settings.read_text())
    doc["deployerClientSettings"]["apiKey"] = key
    doc["deployerClientSettings"]["nodeUrl"] = "https://user:pw@deployer.synthetic.example:11200/x"
    settings.write_text(json.dumps(doc))
    out, facts = _facts_for(bundle)
    dep = facts["deployer"]["value"]
    assert dep["mode"] == "REMOTE" and dep["target_host"] == "deployer.synthetic.example:11200"
    assert dep["api_key_configured"] is True
    assert key not in out and "user:pw" not in out


def test_ldap_authorized_groups_are_counted_not_named():
    assert run_facts("synthetic_design_baseline")["sso_and_ldap"]["value"]["ldapSettings.authorizedGroups_count"] == 0
    stdout, facts = _facts_for(BUNDLES / "synthetic_design_k8s_remote")
    assert facts["sso_and_ldap"]["value"]["ldapSettings.authorizedGroups_count"] == 2
    assert "dss-users" not in stdout


def test_missing_install_id_is_absent():
    assert run_facts("synthetic_design_admin_python")["node"]["value"]["installid"] == "ABSENT"
    assert run_facts("synthetic_design_baseline")["node"]["value"]["installid"] == "SYNTHETICINSTALL01"


def test_sanity_check_reports_presence_and_counts_or_absent():
    assert run_facts("synthetic_design_baseline")["sanity_check"]["value"]["present"] is True
    assert run_facts("synthetic_design_baseline")["sanity_check"]["value"]["empty"] is False
    assert run_facts("synthetic_design_k8s_remote")["sanity_check"]["value"]["empty"] is True  # {"messages": []}
    assert run_facts("synthetic_design_admin_python")["sanity_check"]["value"] == "ABSENT"


def test_byo_llm_is_active_only_when_a_main_llm_or_reference_project_is_set():
    assert run_facts("synthetic_design_baseline")["byo_llm"]["value"] == "ABSENT"  # no localAIServerSettings block
    on = run_facts("synthetic_design_k8s_remote")["byo_llm"]["value"]
    assert on["active"] is True and on["referenceProjectKey_set"] is True and on["mainLLMId"].endswith("gpt-5.2")
    partial = run_facts("synthetic_design_admin_python")["byo_llm"]["value"]
    assert partial["active"] is True and partial["referenceProjectKey_set"] is False
