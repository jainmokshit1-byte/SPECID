"""DEC-42 demo mode (one-click sign-in, demo data at start) and the seeded evaluation."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_engine
from app.eval.runner import wilson_upper
from app.main import app
from app.services import demo, jobs
from app.settings import get_settings
from tests.api.conftest import login


def count(sql: str) -> int:
    with get_engine().connect() as c:
        return int(c.execute(text(sql)).scalar_one())


def test_wilson_and_rule_of_three() -> None:
    assert wilson_upper(0, 1000) == 0.003  # rule of three, never "0%"
    assert wilson_upper(0, 0) is None
    upper = wilson_upper(5, 1000)
    assert upper is not None and 0.01 < upper < 0.013


def test_evaluation_reports_bounds_baselines_and_honesty(
    client: TestClient, ids: dict[str, uuid.UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs, "INLINE", True)
    h = login(client, "meera")
    r = client.post("/api/v1/eval/runs", headers=h, json={"seed": 3, "n_entities": 150})
    assert r.status_code == 202
    e = r.json()
    assert e["status"] == "DONE", e["metrics"]
    m = e["metrics"]
    assert "optimistic by construction" in m["honesty"]
    s, b1, b2 = m["methods"]["specid"], m["methods"]["b1"], m["methods"]["b2"]
    assert s["false_merges"] == 0 and s["hard_negatives"] > 0
    assert s["false_merge_upper_95"] == round(3 / s["hard_negatives"], 6)
    assert 0.5 <= b1["tau"] <= 0.99 and 0.5 <= b2["tau"] <= 0.99
    assert b1["false_merges"] >= s["false_merges"]  # the text-only baseline merges look-alikes
    assert 0 < m["blocking"]["pair_completeness"] <= 1 and m["blocking"]["reduction_ratio"] > 0.9
    assert set(m["per_category"]) <= {
        "VALVE", "PIPE", "FLANGE", "FASTENER", "MOTOR", "UNRECOGNISED",
    }  # fmt: skip
    again = client.post("/api/v1/eval/runs", headers=h, json={"seed": 3, "n_entities": 150}).json()
    assert again["metrics"]["methods"] == m["methods"]  # same seed, same numbers
    md = client.get(f"/api/v1/eval/runs/{e['id']}/report.md", headers=h)
    assert md.status_code == 200 and "SYNTHETIC DATA" in md.text and "B1 text only" in md.text
    listed = client.get("/api/v1/eval/runs", headers=h).json()
    assert {x["id"] for x in listed} == {again["id"], e["id"]}


def test_demo_login_only_in_demo_mode(
    client: TestClient, ids: dict[str, uuid.UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    r = client.post("/api/v1/auth/demo-login", json={"username": "kavya"})
    assert r.status_code == 404  # off by default
    monkeypatch.setattr(get_settings(), "demo_mode", True)
    ok = client.post("/api/v1/auth/demo-login", json={"username": "kavya"})
    assert ok.status_code == 200 and ok.json()["role"] == "CHECKER"
    me = client.get("/api/v1/me", headers={"Authorization": f"Bearer {ok.json()['access_token']}"})
    assert me.json()["cpse_code"] == "CPSE-C"
    assert client.post("/api/v1/auth/demo-login", json={"username": "root"}).status_code == 404


def test_demo_bootstrap_prepares_data_runs_codes_and_an_evaluation(
    client: TestClient, ids: dict[str, uuid.UUID], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEMO_PASSWORD", "demo-password-for-tests")
    demo.bootstrap(app.state, get_settings(), n_entities=120)
    assert count("SELECT count(*) FROM upload_batch WHERE status = 'INGESTED'") == 3
    assert count("SELECT count(*) FROM procurement_line") > 0
    assert count("SELECT count(*) FROM run WHERE status = 'DONE'") == 1
    assert 1 <= count("SELECT count(*) FROM cnmc") <= 3
    assert count("SELECT count(*) FROM eval_run WHERE status = 'DONE'") == 1
    demo.bootstrap(app.state, get_settings(), n_entities=120)  # a restart adds nothing
    assert count("SELECT count(*) FROM upload_batch") == 3
    health = client.get("/api/v1/health").json()
    assert health["demo_mode"] is False and health["ai_provider"] == "off"
