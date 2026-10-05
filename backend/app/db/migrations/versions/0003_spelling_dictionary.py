"""0003_spelling: dictionary kind SPELLING (spelling repair word lists, DEC-34).

Revision ID: 0003_spelling
Revises: 0002_v2
"""

from alembic import op

revision = "0003_spelling"
down_revision = "0002_v2"
branch_labels = None
depends_on = None

KINDS_V1 = "'ABBREVIATION','UOM','HEADER_SYNONYM','UNSPSC_MAP'"


def upgrade() -> None:
    op.get_bind().exec_driver_sql(
        "ALTER TABLE dictionary DROP CONSTRAINT dictionary_kind_check;"
        " ALTER TABLE dictionary ADD CONSTRAINT dictionary_kind_check"
        f" CHECK (kind IN ({KINDS_V1},'SPELLING'))"
    )


def downgrade() -> None:
    op.get_bind().exec_driver_sql(
        "DELETE FROM dictionary WHERE kind = 'SPELLING';"
        " ALTER TABLE dictionary DROP CONSTRAINT dictionary_kind_check;"
        f" ALTER TABLE dictionary ADD CONSTRAINT dictionary_kind_check CHECK (kind IN ({KINDS_V1}))"
    )
