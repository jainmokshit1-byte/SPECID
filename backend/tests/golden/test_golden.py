"""TR-TST-02 golden tests: tests/golden/*.yaml (TRD Appendix K format; PRD Appendix D cases).

Every case runs against core/ and, to prove the YAML is a faithful translation of Appendix D,
against the verbatim reference implementation (tests/reference/specid_ref.py, DEC-21).
"""

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.coreenv import EQV, NOT, D, E
from tests.reference import specid_ref as R

GOLDEN_DIR = Path(__file__).parent
CASE_KEYS = {"a", "b", "expected_verdict", "expected_route", "decisive", "note"}
NOT_VERIFIABLE = {"PARTIAL", "MISSING_ONE", "MISSING_BOTH"}


def _load() -> list[Any]:
    params = []
    for f in sorted(GOLDEN_DIR.glob("*.yaml")):
        doc = yaml.safe_load(f.read_text("utf-8"))
        for i, case in enumerate(doc["cases"], start=1):
            params.append(pytest.param(doc["template"], case, id=f"{f.stem}-{i}"))
    return params


CASES = _load()


def test_golden_set_is_the_25_appendix_d_cases() -> None:
    assert len(CASES) == 25  # 12 dossier pairs + 13 edge cases (PRD 13.2)
    pairs = {(p.values[1]["a"], p.values[1]["b"]) for p in CASES}
    assert set(NOT) | set(EQV) <= pairs
    for p in CASES:
        case = p.values[1]
        assert set(case) <= CASE_KEYS, p.id
        assert {"a", "b", "expected_verdict"} <= set(case), p.id


def _check(template: str | None, case: dict[str, Any], outcome: dict[str, Any]) -> None:
    assert outcome["verdict"] == outcome["verdict_ba"], "asymmetric verdict (T-P3)"
    assert outcome["verdict"] == case["expected_verdict"], outcome["reasons"]
    if template is not None:
        assert outcome["category"] == template.upper()
    if "expected_route" in case:
        assert outcome["route"] == case["expected_route"], outcome["reasons"]
        assert outcome["route_ba"] == case["expected_route"]
    if "decisive" in case:
        status = outcome["status"].get(case["decisive"])
        if case["expected_verdict"] == "NOT_EQUIVALENT":
            assert status == "CONFLICT", outcome["status"]
        else:
            assert status in NOT_VERIFIABLE, outcome["status"]
        assert any(case["decisive"] in r for r in outcome["reasons"]), outcome["reasons"]
    assert all(outcome["rules_cited"]), "every evidence row has rule and rule_text"


@pytest.mark.parametrize(("template", "case"), CASES)
def test_golden_core(template: str | None, case: dict[str, Any]) -> None:
    a, b = E(case["a"]), E(case["b"])
    r, r2 = D(a, b), D(b, a)
    outcome = {
        "category": a.category,
        "verdict": r.verdict,
        "verdict_ba": r2.verdict,
        "route": r.route,
        "route_ba": r2.route,
        "reasons": list(r.reasons),
        "status": {e.attr: e.status for e in r.evidence},
        "rules_cited": [bool(e.rule and e.rule_text) for e in r.evidence],
    }
    _check(template, case, outcome)


@pytest.mark.parametrize(("template", "case"), CASES)
def test_golden_reference(template: str | None, case: dict[str, Any]) -> None:
    a, b = R.extract(case["a"]), R.extract(case["b"])
    r, r2 = R.decide(a, b), R.decide(b, a)
    outcome = {
        "category": a["category"],
        "verdict": r["verdict"],
        "verdict_ba": r2["verdict"],
        "route": r["route"],
        "route_ba": r2["route"],
        "reasons": r["reasons"],
        "status": {e["attr"]: e["status"] for e in r["evidence"]},
        "rules_cited": [bool(e["rule"] and e["rule_text"]) for e in r["evidence"]],
    }
    _check(template, case, outcome)
