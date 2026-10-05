"""Seeded synthetic generator v1 (PRD 10.1, FR-1101, FR-107; TRD TR-TST-07; DEC-33).

SYNTHETIC DATA. Written by the team that wrote the extraction rules, so results on it are
optimistic by construction (PRD 10 honesty rule). No real CPSE data, makers or part numbers.

Same seed + config -> byte-identical files (`manifest.json` holds the SHA-256 of each file).
Defaults follow PRD 10.1 except `n_entities = 1200` (about 3,000 records, DEC-09).

v1 adds purchase history (`procurement_<cpse>.csv`), stock on hand and annual quantity per
record. They come from a second random stream, so codes, texts and both truth files are
byte-identical to v0 for the same seed (only the record files gain columns).
"""

import csv
import datetime as dt
import hashlib
import io
import json
import random
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any

from app.core.units import DN_NPS, schedule_for

GENERATOR_VERSION = "0.2.0"
RECORD_COLUMNS = (
    "legacy_code short_text long_text uom mat_group manufacturer mpn plant criticality "
    "annual_value annual_qty stock_qty"
).split()
PROCUREMENT_COLUMNS = "legacy_code po_date qty uom unit_price currency vendor plant".split()
HONESTY = (
    "Synthetic data written by the team that wrote the rules; optimistic by construction; "
    "not a measure of performance on real CPSE data."
)


@dataclass(frozen=True)
class GeneratorConfig:
    seed: int = 7
    n_entities: int = 1200  # PRD default 4,000; DEC-09 memory decision
    category_mix: tuple[tuple[str, float], ...] = (
        ("VALVE", 0.25),
        ("PIPE", 0.25),
        ("FLANGE", 0.20),
        ("FASTENER", 0.20),
        ("MOTOR", 0.10),
    )
    cpses: tuple[str, ...] = ("A", "B", "C")  # one style profile per CPSE
    presence: tuple[float, float, float] = (0.4, 0.4, 0.2)  # in 1 / 2 / 3 CPSEs
    within_dup_rate: float = 0.10
    hard_negative_share: float = 0.30
    drop_ext_rate: float = 0.30
    drop_core_rate: float = 0.05
    typo_rate: float = 0.02
    make_rate: float = 0.40
    splits: tuple[tuple[str, float], ...] = (("train", 0.6), ("validation", 0.2), ("test", 0.2))
    # v1: purchase history and stock (second random stream, DEC-33)
    as_of: str = "2026-09-30"  # history ends here; fixed so files stay reproducible
    history_months: int = 24
    dormant_rate: float = 0.15  # no purchase in the last 12 months
    stock_rate: float = 0.45  # active records holding some stock
    idle_stock_rate: float = 0.60  # dormant records still holding stock
    cpse_price_bias: tuple[tuple[str, float], ...] = (("A", 0.94), ("B", 1.12), ("C", 1.03))


# ---- value domains (PRD 10.1; SME review required) ----
_DNS = sorted(DN_NPS)
_KW = [5.5, 7.5, 11.0, 15.0, 18.5, 22.0, 30.0, 37.0, 45.0, 55.0, 75.0, 90.0, 110.0, 132.0, 160.0]
_RATED_RPM = {2: 2950, 4: 1475, 6: 980, 8: 735}  # 50 Hz synchronous less slip (PRD B.2)
_THREADS = ["M12", "M16", "M20", "M24", "M30"]
_FASTENER_STRENGTH = {"BOLT": ["8.8", "10.9"], "STUD": ["B7"], "NUT": ["2H"]}
CORE: dict[str, tuple[str, ...]] = {
    "VALVE": ("valve_type", "size_dn", "pressure_class", "body_material", "end_connection"),
    "PIPE": ("size_dn", "schedule", "material", "process"),
    "FLANGE": ("flange_type", "size_dn", "pressure_class", "face", "material"),
    "FASTENER": ("fastener_type", "thread", "length_mm", "strength"),
    "MOTOR": ("motor_type", "power_kw", "poles"),
}
EXTENDED: dict[str, tuple[str, ...]] = {
    "VALVE": (),
    "PIPE": (),
    "FLANGE": (),
    "FASTENER": ("head", "coating"),
    "MOTOR": ("rpm", "voltage"),
}


