"""Optional narrative.json for the v2 deck: the human-judgment text (verdict,
takeaways, risk slides, roadmap...) that rules can't derive. It is an *input*,
so the same inputs always give the same deck, and it can never add findings:
every cited ID must exist and its status must support the claim, and every
figure on a risk tile must appear in the cited row's own notes/evidence.

Any missing key falls back to rule-derived content in build_deck_v2.py.
"""

import json
import re
from pathlib import Path

from deck_analysis import ID_RE, NA, NUMBER_RE, Analysis

WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve"]
EFFORTS = {"S", "M", "L"}
TONES = {"good", "risk", "win"}
STATES = {"ok", "watch", "neutral"}


class NarrativeError(ValueError):
    """The narrative file is malformed or contradicts the checklist."""


def default_path(checklist_path) -> Path:
    """Where a build looks when no narrative is given: beside the checklist,
    named <checklist_stem>_narrative.json."""
    p = Path(checklist_path)
    return p.with_name(f"{p.stem}_narrative.json")


def staleness_warnings(narr: dict, checklist_sha256: str) -> list:
    """The narrative may record the checklist's sha256 (`checklist_sha256`). If the
    checklist changed since, the prose may be stale: warn, don't fail."""
    recorded = narr.get("checklist_sha256")
    if recorded and recorded.lower() != checklist_sha256.lower():
        return ["The narrative was written for a different version of this checklist (checklist_sha256 "
                "differs); re-read it and update the prose before sending the deck."]
    return []


