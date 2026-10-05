"""`make seed`: CPSEs, demo users, templates and dictionaries (Backend Schema section 12).

Usage: python -m app.db.seed     (inside the api container; `make seed` does this)

Safe to run again: existing rows are left untouched (vendor salts never change).
Seeding is a bootstrap outside the app and writes no audit_event rows (DECISIONS.md DEC-11);
the hash chain starts with the first real action (Phase 3).
Synthetic batches come with the generator (Phases 4-5).
"""

import json
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import structlog
import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection, create_engine, text

from app.db.migrate import upgrade_head
from app.schemas.jsonb import DICTIONARY_CONTENT, TemplateDefinition, UomContent
from app.security.auth import hash_password

SECTOR = "Oil & Gas"
CPSES = [  # synthetic organisations, never real CPSE names
    ("CPSE-A", "Synthetic CPSE A"),
    ("CPSE-B", "Synthetic CPSE B"),
    ("CPSE-C", "Synthetic CPSE C"),
]


@dataclass(frozen=True)
class DemoUser:
    username: str
    display_name: str
    role: str
    cpse: str | None


USERS = [
    DemoUser("meera", "Meera", "MAKER", "CPSE-A"),
    DemoUser("arjun", "Arjun", "CHECKER", "CPSE-B"),
    DemoUser("kavya", "Kavya", "CHECKER", "CPSE-C"),  # gives the CPSE-C consent in the demo
    DemoUser("admin", "Admin", "ADMIN", None),
    DemoUser("auditor", "Auditor", "AUDITOR", None),
    DemoUser("erp", "ERP integration", "INTEGRATOR", None),
]

# Section 12: gasket v1 is ACTIVE only once the P1 gasket work is done
DRAFT_UNTIL_P1 = {"gasket"}
DICTIONARY_FILES = {"uom.yaml", "dictionary.yaml"}


class SeedSettings(BaseSettings):
    """TRD Appendix C variables used only by the seed."""

    model_config = SettingsConfigDict(extra="ignore")
    database_url: str
    template_dir: Path = Path("/app/templates")
    seed_demo_users: bool = True
    demo_password: str = Field(min_length=8)


@dataclass
class SeedResult:
    cpse: int = 0
    app_user: int = 0
    template: int = 0
    dictionary: int = 0


def load_templates(template_dir: Path) -> list[TemplateDefinition]:
    files = sorted(p for p in template_dir.glob("*.yaml") if p.name not in DICTIONARY_FILES)
    if not files:
        raise FileNotFoundError(f"no template YAML in {template_dir}")
    return [TemplateDefinition.model_validate(yaml.safe_load(p.read_text("utf-8"))) for p in files]


def load_dictionaries(template_dir: Path) -> list[tuple[str, int, Any]]:
    """(kind, version, content) for ABBREVIATION, HEADER_SYNONYM, UNSPSC_MAP, SPELLING and UOM."""
    doc = yaml.safe_load((template_dir / "dictionary.yaml").read_text("utf-8"))
    uom = yaml.safe_load((template_dir / "uom.yaml").read_text("utf-8"))
    out: list[tuple[str, int, Any]] = []
    for kind in ("ABBREVIATION", "HEADER_SYNONYM", "UNSPSC_MAP", "SPELLING"):
        content = DICTIONARY_CONTENT[kind].model_validate(doc[kind]).model_dump(mode="json")
        out.append((kind, int(doc["version"]), content))
    uom_content = UomContent.model_validate({k: v for k, v in uom.items() if k != "version"})
    out.append(("UOM", int(uom["version"]), uom_content.model_dump(mode="json")))
    return out


def _hash(password: str) -> str:
    return hash_password(password)  # bcrypt cost 12 (TR-SEC-01)


def seed(conn: Connection, settings: SeedSettings) -> SeedResult:
    """Insert the section 12 rows that are missing; returns how many rows were added."""
    res = SeedResult()
    templates = load_templates(settings.template_dir)
    dictionaries = load_dictionaries(settings.template_dir)

    for code, name in CPSES:
        res.cpse += conn.execute(
            text(
                "INSERT INTO cpse (code, name, sector, vendor_salt) VALUES (:c, :n, :s, :salt)"
                " ON CONFLICT (code) DO NOTHING"
            ),
            {"c": code, "n": name, "s": SECTOR, "salt": secrets.token_hex(32)},
        ).rowcount

    cpse_ids = dict(conn.execute(text("SELECT code, id FROM cpse")).all())
    password_hash = _hash(settings.demo_password)
    for u in USERS:
        res.app_user += conn.execute(
            text(
                "INSERT INTO app_user (username, display_name, password_hash, role, cpse_id,"
                " must_change_password) VALUES (:u, :d, :h, :r, :c, :m)"
                " ON CONFLICT (username) DO NOTHING"
            ),
            {
                "u": u.username,
                "d": u.display_name,
                "h": password_hash,
                "r": u.role,
                "c": cpse_ids[u.cpse] if u.cpse else None,
                "m": not settings.seed_demo_users,
            },
        ).rowcount

    for t in templates:
        status = "DRAFT" if t.id in DRAFT_UNTIL_P1 else "ACTIVE"
        res.template += conn.execute(
            text(
                "INSERT INTO template (id, version, category, definition, status, activated_at)"
                " VALUES (:i, :v, :c, CAST(:d AS jsonb), :s,"
                " CASE WHEN :s = 'ACTIVE' THEN now() END)"
                " ON CONFLICT (id, version) DO NOTHING"
            ),
            {
                "i": t.id,
                "v": t.version,
                "c": t.category,
                "d": t.model_dump_json(exclude_unset=True),
                "s": status,
            },
        ).rowcount

    for kind, version, content in dictionaries:
        known = conn.execute(
            text("SELECT 1 FROM dictionary WHERE kind = :k AND version = :v"),
            {"k": kind, "v": version},
        ).first()
        if known:
            continue
        # a newer file version replaces the active one (one ACTIVE row per kind)
        conn.execute(
            text(
                "UPDATE dictionary SET status = 'RETIRED'"
                " WHERE kind = :k AND status = 'ACTIVE' AND version < :v"
            ),
            {"k": kind, "v": version},
        )
        res.dictionary += conn.execute(
            text(
                "INSERT INTO dictionary (kind, version, content, status)"
                " VALUES (:k, :v, CAST(:c AS jsonb), 'ACTIVE')"
            ),
            {"k": kind, "v": version, "c": json.dumps(content, ensure_ascii=False)},
        ).rowcount
    return res


def main() -> int:
    structlog.configure(processors=[structlog.processors.JSONRenderer()])
    log = structlog.get_logger()
    settings = SeedSettings()  # type: ignore[call-arg]  # values come from the environment
    upgrade_head(settings.database_url)
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        res = seed(conn, settings)
    log.info("seed_done", added=res.__dict__, template_dir=str(settings.template_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
