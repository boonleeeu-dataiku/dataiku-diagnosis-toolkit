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


# --- the instance's `security` settings block (Batch 3a) ------------------------------------------------------------
#
# Policy (calibrations.md, Security): a secure toggle that is on is Pass; one that is off is Fail, except where the
# checklist itself allows a deliberate choice (ADVSEC-005, 010, 012, SEC-007), which is Needs Review (ask for the
# documented need). A setting missing from the bundle is Needs Review.

def _security(facts):
    block = fact(facts, "security_settings")
    return block if isinstance(block, dict) else None


def _toggle(facts, key, *, want, off_status, label):
    """Pass when `key` equals `want`; otherwise `off_status`; Needs Review when the setting is missing."""
    sec = _security(facts)
    if sec is None:
        return _missing("security settings")
    value = sec.get(key, ABSENT)
    if not isinstance(value, bool):
        return _missing(f"{key}")
    if value is want:
        return verdict("Pass", f"{label}: {key}={str(value).lower()}", **{key: value})
    reason = f"{label}: {key}={str(value).lower()}"
    if off_status == "Needs Review":
        reason += " (ask whether intentional)"
    return verdict(off_status, reason, **{key: value})


@rule("ADVSEC-001", "Hiding error stacks")
def hide_error_stacks(facts):
    return _toggle(facts, "hideErrorStacks", want=True, off_status="Fail", label="error stacks are hidden")


@rule("ADVSEC-002", "Hiding version info")
def hide_version_info(facts):
    return _toggle(facts, "hideVersionStringsWhenNotLogged", want=True, off_status="Fail", label="version info is hidden before login")


@rule("ADVSEC-003", "Expiring sessions")
def expiring_sessions(facts):
    sec = _security(facts)
    if sec is None:
        return _missing("security settings")
    total, idle = sec.get("sessionsMaxTotalTimeMinutes", ABSENT), sec.get("sessionsMaxIdleTimeMinutes", ABSENT)
    values = {"sessionsMaxTotalTimeMinutes": total, "sessionsMaxIdleTimeMinutes": idle}
    nums = [v for v in (total, idle) if isinstance(v, int) and not isinstance(v, bool)]
    if any(v > 0 for v in nums):
        return verdict("Pass", "a session timeout is set (0 means unlimited)", **values)
    if len(nums) == 2:
        return verdict("Fail", "both session timeouts are 0 (unlimited)", **values)
    return _missing("the session timeout settings")


@rule("ADVSEC-004", "Forcing a single session per user")
def single_session(facts):
    return _toggle(facts, "forceSingleSessionPerUser", want=True, off_status="Fail", label="one session per user is forced")


@rule("ADVSEC-005", "Restricting visibility of groups and users")
def restrict_visibility(facts):
    return _toggle(facts, "restrictUsersAndGroupsVisibility", want=True, off_status="Needs Review",
                   label="users and groups are hidden from other users")


@rule("ADVSEC-006", "Redirecting to a custom URL after logout")
def post_logout_redirect(facts):
    sec = _security(facts)
    if sec is None:
        return _missing("security settings")
    behavior, scheme = sec.get("postLogoutBehavior", ABSENT), sec.get("postLogoutCustomURL_scheme", ABSENT)
    values = {"postLogoutBehavior": behavior, "postLogoutCustomURL_scheme": scheme}
    if behavior in ("CUSTOM_URL", "CUSTOM_URL_POST"):
        if scheme in ("http", "https"):
            return verdict("Pass", f"a custom logout redirect is configured ({scheme} URL)", **values)
        return verdict("Fail", "a custom logout redirect is configured but its URL is not http or https", **values)
    return verdict("Not Applicable", "no custom logout redirect; the default logged-out page is used", **values)


@rule("ADVSEC-010", "Allowing DSS to be hosted inside an iframe")
def iframe_hosting(facts):
    sec = _security(facts)
    if sec is None:
        return _missing("security settings")
    same_site, secure = sec.get("sameSiteNoneCookies", ABSENT), sec.get("secureCookies", ABSENT)
    values = {"sameSiteNoneCookies": same_site, "secureCookies": secure}
    if not isinstance(same_site, bool):
        return _missing("sameSiteNoneCookies")
    if same_site is False:
        return verdict("Pass", "iframe hosting is not enabled (sameSiteNoneCookies=false)", **values)
    if secure is False:
        return verdict("Fail", "iframe hosting is enabled without secure cookies", **values)
    return verdict("Needs Review", "iframe hosting is enabled (ask for the documented need)", **values)


@rule("ADVSEC-012", "Allowing DSS users to edit their display names and emails")
def users_edit_profile(facts):
    return _toggle(facts, "enableEmailAndDisplayNameModification", want=False, off_status="Needs Review",
                   label="users cannot edit their display name and email")


@rule("SEC-007", "Secure Cookies Enabled (security.secureCookies)")
def secure_cookies(facts):
    return _toggle(facts, "secureCookies", want=True, off_status="Needs Review", label="cookies are marked secure")
