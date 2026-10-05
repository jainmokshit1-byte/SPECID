"""Uploads: file, mapping, ingest, quality, purchase history (PRD API-03 to API-06, API-33)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.templates import Template
from app.core.types import Dictionary
from app.db.models import AppUser, Cpse, UploadBatch
from app.db.session import get_session
from app.schemas.batches import BatchOut, BatchUploaded, MappingIn, ProcurementOut
from app.schemas.jsonb import BatchQuality
from app.security.permissions import Action
from app.security.rbac import require
from app.services import ingest
from app.services.errors import NotFound
from app.settings import Settings, get_settings

router = APIRouter(prefix="/batches", tags=["batches"])
uploader = require(Action.UPLOAD_BATCHES)
viewer = require(Action.VIEW_CLUSTERS)


def _dictionary(request: Request) -> Dictionary:
    return request.app.state.dictionary  # type: ignore[no-any-return]


def _templates(request: Request) -> dict[str, Template]:
    return request.app.state.templates  # type: ignore[no-any-return]


def _out(session: Session, batch: UploadBatch) -> BatchOut:
    cpse = session.get(Cpse, batch.cpse_id)
    assert cpse is not None
    return BatchOut(
        id=batch.id,
        cpse_code=cpse.code,
        filename=batch.filename,
        status=batch.status,
        row_count=batch.row_count,
        is_synthetic=batch.is_synthetic,
        column_mapping=batch.column_mapping,
        quality=BatchQuality.model_validate(batch.quality) if batch.quality else None,
        created_at=batch.created_at,
    )


@router.post("", response_model=BatchUploaded, status_code=201)
async def upload_batch(
    request: Request,
    response: Response,
    file: Annotated[UploadFile, File()],
    cpse: Annotated[str | None, Form()] = None,
    is_synthetic: Annotated[bool, Form()] = False,
    actor: AppUser = Depends(uploader),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> BatchUploaded:
    data = await file.read(ingest.MAX_BYTES + 1)
    target = ingest.resolve_cpse(session, actor, cpse)
    res = ingest.create_batch(
        session,
        actor,
        cpse=target,
        filename=file.filename or "upload.csv",
        data=data,
        is_synthetic=is_synthetic,
        dictionary=_dictionary(request),
        upload_dir=settings.upload_dir,
    )
    session.commit()
    if res.already_ingested:
        response.status_code = 200
    table = res.table
    out = _out(session, res.batch)
    return BatchUploaded(
        **out.model_dump(),
        columns=table.headers if table else [],
        suggested_mapping=res.suggested,
        preset=res.preset,
        sample_rows=(
            [dict(zip(table.headers, r, strict=True)) for r in table.rows[: ingest.SAMPLE_ROWS]]
            if table
            else []
        ),
        encoding=table.encoding if table else None,
        already_ingested=res.already_ingested,
    )


@router.put("/{batch_id}/mapping", response_model=BatchOut)
def put_mapping(
    batch_id: uuid.UUID,
    body: MappingIn,
    actor: AppUser = Depends(uploader),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> BatchOut:
    batch = ingest.get_batch(session, batch_id)
    ingest.save_mapping(session, actor, batch, body.column_mapping, settings.upload_dir)
    session.commit()
    return _out(session, batch)


@router.post("/{batch_id}/ingest", response_model=BatchOut)
def ingest_batch(
    batch_id: uuid.UUID,
    request: Request,
    actor: AppUser = Depends(uploader),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> BatchOut:
    batch = ingest.get_batch(session, batch_id)
    ingest.ingest_batch(
        session,
        actor,
        batch,
        dictionary=_dictionary(request),
        templates=_templates(request),
        threshold=settings.classifier_threshold,
        upload_dir=settings.upload_dir,
        model=getattr(request.app.state, "classifier", None),
    )
    session.commit()
    return _out(session, batch)


@router.get("", response_model=list[BatchOut])
def list_batches(
    _: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> list[BatchOut]:
    batches = session.scalars(select(UploadBatch).order_by(UploadBatch.created_at.desc())).all()
    return [_out(session, b) for b in batches]


@router.get("/{batch_id}", response_model=BatchOut)
def get_batch(
    batch_id: uuid.UUID, _: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> BatchOut:
    return _out(session, ingest.get_batch(session, batch_id))


@router.get("/{batch_id}/quality", response_model=BatchQuality)
def get_quality(
    batch_id: uuid.UUID, _: AppUser = Depends(viewer), session: Session = Depends(get_session)
) -> BatchQuality:
    batch = ingest.get_batch(session, batch_id)
    if not batch.quality:
        raise NotFound("This batch has not been ingested yet.")
    return BatchQuality.model_validate(batch.quality)


@router.post("/{batch_id}/procurement", response_model=ProcurementOut)
async def upload_procurement(
    batch_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
    actor: AppUser = Depends(uploader),
    session: Session = Depends(get_session),
) -> ProcurementOut:
    data = await file.read(ingest.MAX_BYTES + 1)
    batch = ingest.get_batch(session, batch_id)
    counts = ingest.ingest_procurement(
        session, actor, batch, filename=file.filename or "procurement.csv", data=data
    )
    session.commit()
    return ProcurementOut(**counts)
