"""TR-DAT-01: the SQLAlchemy models mirror the migrated schema (Backend Schema Appendix A)."""

import pytest
from sqlalchemy import Connection, inspect
from sqlalchemy.dialects import postgresql

from app.db.models import Base

DIALECT = postgresql.dialect()


def _type(t: object) -> str:
    return t.compile(dialect=DIALECT)  # type: ignore[attr-defined, no-any-return]


def test_model_tables_equal_db_tables(conn: Connection) -> None:
    db_tables = set(inspect(conn).get_table_names()) - {"alembic_version"}
    assert set(Base.metadata.tables) == db_tables
    assert len(db_tables) == 26


@pytest.mark.parametrize("table", sorted(Base.metadata.tables))
def test_columns_keys_and_foreign_keys_match(conn: Connection, table: str) -> None:
    insp = inspect(conn)
    model = Base.metadata.tables[table]

    db_cols = {c["name"]: (_type(c["type"]), c["nullable"]) for c in insp.get_columns(table)}
    model_cols = {c.name: (_type(c.type), c.nullable) for c in model.columns}
    assert model_cols == db_cols

    assert [c.name for c in model.primary_key.columns] == insp.get_pk_constraint(table)[
        "constrained_columns"
    ]

    db_fks = {
        (tuple(fk["constrained_columns"]), fk["referred_table"], tuple(fk["referred_columns"]))
        for fk in insp.get_foreign_keys(table)
    }
    model_fks = {
        ((fk.parent.name,), fk.column.table.name, (fk.column.name,)) for fk in model.foreign_keys
    }
    assert model_fks == db_fks
