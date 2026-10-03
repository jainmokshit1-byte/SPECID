"""TR-DAT-03: COPY helper writes bulk rows in batches inside the caller's transaction."""

import hashlib
import uuid

import pytest
from sqlalchemy import Connection, text

from app.db.copy import BATCH_SIZE, copy_rows


def _cpse_and_batch(conn: Connection) -> tuple[uuid.UUID, uuid.UUID]:
    cpse = conn.execute(
        text("INSERT INTO cpse (code, name, vendor_salt) VALUES ('T-1', 'Test', 's') RETURNING id")
    ).scalar_one()
    batch = conn.execute(
        text(
            "INSERT INTO upload_batch (cpse_id, filename, file_sha256, status, is_synthetic)"
            " VALUES (:c, 'synthetic.csv', 'x', 'UPLOADED', true) RETURNING id"
        ),
        {"c": cpse},
    ).scalar_one()
    return cpse, batch


def test_copy_12001_records_in_three_batches(conn: Connection) -> None:
    cpse, batch = _cpse_and_batch(conn)
    n = 2 * BATCH_SIZE + 1
    ids = [uuid.uuid4() for _ in range(n)]
    rows = (
        (ids[i], batch, cpse, f"L{i:06d}", f"SYNTHETIC ITEM {i}",
         hashlib.sha256(str(i).encode()).hexdigest(), {"Description": f"SYNTHETIC ITEM {i}"})
        for i in range(n)
    )  # fmt: skip
    cols = ["id", "batch_id", "cpse_id", "legacy_code", "short_text", "content_hash", "raw"]
    assert copy_rows(conn, "material_record", cols, rows) == n

    assert conn.execute(text("SELECT count(*) FROM material_record")).scalar() == n
    last = conn.execute(
        text("SELECT legacy_code, raw->>'Description' FROM material_record WHERE id = :i"),
        {"i": ids[-1]},
    ).one()
    assert tuple(last) == (f"L{n - 1:06d}", f"SYNTHETIC ITEM {n - 1}")


def test_copy_adapts_jsonb_and_arrays(conn: Connection) -> None:
    cpse, batch = _cpse_and_batch(conn)
    rec = uuid.uuid4()
    copy_rows(
        conn, "material_record", ["id", "batch_id", "cpse_id", "legacy_code", "short_text",
                                  "content_hash"],
        [(rec, batch, cpse, "L1", "GV 4IN", "h1")],
    )  # fmt: skip
    copy_rows(
        conn,
        "spec_record",
        ["record_id", "norm_text", "attrs", "attr_meta", "residual", "class_path", "embedding"],
        [(rec, "GATE VALVE 4 IN", {"size_dn": 100, "trim": None},
          {"size_dn": {"tier": "RULE", "confidence": 1.0, "note": "4 IN = DN100"}},
          ["XYZ"], ["PIPING", "VALVE", "GATE"], [0.25, -0.5])],
    )  # fmt: skip
    row = conn.execute(
        text(
            "SELECT attrs->'size_dn', attrs ? 'trim', attr_meta->'size_dn'->>'note', residual,"
            " class_path, embedding FROM spec_record WHERE record_id = :r"
        ),
        {"r": rec},
    ).one()
    assert tuple(row) == (100, True, "4 IN = DN100", ["XYZ"], ["PIPING", "VALVE", "GATE"],
                          [0.25, -0.5])  # fmt: skip


def test_copy_rejects_unknown_column(conn: Connection) -> None:
    with pytest.raises(ValueError, match="no column"):
        copy_rows(conn, "cpse", ["code", "colour"], [])


def test_copy_is_rolled_back_with_the_transaction(engine) -> None:  # type: ignore[no-untyped-def]
    with engine.connect() as c:
        tx = c.begin()
        copy_rows(c, "cpse", ["code", "name", "vendor_salt"], [("T-ROLLBACK", "Test", "s")])
        tx.rollback()
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM cpse WHERE code = 'T-ROLLBACK'")).scalar() == 0
