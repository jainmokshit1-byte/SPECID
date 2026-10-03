"""Tier-1 rule extraction (PRD 9.4, FR-301-303, FR-307, FR-1431; TRD TR-MOD-04).

The six category extractors are the reference extractors of PRD Appendix C (DEC-20). Every
conversion or inference is recorded as a note on the attribute, so the evidence card can cite it.
"""

import re
from collections.abc import Callable
from dataclasses import replace
from typing import Any, Final

from app.core.classify import CategoryModel, classify
from app.core.normalise import normalise
from app.core.types import AttrMeta, Dictionary, Spec
from app.core.units import hp_to_kw, nb_to_dn, nps_to_dn, pressure_class, schedule_for

Attrs = dict[str, Any]
Notes = dict[str, str]
Extractor = Callable[[str], tuple[Attrs, Notes, str]]

STOP: Final = frozenset({"ASTM", "TYPE", "FOR", "OF", "AND", "WITH", "TO", "THE", "A", "ON"})
_TOKEN = re.compile(r"[A-Z0-9][A-Z0-9.\-]*")
_CATEGORY_WORD = r"\b(VALVE|GASKET|FLANGE|PIPE|MOTOR)\b"


def _take(rx: str, t: str) -> tuple[re.Match[str] | None, str]:
    """Find `rx`, and remove the match from the text (consumed tokens are not residual)."""
    m = re.search(rx, t)
    return (m, t[: m.start()] + " " + t[m.end() :]) if m else (None, t)


def _note(notes: Notes, key: str, text: str | None) -> None:
    if text:
        notes[key] = text


def _size(t: str) -> tuple[int | None, str, str | None]:
    m, t2 = _take(r"\b((?:\d+[- ])?\d+/\d+|\d+)\s*IN\b", t)
    if m:
        nps = m.group(1).replace(" ", "-")
        dn = nps_to_dn(nps)
        return dn, t2, (f"{nps} IN = DN{dn}" if dn else f"{nps} IN is not a standard size")
    m, t2 = _take(r"\b(\d+)\s*NB\b", t)
    if m:
        nb = int(m.group(1))
        dn = nb_to_dn(nb)
        return (
            dn,
            t2,
            (f"{nb} NB = DN{nb}" if dn is not None else f"{nb} NB is not a standard size"),
        )
    return None, t, None


def _class(t: str) -> tuple[int | None, str]:
    m, t2 = _take(r"\bCL(\d{3,4})\b", t)
    return (pressure_class(int(m.group(1))), t2) if m else (None, t)


# PRD Appendix B.3 (reference `MAT`): pattern -> canonical code
_MATERIALS: Final = (
    (r"\bA216\s*(WCB|WCC)\b", "A216-{0}"),
    (r"\b(WCB|WCC)\b", "A216-{0}"),
    (r"\bA351\s*(CF8M|CF8)\b", "A351-{0}"),
    (r"\b(CF8M|CF8)\b", "A351-{0}"),
    (r"\bA182\s*F\s*(304L?|316L?|321|347)\b", "A182-F{0}"),
    (r"\bF(304L?|316L?|321|347)\b", "A182-F{0}"),
    (r"\bA105\b", "A105"),
    (r"\bA106\s*(?:GR)?\s*([ABC])\b", "A106-{0}"),
    (r"\bA106\b", "A106-?"),
    (r"\bA53\s*(?:GR)?\s*([AB])\b", "A53-{0}"),
    (r"\bSS\s*(304L?|316L?|321|347)\b", "SS{0}"),
    (r"\b(304L?|316L?|321|347)\s*SS\b", "SS{0}"),
)


def _material(t: str) -> tuple[str | None, str, str | None]:
    for rx, fmt in _MATERIALS:
        m, t2 = _take(rx, t)
        if m:
            code = fmt.format(*m.groups())
            written = m.group(0).replace(" ", "")
            same = written.startswith(code.split("-")[0])
            return code, t2, (None if same else f"{m.group(0)} -> {code}")
    return None, t, None


