# Known check-specific calibrations

> Interim: some bundle key locations are quoted below because the wording depends on them. How to
> read the bundle belongs to the reader; see `docs/upstream-reader-spec.md` for what is moving there.

Apply these interpretations consistently. They come directly from the user,
supersede a literal reading of the checklist's `expected_value`/evidence
text, and should be extended here over time whenever the user gives another
one — add each as its own bullet rather than overwriting prior ones.

- **Kubernetes-conditional checks in general (Spark-on-K8s, containerized
  execution, cluster configuration, etc.):** first determine whether a
  Kubernetes cluster is actually attached to the instance at all (see
  `config/clusters/` and `defaultK8sClusterId`; the reader's `data-dir-config` reference covers them). If no
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
  memorized/training-time knowledge of "the latest version"). Use the
  **extended** search mode: a standard search can return a stale answer and
  miss a newer major (a standard search once reported 14.7.2 when DSS 15.0.2
  was already out). Search for "Dataiku DSS latest version release notes",
  then run a second search for the next major above the one you found
  (e.g. "Dataiku DSS 15 release notes"); take the highest GA version
  confirmed by an official Dataiku source (release notes / changelog /
  docs.dataiku.com). Never answer from a single standard search. Compare the bundle's `product_version` (from `dss-version.json`,
  format `MAJOR.MINOR.PATCH`) against the latest GA version's major version
  number only, and apply this fixed internal rule:
  - If the bundle's **major** version matches the current major release
    (e.g. bundle is 14.x and the latest GA is also 14.x, regardless of minor
    or patch), mark **Pass**.
  - If the bundle's major version is behind the current major release (e.g.
    bundle is 13.x while latest GA is 14.x), mark **Needs Review** (not
    Fail) — a major-version gap warrants a human look at upgrade planning
    rather than an automatic fail.
  In both cases, state the bundle's version, the latest GA version found, its
  release date if available, and how many major versions behind (0 if
  current). Keep `notes` short (e.g. `Bundle 13.x vs latest GA 14.x (date) —
  1 major behind`) and put the full source citation in `evidence_found`. If an
  extended search returns only links with no content, `WebFetch` the official release-notes page for
  the newest major instead of retrying the search. If
  the web search fails, returns nothing usable, or no web search tool is
  available in this session, do not guess or fall back to prior/training
  knowledge of the latest version — set `notes` to state plainly that
  currency could not be verified against Dataiku's current release
  information (web lookup failed/unavailable) and mark the item **Needs
  Review**.

- **Feature-conditional GenAI checks (Cobuild default LLMs, Agent Hub
  permissions / service account / impersonation groups, Bring-your-own-LLM
  mode, local Hugging Face):** first confirm the feature is actually in use
  (e.g. no `agentBuildingSettings`, no Agent Hub projects/webapps, all
  `localAIServerSettings.*UseLocal` false, no INTERNAL_huggingface code env).
  If it isn't, mark the check **Not Applicable**, not Fail or Needs Review. A
  missing key is only a Fail when the feature is demonstrably in use. When a
  setting is turned off but the checklist asks for acceptance or enablement
  (e.g. AI Services terms not accepted while all AI features are disabled),
  use **Needs Review** and ask whether it is intentional. For "AI assistant
  debug data in the bundle" checks, a bundle that simply lacks the section is
  **Needs Review**, not Fail.

- **Backend Xmx sizing (e.g. "SCALE-008"):** apply the full rule from the checklist, not just the
  RAM tier. Check all of: (1) `backend.xmx` against the RAM tier; (2) `backend.xmx` >= 3x the size
  of the `config/` folder (`du -sh` it, or sum `datadir_listing.txt`); (3) it is not in the
  32-48GB dead zone; (4) `jek.xmx`/`fek.xmx` are not oversized; (5) no `OutOfMemoryError` in the
  backend logs. State which of these you checked in `evidence_found`; never assume a tier from RAM
  alone.

- **Log-error review (e.g. "SCALE-007"):** the bundle usually holds only a few hours of backend
  log. Quote counts with their window (e.g. `214 in ~2.6h`) in both `evidence_found` and `notes`,
  and group by message pattern (digits and ids normalised), not by raw line.