def _sample(cat: str, rng: random.Random) -> dict[str, Any]:
    if cat == "VALVE":
        return {
            "valve_type": rng.choice(["GATE", "GLOBE", "CHECK", "BALL"]),
            "size_dn": rng.choice(_DNS),
            "pressure_class": rng.choice([150, 300, 600]),
            "body_material": rng.choice(["A216-WCB", "A351-CF8M"]),
            "end_connection": rng.choice(["FLANGED-RF", "BW"]),
        }
    if cat == "PIPE":
        dn = rng.choice(_DNS)
        material = rng.choice(["A106-B", "A53-B"])
        return {
            "size_dn": dn,
            "schedule": schedule_for(rng.choice(["40", "80", "STD", "XS"]), dn)[0],
            "material": material,
            # A106 is seamless pipe; A53 comes seamless or welded
            "process": "SEAMLESS" if material == "A106-B" else rng.choice(["SEAMLESS", "WELDED"]),
        }
    if cat == "FLANGE":
        return {
            "flange_type": rng.choice(["WN", "SO", "BLIND"]),
            "size_dn": rng.choice(_DNS),
            "pressure_class": rng.choice([150, 300, 600]),
            "face": rng.choice(["RF", "FF"]),
            "material": rng.choice(["A105", "A182-F316"]),
        }
    if cat == "FASTENER":
        typ = rng.choice(["BOLT", "STUD", "NUT"])
        return {
            "fastener_type": typ,
            "thread": rng.choice(_THREADS),
            "length_mm": None if typ == "NUT" else rng.randrange(20, 201, 10),
            "strength": rng.choice(_FASTENER_STRENGTH[typ]),
            "head": None if typ == "STUD" else "HEX",
            "coating": rng.choice(["ZINC", "HDG", None]),
        }
    poles = rng.choice([2, 4, 6, 8])
    return {
        "motor_type": "AC-IND",
        "power_kw": rng.choice(_KW),
        "poles": poles,
        "rpm": _RATED_RPM[poles],
        "voltage": rng.choice([415, 690]),
    }


def _neighbour(cat: str, attrs: dict[str, Any], rng: random.Random) -> dict[str, Any]:
    """A hard negative: the same spec with exactly one core attribute changed."""
    while True:
        n = dict(attrs)
        choices = [a for a in CORE[cat] if not (a == "length_mm" and attrs[a] is None)]
        choices = [a for a in choices if a != "motor_type"]
        attr = rng.choice(choices)
        fresh = _sample(cat, rng)
        if attr == "size_dn" and cat == "PIPE":
            # STD / XS depend on DN: keep only sizes where the canonical schedule stays the same
            if schedule_for(attrs["schedule"], fresh["size_dn"])[0] != attrs["schedule"]:
                continue
        if attr == "fastener_type":
            continue  # changing the type changes the category word; not a near miss
        if attr == "poles":
            n["rpm"] = _RATED_RPM[fresh["poles"]]
        if attr == "schedule":  # canonical for THIS entity's size (STD = SCH40 up to DN250)
            raw = rng.choice(["40", "80", "STD", "XS"])
            fresh["schedule"] = schedule_for(raw, attrs["size_dn"])[0]
        n[attr] = fresh[attr]
        if attr == "material" and cat == "PIPE" and n["material"] == "A106-B":
            n["process"] = "SEAMLESS"
        if attr == "process" and n["material"] == "A106-B":
            continue
        if _core_key(cat, n) != _core_key(cat, attrs):
            return n


