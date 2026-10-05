# Known check-specific calibrations

> Judgment only: this file says which status to give, never where or how to find something in the
> bundle. That belongs to the reader (`dataiku-diagnosis-reader` skill), which is
> vendored from upstream. If a calibration needs a new "where/how to read" fact, add it to the
> reader's references upstream, re-sync, and point to it from here. See `CLAUDE.md`.

Apply these interpretations consistently. They come directly from the user,
supersede a literal reading of the checklist's `expected_value`/evidence
text, and should be extended here over time whenever the user gives another
one — add each as its own bullet rather than overwriting prior ones.

- **Kubernetes-conditional checks in general (Spark-on-K8s, containerized
  execution, cluster configuration, etc.):** first determine whether a
  Kubernetes cluster is actually attached to the instance at all (the reader's
  `data-dir-config` reference says how to tell). If no
  cluster is attached, mark any check that depends on Kubernetes/Elastic
  Compute as **Not Applicable** rather than Fail or Needs Review — these
  checks are only relevant once a cluster is attached. Once a cluster *is*
  attached, a valid containerized execution configuration must be present —
  treat that as a must-have: if none is defined, mark the check **Fail**.

- **Recommended containerized execution config baseline (e.g. a 'Standard'
  config at ~200MB/16000MB and a 'Webapp' config at ~500MB/500MB, or similar
  named/sized baselines):** treat any such baseline given in the checklist's
  `expected_value`/`supporting_evidence` as an illustrative example, not a
  literal instruction to match names or exact sizes. It is sufficient to see
  **two or more containerized execution configs whose memory or CPU
  requests/limits genuinely differ** (showing an intent to size workloads
  differently) — mark this **Pass**
  even when the config names and exact memory figures don't match the
  baseline example. Still call out in `notes` if all configs are actually
  identically sized despite different names (that remains a real gap, as
  distinct from just not matching the example's naming/numbers).

- **Spark and containerized-execution per-user Kubernetes namespace checks**
  (e.g. items about a "per-user namespace pattern", `dss-ns-${dssUserLogin}`,
  or similar, for either Spark configs or containerized execution configs):
  it is sufficient evidence of compliance to see the namespace parameter
  provisioned with a dynamic/templated variable (such as `${namespace}`),
  **for a managed Kubernetes cluster attached to the Dataiku instance**. Do
  not require tracing the variable to confirm it literally resolves to the
  `dss-ns-${dssUserLogin}` string — mark the item **Pass** (not Needs
  Review) once a templated/dynamic namespace variable is present, and note
  in `evidence_found` which field/value was seen. This calibration applies
  specifically to a **managed** cluster (Dataiku-provisioned/managed). For a
  **manual**/externally-registered cluster, namespace behavior may be
  governed outside DSS configuration entirely — keep judging that case on its
  own merits rather than applying this shortcut. (The reader's
  `data-dir-config` reference says where the namespace fields live and how
  to tell managed from manual.)

- **Dataiku DSS version currency check (e.g. "DSS Version Currency"):** look up the current GA
  release at run time (see the SKILL's "Version-currency lookup"), then compare the bundle's DSS
  `product_version` (the reader's `data-dir-identity` reference says where it is) against the latest
  GA's **major** version only:
  - Same major (e.g. bundle 14.x, latest GA 14.x, any minor/patch): **Pass**.
  - Bundle's major is behind: **Needs Review** (not Fail) — a major gap warrants a human look at
    upgrade planning.
  - Lookup failed, returned nothing usable, or no web search tool is available: **Needs Review**.
    Never guess from prior knowledge; say in `notes` that currency could not be verified.
  State the bundle's version, the latest GA version, its release date if known, and how many majors
  behind (0 if current). Keep `notes` short (e.g. `Bundle 13.x vs latest GA 14.x (date) — 1 major
  behind`); put the full source citation in `evidence_found`.

- **Feature-conditional GenAI checks (Cobuild default LLMs, Agent Hub
  permissions / service account / impersonation groups, Bring-your-own-LLM
  mode, local Hugging Face):** first confirm the feature is actually in use
  (the reader's `data-dir-config` reference lists the signals it has verified
  and which it has not). If it isn't, mark the check **Not Applicable**, not
  Fail or Needs Review. A
  missing key is only a Fail when the feature is demonstrably in use. When a
  setting is turned off but the checklist asks for acceptance or enablement
  (e.g. AI Services terms not accepted while all AI features are disabled),
  use **Needs Review** and ask whether it is intentional. For "AI assistant
  debug data in the bundle" checks, a bundle that simply lacks the section is
  **Needs Review**, not Fail.

- **Backend Xmx sizing (e.g. a "backend Xmx" check):** apply the full rule from the checklist, not
  just the RAM tier. Check all of: (1) `backend.xmx` against the RAM tier; (2) `backend.xmx` >= 3x the size
  of the `config/` folder (the reader's `listings-and-manifests` reference says how to size it);
  (3) it is not in the 32-48GB dead zone; (4) the other components' heaps (`jek.xmx`/`fek.xmx`)
  are not oversized; (5) no `OutOfMemoryError` in the backend logs. State which of these you
  checked in `evidence_found`; never assume a tier from RAM alone.

- **Log-error review (e.g. a backend log-error check):** the bundle usually holds only a few hours of backend
  log. Quote counts with their window (e.g. `214 in ~2.6h`) in both `evidence_found` and `notes`,
  and group by message pattern (digits and ids normalised), not by raw line. The reader's
  `data-dir-runtime-and-codeenvs` reference says how to count and get the window.

- **A hinted setting is not proof of absence:** a checklist `parameter_hint` is a pointer,
  not a guarantee of where the setting lives. Before marking a setting absent or Fail, look for it
  the way the reader's `data-dir-config` reference ("Finding a setting reliably") describes. A
  concurrency or sizing limit that sits in a different place than its name suggests still counts:
  a value of `0` means unsized and is a **Fail** for "Flow Limits Sizing", even when the other
  concurrency limit is in range. Connection-detail gaps that DSS itself flagged are real evidence
  for connection-details checks: report them **Partial** rather than Not Applicable just because
  the storage is HDFS and not a cloud object store.

- **HTTPS enforcement check (especially for custom/on-prem
  installs):** DSS's own config only shows whether DSS
  itself is terminating TLS. It cannot show whether an external reverse
  proxy (nginx, an ALB/load balancer, an API gateway, etc.) sits in front of
  DSS and terminates HTTPS there instead — that setup is invisible to the
  diagnosis bundle. So: if the bundle shows DSS is *not* itself configured
  for HTTPS (e.g. plain HTTP in the server settings), do not mark this **Fail**.
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

- **Automation-node existence / Design–Automation separation, when reviewing a design-node bundle:** the automation node is
  a separate host with its own bundle, so a design-node bundle can never
  definitively confirm one exists. Always mark this **Needs Review**, never
  Pass or Fail from the design bundle alone. Use the reader's `node-types`
  and `data-dir-config` (deployer) references to find the indicators, work
  through them in this order and report what you find:
  1. **Local Project Deployer on the design host:** a deployer configured
     locally that holds projects to deploy onto an automation node is an
     indication an automation node is in use. Enumerate what it holds
     (infrastructures, deployments, published projects, and any automation
     node URLs they point to) and **highlight this indication prominently in
     the headline of `notes`** with the counts, and list the URLs and
     enumeration in `evidence_found`. Distinguish a populated deployer (strong
     indication) from one that is present but empty (deployer enabled, no
     sign of actual use). A local API Deployer targets API nodes — mention it
     separately as an API-node indication, not as evidence of an automation
     node.
  2. **Remote deployer:** if the design node pushes to an external Deployer
     URL, highlight that — suggestive of a Design → Deployer → Automation
     setup, but any automation infrastructure is defined on that node, not in
     this bundle. Exported project bundles are weak supporting evidence either
     way.
  3. **Otherwise:** state in `notes` that there is no definitive
     configuration in the bundle indicating whether an automation node is
     deployed, and that this needs further verification with the customer.

- **Session-management and clickable-link checks (session expiry, single session per user, links in data
  tables):** these settings are captured in the bundle (the reader's `data-dir-config` reference says
  where), so judge them from the value, never **Needs Review** because a checklist hint calls them
  UI-only. A timeout of `0` means unlimited: **Fail** when both session timeouts are `0`, **Pass** when
  either is finite. A single-session or disable-links toggle that is off is **Fail**; on is **Pass**.
  Needs Review only when the settings block itself is missing from the bundle.

- **Custom post-logout redirect (e.g. a "custom URL after logout" check):** this is optional hardening,
  and the checklist itself says the default logout page is not a security concern. When no custom
  redirect is configured, mark it **Not Applicable** (not Fail or Needs Review) and say the default page
  is in use. **Pass** when a valid http/https redirect is configured; **Fail** only when one is
  configured but invalid.

- **Spark validation checks on a non-Kubernetes estate (e.g. a "functional Spark validation" check):**
  these are worded for Spark on Kubernetes (executor pods). If no Kubernetes cluster is attached and Spark
  runs on YARN/Hadoop, treat them under the Kubernetes-conditional rule above: **Not Applicable**.

- **Version-gated checks (e.g. a check that needs a newer DSS than the bundle runs):** compare the
  check's stated minimum version with the bundle's `product_version`. If the bundle is older, mark it
  **Needs Review** (the capability can't exist yet, so Fail would be unfair) and say which version
  introduces it.

- **An inferred limit is not evidence (e.g. a connection pool vs. an internal-database limit that the
  bundle does not record):** don't mark Pass or Fail from an assumed default. Mark **Needs Review**,
  state the inference in `notes` as an inference, and ask for the real value.

- **A dominant benign-looking log pattern (backend log-error review):** still apply the log-error rule
  above and report the status it gives, but when one pattern dominates (for example repeated rejected
  WebSocket sessions that were not logged in) say so in `notes` with its share of the count, so a
  reviewer can judge whether the errors are real.
