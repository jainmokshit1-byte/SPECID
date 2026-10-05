"""FR-801-807, FR-901-907, FR-1501-1513 over HTTP: maker -> checker -> consent -> CNMC ->
crosswalk -> migration pack -> change notices, with every refusal the governance needs."""

import csv
import io
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.cnmc import cnmc_valid
from app.db.session import get_engine, get_session_factory
from app.services import exports, jobs, registry, review
from app.services.errors import Conflict, Forbidden
from app.settings import get_settings
from tests.api.conftest import audit_actions
from tests.api.conftest import login as _login
from tests.api.test_runs import ingest_all, start

Ids = dict[str, uuid.UUID]
API = "/api/v1"


_TOKENS: dict[str, dict[str, str]] = {}


def login(client: TestClient, user: str) -> dict[str, str]:
    """One sign-in per user per test (the login rate limit is 5 per minute)."""
    if user not in _TOKENS:
        _TOKENS[user] = _login(client, user)
    return _TOKENS[user]


@pytest.fixture
def run(client: TestClient, ids: Ids, monkeypatch: pytest.MonkeyPatch) -> Iterator[dict[str, Any]]:
    _TOKENS.clear()
    monkeypatch.setattr(jobs, "INLINE", True)
    r = start(client, ingest_all(client))
    assert r["status"] == "DONE"
    yield r


def sql(query: str, **p: object) -> list[Any]:
    with get_engine().connect() as c:
        return list(c.execute(text(query), p).all())


def queue(client: TestClient, user: str, **params: Any) -> list[dict[str, Any]]:
    r = client.get(f"{API}/clusters", headers=login(client, user), params={"limit": 500, **params})
    assert r.status_code == 200, r.text
    items: list[dict[str, Any]] = r.json()["items"]
    return items


def cluster_with(client: TestClient, cpses: set[str]) -> dict[str, Any]:
    return next(c for c in queue(client, "meera", stage="to_propose") if set(c["cpses"]) == cpses)


def post(client: TestClient, user: str, path: str, body: dict[str, Any]) -> Any:
    return client.post(f"{API}{path}", headers=login(client, user), json=body)


def test_every_cluster_gets_an_open_review_task(client: TestClient, run: dict[str, Any]) -> None:
    n = sql("SELECT count(*) FROM review_task t JOIN cluster c ON c.id = t.cluster_id"
            " WHERE c.run_id = :r AND t.state = 'OPEN'", r=run["id"])[0][0]  # fmt: skip
    assert n == run["stats"]["clusters"] > 0
    items = queue(client, "meera", stage="to_propose")
    assert len(items) == n
    prios = [i["priority"] for i in items]
    assert prios == sorted(prios, reverse=True)  # FR-801: highest priority first


