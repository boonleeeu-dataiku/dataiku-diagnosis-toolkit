---
name: "dataiku-diagnosis-checklist-review"
description: "Evaluate a Dataiku DSS diagnosis bundle against a checklist spreadsheet using the dataiku-diagnosis-reader tool, filling in validation results and a summary tab. Falls back to a bundled default checklist template if the user doesn't have one. Use when the user asks to review/validate a Dataiku diagnosis against a checklist, or run a Dataiku instance health/compliance review."
---

# Dataiku diagnosis checklist review

Given (1) a Dataiku DSS diagnosis bundle directory and (2) a checklist spreadsheet
listing check items (typically columns like `id`, `priority`, `check_type`,
`statement`, `parameter_hint`, `expected_value`, `supporting_evidence`,
`contradicting_evidence`, and empty result columns such as `validation_status`,
`evidence_found`, `notes`, `validated_at`, `validated_by`), evaluate every row
against the bundle's actual contents and write the results back into the
spreadsheet, plus add/update a Summary tab.

If the user invokes this without giving both paths, ask for: the diagnosis
bundle path, and the checklist file path. Don't ask anything else up front —
start working once you have both.

If the user says they don't have a checklist file handy, offer to use the
bundled default template at `resources/checklist_template.xlsx` (relative to
this skill's own directory) instead, and say plainly once you proceed that
you're using the default template rather than a user-supplied checklist.

## 0. Access and tools

- If this session is linked to the user's computer (remote-devices tools
  present) and the paths are local file paths, request folder access to the
  common parent directory covering both the bundle and the checklist
  (`device_request_folder_access`), then `device_stage_files` the checklist
  into the container to read/write it, and `device_list_dir` (recursive) on
  the bundle to see its structure.
- Load the `dataiku-diagnosis-reader` tools if deferred
  (`ToolSearch` with `select:...run_orient,...safe_read`, using whatever
  prefix — bare or `mcp__remote-devices__` — is present in the tool list).
- Load the `xlsx` skill before reading/writing the spreadsheet.
- If a version-currency check is present in the checklist (see calibration
  below), confirm a web search tool is available — it will be needed to
  look up the latest Dataiku DSS release.

## 1. Orient

Run `run_orient` on the bundle root first. It reports node type/version, the
largest files, and presence of key troubleshooting files (dmesg, stacks,
cgroups usage, sanity-check.json, hs_err_pid crash dumps, audit logs). This
tells you what evidence is realistically available before you plan reads.

## 2. Read the checklist fully

Dump every sheet's rows (id, priority, check_type, statement, parameter_hint,
operator, expected_value, supporting_evidence, contradicting_evidence,
rationale, source references) into a working file — don't try to hold 50+
rows of context in your head. Note the exact result-column headers and their
column positions per sheet (they may differ sheet to sheet).

## 3. Plan evidence gathering by theme, not by row

Many checklist rows share the same underlying source file. Read each source
file once and extract everything relevant, rather than re-reading it per row.
Typical high-value sources in a DSS diagnosis bundle:

- `apps/dss/<node>/config/general-settings.json` — covers most
  settings-based checks (security, cgroups, Spark, containerized execution,
  LLM Mesh/GenAI settings, connections preferences, flow limits, etc.)
- `apps/dss/<node>/install.ini` — port, backend.xmx, HTTPS/security headers,
  instance/install IDs
- `apps/dss/<node>/run/sanity-check.json` — DSS's own self-diagnosed
  warnings; treat these as authoritative, direct evidence for the relevant
  checklist items (SSD/rotational disk, missing cgroup limits, missing base
  images, connection detail-read gaps, etc.)
- `apps/dss/<node>/config/connections.json` — enumerate connection types and
  their relevant settings (detailsReadability/readableBy, hdfsInterface,
  fast-write flags, filesystem_root presence/restrictions) programmatically
  (parse as JSON) rather than dumping it raw — it's usually too large for a
  single safe_read.
- `apps/dss/<node>/config/clusters/<name>.json` — cluster type
  (manual vs managed), architecture, Spark/container overrides. An empty or
  absent `config/clusters/` directory, and no `defaultK8sClusterId`/cluster
  reference in `general-settings.json`, means no Kubernetes cluster is
  attached to the instance at all — check this before evaluating any
  Kubernetes-conditional item (see calibration below).