def _core_key(cat: str, attrs: dict[str, Any]) -> tuple[Any, ...]:
    return (cat, *(attrs[a] for a in CORE[cat]))


# ---- rendering: one style profile per CPSE (PRD 10.1) ----
Part = tuple[str | None, str]  # (attribute or None for fixed words, text)


def _size(dn: int, style: str) -> str:
    nps = DN_NPS[dn]
    return {"A": f"{nps}IN", "B": f"{nps} INCH", "C": f"{dn}NB"}[style]


_MATERIAL = {  # canonical -> (style A, style B, style C)
    "A216-WCB": ("A216 WCB", "ASTM A216 WCB", "WCB"),
    "A351-CF8M": ("A351 CF8M", "ASTM A351 CF8M", "CF8M"),
    "A105": ("A105", "ASTM A105", "A105"),
    "A182-F316": ("A182 F316", "ASTM A182 F316", "F316"),
    "A106-B": ("A106 GR.B", "ASTM A106 GRADE B", "A106B"),
    "A53-B": ("A53 GR.B", "ASTM A53 GRADE B", "A53B"),
}
_FACE_WORDS = {"RF": "RAISED FACE", "FF": "FLAT FACE"}


def _mat(code: str, style: str) -> str:
    return _MATERIAL[code]["ABC".index(style)]


def _valve(a: dict[str, Any], style: str, rng: random.Random) -> list[Part]:
    typ, cls, end = a["valve_type"], a["pressure_class"], a["end_connection"]
    if end == "BW":
        end_text = "BW"
    else:
        face = end.split("-")[1]
        end_text = {
            "A": f"FLGD {face}",
            "B": f"{_FACE_WORDS[face]} FLANGED",
            "C": f"{face} FLANGED",
        }[style]
    abbr = {"GATE": "GV", "GLOBE": "GLV", "BALL": "BV"}.get(typ)  # CV is not a category word
    if style == "A":
        return [
            (None, "VALVE"),
            ("valve_type", typ),
            ("size_dn", _size(a["size_dn"], "A")),
            ("pressure_class", f"CL{cls}"),
            ("body_material", _mat(a["body_material"], "A")),
            ("end_connection", end_text),
        ]
    if style == "B":
        return [
            ("valve_type", f"{typ} VALVE,"),
            ("size_dn", _size(a["size_dn"], "B") + ","),
            ("pressure_class", f"CLASS {cls},"),
            ("body_material", _mat(a["body_material"], "B") + ","),
            ("end_connection", end_text),
        ]
    head: Part = ("valve_type", abbr) if abbr else ("valve_type", f"{typ} VALVE")
    return [
        head,
        ("size_dn", _size(a["size_dn"], "C")),
        ("pressure_class", f"{cls}#"),
        ("body_material", _mat(a["body_material"], "C")),
        ("end_connection", end_text),
    ]


def _schedule_text(a: dict[str, Any], style: str, rng: random.Random) -> str:
    s, dn = a["schedule"], a["size_dn"]
    if style == "C" and s == "40" and dn <= 250 and rng.random() < 0.5:
        return "STD"  # STD = SCH40 for DN <= 250
    if style == "C" and s == "80" and dn <= 200 and rng.random() < 0.5:
        return "XS"
    return {"A": f"SCH{s}", "B": f"SCHEDULE {s}", "C": f"SCH {s}"}[style]


def _pipe(a: dict[str, Any], style: str, rng: random.Random) -> list[Part]:
    proc = {"SEAMLESS": ("SMLS", "SEAMLESS", "SMLS"), "WELDED": ("ERW", "WELDED", "ERW")}
    p = proc[a["process"]]["ABC".index(style)]
    implied = a["material"] == "A106-B" and style == "C" and rng.random() < 0.5
    process: list[Part] = [] if implied else [("process", p)]  # A106 implies SEAMLESS
    size, sch = ("size_dn", _size(a["size_dn"], style)), ("schedule", _schedule_text(a, style, rng))
    mat = ("material", _mat(a["material"], style))
    if style == "A":
        return [(None, "PIPE"), *process, size, sch, mat]
    if style == "B":
        parts: list[Part] = [
            (None, "PIPE,"),
            *[(k, v + ",") for k, v in process],
            (size[0], size[1] + ","),
            (sch[0], sch[1] + ","),
            mat,
        ]
        return parts
    return [(None, "PIPE"), size, sch, mat, *process]


