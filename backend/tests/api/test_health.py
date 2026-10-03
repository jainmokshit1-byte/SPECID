"""API-24 GET /api/v1/health (NFR-11, TR-OPS-09). Needs DATABASE_URL pointing at Postgres 16."""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.db.session import get_engine
from app.main import app


def test_health_ok_with_database() -> None:
    with TestClient(app) as client:
        r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"
    assert body["consent_mode"] in ("ALL_PARTICIPANTS", "NONE")
    # the egress guard arrives in Phase 5 and is never claimed early
    assert body["egress_guard"]["installed"] is False
    assert "git_commit" in body


def test_health_503_when_database_unreachable() -> None:
    dead = create_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )
    app.dependency_overrides[get_engine] = lambda: dead
    try:
        with TestClient(app) as client:
            r = client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503
    assert r.json()["db"] == "unreachable"


def test_openapi_served_and_cdn_docs_disabled() -> None:
    with TestClient(app) as client:
        assert client.get("/api/v1/openapi.json").status_code == 200
        assert client.get("/docs").status_code == 404
        assert client.get("/api/v1/docs").status_code == 404
