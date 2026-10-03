"""Passwords and tokens (TRD TR-SEC-01, TR-SEC-02, TR-API-02; PRD FR-1301).

bcrypt cost 12, minimum length 10; JWT HS256 with `exp` 8 h and claims `sub`, `role`, `cpse_id`.
The JWT secret is checked at startup by `Settings` (≥ 32 characters).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

BCRYPT_COST = 12
MIN_PASSWORD_LEN = 10
MAX_PASSWORD_BYTES = 72  # bcrypt ignores (5.x: rejects) anything longer
ALGORITHM = "HS256"

# Compared against when the username is unknown, so both failures take the same time.
_DUMMY_HASH = bcrypt.hashpw(b"not-a-real-password", bcrypt.gensalt(BCRYPT_COST))


def password_problem(password: str) -> str | None:
    """Why a new password is not acceptable, or None."""
    if len(password) < MIN_PASSWORD_LEN:
        return f"Use at least {MIN_PASSWORD_LEN} characters."
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return f"Use at most {MAX_PASSWORD_BYTES} bytes."
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(BCRYPT_COST)).decode()


def check_password(password: str, password_hash: str | None) -> bool:
    """Constant-time check; with no hash (unknown user) still spends one bcrypt round."""
    candidate = password.encode("utf-8")
    if len(candidate) > MAX_PASSWORD_BYTES:
        candidate = candidate[:MAX_PASSWORD_BYTES]
    target = password_hash.encode() if password_hash else _DUMMY_HASH
    try:
        ok = bcrypt.checkpw(candidate, target)
    except ValueError:
        return False
    return ok and password_hash is not None


@dataclass(frozen=True)
class TokenClaims:
    user_id: uuid.UUID
    role: str
    cpse_id: uuid.UUID | None
    expires_at: datetime


def create_token(
    secret: str, user_id: uuid.UUID, role: str, cpse_id: uuid.UUID | None, minutes: int
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "cpse_id": str(cpse_id) if cpse_id else None,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM), exp


def decode_token(secret: str, token: str) -> TokenClaims | None:
    """Claims of a valid, unexpired token signed with `secret`; None otherwise."""
    try:
        p = jwt.decode(
            token, secret, algorithms=[ALGORITHM], options={"require": ["exp", "sub", "role"]}
        )
        return TokenClaims(
            user_id=uuid.UUID(p["sub"]),
            role=str(p["role"]),
            cpse_id=uuid.UUID(p["cpse_id"]) if p.get("cpse_id") else None,
            expires_at=datetime.fromtimestamp(p["exp"], UTC),
        )
    except (jwt.InvalidTokenError, ValueError, KeyError):
        return None
