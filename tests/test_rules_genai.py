"""The GenAI verdict rules (scripts/rules_genai.py): edge cases on hand-built facts and agreement with the fixtures'
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
import rules_genai  # noqa: E402,F401
import verdicts  # noqa: E402

RULED = {"GENAI-001", "GENAI-003", "GENAI-004", "GENAI-005", "GENAI-006", "GENAI-007", "GENAI-008", "GENAI-009"}


def facts(**blocks):
    return {"facts": {name: {"value": value, "source": "test"} for name, value in blocks.items()}}


def status(check_id, doc):
    out = verdicts.compute(doc, [{"id": check_id, "title": verdicts.RULES[check_id][0]}])["verdicts"]
    return out[0]["status"] if out else "undecided"


def gen(**over):
    base = {"generativeAISettings_present": True, "retrieval_code_env": "ABSENT", "pii_detection_code_env": "ABSENT",
            "ai_services_terms_accepted": "ABSENT", "ai_services_enabled": {}, "cobuild_default_llms_set": "ABSENT"}
    return {**base, **over}


def byo(main="ABSENT", ref=False, **over):
    return {"active": main != "ABSENT" or ref, "mainLLMId": main, "referenceProjectKey_set": ref,
            "responseFormatAwareLLMId": "ABSENT", "fastLightLLMId": "ABSENT", **over}


def test_the_genai_rules_are_registered():
    assert RULED <= set(verdicts.RULES)


@pytest.mark.parametrize("retrieval,pii,expected", [
    ("INTERNAL_retrieval_augmented_generation_v1", "INTERNAL_pii_detection_v1", "Pass"),
    ("INTERNAL_retrieval_augmented_generation_v1", "ABSENT", "Pass"),
    ("ABSENT", "INTERNAL_pii_detection_v1", "Pass"),
    ("custom_rag_env", "INTERNAL_pii_detection_v1", "Needs Review"),
    ("INTERNAL_retrieval_augmented_generation_v1", "my_pii_env", "Needs Review"),
    ("ABSENT", "ABSENT", "Fail"),
])
def test_genai001_internal_code_envs(retrieval, pii, expected):
    assert status("GENAI-001", facts(genai_settings=gen(retrieval_code_env=retrieval, pii_detection_code_env=pii))) == expected


@pytest.mark.parametrize("doc", [{}, facts(genai_settings="ABSENT"), facts(genai_settings=gen(generativeAISettings_present=False))])
def test_genai001_missing_settings_is_needs_review(doc):
    assert status("GENAI-001", doc) == "Needs Review"


@pytest.mark.parametrize("trace,expected", [
    ({"configured": True, "fields": {}}, "Pass"),
    ({"configured": False, "fields": {"a": ""}}, "Fail"),
    ({"configured": False, "llmTraceSettings": {}}, "Fail"),
    ("ABSENT", "Needs Review"),
])
def test_genai003_trace_explorer(trace, expected):
    assert status("GENAI-003", facts(trace_explorer=trace)) == expected


@pytest.mark.parametrize("accepted,flags,expected", [
    (True, {"enabled": True}, "Pass"),
    (True, {"aiGenerateSQLEnabled": True, "enabled": "ABSENT"}, "Pass"),
    (True, {"enabled": False}, "Needs Review"),
    (False, {"enabled": True}, "Needs Review"),
    (False, {}, "Needs Review"),
    ("ABSENT", {}, "Needs Review"),
])
def test_genai004_ai_services(accepted, flags, expected):
    assert status("GENAI-004", facts(genai_settings=gen(ai_services_terms_accepted=accepted, ai_services_enabled=flags))) == expected


def test_genai004_missing_fact_is_needs_review():
    assert status("GENAI-004", {}) == "Needs Review"


@pytest.mark.parametrize("block,expected", [
    ("ABSENT", "Not Applicable"),
    (byo(), "Not Applicable"),
    (byo("openai:c:gpt-5.2", True), "Pass"),
    (byo("openai:c:gpt-5.2", False), "Fail"),
    (byo("ABSENT", True), "Fail"),
])
def test_genai005_reference_project_and_main_model(block, expected):
    assert status("GENAI-005", facts(byo_llm=block)) == expected


@pytest.mark.parametrize("ids,expected", [
    ("openai:c:gpt-5.2", "Pass"),
    ("openai:c:gpt-5.5", "Pass"),
    ("openai:c:gpt-6", "Pass"),
    ("openai:c:gpt-5.1", "Fail"),
    ("openai:c:gpt-4o", "Fail"),
    ("openai:c:gpt-5", "Fail"),
    ("custom:c:llama-3", "Needs Review"),
])
def test_genai006_model_versions(ids, expected):
    assert status("GENAI-006", facts(byo_llm=byo(ids, True))) == expected


def test_genai006_any_old_id_fails_even_when_the_main_is_current():
    assert status("GENAI-006", facts(byo_llm=byo("openai:c:gpt-5.2", True, fastLightLLMId="openai:c:gpt-5.1"))) == "Fail"


def test_genai006_unknown_id_downgrades_a_pass_to_needs_review():
    assert status("GENAI-006", facts(byo_llm=byo("openai:c:gpt-5.2", True, fastLightLLMId="custom:c:small"))) == "Needs Review"


@pytest.mark.parametrize("block", ["ABSENT", byo()])
def test_genai006_inactive_is_not_applicable(block):
    assert status("GENAI-006", facts(byo_llm=block)) == "Not Applicable"


@pytest.mark.parametrize("cobuild,expected", [
    ("ABSENT", "Needs Review"),
    ({"defaultEmbeddingLLMId": True, "defaultLLMId": True, "defaultImageGenerationLLMId": True}, "Pass"),
    ({"defaultEmbeddingLLMId": True, "defaultLLMId": False, "defaultImageGenerationLLMId": True}, "Needs Review"),
    ({"defaultEmbeddingLLMId": False, "defaultLLMId": False, "defaultImageGenerationLLMId": False}, "Needs Review"),
])
def test_genai007_cobuild_defaults(cobuild, expected):
    assert status("GENAI-007", facts(genai_settings=gen(cobuild_default_llms_set=cobuild))) == expected


@pytest.mark.parametrize("plugins,expected", [
    ({"agent_hub_installed": True}, "Needs Review"),
    ({"agent_hub_installed": False}, "Not Applicable"),
    ("ABSENT", "Not Applicable"),
])
def test_genai009_agent_hub_is_never_pass_or_fail(plugins, expected):
    assert status("GENAI-009", facts(plugins=plugins)) == expected


@pytest.mark.parametrize("scenario", sorted(p.stem for p in (FIXTURES / "expected").glob("*.yaml")))
def test_genai_rules_agree_with_the_fixtures_expected_answers(scenario):
    proc = subprocess.run([sys.executable, "-B", str(FACTS_PY), str(FIXTURES / "bundles" / scenario)], capture_output=True, text=True, check=True)
    expected = yaml.safe_load((FIXTURES / "expected" / f"{scenario}.yaml").read_text())["items"]
    rows = [{"id": i, "title": verdicts.RULES[i][0]} for i in sorted(RULED)]
    got = {v["id"]: v["status"] for v in verdicts.compute(json.loads(proc.stdout), rows)["verdicts"]}
    assert set(got) == RULED
    for check_id, status_ in got.items():
        if check_id in expected:
            assert status_ in expected[check_id]["status"], f"{scenario} {check_id}: verdict {status_}, expected {expected[check_id]['status']}"


@pytest.mark.parametrize("version,fragment", [("14.4.3", "older than 14.7"), ("14.7.0", "option was selected"), ("15.0.1", "option was selected"),
                                              ("ABSENT", "can't be read")])
def test_genai008_is_always_needs_review_with_a_version_reason(version, fragment):
    doc = facts(node={"nodetype": "design", "product_version": version})
    out = verdicts.compute(doc, [{"id": "GENAI-008", "title": verdicts.RULES["GENAI-008"][0]}])["verdicts"][0]
    assert out["status"] == "Needs Review" and fragment in out["reason"]


def test_genai008_without_the_node_fact_is_needs_review():
    assert status("GENAI-008", facts()) == "Needs Review"
