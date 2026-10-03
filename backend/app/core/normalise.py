"""Normaliser (PRD 9.2, FR-201, TRD TR-MOD-01).

The ordered rules of PRD 9.2 as in the reference `normalise` (PRD Appendix C), in the same
order. Whole-word expansions come from the versioned dictionary, not from literals. Before the
rules, Unicode NFKC is applied and non-printing characters are removed (TR-MOD-01; DEC-21 DEV-3).

One pass of the rules is not idempotent on every input (`1/2 #` -> `1/CL2` -> `1 CL2`), so the
pass repeats until the output stops changing, at most `MAX_PASSES` times (DEC-24 DEV-4).
"""

import hashlib
import re
import unicodedata

import structlog

from app.core.types import Dictionary

MAX_PASSES = 8

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


def _one_pass(text: str, dictionary: Dictionary) -> str:
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


def normalise_passes(text: str, dictionary: Dictionary) -> tuple[str, int]:
    """(normalised text, passes run). The last pass is the one that changed nothing.

    If the output still changes after `MAX_PASSES` passes, the last result is returned and a
    warning is logged with the SHA-256 of the input (never the text itself).
    """
    t = _one_pass(text, dictionary)
    for passes in range(2, MAX_PASSES + 1):
        nxt = _one_pass(t, dictionary)
        if nxt == t:
            return t, passes
        t = nxt
    structlog.get_logger(__name__).warning(
        "normalise_max_passes_reached",
        input_sha256=hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest(),
        passes=MAX_PASSES,
        dictionary_version=dictionary.version,
    )
    return t, MAX_PASSES


def normalise(text: str, dictionary: Dictionary) -> str:
    return normalise_passes(text, dictionary)[0]
