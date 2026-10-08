# Orienting when `orient.sh` cannot run where the bundle is

`scripts/orient.sh <bundle_root>` lives in the skill folder, which may be on a different machine from the bundle (for example a
sandbox agent with the bundle on a linked computer). Don't skip orientation; do one of the following.

**First choice: pipe the script to the machine that holds the bundle.** It is read-only, self-contained and about 4.5KB, so run
`bash -s -- <root>` there with the script body on stdin (a quoted heredoc: `bash -s -- <root> <<'ORIENT'` ... `ORIENT`). Pipe the
whole script verbatim, not a condensed copy, so the output matches what the script prints elsewhere. It needs `bash` plus standard
`find`/`du`/`grep`; on Windows run it where the bundle is, in WSL or Git Bash.

**If stdin can't be passed**, do the same by hand with read-only commands run where the bundle is:

- `find <root> -maxdepth 6 -name install.ini`: its directory is the data-dir mirror.
- `grep -m1 DKU_NODE_TYPE <root>/diag.txt` and `<mirror>/dss-version.json`: node type and version.
- `find <root> -type f -size +50M -exec ls -lh {} +`: the biggest files.
- `ls` for `diag.txt`, `dmesg.txt`, `<mirror>/run/` and `<mirror>/config/general-settings.json`.

Say in your output that you oriented by hand.