- **Not Applicable headlines:** write one clean reason, not a chain of colons. Use
  `Not applicable: <reason>` (e.g. `Not applicable: no local Hugging Face`), not
  `Not applicable: AI feature not in use: no local Hugging Face`.

- **Reading a hinted setting:** a checklist `parameter_hint` is a pointer,
  not a guarantee of the exact path. Before marking a setting absent or Fail,
  search the whole `general-settings.json` for the leaf key (e.g.
  `traceExplorerDefaultWebApp` lives under `generativeAISettings.llmTraceSettings`,
  not at the top level). Likewise a concurrency or sizing limit stored under a
  different block (e.g. `jekSettings.maxRunningJobs`) still counts: a value of
  `0` means unsized and is a **Fail** for "Flow Limits Sizing", even when
  `maxRunningActivities` is in range. Connection-detail findings from
  `sanity-check.json` (e.g. HDFS/Spark connections with no group allowed to read
  details) are real evidence for connection-details checks: report them
  **Partial** rather than Not Applicable just because the storage is HDFS and
  not a cloud object store.

- **HTTPS enforcement check (e.g. "SEC-006", especially for custom/on-prem
  installs):** `install.ini` and DSS's own config only show whether DSS
  itself is terminating TLS. They cannot show whether an external reverse
  proxy (nginx, an ALB/load balancer, an API gateway, etc.) sits in front of
  DSS and terminates HTTPS there instead — that setup is invisible to the
  diagnosis bundle. So: if the bundle shows DSS is *not* itself configured
  for HTTPS (e.g. plain HTTP in `install.ini`), do not mark this **Fail**.
  Mark it **Needs Review** instead, and in `notes` state plainly, in one
  bullet, that the bundle cannot confirm or rule out an external reverse
  proxy terminating HTTPS in front of DSS, with an `Action:` bullet to verify
  it directly with the customer/infrastructure team before treating it as a
  real gap. Only
  mark **Pass** when the bundle shows positive evidence HTTPS is enforced
  somewhere in the path (DSS-terminated or a documented proxy setup
  referenced in the bundle); only mark **Fail** if there is positive
  evidence no HTTPS exists anywhere (e.g. explicit customer confirmation on
  record, not just absence from the bundle).

- **Automation-node existence / Design–Automation separation (e.g.
  "ARCH-001"), when reviewing a design-node bundle** (`install.ini` →
  `nodetype = design`): the automation node is a separate host with its own
  bundle, so a design-node bundle can never definitively confirm one exists.
  Always mark this **Needs Review**, never Pass or Fail from the design
  bundle alone. Work through the indicators in this order and report what
  you find:
  1. **Local deployer on the design host:** if `<mirror>/config/project-deployer/`
     and/or `<mirror>/config/api-deployer/` are present (also check
     `datadir_listing.txt`, since the mirror may not copy these subtrees),
     a deployer is configured locally. `project-deployer/` holds projects to
     deploy onto an automation node — an indication an automation node is in
     use. Enumerate its contents (`infras/*.json` and any automation node
     URLs they point to, `deployments/*.json`, published projects) and
     **highlight this indication prominently in the headline of `notes`**
     with the counts, and list the URLs and enumeration in `evidence_found`.
     Distinguish a populated
     deployer (infras + deployments present — strong indication) from one
     that is present but empty (deployer enabled, no sign of actual use).
     `api-deployer/` holds API services to deploy onto an API node — mention
     it separately as an API-node indication, not as evidence of an
     automation node.
  2. **Remote deployer:** if `general-settings.json` →
     `deployerClientSettings.mode` is `REMOTE` (pointing at an external
     Deployer URL), highlight that the design node pushes to a separate
     Deployer node — suggestive of a Design → Deployer → Automation setup,
     but any automation infrastructure is defined on that node, not in this
     bundle. Exported bundles under `DATA_DIR/bundles/<PROJECT>/` (via
     `datadir_listing.txt`) are weak supporting evidence either way.
  3. **Otherwise:** state in `notes` that there is no definitive
     configuration in the bundle indicating whether an automation node is
     deployed, and that this needs further verification with the customer.
