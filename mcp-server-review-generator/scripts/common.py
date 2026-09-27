"""Shared paths and config loading for the Dataiku Review Generator scripts."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
RESOURCES_DIR = REPO_ROOT / "resources"
CONFIG_DIR = REPO_ROOT / "config"
OUTPUT_DIR = REPO_ROOT / "output"

SAMPLE_DECK = RESOURCES_DIR / "sample_platform_review_deck.pptx"
BRANDING_TEMPLATE = RESOURCES_DIR / "Dataiku Branding Template 2026.pptx"

# Single source of truth for this tool's own version (SemVer), read from the
# repo-root VERSION file so every script gets it via `common.VERSION` -- see
# CHANGELOG.md for what changed at each version and CLAUDE.md's "Versioning"
# section for the bump procedure.
VERSION = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def load_config(name: str) -> dict:
    """Load a YAML config file from config/ by filename, e.g. 'deck_layout.yaml'."""
    path = CONFIG_DIR / name
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
