"""FR-1001-1003 search-before-create, FR-1201/1203 dashboard and money, FR-1401 Look-alike Guard."""

import re
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services import jobs
from tests.api.conftest import login as _login
from tests.api.test_runs import ingest_all, start, synth

API = "/api/v1"
_TOKENS: dict[str, dict[str, str]] = {}


def login(client: TestClient, user: str) -> dict[str, str]:
    if user not in _TOKENS:
        _TOKENS[user] = _login(client, user)
    return _TOKENS[user]


@pytest.fixture
def run(
    client: TestClient, ids: dict[str, uuid.UUID], monkeypatch: pytest.MonkeyPatch
) -> Iterator[dict[str, Any]]:
    _TOKENS.clear()
    monkeypatch.setattr(jobs, "INLINE", True)
    batches = ingest_all(client)
    for batch, (c, user) in zip(batches, (("A", "meera"), ("B", "arjun"), ("C", "kavya")),
                                strict=True):  # fmt: skip
        r = client.post(
            f"{API}/batches/{batch}/procurement",
            headers=login(client, user),
            files={"file": (f"p_{c}.csv", synth()[f"procurement_{c}.csv"], "text/csv")},
        )
        assert r.status_code == 200, r.text
    r = start(client, batches)
    assert r["status"] == "DONE"
    yield r


def test_dashboard_reconciles_with_the_run(client: TestClient, run: dict[str, Any]) -> None:
    d = client.get(f"{API}/dashboard", headers=login(client, "auditor")).json()
    assert d["run_id"] == run["id"] and d["is_synthetic"] is True and d["computed_at"]
    assert [c["cpse"] for c in d["per_cpse"]] == ["CPSE-A", "CPSE-B", "CPSE-C"]
    assert sum(c["records"] for c in d["per_cpse"]) == run["stats"]["records"]
    assert all(0 <= (c["health_score"] or 0) <= 100 for c in d["per_cpse"])
    assert d["groups"]["total"] == run["stats"]["clusters"] >= d["groups"]["cross_cpse"] > 0
    assert d["backlog"] == {"OPEN": run["stats"]["clusters"]}
    assert d["verdicts"] == run["stats"]["verdicts"] and d["issued"] == 0
    assert len(d["top_groups"]) == min(10, run["stats"]["clusters"])
    prios = [g["priority"] for g in d["top_groups"]]
    assert prios == sorted(prios, reverse=True)


def test_money_shows_price_gaps_between_cpses(client: TestClient, run: dict[str, Any]) -> None:
    m = client.get(f"{API}/dashboard", headers=login(client, "meera")).json()["money"]
    assert m["groups_with_prices"] > 0 and m["total_price_gap"] > 0
    assert "not savings" in m["note"]
    top = m["top_price_gaps"][0]
    assert len({b["cpse"] for b in top["by_cpse"]}) >= 2
    assert top["lowest_price"] == min(b["avg_price"] for b in top["by_cpse"])
    gaps = [g["price_gap"] for g in m["top_price_gaps"]]
    assert gaps == sorted(gaps, reverse=True)
    pooled = client.get(f"{API}/pooling", headers=login(client, "meera"), params={"limit": 200})
    assert pooled.json()["groups_with_prices"] == m["groups_with_prices"]
    s = m["stock_sharing"]
    assert s["suggestions"] >= len(s["top"])
    for t in s["top"]:  # idle stock of one CPSE, bought by another in the last 12 months
        assert t["holder"] != t["buyer"] and 0 < t["transferable"] <= t["idle_stock"]


def test_lookalike_guard_lists_vetoed_lookalikes_with_the_decisive_attribute(
    client: TestClient, run: dict[str, Any]
) -> None:
    v = client.get(f"{API}/radar/lookalikes", headers=login(client, "auditor")).json()
    assert v["total"] > 0 and v["thresholds"]["lookalike_min_sim"] == 0.85
    for item in v["items"]:
        assert item["verdict"] == "NOT_EQUIVALENT" and item["text_sim"] >= 0.85
        assert item["decisive"] and all(d["rule"] for d in item["decisive"])
    sims = [i["text_sim"] for i in v["items"]]
    assert sims == sorted(sims, reverse=True)
    assert sum(a["pairs"] for a in v["decisive_attributes"]) >= v["total"]
    total = sum(h["same"] + h["different"] + h["unknown"] for h in v["histogram"])
    assert total == run["stats"]["candidate_pairs"]
    t = client.get(f"{API}/radar/hidden-twins", headers=login(client, "auditor")).json()
    assert all(i["verdict"] in ("EQUIVALENT", "IDENTICAL") and i["text_sim"] <= 0.75
               for i in t["items"])  # fmt: skip
    assert client.get(f"{API}/radar/lookalikes", headers=login(client, "erp")).status_code == 403


def test_search_before_create_finds_an_issued_code(client: TestClient, run: dict[str, Any]) -> None:
    items = client.get(f"{API}/clusters", headers=login(client, "meera"),
                       params={"stage": "to_propose", "limit": 500}).json()["items"]  # fmt: skip
    c = next(i for i in items if set(i["cpses"]) == {"CPSE-A", "CPSE-B"})
    detail = client.get(f"{API}/clusters/{c['id']}", headers=login(client, "meera")).json()
    client.post(f"{API}/clusters/{c['id']}/propose", headers=login(client, "meera"),
                json={"decision": "APPROVE"})  # fmt: skip
    code = client.post(f"{API}/clusters/{c['id']}/check", headers=login(client, "arjun"),
                       json={"action": "CONFIRM"}).json()["cnmc"]  # fmt: skip
    member = detail["members"][0]
    text_ = member["long_text"] or member["short_text"]
    hit = client.post(f"{API}/search-before-create", headers=login(client, "erp"),
                      json={"text": text_}).json()  # fmt: skip
    assert hit["recommended_action"] == "USE_EXISTING" and hit["would_create_duplicate"] is True
    assert hit["candidates"][0]["cnmc"] == code
    assert hit["candidates"][0]["verdict"] in ("EQUIVALENT", "IDENTICAL")

    # the same words with a different pressure class: never "use existing"
    cls = member["attrs"].get("pressure_class")
    if cls:
        other = {150: 300, 300: 600, 600: 150}.get(cls, 150)
        changed = re.sub(rf"\b(CL|CLASS ){cls}\b|\b{cls}#", f"CL{other}", text_)
        miss = client.post(f"{API}/search-before-create", headers=login(client, "erp"),
                           json={"text": changed}).json()  # fmt: skip
        assert all(x["cnmc"] != code or x["verdict"] == "NOT_EQUIVALENT"
                   for x in miss["candidates"])  # fmt: skip

    unknown = client.post(f"{API}/search-before-create", headers=login(client, "meera"),
                          json={"text": "something unusual 42"}).json()  # fmt: skip
    assert unknown["recommended_action"] == "SUPPLY_ATTRIBUTES"
    assert unknown["missing"] == ["category"]
    assert client.post(f"{API}/search-before-create", headers=login(client, "auditor"),
                       json={"text": "x valve"}).status_code == 403  # fmt: skip


def test_dashboard_without_runs_is_empty(client: TestClient, ids: dict[str, uuid.UUID]) -> None:
    _TOKENS.clear()
    d = client.get(f"{API}/dashboard", headers=login(client, "meera")).json()
    assert d == {"run_id": None, "empty": True}
    assert client.get(f"{API}/dashboard", headers=login(client, "meera"),
                      params={"run_id": str(uuid.uuid4())}).status_code == 404  # fmt: skip
