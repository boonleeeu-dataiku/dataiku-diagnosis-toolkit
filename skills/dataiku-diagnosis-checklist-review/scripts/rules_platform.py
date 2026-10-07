"""Verdict rules for the platform, sizing and runtime checks (judgment only; see verdicts.py for the contract).

Each rule's text is the human-readable spec in `references/calibrations.md`. A fact that is missing from the bundle is
Needs Review, never an assumed Fail, except where the calibration says otherwise (SCALE-006)."""
from __future__ import annotations

from verdicts import ABSENT, fact, rule, verdict


def _missing(what: str):
    return verdict("Needs Review", f"{what} missing from the bundle")


def _tier_target_gib(ram_gib: float) -> float:
    """The checklist's recommended cgroup memory cap for a host with `ram_gib` of RAM."""
    if ram_gib > 120:
        return 0.75 * ram_gib
    if ram_gib >= 60:
        return 0.66 * ram_gib
    if ram_gib >= 30:
        return ram_gib - 20
    return 0.5 * ram_gib


@rule("SEC-004", "CGroups Enabled with Memory Limit per Sizing Heuristic")
def cgroups_memory_limit(facts):
    cg, host = fact(facts, "cgroups"), fact(facts, "host_memory")
    if not isinstance(cg, dict):
        return _missing("cgroup settings")
    enabled = cg.get("enabled", ABSENT)
    if enabled is False:
        return verdict("Fail", "cgroups are disabled", enabled=False)
    if enabled is not True:
        return _missing("the cgroups enabled flag")
    pcts = [lim["pct_of_MemTotal"] for lim in (cg.get("limits") if isinstance(cg.get("limits"), list) else [])
            if isinstance(lim, dict) and lim.get("pct_of_MemTotal") is not None]
    if not pcts:
        return verdict("Needs Review", "cgroups enabled but no memory limit set (ask whether intentional)", enabled=True)
    ram = host.get("GiB") if isinstance(host, dict) else None
    if not isinstance(ram, (int, float)) or ram <= 0:
        return _missing("host memory")
    pct = max(pcts)  # the overall memory cap if several are listed
    cap = pct / 100 * ram
    values = {"limit_pct_of_ram": pct, "ram_gib": ram, "limit_gib": round(cap, 1)}
    if pct >= 80:
        return verdict("Needs Review", f"limit is {pct}% of {ram} GiB: over-allocates memory to cgroups", **values)
    target = _tier_target_gib(ram)
    values["tier_target_gib"] = round(target, 1)
    if abs(cap - target) <= 0.10 * target:
        return verdict("Pass", f"limit {cap:.0f} GiB = {pct}% of {ram} GiB; within 10% of tier target {target:.0f} GiB", **values)
    return verdict("Needs Review", f"limit {cap:.0f} GiB = {pct}% of {ram} GiB; more than 10% from tier target {target:.0f} GiB", **values)


@rule("SCALE-001", "External PostgreSQL Runtime Database")
def external_postgresql(facts):
    db = fact(facts, "internal_database")
    if not isinstance(db, dict):
        return _missing("internal database settings")
    kind, loopback = db.get("type", ABSENT), db.get("host_is_loopback", ABSENT)
    values = {"type": kind, "host_is_loopback": loopback}
    if kind == ABSENT:
        return _missing("the internal database type")
    if str(kind).lower() != "postgresql":
        return verdict("Fail", f"internal database is {kind}, not PostgreSQL", **values)
    if loopback is True:
        return verdict("Pass", "PostgreSQL runtime database, locally installed on the DSS host (loopback)", **values)
    if loopback is False:
        return verdict("Pass", "PostgreSQL runtime database on a non-local host", **values)
    return _missing("the database host")


@rule("SCALE-006", "Usage of Instance Sanity Check")
def sanity_check_used(facts):
    sc = fact(facts, "sanity_check")
    if not isinstance(sc, dict):
        return verdict("Fail", "no sanity-check output in the bundle", present=False)
    if sc.get("empty") is True:
        return verdict("Fail", "sanity-check output is empty", present=True, messages=0)
    return verdict("Pass", f"sanity-check output present with {sc.get('messages')} message(s)", present=True, messages=sc.get("messages"))


_LIMITS = ("maxRunningJobs", "maxRunningActivities", "maxRunningActivitiesPerJob")


@rule("SCALE-009", "Flow Limits Sizing (Max Jobs, Max Activities)")
def flow_limits(facts):
    cl = fact(facts, "concurrency_limits")
    if not isinstance(cl, dict):
        return _missing("concurrency limits")
    values = {}
    for name in _LIMITS:
        found = cl.get(name)
        if not isinstance(found, list) or not found:
            return _missing(f"{name}")
        raw = found[0].get("value")  # first location listed; a limit in an unexpected place still counts
        values[name] = 0 if raw in (None, "") else raw  # blank means unsized, like 0
    if not all(isinstance(v, (int, float)) for v in values.values()):
        return _missing("numeric concurrency limits")
    zero = [n for n, v in values.items() if v == 0]
    if zero:
        return verdict("Fail", f"{', '.join(zero)} is 0 (unsized)", **values)
    if 30 <= values["maxRunningActivities"] <= 50 and values["maxRunningActivitiesPerJob"] == 5:
        return verdict("Pass", "limits set; activities within 30-50, per-job at 5", **values)
    return verdict("Needs Review", "limits set but outside the recommended ranges (ask whether justified)", **values)


@rule("SCALE-011", "Remove filesystem_root Connection")
def filesystem_root_removed(facts):
    conns = fact(facts, "connections")
    present = conns.get("filesystem_root_present", ABSENT) if isinstance(conns, dict) else ABSENT
    if present is True:
        return verdict("Fail", "filesystem_root connection still present", filesystem_root_present=True)
    if present is False:
        return verdict("Pass", "no filesystem_root connection", filesystem_root_present=False)
    return _missing("the connections list")


@rule("ARCH-004", "SSD Storage for DSS")
def ssd_storage(facts):
    vol, sanity = fact(facts, "data_volume_device"), fact(facts, "sanity_check")
    sanity_has_messages = isinstance(sanity, dict) and sanity.get("empty") is False
    if isinstance(vol, dict) and isinstance(vol.get("all_non_rotational"), bool):
        if vol["all_non_rotational"] is False:
            return verdict("Fail", "a disk behind the data directory is rotational", all_non_rotational=False)
        if sanity_has_messages:
            return None  # DSS's own sanity check may flag a rotational disk; its text isn't in the facts
        return verdict("Pass", "all disks behind the data directory are non-rotational", all_non_rotational=True)
    if sanity_has_messages:
        return None  # disks unknown, but the sanity-check text may settle it
    return verdict("Needs Review", "the data directory's disks cannot be determined from the bundle")
