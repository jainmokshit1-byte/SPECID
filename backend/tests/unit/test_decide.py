"""FR-601-609 (TRD TR-MOD-06, TR-MOD-12, TR-ALG-02): statuses, verdicts, routes, confidence."""

import pytest

from app.core.confidence import p_rule
from app.core.decide import compare, family
from tests.coreenv import D, E, spec, templates


# FR-601: one row per status (PRD 9.5)
@pytest.mark.parametrize(
    ("name", "x", "y", "status"),
    [
        ("size_dn", None, None, "MISSING_BOTH"),
        ("size_dn", 100, None, "MISSING_ONE"),
        ("size_dn", None, 100, "MISSING_ONE"),
        ("size_dn", 100, 100, "MATCH"),
        ("size_dn", 100, 150, "CONFLICT"),
        ("material", "A105", "A182-F316", "CONFLICT"),  # different family
        ("material", "SS316", "A182-F316", "PARTIAL"),  # generic vs specific, same family
        ("material", "A106-?", "A106-B", "PARTIAL"),
        ("material", "A182-F316", "A351-CF8M", "CONFLICT"),  # forged vs cast, both specific
        ("material", "A105", "A216-WCB", "CONFLICT"),  # PRD 9.5 example
        ("body_material", "SS304", "SS316", "CONFLICT"),
        ("end_connection", "FLANGED-?", "FLANGED-RF", "PARTIAL"),
        ("end_connection", "FLANGED-RF", "FLANGED-FF", "CONFLICT"),
        ("end_connection", "FLANGED-?", "BW", "CONFLICT"),
        ("power_kw", 93.2, 93.0, "MATCH"),  # within 1%
        ("power_kw", 100.0, 110.0, "CONFLICT"),
        ("rpm", 1450, 1480, "MATCH"),  # within 5%
        ("rpm", 1500, 1000, "CONFLICT"),
    ],
)
def test_compare_statuses(name: str, x: object, y: object, status: str) -> None:
    assert compare(name, x, y) == status
    assert compare(name, y, x) == status


def test_material_families_of_table_b3() -> None:
    assert {family(c) for c in ("A216-WCB", "A216-WCC", "A105", "A106-B", "A106-?", "A53-B")} == {
        "CS"
    }
    assert {family(c) for c in ("A182-F316", "A351-CF8M", "SS316")} == {"316"}
    assert {family(c) for c in ("A182-F304", "A351-CF8", "SS304")} == {"304"}


VALVE = "VALVE GATE 4IN CL150 WCB FLANGED RF"


def test_item_criticality_overrides_the_template_default() -> None:
    nut = ("NUT HEX M20 2H", "HEX NUT M20 A194 2H")  # template: not critical
    assert D(E(nut[0]), E(nut[1])).route == "AUTO_ELIGIBLE"
    for crit in ((True, None), (None, True), (True, False)):
        r = D(E(nut[0]), E(nut[1]), criticality=crit)  # either side critical -> critical
        assert r.route == "REVIEW" and "critical class: maker-checker" in r.reasons
    # a valve flagged non-critical on both items has no flag left
    r = D(E(VALVE), E(VALVE), criticality=(False, False))
    assert (r.verdict, r.route, r.reasons) == ("EQUIVALENT", "AUTO_ELIGIBLE", ())


def test_identical_needs_equal_mpn_and_maker() -> None:
    def verdict(
        mpn_a: str | None, maker_a: str | None, mpn_b: str | None, maker_b: str | None
    ) -> str:
        return D(E(VALVE, mpn_a, maker_a), E(VALVE, mpn_b, maker_b)).verdict

    assert verdict("X-1", "ACME", "X-1", "acme") == "IDENTICAL"  # maker case-insensitive
    assert verdict("X-1", "ACME", "X-2", "ACME") == "EQUIVALENT"
    assert verdict("X-1", "ACME", "X-1", "BETA") == "EQUIVALENT"
    assert verdict(None, None, None, None) == "EQUIVALENT"
    assert verdict("X-1", "ACME", None, "ACME") == "EQUIVALENT"


def test_reasons_follow_tr_alg_02_order() -> None:
    a = E("VALVE GATE 4IN CL150 WCB FLANGED RF API 600 NACE")
    b = E("VALVE GATE 4IN CL150 WCB FLANGED RF TRIM 8")
    assert D(a, b).reasons == (
        "design_standard unverified",
        "trim unverified",
        "unexplained tokens: NACE",
        "critical class: maker-checker",
    )


def test_confidence_heuristic() -> None:
    assert D(E(VALVE), E(VALVE)).confidence == 0.98
    a, b = E(VALVE + " API 600"), E(VALVE)
    assert D(a, b).confidence == 0.88  # one extended flag
    a, b = E(VALVE + " API 600 NACE"), E(VALVE)
    assert D(a, b).confidence == 0.73  # plus the residual flag
    assert D(E(VALVE), E(VALVE.replace("CL150", "CL300"))).confidence == 0.0
    assert D(E(VALVE), E("VALVE GATE 4IN CL150 WCB FLANGED")).confidence is None


def test_confidence_floor() -> None:
    from dataclasses import replace

    r = D(E(VALVE), E(VALVE))
    many = replace(r, reasons=tuple(f"x{i} unverified" for i in range(6)))
    assert p_rule(many) == 0.50


def test_decision_carries_the_template_version() -> None:
    assert D(E(VALVE), E(VALVE)).template_version == templates()["VALVE"].version
    assert D(E(VALVE), E("FLANGE WN 4IN CL150 RF A105")).template_version is None


def test_categories_differ_and_unknown_category() -> None:
    r = D(E(VALVE), E("PIPE 6IN SCH40 A106B"))
    assert (r.verdict, r.route, r.reasons, r.evidence) == (
        "NOT_EQUIVALENT",
        "NONE",
        ("category differs",),
        (),
    )
    r = D(spec(None, {}), E(VALVE))
    assert (r.verdict, r.route, r.reasons) == (
        "INSUFFICIENT_DATA",
        "REVIEW",
        ("category not recognised",),
    )


def test_supplied_value_never_overrides_a_veto() -> None:
    from app.core.extract import supply_attribute

    a, b = E(VALVE.replace("CL150", "CL300")), E(VALVE)
    a2 = supply_attribute(a, "trim", "8", "datasheet D-9")
    assert D(a2, b).verdict == "NOT_EQUIVALENT"
