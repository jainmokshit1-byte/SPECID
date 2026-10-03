"""TR-DAT-01: 0001_initial is Backend Schema Appendix A (schema v0.6) verbatim."""

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


def test_head_is_0001(conn: Connection) -> None:
    assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0001_initial"


def test_audit_triggers_and_cnmc_sequence(conn: Connection) -> None:
    triggers = conn.execute(
        text("SELECT tgname FROM pg_trigger WHERE tgrelid = 'audit_event'::regclass")
    ).scalars()
    assert {"audit_event_no_update_delete", "audit_event_no_truncate"} <= set(triggers)
    assert conn.execute(text("SELECT to_regclass('cnmc_seq')")).scalar() == "cnmc_seq"
