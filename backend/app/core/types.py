"""Shared types of the pure decision engine (TRD 4.1)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

Verdict = Literal["IDENTICAL", "EQUIVALENT", "NOT_EQUIVALENT", "INSUFFICIENT_DATA"]
Route = Literal["AUTO_ELIGIBLE", "REVIEW", "NONE"]
Status = Literal["MATCH", "PARTIAL", "CONFLICT", "MISSING_ONE", "MISSING_BOTH"]
Tier = Literal["RULE", "ML", "NER", "LLM", "USER"]
Level = Literal["core", "ext"]


@dataclass(frozen=True)
class AttrMeta:
    tier: Tier
    confidence: float  # rules = 1.0
    note: str | None = None  # conversion / inference, e.g. "4 IN = DN100"


@dataclass(frozen=True)
class Spec:
    category: str | None
    attrs: dict[str, Any]  # canonical values; None = not stated
    meta: dict[str, AttrMeta]  # per attribute
    residual: tuple[str, ...]  # tokens not consumed by any extractor
    mpn: str | None = None
    maker: str | None = None
    class_source: Literal["RULE", "ML", "NONE"] = "NONE"
    class_prob: float | None = None
    repairs: tuple[str, ...] = ()  # spelling repairs applied, e.g. "LFANGE -> FLANGE" (DEC-34)


@dataclass(frozen=True)
class EvidenceRow:
    attr: str
    level: Level
    a: Any
    b: Any
    status: Status
    rule: str
    rule_text: str
    note_a: str | None
    note_b: str | None


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    route: Route
    reasons: tuple[str, ...]
    evidence: tuple[EvidenceRow, ...]
    confidence: float | None  # heuristic p_rule in P0 (PRD 9.6); None for INSUFFICIENT_DATA
    template_version: int | None


@dataclass(frozen=True)
class Dictionary:
    """A versioned dictionary set (PRD FR-203, FR-205): expansions and UoM aliases."""

    version: int
    abbreviations: Mapping[str, str] = field(default_factory=dict)  # PRD 9.2 rule 9
    uom_aliases: Mapping[str, str] = field(default_factory=dict)  # TRD Appendix I
    uom_ambiguous: frozenset[str] = frozenset()
    # spelling repair before the rules (DEC-34 DEV-6): engineering words, and real words that
    # must never be "repaired" into one of them (STUB is not STUD)
    spelling: frozenset[str] = frozenset()
    spelling_protected: frozenset[str] = frozenset()
    # ingest column suggestions (TRD Appendix H): target field -> normalised header synonyms
    header_synonyms: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
