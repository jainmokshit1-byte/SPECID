"""Search-before-create, dashboard, Look-alike Guard and money views
(PRD API-19, API-25, API-26, API-31, API-34)."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.models import AppUser
from app.db.session import get_session
from app.security.permissions import Action
from app.security.rbac import require
from app.services import insights, search
from app.settings import Settings, get_settings

router = APIRouter(tags=["insights"])
searcher = require(Action.SEARCH_BEFORE_CREATE)
viewer = require(Action.VIEW_CLUSTERS)
guard = require(Action.VIEW_GUARD)


class SearchIn(BaseModel):
    text: str = Field(min_length=2, max_length=500)
    mpn: str | None = Field(default=None, max_length=100)
    manufacturer: str | None = Field(default=None, max_length=100)


@router.post("/search-before-create")
def search_before_create(
    body: SearchIn,
    request: Request,
    _: AppUser = Depends(searcher),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return search.search(
        session,
        text_in=body.text,
        mpn=body.mpn,
        manufacturer=body.manufacturer,
        templates=request.app.state.templates,
        dictionary=request.app.state.dictionary,
        threshold=settings.classifier_threshold,
        model=getattr(request.app.state, "classifier", None),
    )


@router.get("/dashboard")
def dashboard(
    run_id: uuid.UUID | None = None,
    _: AppUser = Depends(viewer),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return insights.dashboard(session, run_id)


@router.get("/pooling")
def pooling(
    run_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    _: AppUser = Depends(viewer),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    rid = insights.resolve_run(session, run_id)
    if rid is None:
        return {"run_id": None}
    return {"run_id": rid, **insights.money_summary(session, rid, limit)}


@router.get("/radar/lookalikes")
def lookalikes(
    run_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    _: AppUser = Depends(guard),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return insights.lookalikes(session, run_id, "vetoed", limit)


@router.get("/radar/hidden-twins")
def hidden_twins(
    run_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    _: AppUser = Depends(guard),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return insights.lookalikes(session, run_id, "twins", limit)
