"""0001_initial: Backend Schema Appendix A (schema v0.6), verbatim.

The DDL lives in 0001_initial.sql, copied byte for byte from the Backend Schema;
tests/integration/test_migration.py checks that it still matches.

Revision ID: 0001_initial
Revises:
"""

from pathlib import Path

from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

SQL = Path(__file__).with_suffix(".sql")


def upgrade() -> None:
    # exec_driver_sql: no bind-parameter parsing, the file runs as written
    op.get_bind().exec_driver_sql(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    # Backend Schema section 13: down-migrations start after 0001
    raise NotImplementedError("0001_initial has no downgrade")
