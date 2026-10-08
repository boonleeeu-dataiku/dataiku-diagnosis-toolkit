"""The Spark/Kubernetes verdict rules (scripts/rules_k8s.py): edge cases on hand-built facts and agreement with the fixtures'
expected answers."""
import json
import subprocess
import sys

import pytest
import yaml

from conftest import FIXTURES, REPO_ROOT

SCRIPTS = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "scripts"
FACTS_PY = REPO_ROOT / "skills" / "dataiku-diagnosis-reader" / "scripts" / "facts.py"
sys.path.insert(0, str(SCRIPTS))
import rules_k8s  # noqa: E402,F401
import verdicts  # noqa: E402

RULED = {"ARCH-005", "ARCH-006", "ARCH-007", "ARCH-008", "ARCH-010", "ARCH-011", "ARCH-013", "ARCH-014", "ARCH-015", "ARCH-016", "ARCH-017"}
LIVE_ONLY = {"ARCH-008", "ARCH-014", "ARCH-015"}
K8S_ONLY = RULED - {"ARCH-005", "ARCH-006"}


def status(check_id, k):
    doc = {"facts": {"kubernetes": {"value": k, "source": "test"}}}
    out = verdicts.compute(doc, [{"id": check_id, "title": verdicts.RULES[check_id][0]}])["verdicts"]
    return out[0]["status"] if out else "undecided"


def cont(name="standard", mem=8192, req=2048, cpu=2, ns="templated", kind="KUBERNETES"):
    return {"name": name, "type": kind, "mem_request_mb": req, "mem_limit_mb": mem, "cpu_request": 1, "cpu_limit": cpu, "namespace": ns}


def spark(name="s", mem="4g", managed=False, ns="fixed", resources=True, instances="ABSENT"):
    return {"name": name, "resources_set": resources, "executor_instances": instances, "executor_memory": mem, "executor_cores": "ABSENT",
            "driver_memory": "ABSENT", "managed_kubernetes": managed, "namespace": ns, "authentication_mode": "BUILTIN"}


def kube(attached=True, **over):
    base = {"cluster_attached": attached, "cluster_files": [{"type": "managed", "architecture": "KUBERNETES"}] if attached else [],
            "default_cluster_set": attached, "implicit_cluster": False, "container_configs": [cont("a"), cont("b", 16384, 4096, 4)],
            "default_execution_config": "a", "default_visual_recipes_config_set": True, "containerized_visual_recipes_enabled": True,
            "spark_enabled": True, "spark_configs": [spark("s1"), spark("s2", "12g")]}
    return {**base, **over}


def test_the_k8s_rules_are_registered():
    assert RULED <= set(verdicts.RULES)


@pytest.mark.parametrize("check_id", sorted(K8S_ONLY))
def test_every_kubernetes_check_is_not_applicable_without_a_cluster(check_id):
    assert status(check_id, kube(attached=False, container_configs=[], spark_configs=[])) == "Not Applicable"


@pytest.mark.parametrize("check_id", sorted(K8S_ONLY))
def test_kubernetes_configs_without_an_attached_cluster_are_still_not_applicable(check_id):
    assert status(check_id, kube(attached=False)) == "Not Applicable"


@pytest.mark.parametrize("check_id", sorted(RULED))
def test_a_missing_fact_is_needs_review(check_id):
    doc = {"facts": {}}
    assert verdicts.compute(doc, [{"id": check_id, "title": verdicts.RULES[check_id][0]}])["verdicts"][0]["status"] == "Needs Review"


@pytest.mark.parametrize("check_id", sorted(LIVE_ONLY))
@pytest.mark.parametrize("over,expected", [
    ({}, "Needs Review"),                                              # a bundle can't show a live run, topology or capacity
    ({"spark_enabled": False}, "Needs Review"),                        # cluster attached: Spark use doesn't change it
    ({"cluster_attached": False}, "Not Applicable"),
    ({"cluster_attached": "ABSENT"}, "Needs Review"),
])
def test_live_only_cluster_checks(check_id, over, expected):
    assert status(check_id, kube(**over)) == expected


@pytest.mark.parametrize("over,expected", [
    ({}, "Pass"),
    ({"spark_enabled": False}, "Not Applicable"),
    ({"spark_enabled": "ABSENT"}, "Needs Review"),
    ({"spark_configs": []}, "Fail"),
    ({"spark_configs": [spark(resources=False)]}, "Fail"),
    ({"spark_configs": [spark(resources=False), spark("t")]}, "Pass"),
])
def test_arch005_valid_spark_config(over, expected):
    assert status("ARCH-005", kube(**over)) == expected


