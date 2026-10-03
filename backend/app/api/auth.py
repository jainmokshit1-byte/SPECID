"""API-01 `POST /auth/login`, API-02 `GET /me`, `POST /me/password` (DEC-14)."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.db.models import AppUser
from app.db.session import get_session
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LoginResponse, Me
from app.security.rbac import current_user
from app.services import users
from app.settings import Settings, get_settings

router = APIRouter(tags=["auth"])


def _me(session: Session, user: AppUser) -> Me:
    return Me(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        cpse_id=user.cpse_id,
        cpse_code=users.cpse_code(session, user.cpse_id),
        must_change_password=user.must_change_password,
    )


@router.post("/auth/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    result = users.login(
        session, body.username, body.password, settings.jwt_secret, settings.jwt_expire_min
    )
    session.commit()
    return LoginResponse(
        access_token=result.access_token,
        expires_at=result.expires_at,
        role=result.user.role,
        must_change_password=result.user.must_change_password,
    )


@router.get("/me", response_model=Me)
def me(user: AppUser = Depends(current_user), session: Session = Depends(get_session)) -> Me:
    return _me(session, user)


@router.post("/me/password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    user: AppUser = Depends(current_user),
    session: Session = Depends(get_session),
) -> Response:
    users.change_password(session, user, body.current_password, body.new_password)
    session.commit()
    return Response(status_code=204)
