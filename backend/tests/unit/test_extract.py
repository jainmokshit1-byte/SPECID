"""FR-301-303, FR-307, FR-402, FR-1431 (TRD TR-MOD-03, TR-MOD-04): classification and extraction.

Field-by-field agreement with the reference extractors is in tests/reference/test_conformance.py.
"""

from app.core.classify import classify
from app.core.extract import extract
from tests.coreenv import E, N, dictionary


class FakeModel:
    """Stands in for the Phase 5 category model (TRD 4.3)."""

    def __init__(self, label: str, p: float) -> None:
        self.label, self.p, self.calls = label, p, 0

    def predict(self, norm_text: str) -> tuple[str, float]:
        self.calls += 1
        return self.label, self.p


def test_rules_first_in_reference_order() -> None:
    assert classify(N("GATE VALVE FLANGED RF"), None, 0.8) == ("VALVE", "RULE", None)
    assert classify(N("FLANGE BOLT M16"), None, 0.8)[0] == "FLANGE"
    assert classify(N("STUD M20 X 120"), None, 0.8)[0] == "FASTENER"


def test_model_only_when_no_rule_fires() -> None:
    model = FakeModel("VALVE", 0.95)
    assert classify(N("PIPE 6IN"), model, 0.8) == ("PIPE", "RULE", None)
    assert model.calls == 0
    assert classify(N("CL150 WCB RF"), model, 0.8) == ("VALVE", "ML", 0.95)


def test_model_abstains_below_threshold_or_on_none() -> None:
    assert classify(N("CL150 WCB RF"), FakeModel("VALVE", 0.79), 0.8) == (None, "NONE", 0.79)
    assert classify(N("CABLE 3C 95SQMM"), FakeModel("NONE", 0.99), 0.8) == (None, "NONE", 0.99)


def test_ml_category_is_marked_and_extracted_by_the_same_rules() -> None:
    s = extract(
        "4IN CL150 WCB RF", dictionary=dictionary(), model=FakeModel("VALVE", 0.9), threshold=0.8
    )
    assert (s.category, s.class_source, s.class_prob) == ("VALVE", "ML", 0.9)
    assert s.attrs["size_dn"] == 100 and s.attrs["body_material"] == "A216-WCB"


def test_unknown_category_is_never_guessed() -> None:
    s = E("SOMETHING ELSE 123")
    assert s.category is None and s.attrs == {} and s.class_source == "NONE"
    assert s.residual == ("SOMETHING", "ELSE", "123")


def test_every_conversion_is_noted_with_rule_tier() -> None:
    s = E("GV 100NB 150# WCB RF FLANGED")
    assert {k: m.note for k, m in s.meta.items() if m.note} == {
        "valve_type": "GV = GATE",
        "size_dn": "100 NB = DN100",
        "body_material": "WCB -> A216-WCB",
    }
    assert all(m.tier == "RULE" and m.confidence == 1.0 for m in s.meta.values())
    p = E("PIPE 6IN STD A106")
    assert p.attrs["schedule"] == "40" and p.meta["schedule"].note == "STD = SCH40 (DN150 <= 250)"
    assert p.attrs["process"] == "SEAMLESS" and p.meta["process"].note == "implied by A106"
    assert p.attrs["material"] == "A106-?"
    m = E("MOTOR AC IND 125HP 4P")
    assert m.attrs["power_kw"] == 93.2 and m.meta["power_kw"].note == "125 HP = 93.2 kW"


def test_unknown_size_keeps_its_note_but_no_value() -> None:
    s = E("PIPE 7IN SCH40 A106B")
    assert s.attrs["size_dn"] is None and s.meta["size_dn"].note == "7 IN is not a standard size"


def test_residual_drops_stop_words_and_consumed_tokens() -> None:
    s = E("GATE VALVE 4IN CL150 ASTM A216 WCB FLANGED RF NACE FOR SOUR SERVICE")
    assert s.residual == ("NACE", "SOUR", "SERVICE")


def test_mpn_and_maker_are_carried() -> None:
    s = E("BOLT M16X80 8.8", mpn="X-1", maker="ACME")
    assert (s.mpn, s.maker) == ("X-1", "ACME")
