"""0002_v2: stock on hand, HSN code, pgvector embeddings (docs/SOLUTION.md 9.3, DEC-31).

- material_record.stock_qty: quantity on hand, for stock sharing (Pillar 6)
- cnmc.hsn: Indian HSN code next to UNSPSC, from a verified table only (4, 6 or 8 digits)
- spec_record.embedding: real[] (never written in v1) becomes vector(768) for nomic-embed-text
- cnmc.embedding: vector(768), for search-before-create over the registry
- HNSW cosine indexes on both embedding columns

Revision ID: 0002_v2
Revises: 0001_initial
"""

from alembic import op

revision = "0002_v2"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

UP = """
CREATE EXTENSION IF NOT EXISTS vector;

ALTER TABLE material_record
  ADD COLUMN stock_qty numeric CHECK (stock_qty IS NULL OR stock_qty >= 0);

ALTER TABLE cnmc
  ADD COLUMN hsn text CHECK (hsn IS NULL OR hsn ~ '^[0-9]{4}([0-9]{2}){0,2}$'),
  ADD COLUMN embedding vector(768);

ALTER TABLE spec_record ALTER COLUMN embedding TYPE vector(768) USING NULL;

CREATE INDEX spec_record_embedding_hnsw ON spec_record USING hnsw (embedding vector_cosine_ops);
CREATE INDEX cnmc_embedding_hnsw ON cnmc USING hnsw (embedding vector_cosine_ops);
"""

DOWN = """
DROP INDEX IF EXISTS cnmc_embedding_hnsw;
DROP INDEX IF EXISTS spec_record_embedding_hnsw;
ALTER TABLE spec_record ALTER COLUMN embedding TYPE real[] USING NULL;
ALTER TABLE cnmc DROP COLUMN embedding, DROP COLUMN hsn;
ALTER TABLE material_record DROP COLUMN stock_qty;
"""


def upgrade() -> None:
    op.get_bind().exec_driver_sql(UP)


def downgrade() -> None:
    op.get_bind().exec_driver_sql(DOWN)
