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

**Entries marked `[code-decided]`** have their status computed by `scripts/run_step.py verdicts` (rules in
`scripts/rules_security.py`; SKILL.md, Verdicts). Use the verdict's status exactly; the entry then explains the rule and
holds the `Action:` guidance for `notes`. The rule and its entry must agree: a change to one is a change to the other.

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

- **Internal code environments for LLM Mesh (GENAI-001; RAG, document extraction, PII detection) [code-decided]:** judge
  only whether the internal code envs are in use. Say in `notes` which envs you saw.
  - **Pass:** the defaults are the internal code envs (the reader's `data-dir-config` and
    `data-dir-runtime-and-codeenvs` references say how to tell). Don't downgrade for a container
    execution mode of `INHERIT` when no container config exists, and don't require separate evidence for
    each of the three categories.
  - **Needs Review:** a non-internal code env is used for any of them.
  - **Fail:** nothing is set up (no default env for retrieval or PII detection). The GenAI settings missing from the bundle altogether: Needs Review.
  - Decided from `facts.py`'s `genai_settings` (retrieval and PII detection envs; document extraction has no env of its own).

- **Trace Explorer (GENAI-003) [code-decided]:** the default project and web app both set (`trace_explorer`
  configured): **Pass**. The block present but no default set: **Fail**. The block missing from the bundle: **Needs Review**.

- **AI Services (GENAI-004) [code-decided]:** terms accepted and at least one AI Services flag on (`genai_settings`): **Pass**.
  Terms not accepted, or accepted with nothing enabled, or the flag missing: **Needs Review** (an optional feature; ask whether
  it is intentional), never Fail. Outbound connectivity to the AI gateway can't be verified from a bundle.

- **Cobuild default LLMs (GENAI-007) [code-decided]:** all three default ids set (`genai_settings.cobuild_default_llms_set`):
  **Pass**. Any unset, or the block missing (DSS before the Cobuild settings, or Cobuild never used): **Needs Review**, naming
  the unset ids. Whether Cobuild is in use isn't verified, so this is never Fail or Not Applicable.

- **Bring Your Own LLM (GENAI-005, GENAI-006) [code-decided]:** BYO mode counts as active only when `facts.py`'s `byo_llm`
  reports `active: true` (a main LLM id or a reference project key is set). A custom LLM connection alone does
  not make it active. Inactive (or the block missing): **Not Applicable** for both.
  - **GENAI-005:** active with both the reference project key and a main LLM set: **Pass**; either missing: **Fail**.
  - **GENAI-006:** judge the model ids `byo_llm` reports. A recommended version (OpenAI ChatGPT 5.2 or later):
    **Pass**; a known unsupported one (ChatGPT 5.1 or earlier): **Fail**; non-OpenAI, ambiguous or
    undeterminable: **Needs Review** (name the id in `notes`). Applied to every LLM id reported (main, response-format-aware,
    fast/light): any unsupported one is Fail, else any undeterminable one is Needs Review. A `gpt-5` without a minor number counts as 5.0.

- **Agent Hub deployer permissions (GENAI-009) [code-decided]:** the bundle can't verify who may deploy, so don't infer
  it from the project owner or group grants. Agent Hub installed (the reader's `data-dir-config`
  reference lists the signal): **Needs Review**. Not installed (or no plugin configuration in the bundle at all): **Not Applicable**. Never Pass or Fail.

## Security

- **Security toggles in the `security` settings block (ADVSEC-001, ADVSEC-002, ADVSEC-005, ADVSEC-010, ADVSEC-012, SEC-007)
  [code-decided]:** judge each from its value (`facts.py`, `security_settings`). A secure toggle that is on is **Pass**; one that
  is off is **Fail** (ADVSEC-001 hide error stacks, ADVSEC-002 hide version info). Where the checklist itself allows a
  deliberate choice, a deviation is **Needs Review** (ask for the documented need): ADVSEC-005 (restricted visibility off),
  ADVSEC-012 (users may edit their name and email), SEC-007 (secure cookies off: only safe once all access is HTTPS, which a
  proxy can hide). ADVSEC-010: iframe hosting off (`sameSiteNoneCookies` false) is **Pass**; on with secure cookies off is **Fail**
  (the checklist requires them together); on with secure cookies on is **Needs Review**. A setting or the block missing from the
  bundle is **Needs Review**.

