"""SQLAlchemy 2.0 models for the 26 tables of Backend Schema Appendix A (schema v0.6).

The DDL (CHECK constraints, partial indexes, triggers) lives only in the Alembic migrations;
these classes mirror columns, keys and foreign keys for queries and are checked against the
migrated database by tests/integration/test_models_match_db.py.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    REAL,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NOW = text("now()")


class Base(DeclarativeBase):
    type_annotation_map = {
        uuid.UUID: UUID(as_uuid=True),
        str: Text(),
        int: Integer(),
        bool: Boolean(),
        Decimal: Numeric(),
        datetime: DateTime(timezone=True),
        date: Date(),
        dict[str, Any]: JSONB(),
        list[Any]: JSONB(),
    }


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, server_default=text("gen_random_uuid()"))


def _created_at() -> Mapped[datetime]:
    return mapped_column(server_default=NOW)


def _fk(target: str, **kw: Any) -> Any:
    return mapped_column(ForeignKey(target, **kw))


# ===== Organisations and access =====
class Cpse(Base):
    __tablename__ = "cpse"
    id: Mapped[uuid.UUID] = _uuid_pk()
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    sector: Mapped[str | None]
    vendor_salt: Mapped[str]
    created_at: Mapped[datetime] = _created_at()


class AppUser(Base):
    __tablename__ = "app_user"
    id: Mapped[uuid.UUID] = _uuid_pk()
    username: Mapped[str] = mapped_column(unique=True)
    display_name: Mapped[str | None]
    password_hash: Mapped[str]
    role: Mapped[str]
    cpse_id: Mapped[uuid.UUID | None] = _fk("cpse.id")
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    must_change_password: Mapped[bool] = mapped_column(server_default=text("true"))
    last_login_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = _created_at()


class ApiKey(Base):
    __tablename__ = "api_key"
    id: Mapped[uuid.UUID] = _uuid_pk()
    user_id: Mapped[uuid.UUID] = _fk("app_user.id")
    key_hash: Mapped[str] = mapped_column(unique=True)
    label: Mapped[str]
    created_at: Mapped[datetime] = _created_at()
    revoked_at: Mapped[datetime | None]


# ===== Ingestion =====
class UploadBatch(Base):
    __tablename__ = "upload_batch"
    id: Mapped[uuid.UUID] = _uuid_pk()
    cpse_id: Mapped[uuid.UUID] = _fk("cpse.id")
    filename: Mapped[str]
    file_sha256: Mapped[str]
    status: Mapped[str]
    column_mapping: Mapped[dict[str, Any] | None]
    row_count: Mapped[int | None]
    quality: Mapped[dict[str, Any] | None]
    is_synthetic: Mapped[bool] = mapped_column(server_default=text("false"))
    created_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    created_at: Mapped[datetime] = _created_at()


class MaterialRecord(Base):
    __tablename__ = "material_record"
    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_id: Mapped[uuid.UUID] = _fk("upload_batch.id", ondelete="CASCADE")
    cpse_id: Mapped[uuid.UUID] = _fk("cpse.id")
    legacy_code: Mapped[str]
    short_text: Mapped[str]
    long_text: Mapped[str | None]
    uom: Mapped[str | None]
    uom_canonical: Mapped[str | None]
    mat_group: Mapped[str | None]
    manufacturer: Mapped[str | None]
    mpn: Mapped[str | None]
    plant: Mapped[str | None]
    criticality: Mapped[str | None]
    annual_value: Mapped[Decimal | None]
    annual_qty: Mapped[Decimal | None]
    content_hash: Mapped[str]
    raw: Mapped[dict[str, Any] | None]
    created_at: Mapped[datetime] = _created_at()


class ProcurementLine(Base):
    __tablename__ = "procurement_line"
    id: Mapped[uuid.UUID] = _uuid_pk()
    record_id: Mapped[uuid.UUID] = _fk("material_record.id", ondelete="CASCADE")
    po_date: Mapped[date]
    qty: Mapped[Decimal]
    uom: Mapped[str | None]
    unit_price: Mapped[Decimal | None]
    currency: Mapped[str] = mapped_column(server_default=text("'INR'"))
    vendor_hash: Mapped[str | None]
    plant: Mapped[str | None]
    created_at: Mapped[datetime] = _created_at()


# ===== Rulebook =====
class Template(Base):
    __tablename__ = "template"
    id: Mapped[str] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str]
    definition: Mapped[dict[str, Any]]
    status: Mapped[str]
    golden_passed: Mapped[int | None]
    golden_failed: Mapped[int | None]
    created_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    created_at: Mapped[datetime] = _created_at()
    activated_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    activated_at: Mapped[datetime | None]


class Dictionary(Base):
    __tablename__ = "dictionary"
    kind: Mapped[str] = mapped_column(primary_key=True)
    version: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[dict[str, Any]]
    status: Mapped[str]
    created_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    created_at: Mapped[datetime] = _created_at()


# ===== Specifications =====
class SpecRecord(Base):
    __tablename__ = "spec_record"
    record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("material_record.id", ondelete="CASCADE"), primary_key=True
    )
    template_id: Mapped[str | None]
    template_version: Mapped[int | None]
    category: Mapped[str | None]
    class_source: Mapped[str] = mapped_column(server_default=text("'NONE'"))
    class_prob: Mapped[Decimal | None]
    class_path: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    norm_text: Mapped[str]
    attrs: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'"))
    attr_meta: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'"))
    residual: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    spec_completeness: Mapped[Decimal | None]
    embedding: Mapped[list[float] | None] = mapped_column(ARRAY(REAL))
    dictionary_version: Mapped[int | None]
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _created_at()


class AttributeSupply(Base):
    __tablename__ = "attribute_supply"
    id: Mapped[uuid.UUID] = _uuid_pk()
    record_id: Mapped[uuid.UUID] = _fk("material_record.id", ondelete="CASCADE")
    attr: Mapped[str]
    value: Mapped[str]
    source_note: Mapped[str]
    supplied_by: Mapped[uuid.UUID] = _fk("app_user.id")
    supplied_at: Mapped[datetime] = _created_at()


# ===== Runs and decisions =====
class Run(Base):
    __tablename__ = "run"
    id: Mapped[uuid.UUID] = _uuid_pk()
    batch_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    mode: Mapped[str]
    config: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'"))
    status: Mapped[str]
    stats: Mapped[dict[str, Any] | None]
    error: Mapped[str | None]
    started_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    started_at: Mapped[datetime] = _created_at()
    finished_at: Mapped[datetime | None]


class PairDecision(Base):
    __tablename__ = "pair_decision"
    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = _fk("run.id", ondelete="CASCADE")
    rec_a: Mapped[uuid.UUID] = _fk("material_record.id")
    rec_b: Mapped[uuid.UUID] = _fk("material_record.id")
    verdict: Mapped[str]
    route: Mapped[str]
    p_equiv: Mapped[Decimal | None]
    text_sim: Mapped[Decimal | None]
    baseline: Mapped[dict[str, Any] | None]
    lookalike: Mapped[str | None]
    channels: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    reasons: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    evidence: Mapped[list[Any]]
    model_version: Mapped[str | None]
    template_version: Mapped[int | None]
    created_at: Mapped[datetime] = _created_at()


class CannotLink(Base):
    __tablename__ = "cannot_link"
    rec_a: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("material_record.id", ondelete="CASCADE"), primary_key=True
    )
    rec_b: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("material_record.id", ondelete="CASCADE"), primary_key=True
    )
    reason: Mapped[str]
    created_by: Mapped[uuid.UUID] = _fk("app_user.id")
    created_at: Mapped[datetime] = _created_at()


class Substitution(Base):
    __tablename__ = "substitution"
    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID | None] = _fk("run.id", ondelete="SET NULL")
    from_record: Mapped[uuid.UUID] = _fk("material_record.id")
    to_record: Mapped[uuid.UUID] = _fk("material_record.id")
    rule: Mapped[str]
    status: Mapped[str]
    approver_id: Mapped[uuid.UUID | None] = _fk("app_user.id")
    reason: Mapped[str | None]
    created_at: Mapped[datetime] = _created_at()


# ===== Clusters and review =====
class Cluster(Base):
    __tablename__ = "cluster"
    id: Mapped[uuid.UUID] = _uuid_pk()
    run_id: Mapped[uuid.UUID] = _fk("run.id", ondelete="CASCADE")
    category: Mapped[str | None]
    status: Mapped[str]
    cohesion: Mapped[Decimal | None]
    needs_review: Mapped[bool] = mapped_column(server_default=text("true"))
    is_critical: Mapped[bool] = mapped_column(server_default=text("false"))
    flags_count: Mapped[int] = mapped_column(server_default=text("0"))
    priority: Mapped[Decimal | None]
    created_at: Mapped[datetime] = _created_at()


class ClusterMember(Base):
    __tablename__ = "cluster_member"
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="CASCADE"), primary_key=True
    )
    record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("material_record.id"), primary_key=True)


class BlockedEdge(Base):
    __tablename__ = "blocked_edge"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = _fk("run.id", ondelete="CASCADE")
    rec_a: Mapped[uuid.UUID] = _fk("material_record.id")
    rec_b: Mapped[uuid.UUID] = _fk("material_record.id")
    blocking_a: Mapped[uuid.UUID] = _fk("material_record.id")
    blocking_b: Mapped[uuid.UUID] = _fk("material_record.id")
    reason: Mapped[str]


class ReviewTask(Base):
    __tablename__ = "review_task"
    id: Mapped[uuid.UUID] = _uuid_pk()
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cluster.id", ondelete="CASCADE"), unique=True
    )
    state: Mapped[str]
    made_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    proposed_decision: Mapped[str | None]
    checked_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    created_at: Mapped[datetime] = _created_at()
    updated_at: Mapped[datetime] = _created_at()


class ReviewDecision(Base):
    __tablename__ = "review_decision"
    id: Mapped[uuid.UUID] = _uuid_pk()
    task_id: Mapped[uuid.UUID] = _fk("review_task.id", ondelete="CASCADE")
    actor_id: Mapped[uuid.UUID] = _fk("app_user.id")
    actor_role: Mapped[str]
    decision: Mapped[str]
    comment: Mapped[str | None]
    split_groups: Mapped[list[Any] | None]
    created_at: Mapped[datetime] = _created_at()


class ReviewConsent(Base):
    __tablename__ = "review_consent"
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("review_task.id", ondelete="CASCADE"), primary_key=True
    )
    cpse_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cpse.id"), primary_key=True)
    user_id: Mapped[uuid.UUID] = _fk("app_user.id")
    decision: Mapped[str]
    via: Mapped[str]
    reason: Mapped[str | None]
    created_at: Mapped[datetime] = _created_at()


# ===== Registry =====
class Cnmc(Base):
    __tablename__ = "cnmc"
    cnmc: Mapped[str] = mapped_column(primary_key=True)
    template_id: Mapped[str | None]
    template_version: Mapped[int | None]
    category: Mapped[str]
    class_path: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    unspsc: Mapped[str | None]
    canonical_spec: Mapped[dict[str, Any]]
    spec_completeness: Mapped[Decimal | None]
    variants: Mapped[list[Any]] = mapped_column(server_default=text("'[]'"))
    base_uom: Mapped[str | None]
    short_desc_40: Mapped[str | None]
    long_desc: Mapped[str | None]
    status: Mapped[str]
    merged_into: Mapped[str | None] = _fk("cnmc.cnmc")
    source_cluster: Mapped[uuid.UUID | None] = _fk("cluster.id")
    version: Mapped[int] = mapped_column(server_default=text("1"))
    issued_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    issued_at: Mapped[datetime] = _created_at()


class Crosswalk(Base):
    __tablename__ = "crosswalk"
    id: Mapped[uuid.UUID] = _uuid_pk()
    cnmc: Mapped[str] = _fk("cnmc.cnmc")
    record_id: Mapped[uuid.UUID] = _fk("material_record.id")
    cpse_id: Mapped[uuid.UUID] = _fk("cpse.id")
    legacy_code: Mapped[str]
    relation: Mapped[str]
    status: Mapped[str] = mapped_column(server_default=text("'ACTIVE'"))
    uom: Mapped[str | None]
    uom_factor: Mapped[Decimal | None]
    migration_action: Mapped[str | None]
    cluster_id: Mapped[uuid.UUID | None] = _fk("cluster.id")
    approver_id: Mapped[uuid.UUID | None] = _fk("app_user.id")
    approved_at: Mapped[datetime] = _created_at()
    removed_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    removed_at: Mapped[datetime | None]
    remove_reason: Mapped[str | None]


class ChangeNotice(Base):
    __tablename__ = "change_notice"
    id: Mapped[uuid.UUID] = _uuid_pk()
    cpse_id: Mapped[uuid.UUID] = _fk("cpse.id")
    kind: Mapped[str]
    object_type: Mapped[str]
    object_id: Mapped[str]
    summary: Mapped[str]
    delta: Mapped[list[Any]] = mapped_column(server_default=text("'[]'"))
    audit_event_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = _created_at()
    acknowledged_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    acknowledged_at: Mapped[datetime | None]


# ===== Evaluation =====
class EvalRun(Base):
    __tablename__ = "eval_run"
    id: Mapped[uuid.UUID] = _uuid_pk()
    kind: Mapped[str]
    run_id: Mapped[uuid.UUID | None] = _fk("run.id", ondelete="SET NULL")
    seed: Mapped[int | None]
    config: Mapped[dict[str, Any]] = mapped_column(server_default=text("'{}'"))
    status: Mapped[str]
    metrics: Mapped[dict[str, Any] | None]
    git_commit: Mapped[str | None]
    report_path: Mapped[str | None]
    created_by: Mapped[uuid.UUID | None] = _fk("app_user.id")
    created_at: Mapped[datetime] = _created_at()


# ===== Audit (append-only) =====
class AuditEvent(Base):
    __tablename__ = "audit_event"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ts: Mapped[datetime]  # set by the app, no default (TRD TR-ALG-09)
    actor_id: Mapped[uuid.UUID | None] = _fk("app_user.id")
    action: Mapped[str]
    object_type: Mapped[str]
    object_id: Mapped[str]
    before: Mapped[dict[str, Any] | None]
    after: Mapped[dict[str, Any] | None]
    prev_hash: Mapped[str | None]
    hash: Mapped[str] = mapped_column(unique=True)


# ===== API idempotency (P1) =====
class IdempotencyKey(Base):
    __tablename__ = "idempotency_key"
    key: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), primary_key=True)
    endpoint: Mapped[str] = mapped_column(primary_key=True)
    response: Mapped[dict[str, Any]]
    created_at: Mapped[datetime] = _created_at()