def _flange(a: dict[str, Any], style: str, rng: random.Random) -> list[Part]:
    typ, cls, face = a["flange_type"], a["pressure_class"], a["face"]
    if style == "A":
        return [
            (None, "FLANGE"),
            ("flange_type", typ),
            ("size_dn", _size(a["size_dn"], "A")),
            ("pressure_class", f"CL{cls}"),
            ("face", face),
            ("material", _mat(a["material"], "A")),
        ]
    if style == "B":
        words = {"WN": "WELD NECK", "SO": "SLIP ON", "BLIND": "BLIND"}[typ]
        return [
            ("flange_type", f"{words}"),
            (None, "FLANGE,"),
            ("size_dn", _size(a["size_dn"], "B") + ","),
            ("pressure_class", f"CLASS {cls},"),
            ("face", _FACE_WORDS[face] + ","),
            ("material", _mat(a["material"], "B")),
        ]
    return [
        ("flange_type", typ),
        (None, "FLANGE"),
        ("size_dn", _size(a["size_dn"], "C")),
        ("pressure_class", f"{cls}#"),
        ("face", face),
        ("material", _mat(a["material"], "C")),
    ]


def _fastener(a: dict[str, Any], style: str, rng: random.Random) -> list[Part]:
    typ, thread, length, strength = a["fastener_type"], a["thread"], a["length_mm"], a["strength"]
    grade = {"B7": "A193 B7", "2H": "A194 2H"}.get(strength)
    coat = {"ZINC": ("ZN", "ZINC PLATED", "ZN"), "HDG": ("HDG", "HDG", "HDG")}
    coating = [("coating", coat[a["coating"]]["ABC".index(style)])] if a["coating"] else []
    head = [("head", "HEX")] if a["head"] else []
    if style == "A":
        size = f"{thread}X{length}" if length else thread
        return [
            ("fastener_type", typ),
            *head,
            ("thread", size),
            ("strength", grade or f"GR{strength}"),
            *coating,
        ]
    if style == "B":
        size = f"{thread} X {length}" if length else thread
        head_b = [("head", "HEX HEAD,")] if a["head"] else []
        return [
            ("fastener_type", typ + ","),
            *head_b,
            ("thread", size + ","),
            ("strength", (grade or f"GRADE {strength}") + ("," if coating else "")),
            *coating,
        ]
    size = f"{thread}X{length}" if length else thread
    return [
        ("fastener_type", typ),
        ("thread", size),
        ("strength", grade or strength),
        *head,
        *coating,
    ]


def _motor(a: dict[str, Any], style: str, rng: random.Random) -> list[Part]:
    kw, poles, rpm, volt = a["power_kw"], a["poles"], a["rpm"], a["voltage"]
    if style == "A":
        return [
            (None, "MOTOR AC IND"),
            ("power_kw", f"{kw:g}KW"),
            ("poles", f"{poles}P"),
            ("rpm", f"{rpm}RPM"),
            ("voltage", f"{volt}V"),
        ]
    if style == "B":
        return [
            (None, "AC INDUCTION MOTOR,"),
            ("power_kw", f"{kw:g} KW,"),
            ("poles", f"{poles} POLE,"),
            ("rpm", f"{rpm} RPM,"),
            ("voltage", f"{volt} V"),
        ]
    hp = round(kw / 0.7457, 1)
    power = f"{hp:g}HP" if abs(round(hp * 0.7457, 1) - kw) <= 0.01 * kw else f"{kw:g}KW"
    return [
        (None, "MOTOR AC SQ CAGE"),
        ("power_kw", power),
        ("poles", f"{poles}P"),
        ("voltage", f"{volt}V"),
        ("rpm", f"{rpm} RPM"),
    ]


