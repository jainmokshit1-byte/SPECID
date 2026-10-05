"""Registry, crosswalk, exports, migration packs, change notices (PRD API-15, 17, 18, 35, 38)."""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.db.models import AppUser
from app.db.session import get_session
from app.security.permissions import Action
from app.security.rbac import require
from app.services import exports, migration, notices, registry
from app.services.errors import Forbidden

router = APIRouter(tags=["registry"])
reader = require(Action.VIEW_REGISTRY)
exporter = require(Action.EXPORT_REGISTRY)
notice_reader = require(Action.VIEW_NOTICES)
notice_acker = require(Action.ACK_NOTICES)


def _download(content: bytes, media: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=f"{media}; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/cnmc")
def list_cnmc(
    q: str | None = None,
    category: str | None = None,
    cpse: str | None = None,
    status: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    _: AppUser = Depends(reader),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    total, items = registry.list_cnmc(
        session, q=q, category=category, cpse=cpse, status=status, limit=limit, offset=offset
    )
    return {"total": total, "items": items}


@router.get("/cnmc/{cnmc}")
def get_cnmc(
    cnmc: str, _: AppUser = Depends(reader), session: Session = Depends(get_session)
) -> dict[str, Any]:
    return registry.get_cnmc(session, cnmc)


@router.get("/crosswalk")
def crosswalk(
    cnmc: str | None = None,
    cpse: str | None = None,
    legacy_code: str | None = None,
    _: AppUser = Depends(reader),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """API-17: crosswalk lookup (active rows)."""
    rows = exports.crosswalk_rows(session, cnmc=cnmc, cpse=cpse)
    if legacy_code:
        rows = [r for r in rows if r["legacy_code"] == legacy_code]
    return {"total": len(rows), "items": rows}


@router.get("/exports/crosswalk")
def export_crosswalk(
    format: Literal["csv", "json", "sap_csv"] = "csv",
    cnmc: str | None = None,
    cpse: str | None = None,
    user: AppUser = Depends(exporter),
    session: Session = Depends(get_session),
) -> Response:
    rows = exports.crosswalk_rows(session, cnmc=cnmc, cpse=cpse)
    content, media, ext = exports.crosswalk_file(rows, format)
    exports.record_download(session, user, "crosswalk", format=format, cnmc=cnmc, cpse=cpse,
                            rows=len(rows))  # fmt: skip
    session.commit()
    stem = "sap_crosswalk" if format == "sap_csv" else "crosswalk"
    suffix = f"_{cnmc or cpse}" if (cnmc or cpse) else ""
    return _download(content, media, f"specid_{stem}{suffix}.{ext}")


@router.get("/exports/migration-pack")
def migration_pack(
    cpse: str,
    user: AppUser = Depends(exporter),
    session: Session = Depends(get_session),
) -> Response:
    """API-35: the per-CPSE migration pack (writes the recommended actions back, audited)."""
    target = registry.cpse_by_code(session, cpse)
    if user.role in ("MAKER", "CHECKER") and user.cpse_id != target.id:
        raise Forbidden("You can download only your own CPSE's migration pack.")
    rows = migration.pack(session, user, target)
    exports.record_download(session, user, "migration-pack", cpse=cpse, rows=len(rows))
    session.commit()
    content = exports.to_csv(rows, migration.COLUMNS, preamble=migration.NOTE)
    return _download(content, "text/csv", f"specid_migration_pack_{cpse}.csv")


@router.get("/change-notices")
def list_notices(
    cpse: str | None = None,
    user: AppUser = Depends(notice_reader),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    target = notices.scope_cpse(session, user, cpse)
    items = notices.list_for(session, target)
    waiting = sum(1 for i in items if not i["acknowledged_at"])
    return {"cpse": target.code, "unacknowledged": waiting, "items": items}


@router.post("/change-notices/{notice_id}/ack")
def ack_notice(
    notice_id: uuid.UUID,
    user: AppUser = Depends(notice_acker),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    n = notices.acknowledge(session, user, notice_id)
    session.commit()
    return {"id": n.id, "acknowledged_at": n.acknowledged_at}


@router.get("/change-notices/{notice_id}/delta.csv")
def notice_delta(
    notice_id: uuid.UUID,
    user: AppUser = Depends(notice_reader),
    session: Session = Depends(get_session),
) -> Response:
    n = notices.get(session, user, notice_id)
    rows = list(n.delta or [])
    cols = sorted({k for r in rows for k in r}) or ["legacy_code", "cnmc"]
    return _download(exports.to_csv(rows, cols), "text/csv", f"specid_notice_{n.id}.csv")
