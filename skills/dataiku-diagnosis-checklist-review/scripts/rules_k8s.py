"""Verdict rules for the Spark, Kubernetes and containerized-execution checks (judgment only; see verdicts.py for the contract).

Each rule's text is the human-readable spec in `references/verdict-rules.md` (keep the two in step). Kubernetes-conditional checks are Not Applicable
when no cluster is attached. A fact that is missing from the bundle is Needs Review, never an assumed Fail."""
from __future__ import annotations

from verdicts import ABSENT, fact, rule, verdict


def _missing(what: str):
    return verdict("Needs Review", f"{what} missing from the bundle")


def _k8s(facts):
    k = fact(facts, "kubernetes")
    return k if isinstance(k, dict) else None


def _list(k, key):
    v = k.get(key)
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _on_kubernetes(configs):
    return [c for c in configs if c.get("type") == "KUBERNETES"]


def _no_cluster(k):
    """The verdict for a Kubernetes-conditional check when nothing is attached, or None when a cluster is attached."""
    if k.get("cluster_attached") is True:
        return None
    return verdict("Not Applicable", "no Kubernetes cluster is attached", cluster_attached=False)


def _sizing(c, keys):
    return tuple(c.get(key, ABSENT) for key in keys)


def _differ(configs, keys):
    return len({_sizing(c, keys) for c in configs}) >= 2


CONTAINER_SIZE = ("mem_request_mb", "mem_limit_mb", "cpu_request", "cpu_limit")
SPARK_SIZE = ("executor_instances", "executor_memory", "executor_cores", "driver_memory")


@rule("ARCH-005", "Valid Spark Configuration for Spark Jobs")
def valid_spark_config(facts):
    k = _k8s(facts)
    if k is None:
        return _missing("Spark settings")
    enabled = k.get("spark_enabled", ABSENT)
    valid = [c for c in _list(k, "spark_configs") if c.get("resources_set") is True]
    values = {"spark_enabled": enabled, "configs": len(_list(k, "spark_configs")), "configs_with_resources": len(valid)}
    if enabled is False:
        return verdict("Not Applicable", "Spark is disabled", **values)
    if enabled is not True:
        return _missing("the Spark enabled flag")
    if valid:
        return verdict("Pass", f"Spark enabled with {len(valid)} valid execution config(s)", **values)
    return verdict("Fail", "Spark is enabled but no execution config sets executor or driver resources", **values)


@rule("ARCH-006", "Baseline Spark Configuration Set (High/Standard/Large-memory/High I/O)")
def spark_baseline_configs(facts):
    k = _k8s(facts)
    if k is None:
        return _missing("Spark settings")
    if k.get("spark_enabled") is False:
        return verdict("Not Applicable", "Spark is disabled", spark_enabled=False)
    configs = _list(k, "spark_configs")
    values = {"configs": len(configs)}
    if not configs:
        return verdict("Fail", "no Spark execution configs defined", **values)
    if _differ(configs, SPARK_SIZE):
        return verdict("Pass", f"{len(configs)} Spark configs with genuinely different sizing", **values)
    return verdict("Needs Review", "only one Spark config, or all are identically sized (ask whether the workloads need differently sized configs)", **values)


@rule("ARCH-007", "Kubernetes Namespace and Auth Recommendations for Spark")
def per_user_namespaces(facts):
    k = _k8s(facts)
    if k is None:
        return _missing("Kubernetes settings")
    na = _no_cluster(k)
    if na:
        return na
    targets = [c for c in _list(k, "spark_configs") if c.get("managed_kubernetes") is True] + _on_kubernetes(_list(k, "container_configs"))
    if not targets:
        return verdict("Needs Review", "a cluster is attached but no execution config targets it", cluster_attached=True)
    kinds = sorted({str(c.get("namespace", ABSENT)) for c in targets})
    values = {"namespace_kinds": kinds}
    if "ABSENT" in kinds:
        return verdict("Needs Review", "an execution config has no namespace set", **values)
    if "fixed" in kinds:
        return verdict("Needs Review", "an execution config uses a fixed namespace (ask whether it is per user or governed outside DSS)", **values)
    return verdict("Pass", "namespaces are templated per user", **values)


@rule("ARCH-010", "Valid Containerized Execution Configuration")
def valid_container_config(facts):
    k = _k8s(facts)
    if k is None:
        return _missing("Kubernetes settings")
    na = _no_cluster(k)
    if na:
        return na
    configs = _on_kubernetes(_list(k, "container_configs"))
    sized = [c for c in configs if isinstance(c.get("mem_limit_mb"), (int, float)) and c["mem_limit_mb"] > 0]
    values = {"kubernetes_configs": len(configs), "with_memory_limit": len(sized)}
    if not configs:
        return verdict("Fail", "a cluster is attached but no containerized execution config is defined", **values)
    if not sized:
        return verdict("Needs Review", "container configs exist but none sets a memory limit", **values)
    return verdict("Pass", f"{len(configs)} containerized execution config(s), {len(sized)} with a memory limit", **values)


