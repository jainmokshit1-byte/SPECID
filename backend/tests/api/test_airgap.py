"""API-32 GET /system/airgap (SF-7): status for the footer, never claimed beyond what is true."""

import socket
import uuid

import pytest
from fastapi.testclient import TestClient

from app.security import egress
from tests.api.conftest import login


def test_airgap_reports_the_guard_and_the_counter(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    r = client.get("/api/v1/system/airgap", headers=login(client, "erp"))  # every role may read it
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "OFFLINE" and body["egress_guard"]["installed"] is True
    assert isinstance(body["blocked_egress_attempts"], int) and "localhost" in body["allowed_hosts"]
    assert "Docker network" in body["scope"]


def test_a_blocked_attempt_shows_up_in_the_counter(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    h = login(client, "meera")
    before = client.get("/api/v1/system/airgap", headers=h).json()["blocked_egress_attempts"]
    with pytest.raises(PermissionError):
        socket.create_connection(("203.0.113.5", 80), timeout=1)
    after = client.get("/api/v1/system/airgap", headers=h).json()["blocked_egress_attempts"]
    assert after == before + 1 == egress.blocked_attempts()


def test_airgap_needs_a_signed_in_user(client: TestClient) -> None:
    assert client.get("/api/v1/system/airgap").status_code == 401
