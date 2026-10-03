"""Backend Schema section 15 checks as pytest cases (schema v0.6, Appendix A and B).

Each test runs in a transaction that is rolled back; a rejected statement runs inside a
savepoint so the test can go on. Section 10 invariants enforced by the database are noted
by number.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

IMPDOCS = Path(__file__).resolve().parents[3] / "impdocs"


# ---------- helpers ----------
def ins(conn: Connection, sql: str, **params: Any) -> Any:
    return conn.execute(text(sql), params).scalar()


def rejected(conn: Connection, sql: str, match: str, **params: Any) -> None:
    """The statement fails with an error whose text matches `match`."""
    with pytest.raises(DBAPIError, match=match):
        with conn.begin_nested():
            conn.execute(text(sql), params)


def accepted(conn: Connection, sql: str, **params: Any) -> Any:
    with conn.begin_nested():
        result = conn.execute(text(sql), params)
        return result.scalar() if result.returns_rows else None


def sql_block(doc: str, heading: str) -> str:
    path = IMPDOCS / doc
    if not path.exists():
        pytest.skip("impdocs/ not mounted")
    body = path.read_text(encoding="utf-8")
    body = body[body.index(heading) :]
    start = body.index("```sql\n") + len("```sql\n")
    return body[start : body.index("\n```", start)]


@dataclass
class World:
    cpse_a: uuid.UUID
    cpse_b: uuid.UUID
    maker: uuid.UUID
    checker: uuid.UUID
    rec_lo: uuid.UUID  # rec_lo < rec_hi
    rec_hi: uuid.UUID
    run: uuid.UUID
    cluster: uuid.UUID
    task: uuid.UUID


@pytest.fixture
def w(conn: Connection) -> World:
    """Two CPSEs, a maker (A) and a checker (B), two records, a run, a cluster and its task."""
    cpse = {
        code: ins(
            conn,
            "INSERT INTO cpse (code, name, vendor_salt) VALUES (:c, :c, 's') RETURNING id",
            c=code,
        )
        for code in ("T-A", "T-B")
    }
    user = {
        name: ins(
            conn,
            "INSERT INTO app_user (username, password_hash, role, cpse_id)"
            " VALUES (:u, 'x', :r, :c) RETURNING id",
            u=name, r=role, c=cpse[c],
        )
        for name, role, c in (("t-maker", "MAKER", "T-A"), ("t-checker", "CHECKER", "T-B"))
    }  # fmt: skip
    recs = []
    for code, c in (("L-1", "T-A"), ("L-2", "T-B")):
        batch = ins(
            conn,
            "INSERT INTO upload_batch (cpse_id, filename, file_sha256, status, is_synthetic)"
            " VALUES (:c, 'synthetic.csv', 'x', 'INGESTED', true) RETURNING id",
            c=cpse[c],
        )
        recs.append(
            ins(
                conn,
                "INSERT INTO material_record (batch_id, cpse_id, legacy_code, short_text,"
                " content_hash, annual_value) VALUES (:b, :c, :l, 'GV 4IN CL150', :l, 100)"
                " RETURNING id",
                b=batch, c=cpse[c], l=code,
            )
        )  # fmt: skip
    batch_ids = conn.execute(text("SELECT array_agg(batch_id) FROM material_record")).scalar()
    run = ins(
        conn,
        "INSERT INTO run (batch_ids, mode, status) VALUES (:b, 'CROSS_CPSE', 'DONE') RETURNING id",
        b=batch_ids,
    )
    cluster = ins(
        conn,
        "INSERT INTO cluster (run_id, category, status)"
        " VALUES (:r, 'VALVE', 'PROPOSED') RETURNING id",
        r=run,
    )
    for rec in recs:
        conn.execute(
            text("INSERT INTO cluster_member (cluster_id, record_id) VALUES (:c, :r)"),
            {"c": cluster, "r": rec},
        )
    task = ins(
        conn,
        "INSERT INTO review_task (cluster_id, state) VALUES (:c, 'OPEN') RETURNING id",
        c=cluster,
    )
    lo, hi = sorted(recs, key=str)  # PostgreSQL orders uuid like its text form
    return World(
        cpse["T-A"], cpse["T-B"], user["t-maker"], user["t-checker"], lo, hi, run, cluster, task
    )


def _cnmc(
    conn: Connection, code: str, status: str = "ACTIVE", merged_into: str | None = None
) -> None:
    conn.execute(
        text(
            "INSERT INTO cnmc (cnmc, category, canonical_spec, status, merged_into)"
            " VALUES (:c, 'VALVE', '{}', :s, :m)"
        ),
        {"c": code, "s": status, "m": merged_into},
    )


# ---------- multi-CPSE consent (v0.6, FR-1501; invariants 15, 16) ----------
CONSENT = (
    "INSERT INTO review_consent (task_id, cpse_id, user_id, decision, via, reason)"
    " VALUES (:t, :c, :u, :d, :v, :r)"
)


def test_awaiting_consent_with_maker_and_checker_cpse_consents_accepted(
    conn: Connection, w: World
) -> None:
    conn.execute(
        text(
            "UPDATE review_task SET state = 'AWAITING_CONSENT', made_by = :m, checked_by = :k,"
            " proposed_decision = 'APPROVE' WHERE id = :t"
        ),
        {"m": w.maker, "k": w.checker, "t": w.task},
    )
    accepted(
        conn, CONSENT, t=w.task, c=w.cpse_a, u=w.maker, d="CONSENT", v="MAKER_PROPOSAL", r=None
    )
    accepted(
        conn, CONSENT, t=w.task, c=w.cpse_b, u=w.checker, d="CONSENT",
        v="CHECKER_CONFIRMATION", r=None,
    )  # fmt: skip
    assert ins(conn, "SELECT count(*) FROM review_consent WHERE task_id = :t", t=w.task) == 2


def test_decline_needs_a_reason(conn: Connection, w: World) -> None:
    args = {"t": w.task, "c": w.cpse_b, "u": w.checker, "d": "DECLINE", "v": "STEWARD"}
    rejected(conn, CONSENT, "review_consent_check", **args, r=None)
    rejected(conn, CONSENT, "review_consent_check", **args, r="no")  # shorter than 5
    accepted(conn, CONSENT, **args, r="material grade differs from our spec")


def test_second_consent_row_for_same_cpse_rejected(conn: Connection, w: World) -> None:
    args = {"t": w.task, "c": w.cpse_a, "u": w.maker, "v": "MAKER_PROPOSAL", "r": None}
    accepted(conn, CONSENT, **args, d="CONSENT")
    rejected(conn, CONSENT, "review_consent_pkey", **args, d="CONSENT")


# ---------- change notices (v0.6, SF-12) ----------
NOTICE = (
    "INSERT INTO change_notice (cpse_id, kind, object_type, object_id, summary,"
    " acknowledged_by, acknowledged_at) VALUES (:c, 'CNMC_ISSUED', 'cnmc', 'NMC-00000000018',"
    " 'issued', :by, :at)"
)


def test_change_notice_acknowledged_by_needs_time(conn: Connection, w: World) -> None:
    rejected(conn, NOTICE, "change_notice_check", c=w.cpse_a, by=w.maker, at=None)
    accepted(conn, NOTICE, c=w.cpse_a, by=None, at=None)
    accepted(conn, NOTICE, c=w.cpse_a, by=w.maker, at=date(2026, 10, 3))


# ---------- audit log (invariant 5, FR-1302) ----------
def test_audit_event_is_append_only(conn: Connection) -> None:
    ev = accepted(
        conn,
        "INSERT INTO audit_event (ts, action, object_type, object_id, hash)"
        " VALUES (now(), 'AUDIT_VERIFIED', 'audit_event', '0', 'h0') RETURNING id",
    )
    for sql in (
        "UPDATE audit_event SET action = 'X' WHERE id = :i",
        "DELETE FROM audit_event WHERE id = :i",
        "TRUNCATE audit_event",
    ):
        rejected(conn, sql, "audit_event is append-only", i=ev)
    assert ins(conn, "SELECT action FROM audit_event WHERE id = :i", i=ev) == "AUDIT_VERIFIED"


def test_audit_hash_unique(conn: Connection) -> None:
    sql = (
        "INSERT INTO audit_event (ts, action, object_type, object_id, hash)"
        " VALUES (now(), 'AUDIT_VERIFIED', 'audit_event', '0', 'same')"
    )
    accepted(conn, sql)
    rejected(conn, sql, "audit_event_hash_key")


# ---------- CNMC (invariants 8, 9, 10) ----------
@pytest.mark.parametrize(
    "bad",
    ["NMC-0000000001", "NMC-000000000012", "XYZ-00000000018", "NMC-0000000001A", "nmc-00000000018"],
)
def test_cnmc_bad_format_rejected(conn: Connection, bad: str) -> None:
    rejected(
        conn,
        "INSERT INTO cnmc (cnmc, category, canonical_spec, status)"
        " VALUES (:c, 'VALVE', '{}', 'ACTIVE')",
        "cnmc_cnmc_check",
        c=bad,
    )


def test_cnmc_good_format_accepted(conn: Connection) -> None:
    _cnmc(conn, "NMC-00000000018")
    assert ins(conn, "SELECT status FROM cnmc WHERE cnmc = 'NMC-00000000018'") == "ACTIVE"


def test_merged_cnmc_needs_survivor(conn: Connection) -> None:
    with pytest.raises(DBAPIError, match='"cnmc_check"'):
        with conn.begin_nested():
            _cnmc(conn, "NMC-00000000026", status="MERGED")
    _cnmc(conn, "NMC-00000000018")
    _cnmc(conn, "NMC-00000000026", status="MERGED", merged_into="NMC-00000000018")


def test_short_description_at_most_40(conn: Connection) -> None:
    sql = (
        "INSERT INTO cnmc (cnmc, category, canonical_spec, status, short_desc_40)"
        " VALUES (:c, 'VALVE', '{}', 'ACTIVE', :s)"
    )
    accepted(conn, sql, c="NMC-00000000018", s="X" * 40)
    rejected(conn, sql, "cnmc_short_desc_40_check", c="NMC-00000000026", s="X" * 41)


# ---------- crosswalk (invariants 1, 11) ----------
XWALK = (
    "INSERT INTO crosswalk (cnmc, record_id, cpse_id, legacy_code, relation)"
    " VALUES (:k, :r, :c, 'L-1', 'IDENTICAL') RETURNING id"
)


def test_second_active_mapping_rejected(conn: Connection, w: World) -> None:
    _cnmc(conn, "NMC-00000000018")
    _cnmc(conn, "NMC-00000000026")
    rec = ins(conn, "SELECT id FROM material_record WHERE legacy_code = 'L-1'")
    accepted(conn, XWALK, k="NMC-00000000018", r=rec, c=w.cpse_a)
    rejected(conn, XWALK, "crosswalk_active_uq", k="NMC-00000000026", r=rec, c=w.cpse_a)


def test_removal_needs_who_when_why_then_code_can_be_remapped(conn: Connection, w: World) -> None:
    _cnmc(conn, "NMC-00000000018")
    _cnmc(conn, "NMC-00000000026")
    rec = ins(conn, "SELECT id FROM material_record WHERE legacy_code = 'L-1'")
    xid = accepted(conn, XWALK, k="NMC-00000000018", r=rec, c=w.cpse_a)
    rejected(
        conn, "UPDATE crosswalk SET status = 'REMOVED' WHERE id = :x", "crosswalk_check", x=xid
    )
    rejected(
        conn,
        "UPDATE crosswalk SET status = 'REMOVED', removed_by = :u, removed_at = now()"
        " WHERE id = :x",
        "crosswalk_check",
        x=xid, u=w.maker,
    )  # fmt: skip
    accepted(
        conn,
        "UPDATE crosswalk SET status = 'REMOVED', removed_by = :u, removed_at = now(),"
        " remove_reason = 'unmerge: wrong pressure class' WHERE id = :x",
        x=xid, u=w.maker,
    )  # fmt: skip
    accepted(conn, XWALK, k="NMC-00000000026", r=rec, c=w.cpse_a)


# ---------- maker-checker (invariant 6, FR-803) ----------
def test_checker_equal_to_maker_rejected(conn: Connection, w: World) -> None:
    sql = "UPDATE review_task SET made_by = :m, checked_by = :k WHERE id = :t"
    rejected(conn, sql, "review_task_check", m=w.maker, k=w.maker, t=w.task)
    accepted(conn, sql, m=w.maker, k=w.checker, t=w.task)


def test_one_review_task_per_cluster(conn: Connection, w: World) -> None:
    rejected(
        conn,
        "INSERT INTO review_task (cluster_id, state) VALUES (:c, 'OPEN')",
        "review_task_cluster_id_key",
        c=w.cluster,
    )


# ---------- pair order (invariant 7) ----------
PAIR = (
    "INSERT INTO pair_decision (run_id, rec_a, rec_b, verdict, route, evidence)"
    " VALUES (:run, :a, :b, 'NOT_EQUIVALENT', 'NONE', '[]')"
)


def test_pair_stored_in_wrong_order_rejected(conn: Connection, w: World) -> None:
    rejected(conn, PAIR, "pair_decision_check", run=w.run, a=w.rec_hi, b=w.rec_lo)
    rejected(conn, PAIR, "pair_decision_check", run=w.run, a=w.rec_lo, b=w.rec_lo)
    accepted(conn, PAIR, run=w.run, a=w.rec_lo, b=w.rec_hi)
    rejected(conn, PAIR, "pair_decision_run_id_rec_a_rec_b_key", run=w.run, a=w.rec_lo, b=w.rec_hi)


def test_cannot_link_ordered(conn: Connection, w: World) -> None:
    sql = "INSERT INTO cannot_link (rec_a, rec_b, reason, created_by) VALUES (:a, :b, 'differ', :u)"
    rejected(conn, sql, "cannot_link_check", a=w.rec_hi, b=w.rec_lo, u=w.maker)
    accepted(conn, sql, a=w.rec_lo, b=w.rec_hi, u=w.maker)


# ---------- other database-enforced invariants (section 10: 12, 13, 14) ----------
def test_one_active_template_and_dictionary_version(conn: Connection) -> None:
    tpl = (
        "INSERT INTO template (id, version, category, definition, status)"
        " VALUES ('t-valve', :v, 'VALVE', '{}', :s)"
    )
    accepted(conn, tpl, v=1, s="ACTIVE")
    accepted(conn, tpl, v=2, s="DRAFT")
    rejected(conn, tpl, "template_one_active_uq", v=3, s="ACTIVE")
    dic = "INSERT INTO dictionary (kind, version, content, status) VALUES ('UOM', :v, '{}', :s)"
    accepted(conn, dic, v=91, s="ACTIVE")
    rejected(conn, dic, "dictionary_one_active_uq", v=92, s="ACTIVE")


def test_supplied_attribute_needs_source_note(conn: Connection, w: World) -> None:
    sql = (
        "INSERT INTO attribute_supply (record_id, attr, value, source_note, supplied_by)"
        " VALUES (:r, 'end_connection', 'FLANGED-RF', :n, :u)"
    )
    rejected(conn, sql, "attribute_supply_source_note_check", r=w.rec_lo, n="dsht", u=w.maker)
    accepted(conn, sql, r=w.rec_lo, n="vendor datasheet rev B", u=w.maker)


def test_reingesting_same_row_is_rejected_by_content_hash(conn: Connection, w: World) -> None:
    row = conn.execute(
        text(
            "SELECT batch_id, cpse_id, legacy_code, content_hash FROM material_record WHERE id = :i"
        ),
        {"i": w.rec_lo},
    ).one()
    batch2 = ins(
        conn,
        "INSERT INTO upload_batch (cpse_id, filename, file_sha256, status, is_synthetic)"
        " VALUES (:c, 'again.csv', 'y', 'UPLOADED', true) RETURNING id",
        c=row.cpse_id,
    )
    rejected(
        conn,
        "INSERT INTO material_record (batch_id, cpse_id, legacy_code, short_text, content_hash)"
        " VALUES (:b, :c, :l, 'GV 4IN CL150', :h)",
        "material_record_idem_uq",
        b=batch2, c=row.cpse_id, l=row.legacy_code, h=row.content_hash,
    )  # fmt: skip


# ---------- TRD Appendix J dashboard queries ----------
def test_trd_appendix_j_queries_run(conn: Connection, w: World) -> None:
    block = sql_block("SIH26099_SpecID_TRD.md", "## Appendix J: Dashboard SQL")
    queries = [q.strip() for q in re.split(r"^-- J\.\d.*$", block, flags=re.M) if q.strip()]
    assert len(queries) == 4

    _cnmc(conn, "NMC-00000000018")
    for rec in (w.rec_lo, w.rec_hi):
        cpse, code = conn.execute(
            text("SELECT cpse_id, legacy_code FROM material_record WHERE id = :r"), {"r": rec}
        ).one()
        conn.execute(
            text(
                "INSERT INTO crosswalk"
                " (cnmc, record_id, cpse_id, legacy_code, relation, uom_factor)"
                " VALUES ('NMC-00000000018', :r, :c, :l, 'EQUIVALENT', 1)"
            ),
            {"r": rec, "c": cpse, "l": code},
        )
        conn.execute(
            text("INSERT INTO procurement_line (record_id, po_date, qty) VALUES (:r, :d, 5)"),
            {"r": rec, "d": date(2026, 6, 1)},
        )
    batch_ids = list(
        conn.execute(text("SELECT batch_ids FROM run WHERE id = :r"), {"r": w.run}).scalar()
    )

    j1 = conn.execute(text(queries[0].rstrip(";")), {"batch_ids": batch_ids}).all()
    j2 = conn.execute(text(queries[1].rstrip(";")), {"run_id": w.run}).all()
    j3 = conn.execute(text(queries[2].rstrip(";")), {"run_id": w.run}).scalar()
    j4 = conn.execute(text(queries[3].rstrip(";")), {"min_cpses": 2, "limit": 10}).all()

    assert [tuple(r) for r in j1] == [("T-A", 1), ("T-B", 1)]
    assert sorted(tuple(r) for r in j2) == [("T-A", 0), ("T-B", 0)]
    assert j3 == 1
    assert len(j4) == 1 and j4[0].cpses == 2 and j4[0].combined_qty_base_uom == 10
    assert j4[0].qty_incomplete is False


# ---------- Appendix B: specid_app role and row-level security ----------
def test_appendix_b_hardening_as_specid_app(conn: Connection, w: World) -> None:
    block = sql_block("SIH26099_SpecID_05_Backend_Schema.md", "## Appendix B: Optional hardening")
    if ins(conn, "SELECT count(*) FROM pg_roles WHERE rolname = 'specid_app'"):
        pytest.skip("role specid_app already exists in this cluster")
    conn.exec_driver_sql(block.replace("'set-from-env'", "'test-only-not-a-secret'"))

    for rec, qty in ((w.rec_lo, 3), (w.rec_hi, 7)):
        conn.execute(
            text("INSERT INTO procurement_line (record_id, po_date, qty) VALUES (:r, :d, :q)"),
            {"r": rec, "d": date(2026, 6, 1), "q": qty},
        )
    own = ins(conn, "SELECT cpse_id FROM material_record WHERE id = :r", r=w.rec_lo)
    totals_as_owner = dict(conn.execute(text("SELECT * FROM demand_qty_12m()")).all())

    conn.exec_driver_sql("SET LOCAL ROLE specid_app")
    conn.execute(text("SELECT set_config('app.cpse_id', :c, true)"), {"c": str(own)})
    visible = conn.execute(text("SELECT record_id FROM procurement_line")).scalars().all()
    assert visible == [w.rec_lo]  # own-CPSE rows visible, the other CPSE's hidden
    assert dict(conn.execute(text("SELECT * FROM demand_qty_12m()")).all()) == totals_as_owner
    assert len(totals_as_owner) == 2  # the aggregate still returns both CPSEs' totals
    rejected(conn, "DELETE FROM audit_event", "permission denied")
    conn.exec_driver_sql("RESET ROLE")
