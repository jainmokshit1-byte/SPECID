"""API-23 `GET /audit` (filters, cursor pagination) and `GET /audit/verify` (S12). ADMIN, AUDITOR.

`verify` recomputes the hash chain and logs `AUDIT_VERIFIED` (Backend Schema 9.2).
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.models import AppUser
from app.db.session import get_session
from app.schemas.audit import AuditEventOut, AuditPage, VerifyOut
from app.security.permissions import Action
from app.security.rbac import require
from app.services import audit

router = APIRouter(prefix="/audit", tags=["audit"])
viewer = require(Action.VIEW_AUDIT)


@router.get("", response_model=AuditPage)
def list_audit(
    actor: str | None = Query(default=None, description="username"),
    action: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=audit.MAX_LIMIT),
    cursor: str | None = None,
    _: AppUser = Depends(viewer),
    session: Session = Depends(get_session),
) -> AuditPage:
    filters = audit.AuditFilters(
        actor=actor or None,
        action=action or None,
        object_type=object_type or None,
        object_id=object_id or None,
        since=since,
        until=until,
    )
    rows, nxt = audit.list_events(session, filters, limit, cursor)
    return AuditPage(
        items=[
            AuditEventOut(
                id=e.id,
                ts=e.ts,
                actor_id=e.actor_id,
                actor=name,
                action=e.action,
                object_type=e.object_type,
                object_id=e.object_id,
                before=e.before,
                after=e.after,
                prev_hash=e.prev_hash,
                hash=e.hash,
            )
            for e, name in rows
        ],
        next_cursor=nxt,
    )


@router.get("/verify", response_model=VerifyOut)
def verify(user: AppUser = Depends(viewer), session: Session = Depends(get_session)) -> VerifyOut:
    result = audit.verify_and_record(session, user.id)
    session.commit()
    return VerifyOut(ok=result.ok, events=result.events, first_bad_id=result.first_bad_id)
