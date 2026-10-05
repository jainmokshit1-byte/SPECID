"""Review queue, cluster review, pair evidence and consent (PRD API-10 to API-13, API-37).

API-13 is split in two paths so each declares exactly one row of the permission matrix
(DEC-39): `POST /clusters/{id}/propose` (MAKER) and `POST /clusters/{id}/check` (CHECKER).
"""

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import AppUser
from app.db.session import get_session
from app.security.permissions import Action
from app.security.rbac import require
from app.services import review
from app.services.errors import NotFound
from app.settings import Settings, get_settings

router = APIRouter(tags=["review"])
viewer = require(Action.VIEW_CLUSTERS)
maker = require(Action.PROPOSE_REVIEW)
checker = require(Action.CONFIRM_REVIEW)
steward = require(Action.CONSENT)


class ProposeIn(BaseModel):
    decision: Literal["APPROVE", "REJECT", "SPLIT", "NEEDS_INFO"]
    comment: str | None = Field(default=None, max_length=2000)
    split_groups: list[list[uuid.UUID]] | None = None


class CheckIn(BaseModel):
    action: Literal["CONFIRM", "OVERTURN"]
    comment: str | None = Field(default=None, max_length=2000)


class ConsentIn(BaseModel):
    decision: Literal["CONSENT", "DECLINE"]
    reason: str | None = Field(default=None, max_length=2000)


class Outcome(BaseModel):
    state: str
    cnmc: str | None
    waiting_for: list[str]


@router.get("/clusters")
def list_clusters(
    run_id: uuid.UUID | None = None,
    stage: str | None = None,
    category: str | None = None,
    critical: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    user: AppUser = Depends(viewer),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    total, items = review.queue(
        session, user, run_id=run_id, stage=stage, category=category, critical=critical,
        limit=limit, offset=offset,
    )  # fmt: skip
    return {"total": total, "items": items}


@router.get("/clusters/{cluster_id}")
def get_cluster(
    cluster_id: uuid.UUID, user: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> dict[str, Any]:
    return review.cluster_detail(session, user, cluster_id)


@router.post("/clusters/{cluster_id}/propose", response_model=Outcome)
def propose(
    cluster_id: uuid.UUID,
    body: ProposeIn,
    user: AppUser = Depends(maker),
    session: Session = Depends(get_session),
) -> Outcome:
    task = review.propose(session, user, cluster_id, body.decision, body.comment, body.split_groups)
    session.commit()
    return Outcome(state=task.state, cnmc=None, waiting_for=[])


@router.post("/clusters/{cluster_id}/check", response_model=Outcome)
def check(
    cluster_id: uuid.UUID,
    body: CheckIn,
    user: AppUser = Depends(checker),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Outcome:
    out = review.check(
        session, user, cluster_id, body.action, body.comment, consent_mode=settings.consent_mode
    )
    session.commit()
    return Outcome(**out)


@router.get("/consents")
def consent_queue(
    user: AppUser = Depends(steward), session: Session = Depends(get_session)
) -> dict[str, Any]:
    items = review.consent_queue(session, user)
    return {"total": len(items), "items": items}


@router.post("/clusters/{cluster_id}/consent", response_model=Outcome)
def consent(
    cluster_id: uuid.UUID,
    body: ConsentIn,
    user: AppUser = Depends(steward),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Outcome:
    out = review.answer_consent(
        session, user, cluster_id, body.decision, body.reason, consent_mode=settings.consent_mode
    )
    session.commit()
    return Outcome(**out)


@router.get("/pairs/{pair_id}")
def get_pair(
    pair_id: uuid.UUID, _: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> dict[str, Any]:
    """API-10: one evidence card with both raw texts and the baseline flags."""
    r = session.execute(
        text("""
            SELECT p.id, p.run_id, p.verdict, p.route, p.p_equiv, p.text_sim, p.lookalike,
                   p.baseline, p.channels, p.reasons, p.evidence, p.template_version,
                   ca.code, a.legacy_code, a.short_text, a.long_text, a.manufacturer, a.mpn,
                   cb.code, b.legacy_code, b.short_text, b.long_text, b.manufacturer, b.mpn,
                   sa.category, p.rec_a, p.rec_b
            FROM pair_decision p
            JOIN material_record a ON a.id = p.rec_a JOIN cpse ca ON ca.id = a.cpse_id
            JOIN material_record b ON b.id = p.rec_b JOIN cpse cb ON cb.id = b.cpse_id
            LEFT JOIN spec_record sa ON sa.record_id = p.rec_a
            WHERE p.id = :p
            """),
        {"p": pair_id},
    ).first()
    if r is None:
        raise NotFound("No such pair.")

    def side(o: int, rid: Any) -> dict[str, Any]:
        return {"record_id": rid, "cpse": r[o], "legacy_code": r[o + 1], "short_text": r[o + 2],
                "long_text": r[o + 3], "manufacturer": r[o + 4], "mpn": r[o + 5]}  # fmt: skip

    return {
        "id": r[0], "run_id": r[1], "verdict": r[2], "route": r[3],
        "p_equiv": float(r[4]) if r[4] is not None else None,
        "text_sim": float(r[5]) if r[5] is not None else None, "lookalike": r[6],
        "baseline": r[7], "channels": r[8], "reasons": list(r[9]), "evidence": r[10],
        "template_version": r[11], "a": side(12, r[25]), "b": side(18, r[26]), "category": r[24],
    }  # fmt: skip
