"""FR-101-107, FR-1005 over HTTP: upload, mapping, ingest, quality, purchase history, scope."""

import uuid
from functools import lru_cache
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.session import get_engine
from app.eval.generator import GeneratorConfig, files, generate
from tests.api.conftest import audit_actions, login

BATCHES = "/api/v1/batches"
Ids = dict[str, uuid.UUID]


@lru_cache
def synth() -> dict[str, bytes]:
    """A small seeded dataset (about 250 records): enough to exercise every path quickly."""
    return files(generate(GeneratorConfig(seed=11, n_entities=100)))


def upload(
    client: TestClient, user: str, name: str = "cpse_A.csv", data: bytes | None = None, **form: str
) -> dict[str, Any]:
    r = client.post(
        BATCHES,
        headers=login(client, user),
        files={"file": (name, data if data is not None else synth()[name], "text/csv")},
        data={"is_synthetic": "true", **form},
    )
    assert r.status_code in (200, 201), r.text
    body: dict[str, Any] = r.json()
    return body


def ingest(client: TestClient, user: str, batch_id: str) -> dict[str, Any]:
    r = client.post(f"{BATCHES}/{batch_id}/ingest", headers=login(client, user))
    assert r.status_code == 200, r.text
    body: dict[str, Any] = r.json()
    return body


def count(sql: str, **p: object) -> int:
    with get_engine().connect() as c:
        return int(c.execute(text(sql), p).scalar_one())


def test_upload_suggests_the_mapping_and_previews_rows(client: TestClient, ids: Ids) -> None:
    b = upload(client, "meera")
    assert (b["cpse_code"], b["status"], b["is_synthetic"], b["encoding"]) == (
        "CPSE-A", "UPLOADED", True, "utf-8",
    )  # fmt: skip
    assert b["suggested_mapping"]["legacy_code"] == "legacy_code"
    assert (
        len(b["sample_rows"]) == 5 and b["row_count"] == len(synth()["cpse_A.csv"].splitlines()) - 1
    )
    assert "BATCH_UPLOADED" in audit_actions()


def test_ingest_creates_records_specs_and_a_quality_report(client: TestClient, ids: Ids) -> None:
    b = upload(client, "meera")
    done = ingest(client, "meera", b["id"])
    q = done["quality"]
    assert done["status"] == "INGESTED" and q["rows"] == b["row_count"] and q["rejected_rows"] == 0
    # FR-103: the numbers reconcile with a SQL count
    assert count("SELECT count(*) FROM material_record WHERE batch_id = :b", b=b["id"]) == q["rows"]
    spec_sql = "SELECT count(*) FROM spec_record s JOIN material_record m ON m.id = s.record_id"
    assert count(spec_sql + " WHERE m.batch_id = :b", b=b["id"]) == q["rows"]
    cats = count(spec_sql + " WHERE m.batch_id = :b AND s.category IS NOT NULL", b=b["id"])
    share = sum(v for k, v in q["category_share"].items() if k != "UNRECOGNISED")
    assert abs(share * q["rows"] - cats) < 1
    assert q["completeness"]["legacy_code"] == 1.0 and q["completeness"]["short_text"] == 1.0
    assert 0 <= q["health_score"] <= 100 and set(q["health_components"]) == {
        "descriptions", "unique_codes", "recognised_category", "spec_completeness", "uom_clean",
    }  # fmt: skip
    # the generator writes one UoM alias per style: all are known, none ambiguous
    assert q["uom_ambiguous"] == 0 and q["uom_unknown"] == 0
    # stock and annual figures arrive from the master file
    stocked = "SELECT count(*) FROM material_record WHERE batch_id = :b AND stock_qty > 0"
    assert count(stocked, b=b["id"]) > 0
    assert "BATCH_INGESTED" in audit_actions()
    got = client.get(f"{BATCHES}/{b['id']}/quality", headers=login(client, "auditor"))
    assert got.status_code == 200 and got.json()["rows"] == q["rows"]


def test_reuploading_the_same_file_creates_nothing_new(client: TestClient, ids: Ids) -> None:
    first = upload(client, "meera")
    ingest(client, "meera", first["id"])
    again = upload(client, "meera")
    assert again["id"] == first["id"] and again["already_ingested"] is True
    assert count("SELECT count(*) FROM upload_batch") == 1
    assert ingest(client, "meera", first["id"])["status"] == "INGESTED"  # idempotent
    assert count("SELECT count(*) FROM material_record") == first["row_count"]