def test_three_cpse_cluster_waits_for_consent_then_issues(
    client: TestClient, run: dict[str, Any]
) -> None:
    """The demo path: maker (A) proposes, checker (B) confirms, CPSE-C consents, code issued."""
    c = cluster_with(client, {"CPSE-A", "CPSE-B", "CPSE-C"})
    cid = c["id"]
    detail = client.get(f"{API}/clusters/{cid}", headers=login(client, "meera")).json()
    assert detail["can"]["propose"] and detail["proposal"]["short_desc_40"]
    assert len(detail["proposal"]["short_desc_40"]) <= 40
    assert all(p["verdict"] in ("EQUIVALENT", "IDENTICAL") for p in detail["pairs"])

    assert (
        post(client, "meera", f"/clusters/{cid}/propose", {"decision": "APPROVE"}).json()["state"]
        == "MADE"
    )
    assert post(client, "meera", f"/clusters/{cid}/check", {"action": "CONFIRM"}).status_code == 403
    out = post(client, "arjun", f"/clusters/{cid}/check", {"action": "CONFIRM"}).json()
    assert out == {"state": "AWAITING_CONSENT", "cnmc": None, "waiting_for": ["CPSE-C"]}
    assert sql("SELECT count(*) FROM cnmc")[0][0] == 0  # nothing issued yet

    waiting = client.get(f"{API}/consents", headers=login(client, "kavya")).json()["items"]
    assert [w["cluster_id"] for w in waiting] == [cid] and waiting[0]["my_codes"]
    assert client.get(f"{API}/consents", headers=login(client, "arjun")).json()["items"] == []

    done = post(client, "kavya", f"/clusters/{cid}/consent", {"decision": "CONSENT"}).json()
    assert done["state"] == "DONE" and cnmc_valid(done["cnmc"])
    code = done["cnmc"]
    members = c["members"]
    assert (
        sql("SELECT count(*) FROM crosswalk WHERE cnmc = :n AND status = 'ACTIVE'", n=code)[0][0]
        == members
    )
    consents = sql("SELECT c.code, rc.via FROM review_consent rc JOIN cpse c ON c.id = rc.cpse_id"
                   " ORDER BY c.code")  # fmt: skip
    assert consents == [("CPSE-A", "MAKER_PROPOSAL"), ("CPSE-B", "CHECKER_CONFIRMATION"),
                        ("CPSE-C", "STEWARD")]  # fmt: skip
    assert sql("SELECT status FROM cluster WHERE id = :c", c=cid)[0][0] == "APPROVED"
    acts = audit_actions()
    for a in ("REVIEW_PROPOSED", "REVIEW_CONFIRMED", "CONSENT_REQUESTED", "CONSENT_GIVEN",
              "CNMC_ISSUED"):  # fmt: skip
        assert a in acts, a
    # every participating CPSE got a notice listing its codes
    notices = sql("SELECT c.code, n.kind, jsonb_array_length(n.delta) FROM change_notice n"
                  " JOIN cpse c ON c.id = n.cpse_id ORDER BY c.code")  # fmt: skip
    assert [(n[0], n[1]) for n in notices] == [("CPSE-A", "CNMC_ISSUED"), ("CPSE-B", "CNMC_ISSUED"),
                                                ("CPSE-C", "CNMC_ISSUED")]  # fmt: skip
    assert sum(n[2] for n in notices) == members
    # the registry shows it, with its crosswalk and its history
    listed = client.get(f"{API}/cnmc", headers=login(client, "erp"), params={"q": code}).json()
    assert listed["total"] == 1 and listed["items"][0]["cpses"] == ["CPSE-A", "CPSE-B", "CPSE-C"]
    got = client.get(f"{API}/cnmc/{code}", headers=login(client, "auditor")).json()
    assert len(got["crosswalk"]) == members and got["class_path"][1] == got["category"]
    assert {h["action"] for h in got["history"]} >= {"CNMC_ISSUED", "REVIEW_PROPOSED"}
    assert client.get(f"{API}/audit/verify", headers=login(client, "auditor")).json()["ok"]