@pytest.mark.parametrize("over,expected", [
    ({}, "Pass"),
    ({"spark_enabled": False}, "Not Applicable"),
    ({"spark_enabled": "ABSENT", "spark_configs": []}, "Fail"),
    ({"spark_configs": []}, "Fail"),
    ({"spark_configs": [spark()]}, "Needs Review"),
    ({"spark_configs": [spark("a"), spark("b")]}, "Needs Review"),            # same sizing under different names
    ({"spark_configs": [spark("a"), spark("b", instances="12")]}, "Pass"),
])
def test_arch006_spark_baseline(over, expected):
    assert status("ARCH-006", kube(**over)) == expected


@pytest.mark.parametrize("over,expected", [
    ({}, "Pass"),
    ({"container_configs": [cont(ns="fixed")]}, "Needs Review"),
    ({"container_configs": [cont(ns="fixed")], "cluster_files": [{"type": "manual", "architecture": "KUBERNETES"}]}, "Needs Review"),
    ({"container_configs": [cont(ns="templated")], "cluster_files": [{"type": "manual", "architecture": "KUBERNETES"}]}, "Pass"),
    ({"container_configs": [cont(ns="ABSENT")]}, "Needs Review"),
    ({"container_configs": [], "spark_configs": [spark(managed=True, ns="templated")]}, "Pass"),
    ({"container_configs": [], "spark_configs": [spark(managed=True, ns="templated")], "cluster_attached": False}, "Not Applicable"),
    ({"container_configs": [], "spark_configs": [spark(managed=False, ns="fixed")]}, "Needs Review"),   # YARN Spark doesn't count
    ({"container_configs": [cont(kind="DOCKER", ns="fixed")]}, "Needs Review"),
])
def test_arch007_per_user_namespaces(over, expected):
    assert status("ARCH-007", kube(**over)) == expected


@pytest.mark.parametrize("configs,expected", [
    ([cont()], "Pass"),
    ([], "Fail"),
    ([cont(mem=-1)], "Needs Review"),
    ([cont(kind="DOCKER")], "Fail"),
])
def test_arch010_valid_container_config(configs, expected):
    assert status("ARCH-010", kube(container_configs=configs)) == expected


@pytest.mark.parametrize("configs,expected", [
    ([cont("a"), cont("b", 500, 500, 1)], "Pass"),
    ([cont("a"), cont("b")], "Needs Review"),
    ([cont("a")], "Needs Review"),
    ([], "Fail"),
])
def test_arch011_container_baseline(configs, expected):
    assert status("ARCH-011", kube(container_configs=configs)) == expected


@pytest.mark.parametrize("files,expected", [
    ([{"type": "manual", "architecture": "KUBERNETES"}], "Pass"),
    ([], "Needs Review"),
    ([{"type": "manual", "architecture": "OTHER"}], "Needs Review"),
])
def test_arch013_valid_cluster(files, expected):
    assert status("ARCH-013", kube(cluster_files=files)) == expected


@pytest.mark.parametrize("over,expected", [
    ({}, "Pass"),
    ({"default_execution_config": "ABSENT"}, "Pass"),                 # the default execution config no longer matters
    ({"container_configs": [cont("a", mem=-1)]}, "Pass"),
    ({"default_cluster_set": False}, "Fail"),                         # cluster attached, no default cluster
    ({"default_cluster_set": "ABSENT"}, "Needs Review"),
    ({"cluster_attached": False, "default_cluster_set": False}, "Not Applicable"),   # even with Kubernetes configs defined
    ({"cluster_attached": "ABSENT"}, "Needs Review"),
])
def test_arch016_global_defaults(over, expected):
    assert status("ARCH-016", kube(**over)) == expected


@pytest.mark.parametrize("over,expected", [
    ({}, "Pass"),
    ({"containerized_visual_recipes_enabled": False}, "Needs Review"),
    ({"containerized_visual_recipes_enabled": "ABSENT"}, "Needs Review"),
    ({"default_visual_recipes_config_set": False}, "Needs Review"),
])
def test_arch017_containerized_visual_recipes(over, expected):
    assert status("ARCH-017", kube(**over)) == expected


@pytest.mark.parametrize("scenario", sorted(p.stem for p in (FIXTURES / "expected").glob("*.yaml")))
def test_k8s_rules_agree_with_the_fixtures_expected_answers(scenario):
    proc = subprocess.run([sys.executable, "-B", str(FACTS_PY), str(FIXTURES / "bundles" / scenario)], capture_output=True, text=True, check=True)
    expected = yaml.safe_load((FIXTURES / "expected" / f"{scenario}.yaml").read_text())["items"]
    rows = [{"id": i, "title": verdicts.RULES[i][0]} for i in sorted(RULED)]
    got = {v["id"]: v["status"] for v in verdicts.compute(json.loads(proc.stdout), rows)["verdicts"]}
    assert set(got) == RULED
    for check_id, status_ in got.items():
        if check_id in expected:
            assert status_ in expected[check_id]["status"], f"{scenario} {check_id}: verdict {status_}, expected {expected[check_id]['status']}"