RENDER: dict[str, Callable[[dict[str, Any], str, random.Random], list[Part]]] = {
    "VALVE": _valve,
    "PIPE": _pipe,
    "FLANGE": _flange,
    "FASTENER": _fastener,
    "MOTOR": _motor,
}


def _typo(token: str, rng: random.Random) -> str:
    """Swap two adjacent letters inside an alphabetic word of 4+ letters (numbers never touched)."""
    if len(token) < 4 or not token.isalpha():
        return token
    i = rng.randrange(len(token) - 1)
    return token[:i] + token[i + 1] + token[i] + token[i + 2 :]


def _render(
    cat: str, attrs: dict[str, Any], style: str, cfg: GeneratorConfig, rng: random.Random
) -> tuple[str, list[str]]:
    """(text, core attributes not written). Style A is cut at 40 characters (SAP-like)."""
    dropped: list[str] = []
    parts = []
    for attr, text in RENDER[cat](attrs, style, rng):
        if attr in CORE[cat] and rng.random() < cfg.drop_core_rate:
            dropped.append(attr)
            continue
        if attr in EXTENDED[cat] and rng.random() < cfg.drop_ext_rate:
            continue
        parts.append((attr, text))
    if style == "A":  # truncation at 40: a core attribute cut off counts as not written
        kept, length = [], 0
        for attr, text in parts:
            room = 40 - length - (1 if kept else 0)
            if room <= 0:
                if attr in CORE[cat]:
                    dropped.append(attr)
                continue
            if len(text) > room:
                kept.append(text[:room])
                if attr in CORE[cat]:
                    dropped.append(attr)
                length = 40
                continue
            kept.append(text)
            length += len(text) + (1 if len(kept) > 1 else 0)
        words = " ".join(kept).split(" ")
    else:
        words = " ".join(t for _, t in parts).split(" ")
    words = [_typo(w, rng) if rng.random() < cfg.typo_rate else w for w in words]
    return " ".join(w for w in words if w), sorted(set(dropped))


# ---- purchase history and stock (v1) ----
_VALVE_BASE = {"GATE": 1.0, "GLOBE": 1.25, "CHECK": 0.85, "BALL": 1.1}
_MATERIAL_FACTOR = {
    "A216-WCB": 1.0,
    "A351-CF8M": 2.6,
    "A105": 1.0,
    "A182-F316": 2.4,
    "A106-B": 1.15,
    "A53-B": 1.0,
}
_YEARLY_QTY = {  # lognormal (mu, sigma) of the yearly quantity per record
    "VALVE": (2.0, 0.9),
    "PIPE": (5.5, 1.0),
    "FLANGE": (2.8, 0.9),
    "FASTENER": (5.0, 1.0),
    "MOTOR": (0.6, 0.6),
}


def unit_price(cat: str, a: dict[str, Any]) -> float:
    """Synthetic list price in INR (per metre for pipe, per piece otherwise). Plausible
    orders of magnitude only; not market data."""
    if cat == "VALVE":
        size = (a["size_dn"] / 100) ** 1.4 * (a["pressure_class"] / 150) ** 0.6
        end = 1.08 if a["end_connection"] != "BW" else 1.0
        return (
            9_000 * _VALVE_BASE[a["valve_type"]] * size * _MATERIAL_FACTOR[a["body_material"]] * end
        )
    if cat == "PIPE":
        wall = {"40": 1.0, "80": 1.35}.get(a["schedule"], 1.15)
        return 900 * (a["size_dn"] / 100) ** 1.25 * wall * _MATERIAL_FACTOR[a["material"]]
    if cat == "FLANGE":
        typ = {"WN": 1.2, "SO": 1.0, "BLIND": 0.9}[a["flange_type"]]
        size = (a["size_dn"] / 100) ** 1.3 * (a["pressure_class"] / 150) ** 0.7
        return 2_400 * typ * size * _MATERIAL_FACTOR[a["material"]]
    if cat == "FASTENER":
        d = int(a["thread"][1:])
        length = a["length_mm"] or d
        grade = {"8.8": 1.0, "10.9": 1.3, "B7": 1.5, "2H": 1.2}[a["strength"]]
        return 0.004 * d**2 * (length + 2 * d) * grade + 4
    return 6_500 * a["power_kw"] ** 0.85 * (1 + 0.04 * (a["poles"] - 4))


