"""Bulk inserts with psycopg 3 COPY (TRD TR-DAT-03).

`material_record`, `spec_record`, `pair_decision` and `cluster_member` are written with
`COPY ... FROM STDIN` in batches of 5,000 rows, inside the caller's transaction.
UUIDs come from Python (TR-DAT-02) so rows can reference each other before insert.
pgvector columns (DEC-31) take a sequence of floats and are sent as the vector text literal.
"""

from collections.abc import Iterable, Iterator, Sequence
from itertools import islice
from typing import Any

from psycopg import sql
from sqlalchemy import Connection, text

BATCH_SIZE = 5000
TEXT_OID = 25


def _batched(rows: Iterable[Sequence[Any]], n: int) -> Iterator[list[Sequence[Any]]]:
    it = iter(rows)
    while batch := list(islice(it, n)):
        yield batch


def _column_types(conn: Connection, table: str, columns: Sequence[str]) -> list[tuple[int, str]]:
    rows = conn.execute(
        text(
            "SELECT a.attname, a.atttypid::int, t.typname FROM pg_attribute a"
            " JOIN pg_type t ON t.oid = a.atttypid"
            " WHERE a.attrelid = CAST(:t AS regclass) AND a.attnum > 0 AND NOT a.attisdropped"
        ),
        {"t": table},
    ).all()
    types = {name: (oid, typname) for name, oid, typname in rows}
    missing = [c for c in columns if c not in types]
    if missing:
        raise ValueError(f"{table} has no column(s) {missing}")
    return [types[c] for c in columns]


def _vector_literal(value: Any) -> str | None:
    if value is None:
        return None
    return "[" + ",".join(repr(float(x)) for x in value) + "]"


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
    types = _column_types(conn, table, columns)
    vector_cols = [i for i, (_, typname) in enumerate(types) if typname == "vector"]
    # text COPY: the server parses each field with the column's input function, so a vector
    # column can be sent as its text literal
    oids = [TEXT_OID if typname == "vector" else oid for oid, typname in types]
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
                    if vector_cols:
                        row = list(row)
                        for i in vector_cols:
                            row[i] = _vector_literal(row[i])
                    cp.write_row(row)
            written += len(batch)
    return written