def test_a_decline_keeps_that_cpse_out_and_issues_for_the_rest(
    client: TestClient, run: dict[str, Any]
) -> None:
    c = cluster_with(client, {"CPSE-A", "CPSE-B", "CPSE-C"})
    cid = c["id"]
    post(client, "meera", f"/clusters/{cid}/propose", {"decision": "APPROVE"})
    post(client, "arjun", f"/clusters/{cid}/check", {"action": "CONFIRM"})
    short = post(
        client, "kavya", f"/clusters/{cid}/consent", {"decision": "DECLINE", "reason": "no"}
    )
    assert short.status_code == 400  # a decline needs a reason of 5+ characters
    out = post(client, "kavya", f"/clusters/{cid}/consent",
               {"decision": "DECLINE", "reason": "Different face finish here"}).json()  # fmt: skip
    a_b = sql("SELECT count(*) FROM cluster_member m JOIN material_record r ON r.id = m.record_id"
              " JOIN cpse c ON c.id = r.cpse_id WHERE m.cluster_id = :c AND c.code <> 'CPSE-C'",
              c=cid)[0][0]  # fmt: skip
    if a_b >= 2:
        assert out["state"] == "DONE" and out["cnmc"]
        mapped = sql("SELECT DISTINCT c.code FROM crosswalk x JOIN cpse c ON c.id = x.cpse_id"
                     " WHERE x.cnmc = :n", n=out["cnmc"])  # fmt: skip
        assert sorted(m[0] for m in mapped) == ["CPSE-A", "CPSE-B"]
    else:
        assert out == {"state": "DONE", "cnmc": None, "waiting_for": []}
    declined = sql("SELECT n.kind, n.summary FROM change_notice n JOIN cpse c ON c.id = n.cpse_id"
                   " WHERE c.code = 'CPSE-C'")  # fmt: skip
    assert declined[0][0] == "CONSENT_DECLINED" and "stay unmapped" in declined[0][1]
    assert sql("SELECT reason FROM review_consent WHERE decision = 'DECLINE'")[0][0].startswith(
        "Different"
    )
    again = post(client, "kavya", f"/clusters/{cid}/consent", {"decision": "CONSENT"})
    assert again.status_code == 409  # answered already


def test_two_cpse_cluster_is_issued_on_confirmation(
    client: TestClient, run: dict[str, Any]
) -> None:
    """The maker's and the checker's CPSEs consent implicitly: no steward needed."""
    c = cluster_with(client, {"CPSE-A", "CPSE-B"})
    post(client, "meera", f"/clusters/{c['id']}/propose", {"decision": "APPROVE"})
    out = post(client, "arjun", f"/clusters/{c['id']}/check", {"action": "CONFIRM"}).json()
    assert out["state"] == "DONE" and cnmc_valid(out["cnmc"])
    # a steward of a CPSE that is not in the cluster cannot answer for it
    r = post(client, "kavya", f"/clusters/{c['id']}/consent", {"decision": "CONSENT"})
    assert r.status_code == 403


def test_consent_mode_none_issues_without_stewards(
    client: TestClient, run: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "consent_mode", "NONE")
    c = cluster_with(client, {"CPSE-A", "CPSE-B", "CPSE-C"})
    post(client, "meera", f"/clusters/{c['id']}/propose", {"decision": "APPROVE"})
    out = post(client, "arjun", f"/clusters/{c['id']}/check", {"action": "CONFIRM"}).json()
    assert out["state"] == "DONE" and out["cnmc"]
    after = sql("SELECT after->>'consent_mode' FROM audit_event WHERE action = 'CNMC_ISSUED'")
    assert after[0][0] == "NONE"  # written into every issuance event (TR-ALG-11)


def test_overturn_and_reject_need_a_comment(client: TestClient, run: dict[str, Any]) -> None:
    c = cluster_with(client, {"CPSE-A", "CPSE-B"})
    cid = c["id"]
    bad = post(client, "meera", f"/clusters/{cid}/propose", {"decision": "REJECT"})
    assert bad.status_code == 400 and bad.json()["title"] == "Comment required"
    post(client, "meera", f"/clusters/{cid}/propose", {"decision": "APPROVE"})
    again = post(client, "meera", f"/clusters/{cid}/propose", {"decision": "APPROVE"})
    assert again.status_code == 409  # already MADE
    assert (
        post(client, "arjun", f"/clusters/{cid}/check", {"action": "OVERTURN"}).status_code == 400
    )
    back = post(client, "arjun", f"/clusters/{cid}/check",
                {"action": "OVERTURN", "comment": "Check the face again"}).json()  # fmt: skip
    assert back["state"] == "OPEN"
    reject = post(client, "meera", f"/clusters/{cid}/propose",
                  {"decision": "REJECT", "comment": "Different trim"}).json()  # fmt: skip
    assert reject["state"] == "MADE"
    out = post(client, "arjun", f"/clusters/{cid}/check", {"action": "CONFIRM"}).json()
    assert out == {"state": "DONE", "cnmc": None, "waiting_for": []}
    assert sql("SELECT status FROM cluster WHERE id = :c", c=cid)[0][0] == "REJECTED"
    assert "REVIEW_OVERTURNED" in audit_actions()