def _procurement(
    meta: list[tuple[str, dict[str, Any], dict[str, Any]]], cfg: GeneratorConfig
) -> dict[str, list[dict[str, Any]]]:
    """Purchase lines per CPSE; fills annual_value, annual_qty and stock_qty on each record.

    `meta` holds (cpse, entity, record row) in record order. Each (entity, CPSE) pair keeps one
    price level (CPSE bias x a fixed per-pair factor), so the same item costs differently in
    different CPSEs, as in real fragmented buying."""
    prng = random.Random(f"procurement-v1-{cfg.seed}")
    as_of = dt.date.fromisoformat(cfg.as_of)
    window = cfg.history_months * 30
    bias = dict(cfg.cpse_price_bias)
    vendors = {c: [f"SYNTH-VENDOR-{c}{i:02d}" for i in range(1, 9)] for c in cfg.cpses}
    level: dict[tuple[str, str], float] = {}
    out: dict[str, list[dict[str, Any]]] = {c: [] for c in cfg.cpses}
    for cpse, e, row in meta:
        cat, piece = e["category"], e["category"] != "PIPE"
        key = (e["id"], cpse)
        if key not in level:
            level[key] = unit_price(cat, e["attrs"]) * bias[cpse] * prng.lognormvariate(0, 0.08)
        mu, sigma = _YEARLY_QTY[cat]
        yearly = max(1.0, prng.lognormvariate(mu, sigma))
        dormant = prng.random() < cfg.dormant_rate
        n_po = max(1, min(8, round(prng.lognormvariate(0.9, 0.6))))
        lines = []
        for _ in range(n_po):
            # dormant records bought only in the older part of the window
            days = prng.randrange(366, window) if dormant else prng.randrange(0, window)
            qty = max(1.0, yearly * cfg.history_months / 12 / n_po * prng.uniform(0.5, 1.5))
            qty = float(round(qty)) if piece else round(qty, 1)
            price = level[key] * (1 - 0.05 * days / 365) * prng.uniform(0.97, 1.03)
            lines.append(
                {
                    "legacy_code": row["legacy_code"],
                    "po_date": (as_of - dt.timedelta(days=days)).isoformat(),
                    "qty": qty,
                    "uom": row["uom"],
                    "unit_price": round(price, 2),
                    "currency": "INR",
                    "vendor": prng.choice(vendors[cpse]),
                    "plant": row["plant"],
                }
            )
        lines.sort(key=lambda r: (r["po_date"], r["qty"]))
        out[cpse].extend(lines)
        recent = [x for x in lines if (as_of - dt.date.fromisoformat(x["po_date"])).days < 365]
        row["annual_qty"] = round(sum(x["qty"] for x in recent), 1)
        row["annual_value"] = round(sum(x["qty"] * x["unit_price"] for x in recent))
        if dormant:
            held = prng.random() < cfg.idle_stock_rate
            stock = yearly * prng.uniform(0.5, 1.5) if held else 0.0
        else:
            stock = yearly * prng.uniform(0.05, 0.35) if prng.random() < cfg.stock_rate else 0.0
        row["stock_qty"] = float(round(stock)) if piece else round(stock, 1)
    return out


