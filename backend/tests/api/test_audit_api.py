"""API-23 `GET /audit`, `GET /audit/verify` through the API (FR-1302, TR-TST-09)."""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_engine
from tests.api.conftest import audit_actions, login

API = "/api/v1"


def test_login_succeeded_events_are_listed(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    """Done-when (Phase 3): LOGIN_SUCCEEDED events appear in S12."""
    for name in ("meera", "arjun", "admin"):
        login(client, name)
    h = login(client, "auditor")
    r = client.get(f"{API}/audit", params={"action": "LOGIN_SUCCEEDED"}, headers=h)
    assert r.status_code == 200
    items = r.json()["items"]
    assert [i["actor"] for i in items] == ["auditor", "admin", "arjun", "meera"]
    assert all(i["object_type"] == "app_user" and len(i["hash"]) == 64 for i in items)
    assert items[-1]["prev_hash"] is None and items[0]["prev_hash"] == items[1]["hash"]


def test_filters_and_cursor(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    for _ in range(3):
        login(client, "meera")
    h = login(client, "admin")
    page = client.get(f"{API}/audit", params={"actor": "meera", "limit": 2}, headers=h).json()
    assert len(page["items"]) == 2 and page["next_cursor"]
    rest = client.get(
        f"{API}/audit", params={"actor": "meera", "limit": 2, "cursor": page["next_cursor"]},
        headers=h,
    ).json()  # fmt: skip
    assert len(rest["items"]) == 1 and rest["next_cursor"] is None
    future = client.get(f"{API}/audit", params={"since": "2999-01-01T00:00:00Z"}, headers=h)
    assert future.json()["items"] == []
    bad = client.get(f"{API}/audit", params={"cursor": "%%%"}, headers=h)
    assert bad.status_code == 400 and bad.json()["title"] == "Invalid cursor"


def test_verify_intact_then_reports_tampered_event(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    """Done-when (Phase 3): disable the trigger as owner, edit a row → verify reports that id."""
    login(client, "meera")
    login(client, "arjun")
    h = login(client, "auditor")
    ok = client.get(f"{API}/audit/verify", headers=h).json()
    assert ok == {"ok": True, "events": 3, "first_bad_id": None}
    assert audit_actions()[-1] == "AUDIT_VERIFIED"

    with get_engine().begin() as c:  # the owner can disable the trigger; specid_app cannot
        target = (
            c.execute(
                text(
                    "SELECT id FROM audit_event WHERE action='LOGIN_SUCCEEDED' ORDER BY id OFFSET 1"
                )
            )
            .scalars()
            .first()
        )
        c.exec_driver_sql("ALTER TABLE audit_event DISABLE TRIGGER audit_event_no_update_delete")
        c.execute(
            text("""UPDATE audit_event SET after = '{"username": "mallory"}' WHERE id = :id"""),
            {"id": target},
        )
        c.exec_driver_sql("ALTER TABLE audit_event ENABLE TRIGGER audit_event_no_update_delete")
    broken = client.get(f"{API}/audit/verify", headers=h).json()
    assert broken == {"ok": False, "events": 1, "first_bad_id": target}
    last = client.get(f"{API}/audit", params={"action": "AUDIT_VERIFIED"}, headers=h).json()
    assert last["items"][0]["after"] == {"ok": False, "events": 1, "first_bad_id": target}


def test_cursor_built_by_the_ui_lists_older_events(
    client: TestClient, ids: dict[str, uuid.UUID]
) -> None:
    """S12 links a broken event with cursorBefore(id + 1) = base64 of the id (TR-API-04)."""
    for _ in range(4):
        login(client, "meera")
    h = login(client, "admin")
    page = client.get(f"{API}/audit", params={"cursor": "Mw=="}, headers=h).json()  # btoa("3")
    assert [i["id"] for i in page["items"]] == [2, 1]
