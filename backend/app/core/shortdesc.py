"""Short (40-character, SAP-ready) and long descriptions (PRD 9.9, FR-901, TRD TR-MOD-09).

`short_desc` is the reference `short_desc` (PRD Appendix C), except that parts whose value is
missing are left out instead of printed as `None` or `?IN` (DEC-21 DEV-1). A text longer than
the limit, or an empty one, gives None: the item is flagged for manual abbreviation and is
never truncated.
"""

from typing import Any

from app.core.types import Spec
from app.core.units import DN_NPS

_PROCESS = {"SEAMLESS": "SMLS", "WELDED": "ERW"}


def _inch(a: dict[str, Any]) -> str | None:
    dn = a.get("size_dn")
    nps = DN_NPS.get(dn) if isinstance(dn, int) else None
    return f"{nps}IN" if nps else None


def _pre(prefix: str, value: Any) -> str | None:
    return f"{prefix}{value}" if value is not None else None


def short_desc(spec: Spec, limit: int = 40) -> str | None:
    a, c = spec.attrs, spec.category
    end = a.get("end_connection")
    thread, length = a.get("thread"), a.get("length_mm")
    motor, kw, poles = a.get("motor_type"), a.get("power_kw"), a.get("poles")
    parts: dict[str | None, list[str | None]] = {
        "VALVE": [
            "VLV",
            a.get("valve_type"),
            _inch(a),
            _pre("CL", a.get("pressure_class")),
            a.get("body_material"),
            end.replace("FLANGED-", "FLGD ") if end else None,
        ],
        "PIPE": [
            "PIPE",
            _PROCESS.get(a.get("process") or ""),
            _inch(a),
            _pre("SCH", a.get("schedule")),
            a.get("material"),
        ],
        "FLANGE": [
            "FLG",
            a.get("flange_type"),
            _inch(a),
            _pre("CL", a.get("pressure_class")),
            a.get("face"),
            a.get("material"),
        ],
        "FASTENER": [
            a.get("fastener_type"),
            a.get("head"),
            f"{thread}X{length}" if thread and length else thread,
            a.get("strength"),
            {"ZINC": "ZN"}.get(a.get("coating") or "", a.get("coating")),
        ],
        "MOTOR": [
            "MOTOR",
            motor.replace("-", " ") if motor else None,
            f"{kw:g}KW" if kw else None,
            f"{poles}P" if poles is not None else None,
        ],
        "GASKET": [
            "GASKET",
            "SPW",
            _inch(a),
            _pre("CL", a.get("pressure_class")),
            a.get("winding_material"),
            (a.get("filler") or "")[:5],
        ],
    }
    if c not in parts:
        return None
    s = " ".join(p for p in parts[c] if p)
    return s if 0 < len(s) <= limit else None


# ---- long description: full words in a fixed order per category (PRD 9.9) ----
_END = {
    "FLANGED-RF": "FLANGED RAISED FACE",
    "FLANGED-FF": "FLANGED FLAT FACE",
    "FLANGED-RTJ": "FLANGED RING TYPE JOINT",
    "FLANGED-?": "FLANGED",
    "BW": "BUTT WELD",
    "SW": "SOCKET WELD",
    "THRD": "THREADED",
}
_FACE = {"RF": "RAISED FACE", "FF": "FLAT FACE", "RTJ": "RING TYPE JOINT"}
_FLANGE = {
    "WN": "WELD NECK",
    "SO": "SLIP ON",
    "BLIND": "BLIND",
    "LJ": "LAP JOINT",
    "SW": "SOCKET WELD",
    "THRD": "THREADED",
}
_FINISH = {
    "PE": "PLAIN END",
    "BE": "BEVELLED END",
    "PBE": "PLAIN BOTH ENDS",
    "TBE": "THREADED BOTH ENDS",
}


def _size(a: dict[str, Any]) -> str | None:
    dn = a.get("size_dn")
    if dn is None:
        return None
    nps = DN_NPS.get(dn)
    return f"{nps} IN (DN{dn})" if nps else f"DN{dn}"


def _material(code: Any) -> str | None:
    """`A216-WCB` -> `ASTM A216 WCB`; generic codes (`SS316`, `A106-?`) stay as written."""
    if not code:
        return None
    text = str(code)
    if text[0] == "A" and text[1:2].isdigit() and not text.endswith("?"):
        return "ASTM " + text.replace("-", " ")
    return text


def long_desc(spec: Spec) -> str:
    """Built from the canonical spec only; missing attributes are left out, nothing is invented."""
    a, c = spec.attrs, spec.category
    kw, poles, rpm, volt = a.get("power_kw"), a.get("poles"), a.get("rpm"), a.get("voltage")
    parts: dict[str | None, list[str | None]] = {
        "VALVE": [
            f"{a['valve_type']} VALVE" if a.get("valve_type") else "VALVE",
            _size(a),
            _pre("CLASS ", a.get("pressure_class")),
            _material(a.get("body_material")),
            _END.get(a.get("end_connection") or ""),
            (a.get("design_standard") or "").replace("-", " ") or None,
            _pre("TRIM ", a.get("trim")),
        ],
        "PIPE": [
            "PIPE",
            a.get("process"),
            _size(a),
            _pre("SCH ", a.get("schedule")),
            _material(a.get("material")),
            _FINISH.get(a.get("end_finish") or ""),
        ],
        "FLANGE": [
            (
                f"{_FLANGE.get(a.get('flange_type') or '', a.get('flange_type'))} FLANGE"
                if a.get("flange_type")
                else "FLANGE"
            ),
            _size(a),
            _pre("CLASS ", a.get("pressure_class")),
            _FACE.get(a.get("face") or ""),
            _material(a.get("material")),
        ],
        "FASTENER": [
            " ".join(p for p in (a.get("head"), a.get("fastener_type") or "FASTENER") if p),
            (
                f"{a['thread']} X {a['length_mm']} MM"
                if a.get("thread") and a.get("length_mm")
                else a.get("thread")
            ),
            _pre("GRADE ", a.get("strength")),
            a.get("coating"),
        ],
        "MOTOR": [
            {"AC-IND": "AC INDUCTION MOTOR", "AC": "AC MOTOR"}.get(
                a.get("motor_type") or "", "MOTOR"
            ),
            f"{kw:g} KW" if kw else None,
            f"{poles} POLE" if poles else None,
            f"{rpm} RPM" if rpm else None,
            f"{volt} V" if volt else None,
            a.get("ip"),
            a.get("mounting"),
        ],
        "GASKET": [
            "SPIRAL WOUND GASKET" if a.get("gasket_type") == "SPIRAL-WOUND" else "GASKET",
            _size(a),
            _pre("CLASS ", a.get("pressure_class")),
            _material(a.get("winding_material")),
            f"{a['filler']} FILLER" if a.get("filler") else None,
        ],
    }
    return ", ".join(p for p in parts.get(c, []) if p)
