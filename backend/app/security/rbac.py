"""Role dependency (TRD TR-SEC-03): every router declares who may call it.

`current_user` reads `Authorization: Bearer <JWT>`, checks signature and expiry, and loads the
user from the database, so a disabled user's token stops working at once and the role is always
the stored one. `require_role(*roles)` returns 403 for any other role.
"""

from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.models import AppUser
from app.db.session import get_session
from app.security.auth import decode_token
from app.services import users
from app.services.errors import Forbidden, Unauthorized
from app.settings import Settings, get_settings


def current_user(
    request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AppUser:
    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise Unauthorized("Sign in to continue.")
    claims = decode_token(settings.jwt_secret, token.strip())
    if claims is None:
        raise Unauthorized("Your session has expired or is not valid. Sign in again.")
    user = users.active_user(session, claims.user_id)
    if user is None:
        raise Unauthorized("This account is not active. Sign in again.")
    return user


def require_role(*roles: str) -> Callable[..., AppUser]:
    allowed = frozenset(roles)

    def dependency(user: AppUser = Depends(current_user)) -> AppUser:
        if user.role not in allowed:
            raise Forbidden(f"The {user.role} role cannot do this.", title="No access")
        return user

    dependency.allowed_roles = allowed  # type: ignore[attr-defined]  # read by the route guard test
    return dependency
