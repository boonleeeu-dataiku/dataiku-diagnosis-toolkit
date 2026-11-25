# Secrets in a review

Bundles hold live credentials, and everything you write ends up in the workbook, the deck and the transcript, which
the customer and other people read. A leaked secret there is hard to take back, so the rules below are strict.

Follow the reader's "Handling secrets" section for how to open files (its `scripts/peek.py` for config JSON, never a whole
file dump). In addition:

- Never copy a secret into `evidence_found`, `notes`, the narrative or the deck. If one gets printed, say so in your
  final summary, name the file, and tell the user to rotate it.
- If the bundle itself holds plaintext credentials (for example an internal-database password), report that even if you
  never printed the value: name the file and the kind of credential, never the value, and recommend rotating it and moving
  it to a secrets store. The exact line to put in your final summary is in `SKILL.md`, step 7; use it every time.
