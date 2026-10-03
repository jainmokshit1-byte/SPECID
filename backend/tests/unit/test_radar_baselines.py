"""FR-1401, FR-1411 (TRD TR-MOD-10, TR-MOD-11): look-alike classes and baselines."""

from app.core.baselines import b1, b2, numeric_tokens
from app.core.radar import lookalike_class, text_sim
from tests.coreenv import N


def test_text_sim_is_on_normalised_text() -> None:
    assert text_sim(N("GV 100NB 150#"), N("GV 100 NB CLASS 150")) == 1.0
    assert 0.0 <= text_sim(N("GATE VALVE"), N("HEX BOLT")) < 0.5


def test_lookalike_thresholds_are_parameters() -> None:
    assert lookalike_class(0.80, "NOT_EQUIVALENT", hi=0.80, lo=0.70) == "LOOKALIKE_VETOED"
    assert lookalike_class(0.80, "NOT_EQUIVALENT") is None
    assert lookalike_class(0.70, "IDENTICAL", hi=0.80, lo=0.70) == "HIDDEN_TWIN"
    assert lookalike_class(0.10, "INSUFFICIENT_DATA") is None


def test_baselines() -> None:
    assert numeric_tokens("VALVE 4IN CL150 8.8") == ["150", "4", "8.8"]
    assert b1(0.85, 0.85) and not b1(0.84, 0.85)
    assert b2(0.9, "VALVE CL150 4IN", "4 IN VALVE 150#", 0.55)
    assert not b2(0.9, "VALVE CL150", "VALVE CL300", 0.55)
    assert not b2(0.5, "VALVE CL150", "VALVE CL150", 0.55)
