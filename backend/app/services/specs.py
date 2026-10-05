"""Spec building for stored records: extract, then the `spec_record` row (TRD TR-MOD-04, 7.1).

Used by ingest (quality report) and by the run (fresh specs under the run's template and
dictionary versions). The engine itself stays in `core/`.
"""

import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import Connection, text

from app.core.extract import extract
from app.core.normalise import normalise
from app.core.templates import Template
from app.core.types import Dictionary, Spec
from app.db.copy import copy_rows
from app.schemas.jsonb import AttrMeta as AttrMetaContract
from app.schemas.jsonb import SpecAttrs

SPEC_COLUMNS = [
    "record_id", "template_id", "template_version", "category", "class_source", "class_prob",
    "norm_text", "attrs", "attr_meta", "residual", "spec_completeness", "dictionary_version",
]  # fmt: skip


@dataclass(frozen=True)
class RecordText:
    """What the engine needs from a material record."""

    id: uuid.UUID
    text: str
    mpn: str | None
    maker: str | None


def record_text(short_text: str, long_text: str | None) -> str:
    """The long text when present, else the short text (same rule as the CLI)."""
    return (long_text or "").strip() or short_text


def spec_completeness(spec: Spec, templates: Mapping[str, Template]) -> float | None:
    """Share of the template's core attributes that are known (None without a category)."""
    t = templates.get(spec.category or "")
    if t is None or not t.core:
        return None
    known = sum(1 for c in t.core if spec.attrs.get(c) is not None)
    return round(known / len(t.core), 4)


def build_spec(
    rec: RecordText, dictionary: Dictionary, threshold: float, model: Any = None
) -> Spec:
    return extract(
        rec.text, rec.mpn, rec.maker, dictionary=dictionary, model=model, threshold=threshold
    )


def _dec(value: float | None) -> Decimal | None:
    """COPY into a numeric column needs Decimal, not float."""
    return None if value is None else Decimal(str(value))


def spec_row(
    rec: RecordText,
    spec: Spec,
    templates: Mapping[str, Template],
    dictionary: Dictionary,
) -> tuple[Any, ...]:
    """One `spec_record` row in `SPEC_COLUMNS` order, validated against the JSONB contracts."""
    t = templates.get(spec.category or "")
    attrs = SpecAttrs.model_validate(spec.attrs).root
    meta = AttrMetaContract.model_validate(
        {
            k: {"tier": m.tier, "confidence": m.confidence, "note": m.note}
            for k, m in spec.meta.items()
        }
    ).model_dump(mode="json")
    return (
        rec.id,
        t.id if t else None,
        t.version if t else None,
        spec.category,
        spec.class_source,
        _dec(spec.class_prob),
        normalise(rec.text, dictionary),
        attrs,
        meta,
        list(spec.residual),
        _dec(spec_completeness(spec, templates)),
        dictionary.version,
    )


def store_specs(conn: Connection, rows: Sequence[tuple[Any, ...]]) -> int:
    """Replace the stored specs of these records (derived data) in one COPY."""
    if not rows:
        return 0
    ids = [r[0] for r in rows]
    for i in range(0, len(ids), 5000):
        conn.execute(
            text("DELETE FROM spec_record WHERE record_id = ANY(:ids)"), {"ids": ids[i : i + 5000]}
        )
    return copy_rows(conn, "spec_record", SPEC_COLUMNS, rows)


def specs_for(
    records: Iterable[RecordText], dictionary: Dictionary, threshold: float
) -> dict[uuid.UUID, Spec]:
    return {r.id: build_spec(r, dictionary, threshold) for r in records}
