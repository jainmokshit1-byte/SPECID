"""Backend Schema section 12: `make seed` rows (CPSEs, demo users, templates, dictionaries)."""

import os
from pathlib import Path

import bcrypt
import pytest
import yaml
from sqlalchemy import Connection, text

from app.db.seed import USERS, SeedSettings, load_templates, seed

TEMPLATE_DIR = Path(
    os.environ.get("TEMPLATE_DIR", Path(__file__).resolve().parents[3] / "templates")
)
PASSWORD = "test-only-demo-password"


def _settings(seed_demo_users: bool = True) -> SeedSettings:
    if not (TEMPLATE_DIR / "valve.yaml").exists():
        pytest.skip("templates/ not mounted")
    return SeedSettings(
        database_url="unused",
        template_dir=TEMPLATE_DIR,
        seed_demo_users=seed_demo_users,
        demo_password=PASSWORD,
    )


def test_seed_creates_section_12_rows_once(conn: Connection) -> None:
    s = _settings()
    first = seed(conn, s)
    salts = dict(conn.execute(text("SELECT code, vendor_salt FROM cpse")).all())
    second = seed(conn, s)

    assert (first.cpse, first.app_user, first.template, first.dictionary) == (3, 6, 6, 4)
    assert (second.cpse, second.app_user, second.template, second.dictionary) == (0, 0, 0, 0)
    # re-running never changes a salt (vendor hashes stay stable, TRD TR-MOD-21)
    assert dict(conn.execute(text("SELECT code, vendor_salt FROM cpse")).all()) == salts
    assert len(set(salts.values())) == 3


def test_cpses_are_synthetic_oil_and_gas(conn: Connection) -> None:
    seed(conn, _settings())
    rows = conn.execute(text("SELECT code, name, sector FROM cpse ORDER BY code")).all()
    assert [r.code for r in rows] == ["CPSE-A", "CPSE-B", "CPSE-C"]
    assert all(r.name.startswith("Synthetic") and r.sector == "Oil & Gas" for r in rows)


def test_demo_users_roles_cpses_and_passwords(conn: Connection) -> None:
    seed(conn, _settings())
    rows = conn.execute(
        text(
            "SELECT u.username, u.role, c.code, u.password_hash, u.must_change_password,"
            " u.is_active FROM app_user u LEFT JOIN cpse c ON c.id = u.cpse_id"
        )
    ).all()
    got = {r.username: (r.role, r.code) for r in rows}
    assert got == {
        "meera": ("MAKER", "CPSE-A"),
        "arjun": ("CHECKER", "CPSE-B"),
        "kavya": ("CHECKER", "CPSE-C"),
        "admin": ("ADMIN", None),
        "auditor": ("AUDITOR", None),
        "erp": ("INTEGRATOR", None),
    }
    assert len(USERS) == 6
    for r in rows:
        assert r.password_hash.startswith("$2")  # bcrypt, never plain text
        assert bcrypt.checkpw(PASSWORD.encode(), r.password_hash.encode())
        assert r.must_change_password is False and r.is_active is True


def test_users_must_change_password_without_seed_demo_users(conn: Connection) -> None:
    seed(conn, _settings(seed_demo_users=False))
    flags = set(conn.execute(text("SELECT must_change_password FROM app_user")).scalars())
    assert flags == {True}


def test_templates_five_active_gasket_draft(conn: Connection) -> None:
    seed(conn, _settings())
    rows = dict(conn.execute(text("SELECT id, status FROM template WHERE version = 1")).all())
    assert rows == {
        "valve": "ACTIVE",
        "pipe": "ACTIVE",
        "flange": "ACTIVE",
        "fastener": "ACTIVE",
        "motor": "ACTIVE",
        "gasket": "DRAFT",
    }
    rule = conn.execute(
        text("SELECT definition->'rule_text'->>'schedule' FROM template WHERE id = 'pipe'")
    ).scalar()
    assert rule == "STD = SCH40 only for DN <= 250; XS = SCH80 only for DN <= 200"


def test_dictionaries_v1_active(conn: Connection) -> None:
    seed(conn, _settings())
    rows = {
        r.kind: r.content
        for r in conn.execute(text("SELECT kind, content FROM dictionary WHERE status = 'ACTIVE'"))
    }
    assert set(rows) == {"ABBREVIATION", "UOM", "HEADER_SYNONYM", "UNSPSC_MAP"}
    assert rows["ABBREVIATION"]["FLGD"] == "FLANGED"
    assert rows["UOM"]["aliases"]["NOS"] == "EA" and rows["UOM"]["aliases"]["NO"] == "EA"
    assert rows["UOM"]["ambiguous"] == ["MT"] and "MT" not in rows["UOM"]["aliases"]
    assert "matnr" in rows["HEADER_SYNONYM"]["legacy_code"]
    assert rows["UNSPSC_MAP"] == {}  # FR-405: no unverified code


def test_seed_writes_no_audit_events(conn: Connection) -> None:
    seed(conn, _settings())  # DEC-11: bootstrap outside the app
    assert conn.execute(text("SELECT count(*) FROM audit_event")).scalar() == 0


def test_template_files_match_prd_appendix_a() -> None:
    """Every template YAML document in PRD Appendix A is a file in templates/, unchanged."""
    doc = TEMPLATE_DIR.parent / "impdocs" / "SIH26099_SpecID_Prototype_PRD.md"
    if not doc.exists():
        doc = Path("/impdocs/SIH26099_SpecID_Prototype_PRD.md")
    if not doc.exists() or not (TEMPLATE_DIR / "valve.yaml").exists():
        pytest.skip("impdocs/ or templates/ not mounted")

    text_ = doc.read_text(encoding="utf-8")
    block = text_[text_.index("## Appendix A: Category templates") :]
    start = block.index("```yaml\n") + len("```yaml\n")
    block = block[start : block.index("\n```", start)]
    expected = {d["id"]: d for d in yaml.safe_load_all(block)}
    got = {t.id: t.model_dump(exclude_unset=True) for t in load_templates(TEMPLATE_DIR)}
    assert got == expected
