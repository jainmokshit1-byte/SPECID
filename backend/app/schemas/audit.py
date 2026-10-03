"""Responses of API-23 `GET /audit`, `GET /audit/verify`."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditEventOut(BaseModel):
    id: int
    ts: datetime
    actor_id: uuid.UUID | None
    actor: str | None  # username
    action: str
    object_type: str
    object_id: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    prev_hash: str | None
    hash: str


class AuditPage(BaseModel):
    items: list[AuditEventOut]
    next_cursor: str | None


class VerifyOut(BaseModel):
    ok: bool
    events: int
    first_bad_id: int | None
