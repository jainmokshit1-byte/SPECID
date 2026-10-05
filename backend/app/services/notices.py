"""Per-CPSE change notices (PRD SF-12, FR-1511-1513; TRD TR-MOD-33).

Created inside the transaction of the change that causes them (issuance, decline, …), so a
notice exists exactly when its change does. Acknowledging is idempotent and audited.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import AppUser, ChangeNotice, Cpse
from app.services import audit
from app.services.errors import Forbidden, NotFound


def create(
    session: Session,
    *,
    cpse_id: uuid.UUID,
    kind: str,
    object_type: str,
    object_id: str,
    summary: str,
    delta: list[dict[str, Any]],
    audit_event_id: int | None,
) -> ChangeNotice:
    notice = ChangeNotice(
        cpse_id=cpse_id,
        kind=kind,
        object_type=object_type,
        object_id=object_id,
        summary=summary,
        delta=delta,
        audit_event_id=audit_event_id,
    )
    session.add(notice)
    session.flush()
    return notice


def scope_cpse(session: Session, user: AppUser, code: str | None) -> Cpse:
    """MAKER / CHECKER read their own CPSE's inbox; ADMIN and INTEGRATOR name the CPSE."""
    if user.role in ("MAKER", "CHECKER"):
        own = session.get(Cpse, user.cpse_id) if user.cpse_id else None
        if own is None or (code and code != own.code):
            raise Forbidden("You can read only your own CPSE's notices.")
        return own
    if not code:
        raise NotFound("Say which CPSE's notices to show (?cpse=).")
    cpse = session.scalar(select(Cpse).where(Cpse.code == code))
    if cpse is None:
        raise NotFound(f"No CPSE with code {code}.")
    return cpse


def list_for(session: Session, cpse: Cpse) -> list[dict[str, Any]]:
    rows = session.execute(
        text("""
            SELECT n.id, n.kind, n.object_type, n.object_id, n.summary, n.delta, n.created_at,
                   n.acknowledged_at, u.username
            FROM change_notice n LEFT JOIN app_user u ON u.id = n.acknowledged_by
            WHERE n.cpse_id = :c ORDER BY n.created_at DESC
            """),
        {"c": cpse.id},
    ).all()
    return [
        {"id": r[0], "cpse": cpse.code, "kind": r[1], "object_type": r[2], "object_id": r[3],
         "summary": r[4], "delta": r[5], "created_at": r[6], "acknowledged_at": r[7],
         "acknowledged_by": r[8]}
        for r in rows
    ]  # fmt: skip


def get(session: Session, user: AppUser, notice_id: uuid.UUID) -> ChangeNotice:
    notice = session.get(ChangeNotice, notice_id)
    if notice is None:
        raise NotFound("No such notice.")
    if user.role in ("MAKER", "CHECKER") and user.cpse_id != notice.cpse_id:
        raise Forbidden("This notice belongs to another CPSE.")
    return notice


def acknowledge(session: Session, user: AppUser, notice_id: uuid.UUID) -> ChangeNotice:
    notice = get(session, user, notice_id)
    if notice.acknowledged_at is None:  # idempotent: a second acknowledge changes nothing
        notice.acknowledged_by = user.id
        notice.acknowledged_at = datetime.now(UTC)
        audit.record(
            session,
            actor_id=user.id,
            action="CHANGE_NOTICE_ACKNOWLEDGED",
            object_type="change_notice",
            object_id=str(notice.id),
            after={"kind": notice.kind, "object_id": notice.object_id},
        )
    return notice
