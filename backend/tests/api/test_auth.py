"""API-01/02 and DEC-14/15: login, /me, passwords, user administration (FR-1301, TR-SEC-01/02,
TR-API-02/08). Every state change leaves its audit event (Backend Schema 9.2)."""

import uuid

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.security.auth import create_token
from app.services import audit
from app.settings import get_settings
from tests.api.conftest import DEMO, PASSWORD, audit_actions, login

API = "/api/v1"


@pytest.mark.parametrize("username", list(DEMO))
def test_each_demo_user_logs_in_with_role_and_claims(
    client: TestClient, ids: dict[str, uuid.UUID], username: str
) -> None:
    r = client.post(f"{API}/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    role, cpse = DEMO[username]
    assert body["role"] == role and body["token_type"] == "bearer"
    assert body["must_change_password"] is False
    claims = jwt.decode(body["access_token"], get_settings().jwt_secret, algorithms=["HS256"])
    assert claims["sub"] == str(ids[username]) and claims["role"] == role
    assert (claims["cpse_id"] is None) == (cpse is None)
    assert 8 * 3600 - 5 <= claims["exp"] - claims["iat"] <= 8 * 3600  # TR-API-02: 8 h
    me = client.get(f"{API}/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["username"] == username and me.json()["cpse_code"] == cpse
    assert "password_hash" not in me.text
    assert audit_actions() == ["LOGIN_SUCCEEDED"]


def test_login_updates_last_login_and_audits(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    login(client, "meera")
    with get_engine().connect() as c:
        last = c.execute(
            text("SELECT last_login_at FROM app_user WHERE username='meera'")
        ).scalar_one()
        ev = c.execute(text("SELECT actor_id, object_id, after FROM audit_event")).one()
    assert last is not None
    assert ev.actor_id == ids["meera"] and ev.object_id == str(ids["meera"])
    assert ev.after == {"username": "meera", "role": "MAKER"}


@pytest.mark.parametrize(
    ("username", "password", "reason"),
    [("meera", "wrong-password-x", "wrong password"), ("nobody", PASSWORD, "unknown user")],
)
def test_wrong_login_is_401_with_one_message_and_audited(
    client: TestClient, ids: dict[str, uuid.UUID], username: str, password: str, reason: str
) -> None:
    r = client.post(f"{API}/auth/login", json={"username": username, "password": password})
    assert r.status_code == 401
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["title"] == "Wrong username or password"
    with get_engine().connect() as c:
        ev = c.execute(text("SELECT action, after FROM audit_event")).one()
    assert ev.action == "LOGIN_FAILED"
    assert ev.after == {"username": username, "reason": reason}
    assert password not in str(ev.after)


def test_disabled_user_cannot_log_in(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    with get_engine().begin() as c:
        c.execute(text("UPDATE app_user SET is_active=false WHERE username='meera'"))
    r = client.post(f"{API}/auth/login", json={"username": "meera", "password": PASSWORD})
    assert r.status_code == 401 and r.json()["title"] == "Wrong username or password"


def test_sixth_login_attempt_in_a_minute_is_429(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    for _ in range(5):
        client.post(f"{API}/auth/login", json={"username": "meera", "password": "wrong-pass-1"})
    r = client.post(f"{API}/auth/login", json={"username": "MEERA", "password": PASSWORD})
    assert r.status_code == 429 and r.headers["retry-after"] == "60"
    assert r.json()["detail"] == "Too many attempts, wait 1 minute"
    # another username is not affected
    assert (
        client.post(
            f"{API}/auth/login", json={"username": "arjun", "password": PASSWORD}
        ).status_code
        == 200
    )


@pytest.mark.parametrize("header", [None, "Bearer", "Basic abc", "Bearer not-a-jwt"])
def test_me_without_valid_token_is_401(
    client: TestClient, ids: dict[str, uuid.UUID], header: str | None
) -> None:
    r = client.get(f"{API}/me", headers={"Authorization": header} if header else {})
    assert r.status_code == 401 and r.headers["www-authenticate"] == "Bearer"


def test_expired_wrong_secret_and_disabled_tokens_are_401(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    secret = get_settings().jwt_secret
    expired, _ = create_token(secret, ids["meera"], "MAKER", None, minutes=-1)
    forged, _ = create_token("x" * 40, ids["meera"], "MAKER", None, minutes=60)
    for token in (expired, forged):
        assert (
            client.get(f"{API}/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
        )
    headers = login(client, "meera")
    with get_engine().begin() as c:
        c.execute(text("UPDATE app_user SET is_active=false WHERE username='meera'"))
    assert client.get(f"{API}/me", headers=headers).status_code == 401


def test_token_role_claim_is_not_trusted(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    """A token claiming ADMIN for a maker still acts as the stored role."""
    token, _ = create_token(get_settings().jwt_secret, ids["meera"], "ADMIN", None, minutes=60)
    r = client.get(f"{API}/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


# ----- DEC-15: self-service password change -----
def test_change_password_audits_password_changed(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    h = login(client, "meera")
    new = "a-brand-new-password"
    r = client.post(
        f"{API}/me/password", headers=h, json={"current_password": PASSWORD, "new_password": new}
    )
    assert r.status_code == 204
    assert audit_actions() == ["LOGIN_SUCCEEDED", "PASSWORD_CHANGED"]
    login(client, "meera", new)
    with get_engine().connect() as c:
        after = c.execute(
            text("SELECT after FROM audit_event WHERE action='PASSWORD_CHANGED'")
        ).scalar_one()
    assert after == {"username": "meera", "was_forced": False}


@pytest.mark.parametrize(
    ("current", "new", "title"),
    [
        ("wrong-current-pw", "a-brand-new-password", "Current password is wrong"),
        (PASSWORD, "short", "Password not accepted"),
        (PASSWORD, PASSWORD, "Same password"),
    ],
)
def test_change_password_rejections(
    client: TestClient, ids: dict[str, uuid.UUID], current: str, new: str, title: str
) -> None:
    h = login(client, "meera")
    r = client.post(
        f"{API}/me/password", headers=h, json={"current_password": current, "new_password": new}
    )
    assert r.status_code == 400 and r.json()["title"] == title
    assert audit_actions() == ["LOGIN_SUCCEEDED"]


# ----- DEC-14: user administration -----
def test_admin_lists_users_without_hashes(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    r = client.get(f"{API}/users", headers=login(client, "admin"))
    assert r.status_code == 200
    body = r.json()
    assert [u["username"] for u in body["items"]] == sorted(DEMO)
    assert [c["code"] for c in body["cpses"]] == ["CPSE-A", "CPSE-B", "CPSE-C"]
    assert "password_hash" not in r.text and "vendor_salt" not in r.text
    meera = next(u for u in body["items"] if u["username"] == "meera")
    assert meera["cpse_code"] == "CPSE-A" and meera["role"] == "MAKER"


def test_admin_creates_user_who_must_change_password(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    h = login(client, "admin")
    cpse_b = client.get(f"{API}/users", headers=h).json()["cpses"][1]["id"]
    r = client.post(
        f"{API}/users",
        headers=h,
        json={
            "username": "ravi",
            "display_name": "Ravi",
            "role": "CHECKER",
            "cpse_id": cpse_b,
            "temporary_password": "temporary-pass-1",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["must_change_password"] is True and r.json()["cpse_code"] == "CPSE-B"
    lr = client.post(f"{API}/auth/login", json={"username": "ravi", "password": "temporary-pass-1"})
    assert lr.json()["must_change_password"] is True
    assert audit_actions() == ["LOGIN_SUCCEEDED", "USER_CREATED", "LOGIN_SUCCEEDED"]
    with get_engine().connect() as c:
        ev = c.execute(
            text("SELECT actor_id, after FROM audit_event WHERE action='USER_CREATED'")
        ).one()
    assert ev.actor_id == ids["admin"]
    assert ev.after == {
        "username": "ravi",
        "display_name": "Ravi",
        "role": "CHECKER",
        "cpse_id": cpse_b,
    }


@pytest.mark.parametrize(
    ("patch", "status", "title"),
    [
        ({"username": "Meera"}, 409, "Username taken"),
        ({"role": "SUPERUSER"}, 400, "Unknown role"),
        ({"role": "MAKER", "cpse_id": None}, 400, "CPSE missing"),
        ({"cpse_id": str(uuid.uuid4())}, 400, "Unknown CPSE"),
        ({"temporary_password": "short"}, 400, "Password not accepted"),
    ],
)
def test_create_user_rejections(
    client: TestClient, ids: dict[str, uuid.UUID], patch: dict, status: int, title: str
) -> None:
    body = {"username": "new1", "role": "AUDITOR", "temporary_password": "temporary-pass-1"}
    body.update(patch)
    r = client.post(f"{API}/users", headers=login(client, "admin"), json=body)
    assert (r.status_code, r.json()["title"]) == (status, title)
    assert audit_actions() == ["LOGIN_SUCCEEDED"]


def test_admin_resets_password(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    h = login(client, "admin")
    r = client.post(
        f"{API}/users/{ids['meera']}/reset-password",
        headers=h,
        json={"temporary_password": "temporary-pass-2"},
    )
    assert r.status_code == 200 and r.json()["must_change_password"] is True
    assert (
        client.post(
            f"{API}/auth/login", json={"username": "meera", "password": PASSWORD}
        ).status_code
        == 401
    )
    assert (
        client.post(
            f"{API}/auth/login", json={"username": "meera", "password": "temporary-pass-2"}
        ).json()["must_change_password"]
        is True
    )
    assert audit_actions() == [
        "LOGIN_SUCCEEDED",
        "PASSWORD_RESET",
        "LOGIN_FAILED",
        "LOGIN_SUCCEEDED",
    ]
    nf = client.post(
        f"{API}/users/{uuid.uuid4()}/reset-password",
        headers=h,
        json={"temporary_password": "temporary-pass-2"},
    )
    assert nf.status_code == 404


def test_admin_disables_user_and_not_self(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    h = login(client, "admin")
    meera = login(client, "meera")
    r = client.post(f"{API}/users/{ids['meera']}/disable", headers=h)
    assert r.status_code == 200 and r.json()["is_active"] is False
    assert client.get(f"{API}/me", headers=meera).status_code == 401
    again = client.post(f"{API}/users/{ids['meera']}/disable", headers=h)
    assert (again.status_code, again.json()["title"]) == (409, "Already disabled")
    me = client.post(f"{API}/users/{ids['admin']}/disable", headers=h)
    assert (me.status_code, me.json()["title"]) == (409, "Cannot disable self")
    assert audit_actions().count("USER_DISABLED") == 1


def test_all_auth_events_keep_the_chain_intact(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    login(client, "admin")
    client.post(f"{API}/auth/login", json={"username": "meera", "password": "nope-nope-1"})
    login(client, "meera")

    with Session(get_engine()) as s:
        result = audit.verify(s)
    assert result.ok and result.events == 3
