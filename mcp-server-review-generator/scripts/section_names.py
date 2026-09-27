"""Section-name normalization: map a checklist sheet's (possibly
Excel-truncated) tab name to a curated display name + sort order, with a
generic fallback so an unseen checklist still works without a config edit.
"""

import logging
import re

logger = logging.getLogger(__name__)


def _normalize_key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def normalize_section_name(sheet_tab_name: str, config: dict) -> dict:
    """Return {"display": str, "order": int, "key": str} for a sheet tab
    name. Looks up a curated entry in config["sections"]; falls back to a
    title-cased version of the raw tab name (with a low, stable order so
    unconfigured sections sort after configured ones) and logs a warning.
    """
    key = _normalize_key(sheet_tab_name)
    sections = config.get("sections", {})
    if key in sections:
        entry = sections[key]
        return {"display": entry["display"], "order": entry["order"], "key": key}

    logger.warning(
        "No curated display name for checklist section %r (normalized key %r); "
        "falling back to a title-cased name. Add an entry to "
        "config/section_names.yaml to curate this.",
        sheet_tab_name,
        key,
    )
    return {"display": sheet_tab_name.strip().title(), "order": 1000, "key": key}


def order_sections(sheet_tab_names: list[str], config: dict) -> list[dict]:
    """Return normalized section dicts for every sheet, sorted by
    (configured order, then original sheet order) -- unconfigured sections
    keep their sheet order among themselves rather than being shuffled."""
    normalized = [
        {**normalize_section_name(name, config), "sheet_tab_name": name, "_seq": i}
        for i, name in enumerate(sheet_tab_names)
    ]
    normalized.sort(key=lambda s: (s["order"], s["_seq"]))
    return normalized


def find_narrative_block(header_text: str, alias_key: str, config: dict) -> bool:
    """True if header_text (a Summary-sheet section header cell's value)
    matches one of the case-insensitive substring aliases configured for
    alias_key (e.g. 'critical_findings')."""
    aliases = config.get("narrative_block_aliases", {}).get(alias_key, [])
    haystack = header_text.strip().lower()
    return any(alias in haystack for alias in aliases)
