"""Search-before-create (PRD FR-1001-1003, 9.11; TRD sequence 2.3c, TR-MOD-27).

A free-text description is read like any record (normalise, classify, extract), then decided
against every ACTIVE national code of the same category. No database write.
`recommended_action`: USE_EXISTING when an IDENTICAL or EQUIVALENT code exists,
SUPPLY_ATTRIBUTES when only INSUFFICIENT_DATA ones exist (with the attributes to add),
otherwise CREATE_NEW_ALLOWED. The registry is small next to the master files (thousands of
codes), so every code of the category is decided: no candidate can be missed.
"""

from collections.abc import Mapping
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.decide import decide
from app.core.extract import extract
from app.core.normalise import normalise
from app.core.radar import text_sim
from app.core.templates import Template
from app.core.types import Dictionary, Spec

ORDER = {"IDENTICAL": 0, "EQUIVALENT": 1, "INSUFFICIENT_DATA": 2, "NOT_EQUIVALENT": 3}
MAX_RESULTS = 10
LOOKALIKE_MIN = 0.75  # NOT_EQUIVALENT codes are shown only when the text looks alike


def search(
    session: Session,
    *,
    text_in: str,
    mpn: str | None,
    manufacturer: str | None,
    templates: Mapping[str, Template],
    dictionary: Dictionary,
    threshold: float,
    model: Any = None,
) -> dict[str, Any]:
    q = extract(text_in, mpn, manufacturer, dictionary=dictionary, model=model, threshold=threshold)
    query_norm = normalise(text_in, dictionary)
    parsed = {
        "category": q.category,
        "class_source": q.class_source,
        "attrs": {k: v for k, v in q.attrs.items() if v is not None},
        "repairs": list(q.repairs),
    }
    if q.category is None:
        return {
            "query": parsed,
            "candidates": [],
            "would_create_duplicate": False,
            "recommended_action": "SUPPLY_ATTRIBUTES",
            "message": "Category not recognised; SpecID will not guess. Add the item type.",
            "missing": ["category"],
        }
    rows = session.execute(
        text("""
            SELECT n.cnmc, n.canonical_spec, n.short_desc_40, n.long_desc, n.variants,
                   (SELECT array_agg(DISTINCT c.code ORDER BY c.code) FROM crosswalk x
                      JOIN cpse c ON c.id = x.cpse_id WHERE x.cnmc = n.cnmc AND x.status = 'ACTIVE')
            FROM cnmc n WHERE n.status = 'ACTIVE' AND n.category = :c
            """),
        {"c": q.category},
    ).all()
    out = []
    for code, spec_attrs, short, long, variants, cpses in rows:
        make = _matching_variant(variants or [], mpn, manufacturer)
        cand = Spec(q.category, dict(spec_attrs), {}, (), make[1], make[0])
        d = decide(q, cand, templates)
        sim = text_sim(query_norm, normalise(long or short or "", dictionary))
        if d.verdict == "NOT_EQUIVALENT" and sim < LOOKALIKE_MIN:
            continue
        gaps = ("MISSING_ONE", "MISSING_BOTH", "PARTIAL")
        missing = [e.attr for e in d.evidence if e.level == "core" and e.status in gaps]
        conflicts = [e.attr for e in d.evidence if e.status == "CONFLICT"]
        out.append(
            {"cnmc": code, "short_desc_40": short, "long_desc": long, "cpses": list(cpses or []),
             "verdict": d.verdict, "reasons": list(d.reasons), "text_sim": round(sim, 3),
             "missing": missing, "conflicts": conflicts,
             "evidence": [e.__dict__ for e in d.evidence if e.status != "MISSING_BOTH"]}
        )  # fmt: skip
    out.sort(key=lambda c: (ORDER[c["verdict"]], -c["text_sim"], c["cnmc"]))
    out = out[:MAX_RESULTS]
    verdicts = {c["verdict"] for c in out}
    if verdicts & {"IDENTICAL", "EQUIVALENT"}:
        action, message = "USE_EXISTING", "This item already has a national code. Use it."
    elif "INSUFFICIENT_DATA" in verdicts:
        action, message = (
            "SUPPLY_ATTRIBUTES",
            "A code may exist; add the missing details to be sure.",
        )
    else:
        action, message = "CREATE_NEW_ALLOWED", "No national code matches this specification."
    missing = sorted({m for c in out if c["verdict"] == "INSUFFICIENT_DATA" for m in c["missing"]})
    return {
        "query": parsed,
        "candidates": out,
        "would_create_duplicate": action == "USE_EXISTING",
        "recommended_action": action,
        "message": message,
        "missing": missing,
    }


def _matching_variant(
    variants: list[dict[str, Any]], mpn: str | None, maker: str | None
) -> tuple[str | None, str | None]:
    """(maker, mpn) of the code's variant equal to the query's, so IDENTICAL can be found."""
    key = ((maker or "").strip().upper(), (mpn or "").strip().upper())
    for v in variants:
        if (
            (v.get("manufacturer") or "").strip().upper(),
            (v.get("mpn") or "").strip().upper(),
        ) == key:
            return v.get("manufacturer"), v.get("mpn")
    return None, None