- `dmesg.txt`, `sysctl.txt`, `syspackages.txt` — total RAM, kernel/OS version
- `run/hs_err_pid*.log` — JVM crash dumps; grep the `^# ` header lines for
  the crash cause (OOM vs segfault etc.) rather than reading the full file
- `run/backend.log*` — grep for `ERROR`/`FATAL`/`OutOfMemoryError`; when a
  file is too large for `safe_read`, use the linked device's shell
  (`device_bash`) to `grep -c` / `grep | sort | uniq -c` for patterns and
  counts instead of reading line by line — this is far cheaper.
- `apps/dataiku-dss-<version>/dss-version.json` — product version

For files bigger than a few hundred KB, always use a `pattern` on
`safe_read`, or use `device_bash` with grep/python for structured parsing —
never try to read a multi-hundred-MB file whole.

## 4. Evaluate every row

For each checklist item, decide one of a small fixed set of statuses (keep
this consistent across the whole workbook): **Pass**, **Fail**, **Partial**,
**Needs Review**, **Not Applicable**. Use "Not Applicable" when the check is
conditional (e.g., "if using Snowflake") and the precondition isn't met.
Use "Needs Review" honestly for anything requiring a live functional test,
an external system (Fleet Manager, K8s cluster metrics, CMDB), or a
customer conversation that a static diagnostic snapshot cannot answer —
don't guess Pass/Fail on those.

For each item, write:
- `evidence_found`: concrete citations — exact file path(s) and the specific
  key/value or log line(s) that support the finding.
- `notes`: the recommendation or caveat, and cross-reference related
  findings by id when they're causally linked (e.g., an OOM crash pattern
  linked to a concurrency-limit setting).
- `validated_at` / `validated_by`: today's date and a reviewer label noting
  this was an AI-assisted review against the specific bundle.

Look actively for causal chains across items (e.g., a resource limit set to
a disabling value, paired with crash dumps and recurring error-log entries,
all pointing to one root cause) — call these out explicitly and prioritize
them, rather than reporting each row in isolation.

### Known check-specific calibrations

Apply these interpretations consistently. They come directly from the user,
supersede a literal reading of the checklist's `expected_value`/evidence
text, and should be extended here over time whenever the user gives another
one — add each as its own bullet rather than overwriting prior ones.

- **Kubernetes-conditional checks in general (Spark-on-K8s, containerized
  execution, cluster configuration, etc.):** first determine whether a
  Kubernetes cluster is actually attached to the instance at all (see
  `config/clusters/` and `defaultK8sClusterId` in step 3 above). If no
  cluster is attached, mark any check that depends on Kubernetes/Elastic
  Compute as **Not Applicable** rather than Fail or Needs Review — these
  checks are only relevant once a cluster is attached. Once a cluster *is*
  attached, it becomes critical that a valid containerized execution
  configuration (`containerSettings`) is actually present — treat that as a
  must-have, not optional.

