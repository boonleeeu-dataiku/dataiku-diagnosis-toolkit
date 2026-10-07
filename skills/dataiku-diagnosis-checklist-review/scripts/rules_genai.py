"""Verdict rules for the GenAI checks (judgment only; see verdicts.py for the contract).

Each rule's text is the human-readable spec in `references/calibrations.md`. A fact or section that is missing from the
bundle is Needs Review, never an assumed Fail or Not Applicable, except where the calibration says otherwise."""
from __future__ import annotations

import re

from verdicts import ABSENT, fact, rule, verdict

INTERNAL_PREFIX = "INTERNAL_"
MIN_BYO_VERSION = (5, 2)


def _missing(what: str):
    return verdict("Needs Review", f"{what} missing from the bundle")


@rule("GENAI-001", "Internal Code Environments for RAG, Document Extraction, PII Detection")
def internal_code_envs(facts):
    g = fact(facts, "genai_settings")
    if not isinstance(g, dict) or g.get("generativeAISettings_present") is not True:
        return _missing("GenAI settings")
    envs = {k: g.get(k, ABSENT) for k in ("retrieval_code_env", "pii_detection_code_env")}
    set_envs = [v for v in envs.values() if v != ABSENT]
    external = [v for v in set_envs if not str(v).startswith(INTERNAL_PREFIX)]
    if external:
        return verdict("Needs Review", f"non-internal default code env in use: {', '.join(external)}", **envs)
    if set_envs:
        return verdict("Pass", f"default code envs are internal: {', '.join(set_envs)}", **envs)
    return verdict("Fail", "no default code env is set for retrieval or PII detection", **envs)


@rule("GENAI-003", "Trace Explorer Default Configuration")
def trace_explorer_default(facts):
    t = fact(facts, "trace_explorer")
    if not isinstance(t, dict):
        return _missing("Trace Explorer settings")
    if t.get("configured") is True:
        return verdict("Pass", "Trace Explorer default project and web app are set", configured=True)
    return verdict("Fail", "Trace Explorer default project and web app are not set", configured=False)


@rule("GENAI-004", "AI Services Terms of Use Acceptance & Enablement")
def ai_services(facts):
    g = fact(facts, "genai_settings")
    if not isinstance(g, dict):
        return _missing("AI Services settings")
    accepted = g.get("ai_services_terms_accepted", ABSENT)
    flags = g.get("ai_services_enabled") if isinstance(g.get("ai_services_enabled"), dict) else {}
    enabled = [k for k, v in flags.items() if v is True]
    values = {"terms_accepted": accepted, "features_enabled": enabled}
    if accepted is True and enabled:
        return verdict("Pass", f"terms accepted and AI Services enabled ({len(enabled)} flag(s))", **values)
    if accepted is True:
        return verdict("Needs Review", "terms accepted but AI Services not enabled (ask whether intentional)", **values)
    if accepted is False:
        return verdict("Needs Review", "AI Services terms not accepted (ask whether intentional)", **values)
    return _missing("the AI Services terms flag")


@rule("GENAI-005", "Bring Your Own LLM Mode - Reference Project & Main Model")
def byo_reference_and_model(facts):
    b = fact(facts, "byo_llm")
    if not isinstance(b, dict) or b.get("active") is not True:
        return verdict("Not Applicable", "Bring Your Own LLM mode is not active")
    ref, main = b.get("referenceProjectKey_set") is True, b.get("mainLLMId", ABSENT) != ABSENT
    values = {"referenceProjectKey_set": ref, "main_llm_set": main}
    if ref and main:
        return verdict("Pass", "reference project key and main LLM are both set", **values)
    missing = " and ".join(n for n, ok in (("reference project key", ref), ("main LLM", main)) if not ok)
    return verdict("Fail", f"Bring Your Own LLM is active but the {missing} is not set", **values)


def _openai_version(llm_id: str):
    m = re.search(r"gpt-(\d+)(?:\.(\d+))?", llm_id.lower())
    return (int(m.group(1)), int(m.group(2) or 0)) if m else None


@rule("GENAI-006", "Bring Your Own LLM - Recommended Model Versions")
def byo_model_versions(facts):
    b = fact(facts, "byo_llm")
    if not isinstance(b, dict) or b.get("active") is not True:
        return verdict("Not Applicable", "Bring Your Own LLM mode is not active")
    ids = {k: b.get(k, ABSENT) for k in ("mainLLMId", "responseFormatAwareLLMId", "fastLightLLMId")}
    versions = {k: _openai_version(v) for k, v in ids.items() if v != ABSENT}
    if not versions:
        return _missing("the LLM ids")
    old = [k for k, v in versions.items() if v is not None and v < MIN_BYO_VERSION]
    unknown = [k for k, v in versions.items() if v is None]
    if old:
        return verdict("Fail", f"unsupported model version (older than ChatGPT 5.2): {', '.join(ids[k] for k in old)}", **ids)
    if unknown:
        return verdict("Needs Review", f"model version can't be determined: {', '.join(ids[k] for k in unknown)}", **ids)
    return verdict("Pass", "all LLM ids are ChatGPT 5.2 or later", **ids)


@rule("GENAI-007", "Cobuild Default LLM Configuration")
def cobuild_defaults(facts):
    g = fact(facts, "genai_settings")
    cobuild = g.get("cobuild_default_llms_set", ABSENT) if isinstance(g, dict) else ABSENT
    if not isinstance(cobuild, dict):
        return _missing("the Cobuild default LLM settings")
    unset = sorted(k for k, v in cobuild.items() if v is not True)
    if not unset:
        return verdict("Pass", "all three Cobuild default LLMs are set", unset=[])
    return verdict("Needs Review", f"Cobuild default LLM(s) not set: {', '.join(unset)} (ask whether Cobuild is in use)", unset=unset)


@rule("GENAI-009", "Agent Hub Deployment Required Permissions")
def agent_hub_permissions(facts):
    p = fact(facts, "plugins")
    if not isinstance(p, dict):  # no plugin configuration directory in the bundle: nothing installed (the fixtures' policy)
        return verdict("Not Applicable", "no plugins installed, so Agent Hub is not installed", agent_hub_installed=False)
    if p["agent_hub_installed"]:
        return verdict("Needs Review", "Agent Hub is installed; who may deploy it can't be verified from the bundle", agent_hub_installed=True)
    return verdict("Not Applicable", "Agent Hub is not installed", agent_hub_installed=False)
