"""API-15 GET /templates (FR-401): the rulebook is readable by every role, read-only."""

import uuid

from fastapi.testclient import TestClient

from tests.api.conftest import login


def test_every_role_reads_the_rulebook(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    r = client.get("/api/v1/templates", headers=login(client, "erp"))
    assert r.status_code == 200
    cats = {t["category"]: t for t in r.json()}
    assert {"VALVE", "PIPE", "FLANGE", "GASKET", "FASTENER", "MOTOR"} <= set(cats)
    assert "pressure_class" in cats["VALVE"]["core"] and cats["VALVE"]["critical_default"] is True


def test_one_template_has_its_rule_text(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    h = login(client, "meera")
    body = client.get("/api/v1/templates/valve", headers=h).json()
    assert body["category"] == "VALVE" and body["rule_text"]["size_dn"].startswith("Compared as DN")
    assert client.get("/api/v1/templates/VALVE", headers=h).json()["id"] == "valve"
    r = client.get("/api/v1/templates/nope", headers=h)
    assert r.status_code == 404 and r.headers["content-type"].startswith("application/problem+json")
