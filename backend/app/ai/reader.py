"""Verified AI reader (docs/SOLUTION.md Pillar 2; DEC-41).

For records whose rules left a key attribute unknown, the model is asked to point at the words
that state it. A value is accepted only when every check passes (the grounding check):

1. the quoted span is really in the record's text (case and spacing ignored);
2. the value is allowed: in the template's value list, or the right type for the attribute;
3. where the rules can read the span on their own, they read the same value.

Accepted values are tagged `tier = LLM` with the span in the note, so the evidence card shows
"AI-read from '…'". Rejected values are counted, never used. The reader never sees a pair and
never gives a verdict; `decide()` stays the rule engine.
"""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import structlog

from app.ai.provider import AIError, Provider
from app.core.extract import extract
from app.core.templates import Template
from app.core.types import AttrMeta, Dictionary, Spec

log = structlog.get_logger()
BATCH = 20  # descriptions per model call (free-tier friendly)
INT_ATTRS = frozenset({"size_dn", "pressure_class", "length_mm", "poles", "rpm", "voltage"})
FLOAT_ATTRS = frozenset({"power_kw"})
_SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class ReadResult:
    spec: Spec
    accepted: int
    rejected: int


def _flat(s: str) -> str:
    return _SPACE.sub(" ", s.upper()).strip()


def missing_core(spec: Spec, templates: Mapping[str, Template]) -> list[str]:
    t = templates.get(spec.category or "")
    if t is None:
        return []
    return [c for c in t.core if spec.attrs.get(c) is None]


def coerce(attr: str, value: Any, template: Template) -> Any | None:
    """Value check 2: allowed values, or the attribute's type. None = not allowed."""
    if value is None or value == "":
        return None
    if attr in INT_ATTRS:
        try:
            v: Any = int(float(str(value).strip()))
        except ValueError:
            return None
    elif attr in FLOAT_ATTRS:
        try:
            v = float(str(value).strip())
        except ValueError:
            return None
    else:
        v = str(value).strip().upper()
    domain = template.value_domains.get(attr)
    if domain is not None and v not in domain and str(v) not in [str(d) for d in domain]:
        return None
    return v


def verify(
    text: str,
    category: str,
    attr: str,
    value: Any,
    span: str,
    templates: Mapping[str, Template],
    dictionary: Dictionary,
) -> Any | None:
    """The grounding check: the accepted (canonical) value, or None."""
    if not span or _flat(span) not in _flat(text):
        return None  # 1: the words must be in the record
    t = templates.get(category)
    if t is None:
        return None
    v = coerce(attr, value, t)
    if v is None:
        return None  # 2: allowed value
    ruled = extract(f"{category} {span}", dictionary=dictionary, model=None, threshold=1.0)
    got = ruled.attrs.get(attr) if ruled.category == category else None
    if got is not None and str(got) != str(v):
        return None  # 3: the rules read this span differently
    return got if got is not None else v


def _prompt(items: Sequence[tuple[str, str, list[str]]]) -> str:
    lines = [
        "You read industrial material descriptions. For each item, find the listed attributes.",
        'Return JSON: {"items": [{"id": <id>, "attributes": [{"name": <attribute>, '
        '"value": <value>, "span": <exact words from the description>}]}]}.',
        "Copy the span exactly from the description. Only attributes that are written in the "
        "description; never guess, never use outside knowledge.",
        "Sizes as DN numbers (4 inch = 100).",
        "Items:",
    ]
    for i, (text, category, attrs) in enumerate(items):
        lines.append(json.dumps({"id": i, "category": category, "description": text,
                                 "attributes": attrs}))  # fmt: skip
    return "\n".join(lines)


def read_missing(
    provider: Provider,
    records: Sequence[tuple[str, Spec]],
    templates: Mapping[str, Template],
    dictionary: Dictionary,
) -> list[ReadResult]:
    """`records` = (raw text, spec) with a category; returns one result per record, in order."""
    results = [ReadResult(spec, 0, 0) for _, spec in records]
    for start in range(0, len(records), BATCH):
        chunk = records[start : start + BATCH]
        asks = [(text, spec.category or "", missing_core(spec, templates)) for text, spec in chunk]
        try:
            answer = provider.generate_json(_prompt(asks))
        except AIError as exc:
            log.warning("ai_reader_failed", error=str(exc))
            continue
        for item in (answer or {}).get("items", []) if isinstance(answer, dict) else []:
            try:
                i = int(item.get("id"))
            except (TypeError, ValueError):
                continue
            if not 0 <= i < len(chunk):
                continue
            text, spec = chunk[i]
            wanted = set(asks[i][2])
            attrs, meta = dict(spec.attrs), dict(spec.meta)
            ok = bad = 0
            for a in item.get("attributes", []) or []:
                name = a.get("name") if isinstance(a, dict) else None
                if name not in wanted or attrs.get(name) is not None:
                    continue
                span = str(a.get("span") or "").strip()
                v = verify(text, spec.category or "", name, a.get("value"), span, templates,
                           dictionary)  # fmt: skip
                if v is None:
                    bad += 1
                    continue
                attrs[name] = v
                note = f"AI-read from “{span}”"
                meta[name] = AttrMeta(tier="LLM", confidence=0.9, note=note)
                ok += 1
            if ok or bad:
                results[start + i] = ReadResult(replace(spec, attrs=attrs, meta=meta), ok, bad)
    return results
