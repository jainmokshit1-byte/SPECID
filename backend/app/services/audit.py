"""Hash-chained, append-only audit log (TRD TR-ALG-09, TR-MOD-29; PRD FR-1302).

`record()` runs in the caller's transaction (TR-ARC-11): it takes advisory lock 4242 to
serialise appends, reads the last hash and inserts the new event with
`hash = sha256((prev_hash or "GENESIS") + canonical(event))`.
`verify()` streams the log by id in chunks of 10,000 and reports the first event whose link or
hash does not recompute.

`ts` is set here (UTC, microseconds) and canonicalised as ISO 8601 UTC, so the hash recomputes
whatever the database session time zone is.
"""

import base64
import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import AppUser, AuditEvent
from app.schemas.jsonb import AuditDiff
from app.services.errors import Invalid

LOCK_KEY = 4242
GENESIS = "GENESIS"
VERIFY_CHUNK = 10_000


def _jsonable(diff: dict[str, Any] | None) -> dict[str, Any] | None:
    """Validate (no secrets) and round-trip through JSON, so the stored and hashed forms match."""
    if diff is None:
        return None
    AuditDiff.model_validate(diff)
    result: dict[str, Any] = json.loads(json.dumps(diff, default=str, ensure_ascii=False))
    return result


def canonical(
    *,
    actor_id: uuid.UUID | str | None,
    action: str,
    object_type: str,
    object_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    ts: datetime,
) -> str:
    return json.dumps(
        {
            "actor_id": str(actor_id) if actor_id is not None else None,
            "action": action,
            "object_type": object_type,
            "object_id": object_id,
            "before": before,
            "after": after,
            "ts": ts.astimezone(UTC).isoformat(timespec="microseconds"),
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )


def chain_hash(prev_hash: str | None, canonical_json: str) -> str:
    return hashlib.sha256(((prev_hash or GENESIS) + canonical_json).encode("utf-8")).hexdigest()


def record(
    session: Session,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    object_type: str,
    object_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append one event in the caller's transaction and return it (with its id)."""
    before, after = _jsonable(before), _jsonable(after)
    session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": LOCK_KEY})
    prev = session.execute(
        select(AuditEvent.hash).order_by(AuditEvent.id.desc()).limit(1)
    ).scalar_one_or_none()
    ts = datetime.now(UTC)
    digest = chain_hash(
        prev,
        canonical(
            actor_id=actor_id,
            action=action,
            object_type=object_type,
            object_id=object_id,
            before=before,
            after=after,
            ts=ts,
        ),
    )
    event = AuditEvent(
        ts=ts,
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=before,
        after=after,
        prev_hash=prev,
        hash=digest,
    )
    session.add(event)
    session.flush()
    return event


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    events: int
    first_bad_id: int | None


_VERIFY_COLS = (
    AuditEvent.id,
    AuditEvent.ts,
    AuditEvent.actor_id,
    AuditEvent.action,
    AuditEvent.object_type,
    AuditEvent.object_id,
    AuditEvent.before,
    AuditEvent.after,
    AuditEvent.prev_hash,
    AuditEvent.hash,
)


def verify(session: Session) -> VerifyResult:
    """Recompute the chain; report the first event whose link or hash does not match."""
    prev: str | None = None
    last_id = 0
    count = 0
    while True:
        rows = session.execute(
            select(*_VERIFY_COLS)
            .where(AuditEvent.id > last_id)
            .order_by(AuditEvent.id)
            .limit(VERIFY_CHUNK)
        ).all()
        if not rows:
            return VerifyResult(ok=True, events=count, first_bad_id=None)
        for e in rows:
            expected = chain_hash(
                prev,
                canonical(
                    actor_id=e.actor_id,
                    action=e.action,
                    object_type=e.object_type,
                    object_id=e.object_id,
                    before=e.before,
                    after=e.after,
                    ts=e.ts,
                ),
            )
            if e.prev_hash != prev or e.hash != expected:
                return VerifyResult(ok=False, events=count, first_bad_id=e.id)
            prev, last_id, count = e.hash, e.id, count + 1


def verify_and_record(session: Session, actor_id: uuid.UUID) -> VerifyResult:
    """API-23 `GET /audit/verify`: verify, then log `AUDIT_VERIFIED` with the result."""
    result = verify(session)
    record(
        session,
        actor_id=actor_id,
        action="AUDIT_VERIFIED",
        object_type="audit_event",
        object_id="chain",
        after={"ok": result.ok, "events": result.events, "first_bad_id": result.first_bad_id},
    )
    return result


# ----- listing (S12) -----
MAX_LIMIT = 500


@dataclass(frozen=True)
class AuditFilters:
    actor_id: uuid.UUID | None = None
    actor: str | None = None  # username
    action: str | None = None
    object_type: str | None = None
    object_id: str | None = None
    since: datetime | None = None
    until: datetime | None = None


def _decode_cursor(cursor: str) -> int:
    try:
        return int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except (ValueError, UnicodeDecodeError) as exc:
        raise Invalid("The cursor is not valid.", title="Invalid cursor") from exc


def encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(str(last_id).encode()).decode()


def list_events(
    session: Session, filters: AuditFilters, limit: int = 50, cursor: str | None = None
) -> tuple[list[tuple[AuditEvent, str | None]], str | None]:
    """Newest first, keyset-paginated by id (TR-API-04); each event with its actor's username."""
    limit = max(1, min(limit, MAX_LIMIT))
    q = (
        select(AuditEvent, AppUser.username)
        .outerjoin(AppUser, AppUser.id == AuditEvent.actor_id)
        .order_by(AuditEvent.id.desc())
        .limit(limit + 1)
    )
    if cursor:
        q = q.where(AuditEvent.id < _decode_cursor(cursor))
    if filters.actor_id:
        q = q.where(AuditEvent.actor_id == filters.actor_id)
    if filters.actor:
        q = q.where(AppUser.username == filters.actor)
    if filters.action:
        q = q.where(AuditEvent.action == filters.action)
    if filters.object_type:
        q = q.where(AuditEvent.object_type == filters.object_type)
    if filters.object_id:
        q = q.where(AuditEvent.object_id == filters.object_id)
    if filters.since:
        q = q.where(AuditEvent.ts >= filters.since)
    if filters.until:
        q = q.where(AuditEvent.ts < filters.until)
    rows = [(e, name) for e, name in session.execute(q).all()]
    nxt = encode_cursor(rows[limit - 1][0].id) if len(rows) > limit else None
    return rows[:limit], nxt
