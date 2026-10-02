"""Toolkit-level tests: cross-component contracts, manifest consistency, vendored-copy
drift, and the completed-review checker used by the LLM evals. Unit tests for the
vendored MCP servers live with them (mcp-server-*/test[s]/) and are run separately --
see scripts/test.sh."""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RG_DIR = REPO_ROOT / "mcp-server-review-generator"
FIXTURES = REPO_ROOT / "tests" / "fixtures"
TEMPLATE = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "resources" / "checklist_template.xlsx"

for p in (RG_DIR / "scripts", REPO_ROOT / "tests" / "lib"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


@pytest.fixture(scope="session")
def rg_builder():
    """The review generator's synthetic-checklist builder (its tests/conftest.py), loaded
    under another module name so it doesn't collide with this directory's conftest."""
    spec = importlib.util.spec_from_file_location("rg_checklist_builder", RG_DIR / "tests" / "conftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
