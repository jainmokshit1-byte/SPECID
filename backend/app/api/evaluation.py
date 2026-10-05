"""Evaluation runs (PRD API-22, API-27): start, list, read, Markdown report."""

import threading
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import AppUser, EvalRun
from app.db.session import get_session, get_session_factory
from app.eval.runner import evaluate
from app.security.permissions import Action
from app.security.rbac import require
from app.services import audit, jobs
from app.services.errors import NotFound
from app.settings import Settings, get_settings

router = APIRouter(prefix="/eval", tags=["evaluation"])
starter = require(Action.START_RUNS)
viewer = require(Action.VIEW_CLUSTERS)


class EvalIn(BaseModel):
    seed: int = Field(ge=0, le=10_000)  # required: the seed makes the result reproducible
    n_entities: int = Field(default=1200, ge=50, le=5000)
    hard_negative_share: float = Field(default=0.5, ge=0, le=1)


def _out(e: EvalRun, names: dict[Any, str]) -> dict[str, Any]:
    return {
        "id": e.id,
        "kind": e.kind,
        "seed": e.seed,
        "config": e.config,
        "status": e.status,
        "metrics": e.metrics,
        "git_commit": e.git_commit,
        "created_at": e.created_at,
        "created_by": names.get(e.created_by),
    }


def _execute(eval_id: uuid.UUID, body: EvalIn, app_state: Any, actor: uuid.UUID) -> None:
    factory = get_session_factory()
    with factory() as s:
        s.execute(text("UPDATE eval_run SET status = 'RUNNING' WHERE id = :i"), {"i": eval_id})
        s.commit()
    try:
        metrics = evaluate(
            seed=body.seed,
            n_entities=body.n_entities,
            hard_negative_share=body.hard_negative_share,
            templates=app_state.templates,
            dictionary=app_state.dictionary,
            classifier=getattr(app_state, "classifier", None),
        )
        status = "DONE"
    except Exception as exc:  # reported on the page, never hidden
        metrics, status = {"error": f"{type(exc).__name__}: {exc}"}, "FAILED"
    with factory() as s:
        e = s.get(EvalRun, eval_id)
        assert e is not None
        e.status, e.metrics = status, metrics
        audit.record(
            s,
            actor_id=actor,
            action="EVAL_DONE",
            object_type="eval_run",
            object_id=str(eval_id),
            after={"status": status},
        )
        s.commit()


@router.post("/runs", status_code=202)
def start_eval(
    body: EvalIn,
    request: Request,
    actor: AppUser = Depends(starter),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    e = EvalRun(
        kind="SYNTHETIC",
        seed=body.seed,
        config=body.model_dump(),
        status="QUEUED",
        git_commit=settings.git_commit,
        created_by=actor.id,
    )
    session.add(e)
    session.flush()
    audit.record(
        session,
        actor_id=actor.id,
        action="EVAL_STARTED",
        object_type="eval_run",
        object_id=str(e.id),
        after=body.model_dump(),
    )
    session.commit()
    if jobs.INLINE:
        _execute(e.id, body, request.app.state, actor.id)
    else:
        threading.Thread(
            target=_execute, args=(e.id, body, request.app.state, actor.id), daemon=True
        ).start()
    session.refresh(e)
    return _out(e, {actor.id: actor.username})


@router.get("/runs")
def list_evals(
    _: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> list[dict[str, Any]]:
    names = dict(session.execute(text("SELECT id, username FROM app_user")).all())
    rows = session.scalars(select(EvalRun).order_by(EvalRun.created_at.desc()).limit(50)).all()
    return [_out(e, names) for e in rows]


@router.get("/runs/{eval_id}")
def get_eval(
    eval_id: uuid.UUID, _: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> dict[str, Any]:
    e = session.get(EvalRun, eval_id)
    if e is None:
        raise NotFound("No such evaluation.")
    names = dict(session.execute(text("SELECT id, username FROM app_user")).all())
    return _out(e, names)


@router.get("/runs/{eval_id}/report.md")
def report(
    eval_id: uuid.UUID, _: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> Response:
    e = session.get(EvalRun, eval_id)
    if e is None or not e.metrics or e.status != "DONE":
        raise NotFound("No finished evaluation with this id.")
    m = e.metrics
    s, one, two = m["methods"]["specid"], m["methods"]["b1"], m["methods"]["b2"]

    def row(name: str, x: dict[str, Any]) -> str:
        return (
            f"| {name} | {x['false_merges']} of {x['hard_negatives']} "
            f"(95% upper {x['false_merge_upper_95']}) | {x['tp']} | {x['precision']} | "
            f"{x['recall_strict']} | {x['coverage']} |"
        )

    lines = [
        f"# SpecID evaluation {e.id}",
        "",
        f"**SYNTHETIC DATA.** {m['honesty']}",
        "",
        f"Seed {e.seed}, commit {e.git_commit}, records {m['dataset']['records']}, "
        f"candidate pairs {m['dataset']['candidate_pairs']}"
        f" (test split {m['dataset']['test_pairs']}).",
        "",
        "| Method | False merges on hard negatives | Equivalents found | Precision"
        " | Recall (strict) | Coverage |",
        "|---|---|---|---|---|---|",
        row("SpecID", s),
        row(f"B1 text only (tau {one['tau']})", one),
        row(f"B2 text + numbers (tau {two['tau']})", two),
        "",
        f"Pair completeness {m['blocking']['pair_completeness']}, reduction ratio "
        f"{m['blocking']['reduction_ratio']}. Abstentions {m['abstentions']['total']} "
        f"({m['abstentions']['justified']} where the generator removed a key attribute).",
    ]
    return Response(
        "\n".join(lines) + "\n",
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="eval_{e.id}.md"'},
    )
