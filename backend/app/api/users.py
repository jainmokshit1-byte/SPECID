"""S16 user administration (DEC-14): list, create, reset password, disable. ADMIN only."""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AppUser, Cpse
from app.db.session import get_session
from app.schemas.auth import CpseOut, PasswordReset, UserCreate, UserOut
from app.security.rbac import require_role
from app.services import users

router = APIRouter(prefix="/users", tags=["users"])
admin = require_role("ADMIN")


class UserList(BaseModel):
    items: list[UserOut]
    cpses: list[CpseOut]  # choices for the "Add user" modal


def _out(user: AppUser, codes: dict[uuid.UUID, str]) -> UserOut:
    out = UserOut.model_validate(user)
    out.cpse_code = codes.get(user.cpse_id) if user.cpse_id else None
    return out


def _codes(session: Session) -> dict[uuid.UUID, str]:
    return {c.id: c.code for c in session.scalars(select(Cpse)).all()}


@router.get("", response_model=UserList)
def list_users(_: AppUser = Depends(admin), session: Session = Depends(get_session)) -> UserList:
    cpses = list(session.scalars(select(Cpse).order_by(Cpse.code)).all())
    codes = {c.id: c.code for c in cpses}
    return UserList(
        items=[_out(u, codes) for u in users.list_users(session)],
        cpses=[CpseOut.model_validate(c) for c in cpses],
    )


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: UserCreate, actor: AppUser = Depends(admin), session: Session = Depends(get_session)
) -> UserOut:
    user = users.create_user(
        session,
        actor,
        username=body.username,
        display_name=body.display_name,
        role=body.role,
        cpse_id=body.cpse_id,
        temporary_password=body.temporary_password,
    )
    session.commit()
    return _out(user, _codes(session))


@router.post("/{user_id}/reset-password", response_model=UserOut)
def reset_password(
    user_id: uuid.UUID,
    body: PasswordReset,
    actor: AppUser = Depends(admin),
    session: Session = Depends(get_session),
) -> UserOut:
    user = users.reset_password(session, actor, user_id, body.temporary_password)
    session.commit()
    return _out(user, _codes(session))


@router.post("/{user_id}/disable", response_model=UserOut)
def disable_user(
    user_id: uuid.UUID, actor: AppUser = Depends(admin), session: Session = Depends(get_session)
) -> UserOut:
    user = users.disable_user(session, actor, user_id)
    session.commit()
    return _out(user, _codes(session))
