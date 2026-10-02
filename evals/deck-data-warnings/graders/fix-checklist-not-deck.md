---
type: llm
---

PASS if the reply reports that the deck was built but the checklist has data inconsistencies
(the Total 42 vs 40 items mismatch and/or SEC-004's status disagreement), and advises fixing
the checklist workbook and rebuilding the deck.
FAIL if it presents the deck as ready to send without surfacing those warnings, or suggests
hand-editing the generated .pptx to correct them.
