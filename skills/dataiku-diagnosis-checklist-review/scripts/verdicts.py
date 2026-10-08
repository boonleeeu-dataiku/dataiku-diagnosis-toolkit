#!/usr/bin/env python3
"""Deterministic verdicts: the status of every check that the reader's facts can decide, computed by code.

Judgment only. Where a setting lives or how to read it belongs to the reader (`dataiku-diagnosis-reader`); a rule
here only says which status a given fact value earns. A rule never touches the bundle: it reads the parsed
`facts.py` output and returns one verdict.

A rule is registered with `@rule(id, anchor)` and takes the facts mapping (`{name: {"value": ..., "source": ...}}`).
`anchor` is the title the check had when the rule was written. A checklist row gets the verdict only when its id
matches AND its title matches the anchor (case, punctuation and spacing ignored), so a renumbered or reworded
checklist falls back to the model instead of being forced to a wrong status. Rows that match on id but not on
title, and titles that match under another id, are reported, never silently applied.

A rule may return None for a case the facts cannot settle (for example evidence that lives in log text). The row then
gets no verdict, is listed under `undecided`, and the model decides it as usual.

Code is final: `run_step.py verify` fails when a ruled row's workbook status differs from its verdict.

This module is stdlib only and has no I/O; `run_step.py` reads the facts and the checklist and calls `compute`.
"""
from __future__ import annotations

import re
from typing import Any, Callable

STATUSES = ("Pass", "Fail", "Partial", "Needs Review", "Not Applicable")
ABSENT = "ABSENT"

Facts = dict[str, dict[str, Any]]
Rule = Callable[[Facts], "dict[str, Any] | None"]

# check id -> (anchor title, rule function). Rules are added here batch by batch (see TODO.md).
RULES: dict[str, tuple[str, Rule]] = {}


def rule(check_id: str, anchor: str) -> Callable[[Rule], Rule]:
    """Register a rule for `check_id`, valid for rows titled `anchor`."""
    def register(fn: Rule) -> Rule:
        if check_id in RULES:
            raise ValueError(f"duplicate rule for {check_id}")
        RULES[check_id] = (anchor, fn)
        return fn
    return register


def fact(facts: Facts, name: str) -> Any:
    """The `value` of a fact, or the string "ABSENT" when the fact is missing or the reader reported it absent."""
    entry = facts.get(name)
    return entry.get("value", ABSENT) if isinstance(entry, dict) else ABSENT


def verdict(status: str, reason: str, **deciding_values: Any) -> dict[str, Any]:
    """What a rule returns: a status from STATUSES, a one-line reason, and the values that decided it."""
    return {"status": status, "reason": reason, "deciding_values": deciding_values}


def _missing(what: str) -> dict[str, Any]:
    """Needs Review for a fact the bundle does not hold."""
    return verdict("Needs Review", f"{what} missing from the bundle")


def norm(title: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (title or "").lower())).strip()


def _checked(check_id: str, result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status") not in STATUSES:
        raise ValueError(f"{check_id}: rule returned status {result.get('status')!r}, not one of {STATUSES}")
    if not isinstance(result.get("reason"), str) or not result["reason"].strip() or "\n" in result["reason"]:
        raise ValueError(f"{check_id}: rule must return a one-line reason")
    if not isinstance(result.get("deciding_values"), dict):
        raise ValueError(f"{check_id}: deciding_values must be a dict")
    return result


def compute(facts_doc: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Verdicts for the checklist `rows` (dicts with at least `id` and `title`) from a parsed facts.py document."""
    facts: Facts = facts_doc.get("facts", {})
    anchors = {norm(anchor): check_id for check_id, (anchor, _) in RULES.items()}
    verdicts, title_mismatch, probable_renumber, undecided = [], [], [], []
    for row in rows:
        check_id, title = row.get("id"), row.get("title")
        if check_id in RULES:
            anchor, fn = RULES[check_id]
            if norm(title) == norm(anchor):
                result = fn(facts)
                if result is None:
                    undecided.append({"id": check_id, "title": title})
                    continue
                result = _checked(check_id, result)
                verdicts.append({"id": check_id, "title": title, **{k: result[k] for k in ("status", "deciding_values", "reason")}})
            else:
                title_mismatch.append({"id": check_id, "row_title": title, "rule_title": anchor})
        elif norm(title) in anchors:
            probable_renumber.append({"row_id": check_id, "title": title, "rule_id": anchors[norm(title)]})
    return {
        "verdicts": sorted(verdicts, key=lambda v: v["id"]),
        "undecided": undecided,
        "title_mismatch": title_mismatch,
        "probable_renumber": probable_renumber,
        "rows": len(rows),
        "rules": len(RULES),
    }


def status_problems(verdicts_doc: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    """One problem per ruled row whose workbook status differs from its verdict (code is final)."""
    status_by_id = {r.get("id"): r.get("validation_status") for r in rows}
    problems = []
    for v in verdicts_doc["verdicts"]:
        if v["id"] not in status_by_id:
            problems.append(f"{v['id']}: has a verdict ({v['status']}) but is not in the workbook")
        elif status_by_id[v["id"]] != v["status"]:
            problems.append(f"{v['id']}: workbook {status_by_id[v['id']] or 'blank'}, verdict {v['status']} ({v['reason']})")
    return problems
