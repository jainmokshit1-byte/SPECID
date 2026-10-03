"""Look-alike Guard (PRD 9.13.1, SF-1, FR-1401, TRD TR-MOD-10)."""

from typing import Literal

from rapidfuzz import fuzz

LookalikeClass = Literal["LOOKALIKE_VETOED", "HIDDEN_TWIN"]


def text_sim(a_norm: str, b_norm: str) -> float:
    """Token-set ratio / 100 of the NORMALISED texts."""
    return float(fuzz.token_set_ratio(a_norm, b_norm)) / 100


def lookalike_class(
    sim: float, verdict: str, hi: float = 0.85, lo: float = 0.75
) -> LookalikeClass | None:
    """LOOKALIKE_VETOED: text says "same", SpecID vetoed. HIDDEN_TWIN: the other way round."""
    if verdict == "NOT_EQUIVALENT" and sim >= hi:
        return "LOOKALIKE_VETOED"
    if verdict in ("EQUIVALENT", "IDENTICAL") and sim <= lo:
        return "HIDDEN_TWIN"
    return None
