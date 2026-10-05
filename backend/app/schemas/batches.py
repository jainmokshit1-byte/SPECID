"""Request and response models for uploads (PRD API-03 to API-06, API-33)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.jsonb import BatchQuality


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cpse_code: str
    filename: str
    status: str
    row_count: int | None
    is_synthetic: bool
    column_mapping: dict[str, str] | None
    quality: BatchQuality | None
    created_at: datetime


class BatchUploaded(BatchOut):
    """Upload response: what the mapping step needs (API-03)."""

    columns: list[str]
    suggested_mapping: dict[str, str]
    preset: str | None
    sample_rows: list[dict[str, Any]]
    encoding: str | None
    already_ingested: bool


class MappingIn(BaseModel):
    column_mapping: dict[str, str]


class ProcurementOut(BaseModel):
    lines: int
    unmatched: int
    invalid: int
    duplicates: int
