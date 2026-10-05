"""FR-505-507, FR-601-611, FR-701-703, FR-1401-1411 over HTTP: a harmonisation run end to end."""

import csv
import io
import time
import uuid
from collections.abc import Iterator
from functools import lru_cache
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_engine, get_session_factory
from app.eval.generator import GeneratorConfig, files, generate
from app.services import harmonise, jobs
from tests.api.conftest import audit_actions, login

Ids = dict[str, uuid.UUID]
USERS = {"A": "meera", "B": "arjun", "C": "kavya"}


@lru_cache
def synth() -> dict[str, bytes]:
    return files(generate(GeneratorConfig(seed=13, n_entities=120)))


@pytest.fixture
def inline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the job in the request thread, against the test database."""
    monkeypatch.setattr(jobs, "INLINE", True)


def ingest_all(client: TestClient, cpses: str = "ABC") -> list[str]:
    out = []
    for c in cpses:
        h = login(client, USERS[c])
        r = client.post(
            "/api/v1/batches",
            headers=h,
            files={"file": (f"cpse_{c}.csv", synth()[f"cpse_{c}.csv"], "text/csv")},
            data={"is_synthetic": "true"},
        )
        assert r.status_code == 201, r.text
        batch = r.json()["id"]
        assert client.post(f"/api/v1/batches/{batch}/ingest", headers=h).status_code == 200
        out.append(batch)
    return out


def start(client: TestClient, batches: list[str], mode: str = "CROSS_CPSE", **opt: Any) -> dict:  # type: ignore[type-arg]
    r = client.post(
        "/api/v1/runs",
        headers=login(client, "meera"),
        json={"batch_ids": batches, "mode": mode, "options": opt},
    )
    assert r.status_code == 202, r.text
    body: dict[str, Any] = r.json()
    return body


def sql(query: str, **p: object) -> list[Any]:
    with get_engine().connect() as c:
        return list(c.execute(text(query), p).all())


@pytest.fixture
def done(client: TestClient, ids: Ids, inline: None) -> Iterator[dict[str, Any]]:
    run = start(client, ingest_all(client))
    yield run


def test_a_cross_cpse_run_reaches_done_with_stats(done: dict[str, Any]) -> None:
    assert done["status"] == "DONE" and done["error"] is None and done["finished_at"]
    s = done["stats"]
    assert s["progress"] == {
        "stage": "done",
        "done": s["progress"]["total"],
        "total": s["progress"]["total"],
    }
    assert s["records"] > 0 and s["specs_parsed"] + s["unclassified"] == s["records"]
    assert s["candidate_pairs"] > 0 and set(s["channels"]) == {"B", "L", "D", "M"}
    assert s["channels"]["B"] > 0 and s["channels"]["D"] == 0  # the dense channel arrives in Go 2
    assert sum(s["verdicts"].values()) == s["candidate_pairs"]
    assert s["clusters"] > 0 and set(s["timings_ms"]) >= {
        "read",
        "candidates",
        "decide",
        "cluster",
        "total",
    }
    assert s["blocked_egress"] >= 0
    cfg = done["config"]
    assert cfg["mode"] == "CROSS_CPSE" and cfg["bm25_k"] == 200 and cfg["dense_enabled"] is False
    assert cfg["templates"]["valve"] >= 1 and cfg["dictionary_version"] >= 2 and cfg["git_commit"]
    assert audit_actions()[-2:] == ["RUN_STARTED", "RUN_DONE"]


def test_in_cross_cpse_mode_no_pair_has_both_records_in_one_cpse(done: dict[str, Any]) -> None:
    """FR-505."""
    same = sql(
        "SELECT count(*) FROM pair_decision p JOIN material_record a ON a.id = p.rec_a"
        " JOIN material_record b ON b.id = p.rec_b WHERE a.cpse_id = b.cpse_id AND p.run_id = :r",
        r=done["id"],
    )
    assert same[0][0] == 0


def test_no_hard_negative_is_merged_and_no_true_pair_is_vetoed(done: dict[str, Any]) -> None:
    """FR-602 on a full run: the safety number, from the pipeline rather than the truth pairs."""
    truth = {
        (t["cpse"], t["legacy_code"]): t["entity_id"]
        for t in csv.DictReader(io.StringIO(synth()["truth_entities.csv"].decode()))
    }
    neighbours = {
        t["entity_id"]: t["neighbour_of"]
        for t in csv.DictReader(io.StringIO(synth()["truth_entities.csv"].decode()))
        if t["neighbour_of"]
    }
    rows = sql(
        "SELECT ca.code, a.legacy_code, cb.code, b.legacy_code, p.verdict FROM pair_decision p"
        " JOIN material_record a ON a.id = p.rec_a JOIN cpse ca ON ca.id = a.cpse_id"
        " JOIN material_record b ON b.id = p.rec_b JOIN cpse cb ON cb.id = b.cpse_id"
        " WHERE p.run_id = :r",
        r=done["id"],
    )
    merged_hard = vetoed_true = hard = 0
    for ca, la, cb, lb, verdict in rows:
        ea, eb = truth[(ca, la)], truth[(cb, lb)]
        is_hard = neighbours.get(ea) == eb or neighbours.get(eb) == ea
        hard += is_hard
        merged_hard += is_hard and verdict in ("EQUIVALENT", "IDENTICAL")
        vetoed_true += ea == eb and verdict == "NOT_EQUIVALENT"
    assert hard > 20  # the run did meet near-misses
    assert merged_hard == 0 and vetoed_true == 0


def test_no_cluster_contains_a_vetoed_pair(done: dict[str, Any]) -> None:
    """FR-701: constrained clustering."""
    bad = sql(
        "SELECT count(*) FROM pair_decision p"
        " JOIN cluster_member x ON x.record_id = p.rec_a JOIN cluster_member y"
        " ON y.record_id = p.rec_b AND y.cluster_id = x.cluster_id"
        " WHERE p.run_id = :r AND p.verdict = 'NOT_EQUIVALENT'",
        r=done["id"],
    )
    assert bad[0][0] == 0
    clusters = sql(
        "SELECT c.id, count(*), c.status, c.needs_review, c.priority FROM cluster c"
        " JOIN cluster_member m ON m.cluster_id = c.id WHERE c.run_id = :r GROUP BY c.id",
        r=done["id"],
    )
    assert clusters and all(n >= 2 and st == "PROPOSED" and nr for _, n, st, nr, _ in clusters)
    assert all(float(pr) > 0 for *_, pr in clusters)


def test_evidence_is_stored_with_rules_and_without_missing_both(done: dict[str, Any]) -> None:
    """FR-609, TR-DAT-05."""
    rows = sql(
        "SELECT evidence, template_version, route FROM pair_decision WHERE run_id = :r"
        " AND verdict <> 'NOT_EQUIVALENT' LIMIT 200",
        r=done["id"],
    )
    assert rows
    for evidence, version, route in rows:
        assert version >= 1 and route in ("REVIEW", "NONE")  # AUTO_ELIGIBLE is stored as REVIEW
        for e in evidence:
            assert e["status"] != "MISSING_BOTH" and e["rule"] and e["rule_text"]


def test_lookalikes_and_baselines_are_stored_per_pair(done: dict[str, Any]) -> None:
    """FR-1401, FR-1411: the Look-alike class and both baselines are decided per pair."""
    n = sql("SELECT count(*) FROM pair_decision WHERE run_id = :r AND baseline IS NOT NULL",
            r=done["id"])  # fmt: skip
    assert n[0][0] == done["stats"]["candidate_pairs"]
    vetoed = sql(
        "SELECT verdict, text_sim FROM pair_decision WHERE run_id = :r"
        " AND lookalike = 'LOOKALIKE_VETOED'",
        r=done["id"],
    )
    assert vetoed and all(v == "NOT_EQUIVALENT" and float(s) >= 0.85 for v, s in vetoed)


def test_specs_are_stored_for_every_record(done: dict[str, Any]) -> None:
    n = sql("SELECT count(*) FROM spec_record")
    assert n[0][0] == done["stats"]["records"]


def test_pairs_endpoint_filters_and_pages(client: TestClient, done: dict[str, Any]) -> None:
    h = login(client, "auditor")
    url = f"/api/v1/runs/{done['id']}/pairs"
    allp = client.get(url, headers=h, params={"limit": 5}).json()
    assert allp["total"] == done["stats"]["candidate_pairs"] and len(allp["items"]) == 5
    eq = client.get(url, headers=h, params={"verdict": "EQUIVALENT", "limit": 500}).json()
    assert eq["total"] == done["stats"]["verdicts"]["EQUIVALENT"]
    assert all(p["verdict"] == "EQUIVALENT" and p["cpse_a"] != p["cpse_b"] for p in eq["items"])
    look = client.get(url, headers=h, params={"lookalike": "LOOKALIKE_VETOED"}).json()
    assert look["total"] > 0
    valve = client.get(url, headers=h, params={"category": "VALVE", "limit": 500}).json()
    assert valve["total"] > 0 and valve["total"] < allp["total"]
    assert client.get(url, headers=h, params={"limit": 0}).status_code == 422


def test_a_second_run_over_the_same_batches_is_identical(
    client: TestClient, ids: Ids, inline: None
) -> None:
    batches = ingest_all(client)
    first, second = start(client, batches), start(client, batches)
    assert first["id"] != second["id"]
    assert first["stats"]["verdicts"] == second["stats"]["verdicts"]
    assert first["stats"]["candidate_pairs"] == second["stats"]["candidate_pairs"]
    assert first["stats"]["clusters"] == second["stats"]["clusters"]


def test_within_cpse_mode_finds_internal_duplicates(
    client: TestClient, ids: Ids, inline: None
) -> None:
    (a,) = ingest_all(client, "A")
    run = start(client, [a], mode="WITHIN_CPSE")
    assert run["status"] == "DONE" and run["stats"]["candidate_pairs"] > 0
    same = sql(
        "SELECT count(*) FROM pair_decision p JOIN material_record a ON a.id = p.rec_a"
        " JOIN material_record b ON b.id = p.rec_b WHERE a.cpse_id <> b.cpse_id AND p.run_id = :r",
        r=run["id"],
    )
    assert same[0][0] == 0


def test_run_options_are_validated_and_stored(client: TestClient, ids: Ids, inline: None) -> None:
    batches = ingest_all(client)
    h = login(client, "meera")
    r = client.post("/api/v1/runs", headers=h, json={"batch_ids": batches, "options": {"nope": 1}})
    assert r.status_code == 400 and r.json()["title"] == "Bad options"
    run = start(client, batches, bm25_k=5, block_cap=50)
    assert run["config"]["bm25_k"] == 5 and run["config"]["block_cap"] == 50


def test_run_start_is_validated(client: TestClient, ids: Ids, inline: None) -> None:
    (a,) = ingest_all(client, "A")
    h = login(client, "meera")
    one_cpse = client.post("/api/v1/runs", headers=h, json={"batch_ids": [a]})
    assert one_cpse.status_code == 400 and one_cpse.json()["title"] == "One CPSE"
    missing = client.post("/api/v1/runs", headers=h, json={"batch_ids": [str(uuid.uuid4())]})
    assert missing.status_code == 404
    tiny = {"file": ("x.csv", b"legacy_code,short_text\n1,PIPE\n", "text/csv")}
    raw = client.post("/api/v1/batches", headers=login(client, "arjun"), files=tiny)
    pending = client.post("/api/v1/runs", headers=h, json={"batch_ids": [a, raw.json()["id"]]})
    assert pending.status_code == 409
    assert client.post("/api/v1/runs", headers=h, json={"batch_ids": []}).status_code == 422


def test_a_queued_run_can_be_cancelled(
    client: TestClient, ids: Ids, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs, "submit", lambda *a, **k: None)  # stays QUEUED
    run = start(client, ingest_all(client))
    assert run["status"] == "QUEUED"
    r = client.post(f"/api/v1/runs/{run['id']}/cancel", headers=login(client, "meera"))
    assert r.status_code == 200 and r.json()["status"] == "CANCELLED"
    again = client.post(f"/api/v1/runs/{run['id']}/cancel", headers=login(client, "meera"))
    assert again.status_code == 409
    harmonise.execute(  # a cancelled run is never started
        get_session_factory(), uuid.UUID(run["id"]),
        templates=client.app.state.templates, dictionary=client.app.state.dictionary,  # type: ignore[attr-defined]
        settings=__import__("app.settings", fromlist=["get_settings"]).get_settings(),
    )  # fmt: skip
    assert sql("SELECT count(*) FROM pair_decision")[0][0] == 0


def test_cancelling_a_running_run_removes_its_partial_results(
    client: TestClient, ids: Ids, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs, "submit", lambda *a, **k: None)
    monkeypatch.setattr(harmonise, "PAIR_BATCH", 10)
    run = start(client, ingest_all(client))
    calls = {"n": 0}
    real = harmonise._Control.check_cancel

    def cancel_on_fifth(self: Any) -> None:
        calls["n"] += 1
        if calls["n"] == 5:
            raise harmonise.RunCancelled
        real(self)

    monkeypatch.setattr(harmonise._Control, "check_cancel", cancel_on_fifth)
    from app.settings import get_settings

    harmonise.execute(
        get_session_factory(), uuid.UUID(run["id"]),
        templates=client.app.state.templates, dictionary=client.app.state.dictionary,  # type: ignore[attr-defined]
        settings=get_settings(),
    )  # fmt: skip
    got = client.get(f"/api/v1/runs/{run['id']}", headers=login(client, "meera")).json()
    assert got["status"] == "CANCELLED" and got["finished_at"]
    assert sql("SELECT count(*) FROM pair_decision")[0][0] == 0
    assert sql("SELECT count(*) FROM cluster")[0][0] == 0
    assert "RUN_CANCELLED" in audit_actions()


def test_a_failing_run_is_marked_failed_and_leaves_no_results(
    client: TestClient, ids: Ids, inline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*a: Any, **k: Any) -> None:
        raise RuntimeError("decide exploded")

    monkeypatch.setattr(harmonise, "decide", boom)
    run = start(client, ingest_all(client))
    assert run["status"] == "FAILED" and "decide exploded" in run["error"]
    assert sql("SELECT count(*) FROM pair_decision")[0][0] == 0
    assert "RUN_FAILED" in audit_actions()


def test_runs_interrupted_by_a_restart_are_failed(
    client: TestClient, ids: Ids, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(jobs, "submit", lambda *a, **k: None)
    queued = start(client, ingest_all(client))
    with get_session_factory()() as s:
        assert jobs.recover_interrupted(s) == 1
        s.commit()
    got = client.get(f"/api/v1/runs/{queued['id']}", headers=login(client, "meera")).json()
    assert got["status"] == "FAILED" and "restart" in got["error"]


def test_the_real_worker_process_runs_a_job(client: TestClient, ids: Ids) -> None:
    """No INLINE: the spawned worker installs its guard, opens its own engine and finishes."""
    batches = ingest_all(client)
    run = start(client, batches)
    assert run["status"] == "QUEUED"
    deadline = time.time() + 180
    got: dict[str, Any] = run
    h = login(client, "meera")  # one sign-in: the login rate limit is 5 per minute
    while time.time() < deadline and got["status"] in ("QUEUED", "RUNNING"):
        time.sleep(1)
        got = client.get(f"/api/v1/runs/{run['id']}", headers=h).json()
    assert got["status"] == "DONE", got
    assert got["stats"]["candidate_pairs"] > 0 and got["stats"]["blocked_egress"] >= 0
    jobs.shutdown()


def test_start_and_read_runs_need_the_right_roles(client: TestClient, ids: Ids) -> None:
    assert client.post("/api/v1/runs", json={}).status_code == 401
    assert client.get("/api/v1/runs", headers=login(client, "erp")).status_code == 403
    assert client.get("/api/v1/runs", headers=login(client, "auditor")).status_code == 200
    r = client.post("/api/v1/runs", headers=login(client, "auditor"), json={"batch_ids": []})
    assert r.status_code == 403


def test_a_run_with_an_ai_provider_uses_meaning_search_and_the_reader(
    client: TestClient, ids: Ids, inline: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DEC-41: with a provider (a fake here, Gemini in the hosted demo) the dense channel adds
    pairs and the reader is asked about unknown key values; verdicts still come from the rules."""
    import hashlib

    from app.settings import get_settings

    class FakeAI:
        name = "fake"
        model = embed_model = "fake"

        def __init__(self) -> None:
            self.asked = 0

        def embed(self, texts: Any) -> list[list[float]]:
            out = []
            for t in texts:
                v = [
                    b / 255
                    for b in hashlib.sha256(" ".join(sorted(set(t.split()))).encode()).digest()
                ]
                n = sum(x * x for x in v) ** 0.5
                out.append([x / n for x in v])
            return out

        def generate_json(self, prompt: str) -> Any:
            self.asked += 1
            return {"items": []}

    fake = FakeAI()
    monkeypatch.setattr(harmonise, "make_provider", lambda s: fake)
    monkeypatch.setattr(get_settings(), "ai_provider", "gemini")
    run = start(client, ingest_all(client))
    s = run["stats"]
    assert run["status"] == "DONE" and s["ai_provider"] == "fake"
    assert s["channels"]["D"] > 0 and s["dense_pairs"] > 0
    assert s["ai_records_asked"] > 0 and fake.asked > 0
    assert s["ai_values_accepted"] == 0  # the fake read nothing: nothing was invented
    assert run["config"]["dense_enabled"] is True
