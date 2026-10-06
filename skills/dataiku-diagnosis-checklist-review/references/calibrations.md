# Check-specific calibrations

> Judgment only: this file says which status to give, never where or how to find something in the
> bundle. That belongs to the reader (`dataiku-diagnosis-reader` skill), which is vendored from
> upstream. If a calibration needs a new "where/how to read" fact, add it to the reader's references
> upstream, re-sync, and point to it from here. See `CLAUDE.md`.

These interpretations come directly from the user and override a literal reading of a checklist's
`expected_value`/evidence text. **Match an entry by what the check is about (its title and statement).**
The item ids cited here are pointers into the bundled default checklist, and a different or newer
checklist may renumber, split, merge or drop checks. The "Check anchors" table at the end records the
title each id had when its entry was written. If a row's id and title disagree with an entry's anchor,
trust the topic, not the id, and say so in `notes`. Never apply an entry to a row just because the id
matches. Add each new one as its own entry under the right heading; don't overwrite prior ones.

## General principles (apply to every check)

- **Judge only what the bundle shows.** An aspect that needs a live check (backups, restore tests, who
  holds an OS identity, a functional export test, run history, an external proxy) goes in `notes` as an
  `Action:`; it never moves the status away from what the bundle's own settings support. Absence of
  run history is the normal state of a bundle, not a gap.
- **Conditional check, precondition unmet: Not Applicable**, not Fail or Needs Review. A missing key is
  a Fail only when the feature is demonstrably in use.
- **An inferred value is not evidence.** Don't mark Pass or Fail from an assumed default (e.g. a
  connection pool against an internal-database limit the bundle doesn't record). Mark **Needs Review**,
  state the inference in `notes` as an inference, and ask for the real value.
- **A hinted setting is not proof of absence.** A `parameter_hint` is a pointer, not a guarantee of
  where the setting lives. Before marking a setting absent or Fail, look for it the way the reader's
  `data-dir-config` reference ("Finding a setting reliably") describes.
