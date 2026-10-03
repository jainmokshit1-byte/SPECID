"""Size, schedule, power and UoM canonicalisation.

PRD 9.3 and Appendix B; TRD TR-MOD-02, TR-ALG-06.
"""

from typing import Final

from app.core.types import Dictionary

# PRD Appendix B.1: NPS (inch) to DN (mm)
NPS_DN: Final[dict[str, int]] = {
    "1/2": 15, "3/4": 20, "1": 25, "1-1/4": 32, "1-1/2": 40, "2": 50, "2-1/2": 65, "3": 80,
    "4": 100, "5": 125, "6": 150, "8": 200, "10": 250, "12": 300, "14": 350, "16": 400,
    "18": 450, "20": 500, "24": 600,
}  # fmt: skip
DN_NPS: Final[dict[int, str]] = {v: k for k, v in NPS_DN.items()}

# PRD Appendix B.2 (SME to verify, D-06)
PRESSURE_CLASSES: Final = frozenset({150, 300, 600, 900, 1500, 2500})
STD_SCH40_MAX_DN: Final = 250
XS_SCH80_MAX_DN: Final = 200
KW_PER_HP: Final = 0.7457


def nps_to_dn(nps: str) -> int | None:
    """`4` -> 100, `1-1/2` -> 40; a size outside table B.1 is unknown (never guessed)."""
    return NPS_DN.get(nps)


def nb_to_dn(nb: int) -> int | None:
    """A nominal bore is accepted only if it is a DN of table B.1."""
    return nb if nb in DN_NPS else None


def pressure_class(value: int) -> int | None:
    return value if value in PRESSURE_CLASSES else None


def schedule_for(raw: str, dn: int | None) -> tuple[str, str | None]:
    """`STD` -> `40` only for DN <= 250, `XS` -> `80` only for DN <= 200; returns (value, note)."""
    if raw == "STD" and dn and dn <= STD_SCH40_MAX_DN:
        return "40", f"STD = SCH40 (DN{dn} <= {STD_SCH40_MAX_DN})"
    if raw == "XS" and dn and dn <= XS_SCH80_MAX_DN:
        return "80", f"XS = SCH80 (DN{dn} <= {XS_SCH80_MAX_DN})"
    return raw, None


def hp_to_kw(hp: float) -> float:
    """HP to kW at 0.7457, rounded to 0.1 kW as in the reference extractor."""
    return round(hp * KW_PER_HP, 1)


def uom_canonical(raw: str, dictionary: Dictionary) -> tuple[str | None, bool]:
    """(canonical UoM, ambiguous). Ambiguous aliases such as `MT` give (None, True)."""
    key = raw.strip().upper()
    if key in dictionary.uom_ambiguous:
        return None, True
    return dictionary.uom_aliases.get(key), False
