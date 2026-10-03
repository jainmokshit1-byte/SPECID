"""Shared access to core/ for the Phase 4 tests.

PRD Appendix D is ported to the TRD 4.1/4.2 contracts (DEC-22).

`app.core` is imported inside the functions, so a missing module fails each test that needs it
instead of stopping the whole collection.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

TEMPLATE_DIR = Path(
    os.environ.get("TEMPLATE_DIR", Path(__file__).resolve().parents[2] / "templates")
)
DICTIONARY_FILES = {"dictionary.yaml", "uom.yaml"}


@lru_cache
def template_yaml() -> dict[str, dict[str, Any]]:
    """The raw template YAML documents keyed by category (read without core/)."""
    docs = {}
    for p in sorted(TEMPLATE_DIR.glob("*.yaml")):
        if p.name not in DICTIONARY_FILES:
            doc = yaml.safe_load(p.read_text("utf-8"))
            docs[doc["category"]] = doc
    return docs


@lru_cache
def templates() -> Any:
    from app.core.templates import load_templates

    return load_templates(TEMPLATE_DIR)


@lru_cache
def dictionary() -> Any:
    from app.core.templates import load_dictionary

    return load_dictionary(TEMPLATE_DIR)


def N(text: str) -> str:
    from app.core.normalise import normalise

    return normalise(text, dictionary())


def E(text: str, mpn: str | None = None, maker: str | None = None) -> Any:
    from app.core.extract import extract

    return extract(text, mpn, maker, dictionary=dictionary(), model=None, threshold=0.80)


def D(a: Any, b: Any, **kw: Any) -> Any:
    from app.core.decide import decide

    return decide(a, b, templates(), **kw)


def V(a: str, b: str) -> Any:
    """Appendix D `V`: decide a text pair both ways and assert the verdict is symmetric."""
    r, r2 = D(E(a), E(b)), D(E(b), E(a))
    assert r.verdict == r2.verdict, ("asymmetric verdict", a, b, r.verdict, r2.verdict)
    return r


def spec(category: str | None, attrs: dict[str, Any], **kw: Any) -> Any:
    """A Spec built directly from attribute values (property tests)."""
    from app.core.types import Spec

    return Spec(
        category=category,
        attrs=attrs,
        meta={},
        residual=tuple(kw.get("residual", ())),
        mpn=kw.get("mpn"),
        maker=kw.get("maker"),
    )


# ---- PRD Appendix D section 1: the 12 illustrative pairs of dossier A4.3 ----
NOT = [
    ("VALVE GATE 4IN CL150 A216 WCB FLGD RF", "VALVE GATE 4IN CL300 A216 WCB FLGD RF"),
    ("PIPE SMLS 6IN SCH40 A106 GR.B", "PIPE SMLS 6IN SCH80 A106 GR.B"),
    ("BOLT HEX M16X80 GR8.8 ZN", "BOLT HEX M16X90 GR8.8 ZN"),
    ("FLANGE WN 4IN CL150 RF A105", "FLANGE WN 4IN CL150 RF A182 F316"),
    ("MOTOR AC SQ 100KW 1500RPM 4P", "MOTOR AC SQ 110KW 1500RPM 4P"),
    ("GASKET SPIRAL WND 4IN CL150 SS316/GRAF", "GASKET SPIRAL WND 4IN CL300 SS316/GRAF"),
]
EQV = [
    ("VALVE GATE 4IN CL150 A216 WCB FLGD RF", "GV 100NB 150# WCB RF FLANGED"),
    ("PIPE SMLS 6IN SCH40 A106 GR.B", "PIPE 150NB SCH 40 A106 GRADE B SEAMLESS"),
    ("BOLT HEX M16X80 GR8.8 ZN", "BOLT, HEX HD, M16 X 80, 8.8, ZINC"),
    ("FLANGE WN 4IN CL150 RF A105", "WELD NECK FLANGE 100NB 150# RF ASTM A105"),
    ("MOTOR AC SQ 100KW 1500RPM 4P", "AC INDUCTION MOTOR SQ CAGE 100 KW 4 POLE 1500 RPM"),
    ("GASKET SPIRAL WND 4IN CL150 SS316/GRAF", "SPIRAL WOUND GASKET 100NB 150# 316SS GRAPHITE"),
]