# ---- generation ----
@dataclass
class Generated:
    config: GeneratorConfig
    records: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # cpse -> rows
    truth_entities: list[dict[str, Any]] = field(default_factory=list)
    truth_pairs: list[dict[str, Any]] = field(default_factory=list)
    procurement: dict[str, list[dict[str, Any]]] = field(default_factory=dict)  # cpse -> lines


_UOM = {  # canonical, then the alias each CPSE style writes (TRD Appendix I)
    "PIPE": {"A": "M", "B": "METRE", "C": "MTR"},
    "OTHER": {"A": "EA", "B": "NOS", "C": "PCS"},
}
_MAT_GROUP = {"VALVE": "VLV", "PIPE": "PIP", "FLANGE": "FLG", "FASTENER": "FST", "MOTOR": "MTR"}


def generate(cfg: GeneratorConfig | None = None) -> Generated:
    cfg = cfg or GeneratorConfig()
    rng = random.Random(cfg.seed)
    cats = [c for c, _ in cfg.category_mix]
    weights = [w for _, w in cfg.category_mix]

    # base entities, unique on their core attributes, and their hard-negative neighbours
    entities: list[dict[str, Any]] = []  # {id, category, attrs, group, neighbour_of}
    seen: set[tuple[Any, ...]] = set()
    while len(entities) < cfg.n_entities:
        cat = rng.choices(cats, weights)[0]
        attrs = _sample(cat, rng)
        if _core_key(cat, attrs) in seen:
            continue
        seen.add(_core_key(cat, attrs))
        entities.append({"category": cat, "attrs": attrs, "group": len(entities), "of": None})
    for base in list(entities):
        if rng.random() >= cfg.hard_negative_share:
            continue
        for _ in range(20):
            n = _neighbour(base["category"], base["attrs"], rng)
            if _core_key(base["category"], n) not in seen:
                seen.add(_core_key(base["category"], n))
                entities.append(
                    {"category": base["category"], "attrs": n, "group": base["group"], "of": base}
                )
                break
    for i, e in enumerate(entities):
        e["id"] = f"E{i + 1:05d}"

    # splits by entity group (a neighbour shares its base entity's split)
    groups = list(range(cfg.n_entities))
    rng.shuffle(groups)
    split_of: dict[int, str] = {}
    start = 0
    for k, (name, share) in enumerate(cfg.splits):
        end = len(groups) if k == len(cfg.splits) - 1 else start + round(share * len(groups))
        split_of.update({g: name for g in groups[start:end]})
        start = end

    out = Generated(config=cfg, records={c: [] for c in cfg.cpses})
    seq = {c: 0 for c in cfg.cpses}
    members: dict[str, list[str]] = {}  # entity id -> record keys
    meta: list[tuple[str, dict[str, Any], dict[str, Any]]] = []  # for the v1 history pass
    for e in entities:
        k = rng.choices([1, 2, 3], cfg.presence)[0]
        where = sorted(rng.sample(list(cfg.cpses), k))

        maker = f"SYNTH-MAKER-{rng.randrange(1, 13):02d}"
        mpn = f"SX-{e['id'][1:]}-{rng.randrange(100, 1000)}"
        for cpse in where:
            for _ in range(2 if rng.random() < cfg.within_dup_rate else 1):
                seq[cpse] += 1
                code = f"{cpse}{seq[cpse]:07d}"
                with_make = rng.random() < cfg.make_rate  # per record (PRD 10.1)
                text, dropped = _render(e["category"], e["attrs"], cpse, cfg, rng)
                short, long = (text, "") if len(text) <= 40 else (text[:40].rstrip(), text)
                uom_key = "PIPE" if e["category"] == "PIPE" else "OTHER"
                row: dict[str, Any] = {
                    "legacy_code": code,
                    "short_text": short,
                    "long_text": long,
                    "uom": _UOM[uom_key][cpse],
                    "mat_group": _MAT_GROUP[e["category"]],
                    "manufacturer": maker if with_make else "",
                    "mpn": mpn if with_make else "",
                    "plant": f"P{rng.randrange(1, 4)}",
                    "criticality": "",
                    "annual_value": 0,  # filled from the purchase history
                    "annual_qty": 0,
                    "stock_qty": 0,
                }
                rng.lognormvariate(
                    10, 1.2
                )  # v0 annual_value draw (after plant), keeps the v0 stream
                out.records[cpse].append(row)
                meta.append((cpse, e, row))
                key = f"CPSE-{cpse}:{code}"
                members.setdefault(e["id"], []).append(key)
                out.truth_entities.append(
                    {
                        "cpse": f"CPSE-{cpse}",
                        "legacy_code": code,
                        "entity_id": e["id"],
                        "category": e["category"],
                        "attrs": json.dumps(e["attrs"], sort_keys=True, separators=(",", ":")),
                        "dropped_core": ";".join(dropped),
                        "neighbour_of": e["of"]["id"] if e["of"] else "",
                        "split": split_of[e["group"]],
                    }
                )

    def pair(x: str, y: str, label: str) -> dict[str, Any]:
        (ca, la), (cb, lb) = sorted((x.split(":"), y.split(":")))
        return {
            "cpse_a": ca,
            "legacy_code_a": la,
            "cpse_b": cb,
            "legacy_code_b": lb,
            "label": label,
        }

    for e in entities:
        for x, y in combinations(members.get(e["id"], []), 2):
            out.truth_pairs.append(pair(x, y, "EQUIVALENT"))
    for e in entities:
        if e["of"]:
            for x in members.get(e["of"]["id"], []):
                for y in members.get(e["id"], []):
                    out.truth_pairs.append(pair(x, y, "NOT_EQUIVALENT_HARD"))
    out.truth_pairs.sort(key=lambda p: tuple(p.values()))
    out.procurement = _procurement(meta, cfg)
    return out


