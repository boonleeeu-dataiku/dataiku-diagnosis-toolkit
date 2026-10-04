---
name: dataiku-codex-workflow
description: Apply Codex tool and file-access conventions when using this plugin's Dataiku diagnosis reader, checklist review, or Platform Review deck builder in Codex. Use alongside the corresponding Dataiku task skill, not for unrelated Dataiku work.
---

# Dataiku toolkit in Codex

Use the task-specific skill in this plugin for the actual review or deck workflow. This companion only translates host-specific instructions that appear in those skills.

- There is no reader MCP server: run the reader skill's `scripts/orient.sh <bundle_root>` with the shell for triage. The review generator MCP server provides `write_summary`, `analyze_checklist`, `build_platform_review_deck`, and `validate_deck`. Discover deferred tools using Codex's available tool discovery mechanism; the literal `ToolSearch` syntax in the original skills is only an example from another host. Read bundle files with Codex's normal read/search tools, following the reader skill's large-file guidance.
- For checklist workbooks, use Codex's available spreadsheet capability (the `spreadsheets` skill when installed) and `openpyxl` for the original skill's cell-level writeback. The original reference to an `xlsx` skill means a spreadsheet-capable workflow; it does not require a skill with that exact name.
- For a review performed by Codex, write `Codex (AI-assisted review of <bundle name>)` in `validated_by` and identify Codex in the `write_summary` reviewer field unless the user supplied a reviewer name. The checklist skill's verbatim `Claude` label applies to its original host.
- Codex web search has no `extended` mode. For the checklist skill's version-currency lookup, run its two searches with the available web search tool and open the official Dataiku release page to verify the newest GA version. Use the web tool's page-opening action where the skill says `WebFetch`.
- When using the bundled default checklist, resolve `resources/checklist_template.xlsx` from the checklist-review skill's own directory and save the completed workbook to a separate output path outside the plugin directory.
- If diagnosis files and the checklist are already accessible in the local workspace, work with their paths directly. The `device_*` calls in the checklist skill apply only when the user's files are on a separately linked computer. Ask for access or for the files only when they are actually unavailable.
- Supply absolute paths for diagnosis bundles, checklists, logos, branding templates, and output files when calling the MCP tools. The review generator otherwise resolves relative inputs from its own server directory.
- Keep customer diagnosis bundles outside the plugin repository.
