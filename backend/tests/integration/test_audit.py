"""TRD TR-ALG-09 audit hash chain, TR-TST-09 tamper test, PRD FR-1302."""

import threading
import uuid
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session

from app.db.models import AuditEvent
from app.services import audit
from tests.integration.conftest import wipe_audit


def _add(session: Session, n: int = 3) -> list[AuditEvent]:
    return [
        audit.record(
            session,
            actor_id=None,
            action="LOGIN_FAILED",
            object_type="app_user",
            object_id=f"user{i}",
            after={"reason": "wrong password", "n": i, "ünïcode": "✓"},
        )
        for i in range(n)
    ]


def test_chain_links_from_genesis(session: Session) -> None:
    e = _add(session)
    assert e[0].prev_hash is None
    assert e[1].prev_hash == e[0].hash and e[2].prev_hash == e[1].hash
    first = audit.canonical(
        actor_id=None,
        action="LOGIN_FAILED",
        object_type="app_user",
        object_id="user0",
        before=None,
        after=e[0].after,
        ts=e[0].ts,
    )
    assert e[0].hash == audit.chain_hash(None, first)
    assert audit.verify(session) == audit.VerifyResult(ok=True, events=3, first_bad_id=None)


def test_empty_chain_is_intact(session: Session) -> None:
    assert audit.verify(session) == audit.VerifyResult(ok=True, events=0, first_bad_id=None)


def test_hash_recomputes_after_reading_back_in_another_time_zone(session: Session) -> None:
    _add(session, 2)
    session.execute(text("SET LOCAL TIME ZONE 'Asia/Kolkata'"))
    session.expire_all()
    assert audit.verify(session).ok


def test_canonical_is_stable_and_sorted() -> None:
    ts = datetime(2026, 10, 3, 12, 0, 0, 123456, tzinfo=UTC)
    a = audit.canonical(
        actor_id=None, action="A", object_type="t", object_id="1", before=None, after={"b": 1,
        "a": 2}, ts=ts,
    )  # fmt: skip
    assert a == (
        '{"action":"A","actor_id":null,"after":{"a":2,"b":1},"before":null,'
        '"object_id":"1","object_type":"t","ts":"2026-10-03T12:00:00.123456+00:00"}'
    )
    ist = ts.astimezone(timezone(timedelta(hours=5, minutes=30)))
    assert a == audit.canonical(
        actor_id=None, action="A", object_type="t", object_id="1", before=None,
        after={"a": 2, "b": 1}, ts=ist,
    )  # fmt: skip


def test_secrets_never_enter_the_log(session: Session) -> None:
    with pytest.raises(ValidationError):
        audit.record(
            session, actor_id=None, action="X", object_type="t", object_id="1",
            after={"password": "x"},
        )  # fmt: skip


def test_tamper_disable_trigger_and_edit_reports_that_event(session: Session) -> None:
    """Done-when (Phase 3): disable the trigger as owner, edit a row → verify names the event."""
    e = _add(session, 4)
    session.execute(text("ALTER TABLE audit_event DISABLE TRIGGER audit_event_no_update_delete"))
    session.execute(
        text("""UPDATE audit_event SET after = '{"reason": "edited"}' WHERE id = :id"""),
        {"id": e[2].id},
    )
    assert audit.verify(session) == audit.VerifyResult(ok=False, events=2, first_bad_id=e[2].id)


def test_deleted_row_breaks_the_next_link(session: Session) -> None:
    e = _add(session, 4)
    session.execute(text("ALTER TABLE audit_event DISABLE TRIGGER audit_event_no_update_delete"))
    session.execute(text("DELETE FROM audit_event WHERE id = :id"), {"id": e[1].id})
    assert audit.verify(session).first_bad_id == e[2].id


def test_verify_streams_in_chunks(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(audit, "VERIFY_CHUNK", 2)
    e = _add(session, 5)
    assert audit.verify(session).events == 5
    session.execute(text("ALTER TABLE audit_event DISABLE TRIGGER audit_event_no_update_delete"))
    session.execute(text("UPDATE audit_event SET object_id = 'x' WHERE id = :id"), {"id": e[4].id})
    assert audit.verify(session).first_bad_id == e[4].id


def test_verify_and_record_logs_audit_verified(session: Session) -> None:
    _add(session, 2)
    actor = session.execute(
        text(
            "INSERT INTO app_user (username, password_hash, role) VALUES ('aud','x','AUDITOR')"
            " RETURNING id"
        )
    ).scalar_one()
    result = audit.verify_and_record(session, actor)
    last = session.scalars(select(AuditEvent).order_by(AuditEvent.id.desc())).first()
    assert result.ok and last is not None
    assert (last.action, last.object_type, last.actor_id) == (
        "AUDIT_VERIFIED",
        "audit_event",
        actor,
    )
    assert last.after == {"ok": True, "events": 2, "first_bad_id": None}
    assert audit.verify(session).events == 3


def test_event_rolls_back_with_the_callers_transaction(engine: Engine) -> None:
    with Session(engine) as s:
        audit.record(s, actor_id=None, action="X", object_type="t", object_id="1")
        s.rollback()
    with engine.connect() as c:
        assert c.execute(select(func.count()).select_from(AuditEvent)).scalar_one() == 0


def test_concurrent_appends_are_serialised(engine: Engine) -> None:
    errors: list[BaseException] = []

    def worker(tag: str) -> None:
        try:
            for i in range(10):
                with Session(engine) as s, s.begin():
                    audit.record(s, actor_id=None, action="X", object_type=tag, object_id=str(i))
        except BaseException as exc:  # noqa: BLE001 - surfaced by the assert below
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(f"t{k}",)) for k in range(4)]
    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        with Session(engine) as s:
            assert audit.verify(s) == audit.VerifyResult(ok=True, events=40, first_bad_id=None)
    finally:
        wipe_audit(engine)


def test_list_newest_first_with_filters_and_cursor(session: Session) -> None:
    _add(session, 5)
    audit.record(session, actor_id=None, action="LOGIN_SUCCEEDED", object_type="app_user",
                 object_id="meera")  # fmt: skip
    page, cursor = audit.list_events(session, audit.AuditFilters(action="LOGIN_FAILED"), limit=2)
    assert [e.object_id for e in page] == ["user4", "user3"] and cursor
    page2, cursor2 = audit.list_events(
        session, audit.AuditFilters(action="LOGIN_FAILED"), limit=2, cursor=cursor
    )
    assert [e.object_id for e in page2] == ["user2", "user1"]
    page3, cursor3 = audit.list_events(
        session, audit.AuditFilters(action="LOGIN_FAILED"), limit=2, cursor=cursor2
    )
    assert [e.object_id for e in page3] == ["user0"] and cursor3 is None
    assert len(audit.list_events(session, audit.AuditFilters(object_type="app_user"))[0]) == 6
    future = datetime.now(UTC) + timedelta(hours=1)
    assert audit.list_events(session, audit.AuditFilters(since=future))[0] == []
    assert audit.list_events(session, audit.AuditFilters(actor_id=uuid.uuid4()))[0] == []
