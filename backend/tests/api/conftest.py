"""API test fixtures: the real app against the throwaway test database (never the stack's DB).

Each test starts with three synthetic CPSEs, the six demo users of Backend Schema section 12
(password `PASSWORD`, no forced change) and an empty audit log.
"""

import uuid
from collections.abc import Iterator
from functools import lru_cache

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.db.session import get_engine
from app.main import app
from app.security.auth import hash_password
from app.security.ratelimit import login_limiter

PASSWORD = "test-only-password-1"
DEMO = {  # username -> (role, cpse code)
    "meera": ("MAKER", "CPSE-A"),
    "arjun": ("CHECKER", "CPSE-B"),
    "kavya": ("CHECKER", "CPSE-C"),
    "admin": ("ADMIN", None),
    "auditor": ("AUDITOR", None),
    "erp": ("INTEGRATOR", None),
}


@lru_cache
def _hash() -> str:
    return hash_password(PASSWORD)


def reset_db(eng: Engine) -> dict[str, uuid.UUID]:
    """Empty audit log, CPSE-A/B/C and the demo users; returns username -> id."""
    with eng.begin() as c:
        c.exec_driver_sql("ALTER TABLE audit_event DISABLE TRIGGER USER")
        c.exec_driver_sql("TRUNCATE audit_event RESTART IDENTITY")
        c.exec_driver_sql("ALTER TABLE audit_event ENABLE TRIGGER USER")
        c.exec_driver_sql("DELETE FROM app_user")
        c.exec_driver_sql("DELETE FROM cpse")
        cpse = {
            code: c.execute(
                text(
                    "INSERT INTO cpse (code, name, sector, vendor_salt)"
                    " VALUES (:c, :n, 'Oil & Gas', :s) RETURNING id"
                ),
                {"c": code, "n": f"Synthetic {code}", "s": uuid.uuid4().hex * 2},
            ).scalar_one()
            for code in ("CPSE-A", "CPSE-B", "CPSE-C")
        }
        return {
            name: c.execute(
                text(
                    "INSERT INTO app_user (username, display_name, password_hash, role, cpse_id,"
                    " must_change_password) VALUES (:u, :d, :h, :r, :c, false) RETURNING id"
                ),
                {"u": name, "d": name.title(), "h": _hash(), "r": role, "c": cpse.get(code)},
            ).scalar_one()
            for name, (role, code) in DEMO.items()
        }


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:  # lifespan runs the migrations
        yield c


@pytest.fixture
def ids(client: TestClient) -> dict[str, uuid.UUID]:
    login_limiter.reset()
    return reset_db(get_engine())


def login(client: TestClient, username: str, password: str = PASSWORD) -> dict[str, str]:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def audit_actions(eng: Engine | None = None) -> list[str]:
    with (eng or get_engine()).connect() as c:
        return list(c.execute(text("SELECT action FROM audit_event ORDER BY id")).scalars())
