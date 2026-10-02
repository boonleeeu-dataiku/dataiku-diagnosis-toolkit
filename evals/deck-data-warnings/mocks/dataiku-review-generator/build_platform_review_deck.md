---
expect:
  checklist_path: "/acme_checklist_review\\.xlsx$/"
  customer: "/Acme/"
---

{"output_path": "/plugins/dataiku-diagnosis-toolkit/mcp-server-review-generator/output/Acme_Corp_Platform_Review_2026-07-22.pptx", "structural_problems": [], "data_warnings": ["Overall Status Counts says Total 42, but the section sheets hold 40 items; the deck shows 40.", "Critical Findings shows SEC-004 as 'Fail', but its section sheet says 'Partial'."], "manual_qa_checklist": "Please open the generated deck in PowerPoint/Keynote/Google Slides and manually check that card and table text is not overflowing and that status colors are consistent.", "generator_version": "0.1.6"}
