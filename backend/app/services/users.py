"""Login, users and passwords (PRD FR-1301, API-01/02; DECISIONS.md DEC-14, DEC-15).

Every state change writes its audit event in the caller's transaction (TR-ARC-11); the router
commits. The one exception is a failed login: its `LOGIN_FAILED` event is committed here before
the 401 is raised, because the request itself fails.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AppUser, Cpse
from app.security import auth
from app.security.permissions import CPSE_SCOPED_ROLES, ROLES
from app.security.ratelimit import login_limiter
from app.services import audit
from app.services.errors import Conflict, Invalid, NotFound, RateLimited, Unauthorized

WRONG_LOGIN = "Wrong username or password"


@dataclass(frozen=True)
class LoginResult:
    user: AppUser
    access_token: str
    expires_at: datetime


def _fail(session: Session, username: str, user: AppUser | None, reason: str) -> Unauthorized:
    audit.record(
        session,
        actor_id=user.id if user else None,
        action="LOGIN_FAILED",
        object_type="app_user",
        object_id=str(user.id) if user else "unknown",
        after={"username": username, "reason": reason},
    )
    session.commit()
    return Unauthorized(WRONG_LOGIN, title=WRONG_LOGIN)


def login(
    session: Session, username: str, password: str, secret: str, expire_min: int
) -> LoginResult:
    """API-01. Same message for an unknown user, a wrong password and a disabled account."""
    username = username.strip()
    if not login_limiter.allow(username.lower()):
        raise RateLimited("Too many attempts, wait 1 minute")
    user = session.scalars(
        select(AppUser).where(func.lower(AppUser.username) == username.lower())
    ).one_or_none()
    if not auth.check_password(password, user.password_hash if user else None):
        raise _fail(session, username, user, "unknown user" if user is None else "wrong password")
    assert user is not None
    if not user.is_active:
        raise _fail(session, username, user, "disabled")
    user.last_login_at = datetime.now(UTC)
    audit.record(
        session,
        actor_id=user.id,
        action="LOGIN_SUCCEEDED",
        object_type="app_user",
        object_id=str(user.id),
        after={"username": user.username, "role": user.role},
    )
    token, exp = auth.create_token(secret, user.id, user.role, user.cpse_id, expire_min)
    return LoginResult(user=user, access_token=token, expires_at=exp)


def active_user(session: Session, user_id: uuid.UUID) -> AppUser | None:
    """The signed-in user, or None when unknown or disabled (tokens of disabled users stop)."""
    user = session.get(AppUser, user_id)
    return user if user is not None and user.is_active else None


def cpse_code(session: Session, cpse_id: uuid.UUID | None) -> str | None:
    if cpse_id is None:
        return None
    return session.scalar(select(Cpse.code).where(Cpse.id == cpse_id))


def list_users(session: Session) -> list[AppUser]:
    return list(session.scalars(select(AppUser).order_by(AppUser.username)).all())


def _check_password(password: str) -> None:
    problem = auth.password_problem(password)
    if problem:
        raise Invalid(problem, title="Password not accepted")


def _get(session: Session, user_id: uuid.UUID) -> AppUser:
    user = session.get(AppUser, user_id)
    if user is None:
        raise NotFound("No user with this id.", title="User not found")
    return user


def _public(user: AppUser) -> dict[str, Any]:
    return {
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "cpse_id": str(user.cpse_id) if user.cpse_id else None,
    }


def create_user(
    session: Session,
    actor: AppUser,
    *,
    username: str,
    display_name: str | None,
    role: str,
    cpse_id: uuid.UUID | None,
    temporary_password: str,
) -> AppUser:
    """S16 "Add user": the new user must change the temporary password at first login."""
    username = username.strip()
    if not username:
        raise Invalid("Enter a username.", title="Username missing")
    if role not in ROLES:
        raise Invalid(f"Role must be one of {', '.join(ROLES)}.", title="Unknown role")
    if role in CPSE_SCOPED_ROLES and cpse_id is None:
        raise Invalid(f"A {role} acts for one CPSE; choose it.", title="CPSE missing")
    if cpse_id is not None and session.get(Cpse, cpse_id) is None:
        raise Invalid("No CPSE with this id.", title="Unknown CPSE")
    _check_password(temporary_password)
    if session.scalar(select(AppUser.id).where(func.lower(AppUser.username) == username.lower())):
        raise Conflict(f"The username {username!r} is taken.", title="Username taken")
    user = AppUser(
        username=username,
        display_name=display_name or None,
        password_hash=auth.hash_password(temporary_password),
        role=role,
        cpse_id=cpse_id,
        is_active=True,
        must_change_password=True,
    )
    session.add(user)
    try:
        session.flush()
    except IntegrityError as exc:  # concurrent create with the same name
        raise Conflict(f"The username {username!r} is taken.", title="Username taken") from exc
    audit.record(
        session,
        actor_id=actor.id,
        action="USER_CREATED",
        object_type="app_user",
        object_id=str(user.id),
        after=_public(user),
    )
    return user


def reset_password(
    session: Session, actor: AppUser, user_id: uuid.UUID, temporary_password: str
) -> AppUser:
    """S16 "Reset password" (ADMIN): sets a temporary password to change at next login."""
    user = _get(session, user_id)
    _check_password(temporary_password)
    user.password_hash = auth.hash_password(temporary_password)
    user.must_change_password = True
    audit.record(
        session,
        actor_id=actor.id,
        action="PASSWORD_RESET",
        object_type="app_user",
        object_id=str(user.id),
        after={"username": user.username, "must_change_password": True},
    )
    return user


def disable_user(session: Session, actor: AppUser, user_id: uuid.UUID) -> AppUser:
    """S16 "Disable": the user can no longer sign in and their tokens stop working."""
    user = _get(session, user_id)
    if user.id == actor.id:
        raise Conflict("An admin cannot disable their own account.", title="Cannot disable self")
    if not user.is_active:
        raise Conflict("This user is already disabled.", title="Already disabled")
    user.is_active = False
    audit.record(
        session,
        actor_id=actor.id,
        action="USER_DISABLED",
        object_type="app_user",
        object_id=str(user.id),
        before={"is_active": True},
        after={"username": user.username, "is_active": False},
    )
    return user


def change_password(session: Session, user: AppUser, current: str, new: str) -> AppUser:
    """User menu "Change password" and the forced first-login change (DEC-15: PASSWORD_CHANGED)."""
    if not auth.check_password(current, user.password_hash):
        raise Invalid("The current password is wrong.", title="Current password is wrong")
    _check_password(new)
    if new == current:
        raise Invalid("Choose a password different from the current one.", title="Same password")
    was_forced = user.must_change_password
    user.password_hash = auth.hash_password(new)
    user.must_change_password = False
    audit.record(
        session,
        actor_id=user.id,
        action="PASSWORD_CHANGED",
        object_type="app_user",
        object_id=str(user.id),
        after={"username": user.username, "was_forced": was_forced},
    )
    return user
