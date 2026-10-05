"""TR-DAT-01: 0001_initial is Backend Schema Appendix A (schema v0.6) verbatim; 0002_v2 adds
stock, HSN and pgvector embeddings (DEC-31)."""

import re
from pathlib import Path

import pytest
from sqlalchemy import Connection, text

from app.db.migrate import MIGRATIONS

SQL_FILE = MIGRATIONS / "versions" / "0001_initial.sql"
IMPDOCS = Path(__file__).resolve().parents[3] / "impdocs"
SCHEMA_DOC = IMPDOCS / "SIH26099_SpecID_05_Backend_Schema.md"

TABLES = {
    "cpse", "app_user", "api_key", "upload_batch", "material_record", "procurement_line",
    "template", "dictionary", "spec_record", "attribute_supply", "run", "pair_decision",
    "cannot_link", "substitution", "cluster", "cluster_member", "blocked_edge", "review_task",
    "review_decision", "review_consent", "cnmc", "crosswalk", "change_notice", "eval_run",
    "audit_event", "idempotency_key",
}  # fmt: skip


def test_sql_file_equals_appendix_a() -> None:
    if not SCHEMA_DOC.exists():
        pytest.skip("impdocs/ not mounted")
    doc = SCHEMA_DOC.read_text(encoding="utf-8")
    appendix = doc[doc.index("## Appendix A: DDL") :]
    block = re.search(r"```sql\n(.*?)```", appendix, re.S)
    assert block is not None
    assert SQL_FILE.read_text(encoding="utf-8") == block.group(1)


def test_all_26_tables_created(conn: Connection) -> None:
    rows = conn.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    ).scalars()
    assert set(rows) - {"alembic_version"} == TABLES
    assert len(TABLES) == 26


def test_head_is_0003(conn: Connection) -> None:
    assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0003_spelling"


def test_0002_columns_and_vector_indexes(conn: Connection) -> None:
    def col_type(table: str, col: str) -> str | None:
        return conn.execute(
            text(
                "SELECT format_type(atttypid, atttypmod) FROM pg_attribute"
                " WHERE attrelid = CAST(:t AS regclass) AND attname = :c AND NOT attisdropped"
            ),
            {"t": table, "c": col},
        ).scalar()

    assert conn.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()
    assert col_type("material_record", "stock_qty") == "numeric"
    assert col_type("cnmc", "hsn") == "text"
    assert col_type("cnmc", "embedding") == "vector(768)"
    assert col_type("spec_record", "embedding") == "vector(768)"
    indexes = set(
        conn.execute(
            text("SELECT indexname FROM pg_indexes WHERE indexname LIKE '%_hnsw'")
        ).scalars()
    )
    assert indexes == {"spec_record_embedding_hnsw", "cnmc_embedding_hnsw"}


@pytest.mark.parametrize(
    "hsn,ok",
    [
        ("8481", True),
        ("848180", True),
        ("84818030", True),
        ("848", False),
        ("84818", False),
        ("8481A0", False),
    ],
)
def test_0002_hsn_format(conn: Connection, hsn: str, ok: bool) -> None:
    stmt = text(
        "INSERT INTO cnmc (cnmc, category, canonical_spec, status, hsn)"
        " VALUES ('NMC-00000000018', 'VALVE', '{}', 'ACTIVE', :h)"
    )
    sp = conn.begin_nested()
    if ok:
        conn.execute(stmt, {"h": hsn})
    else:
        with pytest.raises(Exception, match="check constraint"):
            conn.execute(stmt, {"h": hsn})
    sp.rollback()


def test_audit_triggers_and_cnmc_sequence(conn: Connection) -> None:
    triggers = conn.execute(
        text("SELECT tgname FROM pg_trigger WHERE tgrelid = 'audit_event'::regclass")
    ).scalars()
    assert {"audit_event_no_update_delete", "audit_event_no_truncate"} <= set(triggers)
    assert conn.execute(text("SELECT to_regclass('cnmc_seq')")).scalar() == "cnmc_seq"
