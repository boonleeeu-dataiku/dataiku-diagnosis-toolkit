---
name: dataiku-codex-workflow
description: Apply Codex tool and file-access conventions when using this plugin's Dataiku diagnosis reader, checklist review, or Platform Review deck builder in Codex. Use alongside the corresponding Dataiku task skill, not for unrelated Dataiku work.
---

# Dataiku toolkit in Codex

Use the task-specific skill in this plugin for the actual review or deck workflow. This companion only translates host-specific instructions that appear in those skills.

- The two bundled MCP servers provide `run_orient`, `safe_read`, `build_platform_review_deck`, and `validate_deck`. Discover deferred tools using Codex's available tool discovery mechanism; the literal `ToolSearch` syntax in the original skills is only an example from another host.
- For checklist workbooks, use Codex's available spreadsheet capability (the `spreadsheets` skill when installed) and `openpyxl` for the original skill's cell-level writeback. The original reference to an `xlsx` skill means a spreadsheet-capable workflow; it does not require a skill with that exact name.
- When the user has no checklist, follow the checklist-review skill's offer to use its bundled `resources/checklist_template.xlsx`. Resolve that path from the checklist-review skill's own directory, use the template as the input, and save the completed workbook to a separate output path outside the plugin directory. Tell the user that the default template was used.
- If diagnosis files and the checklist are already accessible in the local workspace, work with their paths directly. The `device_*` calls in the checklist skill apply only when the user's files are on a separately linked computer. Ask for access or for the files only when they are actually unavailable.
- Supply absolute paths for diagnosis bundles, checklists, logos, branding templates, and output files when calling the MCP tools. The review generator otherwise resolves relative inputs from its own server directory.
- Keep customer diagnosis bundles outside the plugin repository. The branded deck template must be supplied locally, as described in the plugin README.
