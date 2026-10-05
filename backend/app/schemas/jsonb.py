"""Pydantic models for the JSONB contracts (Backend Schema section 6, TRD 7.2).

Services validate with these before writing a JSONB column. `CONTRACTS` maps
(table, column) to its model.
"""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator

from app.core.templates import Template


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ----- upload_batch -----
class ColumnMapping(RootModel[dict[str, str]]):
    """`{ "<source header>": "<target field>" }` (TRD 7.2)."""


class BatchQuality(Strict):
    rows: int = Field(ge=0)
    empty_short_text: int = Field(ge=0)
    short_text_over_40: int = Field(ge=0)
    duplicate_legacy_codes: int = Field(ge=0)
    completeness: dict[str, float]
    category_share: dict[str, float]
    core_parse_rate: dict[str, float]
    uom_ambiguous: int = Field(ge=0)
    # v2 (DEC-35): rows left out, UoM that is missing or unknown, and the health score
    rejected_rows: int = Field(default=0, ge=0)
    uom_unknown: int = Field(default=0, ge=0)
    skipped_unchanged: int = Field(default=0, ge=0)
    health_score: int | None = Field(default=None, ge=0, le=100)
    health_components: dict[str, float] = Field(default_factory=dict)


# ----- material_record -----
class RawRow(RootModel[dict[str, Any]]):
    """The original row as `{header: value}`."""


# ----- template -----
# The template model lives in core/ (TRD TR-MOD-05); this contract reuses it (single definition).
TemplateDefinition = Template


# ----- dictionary (content per kind) -----
class AbbreviationContent(RootModel[dict[str, str]]):
    """ABBREVIATION: `{abbr: expansion}`."""


class UomContent(Strict):
    """UOM: `{alias: canonical}` plus aliases that are never mapped (TRD Appendix I)."""

    aliases: dict[str, str]
    ambiguous: list[str] = []

    @model_validator(mode="after")
    def _ambiguous_never_mapped(self) -> "UomContent":
        both = set(self.ambiguous) & set(self.aliases)
        if both:
            raise ValueError(f"ambiguous aliases must not be mapped: {both}")
        return self


class HeaderSynonymContent(RootModel[dict[str, list[str]]]):
    """HEADER_SYNONYM: `{target: [synonyms]}` (TRD Appendix H)."""


class UnspscEntry(Strict):
    code: str = Field(pattern=r"^[0-9]{8}$")
    source_note: str = Field(min_length=5)  # FR-405: no code without a source


class UnspscMapContent(RootModel[dict[str, UnspscEntry]]):
    """UNSPSC_MAP: `{class_path: {code, source_note}}`."""


class SpellingContent(Strict):
    """SPELLING (DEC-34): engineering words to repair towards, and real words never repaired."""

    vocabulary: list[str] = Field(default_factory=list)
    protected: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _upper_words_no_overlap(self) -> "SpellingContent":
        for w in (*self.vocabulary, *self.protected):
            if not (w.isalpha() and w.isupper()):
                raise ValueError(f"spelling words are upper-case letters only: {w!r}")
        both = set(self.vocabulary) & set(self.protected)
        if both:
            raise ValueError(f"words in both vocabulary and protected: {sorted(both)}")
        return self


DICTIONARY_CONTENT: dict[str, type[BaseModel]] = {
    "ABBREVIATION": AbbreviationContent,
    "UOM": UomContent,
    "HEADER_SYNONYM": HeaderSynonymContent,
    "UNSPSC_MAP": UnspscMapContent,
    "SPELLING": SpellingContent,
}


# ----- spec_record -----
Tier = Literal["RULE", "ML", "NER", "LLM", "USER"]


class SpecAttrs(RootModel[dict[str, Any]]):
    """`{attr: value}`; None = not stated."""


class AttrMetaEntry(Strict):
    tier: Tier
    confidence: float = Field(ge=0, le=1)
    note: str | None = None


class AttrMeta(RootModel[dict[str, AttrMetaEntry]]):
    """`{attr: {tier, confidence, note}}`."""


# ----- run -----
class RunConfig(Strict):
    """Stored verbatim (TRD 7.2); defaults come from settings.RunDefaults (Phase 5)."""

    mode: Literal["CROSS_CPSE", "WITHIN_CPSE", "BOTH"]
    seed: int
    bm25_k: int = Field(ge=1)
    dense_enabled: bool
    dense_k: int = Field(ge=1)
    block_cap: int = Field(ge=1)
    classifier_threshold: float = Field(ge=0, le=1)
    lookalike_min_sim: float = Field(ge=0, le=1)
    hidden_twin_max_sim: float = Field(ge=0, le=1)
    tau_b1: float | None
    tau_b2: float | None
    templates: dict[str, int]
    dictionary_version: int
    uom_table_version: int
    embedding_model: str
    classifier_model: str
    git_commit: str


class RunProgress(Strict):
    stage: str
    done: int = Field(ge=0)
    total: int = Field(ge=0)


