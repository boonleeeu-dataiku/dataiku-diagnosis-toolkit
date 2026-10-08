"""Registry of deck styles. A style is one way to turn a checklist into a deck; the CLI
and the MCP server dispatch through STYLES instead of hardcoding style names.

Adding a style: write a module with a `build(request) -> dict` function (returning at
least `output_path` and `warnings`; any other keys are passed through to callers), add its
manual-QA text to validate_deck.py, then add one StyleSpec below. Style modules are imported lazily, so a style's own
dependencies (python-pptx for v2) are only needed when that style is used."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

DEFAULT_STYLE = "v2"


@dataclass(frozen=True)
class BuildRequest:
    """Everything any style can be asked to build with; a style ignores what it doesn't use."""
    checklist_path: Path
    customer: str
    output_path: Path
    base_deck: Path | None
    logo_path: Path | None = None
    narrative_path: Path | None = None
    rows_per_slide: int = 4
    include_pass_items: bool = False
    standard_deck: bool = False  # build without the branding template (v2 only; see build_deck_v2.build_standard_base)


@dataclass(frozen=True)
class StyleSpec:
    name: str
    description: str
    build: Callable[[BuildRequest], dict]
    accepts_narrative: bool = False
    qa_checklist: Callable[[], str] = lambda: ""  # manual visual-QA guidance shown after a clean build


def _qa_v1() -> str:
    import validate_deck
    return validate_deck.MANUAL_QA_CHECKLIST_V1


def _qa_v2() -> str:
    import validate_deck
    return validate_deck.MANUAL_QA_CHECKLIST_V2


def _build_v1(req: BuildRequest) -> dict:
    import build_deck
    import data_checks
    if req.standard_deck:
        raise ValueError("style 'v1' has no standard (unbranded) deck: it edits the branding template's own slides. "
                         "Use style 'v2', or supply the branding template via base_deck_path.")
    warnings: list = []
    output = build_deck.build_deck(
        checklist_path=req.checklist_path, customer=req.customer, output_path=req.output_path,
        base_deck=req.base_deck, logo_path=req.logo_path, rows_per_slide=req.rows_per_slide,
        include_pass_items=req.include_pass_items, warnings_out=warnings,
    )
    return {"output_path": output, "warnings": warnings}


def _build_v2(req: BuildRequest) -> dict:
    import build_deck_v2
    return build_deck_v2.build_v2(
        req.checklist_path, req.customer, req.output_path, req.base_deck, req.logo_path, req.narrative_path,
        standard_deck=req.standard_deck,
    )


STYLES = {
    spec.name: spec for spec in (
        StyleSpec("v1", "one slide per few items (older section-by-section layout)", _build_v1, qa_checklist=_qa_v1),
        StyleSpec("v2", "verdict-first ~20-slide storyline (needs python-pptx)", _build_v2, accepts_narrative=True,
                  qa_checklist=_qa_v2),
    )
}


def get_style(name: str) -> StyleSpec:
    if name not in STYLES:
        raise ValueError(f"style must be one of {sorted(STYLES)}, got {name!r}")
    return STYLES[name]


def build(name: str, request: BuildRequest) -> dict:
    """Build a deck in the named style; raises ValueError for an unknown style, or for a
    narrative given to a style that doesn't take one."""
    spec = get_style(name)
    if request.narrative_path is not None and not spec.accepts_narrative:
        raise ValueError(f"a narrative only applies to styles that accept one, not {name!r}")
    return spec.build(request)
