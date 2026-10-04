"""Pure analysis of a checklist for the v2 (verdict-first) deck: no PowerPoint
code here, so every rule is unit-testable.

Everything is derived from checklist cells only -- counts, root-cause groups,
quick wins, owner split, N/A groups. Nothing is invented: a figure the deck
shows on a main slide must trace to a row (see narrative.py for the same rule
applied to Claude-supplied text).
"""

import re
from dataclasses import dataclass, field


# Stacked-bar order (N/A excluded). Not the checklist column order: see build_deck.STATUS_ORDER.
STACK_ORDER = ["Pass", "Needs Review", "Partial", "Fail"]
NA = "Not Applicable"
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*-\d{3}\b")
NUMBER_RE = re.compile(r"\d[\d,.]*")
CONFIG_KV_RE = re.compile(r"\b([A-Za-z_][\w.]*[A-Za-z])\s*=\s*([^\s,;)]+)")
SET_VERB_RE = re.compile(r"^(set|hide|enable|disable|turn|restrict|remove|add)\b", re.I)
FLIP = {"true": "true", "false": "false"}


@dataclass
class Row:
    id: str
    title: str
    priority: str          # "Must" | "Nice"
    status: str            # canonical: Pass / Needs Review / Partial / Fail / Not Applicable
    headline: str
    evidence: list
    action: str
    section: str           # display name
    prefix: str            # ID prefix, e.g. SEC
    raw_text: str = ""     # notes + evidence_found, for number tracing


@dataclass
class QuickWin:
    id: str
    setting: str
    from_: str
    to: str
    confirm: str


@dataclass
class Analysis:
    rows: dict                      # id -> Row, in section order
    section_order: list             # [(display, prefix)]
    counts: dict
    total: int
    na: int
    applicable: int
    root_causes: list = field(default_factory=list)   # [[ids]] largest first
    quick_wins: list = field(default_factory=list)    # [QuickWin]
    remaining_fails: list = field(default_factory=list)
    owners: list = field(default_factory=list)        # [(owner, [ids])]
    na_groups: list = field(default_factory=list)     # [(heading, note, [ids])]
    warnings: list = field(default_factory=list)

    def by_status(self, status):
        return [r for r in self.rows.values() if r.status == status]

    def section_counts(self, display):
        out = {s: 0 for s in STACK_ORDER + [NA]}
        for r in self.rows.values():
            if r.section == display:
                out[r.status] += 1
        return out


def canonical_status(status):
    s = (status or "").strip().lower()
    for canon in STACK_ORDER + [NA]:
        if canon.lower() == s:
            return canon
    return None


def parse_notes(notes, evidence_found=""):
    """Notes are 3 lines: headline, '• evidence', '• Action: ...'. Falls back to
    the first sentence of evidence_found when notes are empty."""
    lines = [l.strip() for l in (notes or "").splitlines() if l.strip()]
    if not lines:
        ev = (evidence_found or "").strip()
        return (ev.split(". ")[0][:160], [], "")
    headline, evidence, action = lines[0], [], ""
    for l in lines[1:]:
        body = l.lstrip("•-* ").strip()
        if body.lower().startswith("action:"):
            action = body.split(":", 1)[1].strip()
        elif body:
            evidence.append(body)
    return headline, evidence, action


def build_rows(data, ordered_sections):
    rows = {}
    for sec in ordered_sections:
        for it in data.items_by_sheet.get(sec["sheet_tab_name"], []):
            status = canonical_status(it.validation_status)
            if status is None:
                continue
            headline, evidence, action = parse_notes(it.notes, it.evidence_found)
            rows[it.id] = Row(
                id=it.id, title=it.title, priority="Must" if it.is_must_have else "Nice", status=status,
                headline=headline, evidence=evidence, action=action[:1].upper() + action[1:],
                section=sec["display"], prefix=it.id.split("-")[0],
                raw_text=f"{it.notes}\n{it.evidence_found}",
            )
    return rows


def _action_cites(row):
    return set(ID_RE.findall(" ".join([row.action, row.headline] + row.evidence))) - {row.id}


def root_cause_groups(rows):
    """Group Fail/Partial rows that cite each other ('see SCALE-009') or share
    a distinctive number in their evidence. Heuristic: narrative.json is the
    authority; this feeds the fallback Risk 1 slide."""
    open_rows = [r for r in rows.values() if r.status in ("Fail", "Partial")]
    parent = {r.id: r.id for r in open_rows}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        if a in parent and b in parent:
            parent[find(a)] = find(b)

    for r in open_rows:
        for cited in _action_cites(r):
            union(r.id, cited)
    tokens = {}
    for r in open_rows:
        for ev in r.evidence:
            for m in re.finditer(r"(\d[\d,]*)\s+([A-Za-z][\w-]*(?:\s+[A-Za-z][\w-]*)?)", ev):
                if len(m.group(1)) >= 2:
                    tokens.setdefault(m.group(0).lower(), []).append(r.id)
    for ids in tokens.values():
        for other in ids[1:]:
            union(ids[0], other)
    groups = {}
    for r in open_rows:
        groups.setdefault(find(r.id), []).append(r.id)
    out = [g for g in groups.values() if len(g) > 1]
    out.sort(key=lambda g: (-len(g), g[0]))
    return out


