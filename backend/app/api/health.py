"""API-24 `GET /health` (PRD section 8; TRD TR-OPS-09, 8.2 System group).

Reports DB status, model manifest, template versions, egress-guard status and git commit.
Templates are loaded in Phase 2 and the egress guard is installed in Phase 5; until then the
response says so instead of claiming them.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy import Engine

from app.db.session import get_engine, ping
from app.settings import Settings, get_settings

router = APIRouter(tags=["system"])

APP_VERSION = "0.1.0"


def _model_manifest(model_dir: str) -> dict[str, Any] | None:
    path = Path(model_dir) / "manifest.json"
    if not path.is_file():
        return None
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (OSError, ValueError):
        return {"error": "manifest.json unreadable"}


@router.get("/health")
def health(
    response: Response,
    settings: Settings = Depends(get_settings),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    db_ok = ping(engine)
    if not db_ok:
        response.status_code = 503
    return {
        "status": "ok" if db_ok else "unavailable",
        "version": APP_VERSION,
        "git_commit": settings.git_commit,
        "db": "ok" if db_ok else "unreachable",
        "models": _model_manifest(settings.model_dir),
        "templates": None,  # loaded from YAML from Phase 2
        "egress_guard": {"enabled": settings.egress_guard_enabled, "installed": False},
        "consent_mode": settings.consent_mode,
        "embeddings_enabled": settings.embeddings_enabled,
    }