def test_maker_is_never_the_checker_even_in_the_service(
    client: TestClient, run: dict[str, Any]
) -> None:
    """Defence in depth: the service refuses it whatever the role, and so does the database."""
    c = cluster_with(client, {"CPSE-A", "CPSE-B"})
    with get_session_factory()() as s:
        arjun = s.execute(text("SELECT id FROM app_user WHERE username = 'arjun'")).scalar_one()
        from app.db.models import AppUser

        user = s.get(AppUser, arjun)
        assert user is not None
        review.propose(s, user, uuid.UUID(c["id"]), "APPROVE", None)
        with pytest.raises(Forbidden):
            review.check(s, user, uuid.UUID(c["id"]), "CONFIRM", None, consent_mode="NONE")
        s.rollback()
    with get_engine().connect() as conn, pytest.raises(Exception, match="check"):
        conn.execute(text("UPDATE review_task SET made_by = :u, checked_by = :u"
                          " WHERE cluster_id = :c"), {"u": arjun, "c": c["id"]})  # fmt: skip


def test_a_legacy_code_is_never_mapped_twice(client: TestClient, run: dict[str, Any]) -> None:
    c = cluster_with(client, {"CPSE-A", "CPSE-B"})
    post(client, "meera", f"/clusters/{c['id']}/propose", {"decision": "APPROVE"})
    post(client, "arjun", f"/clusters/{c['id']}/check", {"action": "CONFIRM"})
    with get_session_factory()() as s:
        from app.db.models import AppUser, ReviewTask

        members = registry.members_of(s, uuid.UUID(c["id"]))
        task = s.query(ReviewTask).filter_by(cluster_id=uuid.UUID(c["id"])).one()
        actor = s.query(AppUser).filter_by(username="arjun").one()
        with pytest.raises(Conflict, match="already mapped"):
            registry.issue(s, actor, task, members, consent_mode="NONE", relation="EQUIVALENT")


def test_exports_and_migration_pack(client: TestClient, run: dict[str, Any]) -> None:
    c = cluster_with(client, {"CPSE-A", "CPSE-B"})
    post(client, "meera", f"/clusters/{c['id']}/propose", {"decision": "APPROVE"})
    code = post(client, "arjun", f"/clusters/{c['id']}/check", {"action": "CONFIRM"}).json()["cnmc"]

    h = login(client, "erp")
    r = client.get(f"{API}/exports/crosswalk", headers=h, params={"format": "csv"})
    assert r.status_code == 200 and r.content.startswith("﻿".encode())
    assert 'attachment; filename="specid_crosswalk.csv"' == r.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert {x["cnmc"] for x in rows} == {code} and len(rows) == c["members"]
    sap = client.get(f"{API}/exports/crosswalk", headers=h, params={"format": "sap_csv"})
    assert (
        sap.content.decode("utf-8-sig").splitlines()[0].startswith("MATNR;ZZ_CNMC;MAKTX_NATIONAL")
    )
    js = client.get(f"{API}/exports/crosswalk", headers=h, params={"format": "json", "cnmc": code})
    assert len(js.json()["rows"]) == c["members"]
    assert (
        client.get(f"{API}/exports/crosswalk", headers=login(client, "auditor")).status_code == 403
    )

    pack = client.get(f"{API}/exports/migration-pack", headers=login(client, "meera"),
                      params={"cpse": "CPSE-A"})  # fmt: skip
    text_ = pack.content.decode("utf-8-sig")
    assert text_.startswith("# Recommendations; apply through your own master-data process")
    body = list(csv.DictReader(io.StringIO(text_.split("\n", 1)[1])))
    assert body and all(b["cpse"] == "CPSE-A" for b in body)
    assert sum(b["survivor"] == "True" for b in body) == len({b["cnmc"] for b in body})
    assert {b["recommended_action"] for b in body} <= {
        "RETAIN", "BLOCK_FOR_NEW_PROCUREMENT", "PHASE_OUT_WHEN_STOCK_ZERO",
    }  # fmt: skip
    written = sql("SELECT count(*) FROM crosswalk x JOIN cpse c ON c.id = x.cpse_id"
                  " WHERE c.code = 'CPSE-A' AND x.migration_action IS NOT NULL")[0][0]  # fmt: skip
    assert written == len(body)
    assert {"EXPORT_DOWNLOADED", "MIGRATION_ACTIONS_SET"} <= set(audit_actions())
    other = client.get(f"{API}/exports/migration-pack", headers=login(client, "meera"),
                       params={"cpse": "CPSE-B"})  # fmt: skip
    assert other.status_code == 403  # a maker downloads only their own CPSE's pack


