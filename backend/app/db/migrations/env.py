"""Alembic environment. The database URL comes from DATABASE_URL (TRD TR-DAT-01)."""

import os

from alembic import context
from sqlalchemy import create_engine, pool

config = context.config


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or os.environ["DATABASE_URL"]
    engine = create_engine(url, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise SystemExit("offline (SQL script) mode is not used; run against the database")
run_migrations_online()
