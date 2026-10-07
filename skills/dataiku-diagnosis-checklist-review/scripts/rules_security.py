"""Verdict rules for the security checks (judgment only; see verdicts.py for the contract).

Each rule's text is the human-readable spec in `references/calibrations.md`, which stays authoritative on intent. A fact
that is missing from the bundle is Needs Review, never an assumed Fail: the bundle may simply not carry the setting."""
from __future__ import annotations

from verdicts import ABSENT, fact, rule, verdict


def _missing(what: str):
    return verdict("Needs Review", f"{what} missing from the bundle")


@rule("SEC-001", "Verify/Capture Instance IDs")
def instance_id(facts):
    node = fact(facts, "node")
    if not isinstance(node, dict):
        return _missing("node information")
    installid = node.get("installid", ABSENT)
    if installid == ABSENT:
        return verdict("Fail", "no instance (install) id in the bundle", installid=ABSENT)
    return verdict("Pass", f"instance id present ({installid})", installid=installid)


@rule("SEC-002", "User Isolation Framework (UIF) Enabled with Appropriate Impersonation Rules")
def user_isolation(facts):
    uif = fact(facts, "user_isolation")
    if not isinstance(uif, dict):
        return _missing("impersonation settings")
    enabled, rules = uif.get("enabled", ABSENT), (uif.get("user_rules") or 0) + (uif.get("group_rules") or 0)
    values = {"enabled": enabled, "rules": rules}
    if enabled is False:
        return verdict("Fail", "UIF is disabled", **values)
    if enabled is not True:
        return _missing("the UIF enabled flag")
    if rules >= 1:
        return verdict("Pass", f"UIF enabled with {rules} impersonation rule(s)", **values)
    return verdict("Partial", "UIF enabled but no user or group rules", **values)


def _sso_ldap(facts):
    block = fact(facts, "sso_and_ldap")
    return block if isinstance(block, dict) else None


@rule("SEC-009", "LDAP Authorized Groups Configured")
def ldap_authorized_groups(facts):
    block = _sso_ldap(facts)
    if block is None:
        return _missing("LDAP settings")
    ldap, count = block.get("ldapSettings.enabled", ABSENT), block.get("ldapSettings.authorizedGroups_count", ABSENT)
    values = {"ldap_enabled": ldap, "authorized_groups": count}
    if ldap is False:
        return verdict("Not Applicable", "LDAP is not enabled", **values)
    if ldap is not True or not isinstance(count, int):
        return _missing("the LDAP enabled flag or authorized-group count")
    if count >= 1:
        return verdict("Pass", f"LDAP enabled with {count} authorized group(s)", **values)
    return verdict("Fail", "LDAP enabled with no authorized groups", **values)


@rule("SEC-010", "SSO Enablement Reviewed")
def sso_enabled(facts):
    block = _sso_ldap(facts)
    if block is None:
        return _missing("SSO and LDAP settings")
    sso, ldap = block.get("ssoSettings.enabled", ABSENT), block.get("ldapSettings.enabled", ABSENT)
    values = {"sso_enabled": sso, "ldap_enabled": ldap, "sso_protocol": block.get("ssoSettings.protocol", ABSENT)}
    if sso is False:
        return verdict("Fail", "SSO is disabled", **values)
    if sso is True and ldap is True:
        return verdict("Pass", "SSO and LDAP both enabled", **values)
    if sso is True and ldap is False:
        return verdict("Needs Review", "SSO enabled but LDAP disabled", **values)
    return _missing("the SSO or LDAP enabled flag")


@rule("SEC-005", "JEK-Specific CGroup Limits Left Unconfigured")
def jek_cgroup_unconfigured(facts):
    cg = fact(facts, "cgroups")
    counts = cg.get("target_counts") if isinstance(cg, dict) else None
    if not isinstance(counts, dict):
        return _missing("cgroup settings")
    jek = counts.get("jobExecutionKernels")  # absent key = no JEK category configured at all
    if jek:
        return verdict("Fail", f"{jek} JEK-specific cgroup target(s) configured", jek_targets=jek)
    return verdict("Pass", "no JEK-specific cgroup target", jek_targets=jek if jek is not None else 0)
