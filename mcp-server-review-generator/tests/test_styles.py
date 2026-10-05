"""Style registry: dispatch, validation, and that styles stay independent of each other."""

from pathlib import Path

import pytest

import styles


def request(**kw):
    return styles.BuildRequest(Path("c.xlsx"), "Acme", Path("o.pptx"), Path("base.pptx"), **kw)


def test_default_style_is_registered():
    assert styles.DEFAULT_STYLE in styles.STYLES


def test_unknown_style_names_the_valid_ones():
    with pytest.raises(ValueError, match=r"v1.*v2"):
        styles.get_style("v9")


def test_narrative_rejected_by_a_style_that_takes_none():
    with pytest.raises(ValueError, match="narrative"):
        styles.build("v1", request(narrative_path=Path("n.json")))


def test_build_dispatches_to_the_registered_style(monkeypatch):
    seen = {}
    spec = styles.StyleSpec("vx", "test", lambda req: seen.setdefault("req", req) and {"output_path": req.output_path, "warnings": []})
    monkeypatch.setitem(styles.STYLES, "vx", spec)
    out = styles.build("vx", request())
    assert out["output_path"] == Path("o.pptx") and seen["req"].customer == "Acme"


def test_regression_v2_does_not_depend_on_the_v1_builder():
    pytest.importorskip("pptx")
    import build_deck_v2
    assert not hasattr(build_deck_v2, "build_deck")


def test_every_style_has_manual_qa_text():
    import validate_deck
    for name in styles.STYLES:
        assert validate_deck.manual_qa_checklist(name).strip()
    assert validate_deck.manual_qa_checklist() == validate_deck.manual_qa_checklist(styles.DEFAULT_STYLE)


def test_unknown_style_has_no_qa_text():
    import validate_deck
    with pytest.raises(ValueError):
        validate_deck.manual_qa_checklist("v9")


def test_cli_style_choices_come_from_the_registry():
    import build_deck
    args = build_deck.parse_args(["--checklist", "c.xlsx", "--customer", "A"])
    assert args.style == styles.DEFAULT_STYLE
    with pytest.raises(SystemExit):
        build_deck.parse_args(["--checklist", "c.xlsx", "--customer", "A", "--style", "v9"])
