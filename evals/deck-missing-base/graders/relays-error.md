---
type: llm
---

PASS if the reply says the deck could not be generated because the Dataiku branding template
(the base deck) is missing, and either tells the user to place it at
mcp-server-review-generator/resources/Dataiku Branding Template 2026.pptx or asks them for the
path to their own copy.
FAIL if it claims a deck was generated, or if it states a guessed location for the user's copy
of the template as though it were known.
