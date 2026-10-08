"""references/verdict-rules.md is the human-readable spec of the code-decided rules. It must list exactly the registered rules, so
a rule added, renamed or removed in scripts/rules_*.py cannot drift from its spec."""
import re
import sys

from conftest import REPO_ROOT

SCRIPTS = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "scripts"
DOC = REPO_ROOT / "skills" / "dataiku-diagnosis-checklist-review" / "references" / "verdict-rules.md"
sys.path.insert(0, str(SCRIPTS))
import run_step  # noqa: E402,F401  (imports every rules_* module, registering the rules)
import verdicts  # noqa: E402

ROW = re.compile(r"^\|\s*((?:ARCH|SEC|SCALE|GENAI|ADVSEC)-\d{3})\s", re.M)
SECTION_FILE = {"Security": "rules_security", "Platform, sizing and logs": "rules_platform",
                "Kubernetes and Spark": "rules_k8s", "GenAI": "rules_genai",
                "Always Needs Review": "rules_review"}


def _rows_by_section():
    sections = re.split(r"^## ", DOC.read_text(encoding="utf-8"), flags=re.M)[1:]
    return {title.split(" (")[0].strip(): ROW.findall(body) for title, _, body in (s.partition("\n") for s in sections)}


def test_every_registered_rule_has_exactly_one_row():
    rows = [i for ids in _rows_by_section().values() for i in ids]
    assert sorted(rows) == sorted(set(rows)), "a rule id appears in two rows"
    assert not set(verdicts.RULES) - set(rows), f"rules with no row in verdict-rules.md: {sorted(set(verdicts.RULES) - set(rows))}"
    assert not set(rows) - set(verdicts.RULES), f"rows with no rule: {sorted(set(rows) - set(verdicts.RULES))}"


def test_each_row_sits_under_the_section_of_its_rule_module():
    for section, ids in _rows_by_section().items():
        if section not in SECTION_FILE:
            continue
        for check_id in ids:
            assert verdicts.RULES[check_id][1].__module__ == SECTION_FILE[section], f"{check_id} is under '{section}' but lives in {verdicts.RULES[check_id][1].__module__}"
