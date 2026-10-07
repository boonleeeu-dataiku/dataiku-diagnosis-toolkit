"""Deterministic parts of the LLM-eval tooling: run summaries and baseline comparison."""

import sys

from conftest import REPO_ROOT

sys.path.insert(0, str(REPO_ROOT / "tests" / "evals"))

import compare  # noqa: E402
import run_review_eval  # noqa: E402


def run(scenario, run_no, oks, produced=True, structure=(), citations=()):
    return {
        "scenario": scenario, "run": run_no, "cost_usd": 1.0, "produced": produced,
        "structure": list(structure), "citations": list(citations),
        "items": {i: {"status": "x", "ok": ok, "failures": []} for i, ok in oks.items()},
    }


def test_summarize_rates():
    results = [
        run("s", 1, {"A": True, "B": True}),
        run("s", 2, {"A": True, "B": False}, citations=["bad"]),
        run("s", 3, {"A": False, "B": False}, structure=["bad"]),
    ]
    s = run_review_eval.summarize(results, "m")
    sc = s["scenarios"]["s"]
    assert s["cost_usd"] == 3.0
    assert (sc["runs"], sc["produced"], sc["structure_clean"], sc["citations_clean"]) == (3, 3, 2, 2)
    assert sc["item_pass_rate"] == {"A": 0.667, "B": 0.333}
    assert sc["accuracy"] == 0.5


def test_compare_flags_only_real_drops():
    ids = [f"I{n}" for n in range(34)]  # the eval checklist's size
    perfect = {i: True for i in ids}
    base = run_review_eval.summarize([run("s", r, perfect) for r in (1, 2, 3)], "old")

    one_wobble = run_review_eval.summarize(
        [run("s", 1, {**perfect, "I3": False}), run("s", 2, perfect), run("s", 3, perfect)], "new")
    regressions, _ = compare.compare(base, one_wobble, tolerance=0.34)
    assert regressions == []

    worse = run_review_eval.summarize([run("s", r, {**perfect, "I3": False}) for r in (1, 2, 3)], "new")
    regressions, _ = compare.compare(base, worse, tolerance=0.34)
    assert regressions == ["s/I3: pass rate 1.00 -> 0.00"]

    broken = run_review_eval.summarize([run("s", r, perfect, structure=["x"]) for r in (1, 2, 3)], "new")
    regressions, _ = compare.compare(base, broken, tolerance=0.34)
    assert regressions == ["s: structure_clean 1.00 -> 0.00"]
