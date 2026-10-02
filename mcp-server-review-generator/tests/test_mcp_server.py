"""mcp_server.py's error surfacing and path resolution. The exact error
messages matter: the dataiku-review-deck-builder skill relays them verbatim
(and keys its "Base deck not found" handling off that wording)."""

import pytest

pytest.importorskip("mcp", reason="mcp SDK not installed (only needed by scripts/mcp_server.py)")

import common  # noqa: E402
from conftest import item  # noqa: E402
import mcp_server  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402


def test_relative_paths_resolve_against_repo_root():
    assert mcp_server._resolve("resources/x.xlsx") == (common.REPO_ROOT / "resources/x.xlsx").resolve()


def test_absolute_paths_are_kept(tmp_path):
    assert mcp_server._resolve(str(tmp_path)) == tmp_path


def test_missing_checklist_surfaces_as_tool_error(tmp_path):
    with pytest.raises(ToolError, match="Checklist file not found"):
        mcp_server.build_platform_review_deck(checklist_path=str(tmp_path / "nope.xlsx"), customer="Acme")


def test_missing_base_deck_surfaces_as_tool_error(checklist_factory, tmp_path):
    with pytest.raises(ToolError, match="Base deck not found"):
        mcp_server.build_platform_review_deck(
            checklist_path=str(checklist_factory()), customer="Acme",
            base_deck_path=str(tmp_path / "missing.pptx"),
        )


def test_missing_logo_surfaces_as_tool_error(checklist_factory, tmp_path):
    base = tmp_path / "base.pptx"
    base.write_bytes(b"")
    with pytest.raises(ToolError, match="Logo file not found"):
        mcp_server.build_platform_review_deck(
            checklist_path=str(checklist_factory()), customer="Acme",
            base_deck_path=str(base), logo_path=str(tmp_path / "logo.png"),
        )


def test_validate_deck_rejects_non_zip(tmp_path):
    bogus = tmp_path / "deck.pptx"
    bogus.write_text("not a zip")
    with pytest.raises(ToolError, match="not a valid .pptx"):
        mcp_server.validate_deck_tool(pptx_path=str(bogus))


def test_validate_deck_missing_file(tmp_path):
    with pytest.raises(ToolError, match="File not found"):
        mcp_server.validate_deck_tool(pptx_path=str(tmp_path / "nope.pptx"))


def test_analyze_checklist_returns_scaffold(checklist_factory):
    path = checklist_factory({"Architecture, Compute & Infrast": [item("ARCH-001", "Fail"), item("ARCH-002", "Not Applicable")]})
    res = mcp_server.analyze_checklist(checklist_path=str(path))
    assert res["counts"]["Fail"] == 1 and len(res["checklist_sha256"]) == 64
    assert [r["id"] for r in res["not_applicable"]] == ["ARCH-002"]


def test_analyze_checklist_missing_file_surfaces_as_tool_error(tmp_path):
    with pytest.raises(ToolError, match="Checklist file not found"):
        mcp_server.analyze_checklist(checklist_path=str(tmp_path / "nope.xlsx"))
