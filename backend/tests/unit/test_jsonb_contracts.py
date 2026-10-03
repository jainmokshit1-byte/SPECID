"""Backend Schema section 6: every JSONB contract has a Pydantic model that rejects wrong shapes."""

import uuid

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas import jsonb as j

# Shapes taken from TRD 7.2 and PRD section 8 (illustrative values, not results)
VALID: list[tuple[type[BaseModel], object]] = [
    (j.ColumnMapping, {"Material No": "legacy_code", "Description": "short_text"}),
    (
        j.BatchQuality,
        {
            "rows": 3, "empty_short_text": 0, "short_text_over_40": 1,
            "duplicate_legacy_codes": 0, "completeness": {"mpn": 0.5},
            "category_share": {"VALVE": 1.0}, "core_parse_rate": {"VALVE": 0.9},
            "uom_ambiguous": 0,
        },
    ),
    (j.SpecAttrs, {"valve_type": "GATE", "size_dn": 100, "trim": None}),
    (j.AttrMeta, {"size_dn": {"tier": "RULE", "confidence": 1.0, "note": "4 IN = DN100"}}),
    (
        j.RunConfig,
        {
            "mode": "CROSS_CPSE", "seed": 7, "bm25_k": 20, "dense_enabled": True, "dense_k": 20,
            "block_cap": 2000, "classifier_threshold": 0.8, "lookalike_min_sim": 0.85,
            "hidden_twin_max_sim": 0.75, "tau_b1": None, "tau_b2": None,
            "templates": {"valve": 1}, "dictionary_version": 1, "uom_table_version": 1,
            "embedding_model": "all-MiniLM-L6-v2", "classifier_model": "category_clf-v1",
            "git_commit": "abc1234",
        },
    ),
    (
        j.RunStats,
        {
            "progress": {"stage": "decide", "done": 1, "total": 2},
            "channels": {"B": 1, "L": 0, "D": 0, "M": 0},
            "verdicts": {"IDENTICAL": 0, "EQUIVALENT": 0, "NOT_EQUIVALENT": 0,
                         "INSUFFICIENT_DATA": 0},
            "blocked_egress": 0,
        },
    ),
    (j.RunStats, {}),
    (j.PairBaseline, {"b1": True, "b2": False, "tau1": 0.8, "tau2": 0.7}),
    (
        j.Evidence,
        [{"attr": "pressure_class", "level": "core", "a": 150, "b": 300, "status": "CONFLICT",
          "rule": "VALVE.pressure_class", "rule_text": "Equal", "note_a": None, "note_b": None}],
    ),
    (j.SplitGroups, [[str(uuid.uuid4())], [str(uuid.uuid4()), str(uuid.uuid4())]]),
    (j.CanonicalSpec, {"valve_type": "GATE"}),
    (j.Variants, [{"manufacturer": "ACME", "mpn": "X-1"}]),
    (j.EvalConfig, {"entities": 4000, "cpse_styles": ["A", "B", "C"], "hard_negative_share": 0.3}),
    (j.EvalMetrics, {"hard_negatives": None, "false_merges": None}),
    (j.AuditDiff, {"role": "CHECKER"}),
    (j.IdempotentResponse, {"status_code": 201, "body": {"id": 1}}),
    (j.AbbreviationContent, {"FLGD": "FLANGED"}),
    (j.UomContent, {"aliases": {"NOS": "EA"}, "ambiguous": ["MT"]}),
    (j.HeaderSynonymContent, {"legacy_code": ["matnr", "code"]}),
    (j.UnspscMapContent, {}),
]  # fmt: skip

INVALID: list[tuple[type[BaseModel], object]] = [
    (j.BatchQuality, {"rows": -1}),
    (j.AttrMeta, {"size_dn": {"tier": "GUESS", "confidence": 1.0}}),
    (j.AttrMeta, {"size_dn": {"tier": "RULE", "confidence": 1.5}}),
    (j.RunConfig, {"mode": "EVERYTHING"}),
    (j.RunStats, {"verdicts": {"MAYBE": 1}}),
    (j.RunStats, {"surprise": 1}),
    # MISSING_BOTH rows are never stored (TR-DAT-05); rule and rule_text are required (SF-4)
    (j.Evidence, [{"attr": "trim", "level": "ext", "a": None, "b": None,
                   "status": "MISSING_BOTH", "rule": "VALVE.trim", "rule_text": "x"}]),
    (j.Evidence, [{"attr": "trim", "level": "ext", "a": 1, "b": 2, "status": "CONFLICT"}]),
    (j.SplitGroups, [[]]),
    (j.SplitGroups, [["11111111-1111-1111-1111-111111111111"],
                     ["11111111-1111-1111-1111-111111111111"]]),
    (j.EvalConfig, {"hard_negative_share": 1.5}),
    (j.AuditDiff, {"password_hash": "x"}),
    (j.UomContent, {"aliases": {"MT": "M"}, "ambiguous": ["MT"]}),
    (j.UnspscMapContent, {"PIPING>VALVE>GATE": {"code": "40141600", "source_note": ""}}),
    (j.UnspscMapContent, {"PIPING>VALVE>GATE": {"code": "4014", "source_note": "browser"}}),
    (j.IdempotentResponse, {"status_code": 42, "body": None}),
]  # fmt: skip


@pytest.mark.parametrize(("model", "value"), VALID)
def test_valid_shapes_accepted(model: type[BaseModel], value: object) -> None:
    model.model_validate(value)


@pytest.mark.parametrize(("model", "value"), INVALID)
def test_wrong_shapes_rejected(model: type[BaseModel], value: object) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(value)


def test_template_rule_text_keys_must_be_attributes() -> None:
    base = {"id": "valve", "version": 1, "category": "VALVE", "critical_default": True,
            "core": ["size_dn"]}  # fmt: skip
    j.TemplateDefinition.model_validate({**base, "rule_text": {"size_dn": "as DN"}})
    with pytest.raises(ValidationError):
        j.TemplateDefinition.model_validate({**base, "rule_text": {"colour": "x"}})


def test_every_section_6_column_has_a_contract() -> None:
    section_6 = {
        ("upload_batch", "column_mapping"), ("upload_batch", "quality"), ("material_record", "raw"),
        ("template", "definition"), ("spec_record", "attrs"), ("spec_record", "attr_meta"),
        ("run", "config"), ("run", "stats"), ("pair_decision", "baseline"),
        ("pair_decision", "evidence"), ("review_decision", "split_groups"),
        ("cnmc", "canonical_spec"), ("cnmc", "variants"), ("eval_run", "config"),
        ("eval_run", "metrics"), ("audit_event", "before"), ("audit_event", "after"),
        ("idempotency_key", "response"),
    }  # fmt: skip
    assert set(j.CONTRACTS) == section_6
    assert set(j.DICTIONARY_CONTENT) == {"ABBREVIATION", "UOM", "HEADER_SYNONYM", "UNSPSC_MAP"}
