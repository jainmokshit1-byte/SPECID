"""Bulk inserts with psycopg 3 COPY (TRD TR-DAT-03).

`material_record`, `spec_record`, `pair_decision` and `cluster_member` are written with
`COPY ... FROM STDIN` in batches of 5,000 rows, inside the caller's transaction.
UUIDs come from Python (TR-DAT-02) so rows can reference each other before insert.
"""

from collections.abc import Iterable, Iterator, Sequence
from itertools import islice
from typing import Any

from psycopg import sql
from sqlalchemy import Connection, text

BATCH_SIZE = 5000


def _batched(rows: Iterable[Sequence[Any]], n: int) -> Iterator[list[Sequence[Any]]]:
    it = iter(rows)
    while batch := list(islice(it, n)):
        yield batch


def _column_oids(conn: Connection, table: str, columns: Sequence[str]) -> list[int]:
    rows = conn.execute(
        text(
            "SELECT attname, atttypid::int FROM pg_attribute"
            " WHERE attrelid = CAST(:t AS regclass) AND attnum > 0 AND NOT attisdropped"
        ),
        {"t": table},
    ).all()
    oids = dict(rows)
    missing = [c for c in columns if c not in oids]
    if missing:
        raise ValueError(f"{table} has no column(s) {missing}")
    return [oids[c] for c in columns]


def copy_rows(
    conn: Connection,
    table: str,
    columns: Sequence[str],
    rows: Iterable[Sequence[Any]],
    batch_size: int = BATCH_SIZE,
) -> int:
    """COPY `rows` into `table(columns)`; returns the number of rows written.

    Values are adapted by the column's database type: dict/list for jsonb, list for arrays.
    """
    oids = _column_oids(conn, table, columns)
    stmt = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns))
    )
    raw = conn.connection.driver_connection
    assert raw is not None
    written = 0
    with raw.cursor() as cur:
        for batch in _batched(rows, batch_size):
            with cur.copy(stmt) as cp:
                cp.set_types(oids)
                for row in batch:
                    cp.write_row(row)
            written += len(batch)
    return written
