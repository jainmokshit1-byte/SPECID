"""TR-SEC-01/02, TR-API-02/08: password rules, bcrypt cost, tokens, login rate limit."""

import uuid

import pytest

from app.security import auth
from app.security.ratelimit import TokenBucket

SECRET = "unit-test-secret-0123456789abcdef01234"


def test_bcrypt_cost_12_and_check() -> None:
    h = auth.hash_password("correct-horse-1")
    assert h.startswith("$2b$12$")
    assert auth.check_password("correct-horse-1", h)
    assert not auth.check_password("correct-horse-2", h)
    assert not auth.check_password("correct-horse-1", None)  # unknown user


@pytest.mark.parametrize(
    ("pw", "ok"), [("123456789", False), ("1234567890", True), ("é" * 37, False), ("x" * 72, True)]
)
def test_password_rules(pw: str, ok: bool) -> None:
    assert (auth.password_problem(pw) is None) is ok


def test_token_round_trip_and_rejections() -> None:
    uid, cpse = uuid.uuid4(), uuid.uuid4()
    token, exp = auth.create_token(SECRET, uid, "CHECKER", cpse, minutes=480)
    claims = auth.decode_token(SECRET, token)
    assert claims is not None
    assert (claims.user_id, claims.role, claims.cpse_id) == (uid, "CHECKER", cpse)
    assert claims.expires_at == exp.replace(microsecond=0)
    assert auth.decode_token("y" * 40, token) is None
    expired, _ = auth.create_token(SECRET, uid, "CHECKER", None, minutes=-1)
    assert auth.decode_token(SECRET, expired) is None
    assert auth.decode_token(SECRET, "garbage") is None


def test_token_bucket_five_per_minute_then_refills() -> None:
    now = [0.0]
    bucket = TokenBucket(5, 60, clock=lambda: now[0])
    assert all(bucket.allow("meera") for _ in range(5))
    assert not bucket.allow("meera")
    assert bucket.allow("arjun")  # per username
    now[0] = 11.0  # 5 tokens / 60 s -> one token after 12 s
    assert not bucket.allow("meera")
    now[0] = 12.5  # 1.5 s later: 0.92 + 0.13 tokens
    assert bucket.allow("meera")
    assert not bucket.allow("meera")
    now[0] = 1000.0
    assert sum(bucket.allow("meera") for _ in range(10)) == 5  # never more than capacity
