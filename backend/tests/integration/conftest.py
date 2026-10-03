"""Integration fixtures: a fresh schema per session, a rolled-back transaction per test.

Needs DATABASE_URL pointing at a throwaway PostgreSQL 16 database (CI, ci_local.sh).
"""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, Engine, create_engine

from app.db.migrate import upgrade_head


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = os.environ["DATABASE_URL"]
    eng = create_engine(url)
    with eng.begin() as c:
        # back to an empty database; PUBLIC keeps USAGE on the schema as in a fresh PG 16
        c.exec_driver_sql(
            "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
            " GRANT USAGE ON SCHEMA public TO PUBLIC"
        )
    upgrade_head(url)
    yield eng
    eng.dispose()


@pytest.fixture
def conn(engine: Engine) -> Iterator[Connection]:
    """A connection inside a transaction that is rolled back after the test."""
    with engine.connect() as c:
        tx = c.begin()
        try:
            yield c
        finally:
            tx.rollback()