- **Version gate beats feature gate.** If the check's stated minimum DSS version is above the bundle's
  `product_version`, mark **Needs Review** (the capability can't exist yet, so Fail would be unfair)
  and name the introducing version in `notes`, even if the feature is also conditional (e.g. Cobuild
  default LLMs, GENAI-007, on an older DSS). Upgrade planning is the actionable point.
- **Optional feature off but the checklist asks for acceptance or enablement (GenAI, graphics export):**
  **Needs Review** (ask whether it is intentional), not Fail. Security controls follow their own entries
  below. A setting or section absent from the bundle is **Needs Review**, never treated as off.

## Kubernetes, containers and Spark

- **Kubernetes-conditional checks in general (ARCH-010, ARCH-013, Spark-on-K8s, containerized execution,
  cluster configuration):** first determine whether a Kubernetes cluster is attached to the instance at
  all (the reader's `data-dir-config` reference says how). None attached: **Not Applicable** for any
  check that depends on Kubernetes/Elastic Compute. Attached: a valid containerized execution
  configuration is a must-have; if none is defined, **Fail**.

- **Spark validation on a non-Kubernetes estate (ARCH-008):** worded for Spark on Kubernetes (executor
  pods). No cluster attached and Spark on YARN/Hadoop: **Not Applicable**, per the rule above.

- **Containerized execution baseline (ARCH-011; e.g. 'Standard' ~200MB/16000MB, 'Webapp' ~500MB/500MB):**
  the checklist's baseline is an illustrative example, not names or sizes to match. **Pass** when there
  are **two or more configs whose memory or CPU requests/limits genuinely differ**, whatever the names.
  If all configs are identically sized despite different names, that is a real gap: say so in `notes`.

- **Spark baseline configs (ARCH-006):** same logic, baseline illustrative. Two or more Spark execution
  configs whose sizing genuinely differs: **Pass**. Only one, or all identically sized: **Partial**.
  None: **Fail**.

- **Per-user Kubernetes namespace (ARCH-007; Spark or containerized configs, e.g. `dss-ns-${dssUserLogin}`):**
  for a **managed** cluster, a namespace parameter provisioned with a dynamic/templated variable (such as
  `${namespace}`) is sufficient: **Pass** (not Needs Review) without tracing the variable, and note the
  field/value seen in `evidence_found`. For a **manual**/externally-registered cluster, namespace
  behaviour may be governed outside DSS, so judge it on its own merits. (The reader's `data-dir-config`
  reference says where the namespace fields live and how to tell managed from manual.)

## GenAI

- **Feature-conditional GenAI checks (Cobuild default LLMs, Bring-your-own-LLM mode, local Hugging Face;
  Agent Hub has its own rule below):** first confirm the feature is in use (the reader's
  `data-dir-config` reference lists the signals it has verified and which it has not). Not in use:
  **Not Applicable**. Turned off but the checklist asks for acceptance or enablement (e.g. AI Services
  terms not accepted while all AI features are disabled): **Needs Review**. For "AI assistant debug data
  in the bundle" checks, a bundle that lacks the section is **Needs Review**, not Fail.

- **Internal code environments for LLM Mesh (GENAI-001; RAG, document extraction, PII detection):** judge
  only whether the internal code envs are in use. Say in `notes` which envs you saw.
  - **Pass:** the defaults are the internal code envs (the reader's `data-dir-config` and
    `data-dir-runtime-and-codeenvs` references say how to tell). Don't downgrade for a container
    execution mode of `INHERIT` when no container config exists, and don't require separate evidence for
    each of the three categories.
  - **Needs Review:** a non-internal code env is used for any of them.
  - **Fail:** nothing is set up.

- **Agent Hub deployer permissions (GENAI-009):** the bundle can't verify who may deploy, so don't infer
  it from the project owner or group grants. Agent Hub installed (the reader's `data-dir-config`
  reference lists the signal): **Needs Review**. Not installed: **Not Applicable**. Never Pass or Fail.

## Security

- **HTTPS (SEC-006):** DSS's own config shows only whether DSS itself terminates TLS; an external
  reverse proxy (nginx, ALB, API gateway) is invisible to the bundle.
  - **Pass:** DSS terminates TLS itself (SSL on and a certificate configured, as the reader's
    `data-dir-identity` reference describes), or the bundle shows a documented proxy setup. Don't
    downgrade because a proxy might also exist. Quote the raw server block in `evidence_found`, so a
    misread is visible.
  - **Needs Review:** DSS is not itself configured for HTTPS (e.g. plain HTTP). Never Fail. One `notes`
    bullet says the bundle can't confirm or rule out a TLS-terminating proxy, plus an `Action:` to verify
    with the customer/infrastructure team.
  - **Fail:** only on positive evidence that no HTTPS exists anywhere (e.g. explicit customer
    confirmation on record), not on absence from the bundle.

- **Session expiry, single session per user, clickable links in data tables (ADVSEC-003, ADVSEC-004,
  ADVSEC-011):** these settings are in the bundle (the reader's `data-dir-config` reference says where),
  so judge them from the value, never Needs Review because a checklist hint calls them UI-only.
  - Timeouts: `0` means unlimited. **Fail** when both are `0`; **Pass** when either is finite.
  - Single-session or disable-links toggle: off is **Fail**, on is **Pass**.
  - **Needs Review** only when the settings block itself is missing.

- **Custom post-logout redirect (ADVSEC-006):** optional hardening; the default logout page is not a
  security concern. None configured: **Not Applicable** (say the default page is in use). Valid
  http/https redirect: **Pass**. **Fail** only when one is configured but invalid.

- **UIF (SEC-002):** impersonation enabled with at least one user or group rule (the reader's lookup
  table says where): **Pass**. Whether the OS identities exist is a live check (`notes` only).
  Disabled: **Fail**.

- **cgroups memory limit (SEC-004):** the recommended cap depends on host RAM, so judge the limit against
  its tier, not a flat percentage. Host RAM `R` is `MemTotal` in GiB and the cap `L` is the memory cgroup
  limit in GiB (the cgroup "G" is GiB; never mix GB and GiB). Quote the percentage from the reader's
  `facts.py`. The checklist's tiers give the recommended cap `T`:

  | Host RAM | Recommended cap `T` |
  |---|---|
  | over 120 GiB | 75% of `R` |
  | 60-120 GiB | 66% of `R` |
  | 30-60 GiB | `R` minus 20 GiB |
  | under 30 GiB | 50% of `R` |

  - **Disabled:** **Fail**. Cgroup settings missing from the bundle: **Needs Review**.
  - **`L` is 80% of `R` or more:** **Needs Review**, naming the risk of over-allocating memory to cgroups
    (too little left for the OS and DSS's own processes). Check this first; it overrides the band below.
  - **`L` within 10% of `T`** (either side): **Pass**, including slightly above `T`.
  - **`L` more than 10% away from `T`, or enabled with no memory limit:** **Needs Review** (ask whether
    it is intentional).
  - In `notes`, give the percentage and tier, e.g. `190G = 75.7% of 251 GiB; tier target 75%`. Empty
    per-workload placements are a `notes` observation, not a downgrade.

- **Export restriction (ADVSEC-008):** the check lists alternative keys (`one_of`), so any one set to
  true is **Pass**; the others (e.g. clipboard keys) are `notes` only. None set: **Fail**.

- **Security HTTP headers (ADVSEC-009):** none of the listed headers configured in DSS: **Fail**. Some
  but not all: **Partial**. All with restrictive values: **Pass**. In `notes`, say a proxy may set them
  (the bundle can't show that).

## Platform, sizing and runtime

- **Backend Xmx sizing (SCALE-008):** apply the full rule from the checklist, not just the RAM tier.
  Check all of: (1) `backend.xmx` against the RAM tier; (2) `backend.xmx` >= 3x the size of the
  `config/` folder (the reader's `listings-and-manifests` reference says how to size it); (3) not in the
  32-48GB dead zone; (4) the other components' heaps (`jek.xmx`/`fek.xmx`) not oversized; (5) no
  `OutOfMemoryError` in the backend logs. State which you checked in `evidence_found`; never assume a
  tier from RAM alone.

- **Flow limits sizing (SCALE-009):** a concurrency or sizing limit that sits in a different place than
  its name suggests still counts. A value of `0` means unsized: **Fail**, even when the other
  concurrency limit is in range.

- **Connection-detail gaps (SCALE-012):** gaps DSS itself flagged are real evidence. Report **Partial**
  rather than Not Applicable just because the storage is HDFS and not a cloud object store.

- **Log-error review (SCALE-007):** the status is mechanical, so every run gives the same one:
  - Any ERROR, FATAL or WARN entries in the backend logs: **Needs Review**, however few or benign-looking.
    Never Fail or Partial.
  - No errors and no warnings at all: **Pass**.
  - Logs missing from the bundle: **Needs Review** (the checklist's `insufficient_evidence_handling`).

  Still make the finding useful. The bundle usually holds only a few hours of backend log, so quote
  counts with their window (e.g. `214 in ~2.6h`) in both `evidence_found` and `notes`, and group by
  message pattern (digits and ids normalised), not by raw line. When one pattern dominates (e.g. repeated
  rejected WebSocket sessions that were not logged in), say so in `notes` with its share, and put the
  `Action:` on the real failures (e.g. failing API calls). The reader's `data-dir-runtime-and-codeenvs`
  reference says how to count and get the window.

- **External PostgreSQL runtime database (SCALE-001):** judge the internal database's type and host (the
  reader's `data-dir-config` reference says where). PostgreSQL on a non-local host: **Pass**. On the same
  host (loopback or the DSS host itself): **Partial**. Not PostgreSQL: **Fail**. Pool size against
  `max_connections` and backups are `notes` only.

- **Metastore (SCALE-002) and graphics export (SCALE-003):** decide from the setting, never Needs Review
  for want of a functional test.
  - **Metastore** (the reader's lookup table says where the flavor lives): **Pass** when it matches the
    estate (Hive on a Hadoop/YARN estate, Glue on AWS, DSS internal otherwise); **Needs Review** only
    when the estate can't be told.
  - **Graphics export:** on is **Pass**; off is **Needs Review** (ask if intentional); setting absent
    from the bundle is **Needs Review**, never off.

- **Admin project garbage collection (SCALE-004):** there is no fixed project name; the reader's lookup
  table says how to find candidate projects and read their scenarios. Judge only scenarios that are
  active with an active trigger. Never open or grep the script behind a Python-based scenario.
  - **Pass:** an active scheduled step-based scenario whose steps clearly clear logs, purge, delete or
    clean up.
  - **Needs Review:** an active scheduled scenario whose purpose is only inferable from its name or that
    runs a script (say in `notes` the script was not read); or a candidate project with scenarios but
    none both active and scheduled.
  - **Fail:** no candidate project, or one whose scenarios are all inactive or absent.

  Run history, whether the cleanup actually runs, and whether it covers logs, idle kernels or both are
  `notes` only.

## Architecture and version

- **Automation-node existence / Design-Automation separation (ARCH-001), on a design-node bundle:** the
  automation node is a separate host with its own bundle, so a design bundle can never confirm one
  exists. Always **Needs Review**, never Pass or Fail. Use the reader's `node-types` and
  `data-dir-config` (deployer) references to find indicators; work through them in this order and
  report what you find:
  1. **Local Project Deployer on the design host:** one holding projects to deploy to an automation node
     indicates an automation node is in use. Enumerate what it holds (infrastructures, deployments,
     published projects, any automation-node URLs). **Put this indication, with counts, in the headline
     of `notes`** and list the URLs and enumeration in `evidence_found`. Distinguish a populated deployer
     (strong indication) from one present but empty (enabled, no sign of use). A local API Deployer
     targets API nodes: mention it separately as an API-node indication, not as evidence of an automation
     node.
  2. **Remote deployer:** a design node pushing to an external Deployer URL suggests Design -> Deployer ->
     Automation, but any automation infrastructure is defined on that node, not in this bundle. Exported
     project bundles are weak supporting evidence either way.
  3. **Otherwise:** state in `notes` that no definitive configuration in the bundle shows whether an
     automation node is deployed, and that it needs verification with the customer.

- **DSS version currency (ARCH-002):** look up the current GA release at run time, then compare the
  bundle's DSS `product_version` (the reader's `data-dir-identity` reference says where it is) against the
  latest GA's **major** version only:
  - Same major (e.g. bundle 14.x, latest GA 14.x, any minor/patch): **Pass**.
  - Bundle's major is behind: **Needs Review** (not Fail); a major gap warrants a human look at upgrade
    planning.
  - Lookup failed, returned nothing usable, or no web search tool is available: **Needs Review**. Never
    guess from prior knowledge; say in `notes` that currency could not be verified.

  State the bundle's version, the latest GA version, its release date if known, and how many majors
  behind (0 if current). Keep `notes` short (e.g. `Bundle 13.x vs latest GA 14.x (date) — 1 major
  behind`); put the full source citation in `evidence_found`.

  **Lookup procedure:** use the **extended** web-search mode every run (a standard search can miss a
  newer major). Search "Dataiku DSS latest version release notes", then once more for the next major above
  the one found (e.g. "Dataiku DSS 15 release notes"). Take the highest GA version confirmed by an
  official Dataiku source (release notes, changelog, docs.dataiku.com). If results are links only,
  `WebFetch` the official release-notes page for the newest major. Never answer from training knowledge.

## Check anchors

The title each cited id had in the bundled default checklist when its entry was written.
`tests/test_calibration_ids.py` fails when the checklist no longer matches this table; update the entry
and the row together.

| Id | Title when written |
|---|---|
| ADVSEC-003 | Expiring sessions |
| ADVSEC-004 | Forcing a single session per user |
| ADVSEC-006 | Redirecting to a custom URL after logout |
| ADVSEC-008 | Restricting exports |
| ADVSEC-009 | Setting security-related HTTP headers |
| ADVSEC-011 | Preventing links to be clickable in data tables |
| ARCH-001 | Separation of Design and Automation Nodes |
| ARCH-002 | Regular DSS Version Upgrades |
| ARCH-006 | Baseline Spark Configuration Set (High/Standard/Large-memory/High I/O) |
| ARCH-007 | Kubernetes Namespace and Auth Recommendations for Spark |
| ARCH-008 | Functional Validation of Spark Execution (Recipe & Notebook) |
| ARCH-010 | Valid Containerized Execution Configuration |
| ARCH-011 | Baseline Container Execution Configs (Standard, Webapp) and Namespace Settings |
| ARCH-013 | Valid Cluster Configuration for Elastic Compute |
| GENAI-001 | Internal Code Environments for RAG, Document Extraction, PII Detection |
| GENAI-007 | Cobuild Default LLM Configuration |
| GENAI-009 | Agent Hub Deployment Required Permissions |
| SCALE-001 | External PostgreSQL Runtime Database |
| SCALE-002 | Appropriate Metastore Configured |
| SCALE-003 | Graphics Export (PDF/Image) Configuration |
| SCALE-004 | Admin Project for Garbage Collection |
| SCALE-007 | Backend.log Error Review |
| SCALE-008 | Backend Xmx Sizing |
| SCALE-009 | Flow Limits Sizing (Max Jobs, Max Activities) |
| SCALE-012 | Cloud Object Storage Configuration (Details Readable By, HDFS Interface) |
| SEC-002 | User Isolation Framework (UIF) Enabled with Appropriate Impersonation Rules |
| SEC-004 | CGroups Enabled with Memory Limit per Sizing Heuristic |
| SEC-006 | HTTPS Access Configured for DSS |
