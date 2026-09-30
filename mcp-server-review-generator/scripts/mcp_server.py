#!/usr/bin/env python3
"""MCP (Model Context Protocol) stdio server exposing this repo's two CLI
entry points -- build_deck.py and validate_deck.py -- as tools for MCP
clients (Claude Desktop, Claude Code, other MCP-capable LLM tools).

Built against the mcp>=2.0 SDK's MCPServer (the renamed successor to 1.x's
FastMCP -- same decorator-based API, see mcp's own v2 migration guide).

Launch directly, e.g. from an MCP client config:
    python3 <repo>/scripts/mcp_server.py

This is a thin wrapper: it resolves the same defaults build_deck.py's own
main() resolves (config/deck_layout.yaml fallbacks, default_output_path()),
then calls build_deck.build_deck() / validate_deck.validate() unchanged.
"""

import functools
import logging
import sys
import zipfile
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import common
import build_deck
import validate_deck as validate_deck_lib

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

# Keep stdout reserved for the MCP JSON-RPC channel; progress logs go to stderr,
# which MCP clients typically surface as server logs.
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stderr)

mcp = MCPServer("dataiku-review-generator", version=common.VERSION)


def _resolve(p: str) -> Path:
    """Resolve a path against the repo root, not this server process's CWD
    (an MCP client config doesn't reliably control the launched process's
    working directory)."""
    path = Path(p)
    return path if path.is_absolute() else (common.REPO_ROOT / path).resolve()


def _surface_errors(fn):
    """mcp.server.mcpserver treats any raised exception other than ToolError as an
    unanticipated crash and hides its message from the caller (the client only sees
    "Error executing tool <name>"). This repo's errors (missing files, a checklist
    failing schema validation, ...) are deliberately clear, fail-fast messages meant
    to be read by whoever's driving the tool -- re-raise them as ToolError so that
    message actually reaches the calling LLM."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(str(e)) from e
    return wrapper


@mcp.tool()
@_surface_errors
def build_platform_review_deck(
    checklist_path: str,
    customer: str,
    logo_path: str | None = None,
    output_path: str | None = None,
    rows_per_slide: int | None = None,
    include_pass_items: bool | None = None,
    base_deck_path: str | None = None,
) -> dict[str, Any]:
    """Generate a branded Dataiku Platform Review .pptx deck from a completed
    checklist workbook, writing it to disk and returning its path.

    Mirrors `python3 scripts/build_deck.py`. Runs the same structural
    validation automatically afterward (see the validate_deck tool) and
    reports any problems found, rather than requiring a separate call.

    Args:
        checklist_path: Path to a completed checklist .xlsx (required).
            A relative path is resolved against this repo's root, not this
            server process's working directory.
        customer: Customer name, shown verbatim (upper-cased) on the title
            slide (required).
        logo_path: Optional path to a customer logo image, spliced into the
            title slide. Omit to leave the title slide without a logo.
        output_path: Output .pptx path. Defaults to
            "output/<Customer_Slug>_Platform_Review_<date>.pptx", where
            <date> is a YYYY-MM-DD found in the checklist filename, else
            today's date.
        rows_per_slide: Max table rows per findings slide. Defaults to
            config/deck_layout.yaml's table_rows_per_slide (4 if unset).
        include_pass_items: Also list Pass/Not-Applicable items in findings
            tables, not just Fail/Partial/Needs Review. If omitted, uses
            config/deck_layout.yaml's include_pass_items (default true).
            Unlike the CLI's --include-pass-items flag (which can only turn
            this on for a run), passing an explicit false here overrides a
            true config default for this call.
        base_deck_path: Base branded .pptx to build from. Defaults to
            "resources/Dataiku Branding Template 2026.pptx".

    Returns:
        A dict with:
          - output_path: absolute path to the generated .pptx
          - structural_problems: list of structural-validation problem
            strings (empty list means the deck passed all automated checks)
          - data_warnings: list of checklist data inconsistencies (e.g.
            section totals that don't match Overall Status Counts, Summary
            rows whose ID/status disagree with the section sheets) -- the
            deck still built, but may show wrong or missing values; fix the
            checklist and rebuild rather than patching the deck
          - manual_qa_checklist: guidance for the manual visual QA pass that
            automated validation cannot perform (only present when
            structural_problems is empty)
          - generator_version: this tool's own version (common.VERSION) that
            produced the deck
    """
    layout_config = common.load_config("deck_layout.yaml")

    checklist = _resolve(checklist_path)
    base_deck = (
        _resolve(base_deck_path) if base_deck_path
        else common.REPO_ROOT / layout_config.get("base_deck", "resources/Dataiku Branding Template 2026.pptx")
    )
    logo = _resolve(logo_path) if logo_path else None
    effective_rows_per_slide = rows_per_slide if rows_per_slide is not None else layout_config.get("table_rows_per_slide", 4)
    effective_include_pass_items = (
        include_pass_items if include_pass_items is not None
        else layout_config.get("include_pass_items", False)
    )
    resolved_output = _resolve(output_path) if output_path else build_deck.default_output_path(checklist, customer)

    if not checklist.exists():
        raise FileNotFoundError(f"Checklist file not found: {checklist}")
    if not base_deck.exists():
        raise FileNotFoundError(f"Base deck not found: {base_deck}")
    if logo is not None and not logo.exists():
        raise FileNotFoundError(f"Logo file not found: {logo}")

    resolved_output = build_deck.build_deck(
        checklist_path=checklist,
        customer=customer,
        output_path=resolved_output,
        base_deck=base_deck,
        logo_path=logo,
        rows_per_slide=effective_rows_per_slide,
        include_pass_items=effective_include_pass_items,
    )

    try:
        problems = validate_deck_lib.validate(resolved_output)
    except Exception as e:
        raise RuntimeError(f"Deck was generated at {resolved_output} but structural validation failed to run: {e}") from e

    result = {
        "output_path": str(resolved_output),
        "structural_problems": problems,
        "data_warnings": build_deck.collect_data_warnings(checklist),
        "generator_version": common.VERSION,
    }
    if not problems:
        result["manual_qa_checklist"] = validate_deck_lib.MANUAL_QA_CHECKLIST
    return result


@mcp.tool(name="validate_deck")
@_surface_errors
def validate_deck_tool(pptx_path: str) -> dict[str, Any]:
    """Run structural self-checks against an already-generated .pptx deck
    (malformed XML, dangling slide relationships, leftover placeholder
    text). Does not perform layout/visual QA -- see the manual_qa_checklist
    returned by build_platform_review_deck for that.

    Args:
        pptx_path: Path to a .pptx file to validate. A relative path is
            resolved against this repo's root, not this server process's
            working directory.

    Returns:
        A dict with:
          - pptx_path: the resolved absolute path that was checked
          - passed: true if no structural problems were found
          - problems: list of human-readable problem strings (empty if
            passed is true)
          - generator_version: this tool's own version (common.VERSION) that
            ran the validation
    """
    path = _resolve(pptx_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    try:
        problems = validate_deck_lib.validate(path)
    except zipfile.BadZipFile as e:
        raise ValueError(f"File is not a valid .pptx (corrupt or wrong format): {path}") from e

    return {
        "pptx_path": str(path),
        "passed": not problems,
        "problems": problems,
        "generator_version": common.VERSION,
    }


if __name__ == "__main__":
    mcp.run()
