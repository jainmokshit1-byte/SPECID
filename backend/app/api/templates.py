"""API-15 `GET /templates`, `GET /templates/{id}` (PRD FR-401): the rulebook, read-only. Every role
may read the rules that decide a match; changing them is a reviewed code change (DEC-43)."""

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.core.templates import Template
from app.db.models import AppUser
from app.security.rbac import current_user
from app.services.errors import NotFound

router = APIRouter(prefix="/templates", tags=["templates"])


def _templates(request: Request) -> dict[str, Template]:
    return request.app.state.templates  # type: ignore[no-any-return]


def _summary(t: Template) -> dict[str, Any]:
    return {
        "id": t.id,
        "category": t.category,
        "version": t.version,
        "status": "ACTIVE",
        "critical_default": t.critical_default,
        "core": t.core,
        "extended": t.extended,
        "rules": len(t.rules),
    }


@router.get("")
def list_templates(request: Request, _: AppUser = Depends(current_user)) -> list[dict[str, Any]]:
    return [_summary(t) for t in sorted(_templates(request).values(), key=lambda t: t.category)]


@router.get("/{template_id}")
def get_template(
    template_id: str, request: Request, _: AppUser = Depends(current_user)
) -> dict[str, Any]:
    for t in _templates(request).values():
        if t.id == template_id or t.category == template_id.upper():
            detail = t.model_dump(exclude={"id", "category", "version", "rules"})
            return {**_summary(t), **detail, "rules": t.rules}
    raise NotFound(f"No rulebook entry {template_id}.")