def test_a_changed_file_ingests_only_changed_rows(client: TestClient, ids: Ids) -> None:
    first = upload(client, "meera")
    ingest(client, "meera", first["id"])
    lines = synth()["cpse_A.csv"].decode().splitlines()
    lines[1] = lines[1].replace("VALVE", "VLV", 1) if "VALVE" in lines[1] else lines[1] + " X"
    changed = ("\n".join(lines) + "\n").encode()
    second = upload(client, "meera", data=changed)
    done = ingest(client, "meera", second["id"])
    assert done["quality"]["rows"] == 1  # DELTA: one changed row
    assert done["quality"]["skipped_unchanged"] == first["row_count"] - 1


def test_sap_style_extract_ingests_with_no_manual_mapping(client: TestClient, ids: Ids) -> None:
    sap = (
        b"MARA-MATNR;MAKT-MAKTX;MARA-MEINS;MARA-MATKL;MARC-WERKS\n"
        b"100001;GATE VALVE 4IN CL150 WCB FLGD RF;NOS;VLV;P1\n"
        b"100002;PIPE SMLS 4IN SCH40 A106 GR.B;MTR;PIP;P1\n"
    )
    b = upload(client, "meera", name="sap.csv", data=sap)
    assert b["preset"] == "SAP" and set(b["suggested_mapping"].values()) == {
        "legacy_code", "short_text", "uom", "mat_group", "plant",
    }  # fmt: skip
    q = ingest(client, "meera", b["id"])["quality"]
    assert q["rows"] == 2 and q["category_share"] == {"PIPE": 0.5, "VALVE": 0.5}
    assert count("SELECT count(*) FROM material_record WHERE uom_canonical IN ('EA','M')") == 2


def test_bad_rows_are_rejected_duplicates_dropped_and_ambiguous_uom_flagged(
    client: TestClient, ids: Ids
) -> None:
    csv = (
        b"legacy_code,short_text,uom\n"
        b"1,GATE VALVE 4IN CL150 WCB FLANGED RF,EA\n"
        b"1,GATE VALVE 4IN CL300 WCB FLANGED RF,EA\n"  # duplicate code
        b",NO CODE,EA\n"  # rejected
        b"3,,EA\n"  # rejected: no description
        b"4,PIPE SMLS 4IN SCH40 A106 GR.B,MT\n"  # MT is ambiguous (metre or tonne)
        b"5,PIPE SMLS 4IN SCH40 A53 GR.B,XYZ\n"  # unknown UoM
    )
    b = upload(client, "meera", name="x.csv", data=csv)
    q = ingest(client, "meera", b["id"])["quality"]
    assert (q["rows"], q["rejected_rows"], q["duplicate_legacy_codes"]) == (3, 2, 1)
    assert (q["uom_ambiguous"], q["uom_unknown"]) == (1, 1)
    assert count("SELECT count(*) FROM material_record WHERE uom_canonical IS NULL") == 2


def test_mapping_can_be_saved_and_changed_before_ingest(client: TestClient, ids: Ids) -> None:
    csv = b"Code,Text\n1,PIPE SMLS 4IN SCH40 A106 GR.B\n"
    b = upload(client, "meera", name="x.csv", data=csv)
    h = login(client, "meera")
    url = f"{BATCHES}/{b['id']}/mapping"
    bad = client.put(url, headers=h, json={"column_mapping": {"Code": "legacy_code"}})
    assert bad.status_code == 400
    assert bad.headers["content-type"].startswith("application/problem+json")
    both = {"column_mapping": {"Code": "legacy_code", "Text": "short_text"}}
    ok = client.put(url, headers=h, json=both)
    assert ok.status_code == 200 and ok.json()["status"] == "MAPPED"
    assert ingest(client, "meera", b["id"])["quality"]["rows"] == 1
    late = client.put(url, headers=h, json=both)
    assert late.status_code == 409


def test_ingest_without_a_mapping_is_refused(client: TestClient, ids: Ids) -> None:
    b = upload(client, "meera", name="x.csv", data=b"foo,bar\n1,2\n")
    assert b["suggested_mapping"] == {}
    r = client.post(f"{BATCHES}/{b['id']}/ingest", headers=login(client, "meera"))
    assert r.status_code == 400 and r.json()["title"] == "No mapping"