- **Recommended containerized execution config baseline (e.g. a 'Standard'
  config at ~200MB/16000MB and a 'Webapp' config at ~500MB/500MB, or similar
  named/sized baselines):** treat any such baseline given in the checklist's
  `expected_value`/`supporting_evidence` as an illustrative example, not a
  literal instruction to match names or exact sizes. It is sufficient to see
  **more than one containerized execution config defined with genuinely
  varying sizes** (e.g. different memory/CPU requests-limits across configs,
  showing an intent to size workloads differently) — mark this **Pass**
  even when the config names and exact memory figures don't match the
  baseline example. Still call out in `notes` if all configs are actually
  identically sized despite different names (that remains a real gap, as
  distinct from just not matching the example's naming/numbers).

- **Spark and containerized-execution per-user Kubernetes namespace checks**
  (e.g. items about a "per-user namespace pattern", `dss-ns-${dssUserLogin}`,
  or similar, for either Spark configs or containerized execution configs):
  it is sufficient evidence of compliance to see the namespace parameter
  (e.g. `managedNamespace` / `kubernetesNamespace`) provisioned with a
  dynamic/templated variable (such as `${namespace}`), **for a managed
  Kubernetes cluster attached to the Dataiku instance**. Do not require
  tracing the variable to confirm it literally resolves to the
  `dss-ns-${dssUserLogin}` string — mark the item **Pass** (not Needs
  Review) once a templated/dynamic namespace variable is present, and note
  in `evidence_found` which field/value was seen. This calibration applies
  specifically to a **managed** cluster (Dataiku-provisioned/managed). For a
  **manual**/externally-registered cluster (check `type` in
  `config/clusters/<name>.json`), namespace behavior may be governed outside
  DSS configuration entirely — keep judging that case on its own merits
  rather than applying this shortcut.

- **Dataiku DSS version currency check (e.g. "DSS Version Currency"):**
  actively look up Dataiku's current generally-available DSS release with a
  web search (do this each run — the answer changes over time, don't rely on
  memorized/training-time knowledge of "the latest version"). Search for
  something like "Dataiku DSS latest version release notes" and use an
  official Dataiku source (release notes / changelog / docs.dataiku.com) for
  the answer. Compare the bundle's `product_version` (from `dss-version.json`,
  format `MAJOR.MINOR.PATCH`) against the latest GA version's major version
  number only, and apply this fixed internal rule:
  - If the bundle's **major** version matches the current major release
    (e.g. bundle is 14.x and the latest GA is also 14.x, regardless of minor
    or patch), mark **Pass**.
  - If the bundle's major version is behind the current major release (e.g.
    bundle is 13.x while latest GA is 14.x), mark **Needs Review** (not
    Fail) — a major-version gap warrants a human look at upgrade planning
    rather than an automatic fail.
  In both cases, state in `notes`/`evidence_found` the bundle's version, the
  latest GA version found, its release date if available, and how many
  major versions behind (0 if current); cite the source. If the web search
  fails, returns nothing usable, or no web search tool is available in this
  session, do not guess or fall back to prior/training knowledge of the
  latest version — set `notes` to state plainly that currency could not be
  verified against Dataiku's current release information (web lookup
  failed/unavailable) and mark the item **Needs Review**.

- **HTTPS enforcement check (e.g. "SEC-006", especially for custom/on-prem
  installs):** `install.ini` and DSS's own config only show whether DSS
  itself is terminating TLS. They cannot show whether an external reverse
  proxy (nginx, an ALB/load balancer, an API gateway, etc.) sits in front of
  DSS and terminates HTTPS there instead — that setup is invisible to the
  diagnosis bundle. So: if the bundle shows DSS is *not* itself configured
  for HTTPS (e.g. plain HTTP in `install.ini`), do not mark this **Fail**.
  Mark it **Needs Review** instead, and in `notes` state plainly that the
  bundle cannot confirm or rule out an external reverse proxy terminating
  HTTPS in front of DSS, and that this needs to be verified directly with
  the customer/infrastructure team before treating it as a real gap. Only
  mark **Pass** when the bundle shows positive evidence HTTPS is enforced
  somewhere in the path (DSS-terminated or a documented proxy setup
  referenced in the bundle); only mark **Fail** if there is positive
  evidence no HTTPS exists anywhere (e.g. explicit customer confirmation on
  record, not just absence from the bundle).

## 5. Write results back with openpyxl

Match each row by its `id` column (not by row number) when writing results,
so the mapping is robust to row reordering. Verify every id in the sheet got
a result and every result was consumed (no silent mismatches) before saving.

## 6. Add/update a Summary sheet

Insert a `Summary` sheet as the first tab (recreate it if it already exists,
so re-running the skill is idempotent) containing:
- Header: bundle name/path, node/version info, generation date, reviewer
- Overall status counts (table) across all sheets
- Per-section status breakdown (table)
- Critical findings: must-have items that Fail, most causally-central first
- Other must-have items that are Partial or Needs Review
- A short, priority-ordered recommendations list, sequencing linked issues
  together (e.g., root cause before its symptoms)

Match the existing workbook's font/fill conventions (check an existing
header cell's font/fill before choosing styles) rather than imposing a new
look. Color-code status cells consistently (e.g., green/red/yellow-ish
fills) and freeze the header rows.

## 7. Deliver

Send the updated file to the conversation. If the source file came from the
user's linked computer, write the result back to the same path via
`device_commit_files` as well, and say so in one line. If you used the
bundled default template instead of a user-supplied checklist, there is no
original path to write back to — just name the output after the diagnosis
bundle (e.g. `<bundle-name>_checklist_review.xlsx`) and send it back to the
conversation. Give a short summary of headline results (counts + the 1-3
most important findings) rather than repeating the whole checklist back in
chat.