def classify_quick_wins(rows, exclude=()):
    """Fail items that are one config setting: a `key=value` in the evidence and an
    Action that starts with a setting verb. `exclude` holds items that belong to a
    root-cause group (they are fixed in sequence, not in one change window)."""
    wins = []
    for r in rows.values():
        if r.status != "Fail" or r.id in exclude or not SET_VERB_RE.match(r.action or ""):
            continue
        m = next((CONFIG_KV_RE.search(t) for t in r.evidence + [r.headline] if CONFIG_KV_RE.search(t)), None)
        if not m:
            continue
        key, val = m.group(1), m.group(2)
        to = ("false" if val.lower() == "true" else "true") if val.lower() in FLIP else re.sub(r";.*", "", r.action)
        after = re.split(r"\bafter\b", r.action, maxsplit=1, flags=re.I)
        confirm = "None"
        if len(after) > 1:
            confirm = "Confirm " + re.sub(r"^(confirm(ing)?|that|with)\s+", "", after[1].strip(), flags=re.I)
        wins.append(QuickWin(r.id, key, val, to, confirm))
    return wins


def split_by_owner(rows, owner_keywords, id_prefix_owner=None):
    """Needs Review rows grouped by owner keywords found in the Action text. The
    first owner (in config order) with a matching keyword wins; id-prefix owner
    is the fallback, then 'Other'. Asserts nothing is lost."""
    id_prefix_owner = id_prefix_owner or {}
    nr = [r for r in rows.values() if r.status == "Needs Review"]
    groups = {}
    for r in nr:
        text = f"{r.action} {r.headline}".lower()
        owner = next((o for o, kws in owner_keywords.items() if any(k in text for k in kws)), None)
        owner = owner or id_prefix_owner.get(r.prefix) or "Other"
        groups.setdefault(owner, []).append(r.id)
    order = list(owner_keywords) + [o for o in groups if o not in owner_keywords]
    out = [(o, groups[o]) for o in order if o in groups]
    if sum(len(g[1]) for g in out) != len(nr):
        raise RuntimeError("owner grouping lost Needs Review items")
    return out


def group_na(rows):
    """N/A items grouped by section (the checklist carries no reason column);
    narrative.json can supply real reason groups."""
    out = []
    for display in dict.fromkeys(r.section for r in rows.values()):
        items = [r for r in rows.values() if r.section == display and r.status == NA]
        if items:
            note = items[0].headline or "Not relevant to this deployment."
            out.append((display, note, [r.id for r in items]))
    return out


def recommendation_warnings(data, rows):
    """The checklist's own Priority-Ordered Recommendations must cite items whose
    status supports a recommendation (the original-deck SEC-009 mistake)."""
    warnings = []
    for i, rec in enumerate(data.recommendations, start=1):
        for cid in expand_ids(rec):
            row = rows.get(cid)
            if row is None:
                warnings.append(f"Recommendation {i} cites {cid}, which isn't in any section sheet.")
            elif row.status in ("Pass", NA):
                warnings.append(f"Recommendation {i} cites {cid}, whose status is {row.status}, not a finding.")
    return warnings


def expand_ids(text):
    """IDs in text, expanding the 'SCALE-007/008' shorthand to SCALE-007 and SCALE-008."""
    ids = []
    for m in re.finditer(r"\b([A-Z][A-Z0-9]*)-(\d{3})((?:\s*[/,]\s*\d{3})*)", text or ""):
        ids.append(f"{m.group(1)}-{m.group(2)}")
        for extra in re.findall(r"\d{3}", m.group(3)):
            ids.append(f"{m.group(1)}-{extra}")
    return ids


def analyze(data, ordered_sections, v2_config=None):
    v2_config = v2_config or {}
    rows = build_rows(data, ordered_sections)
    counts = {s: 0 for s in STACK_ORDER + [NA]}
    for r in rows.values():
        counts[r.status] += 1
    total = len(rows)
    a = Analysis(
        rows=rows,
        section_order=[(s["display"], next((r.prefix for r in rows.values() if r.section == s["display"]), ""))
                       for s in ordered_sections],
        counts=counts, total=total, na=counts[NA], applicable=total - counts[NA],
    )
    if a.applicable <= 0:
        a.warnings.append("No applicable items: every checklist item is Not Applicable.")
    summary_na = (data.overall_counts or {}).get(NA)
    if summary_na not in (None, "") and int(summary_na) != counts[NA]:
        a.warnings.append(f"Overall Status Counts says {int(summary_na)} Not Applicable, but the section sheets "
                          f"hold {counts[NA]}; the deck uses {counts[NA]}.")
    a.root_causes = root_cause_groups(rows)
    a.quick_wins = classify_quick_wins(rows, exclude={i for g in a.root_causes for i in g})
    won = {q.id for q in a.quick_wins}
    a.remaining_fails = [r.id for r in rows.values() if r.status == "Fail" and r.id not in won]
    a.owners = split_by_owner(rows, v2_config.get("owner_keywords", {}), v2_config.get("owner_by_id_prefix", {}))
    a.na_groups = group_na(rows)
    a.warnings += recommendation_warnings(data, rows)
    return a