def test_change_notices_inbox_and_acknowledge(client: TestClient, run: dict[str, Any]) -> None:
    c = cluster_with(client, {"CPSE-A", "CPSE-B"})
    post(client, "meera", f"/clusters/{c['id']}/propose", {"decision": "APPROVE"})
    post(client, "arjun", f"/clusters/{c['id']}/check", {"action": "CONFIRM"})
    inbox = client.get(f"{API}/change-notices", headers=login(client, "meera")).json()
    assert inbox["cpse"] == "CPSE-A" and inbox["unacknowledged"] == 1
    nid = inbox["items"][0]["id"]
    assert client.get(f"{API}/change-notices", headers=login(client, "meera"),
                      params={"cpse": "CPSE-B"}).status_code == 403  # fmt: skip
    assert post(client, "arjun", f"/change-notices/{nid}/ack", {}).status_code == 403
    first = post(client, "meera", f"/change-notices/{nid}/ack", {}).json()
    second = post(client, "meera", f"/change-notices/{nid}/ack", {}).json()
    assert first["acknowledged_at"] == second["acknowledged_at"]  # idempotent
    assert audit_actions().count("CHANGE_NOTICE_ACKNOWLEDGED") == 1
    delta = client.get(f"{API}/change-notices/{nid}/delta.csv", headers=login(client, "meera"))
    assert "legacy_code" in delta.content.decode("utf-8-sig").splitlines()[0]
    by_admin = client.get(f"{API}/change-notices", headers=login(client, "admin"),
                          params={"cpse": "CPSE-B"}).json()  # fmt: skip
    assert by_admin["cpse"] == "CPSE-B" and by_admin["unacknowledged"] == 1


def test_pair_evidence_card(client: TestClient, run: dict[str, Any]) -> None:
    c = cluster_with(client, {"CPSE-A", "CPSE-B"})
    detail = client.get(f"{API}/clusters/{c['id']}", headers=login(client, "auditor")).json()
    pid = detail["pairs"][0]["id"]
    card = client.get(f"{API}/pairs/{pid}", headers=login(client, "auditor")).json()
    assert card["verdict"] in ("EQUIVALENT", "IDENTICAL") and card["a"]["cpse"] != card["b"]["cpse"]
    assert card["evidence"] and all(e["rule"] for e in card["evidence"])
    assert set(card["baseline"]) == {"b1", "b2", "tau1", "tau2"}


def test_csv_formula_injection_is_neutralised() -> None:
    assert [exports.safe_cell(v) for v in ("=SUM(A1)", "+1", "-2", "@x", "\tx", "ok", 5)] == [
        "'=SUM(A1)", "'+1", "'-2", "'@x", "'\tx", "ok", 5,
    ]  # fmt: skip
