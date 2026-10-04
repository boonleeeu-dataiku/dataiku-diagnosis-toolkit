"""Plugin manifests agree with each other and point at files that exist."""

import json
import re

import pytest
import yaml

from conftest import REPO_ROOT


def load(rel):
    return json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))


def test_plugin_version_is_identical_in_all_four_manifests():
    versions = {
        ".claude-plugin/plugin.json": load(".claude-plugin/plugin.json")["version"],
        ".claude-plugin/marketplace.json": load(".claude-plugin/marketplace.json")["plugins"][0]["version"],
        "plugin.json": load("plugin.json")["version"],
        ".codex-plugin/plugin.json": load(".codex-plugin/plugin.json")["version"],
    }
    assert len(set(versions.values())) == 1, versions


def test_changelog_latest_release_matches_plugin_version():
    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    latest = re.search(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.MULTILINE).group(1)
    assert latest == load(".claude-plugin/plugin.json")["version"]


def test_plugin_names_agree():
    name = load(".claude-plugin/plugin.json")["name"]
    assert load(".claude-plugin/marketplace.json")["plugins"][0]["name"] == name
    assert load("plugin.json")["name"] == name
    assert load(".codex-plugin/plugin.json")["name"] == name


def _expand(value: str) -> str:
    for var in ("${CLAUDE_PLUGIN_ROOT}", "${PLUGIN_ROOT}"):
        value = value.replace(var, str(REPO_ROOT))
    return value


@pytest.mark.parametrize("manifest", [".mcp.json", "mcp.json", ".codex-plugin/plugin.json"])
def test_mcp_server_paths_exist(manifest):
    servers = load(manifest)["mcpServers"]
    assert set(servers) == {"dataiku-review-generator"}
    for name, cfg in servers.items():
        for arg in cfg.get("args", []):
            if "/" in arg:
                assert (REPO_ROOT / _expand(arg)).exists(), f"{manifest} {name}: {arg}"
        for key, val in cfg.get("env", {}).items():
            if "PLUGIN_ROOT" in val:
                assert (REPO_ROOT / _expand(val)).exists(), f"{manifest} {name}: {key}={val}"


def test_codex_skill_dirs_exist():
    for d in load(".codex-plugin/plugin.json")["skills"]:
        assert (REPO_ROOT / d).is_dir(), d


SKILL_FILES = sorted((REPO_ROOT / "skills").glob("*/SKILL.md")) + sorted((REPO_ROOT / "codex-skills").glob("*/SKILL.md"))


@pytest.mark.parametrize("skill_md", SKILL_FILES, ids=lambda p: p.parent.name)
def test_skill_frontmatter(skill_md):
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert m, "missing YAML frontmatter"
    meta = yaml.safe_load(m.group(1))
    assert meta["name"] == skill_md.parent.name
    assert isinstance(meta.get("description"), str) and len(meta["description"]) > 40
