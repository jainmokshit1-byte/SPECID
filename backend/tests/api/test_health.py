"""API-24 GET /api/v1/health (NFR-11, TR-OPS-09). Needs DATABASE_URL pointing at Postgres 16."""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import main
from app.core.templates import TemplateError
from app.db.session import get_engine
from app.main import app
from app.settings import get_settings
from tests.coreenv import TEMPLATE_DIR


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


def test_health_reports_template_versions_loaded_at_startup() -> None:
    with TestClient(app) as client:
        body = client.get("/api/v1/health").json()
    # PRD Appendix A: one YAML per category, version 1 (gasket is DRAFT in the DB, DEC-13)
    assert body["templates"] == {
        "fastener": 1,
        "flange": 1,
        "gasket": 1,
        "motor": 1,
        "pipe": 1,
        "valve": 1,
    }


def test_invalid_template_yaml_aborts_startup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """FR-401, TR-OPS-02: startup fails and names the file and line."""
    for f in TEMPLATE_DIR.glob("*.yaml"):
        shutil.copy(f, tmp_path / f.name)
    bad = (tmp_path / "pipe.yaml").read_text("utf-8").replace("version: 1", "version: zero")
    (tmp_path / "pipe.yaml").write_text(bad, "utf-8")
    patched = get_settings().model_copy(update={"template_dir": str(tmp_path)})
    monkeypatch.setattr(main, "get_settings", lambda: patched)
    with pytest.raises(TemplateError, match=r"pipe\.yaml:\d+: version"):
        with TestClient(app):
            pass
