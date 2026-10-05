"""Harmonisation runs (PRD API-07 to API-09): start, progress, cancel, pairs."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.templates import Template
from app.core.types import Dictionary
from app.db.models import AppUser, Run
from app.db.session import get_session
from app.schemas.runs import PairOut, PairPage, RunIn, RunOut
from app.security.permissions import Action
from app.security.rbac import require
from app.services import harmonise, jobs
from app.services.errors import NotFound
from app.settings import Settings, get_settings

router = APIRouter(prefix="/runs", tags=["runs"])
starter = require(Action.START_RUNS)
viewer = require(Action.VIEW_CLUSTERS)


def _out(session: Session, run: Run) -> RunOut:
    name = (
        session.scalar(text("SELECT username FROM app_user WHERE id = :i"), {"i": run.started_by})
        if run.started_by
        else None
    )
    return RunOut(
        id=run.id,
        status=run.status,
        mode=run.mode,
        batch_ids=list(run.batch_ids),
        config=run.config,
        stats=run.stats,
        error=run.error,
        started_by=name,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


def _get(session: Session, run_id: uuid.UUID) -> Run:
    run = session.get(Run, run_id)
    if run is None:
        raise NotFound("No such run.")
    return run


@router.post("", response_model=RunOut, status_code=202)
def start_run(
    body: RunIn,
    request: Request,
    actor: AppUser = Depends(starter),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> RunOut:
    templates: dict[str, Template] = request.app.state.templates
    dictionary: Dictionary = request.app.state.dictionary
    run = harmonise.create_run(
        session,
        actor,
        batch_ids=body.batch_ids,
        mode=body.mode,
        options=body.options,
        settings=settings,
        templates=templates,
        dictionary=dictionary,
    )
    session.commit()  # the job reads the run from the database
    jobs.submit(run.id, templates, dictionary)
    session.refresh(run)
    return _out(session, run)


@router.get("", response_model=list[RunOut])
def list_runs(
    _: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> list[RunOut]:
    runs = session.scalars(select(Run).order_by(Run.started_at.desc()).limit(100)).all()
    return [_out(session, r) for r in runs]


@router.get("/{run_id}", response_model=RunOut)
def get_run(
    run_id: uuid.UUID, _: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> RunOut:
    return _out(session, _get(session, run_id))


@router.post("/{run_id}/cancel", response_model=RunOut)
def cancel_run(
    run_id: uuid.UUID, actor: AppUser = Depends(starter), session: Session = Depends(get_session)
) -> RunOut:
    run = harmonise.request_cancel(session, actor, _get(session, run_id))
    session.commit()
    return _out(session, run)


@router.get("/{run_id}/pairs", response_model=PairPage)
def list_pairs(
    run_id: uuid.UUID,
    response: Response,
    verdict: str | None = None,
    route: str | None = None,
    category: str | None = None,
    lookalike: str | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    _: AppUser = Depends(viewer),
    session: Session = Depends(get_session),
) -> PairPage:
    _get(session, run_id)
    where = "p.run_id = :run"
    args: dict[str, object] = {"run": run_id, "limit": limit, "offset": offset}
    for column, value in (("p.verdict", verdict), ("p.route", route), ("p.lookalike", lookalike),
                          ("sa.category", category)):  # fmt: skip
        if value:
            where += f" AND {column} = :{column.split('.')[1]}"
            args[column.split(".")[1]] = value
    frm = (
        "FROM pair_decision p"
        " JOIN material_record a ON a.id = p.rec_a JOIN cpse ca ON ca.id = a.cpse_id"
        " JOIN material_record b ON b.id = p.rec_b JOIN cpse cb ON cb.id = b.cpse_id"
        " LEFT JOIN spec_record sa ON sa.record_id = p.rec_a"
    )
    total = session.scalar(text(f"SELECT count(*) {frm} WHERE {where}"), args)  # noqa: S608
    rows = session.execute(
        text(
            "SELECT p.id, p.rec_a, p.rec_b, ca.code, a.legacy_code, a.short_text,"
            " cb.code, b.legacy_code, b.short_text, p.verdict, p.route, p.p_equiv, p.text_sim,"
            f" p.lookalike, p.channels, p.reasons {frm} WHERE {where}"  # noqa: S608
            " ORDER BY p.text_sim DESC NULLS LAST, p.id LIMIT :limit OFFSET :offset"
        ),
        args,
    ).all()
    items = [
        PairOut(
            id=r[0], rec_a=r[1], rec_b=r[2], cpse_a=r[3], code_a=r[4], text_a=r[5], cpse_b=r[6],
            code_b=r[7], text_b=r[8], verdict=r[9], route=r[10],
            p_equiv=float(r[11]) if r[11] is not None else None,
            text_sim=float(r[12]) if r[12] is not None else None,
            lookalike=r[13], channels=r[14], reasons=list(r[15]),
        )
        for r in rows
    ]  # fmt: skip
    return PairPage(total=total or 0, items=items)
