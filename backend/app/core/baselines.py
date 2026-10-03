"""Text-only baselines B1 and B2 (PRD 10.2b, SF-2, FR-1411, TRD TR-MOD-11)."""

import re

_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def numeric_tokens(raw: str) -> list[str]:
    """Sorted numeric tokens of a RAW text (PRD 10.2b)."""
    return sorted(_NUMBER.findall(raw.upper()))


def b1(sim: float, tau: float) -> bool:
    """B1 text only: positive when the normalised-text similarity is >= tau1."""
    return sim >= tau


def b2(sim: float, raw_a: str, raw_b: str, tau: float) -> bool:
    """B2 text + numbers: similarity >= tau2 and equal numeric tokens of the raw texts."""
    return sim >= tau and numeric_tokens(raw_a) == numeric_tokens(raw_b)