def test_a_maker_uploads_only_for_their_own_cpse(client: TestClient, ids: Ids) -> None:
    r = client.post(
        BATCHES, headers=login(client, "meera"), data={"cpse": "CPSE-B"},
        files={"file": ("a.csv", synth()["cpse_A.csv"], "text/csv")},
    )  # fmt: skip
    assert r.status_code == 403
    # the admin must name the CPSE
    one = {"file": ("a.csv", synth()["cpse_A.csv"], "text/csv")}
    r = client.post(BATCHES, headers=login(client, "admin"), files=one)
    assert r.status_code == 400 and r.json()["title"] == "CPSE required"
    ok = upload(client, "admin", cpse="CPSE-C")
    assert ok["cpse_code"] == "CPSE-C"
    # another CPSE's maker cannot ingest it
    r = client.post(f"{BATCHES}/{ok['id']}/ingest", headers=login(client, "meera"))
    assert r.status_code == 403


def test_procurement_history_is_hashed_and_idempotent(client: TestClient, ids: Ids) -> None:
    b = upload(client, "meera")
    h = login(client, "meera")
    proc_url = f"{BATCHES}/{b['id']}/procurement"
    proc_file = {"file": ("p.csv", synth()["procurement_A.csv"], "text/csv")}
    early = client.post(proc_url, headers=h, files=proc_file)
    assert early.status_code == 409  # ingest the master file first
    ingest(client, "meera", b["id"])
    r = client.post(proc_url, headers=h, files=proc_file)
    assert r.status_code == 200
    out = r.json()
    n_lines = len(synth()["procurement_A.csv"].splitlines()) - 1
    assert out == {"lines": n_lines, "unmatched": 0, "invalid": 0, "duplicates": 0}
    lines_sql = (
        "SELECT count(*) FROM procurement_line p JOIN material_record m ON m.id = p.record_id"
        " WHERE m.batch_id = :b"
    )
    assert count(lines_sql, b=b["id"]) == n_lines
    # raw vendor names never reach the database; the hash is the salted SHA-256 (64 hex chars)
    with get_engine().connect() as c:
        hashes = set(c.execute(text("SELECT vendor_hash FROM procurement_line")).scalars())
    assert hashes and all(h and len(h) == 64 for h in hashes)
    assert not any("SYNTH-VENDOR" in (h or "") for h in hashes)
    again = client.post(proc_url, headers=h, files=proc_file)
    assert again.json()["lines"] == 0 and again.json()["duplicates"] == n_lines
    assert "PROCUREMENT_INGESTED" in audit_actions()


def test_procurement_fills_annual_figures_only_where_the_master_file_gave_none(
    client: TestClient, ids: Ids
) -> None:
    master = (
        b"legacy_code,short_text,annual_value\n"
        b"1,PIPE SMLS 4IN SCH40 A106 GR.B,500\n"  # supplied: kept
        b"2,PIPE SMLS 6IN SCH40 A106 GR.B,\n"  # not supplied: filled
    )
    b = upload(client, "meera", name="m.csv", data=master)
    ingest(client, "meera", b["id"])
    proc = (
        b"legacy_code,po_date,qty,unit_price,vendor\n"
        b"1,2026-09-01,10,100,V1\n"
        b"2,2026-09-01,10,100,V1\n"
        b"2,2026-03-01,5,90,V2\n"
        b"2,2024-01-01,99,80,V1\n"  # older than 12 months before the last order: not counted
        b"9,2026-09-01,1,1,V1\n"  # no such record
        b"2,not-a-date,1,1,V1\n"
    )
    url = f"{BATCHES}/{b['id']}/procurement"
    r = client.post(
        url, headers=login(client, "meera"), files={"file": ("p.csv", proc, "text/csv")}
    )
    assert r.json() == {"lines": 4, "unmatched": 1, "invalid": 1, "duplicates": 0}
    with get_engine().connect() as c:
        got = dict(c.execute(text("SELECT legacy_code, annual_value FROM material_record")).all())
    assert float(got["1"]) == 500 and float(got["2"]) == 10 * 100 + 5 * 90


def test_listing_and_reading_batches_needs_a_signed_in_viewer(client: TestClient, ids: Ids) -> None:
    b = upload(client, "meera")
    assert client.get(BATCHES).status_code == 401
    assert client.get(BATCHES, headers=login(client, "erp")).status_code == 403
    rows = client.get(BATCHES, headers=login(client, "auditor")).json()
    assert [r["id"] for r in rows] == [b["id"]]
    missing = client.get(f"{BATCHES}/{uuid.uuid4()}", headers=login(client, "auditor"))
    assert missing.status_code == 404


@pytest.mark.parametrize("name", ["a.pdf", "a.exe"])
def test_unsupported_file_types_are_refused(client: TestClient, ids: Ids, name: str) -> None:
    r = client.post(
        BATCHES, headers=login(client, "meera"), files={"file": (name, b"x", "text/plain")}
    )
    assert r.status_code == 400 and r.json()["title"] == "Unsupported file type"