class RunStats(Strict):
    """Filled in as the run advances, so every key is optional (TRD 7.2)."""

    progress: RunProgress | None = None
    records: int | None = None
    specs_parsed: int | None = None
    unclassified: int | None = None
    classified_by_ml: int | None = None
    candidate_pairs: int | None = None
    channels: dict[Literal["B", "L", "D", "M"], int] | None = None
    verdicts: (
        dict[Literal["IDENTICAL", "EQUIVALENT", "NOT_EQUIVALENT", "INSUFFICIENT_DATA"], int] | None
    ) = None
    clusters: int | None = None
    blocked_edges: int | None = None
    timings_ms: dict[str, int] | None = None
    blocked_egress: int | None = None


# ----- pair_decision -----
class PairBaseline(Strict):
    b1: bool
    b2: bool
    tau1: float
    tau2: float


class EvidenceRow(Strict):
    """One stored evidence row (TRD 4.1). MISSING_BOTH rows are omitted on write (TR-DAT-05)."""

    attr: str
    level: Literal["core", "ext"]
    a: Any
    b: Any
    status: Literal["MATCH", "PARTIAL", "CONFLICT", "MISSING_ONE"]
    rule: str
    rule_text: str
    note_a: str | None = None
    note_b: str | None = None


class Evidence(RootModel[list[EvidenceRow]]):
    pass


# ----- review_decision -----
class SplitGroups(RootModel[list[list[uuid.UUID]]]):
    """`[[record_id, ...], ...]` (TRD Appendix F)."""

    @field_validator("root")
    @classmethod
    def _groups_disjoint_and_non_empty(cls, v: list[list[uuid.UUID]]) -> list[list[uuid.UUID]]:
        flat = [r for g in v for r in g]
        if any(not g for g in v) or len(flat) != len(set(flat)):
            raise ValueError("split groups must be non-empty and disjoint")
        return v


# ----- cnmc -----
class CanonicalSpec(RootModel[dict[str, Any]]):
    """`{attr: value}`, the union of member attributes (PRD 9.8)."""


class Variant(Strict):
    manufacturer: str | None
    mpn: str | None


class Variants(RootModel[list[Variant]]):
    pass


# ----- eval_run -----
class EvalConfig(BaseModel):
    """PRD section 8 example; the generator (Phase 4) may add its own parameters."""

    model_config = ConfigDict(extra="allow")
    entities: int | None = Field(default=None, ge=1)
    cpse_styles: list[Literal["A", "B", "C"]] | None = None
    hard_negative_share: float | None = Field(default=None, ge=0, le=1)


class EvalMetrics(BaseModel):
    """Computed at run time and never pre-filled (PRD section 8)."""

    model_config = ConfigDict(extra="allow")
    hard_negatives: int | None = None
    false_merges: int | None = None
    false_merge_upper_95: float | None = None
    auto_eligible_precision: float | None = None
    auto_eligible_precision_wilson_lb: float | None = None
    pair_completeness: float | None = None
    reduction_ratio: float | None = None
    abstention_rate: float | None = None
    bcubed_precision: float | None = None
    bcubed_recall: float | None = None


# ----- audit_event -----
SECRET_KEYS = {"password", "password_hash", "key_hash", "api_key", "token", "jwt", "vendor_salt"}


class AuditDiff(RootModel[dict[str, Any]]):
    """The changed fields only, never secrets (TRD TR-ALG-09)."""

    @field_validator("root")
    @classmethod
    def _no_secrets(cls, v: dict[str, Any]) -> dict[str, Any]:
        found = SECRET_KEYS & {k.lower() for k in v}
        if found:
            raise ValueError(f"audit diffs never carry secrets: {found}")
        return v


# ----- idempotency_key -----
class IdempotentResponse(Strict):
    status_code: int = Field(ge=100, le=599)
    body: Any


CONTRACTS: dict[tuple[str, str], type[BaseModel]] = {
    ("upload_batch", "column_mapping"): ColumnMapping,
    ("upload_batch", "quality"): BatchQuality,
    ("material_record", "raw"): RawRow,
    ("template", "definition"): TemplateDefinition,
    ("spec_record", "attrs"): SpecAttrs,
    ("spec_record", "attr_meta"): AttrMeta,
    ("run", "config"): RunConfig,
    ("run", "stats"): RunStats,
    ("pair_decision", "baseline"): PairBaseline,
    ("pair_decision", "evidence"): Evidence,
    ("review_decision", "split_groups"): SplitGroups,
    ("cnmc", "canonical_spec"): CanonicalSpec,
    ("cnmc", "variants"): Variants,
    ("eval_run", "config"): EvalConfig,
    ("eval_run", "metrics"): EvalMetrics,
    ("audit_event", "before"): AuditDiff,
    ("audit_event", "after"): AuditDiff,
    ("idempotency_key", "response"): IdempotentResponse,
}
# dictionary.content depends on dictionary.kind: see DICTIONARY_CONTENT