# ---- files ----
def _csv(rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def files(gen: Generated) -> dict[str, bytes]:
    """File name -> bytes, manifest last (its hashes cover every other file)."""
    out = {f"cpse_{c}.csv": _csv(rows, RECORD_COLUMNS) for c, rows in gen.records.items()}
    for c, lines in gen.procurement.items():
        out[f"procurement_{c}.csv"] = _csv(lines, PROCUREMENT_COLUMNS)
    out["truth_entities.csv"] = _csv(
        gen.truth_entities,
        "cpse legacy_code entity_id category attrs dropped_core neighbour_of split".split(),
    )
    out["truth_pairs.csv"] = _csv(
        gen.truth_pairs, "cpse_a legacy_code_a cpse_b legacy_code_b label".split()
    )
    labels = [p["label"] for p in gen.truth_pairs]
    manifest = {
        "synthetic": True,
        "honesty": HONESTY,
        "generator_version": GENERATOR_VERSION,
        "seed": gen.config.seed,
        "config": asdict(gen.config),
        "counts": {
            "records": sum(len(r) for r in gen.records.values()),
            "records_per_cpse": {f"CPSE-{c}": len(r) for c, r in gen.records.items()},
            "entities": len({t["entity_id"] for t in gen.truth_entities}),
            "pairs_equivalent": labels.count("EQUIVALENT"),
            "pairs_not_equivalent_hard": labels.count("NOT_EQUIVALENT_HARD"),
            "procurement_lines": sum(len(v) for v in gen.procurement.values()),
        },
        "files": {
            name: {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            for name, data in sorted(out.items())
        },
    }
    out["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return out


def write(gen: Generated, out_dir: str | Path) -> dict[str, Any]:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    data = files(gen)
    for name, content in data.items():
        (path / name).write_bytes(content)
    manifest: dict[str, Any] = json.loads(data["manifest.json"])
    return manifest