@rule("ARCH-011", "Baseline Container Execution Configs (Standard, Webapp) and Namespace Settings")
def container_baseline(facts):
    k = _k8s(facts)
    if k is None:
        return _missing("Kubernetes settings")
    na = _no_cluster(k)
    if na:
        return na
    configs = _on_kubernetes(_list(k, "container_configs"))
    values = {"kubernetes_configs": len(configs)}
    if not configs:
        return verdict("Fail", "a cluster is attached but no containerized execution config is defined", **values)
    if _differ(configs, CONTAINER_SIZE):
        return verdict("Pass", f"{len(configs)} container configs with genuinely different sizing", **values)
    return verdict("Needs Review", "only one container config, or all are identically sized (ask whether the workloads need differently sized configs)", **values)


def _live_cluster_check(facts, what):
    """Checks a bundle can never settle (a live Spark run, topology, capacity): Not Applicable without a cluster, else Needs Review."""
    k = _k8s(facts)
    if k is None:
        return _missing("Kubernetes settings")
    if k.get("cluster_attached") not in (True, False):
        return _missing("the cluster attachment")
    na = _no_cluster(k)
    if na:
        return na
    return verdict("Needs Review", f"a cluster is attached; {what} cannot be shown by a bundle", cluster_attached=True)


@rule("ARCH-008", "Functional Validation of Spark Execution (Recipe & Notebook)")
def spark_functional_validation(facts):
    return _live_cluster_check(facts, "a live Spark run in a recipe and a notebook")


@rule("ARCH-014", "Recommended Cluster Topology (Single Managed Cluster, Node Groups, Autoscaling)")
def cluster_topology(facts):
    return _live_cluster_check(facts, "the cluster topology and autoscaling")


@rule("ARCH-015", "Appropriate Cluster Sizing")
def cluster_sizing(facts):
    return _live_cluster_check(facts, "the cluster capacity against the workloads")


@rule("GENAI-002", "Hugging Face Local LLM Enablement (Conditional)")
def hugging_face_local(facts):
    return _live_cluster_check(facts, "the GPU nodes, their compute capability and the local Hugging Face code environment")


@rule("ARCH-013", "Valid Cluster Configuration for Elastic Compute")
def valid_cluster(facts):
    k = _k8s(facts)
    if k is None:
        return _missing("Kubernetes settings")
    na = _no_cluster(k)
    if na:
        return na
    files = _list(k, "cluster_files")
    kube = [f for f in files if f.get("architecture") == "KUBERNETES"]
    values = {"cluster_files": len(files), "kubernetes_clusters": len(kube)}
    if kube:
        return verdict("Pass", f"{len(kube)} Kubernetes cluster definition(s)", **values)
    return verdict("Needs Review", "a cluster is attached but no Kubernetes cluster definition is in the bundle", **values)


@rule("ARCH-016", "Global Default Cluster and Default Execution Config Set (if Elastic AI used)")
def global_defaults(facts):
    k = _k8s(facts)
    if k is None:
        return _missing("Kubernetes settings")
    attached = k.get("cluster_attached", ABSENT)
    if attached is False:
        return verdict("Not Applicable", "no Kubernetes cluster is attached", cluster_attached=False)
    if attached is not True:
        return _missing("the cluster attachment")
    cluster = k.get("default_cluster_set", ABSENT)
    values = {"default_cluster_set": cluster, "default_execution_config": k.get("default_execution_config", ABSENT)}
    if cluster is True:
        return verdict("Pass", "a cluster is attached and a default cluster is set", **values)
    if cluster is False:
        return verdict("Fail", "a cluster is attached but no default cluster is set", **values)
    return _missing("the default cluster setting")


@rule("ARCH-017", "Containerized Visual Recipes (CDE) Enabled and Base Image Built")
def containerized_visual_recipes(facts):
    k = _k8s(facts)
    if k is None:
        return _missing("Kubernetes settings")
    na = _no_cluster(k)
    if na:
        return na
    cde, default = k.get("containerized_visual_recipes_enabled", ABSENT), k.get("default_visual_recipes_config_set") is True
    values = {"containerized_visual_recipes_enabled": cde, "default_visual_recipes_config_set": default}
    if cde is True and default:
        return verdict("Pass", "containerized visual recipes are enabled with a default execution config", **values)
    return verdict("Needs Review", "containerized visual recipes or their default execution config are not set (ask whether visual recipes are offloaded)", **values)
