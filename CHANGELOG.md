# Changelog

All notable changes to the `dataiku-diagnosis-toolkit` plugin are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/). This tracks the plugin's own
top-level version (`.claude-plugin/plugin.json`), independent of the versions carried by
vendored components (`mcp-server-diagnosis-reader/`, `mcp-server-review-generator/`) — see
`CLAUDE.md`.

## [Unreleased]

## [0.5.0] - 2026-09-30

### Added

- `dataiku-diagnosis-checklist-review`: new calibration for automation-node existence /
  Design–Automation separation checks (e.g. ARCH-001) on design-node bundles. Always marked
  **Needs Review**, since a design bundle cannot confirm a separate automation node. The review
  highlights a local deployer (`config/project-deployer/`, distinguishing populated from empty;
  `config/api-deployer/` noted separately as an API-node indication) or a remote deployer
  (`deployerClientSettings.mode = REMOTE`) as indications, and otherwise states that no
  definitive configuration exists and customer verification is needed. The deployer directories
  were also added to the skill's evidence-source list.

## [0.4.0] - 2026-09-28

### Added

- Bundled default checklist template for `dataiku-diagnosis-checklist-review`
  (`skills/dataiku-diagnosis-checklist-review/resources/checklist_template.xlsx`). If the user
  doesn't have their own checklist, the skill now offers to fall back to this bundled template
  instead of hard-requiring a user-supplied file.

## [0.3.0] - 2026-09-28

### Added

- Codex plugin support alongside Claude: repo-root `plugin.json` and `mcp.json` (Codex's own
  manifests), `.codex-plugin/plugin.json`, `codex-skills/dataiku-codex-workflow/SKILL.md`,
  `scripts/codex-start.sh`, `CODEX_SETUP.md`, and `AGENTS.md` repository guidance restricting
  Codex to its own files. Codex adapts to Claude-side changes post-hoc and never edits Claude's
  skills/MCP code.