def load(path) -> dict:
    p = Path(path)
    if not p.exists():
        raise NarrativeError(f"Narrative file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise NarrativeError(f"Narrative file {p} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise NarrativeError("Narrative file must contain a JSON object at the top level.")
    return data


def _ids(value, where):
    if isinstance(value, str):
        value = ID_RE.findall(value)
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise NarrativeError(f"{where}: ids must be a list of strings.")
    return value


def _traces(num, text):
    """True if a figure appears in the text, as digits or spelled out (four = 4)."""
    low = (text or "").lower()
    if num.lower() in low or _numbers(num) <= _numbers(text):
        return True
    return num.isdigit() and int(num) < len(WORDS) and re.search(rf"\b{WORDS[int(num)]}\b", low) is not None


def _numbers(text):
    return {n.strip(".,") for n in NUMBER_RE.findall(text or "")}


def validate(narr: dict, a: Analysis):
    """Raise NarrativeError on contradictions; return a list of soft warnings."""
    warnings = []
    caveats = set(_ids(narr.get("caveats", []), "caveats"))
    for cid in caveats:
        if cid not in a.rows or a.rows[cid].status != "Pass":
            raise NarrativeError(f"caveats: {cid} must be a Pass item (a 'Pass, with caveat').")

    def check_cited(cid, where, allowed=("Fail", "Partial", "Needs Review")):
        row = a.rows.get(cid)
        if row is None:
            raise NarrativeError(f"{where}: {cid} is not in any checklist section sheet.")
        if row.status in allowed or (row.status == "Pass" and cid in caveats):
            return row
        raise NarrativeError(
            f"{where}: {cid} has status {row.status!r}, which doesn't support citing it as a problem "
            f"(allowed: {', '.join(allowed)}; list a Pass item under 'caveats' if it is a Pass with a known issue)."
        )

    def check_rows(key, fields, allowed=("Fail", "Partial", "Needs Review")):
        out = narr.get(key)
        for i, entry in enumerate(out or [], start=1):
            for f in fields:
                for cid in _ids(entry.get(f, []), f"{key}[{i}].{f}"):
                    check_cited(cid, f"{key}[{i}]", allowed)
        return out

    r1 = narr.get("risk1") or {}
    for i, t in enumerate(r1.get("tiles", []), start=1):
        cid = t.get("id")
        row = check_cited(cid, f"risk1.tiles[{i}]") if cid else None
        num = str(t.get("number", ""))
        if row and not _traces(num, row.raw_text):
            raise NarrativeError(
                f"risk1.tiles[{i}]: figure {num!r} does not appear in {cid}'s notes or evidence "
                f"(figures on main slides must trace to a checklist cell)."
            )
    for i, s in enumerate(r1.get("fix", []), start=1):
        for cid in _ids(s.get("id", []), f"risk1.fix[{i}]"):
            check_cited(cid, f"risk1.fix[{i}]")
    for i, e in enumerate((narr.get("risk2") or {}).get("table", []), start=1):
        check_cited(e.get("id"), f"risk2.table[{i}]", ("Fail", "Partial"))
    for i, c in enumerate((narr.get("risk3") or {}).get("cards", []), start=1):
        for cid in _ids(c.get("ids", []), f"risk3.cards[{i}]"):
            check_cited(cid, f"risk3.cards[{i}]")
    for i, q in enumerate((narr.get("quick_wins") or {}).get("rows", []), start=1):
        check_cited(q.get("id"), f"quick_wins.rows[{i}]", ("Fail",))

    groups = (narr.get("owners") or {}).get("groups")
    if groups is not None:
        seen = []
        for g in groups:
            for ask in g.get("asks", []):
                row = check_cited(ask.get("id"), f"owners[{g.get('owner')}]", ("Needs Review",))
                seen.append(row.id)
        nr = {r.id for r in a.by_status("Needs Review")}
        if len(seen) != len(set(seen)) or set(seen) != nr:
            missing, extra = sorted(nr - set(seen)), sorted(set(seen) - nr)
            raise NarrativeError(
                f"owners: grouped items ({len(seen)}) must equal the Needs Review total ({len(nr)}), each once. "
                f"Missing: {missing}; unexpected/duplicate: {extra}."
            )

    road = narr.get("roadmap") or {}
    for col in ("now", "next", "plan"):
        for i, e in enumerate(road.get(col, []), start=1):
            if str(e.get("effort", "")).upper() not in EFFORTS:
                raise NarrativeError(f"roadmap.{col}[{i}]: effort must be S, M or L.")
            for cid in _ids(e.get("ids", []), f"roadmap.{col}[{i}]"):
                check_cited(cid, f"roadmap.{col}[{i}]")

    na_groups = narr.get("na_groups")
    if na_groups is not None:
        seen = [cid for g in na_groups for cid in _ids(g.get("ids", []), "na_groups")]
        na_ids = {r.id for r in a.by_status(NA)}
        if len(seen) != len(set(seen)) or set(seen) != na_ids:
            raise NarrativeError(
                f"na_groups: must list every Not Applicable item exactly once "
                f"(missing {sorted(na_ids - set(seen))}, unexpected {sorted(set(seen) - na_ids)})."
            )

    for i, t in enumerate(narr.get("takeaways", [])):
        if t.get("tone", "good") not in TONES:
            raise NarrativeError(f"takeaways[{i + 1}].tone must be one of {sorted(TONES)}.")
    if len(narr.get("takeaways", [])) not in (0, 3):
        raise NarrativeError("takeaways: provide exactly 3 (sound / at risk / quick wins) or none.")
    for i, c in enumerate(narr.get("snapshot", []), start=1):
        if c.get("state", "neutral") not in STATES:
            raise NarrativeError(f"snapshot[{i}].state must be one of {sorted(STATES)}.")
    if len(narr.get("snapshot", [])) > 8:
        raise NarrativeError("snapshot: at most 8 cards.")

    # soft check: numbers in free text should exist somewhere in the checklist
    known = _numbers(" ".join(r.raw_text + r.title for r in a.rows.values()))
    known |= {str(v) for v in (*a.counts.values(), a.total, a.applicable)}
    for key in ("verdict_title", "highlights"):
        for n in _numbers(narr.get(key, "")) - known:
            warnings.append(f"narrative {key}: figure {n!r} isn't found in any checklist cell; check it.")
    for i, t in enumerate(narr.get("takeaways", []), start=1):
        for n in _numbers(t.get("body", "")) - known:
            warnings.append(f"narrative takeaways[{i}]: figure {n!r} isn't found in any checklist cell; check it.")
    return warnings
