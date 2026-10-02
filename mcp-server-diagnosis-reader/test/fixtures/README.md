# Test fixtures

Everything under `bundles/` is **synthetic**. It was hand-written for tests and contains no real
diagnosis data. Each bundle has only the files the tests need, laid out like a real extracted
bundle (`diag.txt` + `timings.txt` at the root, and a data-dir mirror under
`data_dataiku/<nodetype>/`).

Never copy anything from `resources/` (real bundles) into this directory. Directory names
deliberately avoid the `dku_diagnosis_*` prefix, which `.gitignore` excludes.

Edge cases that need large or binary files, or symlinks (size caps, binary sniffing, traversal),
are built in a temp directory at test time rather than committed here.
