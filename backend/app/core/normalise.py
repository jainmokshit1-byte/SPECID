"""Normaliser (PRD 9.2, FR-201, TRD TR-MOD-01).

The ordered rules of PRD 9.2 as in the reference `normalise` (PRD Appendix C), in the same
order. Whole-word expansions come from the versioned dictionary, not from literals. Before the
rules, Unicode NFKC is applied and non-printing characters are removed (TR-MOD-01; DEC-21 DEV-3).

One pass of the rules is not idempotent on every input (`1/2 #` -> `1/CL2` -> `1 CL2`), so the
pass repeats until the output stops changing, at most `MAX_PASSES` times (DEC-24 DEV-4).

Before the rules, misspelt engineering words are repaired (DEC-34 DEV-6): `LFANGE` -> `FLANGE`,
`CLSAS` -> `CLASS`, `INDUCTINO` -> `INDUCTION`. A word is repaired only when exactly one word of
the dictionary's spelling list is one edit away (two neighbouring letters swapped, or for words
of five letters or more also one letter changed, added or removed). Words in the spelling list,
protected words (`STUB` is not `STUD`), words with a digit and words under four letters are never
touched. A repair can only turn an unreadable word into a readable one; it never changes a word
that already means something.
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
_WORD = re.compile(r"\b[A-Z]{4,}\b")  # alphabetic words only: numbers are never repaired
MIN_EDIT_LEN = 5  # shorter words get only the neighbour-swap repair (PIEP -> PIPE)


def _clean(text: str) -> str:
    """NFKC, drop non-printing characters (whitespace is kept for rule 10), upper-case."""
    t = unicodedata.normalize("NFKC", text)
    t = "".join(ch for ch in t if ch.isprintable() or ch.isspace())
    return unicodedata.normalize("NFKC", t.upper())


def _swapped(a: str, b: str) -> bool:
    """`a` is `b` with two neighbouring letters swapped."""
    if len(a) != len(b) or a == b:
        return False
    diff = [i for i in range(len(a)) if a[i] != b[i]]
    return (
        len(diff) == 2
        and diff[1] == diff[0] + 1
        and a[diff[0]] == b[diff[1]]
        and (a[diff[1]] == b[diff[0]])
    )


def _one_edit(a: str, b: str) -> bool:
    """`a` and `b` differ by one neighbour swap, or one changed, added or removed letter."""
    if a == b or abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return _swapped(a, b) or sum(x != y for x, y in zip(a, b, strict=True)) == 1
    short, long = (a, b) if len(a) < len(b) else (b, a)
    return any(long[:i] + long[i + 1 :] == short for i in range(len(long)))


def _repair_word(word: str, dictionary: Dictionary) -> str | None:
    known = dictionary.spelling
    if word in known or word in dictionary.spelling_protected or word in dictionary.abbreviations:
        return None
    near = _one_edit if len(word) >= MIN_EDIT_LEN else _swapped
    candidates = [k for k in known if near(word, k)]
    return candidates[0] if len(candidates) == 1 else None


def repair_spelling(text: str, dictionary: Dictionary) -> tuple[str, tuple[str, ...]]:
    """(text with misspelt engineering words repaired, the repairs as "OLD -> NEW").

    `text` is upper-case (after `_clean`). Without a spelling list nothing changes."""
    if not dictionary.spelling:
        return text, ()
    repairs: list[str] = []

    def fix(m: re.Match[str]) -> str:
        new = _repair_word(m.group(0), dictionary)
        if new is None:
            return m.group(0)
        repairs.append(f"{m.group(0)} -> {new}")
        return new

    return _WORD.sub(fix, text), tuple(repairs)


def _one_pass(text: str, dictionary: Dictionary) -> str:
    t = _clean(text)  # rule 1 (upper-case) included
    t = repair_spelling(t, dictionary)[0]  # DEC-34 DEV-6, before the PRD 9.2 rules
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


def spelling_repairs(text: str, dictionary: Dictionary) -> tuple[str, ...]:
    """The spelling repairs `normalise` applies to `text`, for the evidence card (DEC-34)."""
    out: list[str] = []
    t = text
    for _ in range(MAX_PASSES):
        cleaned = _clean(t)
        _, found = repair_spelling(cleaned, dictionary)
        out.extend(r for r in found if r not in out)
        nxt = _one_pass(t, dictionary)
        if nxt == t:
            break
        t = nxt
    return tuple(out)