def _valve(t: str) -> tuple[Attrs, Notes, str]:
    a: Attrs = {}
    n: Notes = {}
    m, t = _take(r"\b(GATE|GLOBE|CHECK|BALL|BUTTERFLY)\b", t)
    if m:
        a["valve_type"] = m.group(1)
    else:
        m, t = _take(r"\b(GV|GLV|CV|BV)\b", t)
        a["valve_type"] = (
            {"GV": "GATE", "GLV": "GLOBE", "CV": "CHECK", "BV": "BALL"}[m.group(1)] if m else None
        )
        if m:
            _note(n, "valve_type", f"{m.group(1)} = {a['valve_type']}")
    a["size_dn"], t, note = _size(t)
    _note(n, "size_dn", note)
    a["pressure_class"], t = _class(t)
    a["body_material"], t, note = _material(t)
    _note(n, "body_material", note)
    fl, t = _take(r"\bFLANGED\b", t)
    face, t = _take(r"\b(RF|FF|RTJ)\b", t)
    if fl or face:
        a["end_connection"] = "FLANGED-" + (face.group(1) if face else "?")
    else:
        m, t = _take(r"\b(BW|SW|SCRD|THRD|NPT)\b", t)
        a["end_connection"] = {"BW": "BW", "SW": "SW"}.get(m.group(1), "THRD") if m else None
    m, t = _take(r"\bAPI\s*(600|602|603|6D|608|594)\b", t)
    a["design_standard"] = "API-" + m.group(1) if m else None
    m, t = _take(r"\bTRIM\s*([A-Z0-9]+)\b", t)
    a["trim"] = m.group(1) if m else None
    return a, n, t


def _pipe(t: str) -> tuple[Attrs, Notes, str]:
    a: Attrs = {}
    n: Notes = {}
    a["size_dn"], t, note = _size(t)
    _note(n, "size_dn", note)
    m, t = _take(r"\bSCH(\d+S?|STD|XS|XXS)\b", t)
    if m:
        s: str | None = m.group(1)
    else:
        m, t = _take(r"\b()(STD|XS|XXS)\b", t)  # bare STD / XS / XXS
        s = m.group(2) if m else None
    if s is not None:
        s, note = schedule_for(s, a["size_dn"])  # SME to verify (PRD B.2)
        _note(n, "schedule", note)
    a["schedule"] = s
    a["material"], t, note = _material(t)
    _note(n, "material", note)
    m, t = _take(r"\b(SEAMLESS|ERW|WELDED)\b", t)
    p = {"SEAMLESS": "SEAMLESS", "ERW": "WELDED", "WELDED": "WELDED"}[m.group(1)] if m else None
    if p is None and (a["material"] or "").startswith("A106"):
        p = "SEAMLESS"  # spec-implied
        _note(n, "process", "implied by A106")
    a["process"] = p
    m, t = _take(r"\b(PE|BE|PBE|TBE)\b", t)
    a["end_finish"] = m.group(1) if m else None
    return a, n, t


_FLANGE_TYPES: Final = (
    (r"\bWELD\s*NECK\b|\bWN\b", "WN"),
    (r"\bSLIP\s*-?\s*ON\b|\bSO\b", "SO"),
    (r"\bBLIND\b|\bBL\b", "BLIND"),
    (r"\bLAP\s*JOINT\b|\bLJ\b", "LJ"),
    (r"\bSOCKET\s*WELD\b|\bSW\b", "SW"),
    (r"\bTHREADED\b|\bTHRD\b|\bSCRD\b", "THRD"),
)


def _flange(t: str) -> tuple[Attrs, Notes, str]:
    a: Attrs = {}
    n: Notes = {}
    typ = None
    for rx, value in _FLANGE_TYPES:
        m, t = _take(rx, t)
        if m:
            typ = value
            break
    a["flange_type"] = typ
    a["size_dn"], t, note = _size(t)
    _note(n, "size_dn", note)
    a["pressure_class"], t = _class(t)
    m, t = _take(r"\b(RF|FF|RTJ)\b", t)
    a["face"] = m.group(1) if m else None
    a["material"], t, note = _material(t)
    _note(n, "material", note)
    return a, n, t


def _fastener(t: str) -> tuple[Attrs, Notes, str]:
    a: Attrs = {}
    n: Notes = {}
    m, t = _take(r"\b(STUD|NUT|BOLT|SCREW)\b", t)
    a["fastener_type"] = m.group(1) if m else None
    m, t = _take(r"\bM(\d{1,2})\s*X\s*(\d{1,3})\b", t)
    if m:
        a["thread"], a["length_mm"] = "M" + m.group(1), int(m.group(2))
    else:
        m, t = _take(r"\bM(\d{1,2})\b", t)
        a["thread"] = "M" + m.group(1) if m else None
        a["length_mm"] = None
    m, t = _take(r"\b(?:A19[34]\s*)?(?:GR)?(4\.6|5\.6|8\.8|10\.9|12\.9|B7|2H)\b", t)
    a["strength"] = m.group(1) if m else None
    m, t = _take(r"\b(HEX|SOCKET|CSK)\b", t)
    a["head"] = m.group(1) if m else None
    _, t = _take(r"\bHEAD\b", t)
    m, t = _take(r"\b(ZN|ZINC|HDG|PTFE|GALV\w*)\b", t)
    a["coating"] = ("ZINC" if m.group(1) in ("ZN", "ZINC") else m.group(1)) if m else None
    _, t = _take(r"\bPLATED\b", t)
    if m and m.group(1) == "ZN":
        _note(n, "coating", "ZN = ZINC")
    return a, n, t


