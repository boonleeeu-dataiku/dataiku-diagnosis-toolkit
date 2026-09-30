---
name: "dataiku-review-deck-builder"
description: "Turn a completed Dataiku DSS platform-review checklist spreadsheet into a branded, customer-facing Platform Review PowerPoint deck. Use when the user has a reviewed/validated checklist (e.g. produced by the dataiku-diagnosis-checklist-review skill) and wants a slide deck to share with the customer."
---

# Dataiku review deck builder

This is step 2 of the two-step workflow: `dataiku-diagnosis-checklist-review` evaluates a
diagnosis bundle against a checklist and writes validation results into the workbook; this skill
turns that completed workbook into a `.pptx` deck. If the user hasn't reviewed the checklist yet,
suggest running that skill first — this one expects a checklist that already has
`validation_status`/`evidence_found`/`notes` filled in.

## 0. Tools

Load the deferred tools if needed (`ToolSearch` with
`select:build_platform_review_deck,validate_deck`). Both come from the bundled
`dataiku-review-generator` MCP server.

## 1. Generate the deck

Call `build_platform_review_deck` with:
- `checklist_path` (required) — the completed checklist `.xlsx`.
- `customer` (required) — customer name, shown on the title slide.
- `logo_path` (optional) — a customer logo image for the title slide.
- `output_path` (optional) — defaults to `output/<Customer_Slug>_Platform_Review_<date>.pptx`.
- `rows_per_slide` / `include_pass_items` (optional) — layout tuning; leave unset unless the user
  asks for something specific.
- `base_deck_path` (optional) — only needed if the branding template isn't at its default location
  (see "If the base deck isn't found" below).

This already runs structural validation internally and returns
`{output_path, structural_problems, data_warnings, manual_qa_checklist, generator_version}` — no separate
`validate_deck` call is needed for a normal run.

## 2. If the base deck isn't found

The tool needs `Dataiku Branding Template 2026.pptx` (134MB, not bundled with this plugin — see
this plugin's README). If the call fails with a "Base deck not found" error:
- Relay that message plainly, and tell the user to complete the one-time setup (placing the file at
  `mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx`), **or**
- If they already have a copy elsewhere (e.g. a sibling `Dataiku Review Generator` checkout on this
  machine), ask for its path and retry the call with `base_deck_path` set explicitly.

Don't guess a path — always get it from the user or a real error message.

## 3. Report results

- If `data_warnings` is non-empty, the deck built but may show wrong or missing values (e.g.
  section totals that don't match Overall Status Counts, or Summary rows whose ID/status disagree
  with the section sheets). List the warnings, fix the **checklist** (not the generated deck), and
  rebuild. Hand-editing the deck would leave the checklist wrong and get overwritten by the next
  build.
- If `structural_problems` is non-empty, don't declare success — list the problems and say the
  deck needs another look before sending it out.
- If empty, tell the user the deck was generated (give the `output_path`), then relay
  `manual_qa_checklist` verbatim as follow-up steps — automated validation only checks structure
  (malformed XML, dangling relationships, leftover placeholder text), never visual layout, so this
  checklist is the only QA pass that catches that.
- Any other tool error (missing checklist, bad logo path, schema mismatch in the checklist) comes
  through as a real, specific message — relay it as-is rather than paraphrasing.
