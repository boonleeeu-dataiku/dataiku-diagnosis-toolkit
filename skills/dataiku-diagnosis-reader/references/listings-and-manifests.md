# Reading the `find -ls` manifest files safely

Several root files are **metadata-only manifests**, produced by `find <dir> -ls` — they record
path/size/owner/mtime for every file under a directory, but contain **no file content**:

- `datadir_listing.txt` — the entire `DATA_DIR` (often the single largest file in the bundle;
  observed from ~340MB/1.5M+ lines to ~2.3GB)
- `installdir_listing.txt` — the DSS install directory (jars, dist, scripts, samples)
- `config_listing.txt` — the `config/` subtree specifically
- `lib_listing.txt` — the `lib/` subtree (JDBC drivers, java libs, a git-tracked python lib dir)
- `code_envs_desc_listing.txt` — both the `code-envs/desc/` and `acode-envs/desc/` subtrees (the
  collector scans both on every node type; includes the internal `.git` history DSS keeps for
  code-env spec changes)

## Format

Standard `find -ls` columns (whitespace-separated, last field is the path):

```
<inode> <blocks> <perms> <links> <owner> <group> <size> <month> <day> <time-or-year> <path>
```

## Why this matters

Because these are metadata-only, they're the right place to check **existence, size, and last-
modified time** of something — but never the right place to look for *content*. Most notably:
job run history, scenario run logs, dataset build timelines, and (sometimes) audit logs appear
here as path entries but are not otherwise present in the bundle as readable content (see
`references/limitations.md`).

## Safe query patterns

Never `cat`/read one of these whole. Instead:

```sh
# Check size/line count before doing anything else
wc -l datadir_listing.txt

# Find entries under a specific subtree
grep '/jobs/' datadir_listing.txt | head -50

# Extract size (7th field) and path (11th+ fields) for matches
grep 'scenarios/MY_SCENARIO' datadir_listing.txt | awk '{$1=$2=$3=$4=$5=$6="";print}'

# Find the largest files listed under a path
grep '/data_dataiku/design/managed_datasets/' datadir_listing.txt | sort -k7 -n -r | head -20

# Does a specific run-history path exist at all, and when was it last touched?
grep -m1 'timelines/MY_PROJECT' datadir_listing.txt
```

If the question is "does X exist and how big is it," these commands answer it directly. If the
question is "what does X contain," these files cannot answer it — say so.