- **HTTPS (SEC-006) [code-decided]:** DSS's own config shows only whether DSS itself terminates TLS; an external
  reverse proxy (nginx, ALB, API gateway) is invisible to the bundle.
  - **Pass:** DSS terminates TLS itself (SSL on and a certificate configured; `facts.py`, `server_config`). Don't
    downgrade because a proxy might also exist. A proxy documented elsewhere in the bundle is not something the code
    reads: it stays Needs Review, with the `Action:` below. Quote the raw server block in `evidence_found`, so a
    misread is visible.
  - **Needs Review:** DSS is not itself configured for HTTPS (e.g. plain HTTP). Never Fail. One `notes`
    bullet says the bundle can't confirm or rule out a TLS-terminating proxy, plus an `Action:` to verify
    with the customer/infrastructure team.
  - **Fail:** only on positive evidence that no HTTPS exists anywhere (e.g. explicit customer
    confirmation on record), not on absence from the bundle.

- **Session expiry, single session per user, clickable links in data tables (ADVSEC-003, ADVSEC-004,
  ADVSEC-011) [code-decided]:** these settings are in the bundle (the reader's `data-dir-config` reference says where),
  so judge them from the value, never Needs Review because a checklist hint calls them UI-only.
  - Timeouts: `0` means unlimited. **Fail** when both are `0`; **Pass** when either is finite.
  - Single-session or disable-links toggle: off is **Fail**, on is **Pass**.
  - **Needs Review** only when the settings block itself is missing.

- **Wiki upload restriction (ADVSEC-007) [code-decided]:** an upload-extension list configured: **Pass**. None configured
  (including a bundle without the instance's properties file, which means nothing was customised): **Fail**, because the default allows
  any file type.

- **Custom post-logout redirect (ADVSEC-006) [code-decided]:** optional hardening; the default logout page is not a
  security concern. None configured: **Not Applicable** (say the default page is in use). Valid
  http/https redirect: **Pass**. **Fail** only when one is configured but invalid.

- **Instance identification (SEC-001) [code-decided]:** **Pass** when the node's instance (install) id is present in the
  bundle (the reader's `facts.py` reports it under `node`); **Fail** when it is missing. Whether it
  matches a customer inventory or tracking tool is a live check: an `Action:` in `notes`, never the status.

- **LDAP authorized groups (SEC-009) [code-decided]:** conditional on LDAP being enabled (`facts.py`, `sso_and_ldap`).
  Enabled with one or more authorized groups: **Pass** (give the count, never the names). Enabled with
  none: **Fail**. LDAP not enabled: **Not Applicable**.

- **SSO enablement (SEC-010) [code-decided]:** judge from `facts.py` `sso_and_ldap` (SSO and LDAP enabled flags; give the
  protocol, never any secret). Check in this order: SSO disabled: **Fail** (whatever LDAP is), with an
  `Action:` in `notes` to discuss the benefits of SSO with the customer. SSO and LDAP both enabled: **Pass**.
  SSO enabled but LDAP disabled, or either setting missing from the bundle: **Needs Review**.

- **UIF (SEC-002) [code-decided]:** impersonation enabled with at least one user or group rule (the reader's lookup
  table says where): **Pass**. Whether the OS identities exist is a live check (`notes` only).
  Disabled: **Fail**. Enabled but with no user or group rule: **Partial**. The enabled flag missing from the bundle:
  **Needs Review**.

- **JEK-specific cgroup limits (SEC-005) [code-decided]:** the check wants none configured. From `facts.py`'s `cgroups`,
  `target_counts` gives the cgroup targets configured per workload category. The Job Execution Kernel (JEK) category
  with 0 targets, or no JEK category at all: **Pass**. One or more JEK targets configured: **Fail**, even when cgroups are disabled overall. The cgroup settings missing
  from the bundle: **Needs Review**. Whether the live OS hierarchy matches is an `Action:` in `notes`, never the status.

- **cgroups memory limit (SEC-004) [code-decided]:** the recommended cap depends on host RAM, so judge the limit against
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

- **Export restriction (ADVSEC-008) [code-decided]:** the check lists alternative keys (`one_of`), so any one set to
  true is **Pass**; the others (e.g. clipboard keys) are `notes` only. None set: **Fail**.

- **Security HTTP headers (ADVSEC-009) [code-decided]:** none of the ten listed headers configured in DSS: **Fail**.
  Pass needs the six core headers set with restrictive values: content-security-policy (non-empty), x-frame-options
  (SAMEORIGIN or DENY), x-content-type-options (nosniff), x-xss-protection (set and not `0`), hsts-max-age (above 0) and
  referrer-policy (non-empty). Some header set but not all six core ones restrictive: **Partial**. The other four
  (permissions-policy and the three cross-origin ones) are `notes` only. In `notes`, say a proxy may set them
  (the bundle can't show that).

## Platform, sizing and runtime

- **Remove the `filesystem_root` connection (SCALE-011) [code-decided]:** the default connection pointing at the server's root
  filesystem is still present: **Fail** (whether a project uses it is a live check: an `Action:` in `notes`, never the
  status). Absent: **Pass**. The connections list missing from the bundle: **Needs Review**.

- **Backend Xmx sizing (SCALE-008):** apply the full rule from the checklist, not just the RAM tier.
  Check all of: (1) `backend.xmx` against the RAM tier; (2) `backend.xmx` >= 3x the size of the
  `config/` folder (use `facts.py`'s `config_folder_size`, which sums the listing; never size it from the partial mirror); (3) not in the
  32-48GB dead zone; (4) the other components' heaps (`jek.xmx`/`fek.xmx`) not oversized; (5) no
  `OutOfMemoryError` in the backend logs. State which you checked in `evidence_found`; never assume a
  tier from RAM alone.

- **Flow limits sizing (SCALE-009) [code-decided]:** a concurrency or sizing limit that sits in a different place than
  its name suggests still counts. A value of `0` (or blank) means unsized: **Fail**, even when the other
  concurrency limit is in range. None is 0 but max activities is outside 30-50 or activities per job is not 5:
  **Needs Review** (ask whether the sizing is justified). All three in range: **Pass**. A limit missing from the bundle:
  **Needs Review**.

- **Preferred connections and engines (SCALE-010):** the check wants the default dataset-creation
  connection, upload connection, storage formats and recipe engine preferences left blank unless a use case
  justifies them (`facts.py`, `default_preferences`). Any of them non-blank: **Needs Review** (ask whether it
  is intentional; name the values in `notes`, and call a non-blank engine preference the riskier one).
  All blank or absent: **Pass**.

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

- **External PostgreSQL runtime database (SCALE-001) [code-decided]:** judge the internal database's type and host (the
  reader's `data-dir-config` reference says where). PostgreSQL on a non-local host: **Pass**. On the same
  host (loopback): also **Pass**, with a `notes` bullet saying it is installed locally on the DSS host (a backup and
  availability caveat, not a status change). Not PostgreSQL: **Fail**. Pool size against
  `max_connections` and backups are `notes` only.
  When `facts.py`'s `internal_database` reports `password_stored_in_plaintext: true`, `notes` carries
  `Action: rotate the stored database credential and move it to a secrets store` (never the value). It does
  not change the status. False or ABSENT: add nothing.

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

- **SSD storage (ARCH-004) [code-decided]:** decide from the host's disks, because DSS's own sanity check may be missing
  from the bundle. Use the reader's `data_volume_device` fact: every disk behind the data directory
  non-rotational: **Pass**; any rotational: **Fail**; the fact is `ABSENT` (data directory, disk listing or
  matching mount not found): **Needs Review**. DSS's own sanity check flagging a rotational disk is also
  **Fail**; its absence is not evidence either way. Name the data directory and disk(s) in `evidence_found`.
  The verdict combines both: a sanity-check message whose code mentions rotational, HDD or SSD is **Fail** (even when the
  disks could not be read); otherwise any rotational disk is **Fail**, every disk non-rotational is **Pass**, and disks
  unknown is **Needs Review**. Only a `facts.py` without message codes leaves the row `undecided`: read the sanity-check
  text and decide as above.


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

- **Instance sanity check (SCALE-006) [code-decided]:** a presence check only. From `facts.py`'s `sanity_check`: output in
  the bundle with at least one message (`empty: false`): **Pass** (give the message counts in `notes`; the
  warnings it lists are judged by the checks they relate to, not here). Output missing (`ABSENT`) **or empty**
  (`empty: true`, a blank file or no messages): **Fail**. Never Partial or Needs Review.

- **Supported operating system (ARCH-003):** take the OS name and version from the bundle (the reader's
  `root-files` reference says where) and compare them with Dataiku's supported-OS documentation for the
  bundle's DSS **major** version, using the same web lookup as ARCH-002 (official Dataiku docs only, never prior
  knowledge). Listed: **Pass** (mention a deprecation notice in `notes` if the page has one). Not listed:
  **Fail**. Lookup failed or unavailable, or the OS isn't captured: **Needs Review**. Name the OS, the DSS
  major and the page consulted in `evidence_found`.

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
| ADVSEC-001 | Hiding error stacks |
| ADVSEC-002 | Hiding version info |
| ADVSEC-003 | Expiring sessions |
| ADVSEC-004 | Forcing a single session per user |
| ADVSEC-005 | Restricting visibility of groups and users |
| ADVSEC-006 | Redirecting to a custom URL after logout |
| ADVSEC-007 | Restricting types of files that can be uploaded in wikis |
| ADVSEC-008 | Restricting exports |
| ADVSEC-009 | Setting security-related HTTP headers |
| ADVSEC-010 | Allowing DSS to be hosted inside an iframe |
| ADVSEC-011 | Preventing links to be clickable in data tables |
| ADVSEC-012 | Allowing DSS users to edit their display names and emails |
| ARCH-001 | Separation of Design and Automation Nodes |
| ARCH-002 | Regular DSS Version Upgrades |
| ARCH-003 | Supported Operating System Version |
| ARCH-004 | SSD Storage for DSS |
| ARCH-006 | Baseline Spark Configuration Set (High/Standard/Large-memory/High I/O) |
| ARCH-007 | Kubernetes Namespace and Auth Recommendations for Spark |
| ARCH-008 | Functional Validation of Spark Execution (Recipe & Notebook) |
| ARCH-010 | Valid Containerized Execution Configuration |
| ARCH-011 | Baseline Container Execution Configs (Standard, Webapp) and Namespace Settings |
| ARCH-013 | Valid Cluster Configuration for Elastic Compute |
| GENAI-001 | Internal Code Environments for RAG, Document Extraction, PII Detection |
| GENAI-003 | Trace Explorer Default Configuration |
| GENAI-004 | AI Services Terms of Use Acceptance & Enablement |
| GENAI-005 | Bring Your Own LLM Mode - Reference Project & Main Model |
| GENAI-006 | Bring Your Own LLM - Recommended Model Versions |
| GENAI-007 | Cobuild Default LLM Configuration |
| GENAI-009 | Agent Hub Deployment Required Permissions |
| SCALE-001 | External PostgreSQL Runtime Database |
| SCALE-002 | Appropriate Metastore Configured |
| SCALE-003 | Graphics Export (PDF/Image) Configuration |
| SCALE-004 | Admin Project for Garbage Collection |
| SCALE-006 | Usage of Instance Sanity Check |
| SCALE-007 | Backend.log Error Review |
| SCALE-008 | Backend Xmx Sizing |
| SCALE-009 | Flow Limits Sizing (Max Jobs, Max Activities) |
| SCALE-010 | Preferred Connections and Engines Settings |
| SCALE-011 | Remove filesystem_root Connection |
| SCALE-012 | Cloud Object Storage Configuration (Details Readable By, HDFS Interface) |
| SEC-001 | Verify/Capture Instance IDs |
| SEC-002 | User Isolation Framework (UIF) Enabled with Appropriate Impersonation Rules |
| SEC-004 | CGroups Enabled with Memory Limit per Sizing Heuristic |
| SEC-005 | JEK-Specific CGroup Limits Left Unconfigured |
| SEC-006 | HTTPS Access Configured for DSS |
| SEC-007 | Secure Cookies Enabled (security.secureCookies) |
| SEC-009 | LDAP Authorized Groups Configured |
| SEC-010 | SSO Enablement Reviewed |
