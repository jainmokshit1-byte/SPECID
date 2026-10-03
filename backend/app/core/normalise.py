"""Normaliser (PRD 9.2, FR-201, TRD TR-MOD-01).

The ordered rules of PRD 9.2 as in the reference `normalise` (PRD Appendix C). Whole-word
expansions come from the versioned dictionary, not from literals. Before the rules, Unicode
NFKC is applied and non-printing characters are removed (TR-MOD-01; DEC-21 DEV-3).
"""

import re
import unicodedata

from app.core.types import Dictionary

_QUOTES = re.compile(r'["“”]')
_PUNCT = re.compile(r"[,;()]")
_SLASH = re.compile(r"/(?=[A-Z])")  # SS316/GRAF -> SS316 GRAF (fractions keep their slash)
_INCH = re.compile(r"(\d)\s*(?:INCHES|INCH|IN)\b")  # 4IN, 4 INCH -> 4 IN
_DN = re.compile(r"\bDN\s*(\d+)\b")  # DN100 -> 100 NB
_NB = re.compile(r"(\d)\s*NB\b")
_HASH = re.compile(r"(\d+)\s*#")  # 150# -> CL150
_CLASS = re.compile(r"\bCLASS\s*(\d+)")
_CL = re.compile(r"\bCL\s+(\d+)")
_SCH = re.compile(r"\bSCH(?:EDULE)?\.?\s*(\d+S?|STD|XS|XXS)\b")
_GRADE = re.compile(r"\bGR(?:ADE)?\.?\s*([A-Z0-9][A-Z0-9.]*)")  # GR.B / GRADE B -> GRB
_SPACE = re.compile(r"\s+")


def _clean(text: str) -> str:
    """NFKC, drop non-printing characters (whitespace is kept for rule 10), upper-case."""
    t = unicodedata.normalize("NFKC", text)
    t = "".join(ch for ch in t if ch.isprintable() or ch.isspace())
    return unicodedata.normalize("NFKC", t.upper())


def normalise(text: str, dictionary: Dictionary) -> str:
    t = _clean(text)  # rule 1 (upper-case) included
    t = _QUOTES.sub(" IN ", t)  # rule 2
    t = _PUNCT.sub(" ", t)
    t = _SLASH.sub(" ", t)  # rule 3
    t = _INCH.sub(r"\1 IN", t)  # rule 4
    t = _DN.sub(r"\1 NB", t)  # rule 5
    t = _NB.sub(r"\1 NB", t)
    t = _HASH.sub(r"CL\1", t)  # rule 6
    t = _CLASS.sub(r"CL\1", t)
    t = _CL.sub(r"CL\1", t)
    t = _SCH.sub(r"SCH\1", t)  # rule 7
    t = _GRADE.sub(r"GR\1", t)  # rule 8
    for abbr, expansion in dictionary.abbreviations.items():  # rule 9
        t = re.sub(rf"\b{re.escape(abbr)}\b", expansion, t)
    return _SPACE.sub(" ", t).strip()  # rule 10
