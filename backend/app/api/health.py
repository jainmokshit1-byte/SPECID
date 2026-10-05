"""API-24 `GET /health` (PRD section 8; TRD TR-OPS-09, 8.2 System group).

Reports DB status, model manifest, template versions, egress-guard status and git commit.
Template versions come from the YAML loaded at startup (Phase 4). The egress guard is reported as
installed only when it really is (WP1.13).
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import Engine

from app.db.session import get_engine, ping
from app.security import egress
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


def _template_versions(request: Request) -> dict[str, int] | None:
    """`{template id: version}` of the template files loaded at startup."""
    templates = getattr(request.app.state, "templates", None)
    return {t.id: t.version for t in templates.values()} if templates else None


@router.get("/health")
def health(
    request: Request,
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
        "templates": _template_versions(request),
        "egress_guard": {
            "enabled": settings.egress_guard_enabled,
            "installed": egress.guard_installed(),
        },
        "consent_mode": settings.consent_mode,
        "embeddings_enabled": settings.embeddings_enabled,
    }