def _motor(t: str) -> tuple[Attrs, Notes, str]:
    a: Attrs = {}
    n: Notes = {}
    ind = bool(re.search(r"\b(INDUCTION|IND|SQ|SQUIRREL)\b", t))
    ac = bool(re.search(r"\bAC\b", t))
    a["motor_type"] = "AC-IND" if (ind and ac) else ("AC" if ac else None)
    for word in ("AC", "INDUCTION", "IND", "SQ", "SQUIRREL", "CAGE"):
        _, t = _take(rf"\b{word}\b", t)
    m, t = _take(r"\b(\d+(?:\.\d+)?)\s*KW\b", t)
    if m:
        a["power_kw"] = float(m.group(1))
    else:
        m, t = _take(r"\b(\d+(?:\.\d+)?)\s*HP\b", t)
        a["power_kw"] = hp_to_kw(float(m.group(1))) if m else None
        if m:
            _note(n, "power_kw", f"{m.group(1)} HP = {a['power_kw']} kW")
    m, t = _take(r"\b(\d{1,2})\s*(?:P|POLES?)\b", t)
    a["poles"] = int(m.group(1)) if m else None
    m, t = _take(r"\b(\d{3,4})\s*RPM\b", t)
    a["rpm"] = int(m.group(1)) if m else None
    m, t = _take(r"\b(\d{3,4})\s*V\b", t)
    a["voltage"] = int(m.group(1)) if m else None
    m, t = _take(r"\bIP\s*(\d{2})\b", t)
    a["ip"] = "IP" + m.group(1) if m else None
    m, t = _take(r"\b(B3|B5|B35|V1)\b", t)
    a["mounting"] = m.group(1) if m else None
    a["ex"] = a["frame"] = None
    return a, n, t


def _gasket(t: str) -> tuple[Attrs, Notes, str]:
    a: Attrs = {}
    n: Notes = {}
    m, t = _take(r"\bSPIRAL\s*WOUND\b|\bSPIRAL\b", t)
    a["gasket_type"] = "SPIRAL-WOUND" if m else None
    a["size_dn"], t, note = _size(t)
    _note(n, "size_dn", note)
    a["pressure_class"], t = _class(t)
    a["winding_material"], t, note = _material(t)
    _note(n, "winding_material", note)
    m, t = _take(r"\b(GRAPHITE|PTFE)\b", t)
    a["filler"] = m.group(1) if m else None
    return a, n, t


EXTRACTORS: Final[dict[str, Extractor]] = {
    "VALVE": _valve,
    "PIPE": _pipe,
    "FLANGE": _flange,
    "FASTENER": _fastener,
    "MOTOR": _motor,
    "GASKET": _gasket,
}


def extract(
    text: str,
    mpn: str | None = None,
    maker: str | None = None,
    *,
    dictionary: Dictionary,
    model: CategoryModel | None,
    threshold: float,
) -> Spec:
    """Normalise -> classify -> category extractor -> residual tokens (minus stop words)."""
    t = normalise(text, dictionary)
    category, source, prob = classify(t, model, threshold)
    if category is None or category not in EXTRACTORS:
        return Spec(None, {}, {}, tuple(_TOKEN.findall(t)), mpn, maker, "NONE", prob)
    if category != "FASTENER":
        _, t = _take(_CATEGORY_WORD, t)
    attrs, notes, t = EXTRACTORS[category](t)
    meta = {
        k: AttrMeta(tier="RULE", confidence=1.0, note=notes.get(k))
        for k in attrs
        if attrs[k] is not None or k in notes
    }
    residual = tuple(x for x in _TOKEN.findall(t) if x not in STOP)
    return Spec(category, attrs, meta, residual, mpn, maker, source, prob)


def supply_attribute(spec: Spec, attr: str, value: Any, source: str) -> Spec:
    """Ask, don't guess (PRD 9.13.3): a reviewer supplies a value with its source.

    Provenance is kept (`tier = USER`, note `supplied by user: <source>`). The source note is
    mandatory; its 5-character minimum is enforced by the database and the service (DEC-22).
    """
    if not source or not source.strip():
        raise ValueError("a source note is required to supply an attribute")
    return replace(
        spec,
        attrs={**spec.attrs, attr: value},
        meta={
            **spec.meta,
            attr: AttrMeta(tier="USER", confidence=1.0, note=f"supplied by user: {source}"),
        },
    )
