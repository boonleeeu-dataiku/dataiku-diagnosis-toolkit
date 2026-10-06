# Working with files on a linked computer

Read this only when the session is linked to the user's computer (remote-devices tools present) and
the paths are local. It covers the review skill and the deck builder.

## Access

Call `get_device_info` first. If both paths already sit under its `connectedFolders`, skip the access
request. Otherwise request folder access to the common parent of both (`device_request_folder_access`;
if the first request doesn't take effect, repeat it once before asking the user). Then:

- `device_stage_files` a user-supplied checklist into the container.
- Run `orient.sh` and bundle reads through `device_bash`; use `device_list_dir` (recursive) to see the
  bundle's structure. If `orient.sh` can't run (it lives in the plugin, not on the device), follow the
  reader's fallback for orienting by hand and say so in your report.
- Connected folders appear in `device_bash` as `$HOME/mnt/<last path segment>`, but the generator
  tools and `device_commit_files` want the real path.

**Bundled default template:** it lives in the container (this skill's `resources/`), so nothing needs
staging. Copy it to a scratch file, fill it in there, copy the finished file to
`/mnt/user-data/outputs/<name>`, and `device_commit_files` it by `stagedPath`. That first commit
creates the file on the device.

## The loop

The `dataiku-review-generator` tools (`write_summary`, `analyze_checklist`, the deck build) run on the
user's computer and see device paths only. In order:

1. Stage the checklist into the container.
2. Edit it and write the narrative there.
3. `device_commit_files` both back, and verify each commit (below).
4. Call the generator tools with device paths (`checklist_path` is the device path). Pass an
   `output_path` in the user's outputs folder: the default is inside the plugin directory, and a
   rebuild on the same day overwrites the same file name.
5. `write_summary` rewrites the checklist on the device, so your container copy is now stale:
   re-stage it before editing again.

If you stage config files into the container to analyse them, redact values only, never key names
(masking keys hides the setting you are sizing), and sanity-check the numbers you extract.

## Verify every commit

`device_commit_files` can report `written` while the device keeps the old bytes, especially when the
same `stagedPath` is committed a second time. The sync is asynchronous, and a build from a stale
narrative or checklist produces only a hash warning.

After each commit, read the device file back with `device_bash` (`wc -c`, or `grep` for a phrase you
just changed) and compare it with the container copy before calling a generator tool. If it is
stale, commit again under a **new staged filename** (e.g. `narrative_rev2.json`) to the same device
path, and verify again. `analyze_checklist` and the build also report `checklist_path`,
`checklist_modified` and `narrative_modified` (UTC): if they are older than what you last wrote,
recommit.

`device_stage_files` is also async: wait for the size or mtime to change instead of sleeping a fixed
time. Use explicit paths, never a glob over the outputs parent, so sibling run folders aren't listed.
