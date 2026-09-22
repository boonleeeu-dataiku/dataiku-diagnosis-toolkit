# Root-level files

These are node-type-agnostic — the same set/format was observed on design and automation
bundles alike (the diagnostic-collection tooling doesn't change based on node role).

## `diag.txt` vs `timings.txt` — read `timings.txt` first

**`diag.txt` is a partial transcript, not a full one.** The diagnosis collector runs one long
sequence of commands (identical in structure whether the node is `design` or `automation`), but
only *some* of them get their `> <command>` header + full output written inline into `diag.txt`.
For commands whose output is large and already goes to its own dedicated file (package listings,
`dmesg`, `sysctl -a`, `ps auxf`, `systemd-cgtop`, `ss -anpO`, the `find -ls` scans, the JVM
stack-dump script), `diag.txt` contains only a couple of bare timestamp lines as a placeholder —
**no command header, no output**. Don't search `diag.txt` for e.g. `dpkg`/`rpm`/`ps auxf` content;
it isn't there even though the command ran — go to `syspackages.txt`/`ps.txt` directly.

**`timings.txt` has the true, complete, ordered command sequence** (tab-separated:
`<start>\t<end>\t<command>`), including every command that `diag.txt` only stubs out. Use it as
the authoritative index of "what ran, in what order, and how long each step took" — and to spot
slow steps (in all three real samples, the full-data-dir `find ... -ls` and the JVM stack-dump
capture were by far the slowest, taking minutes).

Full sequence, as seen in `timings.txt` (order is stable across node types; a `✓` marks steps
whose header+output also appear inline in `diag.txt` — everything else is placeholder-only there).
**The `✓` steps are a dense, high-value source of OS/system/environment facts that's easy to
overlook** — see the detailed breakdown further down before assuming you need `sysctl.txt`/
`ps.txt`/etc. for a system question; a lot of it is already sitting in `diag.txt` itself.

1. ✓ `uname -a` → `id` → `uptime` → `cat /etc/hosts` → `printenv` (full DSS+shell env dump) →
   `date`/`date -u`
2. ✓ Java/javac/nginx version probes → DSS `bin/python -V`/`bin/pip -V` → `python3.6`...
   `python3.12` / `conda` version probes
3. ✓ `/etc/debian_version` / `/etc/redhat-release` / `lsb_release -a` → `hostname --fqdn` →
   `getenforce` (SELinux mode)
4. `dpkg --list` (fails on RHEL-based hosts, → `syspackages.txt`) → `rpm -qa` (→
   `syspackages.txt`) → `pip list` (→ `pip.txt`) → `R CMD BATCH installed_packages.r ... r.txt`
   (✓ header appears in `diag.txt`, but actual output goes to `r.txt` in a tmp path that may not
   be copied into the bundle — see `references/limitations.md`)
5. ✓ `ulimit -a` (soft) and `ulimit -a -H` (hard)
6. ✓ `free -m` → `/proc/cpuinfo` → `/proc/meminfo` → `vm.overcommit_memory`/`vm.overcommit_ratio`/
   `vm.swappiness` → `/proc/mounts`
7. ✓ `mstat 3` → `systemd-cgtop --iterations=3 -b -P` (→ `cgroups_usage.txt`) →
   `timeout 5s ss -anpO` (→ `sockets.txt`)
8. ✓ `ip addr ls` / `ip ro ls` → `df -h` / `df -i` → `lsblk` (+ `-t`). **Version-dependent**: newer
   DSS versions (observed on 14.4.3, absent on 14.2.1) also run `blkid`, `mount`,
   `cat /etc/fstab`, `cat /etc/mtab`, `findmnt -D`, `findmnt -n -o SOURCE /data`, and
   `ls -Rla /dev/disk/` here — check for their presence rather than assuming either way.
9. `dmesg` (→ `dmesg.txt`) → `sysctl -a` (→ `sysctl.txt`) → `ps auxf` (→ `ps.txt`)
10. ✓ **`<mirror>/bin/dss status`** — DSS supervisor status: which components are running, PIDs,
    uptime
11. `ls -la <mirror>/bin/` (→ `bin_listing.txt`)
12. `find <mirror>/config -ls` (→ `config_listing.txt`), `find <mirror>/code-envs/desc
    <mirror>/acode-envs/desc -ls` (→ `code_envs_desc_listing.txt` — note both directories are
    scanned on every node type, not just automation), `find <mirror>/lib -ls` (→ `lib_listing.txt`),
    `find <DATA_DIR> -ls` (→ `datadir_listing.txt` — often the **slowest single step**, minutes on
    a large data dir), `find <install dir> -ls` (→ `installdir_listing.txt`)
13. JVM thread-stack dump capture via `_diag_get_stacks.py` (→ `stacks.txt`) — also often one of
    the slowest steps, and runs on both design and automation nodes
14. ✓ `iostat -x -c 3 6` (sometimes fails — not installed) → `vmstat 3 6`

## Detailed breakdown of what's inline in `diag.txt` (the OS/system/environment facts)

Don't skip straight to `cgroups_usage.txt`/`dmesg.txt`/`ps.txt` for a general system question —
check whether it's answered here first, since these are cheap to read (small, plain text) and
often sufficient on their own.

| Section | What it tells you | Example (from a real sample) |
|---|---|---|
| `uname -a` | Kernel version, hostname, architecture | `Linux gcp9234prdapp04 4.18.0-553.144.1.el8_10.x86_64 ... x86_64 GNU/Linux` |
| `id` | The OS user/group DSS actually runs as | `uid=1011(dss20677p4ddde01) gid=1016(...) groups=1016(...)` |
| `uptime` | Host uptime, load average | ` 08:21:06 up 22:17,  0 users,  load average: 0.38, 0.25, 0.11` |
| `cat /etc/hosts` | Hostname resolution, cloud metadata entries | Shows internal hostname mapping plus e.g. `169.254.169.254 metadata.google.internal` on GCP |
| `printenv` | **The single richest section** — see the dedicated breakdown below | |
| `date` / `date -u` | Local time and UTC at capture time — use to align with log timestamps in other timezones | |
| Java/javac/nginx version probes | Exact installed versions (there can be two JVMs — DSS's bundled one and a system one) | `openjdk version "17.0.19"` (system) vs `java version "1.8.0_492"` (a second/older JVM found on PATH) |
| `bin/python -V` / `bin/pip -V` | DSS's own bundled Python/pip version | `Python 3.9.25`, `pip 25.1.1` |
| `which python3.6` ... `python3.12`, `which conda` | Which OS-level Python versions / conda are installed and on PATH (separate from DSS's bundled Python and from project code-envs) | Shows e.g. `python3.9` present, `python3.10`-`3.12` and `conda` not found |
| `/etc/debian_version` / `/etc/redhat-release` / `lsb_release -a` | OS distribution and version | `Red Hat Enterprise Linux release 8.10 (Ootpa)` |
| `hostname --fqdn` | Fully-qualified domain name | |
| `getenforce` | SELinux mode | `Disabled` / `Permissive` / `Enforcing` |
| `ulimit -a` (soft) / `ulimit -a -H` (hard) | Resource limits actually in effect for the DSS process's shell — open files, max processes, core size, stack size, etc. | `open files (-n) 262144`, `max user processes (-u) 255382`, `core file size (blocks, -c) 0` (soft) vs `unlimited` (hard) — a soft limit of 0 for core size explains missing core dumps even if hard allows them |
| `free -m` | Total/used/free/available memory, swap | `Mem: 63885 36803 20137 ... ` (total/used/free in MB) |
| `/proc/cpuinfo` | Per-core CPU details (model, flags, cache) — count entries for core count | `model name: AMD EPYC 7B13`, repeated once per logical CPU (8 in one sample) |
| `/proc/meminfo` | Fine-grained memory breakdown: hugepages, dirty pages, slab, commit limit/committed | `CommitLimit`, `Committed_AS`, `AnonHugePages`, `HugePages_Total` |
| `vm.overcommit_memory` / `vm.overcommit_ratio` / `vm.swappiness` | Kernel memory-management tuning relevant to OOM behavior | `overcommit_memory=0`, `overcommit_ratio=50`, `swappiness=30` |
| `/proc/mounts` | Every mounted filesystem, including **which cgroup hierarchy version is in use** — separate `/sys/fs/cgroup/memory`, `/sys/fs/cgroup/cpu,cpuacct` etc. mount points indicate **cgroup v1**; a single unified `/sys/fs/cgroup` mount indicates **cgroup v2** | |
| `ip addr ls` / `ip ro ls` | Network interfaces (with IPs) and routing table | Shows `eth0`/`docker0` interfaces, default route |
| `df -h` / `df -i` | Disk space and inode usage per filesystem | `/dev/mapper/vg01-vol01  800G  585G  216G  74% /apps` — check this before assuming disk pressure requires `datadir_listing.txt` |
| `lsblk` / `lsblk -t` | Block device layout (disks, partitions, LVM), and I/O alignment/queue settings | |
| `blkid`, `mount`, `/etc/fstab`, `/etc/mtab`, `findmnt -D`, `ls -Rla /dev/disk/` (version-dependent, see above) | Filesystem UUIDs/labels, active mount options, fstab-defined mounts, disk-by-id/uuid/path symlinks | |
| `<mirror>/bin/dss status` | Which DSS components are running, their PIDs and uptime | `backend RUNNING pid 3611, uptime 22:17:33` |
| `iostat -x -c 3 6` | Per-device I/O stats sampled 6× (often fails — not installed) | |
| `vmstat 3 6` | CPU/memory/swap/IO sampled 6× over ~18s — live load, not just a snapshot | Columns: procs, memory, swap, io, system, cpu (us/sy/id/wa/st) |

### `printenv` — the richest single section

A full dump of every environment variable the DSS process sees. Categories worth knowing about:

- **Node type, fast**: `DKU_NODE_TYPE=design` (or `automation`, etc.) — often faster to check than
  finding and parsing `install.ini` (see `references/data-dir-identity.md`).
- **JVM heap sizes per DSS component**: `DKU_BACKEND_JAVA_OPTS=-Xmx8g ...`,
  `DKU_EVENTSERVER_JAVA_OPTS=-Xmx2g ...`, `DKU_JEK_JAVA_OPTS=...`, `DKU_HPROXY_JAVA_OPTS=...`,
  `DKU_CAK_JAVA_OPTS=...`, `DKU_FEK_JAVA_OPTS=...`, `DKU_DKU_JAVA_OPTS=...` — check these directly
  when investigating an OOM instead of relying only on `install.ini`'s `backend.xmx`.
- **Ports per component**: `DKU_NGINX_PORT`, `DKU_BASE_PORT`, `DKU_BACKEND_PORT`,
  `DKU_EVENTSERVER_PORT`, `DKU_HPROXY_PORT`, `DKU_STORIES_PORT`, `DKU_IPYTHON_PORT`.
- **Key paths**: `DKUINSTALLDIR`, `DIP_HOME` (= the data-dir mirror path), `DKURUNDIR`,
  `DKUJULIADEPOT`, `PYTHONPATH`, `R_LIBS`, `JAVA_HOME`.
- **Spark/Hadoop integration**: `DKU_SPARK_ENABLED`, `DKU_SPARK_VERSION`, `DKU_SPARK_HOME`,
  `DKU_PYSPARK_PYTHONPATH` — a fast way to tell if Spark integration is even enabled before
  digging into `opt/cloudera/...` config.
- **OS distro shorthand**: `DKUDISTRIB=redhat 8.10` — a quicker one-liner than parsing
  `/etc/redhat-release` separately.
- **The OS user DSS runs as**: `USER`, `HOME`, `LOGNAME` (cross-check against `id`'s output).

## Standalone root `.txt` files

Each is the raw stdout of one OS/JVM command. These are generally small enough to read directly
(exceptions noted below and in `references/limitations.md`) and each holds more than its one-line
summary suggests — read the per-file breakdown, not just the table, before concluding something
"isn't in the bundle."

| File | Command | Format |
|---|---|---|
| `sockets.txt` | `timeout 5s ss -anpO` | Column table: Netid, State, Recv-Q, Send-Q, Local/Peer Address:Port, Process |
| `sysctl.txt` | `sysctl -a` | `key = value` |
| `stacks.txt` | JVM thread-dump capture (`_diag_get_stacks.py`) | jstack-style: `"ThreadName" Id=N STATE` + `at pkg.Class.method(File:line)` frames |
| `cgroups_usage.txt` | `systemd-cgtop --iterations=3 -b -P` | Column table: Path, Tasks, %CPU, Memory, Input/s, Output/s |
| `dmesg.txt` | `dmesg` | Timestamped kernel ring-buffer log, `[seconds-since-boot]` |
| `syspackages.txt` | `dpkg --list` (fails on RHEL) then `rpm -qa` | Package-version-arch lines |
| `ps.txt` | `ps auxf` | Standard `ps auxf` columns, tree-indented |
| `r.txt` | R `installed.packages()` | R console transcript + package table |
| `pip.txt` | `pip list` | Two-column table |
| `bin_listing.txt` | `ls -la <mirror>/bin/` | Real `ls -la` output (not `find -ls`) |
| `docker_images_listing.txt` | container config + `docker images`-style dump | Header blocks + table |

### `sockets.txt`

Beyond generic netlink noise, filter to `^tcp\s+LISTEN` and `^u_str LISTEN` lines to get the
signal: every TCP port actually listening, with the owning process where known. This directly
confirms DSS's own ports match `install.ini`/`printenv` (e.g. nginx on `0.0.0.0:10000`, the
Jupyter/ipython gateway on `127.0.0.1:10002`) and surfaces unrelated host services sharing the box
(SSH on `22`, a local Postgres on `127.0.0.1:5432`, Cloudera agent sockets, backup/AV agent
sockets). Grep patterns:

```sh
grep -E '^tcp\s+LISTEN' sockets.txt        # all TCP listeners, with process owner
grep -E '^u_str LISTEN' sockets.txt        # unix-socket listeners (local IPC)
```

Example: `tcp LISTEN 0 128 0.0.0.0:10000 0.0.0.0:* users:(("nginx",pid=11642,fd=4),...))` —
confirms nginx is bound to the DSS base port from `install.ini`.

### `sysctl.txt`

A full `sysctl -a` dump — hundreds of lines. Don't read it all; the small set of keys people
actually ask about:

```sh
grep -E '^(fs\.file-max|fs\.aio-max-nr|vm\.max_map_count|vm\.overcommit_(memory|ratio)|vm\.swappiness|kernel\.(pid_max|threads-max)|net\.core\.somaxconn|net\.ipv4\.ip_local_port_range|crypto\.fips_enabled)' sysctl.txt
```

Covers: max open files (`fs.file-max`), max async I/O contexts (`fs.aio-max-nr` — relevant to
Elasticsearch/mmap-heavy workloads), max memory-mapped areas (`vm.max_map_count`), memory
overcommit tuning (also inlined in `diag.txt`, see above), max PIDs/threads system-wide
(`kernel.pid_max`/`kernel.threads-max`), TCP listen backlog (`net.core.somaxconn`), the ephemeral
port range (`net.ipv4.ip_local_port_range`), and whether the host is in FIPS mode
(`crypto.fips_enabled`).

### `stacks.txt`

A `jstack`-style dump of every JVM thread at capture time (~150-210 threads typical). Each thread
block starts `"ThreadName" Id=N STATE [on <lock>]` followed by its call stack. To triage:

```sh
grep -oE ' (RUNNABLE|WAITING|TIMED_WAITING|BLOCKED|NEW|TERMINATED)' stacks.txt | sort | uniq -c
grep -B1 -A10 'BLOCKED' stacks.txt   # threads actually blocked on a lock — the deadlock signal
```

Most threads being `WAITING`/`TIMED_WAITING` is normal (thread pools idling). A nonzero, growing
count of `BLOCKED` threads — especially several blocked on the same lock object — is the real
deadlock/contention signal. No `BLOCKED` threads at all means there was no deadlock at the exact
capture instant (a transient contention could still have been missed).

### `cgroups_usage.txt`

Paths are namespaced `/DSS/<project>/<activityType>` (activity types seen: `jupyterKernels`,
`pythonRRecipes`, `scenarioPython`, `metricsChecks`, `mlKernels`, `pythonMacros`,
`Devlambdaserver`). The file contains one block per `systemd-cgtop` sampling iteration (3 by
default) plus non-DSS system slices (`/`, `/user.slice`, ...) — filter to `/DSS/` paths and the
memory column (field 4) to rank DSS's own consumers:

```sh
# Columns are: Path Tasks %CPU Memory Input/s Output/s — Memory is field 4
awk '$1 ~ /^\/DSS\// && $4 != "-" {print $4, $1}' cgroups_usage.txt | sort -k1,1 -rh | uniq | head -10
```

Example output: `436.0M /DSS/pvdssjobs02` then `194.1M /DSS/pvdssjobs02/pythonRRecipes`,
`180.3M /DSS/pvdssjobs02/scenarioPython`, `58.7M /DSS/pvdssjobs02/metricsChecks` — scheduled
recipe/scenario/metrics activity in project `pvdssjobs02` dominates memory use on this node.
Cross-reference the project/activity against `config/projects/<KEY>/`
(`references/data-dir-config.md`) to see what that project actually runs.

### `dmesg.txt`

Kernel ring-buffer log from boot (`[seconds-since-boot]` timestamps — convert using the boot time
implied by `uptime`/`date` in `diag.txt`). The single highest-value grep:

```sh
grep -i 'oom-kill\|oom_reaper\|killed process' dmesg.txt
```

A real example: `oom-kill:constraint=CONSTRAINT_MEMCG,...,oom_memcg=/DSS,task_memcg=/DSS/act_lsh/
mlKernels,task=python,pid=2348402,uid=...` followed by `Memory cgroup out of memory: Killed
process 2348402 (python) total-vm:61423112kB, anon-rss:53921716kB, ...` — this directly names the
**cgroup path** (hence project + activity type) and the **RSS at time of kill**, so you rarely
need to guess which project caused an OOM. Also useful: hardware/driver errors, and the exact
boot kernel command line near the top of the file (`Command line: BOOT_IMAGE=... crashkernel=auto
...`).

### `syspackages.txt`

Full `rpm -qa` (or `dpkg --list`) output — hundreds to ~1000+ lines, one package per line
(`name-version-release.arch`). For security/compatibility questions, grep for the package you
care about rather than reading it all:

```sh
grep -iE '^(openssl|glibc|python3|java-|nginx|systemd|kernel)-[0-9]' syspackages.txt
```

Gives you e.g. `openssl-1.1.1k-15.el8_6.x86_64`, `glibc-2.28-251.el8_10.34.x86_64` — useful for
CVE/compatibility questions independent of DSS itself.

### `ps.txt`

`ps auxf`, tree-indented. Two things it's uniquely good for beyond "is X running":

1. **Full JVM command lines** — grep for `java` to get each DSS component's exact heap/GC flags,
   temp dir, and classpath as actually launched (cross-check against `printenv`'s `DKU_*_JAVA_OPTS`
   — they should match, and a mismatch would itself be a finding).
2. **Ranking processes by memory (RSS, column 6)** to find top consumers independent of cgroups:
   ```sh
   tail -n +2 ps.txt | sed 's/^\s*//' | awk '{print $6, $2}' | sort -rn | head -10
   # then look up the full command for a PID of interest:
   grep -w '<pid>' ps.txt
   ```
   (the `COMMAND` column itself starts with tree-drawing characters like `\_`/`|`, so grab it by
   PID rather than by column position.) Also check the `START` column (e.g. `May22`) against the
   capture date to get each process's real uptime, and grep for `defunct` to spot zombies.

### `r.txt`

R version banner, then `installed.packages()` as a table (`Package | LibPath | Version`). Look for
the `dataiku`/`dataiku.spark2`/`dataiku.sparklyr` rows specifically — their version should match
the DSS `product_version`. **May be absent** even though the command ran — see
`references/limitations.md`.

### `pip.txt`

`pip list` for DSS's own bundled Python (used by the Jupyter/ipython gateway) — **not** any
project code-env. For project code-env packages, see `code-envs/desc/python/<env>/actual/
requirements.txt` in `references/data-dir-runtime-and-codeenvs.md` instead.

### `bin_listing.txt`

Real `ls -la` of `<mirror>/bin/` (not a `find -ls` manifest). Confirms which DSS CLI symlinks
exist (`dss`, `dssadmin`, `dsscli`, `cak`, `fek`, `jek`, `hproxy`, `pip`, `python`) and their link
targets (which install-dir version they resolve to — useful after an upgrade to confirm symlinks
were actually repointed). Watch for `_original`/`_modified`/dated-backup siblings of the `env-*.sh`
files (e.g. `env-hadoop.sh_original`, `env-site.sh_17Apr2026`) — evidence of manual admin patching
(see `references/data-dir-identity.md`).

### `docker_images_listing.txt`

Only present when container/K8s code-env execution is configured (its absence isn't meaningful on
its own). Lists, per container-exec config, every built image: repository (both a local tag and
the full remote registry path, e.g. `europe-west1-docker.pkg.dev/<project>/<repo>/...` — this
reveals the cloud region and artifact registry in use), image tag (often embeds the code-env name
and a build timestamp, e.g. `dku-spark-base-<hash>-dss-14.4.3-pyenv-py_29925`), image ID, creation
time, and size (observed up to 10+ GB per image). Useful for "what container images exist for code
env X," "when was this image last rebuilt," and "how much disk is consumed by code-env container
images."

## `etc/`

Minimal in every sample — just `etc/security/limits.conf`, a mostly-template PAM resource-limits
file. Occasionally has a real active override appended (e.g. `* hard core 0`, disabling core
dumps for all users).
